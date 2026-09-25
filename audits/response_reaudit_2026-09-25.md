# Response to the 2026-09-25 re-audit

The re-audit ([report](reaudit_codex_2026-09-25.md)) reviewed commit
`1ab1b2b` and concluded the data layer was still not fit for person-level
Phase 3 results. Each finding is listed with the commit that addresses it,
its effect on the regenerated data, and what remains open. Numbers come from
the full rerun on branch `rebuild/reaudit-fixes`; the 13 real-corpus
regression checks pass on that data.

Status: **fixed** (the demonstrated defect is corrected and tested), **partly
fixed** (remainder listed), **open**.

| Finding | Status | Commit | Change and effect |
|---|---|---|---|
| M1 identity mistakes: Dana / Mark Dana Davis split; Mark Palmer's unmarked messages all assigned to Mark S | fixed for the demonstrated cases | `804ee5e` | A message whose middle name plus surname is its address's usual key follows that key, and so does every message with the same full name; "mark davis" becomes an alias of "dana davis", so all of Dana Davis's messages form one node and the title list's Mark Davis joins it. An address infers a missing middle initial only from at least 20 initialled messages, so Mark Palmer's 66 unmarked messages stay on an ambiguous key. Degree against the title proxy moves from 65.5% to 66.6%, as the re-audit predicted. **Open:** the remaining 129 title-to-person joins have not been individually adjudicated. |
| M2 display-name grammar and typing invent people; analysis mask is not person text | fixed for the demonstrated cases | `804ee5e`, `c3dc5a1` | "First Last, Title" is read as name then title (George Wasaff, Robert Knight). Anything sent through a shared Exchange mailbox (CN=MBX_), any digit-bearing word and "Conf. Room" are roles. Node types come from every key, so the ambiguous base keys are no longer people. A person-text flag and funnel (`person_text.json`): of 169,044 analysis messages, 166,034 from 5,524 people are person text; the rest are unknown (1,194), role (1,057), address (517), list (181) or ambiguous (61). **Open:** parsing and typing remain heuristic. |
| M3 speech-act exemption counted an 80-character prefix | fixed | `4fe4bca` | Length is counted over the whole message after dropping an addressee line and a short sign-off, and routine means the whole text repeats. Routine messages fall from 12,230 to 6,745; 3,308 are excluded from text. The long examples (1,067 to 1,739 words) are no longer exempt. |
| M4 cleaner regression on wrapped To lists; machine records survive | fixed for the demonstrated cases | `3b8c13f`, `9ef95e2` | Quoted Lotus headers may wrap over up to 30 recipient lines and carry a "Sent by:" line; all four regressed messages return to the sender's own text. Colon-free calendar entries, leave requests, self-declared automated e-mails, the remaining performance-review notices and daemon senders are flagged (structured records 3,113 → 3,297). **Open:** answers written inline inside a quoted message are still lost; the list of machine formats is fixed and incomplete. |
| M5 reply-kind links unreliable | partly fixed | `fa34c41` | Threading is its own stage after identity and matches people rather than address spellings; a link is a reply only when addressed back to the parent's sender (an inherited Re: no longer counts); the inversion check looks only at the parent's quoted text; probable copies are never linked. 40,073 links: 31,238 replies, 8,835 forwards. On the old labelled sample, 24 of 27 direct replies stay linked as replies and 72.7% of reply-kind links are direct replies; that sample informed the rules, so it is a regression check, not a held-out estimate. **Open:** a fresh, human-labelled precision and recall sample; empty and changed subjects are not linked. |
| M6 deduplication loses or misassigns recipients | partly fixed | `ad4c4b5` | The kept message lists every recipient address any copy of the same send lists (141 addresses added, including Calger on the FERC briefing paper); aliases collapse when resolved to people. The 233 splits are called candidate separate sends. **Open:** Robert E. Anderson's retained address resolves to Gary Anderson; fixing it needs the X-To display names, which the parser does not keep yet. |
| M7 corpus regression tests read old outputs | fixed | `66d7e3b`, `b722a65`, `c3dc5a1` | `tests/test_pipeline_integration.py` builds a small archive reproducing the audited cases and runs prepare, identity and threads on it. Corpus checks are marked `corpus`, fail when the data was built by different code, require every case to exist, and run after the pipeline (`make regress`). The bootstrap is checked against a brute-force oracle; initial-inference thresholds have boundary tests. |
| m1 people-only sensitivity used fractional out-strength | fixed | `d30578d` | The people-only graph is rebuilt from messages between people, so messages sent stays an exact count. |
| m2 asymmetric tie tolerance | fixed | `b722a65` | Ties use \|a − b\| ≤ 1e-9 · max(\|a\|, \|b\|); a test checks order invariance on the re-audit's boundary pair. |
| m3 probable copies participate in threads | fixed | `fa34c41` | Probable time-shifted copies are never linked. |
| m4 cache provenance and Makefile ordering | fixed | `d30578d`, `c3dc5a1` | The parse stamp adds the Python version, the uv.lock checksum and the parsed table's own checksum, verified before reuse; the table is written atomically. The Makefile is `.NOTPARALLEL`, includes the threads and thread-check stages, runs unit tests before and corpus checks after the pipeline. |
| m5 documentation mismatches | fixed | README | The README reports the new funnel, calls the 233 candidate separate sends, reports reply and forward links separately, drops "never sent mail" for unresolved addresses, and qualifies the old-sample thread figure. |

The release location of the gold-standard data was removed from `config.yaml`
(`8f1a42c`); the evaluation against it is covered in
[`response_gold_audit_2026-09-25.md`](response_gold_audit_2026-09-25.md).
