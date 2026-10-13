# Semantic search over the Enron person-text messages

Sentence embeddings of the 165,431 person-text messages from the main
pipeline's certified run, stored in PostgreSQL with
[pgvector](https://github.com/pgvector/pgvector) and searched by cosine
similarity through an HNSW index, alone or combined with SQL filters on the
sender and date. The same table supports exact similarity joins, used here to
find near-duplicate messages that the main pipeline's deduplication kept.

This is a separate project with its own dependencies and lockfile. It reads
`../data/processed` and never writes to it: the main pipeline fingerprints
its own source, configuration and lockfile, so keeping search outside it
leaves the certified run valid. Before reading, it checks that
`messages.parquet` and `sender_people.parquet` match the SHA-256 recorded in
the main pipeline's `manifest.json`.

## Stages

| Stage | Module | Output |
|---|---|---|
| Embed subject plus estimated authored text (resumable shards, stamped with model revision, text hash and source checksums) | `embed.py` | `data/embeddings.npy`, `data/rows.parquet`, `data/embeddings.json` |
| Load PostgreSQL, build HNSW (cosine) and B-tree (sender and date) indexes, measure recall against exact search | `store.py` | table `messages`, `results/index_check.json` |
| Same-sender near-duplicates by exact similarity join, with the reason the exact rule kept each pair | `duplicates.py` | `results/near_duplicates.csv`, `results/near_duplicates.json` |
| Search by meaning with optional sender and date filters | `query.py` | printed results |

Model: `sentence-transformers/all-MiniLM-L6-v2` at a pinned Hugging Face
revision, 384 dimensions, unit-normalized. Settings are in
[`config.yaml`](config.yaml).

## Results

**Index.** 165,431 messages loaded and indexed in 1.9 minutes on a 2020
dual-core laptop (table and indexes 721 MB). For 200 messages drawn with a
fixed seed and used as queries, the HNSW index (m 16, ef_construction 64,
ef_search 100) returned 96.1% of the exact top 10 computed in NumPy from the
same vectors, at a median 10.9 ms per query. Exact ties between identical
vectors count as misses when the two searches order them differently.

**Near-duplicates the deduplication kept.** Pairs of person-text messages
from the same sender person, sent within 48 hours of each other, both with at
least 100 characters of authored text and with cosine similarity of at least
0.98: 4,180 pairs among 6,235 messages from 765 senders.

| Why the exact rule kept the pair | Pairs |
|---|---:|
| Identical text, subject and recipients, shifted by a whole 9 to 17 hours (over the rule's 8-hour maximum) | 1,729 |
| Authored text differs (edits, added lines) | 1,224 |
| To and Cc recipients differ | 822 |
| Time gap is not a whole number of hours | 198 |
| Subject differs | 111 |
| Same timestamp | 94 |
| Matches on authored text (different sender addresses or quoted text) | 2 |

The long shifts cluster at exactly 10 hours (1,200 pairs), then 11 (247), 12
(187) and 14 (62). In 1,442 of the 1,729 pairs both messages are in the same
custodian's mailbox, and in 710 both are in that custodian's sent folders (for
example `sent` and `_sent_mail`), which points to two exports of one message
rather than two sends. These are candidates, not labelled duplicates: raising
the shift maximum is a Phase 3 change to check against labels before the main
pipeline is rerun.

## Run

Needs uv, PostgreSQL with the pgvector extension and the main pipeline's
outputs. On macOS, Homebrew's `pgvector` formula builds a second PostgreSQL;
building pgvector from source against an existing installation is quicker
(`make PG_CONFIG=$(which pg_config) && make install PG_CONFIG=$(which pg_config)`).

```sh
make setup    # uv sync
make test     # unit tests; make test-db runs the database tests against dbname=enron_search_test
make embed    # about 2 hours on a dual-core laptop CPU, resumable
make store    # load PostgreSQL, build the indexes, check recall (about 2 minutes)
make duplicates
make search Q="rolling blackouts and the California power crisis"
make search Q="counterparty credit exposure and collateral" ARGS="--sender 'sara shackleton' --start 2001-01-01 --end 2001-12-31 -k 5"
```

`ENRON_SEARCH_DSN` overrides the database connection string. PyTorch 2.2
is the last release built for Intel Macs, so on them the lockfile pins it with
NumPy 1.x, PyArrow below 22 and Transformers below 5.

## Limits

The embedded text is the estimated authored text, which still contains
signatures, pasted documents and some quoted lines (see the main README).
The model reads at most 256 word pieces, so long messages are represented by
their beginning, and very short messages are matched mostly through their
subject. Similarity finds related wording, not verified facts.
