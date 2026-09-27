"""Draw the Phase 3 pilot label samples and write blinded label sheets.

Three tasks, each a JSONL sheet of items that hide the pipeline's decision:
  mentions.jsonl   150 name mentions: does the name refer to the person it was resolved to, and what kind of
                   text is it in? 100 from the main measures, 50 from the filtered-out rows (office, company,
                   abbreviation, self, non-person sender), mixed together.
  replies.jsonl    180 messages with the earlier same-subject messages as candidates: which candidate, if any,
                   is the immediate parent? 40 each of high-, medium- and low-confidence reply links and 60
                   unlinked replies that have at least one earlier same-subject message (for missed links), mixed
                   together; the pipeline's parent is always a candidate.
  exclusions.jsonl 150 messages: what kind of text is it? 50 excluded only as signature-only, 40 excluded only as
                   structured records or newsletters (internal person senders), 60 kept person-text messages.
data/processed/phase3_pilot_key_private.json maps every item to its frame and the pipeline's decision;
labellers must not open it.

Reads the certified run in data/processed and data/interim; writes data/labels/phase3_pilot/.
Usage: uv run python scripts/draw_label_samples.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from enron_importance.config import load_config
from enron_importance.dedupe import normalize_subject

SEED = 20260927
OUT = Path(__file__).resolve().parents[1] / "data" / "labels" / "phase3_pilot"
CONTEXT = 300          # characters of text on each side of a mention
CHILD_CHARS = 5000     # characters of a reply's full body shown
CANDIDATE_CHARS = 700  # characters of each candidate's authored text shown
MAX_CANDIDATES = 8
WINDOW = pd.Timedelta(days=14)


def names(values) -> str:
    return ", ".join(str(v) for v in values) if values is not None and len(values) else ""


def main() -> None:
    config = load_config()
    processed, interim = config["paths"]["processed"], config["paths"]["interim"]
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    columns = ["path", "sender", "x_from", "to", "cc", "subject", "date", "authored", "automated", "structured",
               "signature_only", "routine_excluded", "probable_copy", "sender_internal", "analysis", "has_quoted"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=columns)
    messages = messages.merge(pd.read_parquet(processed / "sender_people.parquet"), on="path", how="left")
    types = pd.read_parquet(processed / "person_types.parquet").set_index("person_key")["entity_type"]
    messages["sender_type"] = messages["sender_person"].map(types)
    by_path = messages.set_index("path")
    identities = pd.read_parquet(processed / "identities.parquet")
    addresses = identities.dropna(subset=["person_key"]).groupby("person_key")["address"].apply(list)
    key: dict[str, dict] = {}

    def header(path: str) -> dict:
        row = by_path.loc[path]
        return {"from": row["x_from"] if isinstance(row["x_from"], str) and row["x_from"] else row["sender"],
                "from_address": row["sender"], "to": names(row["to"]), "cc": names(row["cc"]),
                "date": str(row["date"]), "subject": row["subject"]}

    # 1. Mentions.
    mentions = pd.read_parquet(processed / "mentions.parquet")
    main_rows = mentions[mentions["excluded"].isna() & (mentions["recipient"] != mentions["person"])]
    picks = [main_rows.sample(100, random_state=SEED).assign(frame="main")]
    for reason, n in [("office", 15), ("company", 10), ("abbreviation", 10), ("self", 10), ("not_person_text", 5)]:
        rows = mentions[mentions["excluded"] == reason]
        picks.append(rows.sample(min(n, len(rows)), random_state=SEED).assign(frame=f"excluded_{reason}"))
    sample = pd.concat(picks).sample(frac=1, random_state=SEED).reset_index(drop=True)
    with open(OUT / "mentions.jsonl", "w") as sheet:
        for i, row in sample.iterrows():
            item = f"M{i + 1:03d}"
            text = by_path.loc[row["path"], "authored"] or ""
            at = text.find(row["mention"])
            context = (text[max(0, at - CONTEXT):at] + "[[" + row["mention"] + "]]"
                       + text[at + len(row["mention"]):at + len(row["mention"]) + CONTEXT]) if at >= 0 else text[:2 * CONTEXT]
            sheet.write(json.dumps({
                "item": item, "message": header(row["path"]), "recipient_considered": row["recipient"],
                "mention": row["mention"], "context": context,
                "resolved_person": row["person"], "resolved_person_addresses": list(addresses.get(row["person"], []))[:4],
            }) + "\n")
            key[item] = {"task": "mentions", "frame": row["frame"], "path": row["path"], "excluded": row["excluded"]}

    # 2. Replies: every child gets the earlier same-subject messages within 14 days as candidates.
    links = pd.read_parquet(processed / "links.parquet")
    links = links.merge(messages[["path", "subject", "automated", "structured", "probable_copy", "has_quoted",
                                  "sender_person"]], on="path")
    replies = links[links["link_kind"] == "reply"]
    eligible_unlinked = links[links["parent_path"].isna() & ~links["automated"] & ~links["structured"]
                              & ~links["probable_copy"] & links["has_quoted"] & links["sender_person"].notna()
                              & links["subject"].fillna("").str.match(r"(?i)\s*re\s*:")]
    usable = messages[~messages["probable_copy"]]
    threads: dict[str, list[tuple]] = defaultdict(list)
    for path, subject, date in zip(usable["path"], usable["subject"], usable["date"]):
        normalized = normalize_subject(subject)
        if normalized:
            threads[normalized].append((date, path))

    def earlier_messages(path, subject):
        date = by_path.loc[path, "date"]
        return sorted(((d, p) for d, p in threads[normalize_subject(subject)] if p != path and date - WINDOW <= d < date),
                      reverse=True)

    # An unlinked reply can only be a missed link if an earlier same-subject message exists in the corpus.
    has_candidate = pd.Series([bool(earlier_messages(p, s)) for p, s in zip(eligible_unlinked["path"], eligible_unlinked["subject"])],
                              index=eligible_unlinked.index)
    children = [replies[replies["link_confidence"] == level].sample(40, random_state=SEED).assign(frame=f"reply_{level}")
                for level in ("high", "medium", "low")]
    children.append(eligible_unlinked[has_candidate].sample(60, random_state=SEED).assign(frame="unlinked"))
    children = pd.concat(children).sample(frac=1, random_state=SEED).reset_index(drop=True)

    earlier_by_child = {p: earlier_messages(p, s) for p, s in zip(children["path"], children["subject"])}
    bodies_needed = set(children["path"]) | {p for found in earlier_by_child.values() for _, p in found[:MAX_CANDIDATES]} \
        | set(children["parent_path"].dropna())
    body = pq.read_table(interim / "messages_raw.parquet", columns=["path", "body"],
                         filters=[("path", "in", list(bodies_needed))]).to_pandas().set_index("path")["body"]
    with open(OUT / "replies.jsonl", "w") as sheet:
        for i, row in children.iterrows():
            item = f"R{i + 1:03d}"
            earlier = earlier_by_child[row["path"]]
            chosen = [p for _, p in earlier[:MAX_CANDIDATES]]
            parent = row["parent_path"] if isinstance(row["parent_path"], str) else None
            if parent and parent not in chosen:
                chosen = chosen[:MAX_CANDIDATES - 1] + [parent]
            chosen = sorted(chosen, key=lambda p: by_path.loc[p, "date"], reverse=True)
            # A forward-only message has no authored text: show the start of its full body instead.
            candidates = [{"id": f"C{j + 1}", **header(p),
                           "text": ((by_path.loc[p, "authored"] or "") or (body.get(p, "") or ""))[:CANDIDATE_CHARS]}
                          for j, p in enumerate(chosen)]
            text = body.get(row["path"], "") or ""
            sheet.write(json.dumps({
                "item": item, "message": header(row["path"]), "full_body": text[:CHILD_CHARS],
                "body_truncated": len(text) > CHILD_CHARS, "candidates": candidates,
                "more_earlier_candidates_not_shown": max(0, len(earlier) - MAX_CANDIDATES),
            }) + "\n")
            key[item] = {"task": "replies", "frame": row["frame"], "path": row["path"],
                         "pipeline_parent": next((c["id"] for c, p in zip(candidates, chosen) if p == parent), None),
                         "pipeline_kind": row["link_kind"], "candidate_paths": chosen}

    # 3. Exclusions: marginal internal-person exclusions and kept person-text controls.
    otherwise = (messages["sender_internal"] & ~messages["automated"] & ~messages["probable_copy"]
                 & ~messages["routine_excluded"] & (messages["authored"] != "") & (messages["sender_type"] == "person"))
    frames = [
        messages[otherwise & messages["signature_only"] & ~messages["structured"]].sample(50, random_state=SEED).assign(frame="signature_only"),
        messages[otherwise & messages["structured"] & ~messages["signature_only"]].sample(40, random_state=SEED).assign(frame="structured"),
        messages[messages["analysis"] & messages["person_text"].fillna(False)].sample(60, random_state=SEED).assign(frame="kept"),
    ]
    sample = pd.concat(frames).sample(frac=1, random_state=SEED).reset_index(drop=True)
    with open(OUT / "exclusions.jsonl", "w") as sheet:
        for i, row in sample.iterrows():
            item = f"X{i + 1:03d}"
            sheet.write(json.dumps({"item": item, "message": header(row["path"]),
                                    "authored_text": (row["authored"] or "")[:3000]}) + "\n")
            key[item] = {"task": "exclusions", "frame": row["frame"], "path": row["path"]}

    population = {
        "mentions_main": len(main_rows), **{f"mentions_excluded_{r}": int((mentions["excluded"] == r).sum())
                                             for r in ["office", "company", "abbreviation", "self", "not_person_text"]},
        **{f"replies_{level}": int((replies["link_confidence"] == level).sum()) for level in ("high", "medium", "low")},
        "replies_unlinked_eligible": len(eligible_unlinked),
        "replies_unlinked_with_candidates": int(has_candidate.sum()),
        "exclusions_signature_only": int((otherwise & messages["signature_only"] & ~messages["structured"]).sum()),
        "exclusions_structured": int((otherwise & messages["structured"] & ~messages["signature_only"]).sum()),
        "kept_person_text": int((messages["analysis"] & messages["person_text"].fillna(False)).sum()),
    }
    # The key goes to data/processed, which labellers are told not to read.
    (processed / "phase3_pilot_key_private.json").write_text(json.dumps({"seed": SEED, "population": population, "items": key}, indent=1))
    counts = pd.Series([v["task"] for v in key.values()]).value_counts().to_dict()
    print(json.dumps({"items": counts, "population": population}, indent=2))


if __name__ == "__main__":
    main()
