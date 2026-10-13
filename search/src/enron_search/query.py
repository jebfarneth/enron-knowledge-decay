"""Search the person-text messages by meaning.

The query is embedded with the model recorded in the database, and messages
are ranked by cosine similarity through the HNSW index, optionally limited to
one sender person and a date range (UTC dates, both ends included). With a
filter, pgvector's iterative index scan keeps reading the index until k
matching messages are found, and the outer query restores exact similarity
order.

Usage:
  uv run python -m enron_search.query "gas supply shortfall in California"
  uv run python -m enron_search.query "credit exposure" --sender "sara shackleton" --start 2001-01-01 -k 5
"""

from __future__ import annotations

import argparse
import textwrap

import numpy as np
import psycopg
from psycopg import sql

from .config import load_config
from .embed import load_model
from .store import connect

SEARCH = """
WITH candidates AS MATERIALIZED (
    SELECT id, sent_at, sender_person, subject, body, embedding <=> %(vector)s AS distance
    FROM messages
    WHERE (%(sender)s::text IS NULL OR sender_person = %(sender)s::text)
      AND (%(start)s::date IS NULL OR sent_at >= %(start)s::date::timestamp AT TIME ZONE 'UTC')
      AND (%(end)s::date IS NULL OR sent_at < (%(end)s::date + 1)::timestamp AT TIME ZONE 'UTC')
    ORDER BY distance
    LIMIT %(k)s
)
SELECT id, sent_at, sender_person, subject, body, 1 - distance AS similarity FROM candidates ORDER BY distance
"""


def search(connection: psycopg.Connection, vector: np.ndarray, k: int = 10, sender: str | None = None,
           start: str | None = None, end: str | None = None, ef_search: int = 100) -> list[tuple]:
    """Up to k (id, sent_at, sender_person, subject, body, similarity) rows, most similar first."""
    with connection.transaction():
        connection.execute(sql.SQL("SET LOCAL hnsw.ef_search = {}").format(sql.Literal(ef_search)))
        connection.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        return connection.execute(SEARCH, {"vector": vector, "k": k, "sender": sender, "start": start,
                                           "end": end}).fetchall()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text", help="what to search for, in plain language")
    parser.add_argument("-k", type=int, default=10, help="number of messages to show")
    parser.add_argument("--sender", help="only messages from this person key, e.g. 'jeffrey dasovich'")
    parser.add_argument("--start", help="first date to include (YYYY-MM-DD)")
    parser.add_argument("--end", help="last date to include (YYYY-MM-DD)")
    args = parser.parse_args()

    config = load_config()
    with connect(config["database"]["dsn"]) as connection:
        stamp = connection.execute("SELECT value FROM search_build WHERE key = 'embedding'").fetchone()[0]
        settings = config["embedding"]
        if (stamp["model"], stamp["revision"]) != (settings["model"], settings["revision"]):
            raise SystemExit(f"the database was built with {stamp['model']}@{stamp['revision'][:12]}; "
                             "rerun enron_search.embed and enron_search.store")
        model = load_model(config)
        vector = model.encode([args.text], normalize_embeddings=True, convert_to_numpy=True)[0].astype(np.float32)
        rows = search(connection, vector, args.k, args.sender, args.start, args.end, config["database"]["ef_search"])
    for _, sent_at, sender, subject, body, similarity in rows:
        print(f"{similarity:.3f}  {sent_at:%Y-%m-%d}  {sender}  |  {subject or '(no subject)'}")
        print(textwrap.indent(textwrap.shorten(body or "", width=300, placeholder=" ..."), "       "))
    if not rows:
        print("no messages match the filters")


if __name__ == "__main__":
    main()
