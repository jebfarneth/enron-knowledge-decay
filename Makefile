# One command per pipeline stage; `make all` runs everything in order.
# Requires uv (https://docs.astral.sh/uv/). Dependencies are pinned in uv.lock.

.PHONY: all setup test data clean-generated

all: setup test data

setup:
	uv sync --group dev

test:
	uv run pytest -q

# Download (checksum-verified), parse, window, deduplicate, clean, flag senders, thread.
data:
	uv run python -m enron_importance.prepare

# Remove generated data (keeps the downloaded corpus in data/raw).
clean-generated:
	rm -rf data/interim data/processed
