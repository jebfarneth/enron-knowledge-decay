import pandas as pd

from enron_importance.validate_threads import outcomes


def test_outcomes_compare_new_parents_with_labelled_ones():
    labels = pd.DataFrame([
        {"path": "c1", "parent_path": "p1", "classification": "direct_reply"},
        {"path": "c2", "parent_path": "p1", "classification": "wrong_immediate_parent"},
        {"path": "c3", "parent_path": "p1", "classification": "forward_or_relay_not_reply"},
    ])
    messages = pd.DataFrame({"path": ["p1", "p2", "c1", "c2", "c3"], "reply_to": [None, None, 0, 1, None],
                             "link_evidence": [None, None, "addressed", "quoted", None],
                             "link_kind": [None, None, "reply", "forward", None]})
    table = outcomes(labels, messages).set_index("path")
    assert table["outcome"].to_dict() == {"c1": "same parent", "c2": "other parent", "c3": "unlinked"}
