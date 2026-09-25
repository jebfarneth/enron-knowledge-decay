import pandas as pd

from enron_importance.senders import (automated_messages, name_rule, routine_messages, sender_profiles, speech_act,
                                     structured_record, template_of)


def test_template_masks_changing_numbers():
    a = "Start Date: 4/1/01; HourAhead hour: 5;  No ancillary schedules awarded."
    b = "Start Date: 4/2/01; HourAhead hour: 17; No ancillary schedules awarded."
    assert template_of(a) == template_of(b)


def test_name_rules():
    for address in ["no.reply@enron.com", "mailer-daemon@enron.com", "enron.announcements@enron.com", "postmaster@x.com"]:
        assert name_rule(address), address
    for address in ["jeff.dasovich@enron.com", "kay.mann@enron.com", "sally.beck@enron.com", "adminoff@enron.com"]:
        assert not name_rule(address), address


def test_templated_feed_is_flagged_but_a_person_is_not():
    feed = [{"sender": "pete.davis@enron.com", "authored": f"Start Date: 4/{d}/01; HourAhead hour: {h}; schedule awarded."}
            for d in range(1, 11) for h in range(1, 7)]
    person = [{"sender": "jeff.dasovich@enron.com", "authored": f"Note {i}: the CPUC moved the hearing, call me about item {i}."[: 20 + i]}
              for i in range(60)]
    profiles = sender_profiles(pd.DataFrame(feed + person), "enron.com", min_messages=50, feed_share=0.5)
    assert profiles.loc["pete.davis@enron.com", "automated"]
    assert profiles.loc["pete.davis@enron.com", "template_share"] == 1.0
    assert not profiles.loc["jeff.dasovich@enron.com", "automated"]
    assert profiles["internal"].all()


def test_low_volume_senders_are_never_flagged_by_behaviour():
    rows = [{"sender": "x@enron.com", "authored": "same"}] * 10
    profiles = sender_profiles(pd.DataFrame(rows), "enron.com", min_messages=50, feed_share=0.5)
    assert not profiles.loc["x@enron.com", "feed"]


def test_missing_values_do_not_fail():
    assert template_of(float("nan")) == ""
    assert not name_rule(float("nan"))


WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike november oscar papa quebec "
         "romeo sierra tango uniform victor whiskey xray yankee zulu amber birch cedar dahlia elm fern grove hazel "
         "iris jasmine kale laurel maple nettle").split()


def test_feed_split_across_three_templates_is_flagged():
    texts = (["Start Date: 4/{d}/01; HourAhead hour: {h}; No ancillary schedules awarded. Log: parsing file"] * 25
             + ["Start Date: 4/{d}/01; HourAhead hour: {h}; HourAhead schedule download failed."] * 20
             + ["Start Date: 4/{d}/01; HourAhead hour: {h}; download failed. Manual intervention. Log: x"] * 15
             + [f"{word} note about the west desk" for word in WORDS[:40]])
    rows = [{"sender": "feed@enron.com", "authored": t.format(d=i % 28 + 1, h=i % 24)} for i, t in enumerate(texts)]
    profiles = sender_profiles(pd.DataFrame(rows), "enron.com", min_messages=50, feed_share=0.5)
    assert profiles.loc["feed@enron.com", "template_share"] == 0.6
    assert profiles.loc["feed@enron.com", "automated"]


def test_frequent_forwarder_with_no_own_text_is_not_flagged():
    rows = ([{"sender": "person@enron.com", "authored": ""}] * 200
            + [{"sender": "person@enron.com", "authored": f"Thanks {i}, see you at the {i} meeting"[: 15 + i % 20]} for i in range(30)])
    profiles = sender_profiles(pd.DataFrame(rows), "enron.com", min_messages=50, feed_share=0.5)
    assert profiles.loc["person@enron.com", "n_with_text"] == 30
    assert not profiles.loc["person@enron.com", "automated"]


def test_person_with_weekly_report_keeps_their_other_messages():
    rows = ([{"sender": "analyst@enron.com", "authored": f"Attached is the credit watch listing for week {w}."} for w in range(12)]
            + [{"sender": "analyst@enron.com", "authored": f"{word} question about the counterparty limits"} for word in WORDS[:40]])
    frame = pd.DataFrame(rows)
    profiles = sender_profiles(frame, "enron.com", min_messages=50, feed_share=0.9)
    assert not profiles.loc["analyst@enron.com", "automated"]
    routine = routine_messages(frame, min_repeats=10)
    assert routine.sum() == 12 and not routine.iloc[12:].any()


