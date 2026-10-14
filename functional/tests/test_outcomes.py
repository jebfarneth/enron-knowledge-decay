import pandas as pd

from enron_functional.outcomes import catch_up, message_outcomes, rerouted_share, stalled_share

T = pd.Timestamp


def test_messages_to_the_person_and_whether_they_were_answered_within_24_hours():
    windows = pd.DataFrame([{"absence_id": 1, "window": "away", "person": "ann", "start": T("2001-05-07"),
                             "back": T("2001-05-10")}])
    mail = pd.DataFrame([
        {"path": "m1", "local": T("2001-05-07 09:00"), "to_people": ["ann"]},          # answered in 2 hours
        {"path": "m2", "local": T("2001-05-08 09:00"), "to_people": ["ann", "bob"]},   # answered in 30 hours
        {"path": "m3", "local": T("2001-05-09 09:00"), "to_people": ["ann"]},          # under 24 h before the day back
        {"path": "m4", "local": T("2001-05-07 10:00"), "to_people": ["bob"]},          # not to ann
        {"path": "m5", "local": T("2001-05-06 23:00"), "to_people": ["ann"]},          # before the window
    ])
    links = pd.DataFrame({"path": ["r1", "r2"], "parent_path": ["m1", "m2"], "link_kind": "reply",
                          "link_confidence": ["low", "high"], "response_seconds": [7200.0, 30 * 3600.0],
                          "thread": ["t1", "t2"]})
    out = message_outcomes(windows, mail, links).set_index("path")
    assert list(out.index) == ["m1", "m2"]
    assert out.loc["m1", "answered"] and not out.loc["m1", "answered_high"]
    assert not out.loc["m2", "answered"] and out.loc["m2", "answered_48"]
    assert out.loc["m1", "eligible_48"] and not out.loc["m2", "eligible_48"]      # m2 is under 48 h before the day back


def frame(rows):
    out = pd.DataFrame(rows, columns=["local", "sender_person", "to_people", "cc_people", "thread", "path"])
    out["local"] = pd.to_datetime(out["local"])
    return out.sort_values("local").reset_index(drop=True)


def test_stalled_threads_wait_for_the_day_back():
    sent = frame([("2001-05-03", "ann", ["bob"], [], "t1", "a"), ("2001-05-04", "ann", ["bob"], [], "t2", "b")])
    days = {"t1": pd.to_datetime(["2001-05-03", "2001-05-12"]).values,       # quiet during, resumes after: stalled
            "t2": pd.to_datetime(["2001-05-04", "2001-05-08"]).values}       # continues during
    share, n = stalled_share("ann", T("2001-05-07"), T("2001-05-10"), sent, days)
    assert (share, n) == (0.5, 2)


def test_rerouting_counts_contacts_mail_to_new_people():
    baseline = [("2001-04-20", "bob", ["ann"], [], None, f"b{i}") for i in range(3)]
    during = [("2001-05-08", "bob", ["carl"], [], None, "d1"), ("2001-05-08", "bob", ["ann"], [], None, "d2")]
    bob = frame(baseline + during)
    received = frame(baseline).assign(recipient="ann")
    share, n = rerouted_share("ann", T("2001-05-07"), T("2001-05-10"), {"bob": bob}, {"ann": received})
    assert (share, n) == (0.5, 2)


def test_catch_up_is_relative_to_the_working_day_average():
    sent = frame([(f"2001-04-{d:02d} 10:00", "ann", ["bob"], [], None, f"p{d}") for d in range(10, 30)]
                 + [("2001-05-10 10:00", "ann", ["bob"], [], None, "x1"), ("2001-05-11 10:00", "ann", ["bob"], [], None, "x2"),
                    ("2001-05-11 11:00", "ann", ["bob"], [], None, "x3")])
    value = catch_up("ann", T("2001-05-07"), T("2001-05-10"), sent)
    assert round(value, 3) == round(3 / (2 * 20 / 40), 3)
