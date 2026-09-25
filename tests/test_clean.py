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


def test_missing_body_from_parquet_is_empty():
    assert authored_text(float("nan")) == ""
    assert not has_quoted_material(None)


# Formats found in the corpus that the first version of the cleaner missed.
FROM_ON = "That's a better idea.  df\n\nFrom:\tLouis Soldano/ENRON@enronXgate on 03/30/2001 07:45 AM\nTo:\tDrew Fossum/ET&S/Enron@ENRON\ncc:\nSubject: Re: filing\n\nold text\n"
NAME_DATE = "How bout 1?  Thanks. DF\n\nDavid Foti\n02/02/2000 05:44 PM\nTo: Drew Fossum/ET&S/Enron@ENRON\ncc: James Centilli/ET&S/Enron@ENRON\nSubject: meeting\n\nold text\n"
EXTERNAL_ON = "Lee,\n\nAny problem with that approach?\n\nKay\n\nlee.johnson@ss.ps.ge.com on 12/18/2000 07:02:45 AM\nTo: peterthompson@akllp.com, kay.mann@enron.com\ncc: lee.johnson@ss.ps.ge.com\nSubject: guarantee\n\nold text\n"


def test_from_line_with_on_date_is_cut():
    assert authored_text(FROM_ON) == "That's a better idea.  df"


def test_name_line_then_date_line_is_cut():
    assert authored_text(NAME_DATE) == "How bout 1?  Thanks. DF"


def test_external_address_on_date_is_cut():
    assert authored_text(EXTERNAL_ON) == "Lee,\n\nAny problem with that approach?\n\nKay"

FROM_WITH_DATE = ("to take on more responsibility\n\n-e\n\n\tEnron North America Corp.\n\t\n"
                  "\tFrom:  Shanna Husser @ EES                           01/26/2001 09:29 AM\n\n"
                  "To: Eric Bass/HOU/ECT@ECT\ncc:  \nSubject: \n\nold text\n")
BARE_HEADER = "fill me in.  how can i eavesdrop??\n\nTo: John Arnold/HOU/ECT@ECT\ncc:  \nSubject: Re: NG\n\nold text\n"


def test_from_line_with_date_and_company_banner_is_cut():
    assert authored_text(FROM_WITH_DATE) == "to take on more responsibility\n\n-e"


def test_bare_to_cc_subject_block_is_cut():
    assert authored_text(BARE_HEADER) == "fill me in.  how can i eavesdrop??"


# Cases where the independent email_reply_parser cross-check was right.
YAHOO_FOOTER = ("Please reply to this test message.\n\nMany Thanks!\nLisa Scully\n\n"
                "__________________________________________________\nDo You Yahoo!?\nGet personalized email addresses from Yahoo! Mail\n")
INLINE_ATTACHMENT = "See the quotes below.\n\n--------- Inline attachment follows ---------\n\nFrom:  \nTo: vkaminski@aol.com\nSubject:  \n\nold\n"
RAW_HEADERS = "fyi\n\nReturn-path: <info@winebid.com>\nReceived: from mta1.example.net by sims1\nContent-transfer-encoding: 7bit\n\nold\n"
DAY_FIRST = "I will pick it up when I check your list.\n\nFrom: Tana Jones@ECT on 17-08-2000 09:10 CDT\nTo: Mark Taylor\nSubject: list\n\nold\n"


def test_webmail_ad_footer_is_removed():
    assert authored_text(YAHOO_FOOTER) == "Please reply to this test message.\n\nMany Thanks!\nLisa Scully"


def test_inline_attachment_block_is_cut():
    assert authored_text(INLINE_ATTACHMENT) == "See the quotes below."


def test_raw_transport_headers_are_cut():
    assert authored_text(RAW_HEADERS) == "fyi"


def test_day_first_from_line_is_cut():
    assert authored_text(DAY_FIRST) == "I will pick it up when I check your list."


def test_underscore_separator_without_an_ad_is_kept():
    body = "Agenda\n____________________\n1. Budget\n2. Hiring"
    assert authored_text(body) == body


# Negative controls from the 2026-09-25 audit: authored prose that resembles a header.
def test_prose_starting_with_received_from_is_kept():
    body = "Received: from supplier, 20 barrels.\nPlease book them against the March deal."
    assert authored_text(body) == body


def test_agenda_with_a_date_and_to_line_is_kept():
    body = "Meeting agenda\n05/14/2001 09:00 AM\nTo: operations staff\nWe will review the outage plan and staffing."
    assert authored_text(body) == body


def test_spanish_original_message_separator_is_cut():
    body = "De acuerdo, gracias.\n\n-----Mensaje original-----\nDe: Sara\nPara: Juan\nAsunto: contrato\n\nold"
    assert authored_text(body) == "De acuerdo, gracias."


def test_name_and_date_on_one_line_is_cut():
    body = ("Just allocate the actuals at the end of each month.\n\nD\n\n\n"
            "   Aimee Lannou                03/11/2000 09:49 AM\n\nTo: Daren J Farmer/HOU/ECT@ECT\ncc:\nSubject: Re: Allocation\n\nold\n")
    assert authored_text(body) == "Just allocate the actuals at the end of each month.\n\nD"


def test_wrapped_to_list_before_cc_and_subject_is_cut():
    body = ("Who the heck is Mirant Corp????\n\nJulie\n\n\nJohn Hodge@ENRON\n02/06/2001 11:58 AM\n"
            "To: Ruth Concannon/HOU/ECT@ECT, Frank W Vickers/NA/Enron@Enron, Gil \nMuhl/Corp/Enron@ENRON, Phil DeMoes/Corp/Enron@ENRON, David \n"
            "Jones/NA/Enron@ENRON, Robin Barbe/HOU/ECT@ECT\ncc:  \nSubject: Iroquois\n\nold text\n")
    assert authored_text(body) == "Who the heck is Mirant Corp????\n\nJulie"


def test_sent_by_line_and_wrapped_recipients_are_cut():
    body = ("I do not have an EZ tag.\n\n\n\tParking & Transportation@ENRON\n\tSent by: DeShonda Hamilton@ENRON\n"
            "\t04/03/2001 09:31 AM\n\t\t \n\t\t To: John Letvin/Enron@EnronXGate, Becky \nYoung/NA/Enron@Enron, Bob \n"
            "Hillier/Enron@enronXgate\n\t\t cc: Louis Allen/EPSC/HOU/ECT@ECT\n\t\t Subject: EZ Tags\n\nold text\n")
    assert authored_text(body) == "I do not have an EZ tag."
