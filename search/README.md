# Semantic search over the Enron person-text messages

Sentence embeddings of the 163,273 person-text messages from the main
pipeline's certified run (after the time-shifted-copy correction), stored in PostgreSQL with
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

**Index.** 163,273 messages loaded and indexed in 1.7 minutes on a 2020
dual-core laptop (table and indexes 716 MB). For 200 messages drawn with a
fixed seed and used as queries, the HNSW index (m 16, ef_construction 64,
ef_search 100) returned 96.2% of the exact top 10 computed in NumPy from the
same vectors, at a median 10.0 ms per query. Exact ties between identical
vectors count as misses when the two searches order them differently.

**Near-duplicates the deduplication kept.** Pairs of person-text messages
from the same sender person, sent within 48 hours of each other, both with at
least 100 characters of authored text and with cosine similarity of at least
0.98: 2,475 pairs among 3,132 messages from 522 senders.

| Why the exact rule kept the pair | Pairs |
|---|---:|
| Authored text differs (edits, added lines) | 1,195 |
| To and Cc recipients differ | 752 |
| Matches on authored text, subject, recipients and a whole-hour gap (see below) | 241 |
| Subject differs | 109 |
| Same timestamp | 92 |
| Time gap is under an hour, or a minute or more off a whole number of hours | 85 |
| Whole-hour gap over the rule's 17-hour maximum | 1 |

The frozen run's scan, under the 8-hour rule, found 4,180 pairs, 1,729 of
them identical on authored text, subject and recipients and a whole 9 to 17
hours apart. A labelled check confirmed those as copies of one message (one
export a mailbox's Lotus Notes file, the other its Outlook file), and the main
pipeline now flags shifts up to 17 hours, give or take under a minute (see the
main README). On the corrected run 191 such pairs remain, 9 to 14 hours apart
(130 at exactly 10); 179 are in one custodian's mailbox and 87 in that
custodian's sent folders. Checked against the raw bodies, 174 differ outside
the authored text, in the full bodies the rule compares; 13 have
bodies at or under the rule's 100-character minimum; and 4 come from a note
sent twice minutes apart with each send stored twice, which the rule misses
because it compares each copy only with the one before it. The other 50
pairs that match on authored text are 1 to 7 hours apart (45 at 5): in 49 the
sender's address is written differently, and 1 differs outside the authored
text.

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
