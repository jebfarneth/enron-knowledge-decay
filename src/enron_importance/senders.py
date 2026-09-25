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
  performance-review notices, mailbox synchronization logs).
* routine: the sender repeats the same template at least `routine_repeats`
  times. Routine messages stay in the network. They leave the text analysis
  only when longer than `speech_act_words` words (reports, signature-only
  forwards); short repeated utterances such as "approved", "please print" or
  "will do" are speech acts and are kept.

These are heuristic flags, not a validated classifier.
"""

from __future__ import annotations

import re

import pandas as pd

_SYSTEM_LOCAL = re.compile(
    r"(^|[._-])(no[._-]?reply|noreply|do[._-]?not[._-]?reply|mailer[._-]?daemon|postmaster|"
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
    r"^\s*(?:CALENDAR ENTRY:|Task Assignment|The report named:|Employee ID:|Thank you for changing lives"
    r"|\d{1,2}:\d{2}:\d{2} Synchronizing|You have been selected to participate in the .{0,40}Performance"
    r"|Attached below you will find the final Evaluation forms|According to our system records, you have not yet logged)",
    re.IGNORECASE,
)


def template_of(text) -> str:
    """Mask numbers, drop a capitalized addressee line and collapse whitespace."""
    text = text if isinstance(text, str) else ""
    text = _SALUTATION.sub("", text, count=1)
    return _SPACE.sub(" ", _DIGITS.sub("#", text.lower())).strip()[:80]


def structured_record(text) -> bool:
    """True for machine-generated records (calendar entries, notices) rather than prose."""
    return isinstance(text, str) and bool(STRUCTURED.search(_SALUTATION.sub("", text, count=1)))


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


def _repeats(messages: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Each message's template and how often its sender uses that template."""
    templates = messages["authored"].map(template_of)
    keyed = messages["sender"].map(lambda s: s if isinstance(s, str) else "") + "\x1f" + templates
    return templates, keyed.map(keyed.value_counts())


def automated_messages(messages: pd.DataFrame, profiles: pd.DataFrame) -> pd.Series:
    """Every message from a name-rule account; from a feed account, only repeated templates."""
    templates, repeats = _repeats(messages)
    system = messages["sender"].isin(profiles.index[profiles["system_name"]])
    feed = messages["sender"].isin(profiles.index[profiles["feed"]])
    return system | (feed & ((repeats >= 2) | (templates == "")))


def routine_messages(messages: pd.DataFrame, min_repeats: int) -> pd.Series:
    """True for messages whose template the same sender sends at least `min_repeats` times."""
    templates, repeats = _repeats(messages)
    return (templates != "") & (repeats >= min_repeats)


def speech_act(text, max_words: int) -> bool:
    """Short utterances ("approved", "please print") that stay in text analysis even when repeated."""
    return 0 < len(template_of(text).split()) <= max_words
