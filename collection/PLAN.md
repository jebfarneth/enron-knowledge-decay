# Analysis plan: how much does the collection decide?

**Status: approved by the project's owner and committed on 2026-10-14, before
any result below was computed; the commit is the record.** Later changes go
under "Deviations".

## Question

The Enron corpus is about 150 mailboxes that investigators chose to collect.
Paper 1 found that a baseline scoring only "was this person's mailbox
collected?" reaches 94.2% on pairs between a collected and an uncollected
employee, close to email degree (95.5%). This experiment varies the
collection itself: if a different set of mailboxes had been collected, how
much would the benchmark's accuracy change, and how much would the list of
who looks important change?

## Collections

A collection is a set of custodians (mailbox owners). It keeps every message
of the corpus that has at least one copy in one of its mailboxes
(`copies.parquet` and the `custodian` of each kept message), and nothing
else. The network (`network.py`: same message filters, To and Cc, 1/n
weights) and the mention links (`mentions.parquet`, rows whose message is
kept) are rebuilt from those messages only.

Policies, each at k = 10, 25, 50, 75, 100 and 125 mailboxes (150 is the full
corpus):

1. **Random**: 200 draws for each k, seed 20261014.
2. **Busiest first**: the k mailboxes holding the most messages.
3. **Senior first**: the k custodians who dominate the most gold-standard
   employees (an investigator working from the org chart).
4. **Junior first**: the reverse of 3, as a bound.

## Measures and population

Degree, PageRank, mention degree, people mentioned to them and others
mentioned to them (Paper 1's measures, betweenness left out for time), and
the custodian baseline (1 for custodians in the collection). The population
is Paper 1's main population of 7,338 gold pairs, fixed. An employee absent
from a collection's graph scores 0, so two absent employees tie (half
credit), as an analyst holding only that collection would see them.

## Outcomes

1. **Accuracy** of each measure on all pairs and by Paper 1's pair types:
   for random collections, the median and the 2.5th to 97.5th percentile
   range over the 200 draws at each k.
2. **Ranking agreement**: Spearman correlation between a collection's and the
   full corpus's degree and PageRank over the gold employees.
3. **Collection bias**: for each random collection, the collected
   custodians' mean percentile rank by PageRank among gold employees, minus
   their percentile in the full corpus.
4. **Top-20 overlap**: the share of the full corpus's 20 highest-PageRank
   gold employees that are also in the collection's top 20.

## Expectations, stated before any result

- **E1.** At k = 25, the range of degree accuracy over random collections is
  wider than the largest difference between leading measures on the full
  corpus (2.7 points in Paper 1).
- **E2.** Collected custodians rank higher in their collection than in the
  full corpus: the collection-bias shift is above 0 in at least 95% of
  random draws, for every k below 150.
- **E3.** Senior-first collections score higher on degree accuracy than the
  median random collection of the same size.

Each is reported as met or not, with its numbers. Nothing else is tested;
everything else is description.

## Known limits

Name resolution for mentions was done on the full corpus, so a real smaller
collection would resolve somewhat fewer names. Gold employees and pair types
stay as defined on the full corpus. Senior first uses the gold labels to
choose mailboxes, so its accuracy is not independent of the labels; it
stands for an investigator who knows the org chart.

## Deviations

None yet.
