"""Draw the subset of the time-shifted copy sample that a person labels too.

The AI labeller labelled all 75 items of data/labels/shifted_copies/pairs.jsonl.
A person labels 20 of them on a blind sheet (no frame, no AI label): 12 long-shift,
4 near-whole-hour and 4 control items, drawn with a fixed seed. Agreement with the
AI labeller, and with the controls' expected answer (two sends), is scored by
scripts/score_shift_human.py.

Writes data/labels/shifted_copies/human_subset.json (seed, ids and frames) and
human_items.json (the blind sheet, in a shuffled order).

Usage: uv run python scripts/draw_shift_human_subset.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "labels" / "shifted_copies"
SEED = 20261014
COUNTS = {"long": 12, "near": 4, "control": 4}


def main() -> None:
    sample = json.loads((LABELS / "sample.json").read_text())["items"]
    rng = random.Random(SEED)
    chosen = []
    for frame, n in COUNTS.items():
        ids = sorted(i for i, v in sample.items() if v["frame"] == frame)
        chosen += rng.sample(ids, n)
    rng.shuffle(chosen)
    pairs = {p["item"]: p for p in map(json.loads, (LABELS / "pairs.jsonl").read_text().splitlines())}
    (LABELS / "human_subset.json").write_text(json.dumps(
        {"seed": SEED, "counts": COUNTS, "items": {i: sample[i]["frame"] for i in chosen}}, indent=2) + "\n")
    (LABELS / "human_items.json").write_text(json.dumps([pairs[i] for i in chosen], indent=1) + "\n")
    print(f"drew {len(chosen)} items: {COUNTS}")


if __name__ == "__main__":
    main()
