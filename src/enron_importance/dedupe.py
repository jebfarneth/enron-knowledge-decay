"""Restrict to the analysis window and remove duplicate copies of messages.

The CMU maildirs store one email in several folders (for example `sent`,
`_sent_mail`, `sent_items`, `all_documents`, `discussion_threads`), and the
copies usually carry different Message-IDs because each folder was exported
separately. A message is therefore a duplicate when it has the same sender,
timestamp, normalized subject and normalized body as another message, or the
same Message-ID. The copy kept is the one from the most authoritative folder.
"""

from __future__ import annotations

import hashlib
import re

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


def deduplicate(messages: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop duplicate copies, keeping the most authoritative folder's copy."""
    frame = messages.copy()
    frame["content_key"] = content_keys(frame)
    frame["_rank"] = frame["folder"].map(folder_rank)
    frame = frame.sort_values(["_rank", "path"], kind="stable")
    by_content = frame.duplicated("content_key", keep="first")
    has_id = frame["message_id"].notna()
    by_id = has_id & frame.duplicated("message_id", keep="first") & ~by_content
    kept = frame[~by_content & ~by_id].drop(columns="_rank").sort_values("path", kind="stable")
    stats = {"duplicate_content": int(by_content.sum()), "duplicate_message_id": int(by_id.sum())}
    return kept.reset_index(drop=True), stats
