# One target per pipeline stage; `make all` runs every stage in order and
# regenerates every table and figure reported in the README.
# Requires uv (https://docs.astral.sh/uv/). Dependencies are pinned in uv.lock.

RUN = uv run python -m enron_importance

.PHONY: all setup test data identity rank network gold evaluate crosscheck threadcheck figures clean-generated

all: setup test data identity rank network gold evaluate crosscheck threadcheck figures

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

# Agarwal et al. (2012) dominance pairs, if the Columbia release is in data/raw (see config.yaml).
gold:
	$(RUN).gold_standard

# Baselines against the title proxy and the gold standard, paired differences and sensitivity runs.
evaluate:
	$(RUN).evaluate

# Quote removal compared with email_reply_parser.
crosscheck:
	$(RUN).validate_cleaning

# Reply links re-checked against the audit's labelled sample.
threadcheck:
	$(RUN).validate_threads

figures:
	$(RUN).figures.funnel
	$(RUN).figures.baselines

# Remove generated data (keeps the downloaded corpus in data/raw).
clean-generated:
	rm -rf data/interim data/processed
