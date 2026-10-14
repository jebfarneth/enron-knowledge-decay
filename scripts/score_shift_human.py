"""Score the person's labels of the time-shifted copy subset.

Compares data/labels/shifted_copies/human_labels.json (a person's blind labels of the
20 items in human_subset.json) with the AI labeller's labels.jsonl, and with each
item's frame: controls are separate sends by construction (their gaps are not near a
whole number of hours), and long and near items are candidate copies.

Writes data/labels/shifted_copies/human_scores.json.

Usage: uv run python scripts/score_shift_human.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

LABELS = Path(__file__).resolve().parents[1] / "data" / "labels" / "shifted_copies"


def main() -> None:
    subset = json.loads((LABELS / "human_subset.json").read_text())["items"]
    person = json.loads((LABELS / "human_labels.json").read_text())
    ai = {r["item"]: r for r in map(json.loads, (LABELS / "labels.jsonl").read_text().splitlines())}
    if set(person) != set(subset):
        raise SystemExit(f"labels cover {len(set(person) & set(subset))} of {len(subset)} items")
    rows = [{"item": i, "frame": subset[i], "person": person[i]["verdict"], "ai": ai[i]["verdict"],
             "confidence": person[i]["confidence"]} for i in sorted(subset)]
    shifted = [r for r in rows if r["frame"] != "control"]
    controls = [r for r in rows if r["frame"] == "control"]
    report = {
        "items": len(rows),
        "agree_with_ai": sum(r["person"] == r["ai"] for r in rows),
        "shifted_items": len(shifted),
        "shifted_person_verdicts": dict(Counter(r["person"] for r in shifted)),
        "control_items": len(controls),
        "control_person_verdicts": dict(Counter(r["person"] for r in controls)),
        "person_confidence": dict(Counter(r["confidence"] for r in rows)),
        "disagreements": [{k: r[k] for k in ("item", "frame", "person", "ai")} for r in rows if r["person"] != r["ai"]],
    }
    (LABELS / "human_scores.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
