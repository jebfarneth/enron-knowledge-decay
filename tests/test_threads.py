import pandas as pd

from enron_importance.identity import normalize_name
from enron_importance.threads import link_replies, quoted_author


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
    # Not addressed back (the alias is external and unresolved): a relay, whatever the Re: prefix.
    assert linked.loc[1, "link_kind"] == "forward" and pd.isna(linked.loc[1, "response_seconds"])


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


def test_a_reply_that_repeats_the_parent_instruction_is_not_rejected_as_inverted():
    ask = "Please send the signed turbine contract to legal by Friday so we can close the deal."
    parent = {**msg("a@enron.com", ["b@enron.com"], "Contract", "2001-05-01 09:00"), "authored": ask, "body": ask}
    child = {**msg("b@enron.com", ["a@enron.com"], "RE: Contract", "2001-05-01 10:00"), "authored": ask + " Done.",
             "body": ask + " Done."}
    assert link_replies(pd.DataFrame([parent, child]), 14).loc[1, "reply_to"] == 0


def test_a_message_never_replies_to_its_own_sender():
    frame = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com", "a@enron.com"], "Invite", "2001-05-01 09:00"),
        msg("a@enron.com", ["b@enron.com", "a@enron.com"], "Re: Invite", "2001-05-01 10:00"),
    ])
    assert link_replies(frame, 14)["reply_to"].isna().all()


def test_an_addressed_parent_from_someone_other_than_the_quoted_author_is_rejected():
    rows = [
        {**msg("sullivan", ["scott", "cherry"], "Exhibit", "2000-06-08 12:47"), "quoted_from": None},
        {**msg("scott", ["sullivan", "cherry"], "RE: Exhibit", "2000-06-08 13:04"), "quoted_from": None},
        {**msg("cherry", ["scott", "sullivan"], "RE: Exhibit", "2000-06-09 07:51"), "quoted_from": "scott"},
    ]
    linked = link_replies(pd.DataFrame(rows), 14)
    assert linked.loc[2, "reply_to"] == 1          # Scott's message, which Cherry quotes, not Sullivan's
    rows[1]["quoted_from"], rows[2]["quoted_from"] = None, "someone else"
    assert pd.isna(link_replies(pd.DataFrame(rows), 14).loc[2, "reply_to"])


def test_the_quoted_author_decides_even_when_an_older_ancestor_is_quoted_deeper():
    kevin = "We would like to hire Willis Phillips from Koch; Rogers, Dana and I have all interviewed him."
    rows = [
        {**msg("kevin presto", ["john lavorato", "louise kitchen"], "willis phillips", "2001-04-27 08:49"),
         "authored": kevin, "body": kevin, "quoted_from": None},
        {**msg("louise kitchen", ["kevin presto", "john lavorato"], "Re: willis phillips", "2001-04-27 10:13"),
         "authored": "This isn't the ex-metals trader from Koch? What level is he?", "quoted_from": "kevin presto"},
        {**msg("john lavorato", ["louise kitchen", "kevin presto"], "RE: willis phillips", "2001-04-27 11:00"),
         "authored": "He is a director.", "quoted_from": "louise kitchen",
         # Louise's text is quoted in another wrapping, so only Kevin's nested text is found.
         "body": f"He is a director.\n\n -----Original Message-----\nFrom: Kitchen, Louise\n\nThis isn't the\nex-metals\n\n{kevin}"},
    ]
    linked = link_replies(pd.DataFrame(rows), 14)
    assert linked.loc[2, "reply_to"] == 1 and linked.loc[2, "link_confidence"] == "medium"
    linked = link_replies(pd.DataFrame(rows[:1] + rows[2:]), 14)
    assert pd.isna(linked.loc[1, "reply_to"])       # Louise's message is missing: abstain, not Kevin's


def test_a_message_that_first_quotes_its_own_sender_is_not_linked():
    rows = [
        {**msg("louise kitchen", ["mary cook"], "Contracts", "2002-01-04 09:00"), "quoted_from": None},
        {**msg("mary cook", ["louise kitchen"], "RE: Contracts", "2002-01-07 10:41"), "quoted_from": "louise kitchen"},
        {**msg("mary cook", ["peter keohane"], "FW: Contracts", "2002-01-07 11:00", cc=["louise kitchen"]),
         "quoted_from": "mary cook"},
    ]
    linked = link_replies(pd.DataFrame(rows), 14)
    assert linked.loc[1, "reply_to"] == 0
    assert pd.isna(linked.loc[2, "reply_to"])       # not Louise's older message


