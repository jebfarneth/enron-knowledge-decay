"""Parse every message in the CMU maildir tarball into one table.

Reads directly from the .tar.gz (no 1.7 GB extraction). Each file under
maildir/<custodian>/<folder>/... becomes one row; nothing is filtered here,
so later stages can report exactly what they removed.

Usage: uv run python -m enron_importance.ingest
"""

from __future__ import annotations

import tarfile
from email import message_from_bytes
from email.message import Message
from email.policy import compat32
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .config import load_config
from .download import ensure_corpus

SCHEMA = pa.schema([
    ("path", pa.string()),
    ("custodian", pa.string()),
    ("folder", pa.string()),
    ("message_id", pa.string()),
    ("date", pa.timestamp("us", tz="UTC")),
    ("sender", pa.string()),
    ("to", pa.list_(pa.string())),
    ("cc", pa.list_(pa.string())),
    ("bcc", pa.list_(pa.string())),
    ("x_from", pa.string()),
    ("subject", pa.string()),
    ("body", pa.string()),
])


def addresses(message: Message, header: str) -> list[str]:
    """Lower-cased email addresses from a header, in order, without duplicates."""
    values = message.get_all(header) or []
    seen: dict[str, None] = {}
    for _, address in getaddresses([" ".join(str(v).split()) for v in values]):
        address = address.strip().strip("'\"<>").lower()
        if "@" in address:
            seen.setdefault(address, None)
    return list(seen)


def parse_date(value: str | None):
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return None
    return pd.Timestamp(parsed).tz_convert("UTC")


def body_text(message: Message) -> str:
    """Plain-text body. Enron messages are single-part; decode defensively."""
    if message.is_multipart():
        parts = [p for p in message.walk() if p.get_content_type() == "text/plain"]
        payload = parts[0].get_payload(decode=True) if parts else b""
    else:
        payload = message.get_payload(decode=True)
    if payload is None:
        payload = str(message.get_payload()).encode("utf-8", "replace")
    charset = message.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("latin-1", errors="replace")


def parse_message(raw: bytes, path: str) -> dict:
    """One maildir file -> one row. `path` is the archive member name."""
    parts = path.split("/")
    # maildir/<custodian>/<folder>/.../<n>
    custodian = parts[1] if len(parts) > 2 else ""
    folder = parts[2] if len(parts) > 3 else ""
    message = message_from_bytes(raw, policy=compat32)
    senders = addresses(message, "From")
    return {
        "path": path,
        "custodian": custodian,
        "folder": folder,
        "message_id": (message.get("Message-ID") or "").strip() or None,
        "date": parse_date(message.get("Date")),
        "sender": senders[0] if senders else None,
        "to": addresses(message, "To"),
        "cc": addresses(message, "Cc"),
        "bcc": addresses(message, "Bcc"),
        "x_from": " ".join(str(message.get("X-From") or "").split()) or None,
        "subject": " ".join(str(message.get("Subject") or "").split()),
        "body": body_text(message),
    }


def iter_archive(archive: Path) -> Iterator[dict]:
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.startswith("maildir/"):
                continue
            handle = tar.extractfile(member)
            if handle is not None:
                yield parse_message(handle.read(), member.name)


def write_messages(rows: Iterator[dict], destination: Path, batch_size: int = 20_000) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    batch: list[dict] = []
    with pq.ParquetWriter(destination, SCHEMA, compression="zstd") as writer:
        for row in rows:
            batch.append(row)
            if len(batch) == batch_size:
                writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA))
                count += len(batch)
                batch = []
        if batch:
            writer.write_table(pa.Table.from_pylist(batch, schema=SCHEMA))
            count += len(batch)
    return count


def main() -> None:
    config = load_config()
    archive = ensure_corpus(config)
    destination = config["paths"]["interim"] / "messages_raw.parquet"
    count = write_messages(iter_archive(archive), destination)
    print(f"Wrote {count:,} messages to {destination}")


if __name__ == "__main__":
    main()
