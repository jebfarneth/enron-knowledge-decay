"""A labelled check of the detected absences.

The check runs in rounds. `draw` takes round n's seeded random sample of kept
notices, leaving out every notice already read: those read while the rules
were written (labels/dev_inspected_paths.txt) and those of earlier rounds
(labels/check_round<k>_paths.txt), since rules revised after a round has
been read must be checked on notices nobody has seen. It writes a blind sheet
(send date, subject and authored text only) and a separate key with the
detector's windows to data/labels/round<n>/. Labellers follow
labels/absence_guidelines.md and see only the sheet.

`score` compares round n's labels with its key and writes
results/absence_check_round<n>.json (counts and 95% Wilson intervals, no
message text). A notice is correct when the label says the sender is away
and the windows agree, scored two ways: calendar days (first day and day
back each within one day; the primary score of rounds 1 and 2, fixed before
they were labelled) and working days (first and last working day away each
within one working day; the primary score from round 3, fixed before round 3
was drawn, because the analysis counts working days and the calendar score
counts a Friday absence "back Saturday" against "back Monday" as an error).
Round 3 is the last round: its primary score is the detector's reported
accuracy, and the rules do not change after it.

Usage:
  uv run python -m enron_functional.absence_check draw
  uv run python -m enron_functional.absence_check score
  uv run python -m enron_functional.absence_check human
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import date

import pandas as pd

from .absences import LOCAL_TIME
from .config import ROOT, load_config
from .workdays import working_days, working_days_apart

DEV_INSPECTED = ROOT / "labels" / "dev_inspected_paths.txt"


def wilson(successes: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(centre - half, 4), round(centre + half, 4)]


def round_settings(config: dict) -> tuple[int, int, dict]:
    settings = config["absence_check"]
    number = settings["round"]
    return number, settings["seeds"][number], settings


def already_read(number: int) -> set[str]:
    """Paths read before round `number`: while writing the rules and in earlier rounds."""
    seen = set(DEV_INSPECTED.read_text().split())
    for earlier in range(1, number):
        seen |= set((ROOT / "labels" / f"check_round{earlier}_paths.txt").read_text().split())
    return seen


def draw(config: dict) -> None:
    number, seed, settings = round_settings(config)
    data = config["paths"]["data"]
    notices = pd.read_parquet(data / "absence_notices.parquet")
    messages = pd.read_parquet(config["paths"]["source"] / "messages.parquet", columns=["path", "subject", "authored"])
    seen = already_read(number)
    pool = notices[(notices["status"] == "kept") & ~notices["path"].isin(seen)]
    sample = pool.sample(settings["sample_size"], random_state=seed).merge(messages, on="path")
    sample = sample.sample(frac=1, random_state=seed).reset_index(drop=True)
    items, key = [], []
    for item_id, row in enumerate(sample.itertuples(index=False), start=1):
        sent = row.date.tz_convert(LOCAL_TIME)
        items.append({"id": item_id, "sent": f"{sent:%A, %B %-d, %Y, %-I:%M %p}", "subject": row.subject,
                      "text": row.authored})
        key.append({"id": item_id, "path": row.path, "kind": row.kind, "first_day": f"{row.start:%Y-%m-%d}",
                    "day_back": f"{row.back:%Y-%m-%d}"})
    out = data / "labels" / f"round{number}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "items.json").write_text(json.dumps(items, indent=2) + "\n")
    (out / "key.json").write_text(json.dumps(key, indent=2) + "\n")
    (ROOT / "labels" / f"check_round{number}_paths.txt").write_text("\n".join(sorted(k["path"] for k in key)) + "\n")
    print(f"round {number}: drew {len(items)} of {len(pool):,} kept notices (seed {seed}); "
          f"{len(seen)} already read were left out")


def human_ids(settings: dict) -> list[int]:
    """The items of round 1's sheet a person labels too, to measure agreement with the AI labeller."""
    return sorted(random.Random(settings["seeds"][1]).sample(range(1, settings["sample_size"] + 1),
                                                             settings["human_subset_size"]))


def within(label: str, detected: str, days: int) -> bool:
    try:
        return abs((date.fromisoformat(label) - date.fromisoformat(detected)).days) <= days
    except ValueError:
        return False


def same_working_days(label: dict, key: dict, tolerance: int = 1) -> bool:
    """Whether the labelled and detected windows cover the same working days, give or take `tolerance` at each end."""
    try:
        labelled = working_days(date.fromisoformat(label["first_day"]), date.fromisoformat(label["day_back"]))
    except ValueError:
        return False
    detected = working_days(date.fromisoformat(key["first_day"]), date.fromisoformat(key["day_back"]))
    if not labelled or not detected:
        return False
    return (working_days_apart(labelled[0], detected[0]) <= tolerance
            and working_days_apart(labelled[-1], detected[-1]) <= tolerance)


