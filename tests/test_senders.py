import pandas as pd

from enron_importance.senders import name_rule, sender_profiles, template_of


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
    profiles = sender_profiles(pd.DataFrame(feed + person), "enron.com", min_messages=50, template_share=0.5)
    assert profiles.loc["pete.davis@enron.com", "automated"]
    assert profiles.loc["pete.davis@enron.com", "template_share"] == 1.0
    assert not profiles.loc["jeff.dasovich@enron.com", "automated"]
    assert profiles["internal"].all()


def test_low_volume_senders_are_never_flagged_by_behaviour():
    rows = [{"sender": "x@enron.com", "authored": "same"}] * 10
    profiles = sender_profiles(pd.DataFrame(rows), "enron.com", min_messages=50, template_share=0.5)
    assert not profiles.loc["x@enron.com", "templated"]


def test_missing_values_do_not_fail():
    assert template_of(float("nan")) == ""
    assert not name_rule(float("nan"))
