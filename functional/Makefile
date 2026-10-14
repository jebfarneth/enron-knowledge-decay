# Functional importance over the main pipeline's certified run. Run the main
# pipeline (`make all` in the repository root) first.
# Requires uv.

RUN = uv run python -m enron_functional

.NOTPARALLEL:
.PHONY: all setup test absences absence-sample absence-score absence-human

all: setup test absences

setup:
	uv sync --group dev

test:
	uv run pytest -q

# Dated absences from out-of-office replies and first-person announcements.
absences:
	$(RUN).absences

# Blind sample for the labelled check, and its score once labels exist.
absence-sample:
	$(RUN).absence_check draw

absence-score:
	$(RUN).absence_check score

absence-human:
	$(RUN).absence_check human
