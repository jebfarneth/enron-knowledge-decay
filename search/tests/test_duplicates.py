import os

import numpy as np
import pandas as pd
import pytest

from enron_search.duplicates import candidate_pairs, describe, reason, summary
from enron_search.store import connect, ensure_database, load

DSN = os.environ.get("ENRON_SEARCH_TEST_DSN")
db = pytest.mark.skipif(not DSN, reason="set ENRON_SEARCH_TEST_DSN to a disposable database")
BODY = "Please see the attached storage report for the Bammel field before Monday's meeting. " * 2


def message(date, authored=BODY, subject="Storage report", to=("a@enron.com",), cc=(), sender="ann", path="p"):
    return {"path": path, "date": pd.Timestamp(date, tz="UTC"), "authored": authored, "subject": subject,
            "to": list(to), "cc": list(cc), "sender_person": sender}


@pytest.mark.parametrize("second, expected", [
    (message("2001-05-01 14:00", authored=BODY + " Thanks."), "text differs"),
    (message("2001-05-01 14:00", subject="RE: storage REPORT"), "shift not whole hours"),
    (message("2001-05-01 13:30", subject="Bammel"), "subject differs"),
    (message("2001-05-01 13:30", to=("b@enron.com",)), "recipients differ"),
    (message("2001-05-01 13:30", to=("A@enron.com ",)), "matches on authored text"),
    (message("2001-05-01 12:30"), "same time"),
    (message("2001-05-01 22:30"), "shift over 8 hours"),
    (message("2001-05-01 14:10", authored="  " + BODY.replace(". ", ".\n\n")), "shift not whole hours"),
])
def test_reason_names_the_first_failed_condition(second, expected):
    assert reason(message("2001-05-01 12:30"), second) == expected


def unit(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


ROWS = pd.DataFrame([
    {**message("2001-05-01 09:00", path="m/0"), "message_id": "<0>", "sender": "ann@enron.com", "custodian": "c",
     "folder": "f"},
    {**message("2001-05-01 12:00", path="m/1"), "message_id": "<1>", "sender": "ann@enron.com", "custodian": "c",
     "folder": "f"},                                     # 3 hours later, same vector: a candidate
    {**message("2001-05-05 12:00", path="m/2"), "message_id": "<2>", "sender": "ann@enron.com", "custodian": "c",
     "folder": "f"},                                     # same vector, outside the 48-hour window
    {**message("2001-05-01 10:00", path="m/3", sender="bob"), "message_id": "<3>", "sender": "bob@enron.com",
     "custodian": "c", "folder": "f"},                   # same vector, another sender
    {**message("2001-05-01 11:00", path="m/4", authored="short"), "message_id": "<4>",
     "sender": "ann@enron.com", "custodian": "c", "folder": "f"},  # too short
    {**message("2001-05-01 11:30", path="m/5"), "message_id": "<5>", "sender": "ann@enron.com", "custodian": "c",
     "folder": "f"},                                     # different meaning
])
VECTORS = unit([[1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0], [0, 1, 0]])


@pytest.mark.db
@db
def test_pairs_come_from_one_sender_inside_the_window():
    ensure_database(DSN)
    with connect(DSN) as connection:
        load(connection, ROWS, VECTORS, {"model": "test"})
        pairs = candidate_pairs(connection, window_hours=48, min_chars=100, min_similarity=0.98)
    assert pairs[["first", "second"]].values.tolist() == [[0, 1]]
    described = describe(pairs, ROWS)
    assert described.loc[0, "reason"] == "matches on authored text" and described.loc[0, "gap_hours"] == 3
    report = summary(described, {})
    assert report["pairs"] == 1 and report["messages_in_pairs"] == 2 and report["pairs_by_reason"] == {
        "matches on authored text": 1}
