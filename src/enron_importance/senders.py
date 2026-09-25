"""Classify senders as people or automated/system mailboxes.

Two independent signals, both reported:

* Name rules: local parts such as no.reply, mailer-daemon, postmaster,
  announcements or administrators.
* Behaviour: a sender with at least `min_messages` messages containing text,
  nearly all of which (`feed_share`) fall into a few templates once digits
  are masked. Automated feeds (e.g. hourly scheduling notices) repeat a
  handful of texts with changing numbers; people do not. Messages with no
  authored text (pure forwards) are excluded, so frequent forwarders are not
  mistaken for feeds.

People who also send routine reports (weekly lists, report links) are kept;
only their repeated messages are marked routine (see `routine_messages`).
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


def template_of(text) -> str:
    """Mask numbers and collapse whitespace so templated messages compare equal."""
    text = text if isinstance(text, str) else ""
    return _SPACE.sub(" ", _DIGITS.sub("#", text.lower())).strip()[:80]


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


def routine_messages(messages: pd.DataFrame, min_repeats: int) -> pd.Series:
    """True for messages whose template the same sender sends at least `min_repeats` times."""
    templates = messages["authored"].map(template_of)
    keyed = messages["sender"].map(lambda s: s if isinstance(s, str) else "") + "\x1f" + templates
    repeats = keyed.map(keyed.value_counts())
    return (templates != "") & (repeats >= min_repeats)
