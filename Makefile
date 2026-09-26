# One target per pipeline stage; `make all` runs every stage in order and
# regenerates every table and figure reported in the README, then checks the
# audited corpus cases against the fresh data.
# Requires uv (https://docs.astral.sh/uv/). Dependencies are pinned in uv.lock.

RUN = uv run python -m enron_importance

# Stages depend on each other's files; never run them in parallel.
.NOTPARALLEL:
.PHONY: all setup test data identity threads rank network mentions gold goldeval evaluate crosscheck threadcheck figures regress clean-generated

all: setup test data identity threads rank network mentions gold goldeval evaluate crosscheck threadcheck figures regress

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

# Mention network of Agarwal et al. (2014): names in authored text resolved to people
# (name tagging takes over an hour the first time; later runs reuse cached tags).
mentions:
	$(RUN).mentions

# Agarwal et al. (2012) dominance pairs and their evaluation. The release is
# not public (request it from the authors, see config.yaml); without it both
# stages print that they were skipped and the rest of the pipeline runs.
gold:
	$(RUN).gold_standard

goldeval:
	$(RUN).gold_evaluation

# Baselines against the title proxy, paired differences and sensitivity runs.
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
