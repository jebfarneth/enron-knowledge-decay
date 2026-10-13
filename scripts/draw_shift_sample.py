"""Draw a sample of time-shifted near-duplicate pairs and write a label sheet.

The search project's near-duplicate scan (search/results/near_duplicates.csv) found pairs of person-text
messages from one sender with identical authored text, subject and To and Cc that the time-shifted-copy
rule in `dedupe.py` (1 to 8 whole hours apart) leaves in the analysis. Three frames are sampled and mixed:
  long      a whole 9 to 17 hours apart (past the rule's maximum), stratified by the gap;
  near      within a minute of a whole number of hours (one copy's time has seconds, the other's does not);
  control   further than a minute from a whole number of hours, mostly minutes apart (likely sent twice).
Each sampled pair is shown with what can tell one message stored twice from two sends:
  - both messages' raw headers (Date, Message-ID, X-Folder, X-Origin, X-FileName) and one body;
  - every copy of each message (exact copies removed by deduplication included) with its folder and the
    mailbox export it came from (`X-FileName`, a Lotus Notes .nsf or an Outlook .pst), and whether one
    folder of one export holds both messages (folder names recur across a mailbox's exports);
  - other messages in the corpus that quote the text, with the quote header just above it, which often
    records the time the original was sent.
Writes data/labels/shifted_copies/pairs.jsonl (the sheet) and sample.json (seed, frames, strata, and each
item's frame and paths).
Usage: uv run python scripts/draw_shift_sample.py
"""

from __future__ import annotations

import email
import json
import re
import tarfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from enron_importance.config import load_config
from enron_importance.dedupe import normalize_subject

SEED = 20261013
ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "search" / "results" / "near_duplicates.csv"
OUT = ROOT / "data" / "labels" / "shifted_copies"
# Long-shift pairs drawn per gap in hours (all of a stratum when it is smaller).
STRATA = {9: 5, 10: 15, 11: 8, 12: 8, 13: 4, 14: 6, 17: 4}
NEAR, CONTROL = 15, 10
TOLERANCE = 60         # seconds from a whole number of hours
HEADERS = ["Message-ID", "Date", "From", "To", "Cc", "Subject", "X-From", "X-To", "X-cc", "X-Folder", "X-Origin",
           "X-FileName"]
BODY_CHARS = 1500
SNIPPET_CHARS = 60     # authored text searched for in other messages
QUOTE_LINES = 10       # lines shown above a quoted occurrence
MAX_QUOTING = 4
_SPACE = re.compile(r"\s+")


def raw_headers(archive: Path, paths: set[str]) -> dict[str, dict]:
    """Selected raw headers of the given archive members, in one pass over the archive."""
    found = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar:
            if member.name in paths:
                parsed = email.message_from_bytes(tar.extractfile(member).read())
                found[member.name] = {name: parsed.get(name) for name in HEADERS}
                if len(found) == len(paths):
                    break
    return found


def quoting(snippet: str, own: set[str], candidates: pd.DataFrame) -> list[dict]:
    """Messages outside `own` whose body contains the snippet, with the lines just above it."""
    out = []
    for path, sender, date, body in candidates.itertuples(index=False):
        if path in own or not isinstance(body, str):
            continue
        flat = _SPACE.sub(" ", body)
        at = flat.find(snippet)
        if at < 0:
            continue
        # Map back to the original lines: take the lines before the first line containing the snippet's start.
        lines = body.splitlines()
        head = snippet[:25]
        line = next((i for i, text in enumerate(lines) if head in _SPACE.sub(" ", text)), None)
        above = lines[max(0, line - QUOTE_LINES):line] if line is not None else []
        out.append({"path": path, "sender": sender, "date": str(date),
                    "lines_above_quote": [text.rstrip() for text in above if text.strip()]})
        if len(out) == MAX_QUOTING:
            break
    return out


