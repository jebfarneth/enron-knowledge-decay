"""Reconstruct candidate reply links and threads.

Enron headers carry no In-Reply-To or References fields, so replies are
inferred. Message m is linked to an earlier message p when:

1. p and m have the same non-empty normalized subject (Re:/Fw: removed),
2. m's sender was a recipient (To/Cc) of p,
3. p was sent before m, within `max_reply_days`,
4. there is direct evidence of a reply: m is addressed back to p's sender,
   or m's quoted text contains the opening of p's authored text,
5. p does not itself quote m's authored text (that would make p the reply),

and p is the latest such message. Automated messages and structured records
(alerts, digests, calendar entries) are never linked. `link_evidence` records
which of the two kinds of evidence in rule 4 held.

These are inferred candidate parents, not observed replies: a sample review
of the earlier rule found many wrong parents, and messages with empty
subjects or changed subjects are not linked. `response_seconds` is the delay
to the inferred parent. A thread is the connected set of messages joined by
links.
"""

from __future__ import annotations

import re

import pandas as pd

from .clean import reply_start
from .dedupe import normalize_subject

_SPACE = re.compile(r"\s+")
PREFIX_CHARS = 60   # opening of a message's authored text used to recognise it when quoted
MIN_PREFIX_CHARS = 20


def _flat(text) -> str:
    return _SPACE.sub(" ", text if isinstance(text, str) else "").strip().lower()


def _prefix(authored) -> str | None:
    text = _flat(authored)[:PREFIX_CHARS]
    return text if len(text) >= MIN_PREFIX_CHARS else None


def link_replies(messages: pd.DataFrame, max_reply_days: int, eligible: pd.Series | None = None) -> pd.DataFrame:
    """Add reply_to (index of the inferred parent), link_evidence, response_seconds and thread_id.

    `messages` needs sender, to, cc, subject and date, and body and authored
    for quotation evidence (either may be absent). `eligible` marks messages
    that may be linked at all. The index must be unique.
    """
    frame = messages.copy()
    frame["_subject"] = frame["subject"].map(normalize_subject)
    frame["reply_to"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    frame["link_evidence"] = pd.Series([None] * len(frame), index=frame.index, dtype=object)
    frame["response_seconds"] = pd.array([pd.NA] * len(frame), dtype="Float64")
    bodies = frame["body"] if "body" in frame else pd.Series("", index=frame.index)
    authored = frame["authored"] if "authored" in frame else bodies
    window = pd.Timedelta(days=max_reply_days)
    candidates = frame["_subject"] != ""
    if eligible is not None:
        candidates &= eligible.reindex(frame.index, fill_value=False)

    for _, group in frame[candidates].groupby("_subject", sort=False):
        if len(group) < 2:
            continue
        group = group.sort_values("date", kind="stable")
        earlier: list[tuple] = []  # (index, date, sender, recipients, prefix, flat body)
        for index, row in group.iterrows():
            sender = row["sender"]
            addressed_to = set(row["to"]) | set(row["cc"])
            body = bodies[index] if isinstance(bodies[index], str) else ""
            quoted = _flat(body[reply_start(body):])
            own = _prefix(authored[index])
            for prior_index, prior_date, prior_sender, recipients, prior_prefix, prior_body in reversed(earlier):
                if row["date"] - prior_date > window:
                    break
                if not sender or sender not in recipients or prior_date >= row["date"]:
                    continue
                if own and len(own) >= 2 * MIN_PREFIX_CHARS and own in prior_body:
                    continue  # the earlier message already quotes this one
                evidence = [name for name, held in [
                    ("addressed", prior_sender in addressed_to),
                    ("quoted", bool(prior_prefix) and prior_prefix in quoted),
                ] if held]
                if not evidence:
                    continue
                frame.at[index, "reply_to"] = prior_index
                frame.at[index, "link_evidence"] = "+".join(evidence)
                frame.at[index, "response_seconds"] = (row["date"] - prior_date).total_seconds()
                break
            earlier.append((index, row["date"], sender, addressed_to, _prefix(authored[index]), _flat(body)))

    frame["thread_id"] = _thread_ids(frame)
    return frame.drop(columns="_subject")


def _thread_ids(frame: pd.DataFrame) -> pd.Series:
    """Union-find over reply links; a message's thread is its root's index."""
    parent = {index: index for index in frame.index}

    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for index, prior in frame["reply_to"].dropna().items():
        a, b = root(index), root(int(prior))
        if a != b:
            parent[max(a, b)] = min(a, b)
    return pd.Series({index: root(index) for index in frame.index}, dtype="int64")
