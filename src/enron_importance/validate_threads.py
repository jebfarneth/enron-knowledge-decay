"""Re-check reply links against the audit's labelled sample.

The 2026-09-25 audit drew 60 links at random from the earlier linking rule
and labelled each (audits/labels/thread_links_sample60.json): 27 supported
direct replies, and 33 forwards, wrong parents, unrelated broadcasts, updates
or uncertain cases. This reports what the current rule does with each: keeps
the same parent, links another parent, or leaves the message unlinked.

The sample was drawn from the old rule's links, so it measures how the new
rule treats those links (precision among them, and direct replies lost). It
cannot measure replies that neither rule links. Labels were made by an AI
auditor, not by people.

Usage: uv run python -m enron_importance.validate_threads
"""

from __future__ import annotations

import json

import pandas as pd

from .config import ROOT, load_config
from .provenance import record_stage

LABELS = ROOT / "audits" / "labels" / "thread_links_sample60.json"


def outcomes(labels: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """`links` needs path, parent_path, link_evidence and link_kind (links.parquet)."""
    current = links.rename(columns={"parent_path": "new_parent"})[["path", "new_parent", "link_evidence", "link_kind"]]
    table = labels.merge(current, on="path", how="left")
    table["outcome"] = [
        "unlinked" if not isinstance(new, str) else "same parent" if new == old else "other parent"
        for new, old in zip(table["new_parent"], table["parent_path"])
    ]
    return table


def main() -> None:
    config = load_config()
    labels = pd.DataFrame(json.loads(LABELS.read_text())["labels"])
    table = outcomes(labels, pd.read_parquet(config["paths"]["processed"] / "links.parquet"))
    direct = table["classification"] == "direct_reply"
    kept = table["outcome"] == "same parent"
    shown = table["outcome"].where(~kept, "same parent (" + table["link_kind"].fillna("") + ")")
    counts = table.assign(outcome=shown).groupby(["classification", "outcome"]).size().unstack(fill_value=0)
    replies = kept & (table["link_kind"] == "reply")
    summary = {
        "labelled_links": len(table),
        "old_rule_supported_direct_replies": int(direct.sum()),
        "direct_replies_still_linked_to_same_parent": int((direct & kept).sum()),
        "links_kept_same_parent": int(kept.sum()),
        "share_of_kept_links_that_are_direct_replies": round(float((direct & kept).sum() / max(kept.sum(), 1)), 4),
        "links_kept_as_reply_kind": int(replies.sum()),
        "direct_replies_kept_as_reply_kind": int((direct & replies).sum()),
        "share_of_reply_kind_links_that_are_direct_replies": round(float((direct & replies).sum() / max(replies.sum(), 1)), 4),
        "outcomes_by_label": {label: row.to_dict() for label, row in counts.iterrows()},
    }
    out = config["paths"]["results"] / "thread_link_check.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(counts.to_string())
    print(json.dumps({k: v for k, v in summary.items() if k != "outcomes_by_label"}, indent=2))
    record_stage(config, "threadcheck")


if __name__ == "__main__":
    main()
