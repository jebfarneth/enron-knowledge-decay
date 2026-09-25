"""Reconstruct reply links and threads.

Enron headers carry no In-Reply-To or References fields, so replies are
inferred. Message m replies to message p when:

1. p and m have the same normalized subject (Re:/Fw: prefixes removed),
2. m's sender was a recipient (To/Cc) of p,
3. p was sent before m, within `max_reply_days`,

and p is the latest such message. A thread is the connected set of messages
joined by reply links. Response time is the delay between p and m.
"""

from __future__ import annotations

import pandas as pd

from .dedupe import normalize_subject


def link_replies(messages: pd.DataFrame, max_reply_days: int) -> pd.DataFrame:
    """Add reply_to (index of the replied-to message), response_seconds and thread_id.

    `messages` needs sender, to, cc, subject and date columns; its index must be unique.
    """
    frame = messages.copy()
    frame["_subject"] = frame["subject"].map(normalize_subject)
    frame["reply_to"] = pd.array([pd.NA] * len(frame), dtype="Int64")
    frame["response_seconds"] = pd.array([pd.NA] * len(frame), dtype="Float64")
    window = pd.Timedelta(days=max_reply_days)

    for _, group in frame[frame["_subject"] != ""].groupby("_subject", sort=False):
        if len(group) < 2:
            continue
        group = group.sort_values("date", kind="stable")
        earlier: list[tuple] = []  # (index, date, recipients)
        for index, row in group.iterrows():
            sender = row["sender"]
            for prior_index, prior_date, recipients in reversed(earlier):
                if row["date"] - prior_date > window:
                    break
                if sender and sender in recipients and prior_date < row["date"]:
                    frame.at[index, "reply_to"] = prior_index
                    frame.at[index, "response_seconds"] = (row["date"] - prior_date).total_seconds()
                    break
            earlier.append((index, row["date"], set(row["to"]) | set(row["cc"])))

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
