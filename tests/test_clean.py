from enron_importance.clean import authored_text, has_quoted_material

OUTLOOK = """Sounds good, send me the curve by 3pm.

Thanks,
Tim

 -----Original Message-----
From: \tAllen, Phillip K.
Sent:\tMonday, May 14, 2001 4:39 PM
To:\tBelden, Tim
Subject:\tWest desk

Here is our forecast.
"""

LOTUS_FORWARD = """FYI - see below.

---------------------- Forwarded by Jeff Dasovich/NA/Enron on 05/14/2001 04:39 PM ---------------------------

Susan Mara
05/14/2001 01:02 PM
To: Jeff Dasovich/NA/Enron@Enron
Subject: CPUC agenda
"""

LOTUS_REPLY = """Agreed. Let's hold the price.

Kay Mann@ENRON
05/14/2001 09:15 AM
To: Mark Taylor/HOU/ECT@ECT
cc:
Subject: Turbine contract

Can you review section 4?
"""

ANGLE = """Yes, approved.
> Can I book the trade?
> Thanks
"""

DISCLAIMER = """Please call me tomorrow.

**********************************************************************
This e-mail is the property of Enron Corp. and/or its relevant affiliate and may contain confidential and privileged material.
**********************************************************************
"""


def test_outlook_reply_keeps_only_the_new_text():
    assert authored_text(OUTLOOK) == "Sounds good, send me the curve by 3pm.\n\nThanks,\nTim"
    assert has_quoted_material(OUTLOOK)


def test_lotus_forward_keeps_only_the_note():
    assert authored_text(LOTUS_FORWARD) == "FYI - see below."


def test_lotus_reply_header_block_is_cut():
    assert authored_text(LOTUS_REPLY) == "Agreed. Let's hold the price."


def test_angle_bracket_quotes_are_removed():
    assert authored_text(ANGLE) == "Yes, approved."


def test_enron_disclaimer_is_removed():
    assert authored_text(DISCLAIMER) == "Please call me tomorrow."


def test_plain_message_is_unchanged_and_not_flagged():
    body = "Meeting moved to 3pm in EB 3321.\n\nKay"
    assert authored_text(body) == body
    assert not has_quoted_material(body)


def test_pure_forward_has_no_authored_text():
    body = "---------------------- Forwarded by A/HOU/ECT on 01/02/2001 10:00 AM ---------------------------\nold text"
    assert authored_text(body) == ""
