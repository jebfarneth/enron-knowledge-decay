# Hidden Functional Importance in Workplace Email (Enron)

*Can language and communication patterns in email measure how much an
organization depends on a person, and where that differs from their formal rank?*

**Status: rebuild in progress (September 2026).** The first version of this
project (March–May 2026) is preserved in [`legacy/`](legacy/) with a note on why
it is being replaced. Every number and figure below is regenerated from the
public corpus by `make all`. Phases 1–2 (data layer and network baselines)
were independently audited on 2026-09-25 ([report](audits/data_audit_codex_2026-09-25.md));
[`audits/response_2026-09-25.md`](audits/response_2026-09-25.md) lists how each
finding was addressed and what remains open.

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
| Inferred reply and forward links, threads | `threads.py` | `reply_to`, `link_kind`, `thread_id` |
| Per-message sender attribution and address table | `identity.py` | `sender_people.parquet`, `identities.parquet` |
| Formal-rank labels from the 2004 title list | `formal_rank.py` | `formal_rank.parquet` |
| Communication graph and centrality | `network.py` | `edges.parquet`, `centrality.parquet` |
| Pairwise accuracy against the title proxy | `evaluate.py` | `results/baselines_*.csv` |
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
| After removing duplicate copies (233 same-text messages to different recipients kept as separate sends) | 254,110 |
| With estimated authored text | 234,341 |
| Analysis set: internal senders, excluding 9,422 automated messages, 3,113 structured records, 8,934 long routine messages and 1,531 probable time-shifted copies | 167,970 (6,343 sender addresses) |

The automated, structured and routine flags are heuristics, not a validated
classifier. Repeated short messages ("approved", "please print", "will do")
are speech acts and stay in the analysis set; from accounts that mostly send
alerts, only the repeated alerts are removed.

Senders are attributed per message from the message's own display name. The
6,455 internal sender addresses resolve to 5,869 keys: 5,635 people, 96 role
mailboxes (e.g. "Legal Temp 3", "Office of the Chairman"), 136 addresses
with no usable name, 2 distribution lists; three placeholder addresses
(`no.address@enron.com`, `40enron@enron.com`, `enron.announcement@enron.com`)
are never treated as a person. Names sharing an Exchange directory ID and
surname merge (Albert and Bert Meyers); one name with two well-supported
middle initials splits (Mark A and Mark E Taylor).

Reply links need direct evidence (the reply is addressed back to the earlier
sender or quotes it). On the audit's 60 randomly sampled links from the
earlier rule, 25 of the 27 true direct replies are still linked as replies,
and 71% of links now labelled replies are true direct replies (45% of the
earlier rule's links were). Links remain inferred, not observed.

## Phase 2 result: network baselines

![Which network measure recovers formal rank?](figures/fig06_baselines_formal_rank.png)

Labels: seniority levels (CEO 6 … trader/employee 0) for 129 people in the
Shetty & Adibi (2004) title list, matched to corpus identities. They are a
noisy, undated title proxy, not ground truth: two duplicate rows with
conflicting titles are dropped following Diesner & Carley (2005), and four
labels contradicted by the list's own notes or the person's signature are
flagged. Accuracy is the share of the 6,235 different-level pairs a measure
orders correctly (chance = 50%), with 95% person-level bootstrap intervals.

The graph has 20,757 nodes: 5,606 people, 91 role mailboxes, 305 distribution
lists and 14,755 internal addresses that never sent mail and could not be
matched to a person.

| Measure | Accuracy | 95% interval |
|---|---:|---:|
| Degree (distinct contacts) | 65.5% | 57.8–72.8% |
| PageRank | 61.7% | 53.9–68.8% |
| Email received (weighted) | 61.3% | 53.4–68.4% |
| Betweenness (exact) | 57.4% | 48.8–64.8% |
| Email sent (messages) | 52.2% | 44.0–60.0% |

Degree has the highest point estimate. Paired on the same resamples, its lead
over PageRank (3.7 points, interval −0.6 to 7.8) is not distinguishable from
zero; its leads over betweenness and messages sent are. Sensitivity runs
([`results/baselines_sensitivity.csv`](results/baselines_sensitivity.csv))
move degree between 60.3% (CEOs and presidents removed) and 67.2% (people-only
graph); removing disputed labels gives 66.5%, and building the graph only
from messages with at most 10 recipients gives 62.9%, so broadcasts account
for part of degree's signal.

Agarwal et al. (2012) report 79.3% for degree on 440 core-employee pairs of
their reporting-line gold standard. That is related work with a different
label set and graph, not a replication; evaluation against their data will be
added if the authors share it.

## Independent check of the cleaning

Quote removal was compared with `email_reply_parser` (Zapier's Python port of
GitHub's reply parser) on 5,000 messages sampled with a seed not used while
writing the rules. The two outputs agree after whitespace normalization on
77.5% of messages. Neither tool is ground truth, and marker counts alone
reward deleting text, so an empty cleaner is shown as a control:

| On 5,000 sampled messages | This pipeline | email_reply_parser | Empty cleaner |
|---|---:|---:|---:|
| Output empty | 7.3% | 3.5% | 100% |
| "Original Message" separator left | 0.08% | 2.0% | 0% |
| "Forwarded by" banner left | 0.04% | 6.0% | 0% |
| Quoted header line left | 1.7% | 7.8% | 0% |

In the audit's manual review of 200 messages containing quotations, the
previous version of this cleaner left quoted header lines in 7 and deleted
the sender's own text in 1 (an answer written inline inside the quoted
message); `email_reply_parser` left quoted prose in 35. The output is an estimate of top-posted text:
signatures and pasted documents are still included, and removing them is
part of Phase 3.

Half of the corpus is duplicate copies of the same message stored in several
folders; the first version of this project counted every copy.

## Reproduce

```sh
make all           # uv sync, tests, then every stage in order (about 30 minutes)
```

Tunable parameters live in [`config.yaml`](config.yaml); fixed rules (regular
expressions, folder priorities, nickname and role-word lists, PageRank damping)
are versioned in the source. The corpus is the CMU release of May 7, 2015
(<https://www.cs.cmu.edu/~enron/>), checked against a pinned SHA-256 on every
run; the parsed cache is rebuilt whenever the archive or parser changes, and
`funnel.json` records the hashes of the code and configuration that produced
it. Dependencies are pinned in `uv.lock` for Python 3.12; runs have been
reproduced on macOS only.

## Related work

- Agarwal, Omuya, Harnly & Rambow (2012). A Comprehensive Gold Standard for the Enron Organizational Hierarchy. *ACL*.
- Prabhakaran & Rambow (2014). Predicting Power Relations between Participants in Written Dialog from a Single Thread. *ACL*.
- Gilbert (2012). Phrases That Signal Workplace Hierarchy. *CSCW*.
- Bramsen, Escobar-Molano, Patel & Alonso (2011). Extracting Social Power Relationships from Natural Language. *ACL-HLT*.
- Cohen, Carvalho & Mitchell (2004). Learning to Classify Email into "Speech Acts". *EMNLP*.
- Diesner & Carley (2005). Exploration of Communication Networks from the Enron Email Corpus. *SIAM International Conference on Data Mining, Workshop on Link Analysis*.
- Diesner, Frantz & Carley (2005). Communication Networks from the Enron Email Corpus. *Computational & Mathematical Organization Theory*.

## Author

Jeb Farneth · [jebfarneth.com](https://www.jebfarneth.com)
