import pandas as pd
import pytest

from enron_functional import signals

T = pd.Timestamp


def mail(rows):
    frame = pd.DataFrame(rows, columns=["day", "sender_person", "to_people", "cc_people", "topic"])
    frame["day"] = pd.to_datetime(frame["day"])
    return frame.sort_values("day").reset_index(drop=True)


def test_window_measures_on_a_small_network():
    # a broker b between a and c; a 3-person topic 7 that b dominates
    signals._STATE.update(
        mail=mail([("2001-05-01", "a", ["b"], [], 7), ("2001-05-02", "b", ["c"], [], 7),
                   ("2001-05-03", "b", ["a", "c"], [], 7), ("2001-03-01", "a", ["c"], [], 7)]),
        referrals=pd.DataFrame({"day": pd.to_datetime(["2001-05-10"]), "person": ["b"]}),
        notices=pd.DataFrame({"day": pd.to_datetime(["2001-05-11"]), "absent": ["a"], "backups": [["b"]]}))
    original = signals.MIN_TOPIC_MESSAGES
    signals.MIN_TOPIC_MESSAGES = 3
    try:
        rows = {r["person"]: r for r in signals.window_measures((T("2001-06-01"), 56, ["a", "b", "z"]))}
    finally:
        signals.MIN_TOPIC_MESSAGES = original
    b = rows["b"]
    assert (b["sent"], b["received"], b["degree"]) == (2, 1, 2)
    assert b["betweenness"] == pytest.approx(1.0)        # the only path a - c runs through b
    assert b["topic_ownership"] == pytest.approx(2 / 3)
    assert (b["pointed_to"], b["named_backup"]) == (1, 1)
    assert rows["a"]["named_backup"] == 0                 # a's own notice does not count for a
    assert (rows["z"]["degree"], rows["z"]["constraint"], rows["z"]["topic_ownership"]) == (0, 1.0, 0.0)
