from datetime import date

import pandas as pd
import pytest

from enron_functional.absences import (backups, find_notices, merge_absences, nearest_year, notice_sentence,
                                       split_sentences,
                                       parse_window)

TUE = date(2001, 3, 13)  # a Tuesday


@pytest.mark.parametrize("sentence, sent, start, back", [
    # Lotus Notes wording: "until" is the day back
    ("I will be out of the office from 10/07/2000 until 10/15/2000.", date(2000, 10, 13),
     date(2000, 10, 7), date(2000, 10, 15)),
    ("I will be out of the office starting 05/01/2001 and will not return until 05/07/2001.", date(2001, 5, 1),
     date(2001, 5, 1), date(2001, 5, 7)),
    # "through" is the last day away
    ("I will be on vacation beginning Monday, 8/7, through Friday, 8/11.", date(2000, 8, 3),
     date(2000, 8, 7), date(2000, 8, 12)),
    ("Vacation Dec. 22 through Dec. 31", date(2001, 12, 28), date(2001, 12, 22), date(2002, 1, 1)),
    ("I will be out of the office from November 19 - November 28.", date(2001, 11, 19),
     date(2001, 11, 19), date(2001, 11, 29)),
    # weekdays resolve to the next one on or after the message date
    ("I will be out of the office Wednesday through Friday this week (March 15-17).", date(2000, 3, 14),
     date(2000, 3, 15), date(2000, 3, 18)),
    ("I will be out of the office tomorrow and Friday.", TUE, date(2001, 3, 14), date(2001, 3, 17)),
    ("I will be out Thur and Fri.", TUE, date(2001, 3, 15), date(2001, 3, 17)),
    ("I will be out Monday and Tuesday next week.", TUE, date(2001, 3, 19), date(2001, 3, 21)),
    # without a first day the absence starts on the message's date; the day back follows "returning"
    ("Ann is out of the office and will return on December 3.", date(2001, 11, 28),
     date(2001, 11, 28), date(2001, 12, 3)),
    ("I am out of the office until Tuesday December 18.", date(2001, 12, 14), date(2001, 12, 14),
     date(2001, 12, 18)),
    ("I will be out of the Tuesday, November 20, 2001 returning on November 26. 2001.", date(2001, 11, 21),
     date(2001, 11, 20), date(2001, 11, 26)),
    ("I'll be at the park for the duration of this week returing 11/26.", date(2001, 11, 20),
     date(2001, 11, 20), date(2001, 11, 26)),
    ("I will be out on vacation on Friday the 21st.", date(2001, 9, 21), date(2001, 9, 21), date(2001, 9, 22)),
    ("I will be out of the office on Monday11/12 but will work the rest of the week.", date(2001, 11, 7),
     date(2001, 11, 12), date(2001, 11, 13)),
    # a month and day without a year take the year nearest the message
    ("I will be out of the office and return on Monday, January 7.", date(2001, 12, 27),
     date(2001, 12, 27), date(2002, 1, 7)),
    # with no named day, "next week" is the week
    ("I will be on vacation next week.", TUE, date(2001, 3, 19), date(2001, 3, 24)),
])
def test_parse_window(sentence, sent, start, back):
    window = parse_window(sentence, sent)
    assert (window.reason, window.start, window.back) == ("", start, back)


@pytest.mark.parametrize("sentence, reason", [
    ("I will be out of the office on Friday afternoon.", "part day"),
    ("I will be on vacation that entire week.", "no date"),
    ("I will be out of the office starting Monday.", "no day back"),
])
def test_unusable_windows_say_why(sentence, reason):
    assert parse_window(sentence, TUE).reason == reason


def test_the_next_sentence_can_give_the_day_back():
    window = parse_window("I will be out of the office starting 5/1.", date(2001, 4, 30), "I will return on 5/7.")
    assert (window.start, window.back) == (date(2001, 5, 1), date(2001, 5, 7))


def test_a_stated_weekday_that_disagrees_with_the_date_is_flagged():
    assert parse_window("I will be out on Tuesday, March 15.", TUE).weekday_mismatch
    assert not parse_window("I will be out on Thursday, March 15.", TUE).weekday_mismatch


def test_nearest_year_skips_impossible_dates():
    assert nearest_year(2, 29, date(2001, 3, 1)) == date(2000, 2, 29)


