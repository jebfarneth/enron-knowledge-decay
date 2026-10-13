"""Loading and searching a small table in a real PostgreSQL with pgvector.

Run with ENRON_SEARCH_TEST_DSN pointing at a disposable database, for example
ENRON_SEARCH_TEST_DSN="dbname=enron_search_test" uv run pytest -m db
"""

import os

import numpy as np
import pandas as pd
import pytest

from enron_search.query import search
from enron_search.store import connect, ensure_database, exact_nearest, load, nearest, recall_check

DSN = os.environ.get("ENRON_SEARCH_TEST_DSN")
db = pytest.mark.skipif(not DSN, reason="set ENRON_SEARCH_TEST_DSN to a disposable database")


def unit(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


VECTORS = unit([[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0], [0, 0.9, 0.1], [0, 0, 1], [0.5, 0.5, 0]])
ROWS = pd.DataFrame({
    "path": [f"p/{n}" for n in range(6)], "message_id": [f"<{n}>" for n in range(6)],
    "date": pd.to_datetime(["2000-01-05", "2001-03-01", "2001-06-01", "2001-06-02", "2002-01-01", "2001-07-01"],
                           utc=True),
    "sender": ["a@enron.com"] * 3 + ["b@enron.com"] * 3, "sender_person": ["ann"] * 3 + ["bob"] * 3,
    "custodian": ["c"] * 6, "folder": ["f"] * 6, "subject": ["s"] * 6, "authored": [f"body {n}" for n in range(6)],
})


def test_exact_nearest_excludes_the_query_and_orders_by_similarity():
    assert exact_nearest(VECTORS, 0, 2) == [1, 5]


@pytest.fixture
def connection():
    ensure_database(DSN)
    with connect(DSN) as connection:
        load(connection, ROWS, VECTORS, {"model": "test"})
        yield connection


@pytest.mark.db
@db
def test_loaded_rows_are_searchable_with_filters(connection):
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 6
    assert nearest(connection, VECTORS[0], 2, ef_search=40, exclude_id=0) == [1, 5]
    hits = search(connection, VECTORS[0], k=3)
    assert [row[0] for row in hits] == [0, 1, 5]
    assert hits[0][5] == pytest.approx(1.0, abs=1e-6)
    assert [row[0] for row in search(connection, VECTORS[2], k=3, sender="bob")] == [3, 5, 4]
    assert [row[0] for row in search(connection, VECTORS[0], k=5, start="2001-01-01", end="2001-06-01")] == [1, 2]


@pytest.mark.db
@db
def test_recall_is_perfect_on_a_tiny_table(connection):
    # k = 1 avoids ties between equally similar vectors, which either search may order differently.
    result = recall_check(connection, VECTORS, queries=6, k=1, ef_search=40, seed=1)
    assert result["recall_at_1"] == 1.0 and result["queries"] == 6


@pytest.mark.db
@db
def test_reloading_replaces_the_table(connection):
    load(connection, ROWS.iloc[:2], VECTORS[:2], {"model": "test"})
    assert connection.execute("SELECT count(*) FROM messages").fetchone()[0] == 2