def test_feed_account_keeps_the_messages_its_owner_wrote():
    alerts = [{"sender": "pete.davis@enron.com", "authored": f"Start Date: 4/{d}/01; HourAhead hour: {h}; schedule awarded."}
              for d in range(1, 11) for h in range(1, 7)]
    human = [{"sender": "pete.davis@enron.com", "authored": "I reproduced the bug: Schedule Crawler posted false finals. Please watch the next import."},
             {"sender": "pete.davis@enron.com", "authored": "Done."}]
    frame = pd.DataFrame(alerts + human)
    profiles = sender_profiles(frame, "enron.com", min_messages=50, feed_share=0.9)
    assert profiles.loc["pete.davis@enron.com", "feed"]
    automated = automated_messages(frame, profiles)
    assert automated.iloc[:60].all() and not automated.iloc[60:].any()


def test_name_rule_accounts_are_automated_message_by_message():
    frame = pd.DataFrame([{"sender": "no.reply@enron.com", "authored": "unique text"}])
    profiles = sender_profiles(frame, "enron.com", min_messages=50, feed_share=0.9)
    assert automated_messages(frame, profiles).all()


def test_personalized_notices_share_one_template():
    a = "ALLEN, PHILLIP K,\n?\nYou have been selected to participate in the Mid Year 2001 Performance Management process."
    b = "ARNOLD, JOHN D,\n?\nYou have been selected to participate in the Mid Year 2001 Performance Management process."
    assert template_of(a) == template_of(b)
    assert template_of("FYI\nsee below") == "fyi see below"


def test_structured_records_are_not_prose():
    assert structured_record("CALENDAR ENTRY:\tAPPOINTMENT\n\nDescription:\n\tStaff mtg.")
    assert structured_record("ARNOLD, JOHN D:\n \nAttached below you will find the final Evaluation forms for your direct reports")
    assert structured_record("Thank you for changing lives.\n\nEmployee ID:  90009776")
    assert not structured_record("Can you check the calendar entry for Friday?")
    for text in ["Calendar Entry\n\nBrief description:\nDate:", "This in an automated e-mail sent out from the Commissioner.COM",
                 "Requester: Ian Cooke\nRequest Type: Vacation", "Feb 02, 2001\n\nYEAR END 2000 PERFORMANCE EVALUATION FORMS ARE DUE",
                 "MAY,  LARRY ,\n \nYou have been selected to participate in Enron's Mid Year 2001 Performance Management process",
                 "NOTE:  YOU WILL RECEIVE THIS MESSAGE EACH TIME YOU ARE SELECTED AS A REVIEWER."]:
        assert structured_record(text), text
    assert name_rule("daemon.extra@enron.com")


def test_repeated_short_speech_acts_stay_in_text_analysis():
    for text in ["Approved", "please print", "Will do.", "Looks good to me.", "pls print. thanks df"]:
        assert speech_act(text, 4), text
    assert not speech_act("Attached is the credit watch listing for this week.", 4)
    assert not speech_act("", 4)
    assert speech_act("Please see attached.\n\nThanks,\nWendi LeBrocq\nx3-3835", 4)


def test_length_counts_the_whole_message_not_its_opening():
    divider = "=" * 90
    digest = f"{divider}\n" + "The committee met today and approved the new budget for the west desk. " * 20
    assert not speech_act(digest, 4)
    assert not speech_act("http://www.example.com/" + "a" * 80 + " Enron shares fell again today as traders sold.", 4)


def test_routine_needs_the_whole_text_repeated_not_just_the_opening():
    notice = "PRIVILEGED AND CONFIDENTIAL - ATTORNEY WORK PRODUCT. "
    rows = [{"sender": "britt.davis@enron.com", "authored": notice + f"Analysis of claim {c}: the {c} indemnity fails."}
            for c in "abcdefghijkl"]
    frame = pd.DataFrame(rows)
    assert not routine_messages(frame, min_repeats=10).any()
    assert routine_messages(pd.DataFrame([{"sender": "a@enron.com", "authored": notice}] * 10), 10).all()
