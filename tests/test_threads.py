import pandas as pd

from enron_importance.threads import link_replies


def msg(sender, to, subject, when, cc=()):
    return {"sender": sender, "to": list(to), "cc": list(cc), "subject": subject, "date": pd.Timestamp(when, tz="UTC")}


def test_reply_chain_forms_one_thread_with_response_times():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Turbine contract", "2001-05-01 09:00"),
        msg("b@enron.com", ["a@enron.com"], "RE: Turbine contract", "2001-05-01 10:30"),
        msg("a@enron.com", ["b@enron.com"], "Re: RE: Turbine contract", "2001-05-02 09:00"),
    ])
    linked = link_replies(frame, max_reply_days=14)
    assert pd.isna(linked.loc[0, "reply_to"])
    assert linked["reply_to"].tolist()[1:] == [0, 1]
    assert linked.loc[1, "response_seconds"] == 5400
    assert linked["thread_id"].nunique() == 1


def test_cc_recipient_can_reply():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Budget", "2001-05-01 09:00", cc=["c@enron.com"]),
        msg("c@enron.com", ["a@enron.com"], "RE: Budget", "2001-05-01 11:00"),
    ])
    assert link_replies(frame, 14).loc[1, "reply_to"] == 0


def test_non_recipient_same_subject_is_not_a_reply():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Budget", "2001-05-01 09:00"),
        msg("z@enron.com", ["a@enron.com"], "RE: Budget", "2001-05-01 11:00"),
    ])
    linked = link_replies(frame, 14)
    assert pd.isna(linked.loc[1, "reply_to"])
    assert linked["thread_id"].nunique() == 2


def test_replies_outside_the_window_are_not_linked():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Budget", "2001-05-01 09:00"),
        msg("b@enron.com", ["a@enron.com"], "RE: Budget", "2001-06-15 09:00"),
    ])
    assert pd.isna(link_replies(frame, 14).loc[1, "reply_to"])


def test_reply_attaches_to_the_latest_eligible_message():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Budget", "2001-05-01 09:00"),
        msg("a@enron.com", ["b@enron.com"], "Budget", "2001-05-01 15:00"),
        msg("b@enron.com", ["a@enron.com"], "RE: Budget", "2001-05-01 16:00"),
    ])
    linked = link_replies(frame, 14)
    assert linked.loc[2, "reply_to"] == 1
    assert linked.loc[2, "response_seconds"] == 3600