@pytest.mark.parametrize("subject, text, kind", [
    ("Out of Office AutoReply: Storage", "Ann Lee is out of the office and will return on May 7.", "auto-reply"),
    ("Ann Lee/HOU/ECT is out of the office.", "I will be out of the office from 5/1/2001 until 5/7/2001.",
     "auto-reply"),
    ("Vacation", "Please be advised. I will be on vacation beginning 8/7 through 8/11.", "announcement"),
    ("Re: meeting", "Bob, I'm out of the office Thursday and Friday. Can we meet next week?", "announcement"),
])
def test_notices(subject, text, kind):
    assert notice_sentence(subject, text)[0] == kind


@pytest.mark.parametrize("text", [
    "I was out of the office last week, sorry for the delay.",
    "John is out of the office until Wednesday.",
    "I will be out there on Tuesday to see the plant.",
    "I am out of ideas on this one.",
    "I will figure out the numbers by Monday.",
])
def test_not_notices(text):
    assert notice_sentence("Re: storage", text) is None


PEOPLE = {"monica reasoner", "michael jones", "linda hallmark", "randy janzen", "patti thompson", "ann lee"}


@pytest.mark.parametrize("text, expected", [
    ("For all margin issues please contact Monica Reasoner at 713-853-9839.", ["monica reasoner"]),
    ("If you have something urgent, contact Michael B Jones or Linda Hallmark.", ["michael jones", "linda hallmark"]),
    ("In my absence Randy Janzen will be providing assistance to my customers.", ["randy janzen"]),
    ("My assistant, Patti Thompson, has my cell phone number.", ["patti thompson"]),
    ("Please contact Kim Alexander with any questions.", []),          # not a known person
    ("Please contact Ann Lee with any questions.", []),                # the absent person herself
])
def test_backups(text, expected):
    assert backups(text, PEOPLE, "ann lee")[0] == expected


SETTINGS = {"max_days_before_notice": 31, "max_days_after_notice": 62, "max_length_days": 31, "merge_gap_days": 1}


def message(path, when, subject, text, person="ann lee"):
    return {"path": path, "date": pd.Timestamp(when, tz="UTC"), "sender": "ann.lee@enron.com", "subject": subject,
            "authored": text, "to": [], "cc": [], "automated": False, "sender_person": person}


def test_notices_merge_into_absences_and_report_why_others_were_dropped():
    messages = pd.DataFrame([
        message("a/1", "2001-05-02 15:00", "Out of Office AutoReply: x", "I will be out until Monday, May 7."),
        message("a/2", "2001-05-03 15:00", "Out of Office AutoReply: y", "I will be out until Monday, May 7."),
        message("a/3", "2001-05-04 15:00", "Re: z", "I'll be out of the office May 7 and May 8. Thanks."),
        message("a/4", "2001-08-01 15:00", "Re: q", "I will be out of the office from 8/1 until 10/1."),
        message("a/5", "2001-08-01 15:00", "Re: q", "I will be out of the office Friday afternoon."),
        message("b/1", "2001-05-02 15:00", "Vacation", "I will be on vacation 5/14 through 5/18.", person=None),
    ])
    notices = find_notices(messages, PEOPLE, SETTINGS)
    assert notices.set_index("path")["status"].to_dict() == {
        "a/1": "kept", "a/2": "kept", "a/3": "kept", "a/4": "too long", "a/5": "part day",
        "b/1": "sender not a person"}
    absences = merge_absences(notices, SETTINGS["merge_gap_days"])
    assert len(absences) == 1
    row = absences.iloc[0]
    assert (row["start"], row["back"], row["days"], row["notices"], row["conflicting"]) == (
        pd.Timestamp("2001-05-02"), pd.Timestamp("2001-05-09"), 7, 3, True)


@pytest.mark.parametrize("sentence, sent, start, back", [
    ("I will also be on vacation Dec. 7 & 8.", date(2000, 12, 6), date(2000, 12, 7), date(2000, 12, 9)),
    ("I will be out of the office on Thursday and Friday Aug 2 & 3.", date(2001, 8, 1), date(2001, 8, 2),
     date(2001, 8, 4)),
])
def test_day_lists(sentence, sent, start, back):
    window = parse_window(sentence, sent)
    assert (window.reason, window.start, window.back) == ("", start, back)


def test_a_clock_time_range_is_part_of_a_day():
    assert parse_window("I will be out of the office tomorrow during the same time, 9:30 until 11.", TUE).reason \
        == "part day"
    assert parse_window("I will be out of the office from 5/30 - 6/1.", date(2001, 5, 29)).reason == ""


