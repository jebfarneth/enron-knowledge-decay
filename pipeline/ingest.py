#!/usr/bin/env python3
"""
ingest.py

Converts the raw Enron `emails.csv` export into a structured parquet file for
the downstream NLP and knowledge-graph pipeline.

The script parses message headers, sender and recipient fields, dates, subjects,
and plain-text bodies while preserving malformed records for auditability.

Inputs:
    emails.csv

Outputs:
    enron_emails.parquet

Usage:
    python pipeline/ingest.py

Notes:
    The current ingestion path targets the public Enron email corpus. The TODO
    below documents the intended extension path for client data formats such as
    CSV exports, mailbox exports, Slack JSON, or other organizational archives.
"""

import email
import email.utils

import pandas as pd

# TODO: Generalize ingestion layer to accept client data formats
# Enron corpus = demo mode
# Client data upload = production mode
# Supported formats planned: CSV exports, email exports, Slack JSON exports
# Refactor after Phase 1 and Phase 2 are complete


def extract_addresses(header_value):
    if not header_value:
        return None
    addresses = []
    for _, addr in email.utils.getaddresses([header_value]):
        if addr:
            addresses.append(addr.lower())
    return ", ".join(addresses) if addresses else None


def parse_body(msg):
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(body_parts) if body_parts else None


def main():
    print("Reading emails.csv...")
    df_raw = pd.read_csv("emails.csv", dtype=str)

    records = []
    malformed = []

    total = len(df_raw)
    print(f"Processing {total:,} emails...")

    for i, row in enumerate(df_raw.itertuples(index=False), start=1):
        if i % 50_000 == 0:
            print(f"  Progress: {i:,} / {total:,}")

        file_path = row.file
        raw_message = row.message

        if not isinstance(raw_message, str):
            malformed.append(file_path)
            records.append({
                "file": file_path,
                "message_id": None,
                "date": None,
                "from": None,
                "to": None,
                "cc": None,
                "subject": None,
                "body": None,
            })
            continue

        try:
            msg = email.message_from_string(raw_message)
        except Exception:
            malformed.append(file_path)
            records.append({
                "file": file_path,
                "message_id": None,
                "date": None,
                "from": None,
                "to": None,
                "cc": None,
                "subject": None,
                "body": None,
            })
            continue

        # Parse date
        date_str = msg.get("Date")
        parsed_date = None
        if date_str:
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                parsed_date = None

        # Extract from/to/cc with lowercased addresses
        from_addr = extract_addresses(msg.get("From"))
        to_addr = extract_addresses(msg.get("To"))
        cc_addr = extract_addresses(msg.get("Cc"))

        # Subject
        subject = msg.get("Subject")

        # Message-ID
        message_id = msg.get("Message-ID")
        if message_id:
            message_id = message_id.strip()

        # Body
        body = parse_body(msg)

        records.append({
            "file": file_path,
            "message_id": message_id,
            "date": parsed_date,
            "from": from_addr,
            "to": to_addr,
            "cc": cc_addr,
            "subject": subject,
            "body": body,
        })

    print(f"  Progress: {total:,} / {total:,}")

    result_df = pd.DataFrame(records)
    result_df.to_parquet("enron_emails.parquet", index=False)

    print(f"\nDone. Saved {len(result_df):,} rows to enron_emails.parquet")
    print(f"Malformed emails: {len(malformed)}")


if __name__ == "__main__":
    main()
