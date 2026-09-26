"""Restrict to the analysis window and remove duplicate copies of messages.

The CMU maildirs store one email in several folders (for example `sent`,
`_sent_mail`, `sent_items`, `all_documents`, `discussion_threads`), and the
copies usually carry different Message-IDs because each folder was exported
separately. A message is therefore a duplicate when it has the same sender,
timestamp, normalized subject and normalized body as another message, or the
same Message-ID. Copies whose recipient lists are both non-empty and share
no address are treated as candidate separate sends of the same text (one
note mailed to two distributions) and are all kept; address strings alone
cannot prove two sends, since one person can appear under two spellings.
The copy kept is the one from the most authoritative folder; every discarded
copy is recorded against it. Recipient addresses that only other copies
list are kept in separate columns; downstream stages add one only when it
resolves to a person who is not already a recipient under another spelling.

Some copies of one message carry timestamps shifted by whole hours (the same
numeric time zone, different wall-clock times, from different mailbox
exports). They are not removed, only flagged: a later message with the same
sender, subject, body (over `min_chars` characters) and recipients, exactly
1 to `max_hours` hours after another, is a probable copy of it.
"""

from __future__ import annotations

import hashlib
import re

import numpy as np
import pandas as pd

# Folders ordered from most to least authoritative copy of a message.
FOLDER_PRIORITY = [
    "sent", "_sent_mail", "sent_items",
    "inbox", "notes_inbox",
    "all_documents", "discussion_threads", "deleted_items",
]
_SUBJECT_PREFIX = re.compile(r"^\s*((re|fw|fwd)\s*:\s*)+", re.IGNORECASE)
_SPACE = re.compile(r"\s+")


def _text(value) -> str:
    """Missing values arrive as None or NaN from parquet; treat both as empty."""
    return value if isinstance(value, str) else ""


def normalize_subject(subject) -> str:
    return _SPACE.sub(" ", _SUBJECT_PREFIX.sub("", _text(subject))).strip().lower()


def normalize_body(body) -> str:
    return _SPACE.sub(" ", _text(body)).strip().lower()


def content_keys(frame: pd.DataFrame) -> pd.Series:
    """SHA-1 of sender, timestamp, normalized subject and normalized body, per row."""
    senders = frame["sender"].map(_text)
    dates = frame["date"].map(lambda d: d.isoformat() if pd.notna(d) else "")
    subjects = frame["subject"].map(normalize_subject)
    bodies = frame["body"].map(normalize_body)
    return pd.Series(
        [hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest() for parts in zip(senders, dates, subjects, bodies)],
        index=frame.index,
    )


def folder_rank(folder) -> int:
    folder = _text(folder).lower()
    return FOLDER_PRIORITY.index(folder) if folder in FOLDER_PRIORITY else len(FOLDER_PRIORITY)


