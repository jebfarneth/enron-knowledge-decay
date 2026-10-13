"""Score the time-shifted copy labels and check every candidate pair without labels.

Reads data/labels/shifted_copies/labels.jsonl and sample.json (see draw_shift_sample.py). For each frame,
the share of labelled pairs that are one message stored twice, with a Wilson 95% interval; for the long
frame also by gap and weighted by each gap's share of the frame. Items labelled cannot_tell are left out
of the denominators.

Three checks cover every pair in the frames, not only the sample:
  exports    pairs where one folder of one mailbox export holds both messages (two sends would usually
             leave both in the sender's sent folder and in each recipient's inbox; folder names recur
             across a mailbox's Lotus Notes and Outlook exports, so the export file is part of the
             folder), and pairs whose earlier message's copies all come from Notes (.nsf) exports and
             later message's from Outlook (.pst) exports;
  clocks     the gap by whether the earlier message was sent in US daylight time (a shift caused by a
             time-zone offset changes with the clocks; two sends do not);
  chance     how many pairs two sends would put this close to a whole number of hours by chance, from
             the control pairs' gaps (a resend is as likely to land on any second of the hour).

Writes data/labels/shifted_copies/scores.json. Usage: uv run python scripts/score_shift_labels.py
"""

from __future__ import annotations

import email
import json
import math
import tarfile
from collections import Counter
from pathlib import Path

import pandas as pd

from enron_importance.config import load_config

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "labels" / "shifted_copies"
FRAME = ROOT / "search" / "results" / "near_duplicates.csv"
MAX_HOURS = 17


def wilson(k: int, n: int, z: float = 1.96) -> dict:
    if n == 0:
        return {"k": k, "n": n, "rate": None, "low": None, "high": None}
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": k, "n": n, "rate": p, "low": max(0.0, centre - half), "high": min(1.0, centre + half)}


def export_files(archive: Path, paths: set[str]) -> dict[str, str]:
    """X-FileName of the given archive members (the mailbox export each came from), in one pass."""
    found = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar:
            if member.name in paths:
                found[member.name] = email.message_from_bytes(tar.extractfile(member).read()).get("X-FileName") or ""
                if len(found) == len(paths):
                    break
    return found


def frames(pairs: pd.DataFrame, tolerance: int) -> dict[str, pd.DataFrame]:
    seconds = (pairs["gap_hours"] * 3600).round()
    hours = (seconds / 3600).round()
    near_whole = ((seconds - hours * 3600).abs() < tolerance) & (hours >= 1)
    unwhole = pairs["reason"] == "shift not whole hours"
    return {"long": pairs[pairs["reason"] == "shift over 8 hours"], "near": pairs[unwhole & near_whole],
            "control": pairs[unwhole & ~near_whole]}


def main() -> None:
    meta = json.loads((LABELS / "sample.json").read_text())
    with open(LABELS / "labels.jsonl") as handle:
        labels = {row["item"]: row for row in map(json.loads, handle)}
    if set(labels) != set(meta["items"]):
        raise SystemExit("labels.jsonl does not cover exactly the sampled items")

    out: dict = {"labels": {}, "checks": {}}
    for frame in ("long", "near", "control"):
        items = [(item, info) for item, info in meta["items"].items() if info["frame"] == frame]
        known = [labels[item] for item, _ in items if labels[item]["verdict"] != "cannot_tell"]
        out["labels"][frame] = {
            "one_message": wilson(sum(l["verdict"] == "one_message" for l in known), len(known)),
            "verdict": dict(Counter(labels[item]["verdict"] for item, _ in items)),
            "time_supported": dict(Counter(labels[item]["time_supported"] for item, _ in items)),
        }
    by_gap, weighted = {}, 0.0
    total = sum(meta["long_frame_pairs_by_gap"].values())
    for gap, size in meta["long_frame_pairs_by_gap"].items():
        known = [labels[item] for item, info in meta["items"].items()
                 if info["frame"] == "long" and f"{info['gap_hours']:g}" == gap and labels[item]["verdict"] != "cannot_tell"]
        share = sum(l["verdict"] == "one_message" for l in known) / len(known) if known else 0.0
        by_gap[gap] = {"frame_pairs": size, **wilson(sum(l["verdict"] == "one_message" for l in known), len(known))}
        weighted += size / total * share
    out["labels"]["long"]["by_gap"] = by_gap
    out["labels"]["long"]["one_message_weighted"] = weighted

    config = load_config()
    copies = pd.read_parquet(config["paths"]["processed"] / "copies.parquet")
    removed = copies.groupby("kept_path")["path"].apply(list)

    pairs = pd.read_csv(FRAME)

    def copies_of(path: str) -> list[str]:
        return [path] + removed.get(path, [])

    paths = {p for a, b in zip(pairs["first_path"], pairs["second_path"]) for p in copies_of(a) + copies_of(b)}
    exports = export_files(config["paths"]["raw"] / "enron_mail_20150507.tar.gz", paths)

    def places(path: str) -> set[tuple[str, str]]:
        return {(p.rsplit("/", 1)[0], exports.get(p, "")) for p in copies_of(path)}

    def all_end(path: str, suffix: str) -> bool:
        return all(exports.get(p, "").lower().endswith(suffix) for p in copies_of(path))

    for name, rows in frames(pairs, meta["tolerance_seconds"]).items():
        both = sum(bool(places(a) & places(b)) for a, b in zip(rows["first_path"], rows["second_path"]))
        notes_then_outlook = sum(all_end(a, ".nsf") and all_end(b, ".pst")
                                 for a, b in zip(rows["first_path"], rows["second_path"]))
        dates = pd.to_datetime(rows["first_date"]).dt.tz_convert("America/Chicago")
        daylight = dates.map(lambda d: bool(d.dst()))
        hours = rows["gap_hours"].round().astype(int)
        out["checks"][name] = {
            "pairs": len(rows), "pairs_with_one_export_folder_holding_both": int(both),
            "pairs_earlier_only_in_notes_later_only_in_outlook": int(notes_then_outlook),
            "pairs_by_gap_and_clock": {f"{h}": {"daylight": int(((hours == h) & daylight).sum()),
                                               "standard": int(((hours == h) & ~daylight).sum())}
                                       for h in sorted(hours.unique())},
        }
    # Control pairs 1 to MAX_HOURS hours apart show how often two sends fall in that range; a send lands
    # within the tolerance of a whole hour with probability 2 * tolerance / 3600, and exactly on one
    # (both times on whole minutes, as in the long frame) with probability 1 / 60.
    control = frames(pairs, meta["tolerance_seconds"])["control"]
    in_range = int(control["gap_hours"].between(1, MAX_HOURS + 1).sum())
    near_share = 2 * meta["tolerance_seconds"] / 3600
    out["checks"]["chance"] = {
        "control_pairs_1_to_max_hours": in_range,
        "expected_two_send_pairs_near_whole_hours": in_range * near_share / (1 - near_share),
        "expected_two_send_pairs_on_whole_hours": in_range * (1 / 60) / (1 - 1 / 60),
        "observed_long_and_near_pairs": int(sum(len(f) for n, f in frames(pairs, meta["tolerance_seconds"]).items()
                                                if n != "control")),
    }
    (LABELS / "scores.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