def test_sentences_split_for_lowercase_writers_but_not_after_date_abbreviations():
    assert split_sentences("kam, i appreciate it. i'll be in tomorrow. Back on Wed. 5/2 or Dec. 7.") == [
        "kam, i appreciate it.", "i'll be in tomorrow.", "Back on Wed. 5/2 or Dec. 7."]


def test_backups_across_phone_numbers():
    assert backups("Kelly Lombardi (5-8491) will be my backup while I am out.", {"kelly lombardi"}, "ann lee")[0] \
        == ["kelly lombardi"]
    assert backups("Please call Renee Ratcliff (713-345-7960) or Mary McKendree (713-345-8085).",
                   {"renee ratcliff", "mary mckendree"}, "ann lee")[0] == ["renee ratcliff", "mary mckendree"]


@pytest.mark.parametrize("sentence, sent", [
    ("I will be out of the office Wednesday morning November 15, 2000, for a brief appointment.", date(2000, 11, 14)),
    ("I will be out the afternoon of Friday, March 2 for my MRI.", date(2001, 2, 22)),
    ("I will be out of the office this afternoon, but will be back on Monday.", date(2001, 10, 26)),
])
def test_part_days_named_before_the_date_or_with_no_whole_day(sentence, sent):
    assert parse_window(sentence, sent).reason == "part day"


@pytest.mark.parametrize("sentence, sent, start, back", [
    ("I'm out Tues. and Weds.", date(1999, 10, 4), date(1999, 10, 5), date(1999, 10, 7)),
    ("I will be out of the office on Jan.2 but will be back on Wednesday.", date(2000, 12, 29), date(2001, 1, 2),
     date(2001, 1, 3)),
])
def test_abbreviations(sentence, sent, start, back):
    window = parse_window(sentence, sent)
    assert (window.reason, window.start, window.back) == ("", start, back)


def test_this_weekend_is_not_this_week():
    assert parse_window("I'll be out of town due to a family emergency this weekend.", date(2002, 1, 10)).reason \
        == "no date"


def test_weekdays_in_a_list_follow_the_day_before_them():
    window = parse_window("I will be out on Monday and Tuesday and will have to find a backup.", date(2000, 11, 14))
    assert (window.start, window.back) == (date(2000, 11, 20), date(2000, 11, 22))


@pytest.mark.parametrize("subject, text, expected", [
    ("Re: report", "I will be out tomorrow, so the next report will be Monday.", "I will be out tomorrow"),
    ("Re: holiday", "Covers trading for Saturday 11/24, Sunday 11/25, and Monday 11/26 As I mentioned, "
                    "I will be out of the office on Friday.", "I will be out of the office on Friday."),
    ("Re: x", "Tuesday I'll be out of pocket most of the day.", "Tuesday I'll be out of pocket most of the day."),
])
def test_announcements_are_dated_from_their_own_clause(subject, text, expected):
    assert notice_sentence(subject, text)[1] == expected


def test_weekend_only_absences_are_dropped():
    messages = pd.DataFrame([message("a/1", "2000-10-23 15:00", "Re: x",
                                     "I'm out of town Saturday, back on Sunday.")])
    assert find_notices(messages, PEOPLE, SETTINGS)["status"].tolist() == ["weekend only"]


def test_out_that_way_is_not_an_absence():
    assert notice_sentence("Re: x", "I might squeeze it in on Saturday b/c I will be out that way.") is None


def test_wilson_interval():
    from enron_functional.absence_check import wilson
    assert wilson(50, 50)[0] == pytest.approx(0.9287, abs=1e-4)
    assert wilson(0, 0) is None


