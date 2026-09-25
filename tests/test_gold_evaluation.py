import numpy as np
import pandas as pd
import pytest

from enron_importance.gold_evaluation import gold_scores, gold_table, macro_accuracy, pair_credit, paired_gold

PAIRS = pd.DataFrame({"dominant": ["a", "a", "b", "d"], "subordinate": ["b", "c", "c", "e"],
                      "type": ["core", "inter", "non-core", "non-core"]})
SCORES = pd.DataFrame({"degree": [5.0, 5.0, 1.0, 2.0, 7.0], "custodian": [1.0, 0.0, 0.0, 1.0, 0.0]},
                      index=["a", "b", "c", "d", "e"])


def test_pair_credit_handles_wins_losses_and_near_ties():
    assert list(pair_credit(np.array([2.0, 1.0, 3.0]), np.array([1.0, 2.0, 3.0 + 1e-12]))) == [1.0, 0.0, 0.5]


def test_gold_table_accuracy_by_type():
    table = gold_table(PAIRS, SCORES, ["degree"], reps=50, seed=0).set_index("pairs_type")
    assert table.loc["all", "accuracy"] == pytest.approx((0.5 + 1 + 1 + 0) / 4)
    assert table.loc["core", "accuracy"] == 0.5 and table.loc["non-core", "pairs"] == 2


def test_gold_table_bootstrap_matches_a_brute_force_oracle():
    table = gold_table(PAIRS, SCORES, ["degree"], reps=200, seed=3).set_index("pairs_type")
    people = sorted("abcde")
    credit = {("a", "b"): 0.5, ("a", "c"): 1.0, ("b", "c"): 1.0, ("d", "e"): 0.0}
    rng = np.random.default_rng(3)
    draws = []
    for _ in range(200):
        sample = [people[i] for i in rng.integers(0, 5, 5)]
        total = weight = 0.0
        for x in sample:            # every ordered pair of sampled copies that forms a gold pair
            for y in sample:
                if (x, y) in credit:
                    total += credit[(x, y)]
                    weight += 1
        if weight:
            draws.append(total / weight)
    assert (table.loc["all", "ci_low"], table.loc["all", "ci_high"]) == pytest.approx(tuple(np.percentile(draws, [2.5, 97.5])))
    assert table.loc["all", "draws"] == len(draws)


def test_missing_scores_must_be_filled_or_filtered():
    scores = SCORES.assign(degree=[5.0, np.nan, 1.0, 2.0, 7.0])
    with pytest.raises(ValueError):
        gold_table(PAIRS, scores, ["degree"], reps=10, seed=0)
    filled = gold_table(PAIRS, scores, ["degree"], reps=10, seed=0, fill=0.0).set_index("pairs_type")
    assert filled.loc["core", "accuracy"] == 1.0   # a scores 5 against b filled with 0


def test_empty_pair_types_give_nan_not_an_error():
    table = gold_table(PAIRS[PAIRS["type"] == "core"], SCORES, ["degree"], reps=10, seed=0).set_index("pairs_type")
    assert np.isnan(table.loc["inter", "accuracy"]) and table.loc["inter", "draws"] == 0
    assert gold_table(PAIRS.iloc[:0], SCORES, ["degree"], reps=10, seed=0)["accuracy"].isna().all()


def test_same_graph_node_for_two_gold_employees_is_a_tie():
    scores = pd.DataFrame({"degree": [3.0, 3.0]}, index=["x", "y"])
    pairs = pd.DataFrame({"dominant": ["x"], "subordinate": ["y"], "type": ["core"]})
    assert gold_table(pairs, scores, ["degree"], reps=10, seed=0).iloc[0]["accuracy"] == 0.5


def test_macro_average_weights_each_dominant_equally():
    assert macro_accuracy(PAIRS, SCORES, "degree") == pytest.approx(((0.5 + 1) / 2 + 1 + 0) / 3)


def test_paired_difference_uses_the_same_pairs():
    paired = paired_gold(PAIRS, SCORES, "custodian", "degree", reps=50, seed=0).set_index("pairs_type")
    assert paired.loc["all", "difference"] == pytest.approx(np.mean([1, 1, 0.5, 1]) - np.mean([0.5, 1, 1, 0]))


def test_scores_are_missing_for_unmatched_employees_but_custodian_is_always_known():
    employees = pd.DataFrame({"gold_id": ["a", "b"], "person_key": ["ka", None], "match_status": ["name", "absent"],
                              "custodian": [True, False]})
    measures = pd.DataFrame({"person_key": ["ka"], "degree": [4.0], "in_strength": [1.0], "out_strength": [1.0],
                             "pagerank": [0.1], "betweenness": [0.0]})
    scores = gold_scores(employees, measures)
    assert scores.loc["a", "degree"] == 4.0 and np.isnan(scores.loc["b", "degree"])
    assert list(scores["custodian"]) == [1.0, 0.0]
