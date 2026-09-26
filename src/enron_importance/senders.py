"""Flag automated, structured and routine messages.

Sender accounts are profiled with two signals, both reported:

* Name rules: local parts such as no.reply, mailer-daemon, postmaster,
  announcements or administrators.
* Behaviour (feed): a sender with at least `min_messages` messages containing
  text, of which at least `feed_share` fall into their `top_templates` most
  common templates once digits are masked (e.g. hourly scheduling notices).
  Messages with no authored text (pure forwards) are not counted, so frequent
  forwarders are not mistaken for feeds.

Automation is then decided per message, not per account: every message from
a name-rule account is automated, but from a feed account only the messages
whose template repeats are. A person whose address also sends alerts (Pete
Davis and the Schedule Crawler) keeps the messages they wrote themselves.

Two further message-level flags:

* structured: machine records rather than prose, whoever sent them
  (calendar entries, task and report notifications, payroll receipts,
  performance-review notices, leave requests, self-declared automated
  e-mails, mailbox synchronization logs), and copied newsletters (their
  "daily service of" and unsubscribe markers). A fixed list of formats: it
  misses formats not listed.
* signature only: the authored text is nothing but the sender's own
  signature block (optionally after a sign-off such as "Cordially,"): a
  name line containing the sender's name, then title, department, company,
  address, phone or e-mail lines.
* routine: the sender sends the same whole text (digits masked) at least
  `routine_repeats` times; a shared opening is not enough. Routine messages
  stay in the network. They leave the text analysis only when longer than
  `speech_act_words` words, counted over the whole message after dropping an
  addressee line and a short sign-off; short repeated utterances such as
  "approved", "please print" or "will do" are speech acts and are kept.

These are heuristic flags, not a validated classifier.
"""

from __future__ import annotations

import re

import pandas as pd

_SYSTEM_LOCAL = re.compile(
    r"(^|[._-])(no[._-]?reply|noreply|do[._-]?not[._-]?reply|mailer[._-]?daemon|daemon|postmaster|"
    r"announce(ments)?|administrator|admin|bounce[s]?|newsletter|listserv|majordomo|"
    r"helpdesk|help[._-]desk|system|notification[s]?|alert[s]?|mailbox)([._-]|$)",
    re.IGNORECASE,
)
_DIGITS = re.compile(r"\d+")
_SPACE = re.compile(r"\s+")
# A leading addressee line in capitals ("ALLEN, PHILLIP K,") or "Dear ...":
# personalized notices differ only here.
_SALUTATION = re.compile(r"^\s*(?:Dear [^\n]{1,40}|[A-Z][A-Z .,'-]{2,40})[,:][ \t]*\n")
STRUCTURED = re.compile(
    r"^\s*(?:[A-Z][a-z]{2} \d{1,2}, \d{4}\s*)?"  # optional date line before a notice
    r"(?:CALENDAR ENTRY\b|Task Assignment|The report named:|Employee ID:|Thank you for changing lives"
    r"|\d{1,2}:\d{2}:\d{2} Synchronizing|This (?:is|in) an automated (?:e-?mail|message|notification)"
    r"|Requester:[^\n]*\n\s*Request Type:"
    r"|You have been selected to participate in .{0,40}Performance|YEAR END \d{4} PERFORMANCE EVALUATION"
    r"|NOTE:\s+YOU WILL RECEIVE THIS MESSAGE EACH TIME|Please note that your employees have suggested"
    r"|Attached below you will find the final Evaluation forms"
    r"|According to our system records, you have not yet logged)",
    re.IGNORECASE,
)


def template_of(text) -> str:
    """Mask numbers, drop a capitalized addressee line and collapse whitespace."""
    text = text if isinstance(text, str) else ""
    text = _SALUTATION.sub("", text, count=1)
    return _SPACE.sub(" ", _DIGITS.sub("#", text.lower())).strip()[:80]


# Copied newsletters and mailing-list digests, wherever the markers appear.
# Strong markers identify a newsletter anywhere; an unsubscribe or "you are receiving this" line
# counts only in a link-heavy message, since mailing-list conversations carry the same footer.
NEWSLETTER = re.compile(r"this e-?mail is a (daily|weekly) service of|was forwarded to you by a colleague", re.IGNORECASE)
LIST_FOOTER = re.compile(r"to unsubscribe|unsubscribe from this|you are receiving this (e-?mail|newsletter|message) because",
                         re.IGNORECASE)
_URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.IGNORECASE)  # one match per whole link


def structured_record(text) -> bool:
    """True for machine-generated records (calendar entries, notices) and copied newsletters rather than prose."""
    if not isinstance(text, str):
        return False
    return bool(STRUCTURED.search(_SALUTATION.sub("", text, count=1)) or NEWSLETTER.search(text)
                or (LIST_FOOTER.search(text) and len(_URL.findall(text)) >= 3))


_PHONE = re.compile(r"\(?\d{3}\)?[\s.-]*\d{3}[\s.-]\d{4}|\b(phone|fax|tel|cell|mobile|pager|direct)\b", re.IGNORECASE)
_SIGNATURE_WORDS = {
    "coordinator", "director", "manager", "assistant", "analyst", "specialist", "counsel", "attorney",
    "president", "vp", "vice", "associate", "senior", "sr", "executive", "officer", "affairs", "government",
    "department", "legal", "corp", "corporation", "inc", "enron", "suite", "street", "houston", "texas",
    "floor", "administrative", "services", "group", "global", "north", "america", "americas", "llc",
}


