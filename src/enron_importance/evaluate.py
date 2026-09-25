"""Evaluate importance scores against formal rank.

Metric: pairwise ordering accuracy (as in Agarwal et al. 2012). For every
pair of listed people at different title levels, a score is correct when it
ranks the more senior person higher; ties count as half. Random guessing
scores 0.5.

Uncertainty: 95% percentile intervals from a person-level bootstrap. People
(not pairs) are resampled, because pairs sharing a person are not
independent.

Usage: uv run python -m enron_importance.evaluate
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import load_config

BASELINES = ["degree", "in_strength", "out_strength", "pagerank", "betweenness"]


def pairwise_accuracy(levels: np.ndarray, scores: np.ndarray) -> float:
    """Share of different-level pairs ordered correctly by `scores` (ties = 0.5)."""
    level_gap = np.sign(levels[:, None] - levels[None, :])
    score_gap = np.sign(scores[:, None] - scores[None, :])
    mask = np.triu(level_gap != 0, k=1)
    if not mask.any():
        return float("nan")
    agree = (level_gap == score_gap)[mask].astype(float)
    ties = (score_gap == 0)[mask]
    return float(np.where(ties, 0.5, agree).mean())


def bootstrap_interval(levels: np.ndarray, scores: np.ndarray, reps: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(levels)
    draws = [pairwise_accuracy(levels[idx], scores[idx]) for idx in (rng.integers(0, n, n) for _ in range(reps))]
    low, high = np.nanpercentile(draws, [2.5, 97.5])
    return float(low), float(high)


def evaluation_table(ranked: pd.DataFrame, measures: list[str], reps: int, seed: int) -> pd.DataFrame:
    """`ranked`: one row per person with `level` and one column per measure."""
    levels = ranked["level"].to_numpy(float)
    rows = []
    for measure in measures:
        scores = ranked[measure].to_numpy(float)
        low, high = bootstrap_interval(levels, scores, reps, seed)
        rows.append({"measure": measure, "accuracy": pairwise_accuracy(levels, scores), "ci_low": low, "ci_high": high})
    return pd.DataFrame(rows)


def ranked_people(config: dict) -> pd.DataFrame:
    processed = config["paths"]["processed"]
    ranks = pd.read_parquet(processed / "formal_rank.parquet").dropna(subset=["person_key", "level"])
    # A person listed twice keeps their highest level.
    people = ranks.groupby("person_key", as_index=False)["level"].max()
    measures = pd.read_parquet(processed / "centrality.parquet")
    table = people.merge(measures, on="person_key", how="left")
    return table.fillna({m: 0.0 for m in BASELINES})


def main() -> None:
    config = load_config()
    ranked = ranked_people(config)
    table = evaluation_table(ranked, BASELINES, config["evaluation"]["bootstrap_reps"], config["random_seed"])
    results = config["paths"]["results"]
    results.mkdir(parents=True, exist_ok=True)
    table.to_csv(results / "baselines_formal_rank.csv", index=False, float_format="%.4f")
    levels = ranked["level"].to_numpy()
    n_pairs = int(np.triu(levels[:, None] != levels[None, :], k=1).sum())
    print(f"{len(ranked)} people, {n_pairs:,} different-level pairs")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
