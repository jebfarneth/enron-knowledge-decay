# Analysis plan, part 2: can a measure resist the collection?

**Status: approved by the project's owner and committed on 2026-10-14, before
any result below was computed; the commit is the record.** Later changes go
under "Deviations".

## Question

Part 1 (`PLAN.md`) found that which mailboxes are collected moves accuracy
by up to 16.8 points at 25 mailboxes and lifts collected people in the
rankings. The cause is visibility: a collected person's mail is seen in full,
an uncollected person's only through the collected. This part tests measures
designed so that being collected adds nothing.

## Corrected measures

Computed from a collection's messages, with the same rules as Part 1.

1. **Anchored degree.** The number of distinct collection owners, other
   than the person, that the person exchanged mail with (To or Cc, either
   direction). Every message with a collection owner on it is in the
   collection, so these ties are fully visible for everyone, collected or
   not.
2. **Anchored strength.** The same ties weighted by Part 1's message weights
   (a message to n people adds 1/n to each edge), summed over both
   directions.
3. **Talked about.** The number of distinct people who mention the person in
   messages the person is not on (sender, To or Cc), from Paper 1's resolved
   mention links with no exclusion. Whether such a message is collected
   depends on its sender and recipients, not on the person mentioned.

**Collection owners.** A mailbox's owner is the person who is the sender or
a To or Cc recipient on the most of the mailbox's person-text messages. This
maps all 150 mailboxes; it maps Skilling's mailbox to Skilling rather than to
the assistant who sent from it, and both Whalley mailboxes to Greg Whalley.
The weakest mapping, `dean-c`, has its owner on 43% of its messages.

## Comparison

The same collections as Part 1: the full corpus, 200 random draws at each of
k = 10, 25, 50, 75, 100 and 125 (seed 20261014, drawn in the same order), and
busiest, senior and junior first. For each corrected measure, and for degree
and PageRank as computed in Part 1:

1. **Accuracy** on Paper 1's 7,338 main pairs, all pairs and by pair type
   (median and 95% range over random draws).
2. **Collection bias**, as in Part 1: the collected gold employees' mean
   percentile rank in the collection minus their percentile under the same
   measure on the full corpus.
3. **Stability**: Spearman correlation and top-20 overlap with the same
   measure on the full corpus.

## Expectations, stated before any result

- **F1.** The median collection bias of anchored degree is closer to zero
  than that of degree at every k below 150.
- **F2.** The same for talked about.
- **F3.** At k = 25, the 95% range of anchored degree's accuracy over random
  collections is narrower than that of degree (16.8 points in Part 1).

Each is reported as met or not, with its numbers. Accuracy on the full corpus
is reported for every measure, so any cost of a correction is visible.

## Known limits

Anchored measures ignore ties between uncollected people by design, so with
few mailboxes they are coarse and tie often. Collection owners are inferred
from the mail, not taken from a roster. Talked about inherits Paper 1's name
resolution (about 79% of sampled mentions resolved to the right person in
the pilot).

## Deviations

None yet.