def main() -> None:
    config = load_config()
    processed, interim = config["paths"]["processed"], config["paths"]["interim"]
    pairs = pd.read_csv(FRAME)
    seconds = (pairs["gap_hours"] * 3600).round()
    hours = (seconds / 3600).round()
    near_whole = ((seconds - hours * 3600).abs() < TOLERANCE) & (hours >= 1)
    unwhole = pairs["reason"] == "shift not whole hours"
    frames = {"long": pairs[pairs["reason"] == "shift over 8 hours"], "near": pairs[unwhole & near_whole],
              "control": pairs[unwhole & ~near_whole]}
    sizes = frames["long"]["gap_hours"].value_counts().sort_index()
    if set(sizes.index.astype(int)) != set(STRATA):
        raise SystemExit(f"gaps in the frame {sorted(sizes.index)} differ from the strata {sorted(STRATA)}")
    sample = pd.concat([frames["long"][frames["long"]["gap_hours"] == gap].sample(min(n, int(sizes[gap])),
                                                                                   random_state=SEED)
                        for gap, n in STRATA.items()]).assign(frame="long")
    sample = pd.concat([sample, frames["near"].sample(NEAR, random_state=SEED).assign(frame="near"),
                        frames["control"].sample(CONTROL, random_state=SEED).assign(frame="control")])
    sample = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)

    messages = pd.read_parquet(processed / "messages.parquet",
                               columns=["path", "custodian", "folder", "date", "sender", "subject", "authored"])
    by_path = messages.set_index("path")
    copies = pd.read_parquet(processed / "copies.parquet")
    removed_copies = copies.groupby("kept_path")["path"].apply(list)

    def all_copies(path: str) -> list[str]:
        return [path] + removed_copies.get(path, [])

    pair_paths = {p for a, b in zip(sample["first_path"], sample["second_path"]) for p in all_copies(a) + all_copies(b)}
    headers = raw_headers(config["paths"]["raw"] / "enron_mail_20150507.tar.gz", pair_paths)

    # Messages that may quote a sampled pair: kept messages with the same normalized subject.
    subjects = {normalize_subject(by_path.loc[p, "subject"]) for p in sample["first_path"]}
    subject_of = messages["subject"].map(normalize_subject)
    related = messages.loc[subject_of.isin(subjects), ["path", "sender", "date"]].assign(subject=subject_of)
    bodies = pq.read_table(interim / "messages_raw.parquet", columns=["path", "body"],
                           filters=[("path", "in", list(set(related["path"]) | set(sample["first_path"])))]
                           ).to_pandas().set_index("path")["body"]
    related = related.assign(body=related["path"].map(bodies))
    by_subject = defaultdict(list)
    for row in related.itertuples(index=False):
        by_subject[row.subject].append((row.path, row.sender, row.date, row.body))

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "pairs.jsonl", "w") as sheet:
        for i, row in sample.iterrows():
            item = f"S{i + 1:03d}"
            first, second = all_copies(row["first_path"]), all_copies(row["second_path"])
            def located(paths):
                return [{"path": p, "export": (headers.get(p) or {}).get("X-FileName"),
                         "folder": (headers.get(p) or {}).get("X-Folder")} for p in paths]

            def places(paths):
                return {(p.rsplit("/", 1)[0], (headers.get(p) or {}).get("X-FileName")) for p in paths}
            authored = _SPACE.sub(" ", by_path.loc[row["first_path"], "authored"]).strip()
            snippet = authored[:SNIPPET_CHARS]
            candidates = pd.DataFrame(by_subject[normalize_subject(by_path.loc[row["first_path"], "subject"])],
                                      columns=["path", "sender", "date", "body"])
            sheet.write(json.dumps({
                "item": item,
                "earlier": {"path": row["first_path"], "date_utc": row["first_date"],
                            "raw_headers": headers.get(row["first_path"]), "copies": located(first)},
                "later": {"path": row["second_path"], "date_utc": row["second_date"],
                          "raw_headers": headers.get(row["second_path"]), "copies": located(second)},
                "gap_hours": row["gap_hours"],
                "export_folders_holding_both": sorted(f"{folder} ({export})" for folder, export
                                                      in places(first) & places(second)),
                "body": (bodies.get(row["first_path"]) or "")[:BODY_CHARS],
                "quoted_in": quoting(snippet, set(first) | set(second), candidates),
            }, default=str) + "\n")
    long = sample[sample["frame"] == "long"]
    meta = {"seed": SEED, "source": "search/results/near_duplicates.csv", "tolerance_seconds": TOLERANCE,
            "frame_pairs": {name: len(rows) for name, rows in frames.items()},
            "sample_pairs": sample["frame"].value_counts().to_dict(),
            "long_frame_pairs_by_gap": {f"{g:g}": int(n) for g, n in sizes.items()},
            "long_sample_pairs_by_gap": {f"{g:g}": int(n) for g, n in long["gap_hours"].value_counts().sort_index().items()},
            "items": {f"S{i + 1:03d}": {"frame": f, "first_path": a, "second_path": b, "gap_hours": g}
                      for i, (f, a, b, g) in enumerate(zip(sample["frame"], sample["first_path"], sample["second_path"],
                                                           sample["gap_hours"]))}}
    (OUT / "sample.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: v for k, v in meta.items() if k != "items"}, indent=2))


if __name__ == "__main__":
    main()
