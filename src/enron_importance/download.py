"""Download the Enron corpus and verify it against the pinned checksum.

Usage: uv run python -m enron_importance.download
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

from .config import load_config

CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, destination: Path) -> None:
    """Download to a .part file and rename only after a complete transfer."""
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(url) as response, open(partial, "wb") as out:
        while block := response.read(CHUNK):
            out.write(block)
    partial.rename(destination)


def ensure_corpus(config: dict | None = None) -> Path:
    """Return the verified corpus path, downloading it if absent.

    Raises SystemExit if the file's size or SHA-256 does not match config.yaml.
    """
    config = config or load_config()
    corpus = config["corpus"]
    target = config["paths"]["raw"] / corpus["filename"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        print(f"Downloading {corpus['url']} ...")
        fetch(corpus["url"], target)
    size = target.stat().st_size
    if size != corpus["bytes"]:
        sys.exit(f"{target.name}: expected {corpus['bytes']} bytes, found {size}")
    actual = sha256_of(target)
    if corpus["sha256"] is None:
        sys.exit(f"No checksum pinned yet. Record this in config.yaml: sha256: {actual}")
    if actual != corpus["sha256"]:
        sys.exit(f"{target.name}: SHA-256 mismatch ({actual})")
    print(f"Verified {target.name} ({size:,} bytes, sha256 {actual[:12]}...)")
    return target


if __name__ == "__main__":
    ensure_corpus()
