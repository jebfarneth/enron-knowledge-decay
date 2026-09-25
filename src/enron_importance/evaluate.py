"""Evaluate importance scores against the formal-rank title proxy.

Metric: pairwise ordering accuracy (as in Agarwal et al. 2012). For every
pair of listed people at different title levels, a score is correct when it
ranks the more senior person higher; ties count as half. Random guessing
scores 0.5. Scores equal to within a relative 1e-9 are ties, so floating-point
summation order cannot turn a mathematical tie into an ordering.

Uncertainty: 95% percentile intervals from a person-level bootstrap. People
(not pairs) are resampled, because pairs sharing a person are not
independent. Measures are compared with paired differences on the same
resamples, not by eye from overlapping intervals.

A second label set is the Agarwal et al. (2012) gold standard: for each
dominance pair, a score is correct when it ranks the dominant employee
higher (ties count as half), as in their Table 1. Employees missing from the
graph score 0. Its intervals resample gold employees; a resampled pair
counts once per copy of each of its two people.

Outputs
  results/baselines_formal_rank.csv          main evaluation (title proxy)
  results/baselines_paired_differences.csv   top measure minus each other measure
  results/baselines_sensitivity.csv          label and graph sensitivity runs
  results/baselines_gold_standard.csv        accuracy on gold dominance pairs, by pair type

Usage: uv run python -m enron_importance.evaluate
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_config
from .network import build_edges, centrality, network_messages, recipient_resolver

BASELINES = ["degree", "in_strength", "out_strength", "pagerank", "betweenness"]
RTOL = 1e-9


def _near(a: np.ndarray, b: np.ndarray, rtol: float) -> np.ndarray:
    """Symmetric relative closeness: |a - b| <= rtol * max(|a|, |b|)."""
    return np.abs(a - b) <= rtol * np.maximum(np.abs(a), np.abs(b))


def _sign_gap(values: np.ndarray, rtol: float = 0.0) -> np.ndarray:
    gap = np.sign(values[:, None] - values[None, :])
    if rtol:
        gap[_near(values[:, None], values[None, :], rtol)] = 0
    return gap


def pairwise_accuracy(levels: np.ndarray, scores: np.ndarray) -> float:
    """Share of different-level pairs ordered correctly by `scores` (ties = 0.5)."""
    level_gap = _sign_gap(levels)
    score_gap = _sign_gap(scores, RTOL)
    mask = np.triu(level_gap != 0, k=1)
    if not mask.any():
        return float("nan")
    agree = (level_gap == score_gap)[mask].astype(float)
    ties = (score_gap == 0)[mask]
    return float(np.where(ties, 0.5, agree).mean())


def resamples(n: int, reps: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n, n) for _ in range(reps)]


def bootstrap_interval(levels: np.ndarray, scores: np.ndarray, reps: int, seed: int) -> tuple[float, float]:
    draws = [pairwise_accuracy(levels[idx], scores[idx]) for idx in resamples(len(levels), reps, seed)]
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return float(low), float(high)


def paired_difference(levels: np.ndarray, first: np.ndarray, second: np.ndarray, reps: int,
                      seed: int) -> tuple[float, float, float]:
    """Accuracy of `first` minus `second`, with a 95% interval from the same person resamples."""
    draws = [pairwise_accuracy(levels[idx], first[idx]) - pairwise_accuracy(levels[idx], second[idx])
             for idx in resamples(len(levels), reps, seed)]
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return pairwise_accuracy(levels, first) - pairwise_accuracy(levels, second), float(low), float(high)


def different_level_pairs(levels: np.ndarray) -> int:
    return int(np.triu(levels[:, None] != levels[None, :], k=1).sum())


def evaluation_table(ranked: pd.DataFrame, measures: list[str], reps: int, seed: int) -> pd.DataFrame:
    """`ranked`: one row per person with `level` and one column per measure."""
    levels = ranked["level"].to_numpy(float)
    rows = []
    for measure in measures:
        scores = ranked[measure].to_numpy(float)
        low, high = bootstrap_interval(levels, scores, reps, seed)
        rows.append({"measure": measure, "accuracy": pairwise_accuracy(levels, scores), "ci_low": low, "ci_high": high,
                     "people": len(ranked), "pairs": different_level_pairs(levels)})
    return pd.DataFrame(rows)


def paired_table(ranked: pd.DataFrame, measures: list[str], reps: int, seed: int) -> pd.DataFrame:
    """The highest-accuracy measure minus every other measure, on paired resamples."""
    levels = ranked["level"].to_numpy(float)
    accuracy = {m: pairwise_accuracy(levels, ranked[m].to_numpy(float)) for m in measures}
    top = max(accuracy, key=accuracy.get)
    rows = []
    for other in (m for m in measures if m != top):
        diff, low, high = paired_difference(levels, ranked[top].to_numpy(float), ranked[other].to_numpy(float), reps, seed)
        rows.append({"measure": top, "versus": other, "difference": diff, "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


def label_table(ranks: pd.DataFrame, levels: dict | None = None, exclude_disputed: bool = False,
                max_level: float | None = None) -> pd.DataFrame:
    """One row per labelled person. `levels` re-admits dropped conflicting rows at their listed title."""
    ranks = ranks.copy()
    if levels is not None:
        dropped = ranks["match"] == "dropped conflicting row"
        ranks.loc[dropped, "level"] = ranks.loc[dropped, "title"].map(levels)
    ranks = ranks.dropna(subset=["person_key", "level"])
    if exclude_disputed:
        ranks = ranks[~ranks["disputed"].astype(bool)]
    # A person still listed twice keeps their highest level.
    people = ranks.groupby("person_key", as_index=False)["level"].max()
    if max_level is not None:
        people = people[people["level"] <= max_level]
    return people.reset_index(drop=True)


def attach(people: pd.DataFrame, measures: pd.DataFrame) -> pd.DataFrame:
    table = people.merge(measures, on="person_key", how="left")
    return table.fillna({m: 0.0 for m in BASELINES if m in table})


def sensitivity(config: dict, ranks: pd.DataFrame, measures: pd.DataFrame) -> pd.DataFrame:
    """Rerun the evaluation under alternative label policies and graph definitions."""
    reps, seed = config["evaluation"]["bootstrap_reps"], config["random_seed"]
    levels = config["formal_rank"]["levels"]
    labels = {
        "main": label_table(ranks),
        "disputed labels removed": label_table(ranks, exclude_disputed=True),
        "conflicting rows kept at higher title": label_table(ranks, levels=levels),
        "CEO and President removed": label_table(ranks, max_level=levels["President"] - 1),
    }
    tables = [evaluation_table(attach(people, measures), BASELINES, reps, seed).assign(variant=name)
              for name, people in labels.items()]

    # Graph variants. Betweenness is omitted: it needs minutes per graph.
    fast = [m for m in BASELINES if m != "betweenness"]
    messages = network_messages(config)
    resolve = recipient_resolver(config)
    domain = config["senders"]["internal_domain"]
    graphs = {f"messages with at most {n} recipients": build_edges(messages, resolve, domain, max_recipients=n)
              for n in config["evaluation"]["recipient_limits"]}
    people_only = set(measures.loc[measures["entity_type"] == "person", "person_key"])
    edges, _ = build_edges(messages, resolve, domain)
    keep = edges["source"].isin(people_only) & edges["target"].isin(people_only)
    graphs["people-only graph"] = (edges[keep], None)
    for name, (graph_edges, sent) in graphs.items():
        variant = centrality(graph_edges, sent, betweenness=False)
        tables.append(evaluation_table(attach(labels["main"], variant), fast, reps, seed).assign(variant=name))
    return pd.concat(tables, ignore_index=True)[["variant", "measure", "accuracy", "ci_low", "ci_high", "people", "pairs"]]


def pair_credit(dominant: np.ndarray, subordinate: np.ndarray) -> np.ndarray:
    """1 when the dominant score is higher, 0.5 for a tie (relative 1e-9), 0 otherwise."""
    tie = _near(dominant, subordinate, RTOL)
    return np.where(tie, 0.5, (dominant > subordinate).astype(float))


def gold_table(pairs: pd.DataFrame, measures: pd.DataFrame, names: list[str], reps: int, seed: int) -> pd.DataFrame:
    """Accuracy on gold dominance pairs for each measure, overall and by pair type, with person-bootstrap intervals."""
    scores = measures.set_index("person_key")
    people = pd.Index(sorted(set(pairs["dominant"]) | set(pairs["subordinate"])))
    first, second = people.get_indexer(pairs["dominant"]), people.get_indexer(pairs["subordinate"])
    rng = np.random.default_rng(seed)
    counts = [np.bincount(rng.integers(0, len(people), len(people)), minlength=len(people)) for _ in range(reps)]
    rows = []
    for name in names:
        lookup = lambda keys: keys.map(scores[name]).fillna(0.0).to_numpy(float)  # noqa: E731
        credit = pair_credit(lookup(pairs["dominant_key"]), lookup(pairs["subordinate_key"]))
        for group in ["all", "core", "inter", "non-core"]:
            mask = np.ones(len(pairs), bool) if group == "all" else (pairs["type"] == group).to_numpy()
            draws = []
            for c in counts:
                weight = (c[first] * c[second])[mask]
                if weight.sum():
                    draws.append(float((weight * credit[mask]).sum() / weight.sum()))
            low, high = np.percentile(draws, [2.5, 97.5])
            rows.append({"measure": name, "pairs_type": group, "pairs": int(mask.sum()),
                         "accuracy": float(credit[mask].mean()), "ci_low": float(low), "ci_high": float(high)})
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    processed, results = config["paths"]["processed"], config["paths"]["results"]
    reps, seed = config["evaluation"]["bootstrap_reps"], config["random_seed"]
    ranks = pd.read_parquet(processed / "formal_rank.parquet")
    measures = pd.read_parquet(processed / "centrality.parquet")
    ranked = attach(label_table(ranks), measures)
    table = evaluation_table(ranked, BASELINES, reps, seed)
    results.mkdir(parents=True, exist_ok=True)
    table.to_csv(results / "baselines_formal_rank.csv", index=False, float_format="%.4f")
    paired = paired_table(ranked, BASELINES, reps, seed)
    paired.to_csv(results / "baselines_paired_differences.csv", index=False, float_format="%.4f")
    print(f"{len(ranked)} people, {different_level_pairs(ranked['level'].to_numpy()):,} different-level pairs")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(paired.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    gold = processed / "gold_pairs.parquet"
    if gold.exists():
        gold_results = gold_table(pd.read_parquet(gold), measures, BASELINES, reps, seed)
        gold_results.to_csv(results / "baselines_gold_standard.csv", index=False, float_format="%.4f")
        print(gold_results.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    runs = sensitivity(config, ranks, measures)
    runs.to_csv(results / "baselines_sensitivity.csv", index=False, float_format="%.4f")
    print(runs.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
