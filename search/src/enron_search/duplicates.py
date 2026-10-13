"""Near-duplicate messages from one sender that the exact deduplication kept.

The main pipeline removes copies with the same sender, timestamp, subject and
body, and flags time-shifted copies (same sender, subject, recipients and a
body over 100 characters, 1 to 8 whole hours apart). The Phase 3 labelling
pilot still found messages stored twice. This check looks for them by
meaning: pairs of person-text messages from the same sender person, sent
within `window_hours` of each other, whose authored texts both have at least
`min_chars` characters and whose embeddings have cosine similarity of at
least `min_similarity`. Similarity is computed exactly in PostgreSQL with
pgvector's distance operator over the (sender person, date) index; no
approximate index is involved.

Each pair records which of the exact rule's conditions it fails, which shows
why deduplication kept it:
  text differs              authored texts differ after collapsing whitespace
  subject differs           subjects differ without Re:/Fw: prefixes, ignoring case
  recipients differ         To and Cc address sets differ
  same time                 identical timestamps (separate sends to disjoint lists are kept on purpose)
  shift not whole hours     the time gap is not a whole number of hours
  shift over 8 hours        a whole-hour gap longer than the flagging rule's maximum
  matches on authored text  none of the above; the flagging rule compares sender addresses and full
                            bodies (quoted text included), so one person writing from two addresses,
                            or the same note above different quoted text, escapes it
Candidates are not confirmed duplicates: a sender can send the same text
twice on purpose. They are the frame for a labelled check.

Writes results/near_duplicates.csv (message paths, dates, similarity, reason;
no message text) and results/near_duplicates.json (counts).

Usage: uv run python -m enron_search.duplicates
"""

from __future__ import annotations

import json
import re

import pandas as pd
import psycopg

from .config import load_config
from .corpus import certified_sources, strip_prefixes
from .store import connect

PAIRS = """
SELECT a.id AS first, b.id AS second, 1 - (a.embedding <=> b.embedding) AS similarity
FROM messages a
JOIN messages b
  ON b.sender_person = a.sender_person
 AND b.sent_at >= a.sent_at
 AND b.sent_at <= a.sent_at + make_interval(hours => %(window)s)
 AND (b.sent_at > a.sent_at OR b.id > a.id)
WHERE length(a.body) >= %(min_chars)s
  AND length(b.body) >= %(min_chars)s
  AND a.embedding <=> b.embedding <= 1 - %(min_similarity)s
ORDER BY a.id, b.id
"""
_SPACE = re.compile(r"\s+")
MAX_SHIFT_HOURS = 8
SENT_FOLDERS = {"sent", "_sent_mail", "sent_items"}


def candidate_pairs(connection: psycopg.Connection, window_hours: int, min_chars: int,
                    min_similarity: float) -> pd.DataFrame:
    """(first, second, similarity) for every qualifying pair, first sent no later than second."""
    rows = connection.execute(PAIRS, {"window": window_hours, "min_chars": min_chars,
                                      "min_similarity": min_similarity}).fetchall()
    return pd.DataFrame(rows, columns=["first", "second", "similarity"])


def recipients(to, cc) -> frozenset[str]:
    return frozenset(address.strip().lower() for part in (to, cc) if part is not None for address in part)


def reason(first: dict, second: dict) -> str:
    """The first condition of the exact copy rule that this pair fails."""
    if _SPACE.sub(" ", first["authored"]).strip() != _SPACE.sub(" ", second["authored"]).strip():
        return "text differs"
    if strip_prefixes(first["subject"]).lower() != strip_prefixes(second["subject"]).lower():
        return "subject differs"
    if recipients(first["to"], first["cc"]) != recipients(second["to"], second["cc"]):
        return "recipients differ"
    seconds = (second["date"] - first["date"]).total_seconds()
    if seconds == 0:
        return "same time"
    if seconds % 3600:
        return "shift not whole hours"
    if seconds > MAX_SHIFT_HOURS * 3600:
        return "shift over 8 hours"
    return "matches on authored text"


def describe(pairs: pd.DataFrame, rows: pd.DataFrame) -> pd.DataFrame:
    """Add both messages' paths, dates and sender, the gap in hours and the reason the pair was kept."""
    records = rows.to_dict("records")
    out = []
    for first, second, similarity in pairs.itertuples(index=False):
        a, b = records[first], records[second]
        out.append({"first_path": a["path"], "second_path": b["path"], "sender_person": a["sender_person"],
                    "first_date": a["date"], "second_date": b["date"],
                    "gap_hours": round((b["date"] - a["date"]).total_seconds() / 3600, 4),
                    "similarity": round(float(similarity), 6), "reason": reason(a, b)})
    return pd.DataFrame(out, columns=["first_path", "second_path", "sender_person", "first_date", "second_date",
                                      "gap_hours", "similarity", "reason"])


def long_shifts(described: pd.DataFrame) -> dict:
    """Pairs identical on authored text, subject and recipients but shifted by more than 8 whole hours."""
    pairs = described[described["reason"] == "shift over 8 hours"]
    # Paths are maildir/<custodian>/<folder>/...
    first, second = pairs["first_path"].str.split("/"), pairs["second_path"].str.split("/")
    same = first.str[1] == second.str[1]
    sent = first.str[2].isin(SENT_FOLDERS) & second.str[2].isin(SENT_FOLDERS)
    gaps = pairs["gap_hours"].value_counts().sort_index()
    return {"pairs": len(pairs), "gap_hours": {f"{hours:g}": int(count) for hours, count in gaps.items()},
            "same_custodian": int(same.sum()), "same_custodian_two_sent_folders": int((same & sent).sum())}


def summary(described: pd.DataFrame, settings: dict) -> dict:
    messages = pd.concat([described["first_path"], described["second_path"]]).nunique()
    return {**settings, "pairs": len(described), "messages_in_pairs": int(messages),
            "senders": int(described["sender_person"].nunique()),
            "pairs_by_reason": described["reason"].value_counts().to_dict(),
            "pairs_at_similarity": {f">={t}": int((described["similarity"] >= t).sum())
                                    for t in (0.98, 0.99, 0.999)},
            "shift_over_8_hours": long_shifts(described)}


def main() -> None:
    config = load_config()
    settings = config["duplicates"]
    source, data = config["paths"]["source"], config["paths"]["data"]
    certified_sources(source)
    rows = pd.read_parquet(data / "rows.parquet")
    headers = pd.read_parquet(source / "messages.parquet", columns=["path", "to", "cc"])
    rows = rows.merge(headers, on="path", how="left", validate="one_to_one")
    with connect(config["database"]["dsn"]) as connection:
        count = connection.execute("SELECT count(*) FROM messages").fetchone()[0]
        if count != len(rows):
            raise SystemExit(f"the database has {count:,} messages but rows.parquet {len(rows):,}; rerun the store")
        pairs = candidate_pairs(connection, settings["window_hours"], settings["min_chars"],
                                settings["min_similarity"])
    described = describe(pairs, rows)
    results = config["paths"]["results"]
    results.mkdir(parents=True, exist_ok=True)
    described.to_csv(results / "near_duplicates.csv", index=False)
    report = summary(described, settings)
    (results / "near_duplicates.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