def test_a_forward_subject_is_a_relay_even_when_addressed_back():
    text = "The Dynegy master netting agreement is signed and filed with legal."
    parent = {**msg("a@enron.com", ["b@enron.com"], "Netting", "2001-05-01 09:00"), "authored": text, "body": text}
    child = {**msg("b@enron.com", ["a@enron.com", "c@enron.com"], "FW: Netting", "2001-05-01 10:00"), "authored": "FYI",
             "body": f"FYI\n\n -----Original Message-----\nFrom: A\nSent: x\n\n{text}"}
    linked = link_replies(pd.DataFrame([parent, child]), 14)
    assert linked.loc[1, "reply_to"] == 0 and linked.loc[1, "link_kind"] == "forward"
    assert pd.isna(linked.loc[1, "response_seconds"])


def test_link_confidence_counts_the_author_and_text_evidence():
    text = "Can you send me the west power curve by 3pm today, please?"
    parent = {**msg("a", ["b"], "Curve", "2001-05-01 09:00"), "authored": text, "body": text}
    quoting = f"Done.\n\n -----Original Message-----\nFrom: A\nSent: x\n\n{text}"
    for quoted_from, body, expected in [("a", quoting, "high"), (None, quoting, "medium"), ("a", "Done.", "medium"),
                                        (None, "Done.", "low")]:
        child = {**msg("b", ["a"], "RE: Curve", "2001-05-01 10:00"), "authored": "Done.", "body": body,
                 "quoted_from": quoted_from}
        assert link_replies(pd.DataFrame([{**parent, "quoted_from": None}, child]), 14).loc[1, "link_confidence"] == expected


def test_a_quoted_author_matches_a_sender_with_a_middle_initial():
    rows = [{**msg("kevin presto", ["john lavorato"], "Hire", "2001-04-27 08:49"), "quoted_from": None},
            {**msg("john lavorato", ["kevin presto"], "RE: Hire", "2001-04-27 09:00"), "quoted_from": "kevin m presto"}]
    assert link_replies(pd.DataFrame(rows), 14).loc[1, "reply_to"] == 0


def test_quoted_author_reads_every_header_form_and_takes_the_first():
    def author(body):
        return quoted_author(body, lambda a: {"kay.mann@enron.com": "kay mann"}.get(a, a), normalize_name)

    lotus_bare = "Here it is.\n\n\n\tTana Jones\n\t05/01/2001 06:00 AM\n\t\t\n\t\t To: Sara Shackleton/HOU/ECT@ECT\n\t\t cc: \n"
    nested = "\n\n -----Original Message-----\nFrom: Heard, Marie\nSent: x\n\nold text"
    assert author(lotus_bare + "\t\t Subject: ISDA\n\nPlease send it." + nested) == {"tana jones"}
    assert author("OK\n\n\nKay Mann@ENRON\n05/01/2001 09:00 AM\nTo: Mark Taylor/HOU/ECT@ECT\ncc:\nSubject: T\n\nx") == {"kay mann"}
    assert author("OK\n\n -----Original Message-----\nFrom: Kay Mann/HOU/ECT@ECT on 05/01/2001\nSent: x\n\nx") == {"kay mann"}
    assert author("OK\n\n -----Original Message-----\nFrom: Sharen Cason 01/05/2001 10:23 AM\nSent: x\n\nx") == {"sharen cason"}
    one_line = ("FYI.\n\n---------------------- Forwarded by Vince J Kaminski/HOU/ECT on 04/09/2001 11:20 AM ------\n\n\n"
                '"Susan C. Hansen" <susan.hansen@stanford.edu> on 04/06/2001 06:14:10 PM\nTo:\tVince.J.Kaminski@enron.com\n'
                "Subject:\tVisiting Enron\n\nDear Vince,")
    assert author(one_line) == {"susan.hansen@stanford.edu", "susan hansen"}   # the address and the display name
    bare_address = "OK\n\n -----Original Message-----\nFrom: carol.st.clair@enron.com [mailto:carol.st.clair@enron.com]\nSent: x\n\nx"
    assert author(bare_address) == {"carol.st.clair@enron.com", "carol clair"}  # the local part names the person
    # A name and a date inside a quote, without a To: line, are not a header.
    assert author("OK\n\n -----Original Message-----\nSent: x\n\nThanks,\nTana Jones\n05/01/2001 10:00 AM\nMore") is None


def test_a_quoted_author_matches_any_key_the_parent_sender_goes_by():
    rows = [
        # An outside sender has no person key: the message's sender is its raw address.
        {**msg("cameron@mondavi.com", ["jeff dasovich"], "Wine", "2001-05-01 09:00"),
         "sender_keys": frozenset({"cameron sellers"}), "quoted_from": None},
        {**msg("jeff dasovich", ["cameron@mondavi.com"], "RE: Wine", "2001-05-01 10:00"),
         "quoted_from": frozenset({"cameron sellers"})},
    ]
    assert link_replies(pd.DataFrame(rows), 14).loc[1, "reply_to"] == 0
    rows[1]["quoted_from"] = frozenset({"someone else"})
    assert pd.isna(link_replies(pd.DataFrame(rows), 14).loc[1, "reply_to"])
