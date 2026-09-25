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


def test_forward_to_someone_else_without_quotation_is_not_a_reply():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com"], "Netting agreement", "2001-11-16 09:00"),
        msg("b@enron.com", ["c@enron.com"], "FW: Netting agreement", "2001-11-16 10:00"),
    ])
    assert pd.isna(link_replies(frame, 14).loc[1, "reply_to"])


def test_quotation_links_a_reply_sent_to_a_different_address():
    parent = {**msg("a@enron.com", ["b@enron.com"], "Curve", "2001-05-01 09:00"),
              "authored": "Can you send me the west power curve by 3pm today?", "body": "Can you send me the west power curve by 3pm today?"}
    child = {**msg("b@enron.com", ["a.alias@haas.berkeley.edu"], "RE: Curve", "2001-05-01 10:00"),
             "authored": "Attached.",
             "body": "Attached.\n\n -----Original Message-----\nFrom: A\nSent: today\n\nCan you send me the west power curve by 3pm today?"}
    linked = link_replies(pd.DataFrame([parent, child]), 14)
    assert linked.loc[1, "reply_to"] == 0 and linked.loc[1, "link_evidence"] == "quoted"
    assert linked.loc[1, "link_kind"] == "reply" and linked.loc[1, "response_seconds"] == 3600


def test_parent_that_already_quotes_the_child_is_rejected():
    text = "The Port memo is ready for review and I have marked the open issues in red."
    original = {**msg("a@enron.com", ["b@enron.com"], "Memo", "2001-05-01 22:57"), "authored": text, "body": text}
    quoting = {**msg("b@enron.com", ["a@enron.com"], "RE: Memo", "2001-05-01 13:00"),
               "authored": "Thanks", "body": f"Thanks\n\n -----Original Message-----\nFrom: A\nSent: x\n\n{text}"}
    linked = link_replies(pd.DataFrame([quoting, original]), 14)
    assert pd.isna(linked.loc[1, "reply_to"])


def test_ineligible_messages_are_never_linked():
    frame = pd.DataFrame([
        msg("crawler@enron.com", ["pete@enron.com"], "Schedule Crawler: HourAhead Failure", "2001-05-01 09:00"),
        msg("pete@enron.com", ["crawler@enron.com"], "Schedule Crawler: HourAhead Failure", "2001-05-01 10:00"),
    ])
    linked = link_replies(frame, 14, eligible=pd.Series([False, True]))
    assert linked["reply_to"].isna().all()


def test_relaying_a_message_to_someone_else_is_a_forward():
    text = "Kevin approved the RDI access request for the whole scheduling group."
    parent = {**msg("kevin@enron.com", ["b@enron.com"], "RDI access", "2001-05-01 09:00"), "authored": text, "body": text}
    child = {**msg("b@enron.com", ["paula@enron.com"], "FW: RDI access", "2001-05-01 10:00"), "authored": "FYI",
             "body": f"FYI\n\n -----Original Message-----\nFrom: Kevin\nSent: x\n\n{text}"}
    linked = link_replies(pd.DataFrame([parent, child]), 14)
    assert linked.loc[1, "reply_to"] == 0 and linked.loc[1, "link_kind"] == "forward"
    assert pd.isna(linked.loc[1, "response_seconds"])


def test_the_message_quoted_first_is_the_parent_not_an_earlier_one():
    first = "Try the lemon cake recipe from the Houston paper, it keeps for days."
    second = "Actually the carrot cake is easier and the kids will like it better."
    rows = [
        {**msg("dennis@enron.com", ["b@enron.com"], "cakes", "2001-05-01 00:13"), "authored": first, "body": first},
        {**msg("dennis@enron.com", ["b@enron.com"], "Re: cakes", "2001-05-01 07:42"), "authored": second, "body": second},
        {**msg("b@enron.com", ["dennis@enron.com"], "Re: cakes", "2001-05-01 08:00"), "authored": "Carrot it is.",
         "body": f"Carrot it is.\n\n -----Original Message-----\nFrom: Dennis\nSent: x\n\n{second}\n\n{first}"},
    ]
    assert link_replies(pd.DataFrame(rows), 14).loc[2, "reply_to"] == 1
