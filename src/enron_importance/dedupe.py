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


def normalize_subject(subject: str) -> str:
    return _SPACE.sub(" ", _SUBJECT_PREFIX.sub("", subject or "")).strip().lower()


def normalize_body(body: str) -> str:
    return _SPACE.sub(" ", body or "").strip().lower()


def content_key(row: pd.Series) -> str:
    parts = [
        row["sender"] or "",
        row["date"].isoformat() if pd.notna(row["date"]) else "",
        normalize_subject(row["subject"]),
        normalize_body(row["body"]),
    ]
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()


def folder_rank(folder: str) -> int:
    folder = (folder or "").lower()
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
    frame["content_key"] = frame.apply(content_key, axis=1)
    frame["_rank"] = frame["folder"].map(folder_rank)
    frame = frame.sort_values(["_rank", "path"], kind="stable")
    by_content = frame.duplicated("content_key", keep="first")
    has_id = frame["message_id"].notna()
    by_id = has_id & frame.duplicated("message_id", keep="first") & ~by_content
    kept = frame[~by_content & ~by_id].drop(columns="_rank").sort_values("path", kind="stable")
    stats = {"duplicate_content": int(by_content.sum()), "duplicate_message_id": int(by_id.sum())}
    return kept.reset_index(drop=True), stats
