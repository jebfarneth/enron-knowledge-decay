"""Load the embeddings into PostgreSQL with pgvector and check the index against exact search.

Table `messages`: one row per person-text message with its headers, sender
person, authored text and 384-dimension embedding, plus an HNSW index for
cosine distance (`<=>`) and B-tree indexes on (sender person, date) and on
date, so similarity search combines with ordinary SQL filters. Table `search_build`
keeps the embedding stamp, so queries are embedded with the same model.

The load is rebuilt from scratch on every run inside one transaction. After
it, the index is checked: a seeded sample of messages is used as queries,
and the HNSW top k is compared with the exact top k computed in NumPy from
the same vectors (recall@k). The result goes to results/index_check.json.

Usage: uv run python -m enron_search.store
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg
from pgvector.psycopg import register_vector
from psycopg import sql

from .config import load_config

COLUMNS = [("id", "int4"), ("path", "text"), ("message_id", "text"), ("sent_at", "timestamptz"),
           ("sender_address", "text"), ("sender_person", "text"), ("custodian", "text"), ("folder", "text"),
           ("subject", "text"), ("body", "text")]


def ensure_database(dsn: str) -> None:
    """Create the configured database if it does not exist yet."""
    name = psycopg.conninfo.conninfo_to_dict(dsn).get("dbname")
    try:
        psycopg.connect(dsn).close()
    except psycopg.OperationalError as error:
        if not name or f'database "{name}" does not exist' not in str(error):
            raise
        admin = psycopg.conninfo.make_conninfo(dsn, dbname="postgres")
        with psycopg.connect(admin, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def connect(dsn: str) -> psycopg.Connection:
    connection = psycopg.connect(dsn)
    connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    connection.commit()
    register_vector(connection)
    return connection


def load(connection: psycopg.Connection, rows: pd.DataFrame, vectors: np.ndarray, stamp: dict,
         m: int = 16, ef_construction: int = 64) -> None:
    """Replace the messages table with these rows and vectors, then build its indexes."""
    if len(rows) != len(vectors):
        raise ValueError(f"{len(rows):,} rows but {len(vectors):,} vectors")
    dimensions = vectors.shape[1]
    columns = ", ".join(f"{name} {kind}" for name, kind in COLUMNS)
    with connection.transaction():
        connection.execute("DROP TABLE IF EXISTS messages")
        connection.execute("DROP TABLE IF EXISTS search_build")
        connection.execute(f"CREATE TABLE messages ({columns}, embedding vector({dimensions}) NOT NULL, "
                           "PRIMARY KEY (id), UNIQUE (path))")
        connection.execute("CREATE TABLE search_build (key text PRIMARY KEY, value jsonb NOT NULL)")
        connection.execute("INSERT INTO search_build VALUES ('embedding', %s)", [json.dumps(stamp)])
        names = ", ".join(name for name, _ in COLUMNS)
        with connection.cursor().copy(f"COPY messages ({names}, embedding) FROM STDIN WITH (FORMAT BINARY)") as copy:
            copy.set_types([kind for _, kind in COLUMNS] + ["vector"])
            records = zip(range(len(rows)), rows["path"], rows["message_id"], rows["date"], rows["sender"],
                          rows["sender_person"], rows["custodian"], rows["folder"], rows["subject"],
                          rows["authored"], vectors)
            for record in records:
                copy.write_row([None if value is pd.NaT else value for value in record])
        # Building the HNSW graph in memory is much faster than spilling to disk.
        connection.execute("SET LOCAL maintenance_work_mem = '1GB'")
        connection.execute(sql.SQL("CREATE INDEX messages_embedding ON messages USING hnsw "
                                   "(embedding vector_cosine_ops) WITH (m = {}, ef_construction = {})")
                           .format(sql.Literal(m), sql.Literal(ef_construction)))
        connection.execute("CREATE INDEX messages_sender ON messages (sender_person, sent_at)")
        connection.execute("CREATE INDEX messages_sent_at ON messages (sent_at)")
    connection.execute("ANALYZE messages")
    connection.commit()


def nearest(connection: psycopg.Connection, vector: np.ndarray, k: int, ef_search: int,
            exclude_id: int | None = None) -> list[int]:
    """Ids of the k messages closest to vector through the HNSW index."""
    with connection.transaction():
        connection.execute(sql.SQL("SET LOCAL hnsw.ef_search = {}").format(sql.Literal(ef_search)))
        cursor = connection.execute("SELECT id FROM messages WHERE id IS DISTINCT FROM %s::int4 "
                                    "ORDER BY embedding <=> %s LIMIT %s", [exclude_id, vector, k])
        return [row[0] for row in cursor]


def exact_nearest(vectors: np.ndarray, query: int, k: int) -> list[int]:
    """Ids of the k vectors with the highest cosine similarity to vectors[query], itself excluded."""
    scores = vectors @ vectors[query]
    scores[query] = -np.inf
    top = np.argpartition(-scores, k)[:k]
    return top[np.argsort(-scores[top], kind="stable")].tolist()


def recall_check(connection: psycopg.Connection, vectors: np.ndarray, queries: int, k: int, ef_search: int,
                 seed: int) -> dict:
    """Share of the exact top k that the HNSW index returns, over a seeded sample of messages as queries."""
    sample = np.random.default_rng(seed).choice(len(vectors), size=min(queries, len(vectors)), replace=False)
    found, times = 0, []
    for query in sample.tolist():
        begun = time.perf_counter()
        approximate = nearest(connection, vectors[query], k, ef_search, exclude_id=query)
        times.append(time.perf_counter() - begun)
        found += len(set(approximate) & set(exact_nearest(vectors, query, k)))
    return {"queries": len(sample), "k": k, "ef_search": ef_search, "seed": seed,
            f"recall_at_{k}": round(found / (len(sample) * k), 4),
            "median_query_ms": round(float(np.median(times)) * 1000, 2)}


def main() -> None:
    config = load_config()
    data, database = config["paths"]["data"], config["database"]
    stamp = json.loads((data / "embeddings.json").read_text(encoding="utf-8"))
    vectors = np.load(data / "embeddings.npy")
    rows = pd.read_parquet(data / "rows.parquet")
    ensure_database(database["dsn"])
    with connect(database["dsn"]) as connection:
        begun = time.monotonic()
        load(connection, rows, vectors, stamp, database["hnsw_m"], database["hnsw_ef_construction"])
        print(f"loaded {len(rows):,} messages and built the indexes in {(time.monotonic() - begun) / 60:.1f} min")
        check = config["check"]
        result = recall_check(connection, vectors, check["queries"], check["k"], database["ef_search"], check["seed"])
        size = connection.execute("SELECT pg_size_pretty(pg_total_relation_size('messages'))").fetchone()[0]
    result.update({"messages": len(rows), "hnsw_m": database["hnsw_m"],
                   "hnsw_ef_construction": database["hnsw_ef_construction"], "table_size": size,
                   "embedding": {key: stamp[key] for key in ("model", "revision", "embeddings_sha256")}})
    results: Path = config["paths"]["results"]
    results.mkdir(parents=True, exist_ok=True)
    (results / "index_check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