_SIGN_OFF = re.compile(r"^(cordially|regards|best regards|kind regards|sincerely|respectfully|best|cheers)[,.!]?$", re.IGNORECASE)


def signature_only(text, sender_names=None) -> bool:
    """True when the text is only a signature block.

    The block may open with a sign-off ("Cordially,"); its first other line
    must be a name line of two to four capitalized words that, when
    `sender_names` is given, contains two of the sender's own name words
    (first and last name), so another person's contact block is not the
    sender's signature. Every later line must be short: a name, title,
    department, company, address, phone or e-mail line, with at least one
    phone, e-mail, address or title line; a "label: value" line other than a
    phone or e-mail line is a form field, not a signature. Anything before
    the block ("Not I.", "Done :)") or a sentence that happens to contain a
    phone number means it is not a signature. A roster that opens with the
    sender's own name can still pass.
    """
    lines = [line.strip() for line in (text if isinstance(text, str) else "").splitlines() if line.strip()]
    while lines and _SIGN_OFF.match(lines[0]):
        lines = lines[1:]
    if len(lines) < 2:
        return False
    first = re.findall(r"\b[A-Za-z][A-Za-z.'-]*", lines[0])
    if not 2 <= len(first) <= 4 or not all(w[0].isupper() for w in first) or re.search(r"[:;!?()\d\t]", lines[0]):
        return False
    if sender_names is not None and len({w.lower().strip(".'") for w in first} & set(sender_names)) < 2:
        return False
    evidence = False
    for line in lines[1:]:
        words = re.findall(r"\b[A-Za-z][A-Za-z.&'-]*", line)
        if len(words) > 8:
            return False
        if _PHONE.search(line) or "@" in line:
            evidence = True
            continue
        if ":" in line:
            return False  # a form field ("Supervisor: ..."), not a signature line
        if len(words) > 6 or not all(w[0].isupper() for w in words):
            return False
        if {w.lower().strip(".") for w in words} & _SIGNATURE_WORDS or re.search(r"\d+\s+\w+", line):
            evidence = True
    return evidence


def name_rule(address) -> bool:
    local = (address if isinstance(address, str) else "").split("@")[0]
    return bool(_SYSTEM_LOCAL.search(local))


def sender_profiles(messages: pd.DataFrame, internal_domain: str, min_messages: int, feed_share: float,
                    top_templates: int = 3) -> pd.DataFrame:
    """One row per sender with volume, template share and the resulting flags.

    `messages` needs `sender` and `authored` (authored text) columns.
    template_share = share of the sender's text-bearing messages covered by
    their `top_templates` most common templates.
    """
    frame = messages.dropna(subset=["sender"])[["sender", "authored"]].copy()
    frame["template"] = frame["authored"].map(template_of)
    counts = frame.groupby("sender").size().rename("n_messages")
    texts = frame[frame["template"] != ""]
    grouped = texts.groupby("sender")["template"]
    profiles = pd.DataFrame(counts)
    profiles["n_with_text"] = grouped.size().reindex(profiles.index, fill_value=0)
    share = grouped.agg(lambda t: t.value_counts(normalize=True).iloc[:top_templates].sum())
    profiles["template_share"] = share.reindex(profiles.index, fill_value=0.0)
    profiles["internal"] = profiles.index.str.endswith("@" + internal_domain)
    profiles["system_name"] = profiles.index.map(name_rule)
    profiles["feed"] = (profiles["n_with_text"] >= min_messages) & (profiles["template_share"] >= feed_share)
    profiles["automated"] = profiles["system_name"] | profiles["feed"]
    return profiles.sort_values("n_messages", ascending=False)


def full_template(text) -> str:
    """Like `template_of` but over the whole message, not only its opening."""
    text = text if isinstance(text, str) else ""
    text = _SALUTATION.sub("", text, count=1)
    return _SPACE.sub(" ", _DIGITS.sub("#", text.lower())).strip()


def _repeats(messages: pd.DataFrame, template=template_of) -> tuple[pd.Series, pd.Series]:
    """Each message's template and how often its sender uses that template."""
    templates = messages["authored"].map(template)
    keyed = messages["sender"].map(lambda s: s if isinstance(s, str) else "") + "\x1f" + templates
    return templates, keyed.map(keyed.value_counts())


def automated_messages(messages: pd.DataFrame, profiles: pd.DataFrame) -> pd.Series:
    """Every message from a name-rule account; from a feed account, only repeated templates."""
    templates, repeats = _repeats(messages)
    system = messages["sender"].isin(profiles.index[profiles["system_name"]])
    feed = messages["sender"].isin(profiles.index[profiles["feed"]])
    return system | (feed & ((repeats >= 2) | (templates == "")))


def routine_messages(messages: pd.DataFrame, min_repeats: int) -> pd.Series:
    """True for messages whose whole text the same sender sends at least `min_repeats` times."""
    templates, repeats = _repeats(messages, full_template)
    return (templates != "") & (repeats >= min_repeats)


def utterance_words(text) -> int:
    """Words in a message after dropping an addressee line and a short sign-off ("Thanks, / DF")."""
    lines = [line for line in _SALUTATION.sub("", text if isinstance(text, str) else "", count=1).splitlines()
             if line.strip()]
    for _ in range(3):  # sign-off lines of at most three words at the end
        if len(lines) > 1 and len(lines[-1].split()) <= 3:
            lines.pop()
    return len(" ".join(lines).split())


def speech_act(text, max_words: int) -> bool:
    """Short utterances ("approved", "please print") that stay in text analysis even when repeated."""
    return 0 < utterance_words(text) <= max_words
