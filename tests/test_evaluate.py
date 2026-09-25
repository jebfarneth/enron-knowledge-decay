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


def test_bootstrap_interval_is_computed_not_fixed():
    levels = np.arange(30, dtype=float)
    assert bootstrap_interval(levels, levels * 2, reps=100, seed=3) == (1.0, 1.0)
    assert bootstrap_interval(levels, -levels, reps=100, seed=3) == (0.0, 0.0)


def test_floating_point_near_ties_count_as_ties():
    levels = np.array([2.0, 0.0])
    assert pairwise_accuracy(levels, np.array([72.00000000000001, 72.0])) == 0.5
    assert pairwise_accuracy(levels, np.array([72.001, 72.0])) == 1.0


def test_paired_difference_uses_the_same_resamples():
    from enron_importance.evaluate import paired_difference
    levels = np.arange(20, dtype=float)
    diff, low, high = paired_difference(levels, levels, levels.copy(), reps=100, seed=0)
    assert diff == low == high == 0.0
    diff, low, high = paired_difference(levels, levels, -levels, reps=100, seed=0)
    assert diff == low == high == 1.0


def test_label_table_policies():
    from enron_importance.evaluate import label_table
    ranks = pd.DataFrame([
        {"person_key": "a", "title": "Trader", "level": 0.0, "match": "normalized name", "disputed": False},
        {"person_key": "a", "title": "Vice President", "level": None, "match": "dropped conflicting row", "disputed": False},
        {"person_key": "b", "title": "Manager", "level": 1.0, "match": "normalized name", "disputed": True},
        {"person_key": "c", "title": "CEO", "level": 6.0, "match": "normalized name", "disputed": False},
    ])
    levels = {"Trader": 0, "Manager": 1, "Vice President": 3, "CEO": 6}
    assert label_table(ranks).set_index("person_key")["level"].to_dict() == {"a": 0.0, "b": 1.0, "c": 6.0}
    assert label_table(ranks, levels=levels).set_index("person_key").loc["a", "level"] == 3
    assert "b" not in set(label_table(ranks, exclude_disputed=True)["person_key"])
    assert "c" not in set(label_table(ranks, max_level=4)["person_key"])


def test_gold_table_scores_pairs_and_splits_by_type():
    from enron_importance.evaluate import gold_table
    pairs = pd.DataFrame({"dominant": ["a", "a", "b"], "subordinate": ["b", "c", "c"],
                          "dominant_key": ["ka", "ka", "kb"], "subordinate_key": ["kb", None, "kc"],
                          "type": ["core", "inter", "non-core"]})
    measures = pd.DataFrame({"person_key": ["ka", "kb", "kc"], "degree": [5.0, 5.0, 1.0]})
    table = gold_table(pairs, measures, ["degree"], reps=50, seed=0).set_index("pairs_type")
    # a-b tie (0.5), a over unmatched c scores 0 (1), b over c (1)
    assert table.loc["all", "accuracy"] == pytest.approx(2.5 / 3)
    assert table.loc["core", "accuracy"] == 0.5 and table.loc["inter", "pairs"] == 1
    assert table.loc["all", "ci_low"] <= table.loc["all", "accuracy"] <= table.loc["all", "ci_high"]


def test_bootstrap_matches_an_independent_brute_force_oracle():
    levels = np.array([3, 2, 2, 1, 0, 0, 1, 3, 2, 0], dtype=float)
    scores = np.array([9, 4, 7, 3, 1, 5, 2, 6, 8, 0], dtype=float)
    rng = np.random.default_rng(7)
    draws = []
    for _ in range(300):
        idx = rng.integers(0, len(levels), len(levels))
        credit = total = 0.0
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                la, lb, sa, sb = levels[idx[a]], levels[idx[b]], scores[idx[a]], scores[idx[b]]
                if la == lb:
                    continue
                total += 1
                credit += 0.5 if sa == sb else float((la > lb) == (sa > sb))
        draws.append(credit / total)
    expected = tuple(float(v) for v in np.percentile(draws, [2.5, 97.5]))
    assert bootstrap_interval(levels, scores, reps=300, seed=7) == pytest.approx(expected)
    assert expected[0] < 0.9 < expected[1]  # a non-degenerate interval


def test_near_ties_are_symmetric():
    a, b = 17.80489355345007, 17.804893571254965
    assert pairwise_accuracy(np.array([0.0, 1.0]), np.array([a, b])) == pairwise_accuracy(np.array([1.0, 0.0]), np.array([b, a]))
