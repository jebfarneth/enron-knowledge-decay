"""Classify senders as people or automated/system mailboxes.

Two independent signals, both reported:

* Name rules: local parts such as no.reply, mailer-daemon, postmaster,
  announcements or administrators.
* Behaviour: a sender with at least `min_messages` messages, most of which
  reduce to one template once digits, dates and times are masked. Automated
  feeds (e.g. hourly scheduling notices) send the same text with changing
  numbers; people do not.
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
    return _SPACE.sub(" ", _DIGITS.sub("#", text.lower())).strip()[:500]


def name_rule(address) -> bool:
    local = (address if isinstance(address, str) else "").split("@")[0]
    return bool(_SYSTEM_LOCAL.search(local))


def sender_profiles(messages: pd.DataFrame, internal_domain: str, min_messages: int, template_share: float) -> pd.DataFrame:
    """One row per sender with volume, template share and the resulting flags.

    `messages` needs `sender` and `authored` (authored text) columns.
    """
    frame = messages.dropna(subset=["sender"])[["sender", "authored"]].copy()
    frame["template"] = frame["authored"].map(template_of)
    grouped = frame.groupby("sender")
    profiles = pd.DataFrame({
        "n_messages": grouped.size(),
        # Share of the sender's messages in their single most common template.
        "template_share": grouped["template"].agg(lambda t: t.value_counts(normalize=True).iloc[0]),
    })
    profiles["internal"] = profiles.index.str.endswith("@" + internal_domain)
    profiles["system_name"] = profiles.index.map(name_rule)
    profiles["templated"] = (profiles["n_messages"] >= min_messages) & (profiles["template_share"] >= template_share)
    profiles["automated"] = profiles["system_name"] | profiles["templated"]
    return profiles.sort_values("n_messages", ascending=False)
