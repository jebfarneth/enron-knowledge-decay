"""Score the Phase 3 pilot labels against the pipeline's decisions.

Reads the adjudicated labels (and each labeller's own labels, for comparison) from data/labels/phase3_pilot/
and the hidden key from data/processed/phase3_pilot_key_private.json. Items labelled cannot_tell are left out
of each rate's denominator. Intervals are Wilson 95% intervals for the sampled frame; the population-weighted
reply precision and the recall estimate use the frame sizes recorded in the key.

Writes data/labels/phase3_pilot/scores.json. Usage: uv run python scripts/score_pilot_labels.py
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / "data" / "labels" / "phase3_pilot"
KEY = ROOT / "data" / "processed" / "phase3_pilot_key_private.json"
LEVELS = ("high", "medium", "low")


def wilson(k: int, n: int, z: float = 1.96) -> dict:
    if n == 0:
        return {"k": k, "n": n, "rate": None, "low": None, "high": None}
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"k": k, "n": n, "rate": p, "low": max(0.0, centre - half), "high": min(1.0, centre + half)}


def load(name: str) -> dict:
    with open(LABELS / name) as handle:
        return {row["item"]: row for row in map(json.loads, handle)}


def score(labels: dict, items: dict, population: dict) -> dict:
    groups = defaultdict(list)
    for item, meta in items.items():
        groups[(meta["task"], meta["frame"])].append((meta, labels[item]))
    out: dict = {"mentions": {}, "replies": {}, "exclusions": {}}

    for (task, frame), rows in sorted(groups.items()):
        if task == "mentions":
            known = [label for _, label in rows if label["referent"] != "cannot_tell"]
            out["mentions"][frame] = {
                "resolved_correctly": wilson(sum(l["referent"] == "resolved_person" for l in known), len(known)),
                "refers_to_an_enron_person": wilson(sum(l["referent"] in ("resolved_person", "other_enron_person") for l in known), len(known)),
                "referent": dict(Counter(l["referent"] for _, l in rows)),
                "context": dict(Counter(l["context"] for _, l in rows)),
            }
        elif task == "replies":
            known = [(meta, label) for meta, label in rows if label["parent"] != "cannot_tell"]
            if frame == "unlinked":
                out["replies"][frame] = {
                    "parent_among_candidates": wilson(sum(l["parent"].startswith("C") for _, l in known), len(known)),
                    "parent": dict(Counter(l["parent"] if not l["parent"].startswith("C") else "candidate" for _, l in rows)),
                }
            else:
                out["replies"][frame] = {
                    "parent_correct": wilson(sum(l["parent"] == m["pipeline_parent"] for m, l in known), len(known)),
                    "parent_correct_and_reply": wilson(sum(l["parent"] == m["pipeline_parent"] and l["kind"] == "reply"
                                                           for m, l in known), len(known)),
                    "parent": dict(Counter(l["parent"] if not l["parent"].startswith("C") else "candidate" for _, l in rows)),
                }
        else:
            out["exclusions"][frame] = {
                "substantive": wilson(sum(l["category"] == "substantive" for _, l in rows), len(rows)),
                "category": dict(Counter(l["category"] for _, l in rows)),
            }

    # Population-weighted reply precision, and recall among replies whose parent could be linked.
    sizes = {level: population[f"replies_{level}"] for level in LEVELS}
    correct = sum(sizes[level] * out["replies"][f"reply_{level}"]["parent_correct"]["rate"] for level in LEVELS)
    missed = population["replies_unlinked_with_candidates"] * out["replies"]["unlinked"]["parent_among_candidates"]["rate"]
    out["replies"]["weighted"] = {
        "reply_links": sum(sizes.values()),
        "estimated_correct_links": round(correct),
        "precision": correct / sum(sizes.values()),
        "estimated_missed_links": round(missed),
        "recall_within_frame": correct / (correct + missed),
        "note": "Recall covers unlinked Re: messages with quoted text, a person sender and at least one earlier "
                "same-subject message within 14 days; missed links outside that frame are not estimated.",
    }
    return out


def main() -> None:
    key = json.loads(KEY.read_text())
    items, population = key["items"], key["population"]
    results = {name: score(load(f"labels_{name}.jsonl"), items, population)
               for name in ("adjudicated", "codexA", "codexB")}
    results["population"] = population
    (LABELS / "scores.json").write_text(json.dumps(results, indent=2) + "\n")
    weighted = results["adjudicated"]["replies"]["weighted"]
    print(json.dumps(weighted, indent=2))


if __name__ == "__main__":
    main()
