"""Phase 1 pipeline: raw archive -> cleaned, deduplicated, threaded messages.

Writes
  data/processed/messages.parquet   one row per kept message
  data/processed/senders.parquet    one row per sender with automation flags
  data/processed/copies.parquet     every discarded duplicate and the message kept for it
  data/processed/funnel.json        counts at every step + output checksums

Usage: uv run python -m enron_importance.prepare
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .clean import authored_text, has_quoted_material
from .config import load_config
from .dedupe import deduplicate, flag_shifted_copies, restrict_window
from .download import ensure_corpus, sha256_of
from .ingest import iter_archive, write_messages
from .senders import automated_messages, routine_messages, sender_profiles, speech_act, structured_record
from .threads import link_replies


def prepare(config: dict) -> dict:
    paths = config["paths"]
    raw_table = paths["interim"] / "messages_raw.parquet"
    if not raw_table.exists():
        write_messages(iter_archive(ensure_corpus(config)), raw_table)
    messages = pd.read_parquet(raw_table)
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
    messages = link_replies(messages, config["threads"]["max_reply_days"], ~messages["automated"] & ~messages["structured"])
    funnel["messages_linked_as_replies"] = int(messages["reply_to"].notna().sum())
    funnel["threads"] = int(messages["thread_id"].nunique())

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
        "corpus_sha256": config["corpus"]["sha256"],
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
