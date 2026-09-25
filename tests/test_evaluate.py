import numpy as np
import pandas as pd
import pytest

from enron_importance.evaluate import bootstrap_interval, evaluation_table, pairwise_accuracy


def test_perfect_reversed_and_tied_scores():
    levels = np.array([3, 2, 1, 0])
    assert pairwise_accuracy(levels, np.array([4, 3, 2, 1])) == 1.0
    assert pairwise_accuracy(levels, np.array([1, 2, 3, 4])) == 0.0
    assert pairwise_accuracy(levels, np.zeros(4)) == 0.5


def test_same_level_pairs_are_ignored():
    levels = np.array([1, 1, 0])
    # Only pairs (0,2) and (1,2) count; both are ordered correctly.
    assert pairwise_accuracy(levels, np.array([5, 9, 1])) == 1.0


def test_partial_accuracy_counts_each_pair():
    levels = np.array([2, 1, 0])
    # Pairs: (0,1) wrong, (0,2) right, (1,2) right.
    assert pairwise_accuracy(levels, np.array([1, 2, 0])) == pytest.approx(2 / 3)


def test_bootstrap_is_reproducible_and_brackets_the_estimate():
    rng = np.random.default_rng(0)
    levels = rng.integers(0, 5, 60).astype(float)
    scores = levels + rng.normal(0, 1.5, 60)
    first = bootstrap_interval(levels, scores, reps=200, seed=42)
    assert first == bootstrap_interval(levels, scores, reps=200, seed=42)
    assert first[0] <= pairwise_accuracy(levels, scores) <= first[1]


def test_evaluation_table_has_one_row_per_measure():
    ranked = pd.DataFrame({"level": [2, 1, 0], "good": [3.0, 2.0, 1.0], "bad": [1.0, 2.0, 3.0]})
    table = evaluation_table(ranked, ["good", "bad"], reps=50, seed=1).set_index("measure")
    assert table.loc["good", "accuracy"] == 1.0 and table.loc["bad", "accuracy"] == 0.0
