"""The person-text messages of the frozen pipeline run, and the text each one is embedded from.

Search reads two outputs of the main pipeline: processed/messages.parquet
(estimated authored text and headers) and processed/sender_people.parquet
(per-message sender attribution and the person-text flag). Both must match
the SHA-256 the main pipeline recorded for them in
processed/manifest.json, so search always runs on the certified run.

The text embedded for a message is its subject without reply and forward
prefixes, then its estimated authored text, with whitespace collapsed and
cut to a fixed number of characters. Authored text still contains
signatures and pasted documents inside messages (see the main README).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pandas as pd

SOURCES = ("processed/messages.parquet", "processed/sender_people.parquet")
MESSAGE_COLUMNS = ["path", "message_id", "date", "sender", "subject", "authored", "custodian", "folder"]

_PREFIX = re.compile(r"^\s*(?:(?:re|fw|fwd)\s*(?:\[\d+\])?\s*:\s*)+", re.IGNORECASE)
_SPACE = re.compile(r"\s+")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def certified_sources(source: Path) -> dict[str, str]:
    """Checksums of the files search reads, verified against the main pipeline's manifest.

    `source` is the main pipeline's processed directory. Raises when a file is
    missing from the manifest or differs from what the pipeline recorded.
    """
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    recorded = {name: digest for stage in manifest["stages"].values() for name, digest in stage["outputs"].items()}
    checksums = {}
    for name in SOURCES:
        if name not in recorded:
            raise RuntimeError(f"{name} is not in the main pipeline's manifest; run the main pipeline first")
        actual = sha256_of(source.parent / name)
        if actual != recorded[name]:
            raise RuntimeError(f"{name} differs from the certified run (manifest {recorded[name][:12]}, "
                               f"file {actual[:12]}); rerun the main pipeline")
        checksums[name] = actual
    return checksums


def strip_prefixes(subject: str | None) -> str:
    return _PREFIX.sub("", subject or "").strip()


def build_text(subject: str | None, authored: str | None, max_chars: int) -> str:
    """Subject without Re:/Fw: prefixes, then the authored text, whitespace collapsed, cut to max_chars."""
    text = " ".join(part for part in (strip_prefixes(subject), _SPACE.sub(" ", authored or "").strip()) if part)
    return text[:max_chars]


def person_text_messages(source: Path) -> pd.DataFrame:
    """Person-text messages ordered by path, one row each, with the sender's person key."""
    messages = pd.read_parquet(source / "messages.parquet", columns=MESSAGE_COLUMNS)
    people = pd.read_parquet(source / "sender_people.parquet", columns=["path", "sender_person", "person_text"])
    merged = messages.merge(people, on="path", how="inner", validate="one_to_one")
    merged = merged[merged["person_text"]].drop(columns="person_text")
    return merged.sort_values("path", kind="stable").reset_index(drop=True)