@pytest.mark.parametrize("sentence, sent, follow, start, back", [
    # a week that comes first is the absence; days inside it are events during it
    ("I will be on vacation next week, but in my absence the conference call is still on Monday.",
     date(2001, 8, 2), "", date(2001, 8, 6), date(2001, 8, 11)),
    ("I plan to be on vacation next week and therefore will not be at the December 18th staff meeting.",
     date(2000, 12, 14), "", date(2000, 12, 18), date(2000, 12, 23)),
    # a week joined by "and" is part of the absence
    ("I will be out tomorrow and next week.", date(2001, 11, 15), "", date(2001, 11, 16), date(2001, 11, 24)),
    # "the 18th"
    ("I'll be on vacation this week and will return the 18th.", date(2001, 6, 11), "", date(2001, 6, 11),
     date(2001, 6, 18)),
    # a new action after "and will" is not read
    ("I am out of the office Thur and Friday and will get my permanent seat next week.", date(2001, 10, 2), "",
     date(2001, 10, 4), date(2001, 10, 6)),
    ("I am out of the office this week but will put a check in the mail next week.", date(2000, 8, 22), "",
     date(2000, 8, 22), date(2000, 8, 26)),
    # the day back from a following sentence, when it is within three days of the last day
    ("I will not be in the office on Friday, September 29.", date(2000, 9, 28),
     "Mary Cook will be able to handle any crises. I'll be back in the office on Monday.",
     date(2000, 9, 29), date(2000, 10, 2)),
    ("Ed will be out of the office through Friday, 3/08/02.", date(2002, 3, 6), "He will be back in Monday, 3/11/02.",
     date(2002, 3, 6), date(2002, 3, 11)),
    ("I will not be in the office on Friday, September 29.", date(2000, 9, 28),
     "Lunch is on Tuesday. I'll be back from the trip on October 20.", date(2000, 9, 29), date(2000, 9, 30)),
    # a weekday in parentheses after a return cue
    ("I will be back (Monday) January 21st from 6:30am to 10:00pm", date(2002, 1, 18), "", date(2002, 1, 18),
     date(2002, 1, 21)),
])
def test_round_one_patterns(sentence, sent, follow, start, back):
    window = parse_window(sentence, sent, follow)
    assert (window.reason, window.start, window.back) == ("", start, back)


def test_until_late_this_afternoon_is_part_of_a_day():
    assert parse_window("I am out until late this afternoon or tomorrow.", date(2001, 2, 15)).reason == "part day"


def test_cue_words_match_whole_words_only():
    from enron_functional.absences import RETURN, START, THROUGH
    assert RETURN.search("out until ") and not RETURN.search("the call is still on ")
    assert THROUGH.search("Monday to ") and not THROUGH.search("going into ")
    assert START.search("out from ")


def test_a_new_clause_after_and_want_is_not_read():
    window = parse_window("I'm out all next week and want to make sure this goes out before the baby is due on the "
                          "16th of Jan.", date(2000, 12, 21))
    assert (window.start, window.back) == (date(2000, 12, 25), date(2000, 12, 30))


def test_a_parenthesised_extension_does_not_end_a_sentence():
    assert split_sentences("Mary Cook (ext. 57732) will handle any crises. I'll be back on Monday.") == [
        "Mary Cook (ext. 57732) will handle any crises.", "I'll be back on Monday."]


@pytest.mark.parametrize("sentence, sent, follow, start, back", [
    ("I'll be on vacation starting Thursday, 20 December, returning Wednesday, January 2nd.", date(2001, 12, 27), "",
     date(2001, 12, 20), date(2002, 1, 2)),
    ("I shall be on vacation July 5, 6 and 9.", date(2001, 6, 25), "", date(2001, 7, 5), date(2001, 7, 10)),
    ("I will be out of the office for one half day on Friday and a full day on Monday.", date(2001, 6, 21), "",
     date(2001, 6, 25), date(2001, 6, 26)),
    ("Lunch this week would be difficult, as I'm out Thursday and Friday at a seminar in Dallas.", date(2001, 10, 22),
     "", date(2001, 10, 25), date(2001, 10, 27)),
    ("I will be out of the office attending a conference this week.", date(2001, 10, 22),
     "I will be back in the office on Thursday. Please contact Felicia.", date(2001, 10, 22), date(2001, 10, 25)),
    ("I'm gone through Wednesday of next week.", date(2000, 12, 20), "", date(2000, 12, 20), date(2000, 12, 28)),
    ("I'm out of the office until Wednesday next week.", date(2000, 3, 29), "", date(2000, 3, 29), date(2000, 4, 5)),
])
def test_round_two_patterns(sentence, sent, follow, start, back):
    window = parse_window(sentence, sent, follow)
    assert (window.reason, window.start, window.back) == ("", start, back)


def test_an_auto_reply_sent_on_its_own_day_back_has_no_absence_left():
    assert parse_window("I'm out of the office and will return on Thursday, December27th.",
                        date(2001, 12, 27)).reason == "no day back"


def test_the_remainder_of_the_day_is_part_of_a_day():
    assert parse_window("I will be out of the office the remainder of the day, and return tomorrow.",
                        date(2001, 3, 14)).reason == "part day"


def test_a_weekday_and_its_date_across_a_period_stay_together():
    sentences = split_sentences("I will be out of the office until Wednesday. January 2, 2002. Please call Kim.")
    assert sentences[0] == "I will be out of the office until Wednesday. January 2, 2002."
    window = parse_window(sentences[0], date(2001, 12, 20))
    assert (window.start, window.back) == (date(2001, 12, 20), date(2002, 1, 2))
