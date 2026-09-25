"""Estimate the text a sender wrote, separating it from quoted, forwarded and boilerplate text.

Topic and dialog-act models must only see what the sender authored; otherwise
a reply is credited with the words of everyone earlier in the thread. Enron
mail mixes three reply formats, all handled here:

* Outlook:      "-----Original Message-----" followed by From/Sent/To/Subject
* Lotus Notes:  "---- Forwarded by Name/HOU/ECT on 05/14/2001 04:39 PM ----",
                or a "Name@ENRON" / date / "To:" / "cc:" / "Subject:" block
* Plain text:   lines starting with ">"

The authored part is everything before the earliest reply marker, with ">"
lines, known legal disclaimers and webmail footers removed. This is an
estimate of top-posted text, not verified authorship: answers written inline
inside a quoted message are lost, header formats not listed here are kept,
and signatures and pasted documents stay in (see the 2026-09-25 audit).
"""

from __future__ import annotations

import re

_MARKERS = [
    # Outlook reply/forward separator.
    re.compile(r"^\s*-{2,}\s*(?:Original Message|Mensaje original|Message d'origine|Urspr\u00fcngliche Nachricht)\s*-{2,}",
               re.IGNORECASE | re.MULTILINE),
    # Lotus Notes forward banner.
    re.compile(r"^\s*-{3,}\s*Forwarded by .*$", re.IGNORECASE | re.MULTILINE),
    # Outlook-style header block quoted inline ("From: x" then "Sent:" within two lines).
    re.compile(r"^\s*From:\s.*\n(?:.*\n){0,2}?\s*Sent:\s", re.IGNORECASE | re.MULTILINE),
    # Lotus Notes reply header: a name or address line, a date line, To:, then
    # cc: or Subject: ("Kay Mann@ENRON" / "05/22/2001 03:03 PM" / "To:" / "cc:").
    re.compile(
        r"^[^\n]{1,80}\n\s*\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}(?::\d{2})? ?[AP]M\s*\n(?:.*\n){0,2}?\s*To:[^\n]*\n"
        r"(?:.*\n){0,2}?\s*(?:cc|Subject):",
        re.MULTILINE,
    ),
    # Single-line variant: "Name/ENRON@enronXgate on 03/30/2001 07:45 AM" or
    # "From: X on 12/18/2000 07:02:45 AM", then To:.
    re.compile(
        r"^[^\n]{1,160}\bon \d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}(?::\d{2})? ?[AP]M\s*\n(?:.*\n){0,1}?\s*To:\s",
        re.MULTILINE,
    ),
    # "From:  Name @ EES      01/26/2001 09:29 AM" (date on the From line), then To:,
    # optionally preceded by an indented company banner such as "Enron North America Corp.".
    re.compile(
        r"^(?:[ \t]+[A-Z][^\n]{0,60}(?:Corp\.|Inc\.|LLC|Ltd\.)[ \t]*\n(?:[ \t]*\n)*)?[ \t]*From:[^\n]*\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}(?::\d{2})? ?[AP]M[ \t]*\n(?:[ \t]*\n)*[ \t]*To:\s",
        re.MULTILINE,
    ),
    # Name and date on one line ("   Aimee Lannou      03/11/2000 09:49 AM"), then To:.
    re.compile(
        r"^[ \t]*[A-Za-z][^\n]{0,80}?[ \t]{2,}\d{1,2}/\d{1,2}/\d{2,4} \d{1,2}:\d{2}(?::\d{2})? ?[AP]M[ \t]*\n(?:[ \t]*\n)*[ \t]*To:\s",
        re.MULTILINE,
    ),
    # Bare quoted header block with no name line: "To:" then "cc:" then "Subject:".
    re.compile(r"^[ \t]*To:[^\n]*\n[ \t]*cc:[^\n]*\n(?:[ \t]*\n)*[ \t]*Subject:", re.IGNORECASE | re.MULTILINE),
    # Inline forwarded message: "--------- Inline attachment follows ---------".
    re.compile(r"^[ \t]*-{3,}\s*Inline attachment follows\s*-{3,}", re.IGNORECASE | re.MULTILINE),
    # Raw mail transport headers pasted into a body (a forwarded raw message).
    # Two consecutive header lines are required, so prose such as
    # "Received: from supplier, 20 barrels." is not cut.
    re.compile(r"^(?:Received: from |Return-path: |Content-transfer-encoding: )[^\n]*\n[A-Za-z-]+: \S",
               re.IGNORECASE | re.MULTILINE),
    # "From: Name@ECT on 17-08-2000 09:10 CDT" (day-first date, 24-hour time, zone).
    re.compile(r"^[ \t]*From:[^\n]*\bon \d{1,2}[-/.]\d{1,2}[-/.]\d{2,4} \d{1,2}:\d{2}(?::\d{2})?(?: ?[AP]M)?(?: [A-Z]{2,4})?[ \t]*$", re.MULTILINE),
    # "On <date>, <name> wrote:"
    re.compile(r"^\s*On .{5,120}wrote:\s*$", re.IGNORECASE | re.MULTILINE),
]

# Disclaimers appended by Enron and counterparties; removed wherever they occur.
_DISCLAIMERS = [
    re.compile(
        r"\*{5,}\s*This e-?mail is the property of Enron Corp\..*?(?:\*{5,}|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"This (?:e-?mail|message)(?: and any attachments)? (?:is|are|may be) (?:confidential|privileged).*?(?:\n\s*\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    ),
]
# Webmail advertising footers appended by the sender's mail provider.
_PROVIDER_FOOTERS = re.compile(
    r"\n[ \t]*_{10,}[ \t]*\n(?:[^\n]*\n){0,3}?[^\n]*(?:Do You Yahoo!\?|Get your FREE download of MSN|MSN Explorer|Hotmail\.com|Get Your Private, Free E-?mail|AOL Instant Messenger)[\s\S]*$",
    re.IGNORECASE,
)
_QUOTED_LINE = re.compile(r"^\s*>.*$\n?", re.MULTILINE)
_BLANK_RUNS = re.compile(r"\n\s*\n(\s*\n)+")


def reply_start(body: str) -> int:
    """Character offset where quoted/forwarded material begins (len(body) if none)."""
    starts = [m.start() for pattern in _MARKERS if (m := pattern.search(body))]
    return min(starts, default=len(body))


def authored_text(body) -> str:
    """The part of `body` written by the sender of this message."""
    body = (body if isinstance(body, str) else "").replace("\r\n", "\n").replace("\r", "\n")
    text = body[: reply_start(body)]
    text = _PROVIDER_FOOTERS.sub("\n", text)
    for pattern in _DISCLAIMERS:
        text = pattern.sub("", text)
    text = _QUOTED_LINE.sub("", text)
    text = _BLANK_RUNS.sub("\n\n", text)
    return text.strip()


def has_quoted_material(body) -> bool:
    body = body if isinstance(body, str) else ""
    return reply_start(body) < len(body) or bool(_QUOTED_LINE.search(body))
