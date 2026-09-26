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

Evaluation against the Agarwal et al. (2012) gold standard is in
`gold_evaluation.py`.

Outputs
  results/baselines_formal_rank.csv          main evaluation (title proxy)
  results/baselines_paired_differences.csv   top measure minus each other measure, and mentioned_to minus degree
  results/baselines_sensitivity.csv          label and graph sensitivity runs

Usage: uv run python -m enron_importance.evaluate
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_config
from .network import build_edges, centrality, network_messages, recipient_resolver
from .provenance import record_stage

BASELINES = ["degree", "in_strength", "out_strength", "pagerank", "betweenness"]
# From the mention network (mentions.py), when that stage has been run; mentioned_to is the primary
# mention measure, and the unfiltered pair keeps the definition before audit 4 for comparison.
MENTION_MEASURES = ["mention_degree", "mentioned_to", "third_party_mentioned_to", "mention_degree_unfiltered",
                    "mentioned_to_unfiltered"]
# The comparison declared before the audit-4 rerun: the primary mention measure against degree.
PRIMARY = ("mentioned_to", "degree")


def load_measures(processed) -> tuple[pd.DataFrame, list[str]]:
    """Network measures per node, joined with mention-network measures when available (0 for no mention links)."""
    measures = pd.read_parquet(processed / "centrality.parquet")
    mentions = processed / "mention_centrality.parquet"
    if not mentions.exists():
        return measures, list(BASELINES)
    measures = measures.merge(pd.read_parquet(mentions), on="person_key", how="left")
    measures[MENTION_MEASURES] = measures[MENTION_MEASURES].fillna(0.0)
    return measures, BASELINES + MENTION_MEASURES
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
    """The highest-accuracy measure minus every other measure, and the declared PRIMARY comparison,
    on paired resamples."""
    levels = ranked["level"].to_numpy(float)
    accuracy = {m: pairwise_accuracy(levels, ranked[m].to_numpy(float)) for m in measures}
    top = max(accuracy, key=accuracy.get)
    comparisons = [(top, other) for other in measures if other != top]
    if set(PRIMARY) <= set(measures) and PRIMARY not in comparisons:
        comparisons.append(PRIMARY)
    rows = []
    for first, second in comparisons:
        diff, low, high = paired_difference(levels, ranked[first].to_numpy(float), ranked[second].to_numpy(float), reps, seed)
        rows.append({"measure": first, "versus": second, "difference": diff, "ci_low": low, "ci_high": high})
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
    return table.fillna({m: 0.0 for m in BASELINES + MENTION_MEASURES if m in table})


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
    names = [m for m in BASELINES + MENTION_MEASURES if m in measures]
    tables = [evaluation_table(attach(people, measures), names, reps, seed).assign(variant=name)
              for name, people in labels.items()]

    # Graph variants. Betweenness is omitted: it needs minutes per graph.
    fast = [m for m in BASELINES if m != "betweenness"]
    messages = network_messages(config)
    resolve = recipient_resolver(config)
    domain = config["senders"]["internal_domain"]
    graphs = {f"messages with at most {n} recipients": build_edges(messages, resolve, domain, max_recipients=n)
              for n in config["evaluation"]["recipient_limits"]}
    # People-only graph rebuilt from messages, so messages sent stays an exact count.
    people_only = set(measures.loc[measures["entity_type"] == "person", "person_key"])
    graphs["people-only graph"] = build_edges(messages[messages["sender_person"].isin(people_only)],
                                              lambda a: r if (r := resolve(a)) in people_only else None, domain)
    for name, (graph_edges, sent) in graphs.items():
        variant = centrality(graph_edges, sent, betweenness=False)
        tables.append(evaluation_table(attach(labels["main"], variant), fast, reps, seed).assign(variant=name))
    return pd.concat(tables, ignore_index=True)[["variant", "measure", "accuracy", "ci_low", "ci_high", "people", "pairs"]]


def main() -> None:
    config = load_config()
    processed, results = config["paths"]["processed"], config["paths"]["results"]
    reps, seed = config["evaluation"]["bootstrap_reps"], config["random_seed"]
    ranks = pd.read_parquet(processed / "formal_rank.parquet")
    measures, names = load_measures(processed)
    ranked = attach(label_table(ranks), measures)
    table = evaluation_table(ranked, names, reps, seed)
    results.mkdir(parents=True, exist_ok=True)
    table.to_csv(results / "baselines_formal_rank.csv", index=False, float_format="%.10f")
    paired = paired_table(ranked, names, reps, seed)
    paired.to_csv(results / "baselines_paired_differences.csv", index=False, float_format="%.10f")
    print(f"{len(ranked)} people, {different_level_pairs(ranked['level'].to_numpy()):,} different-level pairs")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(paired.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    runs = sensitivity(config, ranks, measures)
    runs.to_csv(results / "baselines_sensitivity.csv", index=False, float_format="%.10f")
    print(runs.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    record_stage(config, "evaluate")


if __name__ == "__main__":
    main()
