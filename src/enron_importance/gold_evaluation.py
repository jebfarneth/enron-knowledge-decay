"""Evaluate network measures against the Agarwal et al. (2012) gold standard.

Task, as in the paper's Table 1: for each dominance pair, a score is correct
when it ranks the dominant employee higher; ties (equal within a relative
1e-9) count as half. This benchmark is reconstructed from a later release
and does not reproduce the paper's pair counts, so results are related to
the paper's, not a replication of them.

Main population: pairs from the main construction (see `gold_standard.py`)
whose two employees are both matched to a graph node by name or by an
address node spelled from their name, neither of whose records is an
uncertain owner, and whose dominance does not run through an uncertain
record. "Matched" and "uncertain" are operational labels from those rules,
not verified identities. Every other choice is a sensitivity run
in `results/gold_standard_sensitivity.csv`, including the earlier
convention of scoring unmatched employees 0 over all pairs.

`custodian` is a baseline that scores 1 for employees whose mailboxes are in
the corpus and 0 otherwise: it shows how much of the task is about which
mailboxes were collected, not about communication.

Intervals are 95% percentile intervals from resampling gold employees; a
resampled pair counts once per copy of each of its two people. A few
executives appear in thousands of pairs, so these intervals are wide and
describe that resampling scheme only: they do not include matching, label
or graph-construction uncertainty. Pairs are also summarized per dominant
employee (macro average), which weights each manager equally.

Outputs
  results/baselines_gold_standard.csv       main population, by pair type
  results/gold_standard_sensitivity.csv     alternative populations, constructions and scorings
  results/gold_standard_paired.csv          paired differences against degree
  results/gold_standard_coverage.json       match statuses and pair counts

Usage: uv run python -m enron_importance.gold_evaluation
"""

from __future__ import annotations

import json
import shutil
from collections import defaultdict

import numpy as np
import pandas as pd

from .config import load_config
from .evaluate import BASELINES, RTOL, _near, load_measures
from .gold_standard import MAPPED

GROUPS = ["all", "core", "inter", "non-core"]
MEASURES = BASELINES + ["custodian"]  # plus mention-network measures when available


def pair_credit(dominant: np.ndarray, subordinate: np.ndarray) -> np.ndarray:
    """1 when the dominant score is higher, 0.5 for a tie (relative 1e-9), 0 otherwise."""
    tie = _near(dominant, subordinate, RTOL)
    return np.where(tie, 0.5, (dominant > subordinate).astype(float))


def gold_scores(employees: pd.DataFrame, measures: pd.DataFrame, names: list[str] = BASELINES) -> pd.DataFrame:
    """One row per gold employee: each measure for matched employees (NaN otherwise), and `custodian`."""
    by_key = measures.set_index("person_key")
    matched = employees["match_status"].isin(MAPPED)
    scores = pd.DataFrame(index=employees["gold_id"].to_numpy())
    for name in names:
        scores[name] = employees["person_key"].map(by_key[name]).where(matched).to_numpy()
    scores["custodian"] = employees["custodian"].astype(float).to_numpy()
    return scores


