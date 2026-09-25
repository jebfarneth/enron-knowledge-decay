import pandas as pd

from enron_importance.validate_cleaning import compare, summary, token_jaccard


def test_jaccard_edges():
    assert token_jaccard("", "") == 1.0
    assert token_jaccard("a b", "a b") == 1.0
    assert token_jaccard("a b", "c d") == 0.0


def test_both_tools_agree_on_a_plain_reply():
    frame = compare(pd.Series(["Thanks!\n\n> earlier text\n", "Meeting at 3pm."]))
    assert frame["agree"].all()
    result = summary(frame)
    assert result["messages"] == 2 and result["residue"]["angle_quote"]["ours"] == 0.0


def test_summary_exposes_a_cleaner_that_deletes_everything():
    frame = compare(pd.Series(["Please call me.\n\n-----Original Message-----\nFrom: A\nSent: B\n\nold", "Plain note."]))
    result = summary(frame)
    assert result["empty_output"]["ours"] == 0.0
    assert result["median_share_of_text_kept"]["ours"] > 0.2
    assert result["residue"]["original_message"]["empty_cleaner"] == 0.0 and result["empty_output"]["empty_cleaner"] == 1.0
