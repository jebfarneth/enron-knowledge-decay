"""Paper 1's mention comparisons from high-confidence names only (collection/PLAN_resolution.md, Part 4).

In the pilot, 78.6% of sampled names in the mention measures resolved to the
right person, and most errors were people outside Enron matched to an
employee with the same name. This script recomputes the mention measures on
the full corpus from two subsets of Paper 1's main mention links, each
dropping a likelier kind of error:

  full names      the name has a first and a last name ("Mark Taylor"), not
                  one word ("Mark", "Taylor") or initials
  one candidate   exactly one person in the email network is compatible
                  with the name

and compares each measure with degree on Paper 1's 7,338 main pairs, all
pairs and by pair type, with Paper 1's person bootstrap (paired differences
on the same resamples). With all links it must reproduce Paper 1's paired
results. It also reports, from the pilot's adjudicated labels, how often
names in each subset resolved to the right person.

Writes collection/results/confident_names.csv and confident_names.json.

Usage: .venv/bin/python collection/confident_names.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corrections as co  # noqa: E402
import experiment as ex  # noqa: E402

from enron_importance.gold_evaluation import pair_credit, paired_gold  # noqa: E402
from enron_importance.mentions import _INITIALS, _TOKEN, compatible, name_index  # noqa: E402

MEASURES = ["mention_degree", "mentioned_to", "third_party_mentioned_to", "talked_about"]
PILOT = Path(__file__).resolve().parents[1] / "data" / "labels" / "phase3_pilot"


def kind(mention: str) -> str:
    """How `compatible` matches a name: initials, one word (first or last name), or a full name."""
    if _INITIALS.fullmatch(mention.replace("'s", "")):
        return "initials"
    words = [w for w in _TOKEN.findall(mention.lower().replace("'s", "")) if len(w) > 1]
    return "full name" if len(words) >= 2 else "one word"


def scores(ctx: dict, links: pd.DataFrame) -> pd.DataFrame:
    everything = np.ones(len(ctx["member_mentions"]), bool)
    table = ex.mention_measures(links, everything).set_index("person_key").join(
        co.talked_about(links, everything), how="outer").fillna(0.0)
    network = ctx["full_network"].set_index("person_key")
    keys = ctx["employees"]["person_key"]
    out = pd.DataFrame(index=ctx["employees"]["gold_id"].to_numpy())
    out["degree"] = keys.map(network["degree"]).fillna(0.0).to_numpy(float)
    for m in MEASURES:
        out[m] = keys.map(table[m]).fillna(0.0).to_numpy(float)
    return out


def pilot_precision(index: dict) -> dict:
    items = {}
    for line in (PILOT / "mentions.jsonl").read_text().splitlines():
        item = json.loads(line)
        items[item["item"]] = item
    labels = [json.loads(line) for line in (PILOT / "labels_adjudicated.jsonl").read_text().splitlines()]
    rows = []
    key = json.loads((Path(__file__).resolve().parents[1] / "data" / "processed" / "phase3_pilot_key_private.json").read_text())
    for label in labels:
        name = label.get("item")
        if name not in items or key["items"].get(name, {}).get("frame") != "main" or label["referent"] == "cannot_tell":
            continue   # scored as scripts/score_pilot_labels.py scores them: "cannot tell" is left out
        mention = items[name]["mention"]
        rows.append({"kind": kind(mention), "one_candidate": len(compatible(mention, index)) == 1,
                     "correct": label["referent"] == "resolved_person", "outside": label["referent"] == "outside_person"})
    frame = pd.DataFrame(rows)
    report = lambda f: {"n": len(f), "correct": int(f["correct"].sum()), "outside_person": int(f["outside"].sum())}  # noqa: E731
    return {"all": report(frame), "full names": report(frame[frame["kind"] == "full name"]),
            "one word": report(frame[frame["kind"] == "one word"]), "one candidate": report(frame[frame["one_candidate"]]),
            "several candidates": report(frame[~frame["one_candidate"]])}


def main() -> None:
    started = time.time()
    ctx = ex.prepare(started)
    config = ctx["config"]
    processed = config["paths"]["processed"]
    reps, seed = config["evaluation"]["bootstrap_reps"], config["random_seed"]
    types = pd.read_parquet(processed / "person_types.parquet")
    people = set(types.loc[types["entity_type"] == "person", "person_key"])
    edges = pd.read_parquet(processed / "edges.parquet")
    index = name_index(people & (set(edges["source"]) | set(edges["target"])))

    population = ctx["population"]
    t = population["type"].to_numpy()
    groups = {g: (np.ones(len(t), bool) if g == "all" else t == g) for g in ex.TYPES}
    links = ctx["links"].copy()
    candidates = {m: len(compatible(m, index)) for m in links["mention"].unique()}
    links["kind"] = links["mention"].map(kind)
    links["candidates"] = links["mention"].map(candidates)
    subsets = {"all links": links, "full names": links[links["kind"] == "full name"],
               "one candidate": links[links["candidates"] == 1]}

    rows, out_accuracy = [], {}
    for subset, l in subsets.items():
        s = scores(ctx, l)
        out_accuracy[subset] = {}
        for m in ["degree"] + MEASURES:
            credit = pair_credit(population["dominant"].map(s[m]).to_numpy(float),
                                 population["subordinate"].map(s[m]).to_numpy(float))
            out_accuracy[subset][m] = {g: round(float(credit[mask].mean()), 4) for g, mask in groups.items()}
        for m in MEASURES:
            for _, r in paired_gold(population, s, m, "degree", reps, seed).iterrows():
                rows.append({"subset": subset, "links": len(l), "measure": m, "pairs_type": r["pairs_type"],
                             "accuracy": out_accuracy[subset][m][r["pairs_type"]],
                             "difference_vs_degree": r["difference"], "ci_low": r["ci_low"], "ci_high": r["ci_high"]})
    results = pd.DataFrame(rows)

    # With all links, the paired differences must be Paper 1's.
    paper = pd.read_csv(config["paths"]["results"] / "gold_standard_paired.csv")
    for m in ("mention_degree", "mentioned_to", "third_party_mentioned_to"):
        mine = results[(results["subset"] == "all links") & (results["measure"] == m)].set_index("pairs_type")
        theirs = paper[(paper["measure"] == m) & (paper["versus"] == "degree")].set_index("pairs_type")
        for column, other in (("difference_vs_degree", "difference"), ("ci_low", "ci_low"), ("ci_high", "ci_high")):
            if not np.allclose(mine[column], theirs.loc[mine.index, other], atol=1e-9):
                raise SystemExit(f"{m} {column}: all links do not reproduce gold_standard_paired.csv")
    print(f"check passed: all links reproduce Paper 1's paired differences; {time.time() - started:.0f} s", flush=True)

    out = {"links": {k: len(v) for k, v in subsets.items()},
           "link_share_by_kind": {k: round(float(v), 4) for k, v in links["kind"].value_counts(normalize=True).items()},
           "pilot_precision": pilot_precision(index), "accuracy": out_accuracy}
    primary = results[(results["measure"] == "mentioned_to") & (results["pairs_type"] == "non-core")].set_index("subset")
    out["expectations"] = {
        "H1_non_core_advantage_of_people_mentioned_to_them": {
            s: [round(float(primary.loc[s, c]), 4) for c in ("difference_vs_degree", "ci_low", "ci_high")]
            for s in ("full names", "one candidate")},
        "H1_met": bool((primary.loc[["full names", "one candidate"], "ci_low"] > 0).all()),
    }
    results.to_csv(ex.OUT / "confident_names.csv", index=False, float_format="%.6f")
    (ex.OUT / "confident_names.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["expectations"], indent=2))


if __name__ == "__main__":
    main()
