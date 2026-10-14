"""The main pipeline's certified outputs that this project reads.

Every file read must match the SHA-256 the main pipeline recorded for it in
processed/manifest.json, so results always come from the certified run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

MESSAGE_COLUMNS = ["path", "date", "sender", "subject", "authored", "to", "cc", "probable_copy", "automated"]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def certified_sources(source: Path, names: tuple[str, ...]) -> dict[str, str]:
    """Checksums of `names` (paths like "processed/messages.parquet"), verified against the manifest.

    `source` is the main pipeline's processed directory. Raises when a file is
    missing from the manifest or differs from what the pipeline recorded.
    """
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    recorded = {name: digest for stage in manifest["stages"].values() for name, digest in stage["outputs"].items()}
    checksums = {}
    for name in names:
        if name not in recorded:
            raise RuntimeError(f"{name} is not in the main pipeline's manifest; run the main pipeline first")
        actual = sha256_of(source.parent / name)
        if actual != recorded[name]:
            raise RuntimeError(f"{name} differs from the certified run (manifest {recorded[name][:12]}, "
                               f"file {actual[:12]}); rerun the main pipeline")
        checksums[name] = actual
    return checksums


def messages_with_people(source: Path) -> pd.DataFrame:
    """Every kept message (time-shifted copies dropped) with its sender's person key."""
    messages = pd.read_parquet(source / "messages.parquet", columns=MESSAGE_COLUMNS)
    people = pd.read_parquet(source / "sender_people.parquet", columns=["path", "sender_person"])
    merged = messages.merge(people, on="path", how="inner", validate="one_to_one")
    return merged[~merged["probable_copy"]].drop(columns="probable_copy").reset_index(drop=True)
