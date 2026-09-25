import pandas as pd

from enron_importance.formal_rank import formal_ranks

LEVELS = {"CEO": 6, "Vice President": 3, "Employee": 0}


def identities(*keys):
    return pd.DataFrame({"address": [f"{i}@enron.com" for i in range(len(keys))], "person_key": list(keys)})


def test_names_match_by_normalized_key_and_carry_levels():
    titles = pd.DataFrame({"name": ["Jeffery Skilling", "Tim Belden "], "title": ["CEO", "Vice President"]})
    ranks = formal_ranks(titles, identities("jeffrey skilling", "timothy belden"), LEVELS, {}).set_index("name")
    assert ranks.loc["Jeffery Skilling", "person_key"] == "jeffrey skilling"
    assert ranks.loc["Jeffery Skilling", "level"] == 6
    assert ranks.loc["Tim Belden", "level"] == 3


def test_reviewed_corrections_apply_before_normalization():
    titles = pd.DataFrame({"name": ["Micheal Swerzzbin"], "title": ["Vice President"]})
    ranks = formal_ranks(titles, identities("michael swerzbin"), LEVELS, {"Micheal Swerzzbin": "michael swerzbin"})
    assert ranks.loc[0, "person_key"] == "michael swerzbin" and ranks.loc[0, "match"] == "reviewed correction"


def test_unmatched_and_untitled_rows_are_kept_but_marked():
    titles = pd.DataFrame({"name": ["Jacob Thomas", "Philip Allen"], "title": ["Vice President", float("nan")]})
    ranks = formal_ranks(titles, identities("phillip allen"), LEVELS, {}).set_index("name")
    assert pd.isna(ranks.loc["Jacob Thomas", "person_key"]) and ranks.loc["Jacob Thomas", "match"] == "unmatched"
    assert ranks.loc["Philip Allen", "person_key"] == "phillip allen" and pd.isna(ranks.loc["Philip Allen", "level"])
