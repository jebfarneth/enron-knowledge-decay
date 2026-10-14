# Functional importance: absences in the Enron email

When someone is away, does the work sent to them wait? This sub-project
finds dated absences in the corpus (out-of-office replies and "I'll be out
…" announcements), checks them against blind labels, and will test whether
signals measured from email before an absence predict how much mail to the
absent person goes unanswered. The analysis is specified in
[`PLAN.md`](PLAN.md) before any outcome is computed.

Like [`search/`](../search/), it is a separate project with its own lockfile.
It reads `../data/processed` after checking each file against the main
pipeline's `manifest.json`, and never writes there, so the certified run
stays valid.

## Stages

| Stage | Module | Output |
|---|---|---|
| Find notices, date each absence, name backups, merge notices into absences | `absences.py` | `data/absence_notices.parquet`, `data/absences.parquet`, `results/absences.json` |
| Blind labelled check, in rounds | `absence_check.py` | `data/labels/round<n>/`, `results/absence_check_round<n>.json` |
| Agreement between a person's labels and the AI labeller's | `absence_check.py human` | `results/absence_check_human.json` |

## Absences

1,978 messages announce an absence (1,625 announcements, 353 automatic
replies). 1,213 give a usable window. Of the rest, 453 give no date, 105
come from senders not resolved to a person, 99 cover only part of a day, 37
name a weekday that disagrees with the date, 36 give no day back, and 35 are
too long, weekend only, or otherwise out of range. They merge into 985 absences of 558 people: 326 of one
day, 182 of two or three, 312 of four to seven, 133 of eight to fourteen and
32 longer. 179 absences name a backup who resolves to a known person
("please contact Monica Reasoner"); 385 notices name someone.

## Labelled check

Each round draws 100 kept notices at random (fixed seed), leaving out every
notice read before: the 120 read while the rules were written
([`labels/dev_inspected_paths.txt`](labels/dev_inspected_paths.txt)) and
those of earlier rounds. An AI labeller (Claude, Opus 5.5), in a separate
session that saw only the emails and the
[guidelines](labels/absence_guidelines.md), labelled whether the sender is
away for at least a full working day and from when to when. Rules were
revised after rounds 1 and 2; round 3, fixed in advance as the last, checks
the rules as they stand.

| Round | Notices decided | Calendar days (±1) | Working days (±1 at each end) |
|---|---:|---|---|
| 1 | 99 | **86 (79 to 92%)** | 92 (86 to 97%)\* |
| 2 | 99 | **83 (75 to 90%)** | 86 (79 to 92%)\* |
| 3 | 97 | 82 (76 to 90%)\* | **86 (81 to 94%)** |

Bold marks each round's primary score, fixed before it was labelled; \*
marks scores computed afterwards. Intervals are 95% Wilson intervals. The
primary score moved from calendar to working days before round 3 was drawn:
the analysis counts working days, and the calendar score counted a Friday
absence written "back Monday" against one ending "Saturday" as wrong. In
round 3, automatic replies were correct in 29 of 30 and announcements in 57
of 67. The remaining errors are mostly part days the rules miss ("most of
Monday", "10:30 to 3:00") and "the week of July 4".

The project's owner labelled 25 of round 1's notices with the same
guidelines and the same blind sheet. Owner and AI labeller agreed on whether
the sender was away in 24 of 25, and where both said so, on the working days
away in 23 of 24 (96%, 80 to 99%); on calendar days, in only 16, mostly
"back Monday" against "back Saturday". Before one correction the working-day
count was 22: the owner had entered one absence a year off (2001 for an
email of 2000) and confirmed it as an entry slip after scoring; the label
records the correction. The remaining difference is a day back left
"unknown" with a note giving the AI labeller's date. Before labelling item
59 the owner asked Claude how to read it; Claude explained the guideline
without showing any label, so that label is not fully independent
(`results/absence_check_human.json`).

## Run

```sh
make setup
make test           # unit tests, no data needed
make absences       # about 2 minutes
make absence-sample # draws the round set in config.yaml
make absence-score  # once data/labels/round<n>/labels.json exists
```

`data/` holds message text and is not committed.
