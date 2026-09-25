"""Phase 1 pipeline: raw archive -> cleaned, deduplicated, threaded messages.

Writes
  data/processed/messages.parquet   one row per kept message
  data/processed/senders.parquet    one row per sender with automation flags
  data/processed/funnel.json        counts at every step + output checksums

Usage: uv run python -m enron_importance.prepare
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .clean import authored_text, has_quoted_material
from .config import load_config
from .dedupe import deduplicate, restrict_window
from .download import ensure_corpus, sha256_of
from .ingest import iter_archive, write_messages
from .senders import routine_messages, sender_profiles
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

    messages, removed = deduplicate(messages)
    funnel.update({f"dropped_{key}": value for key, value in removed.items()})
    funnel["unique_messages"] = len(messages)

    messages["authored"] = messages["body"].map(authored_text)
    messages["has_quoted"] = messages["body"].map(has_quoted_material)
    funnel["with_quoted_material"] = int(messages["has_quoted"].sum())
    funnel["with_authored_text"] = int((messages["authored"] != "").sum())

    senders_cfg = config["senders"]
    senders = sender_profiles(messages, senders_cfg["internal_domain"], senders_cfg["min_messages"],
                              senders_cfg["feed_share"], senders_cfg["top_templates"])
    automated = set(senders.index[senders["automated"]])
    messages["sender_automated"] = messages["sender"].isin(automated)
    messages["sender_internal"] = messages["sender"].fillna("").str.endswith("@" + senders_cfg["internal_domain"])
    funnel["senders"] = len(senders)
    funnel["senders_automated"] = int(senders["automated"].sum())
    funnel["messages_from_automated_senders"] = int(messages["sender_automated"].sum())
    messages["routine"] = routine_messages(messages, senders_cfg["routine_repeats"]) & ~messages["sender_automated"]
    funnel["routine_messages_from_people"] = int(messages["routine"].sum())

    messages = link_replies(messages.reset_index(drop=True), config["threads"]["max_reply_days"])
    funnel["messages_linked_as_replies"] = int(messages["reply_to"].notna().sum())
    funnel["threads"] = int(messages["thread_id"].nunique())

    analysis = (messages["sender_internal"] & ~messages["sender_automated"] & ~messages["routine"]
                & (messages["authored"] != ""))
    funnel["analysis_messages"] = int(analysis.sum())
    funnel["analysis_senders"] = int(messages.loc[analysis, "sender"].nunique())

    out = paths["processed"]
    out.mkdir(parents=True, exist_ok=True)
    messages.drop(columns=["body"]).to_parquet(out / "messages.parquet", index=False)
    senders.rename_axis("sender").reset_index().to_parquet(out / "senders.parquet", index=False)
    manifest = {
        "corpus": config["corpus"]["filename"],
        "corpus_sha256": config["corpus"]["sha256"],
        "funnel": funnel,
        "outputs": {name: sha256_of(out / name) for name in ["messages.parquet", "senders.parquet"]},
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
