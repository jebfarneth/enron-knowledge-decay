# Analysis plan: does email show who an organization depends on?

**Status: approved by the project's owner and committed on 2026-10-13,
before any outcome below was computed; the commit is the record.** Later
changes are listed under "Deviations" with their reason.

## Question

When someone is away, does the work sent to them wait? And do signals
measured from email *before* the absence predict how much it waits, beyond
what formal rank and email volume predict?

Functional importance here means dependence: how much other people's work
needs this person in particular. An absence shows it. If someone else covers,
mail to the absent person still gets answered; if nobody can, it waits.

## Absences (the test)

- Source: the absence detector (`absences.py`) as checked in round 3 of the
  labelled check, the last round: 86 of 97 notices correct on working days
  (89%, 95% interval 81 to 94%). Its rules do not change after that round.
- Included: absences starting 2000-01-01 to 2001-11-30 (before the
  bankruptcy filing on 2001-12-02) and covering at least one working day,
  whose absent person sent at least 20 person-text messages in the 56 days
  before the first day away. Absences after 2001-11-30 are a sensitivity run.
- Feasibility, counted before any outcome (exposure only, no replies
  looked at): 337 absences of 140 people meet this; 2,993 messages were
  sent (To) to an absent person during one.

## Control windows

For each absence, up to four windows for the same person with the same length
and starting weekday, 2, 3, 5 and 6 weeks before the first day away, leaving
out any window that overlaps one of the person's detected absences, a company
holiday (`workdays.py`: New Year's Day, Memorial Day, Independence Day, Labor
Day, Thanksgiving and the day after, Christmas Day), or the week from
December 24 to January 1. Absences that themselves include that week are a
sensitivity run, not the main analysis. Comparisons are
within person: each absence against that person's own ordinary weeks.

## Outcome

**Primary: answered while away.** For every message an internal person sends
To the absent person during the window, at least 24 hours before the day back:
whether it gets a linked reply (`links.parquet`, kind "reply", any confidence)
from anyone within 24 hours. The same for messages to the same person in the
control windows. The away effect is the drop in that share.

Secondary:
1. **Stalled threads.** Threads the person sent to in the 7 days before the
   window: the share with no message during the window and a message within
   14 days after it, against control windows.
2. **Rerouting.** The absent person's contacts (at least 3 messages exchanged
   in the 56 days before): the share of their messages during the window to
   people they did not email in those 56 days, against control windows.
3. **Catch-up.** Messages the person sends in the first two working days back,
   relative to their daily average in the 56 days before.

## Signals (measured in the 56 days before the first day away)

1. **Brokerage:** betweenness (weights 1/messages) and Burt's constraint in
   the person-to-person graph of internal person-text mail (To and Cc,
   weighted 1/recipients as in the main pipeline).
2. **Topic ownership:** person-text messages clustered by their search
   embeddings (k-means, k = 100, seed 20261013, fitted once on the whole
   corpus); the person's largest share of a topic's messages, among topics
   with at least 20 messages in the window.
3. **Being pointed to:** messages in which someone tells a third person to ask,
   check with, contact or talk to this person ("check with Sara", "Sara will
   know"), detected by rules checked against blind labels before use.
4. **Named as backup:** times other people's absence notices named this person
   as covering for them, before the first day away.

Baselines: messages received (To) and sent, and degree, in the same 56 days;
formal rank from the title list (`formal_rank.parquet`) where matched.

## Analysis

- **H1 (primary).** Message-level logistic regression of answered-within-24h
  on away (absence vs control window), each signal (standardized), and
  away × signal, with the baselines and their away interactions as controls.
  The test is the away × signal coefficient for each of the four signals:
  95% intervals from a 1,000-draw bootstrap over people, Holm-adjusted across
  the four. Also person-disjoint 5-fold cross-validated log loss: baselines
  alone against baselines plus signals.
- **H2.** The away effect is smaller when the person's notice names a backup
  (one pre-specified test, same bootstrap).
- **H3 (descriptive).** Each person's away effect, shrunk toward the mean
  (empirical Bayes), against their formal rank: who the organization depended
  on more than their title suggests. Automated and shared mailboxes are left
  out.
- Placebo check: control windows against each other should show no away
  effect.
- Sensitivity: absences from automatic replies only (29 of 30 correct in
  round 3, against 57 of 67 for announcements); high-confidence links only;
  48-hour reply horizon; activity threshold 10 instead of 20; 26-week signal
  windows; post-bankruptcy absences.

## Known limits

Replies are inferred, not observed (no In-Reply-To headers in the corpus), and
a reply by phone or in person is invisible. People are visible mostly through
the ~150 mailboxes collected, so non-custodians' mail is partial. Absences are
announced, not observed, and the detector's errors are measured by the
labelled check.

## Deviations

None yet.
