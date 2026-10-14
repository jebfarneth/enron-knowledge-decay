# How much does the collection decide?

The Enron corpus is the ~150 mailboxes investigators collected. This folder
rebuilds Paper 1's hierarchy measures from chosen subsets of those mailboxes,
to see how much a different collection would change the benchmark's results
and who looks important. It is Section 7 of the paper (`../paper/`).

Both plans were committed before any result was computed:
[`PLAN.md`](PLAN.md) (the collection experiment) and
[`PLAN_corrections.md`](PLAN_corrections.md) (measures built to resist it).

## Design

A collection keeps every message with at least one stored copy in one of its
mailboxes (exact duplicates and time-shifted copies included). Degree,
PageRank and the mention measures are rebuilt from those messages with the main
pipeline's rules and scored on Paper 1's 7,338 main gold pairs. On all 150
mailboxes the rebuild reproduces Paper 1's accuracies exactly; the script stops
if it does not. 1,219 collections: 200 random draws at each of 10, 25, 50, 75,
100 and 125 mailboxes, plus busiest-first, senior-first and junior-first.

## Results

| Expectation (stated in advance) | Result | |
|---|---|---|
| E1. At 25 mailboxes, degree's accuracy range is wider than the 2.7-point gap between leading measures | 74.3% to 91.1% (16.8 points) | Met |
| E2. Collected employees rank higher than in the full corpus in at least 95% of random draws | 95.5% at 10 mailboxes, at least 99.5% from 25 up | Met |
| E3. Senior-first collections beat the median random collection at every size | 5 of 6 sizes | Not met |
| F1. Anchored degree's collection bias is closer to zero than degree's at every size | Overcorrects at 10 mailboxes | Not met |
| F2. Talked about's collection bias is closer to zero than degree's at every size | Closer at every size | Met |
| F3. At 25 mailboxes, anchored degree's accuracy range is narrower than degree's | 24.8 against 16.8 points | Not met |

Described, not predicted: talked about (how many people mention someone in
messages that person is not on) varies least, 83.3% to 88.8% at 25 mailboxes,
and costs 0.8 points of accuracy on the full corpus (88.8% against 89.6%).

## Run

From the repository root, with the main pipeline's certified run in place:

```sh
.venv/bin/python collection/experiment.py    # about 45 minutes
.venv/bin/python collection/corrections.py   # about 45 minutes; checks every collection against experiment.py's
```

Outputs: `results/collections.csv`, `results/summary.json`,
`results/corrections.csv`, `results/corrections_summary.json`.
