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


def _big_fixture():
    rng = np.random.default_rng(1)
    people = [f"p{i}" for i in range(30)]
    level = {p: int(rng.integers(0, 4)) for p in people}
    rows = []
    while len(rows) < 80:
        a, b = rng.choice(people, 2, replace=False)
        if level[a] > level[b]:
            rows.append((a, b, ["core", "inter", "non-core"][len(rows) % 3]))
    scores = pd.DataFrame({"degree": [level[p] + rng.normal(0, 3.0) for p in people],
                           "custodian": [float(rng.integers(0, 2)) for _ in people]}, index=people)
    return pd.DataFrame(rows, columns=["dominant", "subordinate", "type"]).drop_duplicates(["dominant", "subordinate"]), scores


BIG, BIG_SCORES = _big_fixture()


def brute_force(pairs, credit, reps, seed):
    people = sorted(set(pairs["dominant"]) | set(pairs["subordinate"]))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(reps):
        sample = [people[i] for i in rng.integers(0, len(people), len(people))]
        total = weight = 0.0
        for x in sample:
            for y in sample:
                if (x, y) in credit:
                    total += credit[(x, y)]
                    weight += 1
        if weight:
            draws.append(total / weight)
    return tuple(np.percentile(draws, [2.5, 97.5]))


def test_gold_intervals_match_the_oracle_on_a_nondegenerate_fixture():
    score = BIG_SCORES["degree"]
    credit = {(d, s): 0.5 if score[d] == score[s] else float(score[d] > score[s])
              for d, s in zip(BIG["dominant"], BIG["subordinate"])}
    low, high = brute_force(BIG, credit, 300, 11)
    table = gold_table(BIG, BIG_SCORES, ["degree"], reps=300, seed=11).set_index("pairs_type")
    assert (table.loc["all", "ci_low"], table.loc["all", "ci_high"]) == pytest.approx((low, high))
    assert 0.0 < low < high < 1.0


def test_paired_intervals_match_the_oracle():
    d, c = BIG_SCORES["degree"], BIG_SCORES["custodian"]
    cr = lambda s, a, b: 0.5 if s[a] == s[b] else float(s[a] > s[b])  # noqa: E731
    gap = {(a, b): cr(c, a, b) - cr(d, a, b) for a, b in zip(BIG["dominant"], BIG["subordinate"])}
    low, high = brute_force(BIG, gap, 300, 5)
    paired = paired_gold(BIG, BIG_SCORES, "custodian", "degree", reps=300, seed=5).set_index("pairs_type")
    assert (paired.loc["all", "ci_low"], paired.loc["all", "ci_high"]) == pytest.approx((low, high))


def test_paired_differences_survive_empty_resamples():
    one = PAIRS.iloc[:1]
    paired = paired_gold(one, SCORES, "custodian", "degree", reps=1, seed=0)
    assert len(paired) >= 1 and "draws" in paired


def test_intervals_resample_gold_employees_even_when_they_share_a_graph_key():
    # Real pairs carry each employee's graph key; two employees on one key stay two resampling units.
    keyed = BIG.assign(dominant_key=BIG["dominant"].replace({"p1": "shared", "p2": "shared"}),
                       subordinate_key=BIG["subordinate"].replace({"p1": "shared", "p2": "shared"}))
    assert keyed["dominant_key"].nunique() < keyed["dominant"].nunique()
    score = BIG_SCORES["degree"]
    credit = {(d, s): 0.5 if score[d] == score[s] else float(score[d] > score[s])
              for d, s in zip(BIG["dominant"], BIG["subordinate"])}
    table = gold_table(keyed, BIG_SCORES, ["degree"], reps=300, seed=11).set_index("pairs_type")
    assert (table.loc["all", "ci_low"], table.loc["all", "ci_high"]) == pytest.approx(brute_force(BIG, credit, 300, 11))


def test_paired_intervals_also_resample_employees_when_they_share_a_graph_key():
    keyed = BIG.assign(dominant_key=BIG["dominant"].replace({"p1": "shared", "p2": "shared"}),
                       subordinate_key=BIG["subordinate"].replace({"p1": "shared", "p2": "shared"}))
    d, c = BIG_SCORES["degree"], BIG_SCORES["custodian"]
    cr = lambda s, a, b: 0.5 if s[a] == s[b] else float(s[a] > s[b])  # noqa: E731
    gap = {(a, b): cr(c, a, b) - cr(d, a, b) for a, b in zip(BIG["dominant"], BIG["subordinate"])}
    paired = paired_gold(keyed, BIG_SCORES, "custodian", "degree", reps=300, seed=5).set_index("pairs_type")
    assert (paired.loc["all", "ci_low"], paired.loc["all", "ci_high"]) == pytest.approx(brute_force(BIG, gap, 300, 5))
