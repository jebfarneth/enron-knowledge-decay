# Hidden Functional Importance in Workplace Email (Enron)

*Can language and communication patterns in email measure how much an
organization depends on a person, and where that differs from their formal rank?*

**Status: rebuild in progress (September 2026).** The first version of this
project (March–May 2026) is preserved in [`legacy/`](legacy/) with a note on why
it is being replaced. Every number and figure below is regenerated from the
public corpus by `make all`. Phases 1–2 (data layer and network baselines)
were audited independently three times on 2026-09-25: the
[data audit](audits/data_audit_codex_2026-09-25.md), a
[re-audit of the fixes](audits/reaudit_codex_2026-09-25.md) and an
[audit of the gold-standard evaluation](audits/gold_audit_codex_2026-09-25.md).
The responses ([1](audits/response_2026-09-25.md),
[2](audits/response_reaudit_2026-09-25.md),
[3](audits/response_gold_audit_2026-09-25.md)) list how each finding was
addressed and what remains open.

## Research question

Prior NLP work predicts **formal hierarchy** from email (who outranks whom).
This project aims to treat formal rank and **functional importance** (how much
others depend on a person) as separate quantities, measure both from the
Enron corpus, and study where they diverge. Validating functional importance
(for example against what happened to a person's contacts after they left) is
a planned later phase; nothing in the current code measures it yet.

## Pipeline

| Stage | Module | Output |
|---|---|---|
| Download and verify corpus (SHA-256, every run) | `download.py` | `data/raw/enron_mail_20150507.tar.gz` |
| Parse every message from the archive | `ingest.py` | `data/interim/messages_raw.parquet` |
| Analysis window, deduplication, copy provenance | `dedupe.py` | `copies.parquet`, `probable_copy` flag |
| Estimated authored text (quotes, forwards, disclaimers removed) | `clean.py` | `authored` column |
| Automated, structured and routine message flags | `senders.py` | `automated`, `structured`, `routine` |
| Per-message sender attribution, address table, person-text flag | `identity.py` | `sender_people.parquet`, `identities.parquet` |
| Inferred reply and forward links between people, threads | `threads.py` | `links.parquet` |
| Formal-rank labels from the 2004 title list | `formal_rank.py` | `formal_rank.parquet` |
| Communication graph and centrality | `network.py` | `edges.parquet`, `centrality.parquet` |
| Dominance pairs from the Agarwal et al. (2012) gold standard | `gold_standard.py` | `gold_pairs.parquet` |
| Accuracy against the gold standard | `gold_evaluation.py` | `results/gold_standard_*.csv` |
| Accuracy against the title proxy | `evaluate.py` | `results/baselines_*.csv` |
| Cross-check of quote removal vs `email_reply_parser` | `validate_cleaning.py` | `results/cleaning_crosscheck.json` |
| Re-check of reply links against the audit's labelled sample | `validate_threads.py` | `results/thread_link_check.json` |

Later stages (dialog acts, topics, text models, evaluation figures) are added
phase by phase.

## Phase 1 result

![From raw corpus to analysis set](figures/fig01_data_funnel.png)

| Step | Messages |
|---|---:|
| Files in the corpus | 517,401 |
| Dated 1998–2002 | 516,359 |
| After removing duplicate copies (233 same-text messages to disjoint recipient lists kept as candidate separate sends) | 254,110 |
| With estimated authored text | 234,316 |
| Analysis set: internal senders, excluding 9,429 automated messages, 3,297 structured records, 3,308 long routine messages and 1,531 probable time-shifted copies | 169,044 (6,337 sender addresses) |
| Person text: analysis messages whose sender is attributed to a person | 166,034 (5,524 people) |

The automated, structured and routine flags are heuristics, not a validated
classifier. A message is routine when its sender repeats the whole text;
repeated short messages ("approved", "please print", "will do") are speech
acts and stay in the analysis set. From accounts that mostly send alerts,
messages whose opening repeats are treated as alerts and one-off messages are
kept.

Senders are attributed per message from the message's own display name. The
6,455 internal sender addresses resolve to 5,871 keys (5,605 people, 136
roles, 127 addresses with no usable name, 2 lists, 1 ambiguous); four
placeholder addresses are never treated as a person. Role keys include
numbered and shared mailboxes ("Legal Temp 3", "Office of the Chairman",
anything sent through a shared Exchange mailbox, conference rooms). Names
sharing an Exchange directory ID and surname merge (Albert and Bert Meyers),
a middle name a person goes by joins them ("Davis, Mark Dana" is Dana Davis),
and one name with two well-supported middle initials splits (Mark A and
Mark E Taylor). Attribution and typing remain heuristic.

Reply links are inferred between people and need direct evidence: the reply
is addressed back to the earlier sender or quotes it. There are 40,073 links:
31,238 replies and 8,835 forwards. On the audit's 60 labelled links from an
earlier rule, 24 of the 27 true direct replies are still linked as replies,
and 72.7% of links now labelled replies are true direct replies (45% of the
earlier rule's links were). That sample informed the rules, so it is a
regression check, not a held-out estimate; links remain inferred, not
observed.

## Phase 2 result: network baselines

![Which network measure recovers formal rank?](figures/fig06_baselines_formal_rank.png)

**Title proxy.** Seniority levels (CEO 6 … trader/employee 0) for 129 people
in the Shetty & Adibi (2004) title list, matched to corpus identities. They
are a noisy, undated title proxy, not ground truth: two duplicate rows with
conflicting titles are dropped following Diesner & Carley (2005), and four
labels that the list's own notes or the person's signature call into
question are flagged. Accuracy is the share of the 6,235 different-level
pairs a measure orders correctly (chance = 50%), with 95% person-level
bootstrap intervals.

The graph has 20,782 nodes: 5,572 people, 130 roles, 305 distribution lists,
2 ambiguous keys and 14,773 internal addresses that could not be matched to a
person.

| Measure | Accuracy | 95% interval |
|---|---:|---:|
| Degree (distinct contacts) | 66.6% | 59.0–73.4% |
| PageRank | 62.9% | 55.7–70.1% |
| Email received (weighted) | 62.3% | 55.5–68.8% |
| Betweenness (exact) | 58.3% | 50.5–65.6% |
| Email sent (messages) | 52.9% | 44.7–60.1% |

Degree has the highest point estimate. Paired on the same resamples, its lead
over PageRank (3.7 points, interval −0.8 to 8.1) is not distinguishable from
zero; its leads over betweenness and messages sent are. Sensitivity runs
([`results/baselines_sensitivity.csv`](results/baselines_sensitivity.csv))
move degree between 61.6% (CEOs and presidents removed) and 68.3% (people-only
graph); removing disputed labels gives 67.7%, and building the graph only
from messages with at most 10 recipients gives 63.9%, so broadcasts account
for part of degree's signal.

**Gold standard.** The Agarwal et al. (2012) hierarchy, from a release the
authors shared privately (it is not public; request it from them). Its
org-chart positions give 13,241 dominance pairs among 1,518 employees; the
paper reports 13,724 and this reconstruction does not reproduce its counts,
so results here are related to the paper's, not a replication. Employees are
matched to graph nodes by their principal name (release records for
executives often list their assistants' addresses). The main population is
the 11,372 pairs whose two employees are both matched and whose records do not
merge an assistant's position with another.

| Measure | Accuracy (11,372 pairs) | 95% interval |
|---|---:|---:|
| PageRank | 85.6% | 73.4–95.3% |
| Degree | 85.0% | 73.3–93.9% |
| Email received (weighted) | 82.5% | 69.3–92.9% |
| Betweenness (exact) | 75.4% | 60.7–87.2% |
| Email sent (messages) | 69.0% | 54.8–81.0% |
| Custodian baseline (mailbox in the corpus) | 65.1% | 53.1–77.0% |

PageRank and degree are indistinguishable (paired difference +0.6 points,
−1.0 to +2.5). Whether a person's mailbox was collected already orders 88.9%
of pairs between a custodian and a non-custodian, against degree's 91.9%, so
much of that part of the task reflects corpus collection. A few executives
appear in thousands of pairs: weighting each manager equally gives degree
77.0%, and dropping Kenneth Lay and Jeffrey Skilling gives 80.3%. Other
constructions and scorings are in
[`results/gold_standard_sensitivity.csv`](results/gold_standard_sensitivity.csv);
for comparison, degree over raw addresses in all mail, as in the paper's
setup, gives 83.1% on all 13,241 pairs (the paper reports 83.88% on its own
pairs).

## Independent check of the cleaning

Quote removal was compared with `email_reply_parser` (Zapier's Python port of
GitHub's reply parser) on 5,000 messages sampled with a seed not used while
writing the rules. The two outputs agree after whitespace normalization on
77.2% of messages. Neither tool is ground truth, and marker counts alone
reward deleting text, so an empty cleaner is shown as a control:

| On 5,000 sampled messages | This pipeline | email_reply_parser | Empty cleaner |
|---|---:|---:|---:|
| Output empty | 7.3% | 3.5% | 100% |
| "Original Message" separator left | 0.08% | 2.0% | 0% |
| "Forwarded by" banner left | 0.04% | 6.0% | 0% |
| Quoted header line left | 1.1% | 7.8% | 0% |

Most of the extra empty outputs are messages that only forward with a Lotus
Notes banner. In the audit's manual review of 200 messages containing
quotations, an earlier version of this cleaner left quoted header lines in 7
and deleted the sender's own text in 1 (an answer written inline inside the
quoted message); `email_reply_parser` left quoted prose in 35. The output is
an estimate of top-posted text: inline answers are lost, and signatures and
pasted documents are still included; removing them is part of Phase 3.

Half of the corpus is duplicate copies of the same message stored in several
folders; the first version of this project counted every copy.

## Reproduce

```sh
make all           # uv sync, unit tests, every stage in order, then real-corpus checks (about 40 minutes)
```

Tunable parameters live in [`config.yaml`](config.yaml); fixed rules (regular
expressions, folder priorities, nickname and role-word lists, PageRank damping)
are versioned in the source. The corpus is the CMU release of May 7, 2015
(<https://www.cs.cmu.edu/~enron/>), checked against a pinned SHA-256 on every
run. The parsed cache is reused only when its stamp matches the archive
checksum, the parser source, the Python version, the lockfile and the parsed
table's own checksum, and `funnel.json` records the hashes of the code and
configuration that produced it. The gold-standard stages need the private
release and print that they were skipped without it. Dependencies are pinned
in `uv.lock` for Python 3.12; runs have been reproduced on macOS only.

## Related work

- Agarwal, Omuya, Harnly & Rambow (2012). A Comprehensive Gold Standard for the Enron Organizational Hierarchy. *ACL*.
- Agarwal, Omuya, Zhang & Rambow (2014). Enron Corporation: You're the Boss if People Get Mentioned to You. *International Conference on Social Computing*.
- Prabhakaran & Rambow (2014). Predicting Power Relations between Participants in Written Dialog from a Single Thread. *ACL*.
- Gilbert (2012). Phrases That Signal Workplace Hierarchy. *CSCW*.
- Bramsen, Escobar-Molano, Patel & Alonso (2011). Extracting Social Power Relationships from Natural Language. *ACL-HLT*.
- Cohen, Carvalho & Mitchell (2004). Learning to Classify Email into "Speech Acts". *EMNLP*.
- Diesner & Carley (2005). Exploration of Communication Networks from the Enron Email Corpus. *SIAM International Conference on Data Mining, Workshop on Link Analysis*.
- Diesner, Frantz & Carley (2005). Communication Networks from the Enron Email Corpus. *Computational & Mathematical Organization Theory*.

## Author

Jeb Farneth · [jebfarneth.com](https://www.jebfarneth.com)