def _resample_counts(people: int, reps: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [np.bincount(rng.integers(0, people, people), minlength=people) for _ in range(reps)]


def _credits(pairs: pd.DataFrame, scores: pd.DataFrame, name: str, fill: float | None) -> np.ndarray:
    dominant = pairs["dominant"].map(scores[name])
    subordinate = pairs["subordinate"].map(scores[name])
    if fill is not None:
        dominant, subordinate = dominant.fillna(fill), subordinate.fillna(fill)
    if dominant.isna().any() or subordinate.isna().any():
        raise ValueError(f"{name}: pairs with unscored employees; filter the population or pass fill")
    return pair_credit(dominant.to_numpy(float), subordinate.to_numpy(float))


def gold_table(pairs: pd.DataFrame, scores: pd.DataFrame, names: list[str], reps: int, seed: int,
               fill: float | None = None) -> pd.DataFrame:
    """Accuracy per measure, overall and by pair type, with person-bootstrap intervals.

    `pairs` is the population to score; `fill` scores missing employees
    (None requires every employee in `pairs` to be scored). A pair type
    with no pairs gives NaN; bootstrap draws without pairs of a type are
    skipped for that type, and `draws` reports how many were used.
    """
    people = pd.Index(sorted(set(pairs["dominant"]) | set(pairs["subordinate"])))
    first, second = people.get_indexer(pairs["dominant"]), people.get_indexer(pairs["subordinate"])
    counts = _resample_counts(len(people), reps, seed) if len(people) else []
    rows = []
    for name in names:
        credit = _credits(pairs, scores, name, fill) if len(pairs) else np.array([])
        for group in GROUPS:
            mask = np.ones(len(pairs), bool) if group == "all" else (pairs["type"] == group).to_numpy()
            draws = []
            for c in counts:
                weight = (c[first] * c[second])[mask]
                if weight.sum():
                    draws.append(float((weight * credit[mask]).sum() / weight.sum()))
            low, high = np.percentile(draws, [2.5, 97.5]) if draws else (np.nan, np.nan)
            rows.append({"measure": name, "pairs_type": group, "pairs": int(mask.sum()),
                         "accuracy": float(credit[mask].mean()) if mask.any() else np.nan,
                         "ci_low": float(low), "ci_high": float(high), "draws": len(draws)})
    return pd.DataFrame(rows)


def paired_gold(pairs: pd.DataFrame, scores: pd.DataFrame, first: str, second: str, reps: int, seed: int) -> pd.DataFrame:
    """Accuracy of `first` minus `second` by pair type, on the same person resamples."""
    people = pd.Index(sorted(set(pairs["dominant"]) | set(pairs["subordinate"])))
    i, j = people.get_indexer(pairs["dominant"]), people.get_indexer(pairs["subordinate"])
    gap = _credits(pairs, scores, first, None) - _credits(pairs, scores, second, None)
    rows = []
    for group in GROUPS:
        mask = np.ones(len(pairs), bool) if group == "all" else (pairs["type"] == group).to_numpy()
        if not mask.any():
            continue
        draws = [float((w * gap[mask]).sum() / w.sum()) for c in _resample_counts(len(people), reps, seed)
                 if (w := (c[i] * c[j])[mask]).sum()]
        low, high = np.percentile(draws, [2.5, 97.5]) if draws else (np.nan, np.nan)
        rows.append({"measure": first, "versus": second, "pairs_type": group, "difference": float(gap[mask].mean()),
                     "ci_low": float(low), "ci_high": float(high), "draws": len(draws)})
    return pd.DataFrame(rows)


def macro_accuracy(pairs: pd.DataFrame, scores: pd.DataFrame, name: str) -> float:
    """Mean over dominant employees of each one's share of correctly ordered pairs."""
    credit = pd.Series(_credits(pairs, scores, name, None), index=pairs.index)
    return float(credit.groupby(pairs["dominant"]).mean().mean())


def raw_address_degree(messages: pd.DataFrame, employees: pd.DataFrame) -> pd.Series:
    """Undirected degree over raw addresses in all mail (To, Cc, Bcc, any domain), max over each employee's release addresses."""
    neighbours: dict[str, set] = defaultdict(set)
    for sender, to, cc, bcc in zip(messages["sender"], messages["to"], messages["cc"], messages["bcc"]):
        if not isinstance(sender, str):
            continue
        for recipient in set(to) | set(cc) | set(bcc):
            if recipient != sender:
                neighbours[sender].add(recipient)
                neighbours[recipient].add(sender)
    degree = {address: len(others) for address, others in neighbours.items()}
    return pd.Series([max((degree.get(a, 0) for a in addresses), default=0) for addresses in employees["addresses"]],
                     index=employees["gold_id"].to_numpy(), dtype=float)


def main(config: dict | None = None) -> None:
    config = config or load_config()
    processed, results = config["paths"]["processed"], config["paths"]["results"]
    if not (processed / "gold_pairs.parquet").exists():
        print("Skipped: no gold_pairs.parquet (the gold-standard release is not available).")
        return
    reps, seed = config["evaluation"]["bootstrap_reps"], config["random_seed"]
    employees = pd.read_parquet(processed / "gold_employees.parquet")
    pairs = pd.read_parquet(processed / "gold_pairs.parquet")
    measures, names = load_measures(processed)
    scores = gold_scores(employees, measures, names)
    all_measures = names + ["custodian"]

    mapped = pairs["dominant_status"].isin(MAPPED) & pairs["subordinate_status"].isin(MAPPED)
    unmixed = ~pairs["dominant_mixed"] & ~pairs["subordinate_mixed"]
    certain = ~pairs["dominant_uncertain"] & ~pairs["subordinate_uncertain"]
    independent = pairs["independent_of_uncertain"].fillna(False).astype(bool)
    main_construction = pairs["construction"] == "main"
    population = pairs[main_construction & mapped & certain & independent]
    table = gold_table(population, scores, all_measures, reps, seed)
    results.mkdir(parents=True, exist_ok=True)
    table.to_csv(results / "baselines_gold_standard.csv", index=False, float_format="%.10f")

    confirmed = (pairs["dominant_status"] == "name+address") & (pairs["subordinate_status"] == "name+address")
    lay_skilling = set(employees.loc[employees["person_key"].isin(["kenneth lay", "jeffrey skilling"]), "gold_id"])
    variants = {
        "all pairs, unmatched employees scored 0": (pairs[main_construction], 0.0),
        "matched, including uncertain records": (pairs[main_construction & mapped], None),
        "matched, uncertain records excluded only as endpoints": (pairs[main_construction & mapped & certain], None),
        "matched, mixed-position endpoints excluded (earlier main)": (pairs[main_construction & mapped & unmixed], None),
        "name+address matches only": (pairs[main_construction & confirmed & certain & independent], None),
        "without Lay and Skilling": (population[~population["dominant"].isin(lay_skilling)
                                                & ~population["subordinate"].isin(lay_skilling)], None),
    }
    for construction in sorted(set(pairs["construction"]) - {"main"}):
        variants[construction] = (pairs[(pairs["construction"] == construction) & mapped & certain], None)
    runs = [gold_table(subset, scores, all_measures, reps, seed, fill).assign(variant=name)
            for name, (subset, fill) in variants.items()]
    raw = pd.DataFrame({"raw_address_degree": raw_address_degree(
        pd.read_parquet(processed / "messages.parquet", columns=["sender", "to", "cc", "bcc"]), employees)})
    runs.append(gold_table(pairs[main_construction], raw, ["raw_address_degree"], reps, seed, 0.0)
                .assign(variant="all pairs, raw-address degree over all mail, max over release addresses"))
    macro = pd.DataFrame([{"variant": "macro average over dominant employees", "measure": name, "pairs_type": "all",
                           "pairs": len(population), "accuracy": macro_accuracy(population, scores, name)}
                          for name in all_measures])
    sensitivity = pd.concat(runs + [macro], ignore_index=True)
    sensitivity = sensitivity[["variant", "measure", "pairs_type", "pairs", "accuracy", "ci_low", "ci_high", "draws"]]
    sensitivity.to_csv(results / "gold_standard_sensitivity.csv", index=False, float_format="%.10f")

    paired = pd.concat([paired_gold(population, scores, other, "degree", reps, seed)
                        for other in all_measures if other != "degree"], ignore_index=True)
    paired.to_csv(results / "gold_standard_paired.csv", index=False, float_format="%.10f")
    shutil.copyfile(processed / "gold_coverage.json", results / "gold_standard_coverage.json")

    show = lambda frame: print(frame.to_string(index=False, float_format=lambda v: f"{v:.3f}"))  # noqa: E731
    print(f"Main population: {len(population):,} pairs")
    show(table)
    show(sensitivity[sensitivity["pairs_type"] == "all"])
    show(paired)


if __name__ == "__main__":
    main()
