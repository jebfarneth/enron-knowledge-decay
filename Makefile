# One target per pipeline stage; `make all` runs every stage in order and
# regenerates every table and figure reported in the README, then checks the
# audited corpus cases against the fresh data.
# Requires uv (https://docs.astral.sh/uv/). Dependencies are pinned in uv.lock.

RUN = uv run python -m enron_importance

# Stages depend on each other's files; never run them in parallel.
.NOTPARALLEL:
.PHONY: all setup test data identity threads rank network gold evaluate crosscheck threadcheck figures regress clean-generated

all: setup test data identity threads rank network gold evaluate crosscheck threadcheck figures regress

setup:
	uv sync --group dev

# Unit and generated-corpus integration tests (no real data needed).
test:
	uv run pytest -q -m "not corpus"

# Download (checksum-verified on every run), parse, window, deduplicate, clean, flag.
data:
	$(RUN).prepare

# Per-message sender attribution, the address table and person-text eligibility.
identity:
	$(RUN).identity

# Reply and forward links between people.
threads:
	$(RUN).threads

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

# Audited real-corpus cases, checked against the data just generated.
regress:
	uv run pytest -q -m corpus

# Remove generated data (keeps the downloaded corpus in data/raw).
clean-generated:
	rm -rf data/interim data/processed