def restrict_window(messages: pd.DataFrame, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    """Keep dated messages inside [start, end]; report what was dropped."""
    lower = pd.Timestamp(start, tz="UTC")
    upper = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    undated = messages["date"].isna()
    outside = ~undated & ((messages["date"] < lower) | (messages["date"] >= upper))
    kept = messages[~undated & ~outside].copy()
    return kept, {"undated": int(undated.sum()), "outside_window": int(outside.sum())}


def _recipients(frame: pd.DataFrame) -> list[frozenset]:
    if "to" not in frame:
        return [frozenset()] * len(frame)
    return [frozenset(list(to) + list(cc)) for to, cc in zip(frame["to"], frame["cc"])]


def send_keys(frame: pd.DataFrame) -> pd.Series:
    """Content key, split where copies went to disjoint non-empty recipient lists.

    Within one content key, copies whose recipient lists share an address are
    one send (connected components, so copy order does not matter); a copy
    with no recipients joins the send of the highest-priority copy. `frame`
    must already be in priority order.
    """
    keys = frame["content_key"].to_numpy(dtype=object).copy()
    recipients = _recipients(frame)
    duplicated = np.flatnonzero(frame["content_key"].duplicated(keep=False).to_numpy())
    groups: dict[str, list[int]] = {}
    for i in duplicated:
        groups.setdefault(keys[i], []).append(i)
    for key, members in groups.items():
        parent = {i: i for i in members}

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        owner: dict[str, int] = {}
        for i in members:
            for address in recipients[i]:
                if address in owner:
                    parent[root(i)] = root(owner[address])
                else:
                    owner[address] = i
        listed = [i for i in members if recipients[i]]
        for i in members:
            if not recipients[i]:
                parent[root(i)] = root(listed[0] if listed else members[0])
        order = {r: n for n, r in enumerate(dict.fromkeys(root(i) for i in members))}
        for i in members:
            keys[i] = f"{key}:{order[root(i)]}"
    return pd.Series(keys, index=frame.index)


def deduplicate(messages: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Drop duplicate copies, keeping the most authoritative folder's copy.

    Returns the kept messages, counts, and a copies table mapping every
    discarded copy's path to the path of the message kept for it. The kept
    message's own To and Cc stay as they are; addresses that only its other
    copies list are kept apart in `to_extra` and `cc_extra`, to be added
    downstream only when they resolve to a person not already a recipient.
    """
    frame = messages.copy()
    frame["content_key"] = content_keys(frame)
    frame["_rank"] = frame["folder"].map(folder_rank)
    frame = frame.sort_values(["_rank", "path"], kind="stable")
    frame["_send"] = send_keys(frame)
    by_content = frame.duplicated("_send", keep="first")
    has_id = frame["message_id"].notna()
    by_id = has_id & ~by_content & frame[~by_content].duplicated("message_id", keep="first").reindex(frame.index, fill_value=False)
    kept_path = frame.groupby("_send")["path"].transform("first")
    id_keeper = frame[~by_content & has_id].drop_duplicates("message_id").set_index("message_id")["path"]
    kept_path = kept_path.where(~by_id, frame["message_id"].map(id_keeper))
    removed = by_content | by_id
    # A copy's keeper may itself have been removed by the other rule: follow to a kept message.
    target = dict(zip(frame["path"], kept_path))
    gone = set(frame.loc[removed, "path"])
    for path in frame.loc[removed, "path"]:
        seen = set()
        while target[path] in gone and target[path] not in seen:
            seen.add(target[path])
            target[path] = target[target[path]]
    kept_path = frame["path"].map(target)
    copies = pd.DataFrame({"path": frame.loc[removed, "path"], "kept_path": kept_path[removed]}).sort_values("path")
    separate = frame.drop_duplicates("_send").duplicated("content_key").sum()
    added = 0
    if "to" in frame:
        # Copies of one message can list recipients differently (one copy has
        # f..calger@, another only f..carla@); record what the copies add.
        keepers = set(kept_path[removed])  # only kept messages with discarded copies need their lists
        listed = {path: set(to) | set(cc) for path, to, cc in zip(frame["path"], frame["to"], frame["cc"]) if path in keepers}
        for column in ["to", "cc"]:
            extra: dict[str, list[str]] = {}
            for path, keeper, addresses in zip(frame.loc[removed, "path"], kept_path[removed], frame.loc[removed, column]):
                new = [a for a in addresses if a not in listed[keeper] and a not in extra.get(keeper, [])]
                extra.setdefault(keeper, []).extend(new)
            frame[f"{column}_extra"] = frame["path"].map(lambda p: extra.get(p, []))
            added += int(frame.loc[~removed, f"{column}_extra"].map(len).sum())
    kept = frame[~removed].drop(columns=["_rank", "_send"]).sort_values("path", kind="stable")
    stats = {"duplicate_content": int(by_content.sum()), "duplicate_message_id": int(by_id.sum()),
             "candidate_separate_sends": int(separate), "recipient_addresses_only_in_other_copies": added}
    return kept.reset_index(drop=True), stats, copies.reset_index(drop=True)


def flag_shifted_copies(messages: pd.DataFrame, max_hours: int, min_chars: int) -> pd.Series:
    """Path of the earlier message each probable time-shifted copy duplicates (None otherwise)."""
    bodies = messages["body"].map(normalize_body)
    recipients = ["\x1f".join(sorted(r)) for r in _recipients(messages)]
    key = pd.Series(
        [hashlib.sha1("\x1e".join(parts).encode("utf-8")).hexdigest() for parts in
         zip(messages["sender"].map(_text), messages["subject"].map(normalize_subject), bodies, recipients)],
        index=messages.index,
    )
    order = pd.DataFrame({"key": key, "date": messages["date"], "path": messages["path"]})[bodies.str.len() > min_chars]
    order = order.sort_values(["key", "date", "path"], kind="stable")
    same = order["key"].eq(order["key"].shift())
    gap = (order["date"] - order["date"].shift()).dt.total_seconds()
    shifted = same & (gap % 3600 == 0) & gap.between(3600, max_hours * 3600)
    first = order["path"].where(~shifted).ffill()
    return first.where(shifted).reindex(messages.index)
