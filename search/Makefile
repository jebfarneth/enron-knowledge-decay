# Semantic search over the main pipeline's certified run. Run the main
# pipeline (`make all` in the repository root) first.
# Requires uv and PostgreSQL with pgvector.

RUN = uv run python -m enron_search

.NOTPARALLEL:
.PHONY: all setup test test-db embed store duplicates search

all: setup test embed store duplicates

setup:
	uv sync --group dev

# Unit tests (no database or model needed).
test:
	uv run pytest -q -m "not db"

# Database tests against a disposable database.
test-db:
	ENRON_SEARCH_TEST_DSN="dbname=enron_search_test" uv run pytest -q -m db

# Embed every person-text message (resumable).
embed:
	$(RUN).embed

# Load PostgreSQL, build the HNSW and filter indexes, check recall against exact search.
store:
	$(RUN).store

# Same-sender near-duplicates the exact deduplication kept.
duplicates:
	$(RUN).duplicates

# make search Q="..." [ARGS="--sender 'kay mann' -k 5"]
search:
	$(RUN).query "$(Q)" $(ARGS)
