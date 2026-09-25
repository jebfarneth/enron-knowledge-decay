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
copy is recorded against it, and the kept message lists every recipient
address that any copy of the same send lists. Aliases of one person then
collapse when recipients are resolved to people.

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

    `frame` must already be in priority order; each copy joins the first
    earlier send it shares a recipient with (or any send, if either list is empty).
    """
    keys = frame["content_key"].to_numpy(dtype=object).copy()
    recipients = _recipients(frame)
    sends: dict[str, list[frozenset]] = {}
    for i in np.flatnonzero(frame["content_key"].duplicated(keep=False).to_numpy()):
        seen = sends.setdefault(keys[i], [])
        mine = recipients[i]
        match = next((n for n, other in enumerate(seen) if not mine or not other or mine & other), None)
        if match is None:
            seen.append(mine)
            match = len(seen) - 1
        keys[i] = f"{keys[i]}:{match}"
    return pd.Series(keys, index=frame.index)


def deduplicate(messages: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Drop duplicate copies, keeping the most authoritative folder's copy.

    Returns the kept messages, counts, and a copies table mapping every
    discarded copy's path to the path of the message kept for it.
    """
    frame = messages.copy()
    frame["content_key"] = content_keys(frame)
    frame["_rank"] = frame["folder"].map(folder_rank)
    frame = frame.sort_values(["_rank", "path"], kind="stable")
    frame["_send"] = send_keys(frame)
    by_content = frame.duplicated("_send", keep="first")
    has_id = frame["message_id"].notna()
    by_id = has_id & frame.duplicated("message_id", keep="first") & ~by_content
    kept_path = frame.groupby("_send")["path"].transform("first")
    kept_path = kept_path.where(~by_id, frame["message_id"].map(frame.drop_duplicates("message_id").set_index("message_id")["path"]))
    removed = by_content | by_id
    copies = pd.DataFrame({"path": frame.loc[removed, "path"], "kept_path": kept_path[removed]}).sort_values("path")
    separate = frame.drop_duplicates("_send").duplicated("content_key").sum()
    added = 0
    if "to" in frame:
        # Copies of one send can list recipients differently (one copy has
        # f..calger@, another only f..carla@); keep every address any copy lists.
        for column in ["to", "cc"]:
            union = (frame[["_send", column]].explode(column).dropna().drop_duplicates()
                     .groupby("_send", sort=False)[column].agg(list))
            merged = frame["_send"].map(union)
            before = frame[column].map(len)
            frame[column] = [list(dict.fromkeys(list(own) + (extra if isinstance(extra, list) else [])))
                             for own, extra in zip(frame[column], merged)]
            added += int((frame.loc[~removed, column].map(len) - before[~removed]).sum())
    kept = frame[~removed].drop(columns=["_rank", "_send"]).sort_values("path", kind="stable")
    stats = {"duplicate_content": int(by_content.sum()), "duplicate_message_id": int(by_id.sum()),
             "candidate_separate_sends": int(separate), "recipient_addresses_added_from_copies": added}
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
