# One target per pipeline stage; `make all` runs every stage in order and
# regenerates every table and figure reported in the README.
# Requires uv (https://docs.astral.sh/uv/). Dependencies are pinned in uv.lock.

RUN = uv run python -m enron_importance

.PHONY: all setup test data identity rank network evaluate crosscheck figures clean-generated

all: setup test data identity rank network evaluate crosscheck figures

setup:
	uv sync --group dev

test:
	uv run pytest -q

# Download (checksum-verified on every run), parse, window, deduplicate, clean, flag, thread.
data:
	$(RUN).prepare

# Per-message sender attribution and the address table.
identity:
	$(RUN).identity

# Title-list labels matched to identities.
rank:
	$(RUN).formal_rank

# Communication graph and centrality measures (exact betweenness takes several minutes).
network:
	$(RUN).network

# Baselines against the title proxy, paired differences and sensitivity runs.
evaluate:
	$(RUN).evaluate

# Quote removal compared with email_reply_parser.
crosscheck:
	$(RUN).validate_cleaning

figures:
	$(RUN).figures.funnel
	$(RUN).figures.baselines

# Remove generated data (keeps the downloaded corpus in data/raw).
clean-generated:
	rm -rf data/interim data/processed
