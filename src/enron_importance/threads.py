"""Reconstruct candidate reply links and threads.

Enron headers carry no In-Reply-To or References fields, so links are
inferred. An earlier message p is a candidate parent of message m when:

1. p and m have the same non-empty normalized subject (Re:/Fw: removed),
2. m's sender was a recipient (To/Cc) of p,
3. p was sent before m, within `max_reply_days`,
4. there is direct evidence: m is addressed back to p's sender, or m's
   quoted text contains the opening of p's authored text,
5. p does not itself quote m's authored text (that would make p the reply).

Among candidates, the one whose text is quoted nearest the top of m's quoted
section is the parent (the message m directly answers); without quotation,
the latest addressed candidate. Automated messages and structured records
(alerts, digests, calendar entries) are never linked.

`link_evidence` records which evidence held. `link_kind` is "reply" when m
is addressed back to p's sender or its subject starts with "Re:", and
"forward" when m only relays p's text to others; `response_seconds` is set
for replies only.

These are inferred candidate parents, not observed replies. Messages with
empty or changed subjects are not linked, and a parent whose subject differs
leaves m linked to an earlier message of the thread.
"""

from __future__ import annotations

import re

import pandas as pd

from .clean import reply_start
from .dedupe import normalize_subject

_SPACE = re.compile(r"\s+")
_REPLY_SUBJECT = re.compile(r"^\s*re\s*:", re.IGNORECASE)
PREFIX_CHARS = 60   # opening of a message's authored text used to recognise it when quoted
MIN_PREFIX_CHARS = 20


def _flat(text) -> str:
    return _SPACE.sub(" ", text if isinstance(text, str) else "").strip().lower()


def _prefix(authored) -> str | None:
    text = _flat(authored)[:PREFIX_CHARS]
    return text if len(text) >= MIN_PREFIX_CHARS else None


def link_replies(messages: pd.DataFrame, max_reply_days: int, eligible: pd.Series | None = None) -> pd.DataFrame:
    """Add reply_to (index of the inferred parent), link_evidence, link_kind, response_seconds and thread_id.

    `messages` needs sender, to, cc, subject and date, and body and authored
    for quotation evidence (either may be absent). `eligible` marks messages
    that may be linked at all. The index must be unique.
    """
    frame = messages.copy()
    frame["_subject"] = frame["subject"].map(normalize_subject)
    frame["reply_to"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    frame["link_evidence"] = pd.Series([None] * len(frame), index=frame.index, dtype=object)
    frame["link_kind"] = pd.Series([None] * len(frame), index=frame.index, dtype=object)
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
            best = None  # (rank, index, date, evidence, addressed)
            for prior_index, prior_date, prior_sender, recipients, prior_prefix, prior_body in reversed(earlier):
                if row["date"] - prior_date > window:
                    break
                if not sender or sender not in recipients or prior_date >= row["date"]:
                    continue
                if own and len(own) >= 2 * MIN_PREFIX_CHARS and own in prior_body:
                    continue  # the earlier message already quotes this one
                addressed = prior_sender in addressed_to
                position = quoted.find(prior_prefix) if prior_prefix else -1
                if not addressed and position < 0:
                    continue
                evidence = "+".join(name for name, held in [("addressed", addressed), ("quoted", position >= 0)] if held)
                # Quoted parents rank by how near the top they are quoted; then the latest addressed one.
                rank = (0, position) if position >= 0 else (1, 0)
                if best is None or rank < best[0]:
                    best = (rank, prior_index, prior_date, evidence, addressed)
            if best is not None:
                _, prior_index, prior_date, evidence, addressed = best
                kind = "reply" if addressed or _REPLY_SUBJECT.match(row["subject"] if isinstance(row["subject"], str) else "") else "forward"
                frame.at[index, "reply_to"] = prior_index
                frame.at[index, "link_evidence"] = evidence
                frame.at[index, "link_kind"] = kind
                if kind == "reply":
                    frame.at[index, "response_seconds"] = (row["date"] - prior_date).total_seconds()
            earlier.append((index, row["date"], sender, addressed_to, own, _flat(body)))

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