def score(config: dict) -> None:
    number, _, settings = round_settings(config)
    primary = settings["primary_score"][number]
    folder, results = config["paths"]["data"] / "labels" / f"round{number}", config["paths"]["results"]
    key = {k["id"]: k for k in json.loads((folder / "key.json").read_text())}
    labels = {int(k): v for k, v in json.loads((folder / "labels.json").read_text()).items()}
    if set(labels) != set(key):
        raise SystemExit(f"labels cover {len(labels)} of {len(key)} items")
    rows = []
    for item_id, label in labels.items():
        k = key[item_id]
        absent = label["absent"]
        rows.append({"kind": k["kind"], "absent": absent,
                     "correct": absent == "yes" and within(label["first_day"], k["first_day"], 1)
                     and within(label["day_back"], k["day_back"], 1),
                     "exact": absent == "yes" and within(label["first_day"], k["first_day"], 0)
                     and within(label["day_back"], k["day_back"], 0),
                     "working": absent == "yes" and same_working_days(label, k),
                     "first_off": absent == "yes" and not within(label["first_day"], k["first_day"], 1),
                     "back_off": absent == "yes" and not within(label["day_back"], k["day_back"], 1)})
    frame = pd.DataFrame(rows)

    def block(part: pd.DataFrame) -> dict:
        n = len(part)
        decided = part[part["absent"] != "unclear"]
        correct, working = int(decided["correct"].sum()), int(decided["working"].sum())
        share = (lambda k: round(k / len(decided), 4) if len(decided) else None)
        return {"items": n, "absent": part["absent"].value_counts().to_dict(), "of_decided": len(decided),
                "calendar_days": {"correct": correct, "share": share(correct), "interval_95": wilson(correct, len(decided)),
                                  "exact": int(decided["exact"].sum()), "first_day_off": int(decided["first_off"].sum()),
                                  "day_back_off": int(decided["back_off"].sum())},
                "working_days": {"correct": working, "share": share(working),
                                 "interval_95": wilson(working, len(decided))}}

    report = {"round": number, "primary_score": primary,
              "all": block(frame), **{kind: block(part) for kind, part in frame.groupby("kind")}}
    results.mkdir(parents=True, exist_ok=True)
    (results / f"absence_check_round{number}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def human(config: dict) -> None:
    """Agreement of a person's labels with the AI labeller's on round 1's human subset.

    Reads data/labels/round1/human_labels.json (the person's labels, keyed by
    item id) and writes results/absence_check_human.json: how often the two
    labellers agree that the sender is away, and, where both say so, whether
    their windows cover the same working days (within one at each end) and
    the same calendar days (within one). Also the round-1 detector's score
    against the person's labels.
    """
    settings, folder = config["absence_check"], config["paths"]["data"] / "labels" / "round1"
    ids = human_ids(settings)
    person = {int(k): v for k, v in json.loads((folder / "human_labels.json").read_text()).items()}
    ai = {int(k): v for k, v in json.loads((folder / "labels.json").read_text()).items()}
    key = {k["id"]: k for k in json.loads((folder / "key.json").read_text())}
    if set(person) != set(ids):
        raise SystemExit(f"the person's labels cover {len(set(person) & set(ids))} of {len(ids)} items")
    both_yes = [i for i in ids if person[i]["absent"] == ai[i]["absent"] == "yes"]
    same_absent = sum(person[i]["absent"] == ai[i]["absent"] for i in ids)
    working = sum(same_working_days(person[i], ai[i]) for i in both_yes)
    calendar = sum(within(person[i]["first_day"], ai[i]["first_day"], 1)
                   and within(person[i]["day_back"], ai[i]["day_back"], 1) for i in both_yes)
    decided = [i for i in ids if person[i]["absent"] != "unclear"]
    detector = sum(person[i]["absent"] == "yes" and same_working_days(person[i], key[i]) for i in decided)
    report = {"items": len(ids), "same_absent_answer": same_absent, "both_away": len(both_yes),
              "same_working_days": working, "same_working_days_interval_95": wilson(working, len(both_yes)),
              "same_calendar_days": calendar,
              "round1_detector_vs_person": {"correct_working_days": detector, "of_decided": len(decided),
                                            "interval_95": wilson(detector, len(decided))},
              "disagreements": [i for i in ids if i not in both_yes or not same_working_days(person[i], ai[i])]}
    config["paths"]["results"].mkdir(parents=True, exist_ok=True)
    (config["paths"]["results"] / "absence_check_human.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main() -> None:
    config = load_config()
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "draw":
        draw(config)
    elif command == "score":
        score(config)
    elif command == "human":
        human(config)
    else:
        raise SystemExit("usage: python -m enron_functional.absence_check draw|score|human")


if __name__ == "__main__":
    main()
