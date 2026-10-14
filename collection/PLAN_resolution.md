# Analysis plan, parts 3 and 4: names resolved inside each collection, and high-confidence names

**Status: approved by the project's owner and committed on 2026-10-14, before
any result below was computed; the commit is the record.** Later changes go
under "Deviations".

Both parts answer a review of the paper draft (2026-10-14). Unlike Parts 1
and 2, they check results that are already known (talked about's range
under full-corpus resolution, and Paper 1's mention comparisons), so they
are robustness checks, not new tests.

## Part 3: name resolution inside each collection

**Why.** Section 7 reports that talked about varies least across
collections (83.3% to 88.8% at 25 mailboxes, a 5.5-point range, against
16.8 for degree). Its names were resolved with the full corpus: a name's
candidates were everyone in the full email network, and the closest one was
found with full-network hop distances. An analyst holding 25 mailboxes would
know only the people in those mailboxes' network, so the stability may be
partly borrowed from mail outside the collection.

**Design.** For each of Part 1's 1,219 collections (same seed, same order),
every tagged name in the collection's messages is resolved again with
`mentions.py`'s rules applied to the collection alone: the candidates are
the people in the collection's email network, the closest is found with hop
distances in that network, and ties or unreachable candidates leave the name
unresolved. The spaCy tags are not recomputed, since tagging reads only each
message's own text. Paper 1's three mention measures and talked about are
recomputed from the new links (`collection/resolution.py`).

**Scope.** A timing run (which computed no accuracy) took about 48 seconds
per 25-mailbox collection and about 4 minutes for the full corpus, so all
1,219 collections would need about 37 CPU hours. Part 3 runs the full
corpus, the three ordered collections at every size, all 200 random draws
at k = 10 and 25 (R1 needs the full set at 25), and the first 50 random
draws, in Part 1's order, at k = 50, 75, 100 and 125: 619 collections.
Degree's numbers in R2 are taken from Part 2 on exactly the same
collections.

**Checks.** Resolving inside the full collection must reproduce
`mentions.parquet` row for row, exclusions included; and for every
collection, the measures computed from Paper 1's links must equal Parts 1
and 2's results.

**Outcomes.** For random collections at each size: the median and 95% range
of each mention measure's accuracy under in-collection resolution, and its
median paired change from full-corpus resolution; collection bias, Spearman
correlation and top-20 overlap for talked about and people mentioned to
them; and the share of links that still resolve.

**Expectations, stated before any result.**

- **R1.** At k = 25, the 95% range of talked about's accuracy over random
  collections, with in-collection resolution, is narrower than degree's
  (16.8 points).
- **R2.** With in-collection resolution, talked about's median collection
  bias is closer to zero than degree's at every k below 150 (Part 2's F2,
  repeated).

## Part 4: high-confidence names on the full corpus

**Why.** In the pilot, 78.6% of sampled names in the mention measures
resolved to the right person (n = 98), and 15 of the 21 errors were people
outside Enron matched to an employee with the same name.

**Design.** Paper 1's main mention links are restricted in two ways, each
dropping a likelier kind of error: **full names** (a first and a last name,
not one word or initials) and **one candidate** (exactly one person in the
email network is compatible with the name). The mention measures are
recomputed on the full corpus from each subset and compared with degree on
the 7,338 main pairs, all pairs and by pair type, with Paper 1's person
bootstrap (1,000 resamples, paired differences on the same resamples). With
all links the script must reproduce Paper 1's paired results
(`collection/confident_names.py`). The pilot's adjudicated labels are
reported by subset, as a descriptive check that each subset is more often
right; the subsets are small.

**Expectation, stated before any result.**

- **H1.** People mentioned to them (the primary mention measure) stays ahead
  of degree on non-core pairs in both subsets, with a 95% interval above
  zero (Paper 1: +3.7 points, +1.0 to +7.7).

Restricting links drops information as well as errors, so lower accuracy in
a subset does not by itself show that errors drove the results; H1 asks
whether the comparison with degree keeps its direction.

## What changes in the paper

- R1 and R2 met: Section 7 reports talked about under in-collection
  resolution, and the limitation on full-corpus resolution is replaced by
  this check.
- R1 or R2 not met: the abstract, Section 7 and the conclusion stop
  describing talked about as the measure that varies least, and report the
  in-collection numbers.
- H1 met: the paper reports that the non-core advantage holds on
  high-confidence names. Not met: Section 6 says the non-core advantage
  depends on lower-confidence names.

## Known limits

Addresses are still matched to people with the full corpus's identity
table, which every measure uses, degree included; only name resolution is
redone. The pilot precision comes from the run before the copy correction.

## Deviations

None yet.
