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

## Implementation decisions

Made on 2026-10-13 while writing the code, before any outcome was computed;
the plan above leaves them open.

1. **Messages.** "Internal" mail is person-text mail (`person_text` in
   `sender_people.parquet`) from an @enron.com sender address. Recipients are
   resolved to people through `identities.parquet`; unresolved addresses are
   dropped.
2. **Times.** A window runs from Houston midnight of its first day to Houston
   midnight of its day back. "At least 24 hours before the day back" means
   sent no later than the day back's midnight minus 24 hours.
3. **Replies.** A message is answered when `links.parquet` holds a row of kind
   "reply" whose parent is that message, sent within 24 hours after it. A
   reply by the absent person counts.
4. **Scales.** Counts (betweenness, being pointed to, named as backup, mail
   received and sent, degree) enter as log(1 + x); shares (topic ownership)
   and Burt's constraint as they are. Every signal and baseline is then
   standardized over the included absences.
5. **Graph.** People only. Betweenness on the undirected graph with edge
   length 1/weight, as in the main pipeline; Burt's constraint on the same
   undirected weighted graph (igraph).
6. **Topics.** scikit-learn `KMeans`, k = 100, `random_state` 20261013,
   `n_init` 1 (k-means++), on the 163,273 unit-length search embeddings,
   after checking their stamp against the main pipeline's manifest.
7. **Control windows** leave out windows that overlap any detected absence of
   the person (every kept notice), not only included absences.
8. **Being pointed to** is a third-party mention (the person is neither the
   sender nor a recipient) with a referral cue ("ask", "check with", "talk
   to", "contact", "get with", "X will know", "X can help" and similar),
   using the main pipeline's resolved mentions. Its rules are frozen and then
   checked in one blind round of 100 detected referrals, labelled as the
   absences were; its precision is reported.
9. **Named as backup** counts notices by other people naming the person in the
   56 days before, following the section heading.
10. **Rank** has formal titles for few people, so it enters a second H1 model
    fitted on the people matched to the title list, not the main one.
11. **H2**: a notice "names a backup" when any notice of the absence names
    someone, resolved to a person or not.
12. **H3**: a person's away effect is the difference of answered shares
    (absence windows minus control windows, pooled over their absences),
    for people with at least 10 messages in each; it is shrunk with a
    normal–normal empirical Bayes estimate (method of moments).
13. **Placebo**: for each absence, the control window 2 weeks before plays
    "away" against the other three.
14. **Bootstrap**: people are resampled with replacement, 1,000 draws,
    seed 20261013. Two-sided p = 2 × min(share of draws ≤ 0, share ≥ 0);
    Holm adjusts those p-values; 95% percentile intervals are reported as
    they are, beside the Holm-adjusted p.

## Deviations

1. **Five tests, not four** (2026-10-13, before any outcome). Brokerage has
   two measures, betweenness and constraint, so the model has five away ×
   signal coefficients and Holm adjusts across five. This is more
   conservative than four.
