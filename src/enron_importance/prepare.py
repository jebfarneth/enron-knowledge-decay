"""Phase 1 pipeline: raw archive -> cleaned, deduplicated, flagged messages (threads are linked later).

Writes
  data/processed/messages.parquet   one row per kept message
  data/processed/senders.parquet    one row per sender with automation flags
  data/processed/copies.parquet     every discarded duplicate and the message kept for it
  data/processed/funnel.json        counts at every step + output checksums

Usage: uv run python -m enron_importance.prepare
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from .clean import authored_text, has_quoted_material
from .config import load_config
from .dedupe import deduplicate, flag_shifted_copies, restrict_window
from .download import ensure_corpus, sha256_of
from .ingest import iter_archive, write_messages
from .senders import automated_messages, routine_messages, sender_profiles, speech_act, structured_record


PACKAGE = Path(__file__).resolve().parent


def code_hash(*names: str) -> str:
    """SHA-256 over the named source files of this package (all of them if none given)."""
    files = [PACKAGE / name for name in names] if names else sorted(PACKAGE.rglob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(PACKAGE).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def parsed_messages(config: dict) -> pd.DataFrame:
    """The parsed archive, re-parsed unless the cache was built from this archive by this parser.

    The archive is verified against its pinned size and SHA-256 on every run,
    cached or not. The cache stamp records the archive checksum, the parser's
    source, the Python and dependency versions (uv.lock) and the parsed
    table's own checksum, which is checked before the cache is reused.
    """
    archive = ensure_corpus(config)
    raw_table = config["paths"]["interim"] / "messages_raw.parquet"
    stamp_path = raw_table.with_suffix(".json")
    lock = PACKAGE.parents[1] / "uv.lock"
    inputs = {"corpus_sha256": config["corpus"]["sha256"], "parser_sha256": code_hash("ingest.py"),
              "python": sys.version.split()[0], "uv_lock_sha256": sha256_of(lock) if lock.exists() else None}
    stamp = json.loads(stamp_path.read_text()) if stamp_path.exists() else {}
    cached = (raw_table.exists() and {k: stamp.get(k) for k in inputs} == inputs
              and stamp.get("output_sha256") == sha256_of(raw_table))
    if not cached:
        partial = raw_table.with_suffix(".parquet.part")
        write_messages(iter_archive(archive), partial)
        partial.replace(raw_table)
        stamp_path.write_text(json.dumps({**inputs, "output_sha256": sha256_of(raw_table)}, indent=2) + "\n")
    return pd.read_parquet(raw_table)


def prepare(config: dict) -> dict:
    paths = config["paths"]
    messages = parsed_messages(config)
    funnel: dict[str, int] = {"parsed_files": len(messages)}

    messages, dropped = restrict_window(messages, config["ingest"]["start"], config["ingest"]["end"])
    funnel.update({f"dropped_{key}": value for key, value in dropped.items()})
    funnel["in_window"] = len(messages)

    messages, removed, copies = deduplicate(messages)
    funnel.update({f"dropped_{key}" if key.startswith("duplicate") else key: value for key, value in removed.items()})
    funnel["unique_messages"] = len(messages)
    shifted = config["dedupe"]
    messages["probable_copy_of"] = flag_shifted_copies(messages, shifted["max_shift_hours"], shifted["min_body_chars"])
    messages["probable_copy"] = messages["probable_copy_of"].notna()
    funnel["probable_time_shifted_copies"] = int(messages["probable_copy"].sum())

    messages["authored"] = messages["body"].map(authored_text)
    messages["has_quoted"] = messages["body"].map(has_quoted_material)
    funnel["with_quoted_material"] = int(messages["has_quoted"].sum())
    funnel["with_authored_text"] = int((messages["authored"] != "").sum())

    senders_cfg = config["senders"]
    senders = sender_profiles(messages, senders_cfg["internal_domain"], senders_cfg["min_messages"],
                              senders_cfg["feed_share"], senders_cfg["top_templates"])
    messages["sender_automated"] = messages["sender"].isin(senders.index[senders["automated"]])
    messages["sender_internal"] = messages["sender"].fillna("").str.endswith("@" + senders_cfg["internal_domain"])
    funnel["senders"] = len(senders)
    funnel["senders_flagged"] = int(senders["automated"].sum())
    funnel["messages_from_flagged_senders"] = int(messages["sender_automated"].sum())
    messages["automated"] = automated_messages(messages, senders)
    funnel["automated_messages"] = int(messages["automated"].sum())
    messages["structured"] = messages["authored"].map(structured_record) & ~messages["automated"]
    funnel["structured_records"] = int(messages["structured"].sum())
    messages["routine"] = routine_messages(messages, senders_cfg["routine_repeats"]) & ~messages["automated"]
    messages["routine_excluded"] = messages["routine"] & ~messages["authored"].map(
        lambda t: speech_act(t, senders_cfg["speech_act_words"]))
    funnel["routine_messages"] = int(messages["routine"].sum())
    funnel["routine_messages_excluded_from_text"] = int(messages["routine_excluded"].sum())

    messages = messages.reset_index(drop=True)

    analysis = (messages["sender_internal"] & ~messages["automated"] & ~messages["structured"] & ~messages["probable_copy"]
                & ~messages["routine_excluded"] & (messages["authored"] != ""))
    messages["analysis"] = analysis
    funnel["analysis_messages"] = int(analysis.sum())
    funnel["analysis_senders"] = int(messages.loc[analysis, "sender"].nunique())

    out = paths["processed"]
    out.mkdir(parents=True, exist_ok=True)
    messages.drop(columns=["body"]).to_parquet(out / "messages.parquet", index=False)
    senders.rename_axis("sender").reset_index().to_parquet(out / "senders.parquet", index=False)
    copies.to_parquet(out / "copies.parquet", index=False)
    manifest = {
        "corpus": config["corpus"]["filename"],
        "corpus_sha256_verified": config["corpus"]["sha256"],
        "code_sha256": code_hash(),
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest(),
        "funnel": funnel,
        "outputs": {name: sha256_of(out / name) for name in ["messages.parquet", "senders.parquet", "copies.parquet"]},
    }
    (out / "funnel.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    manifest = prepare(load_config())
    width = max(map(len, manifest["funnel"]))
    for key, value in manifest["funnel"].items():
        print(f"{key:<{width}}  {value:>10,}")


if __name__ == "__main__":
    main()
