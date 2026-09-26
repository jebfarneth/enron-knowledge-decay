# Independent audit 4 — Enron data layer, evaluations and mention network

Audit target: `52c36492dbca7ccde1d800fa4d1b6b757d1b7b42`, branch `main`. Date: 2026-09-26. This report distinguishes a reproduced computation from a validated research measurement. The original peer-reviewed hierarchy resource is not discredited by defects in this project's reconstruction, matching or evaluation.

## 1. Executive verdict

**Yes with conditions for exploratory Phase 3; not ready for unqualified measurement claims.** The data layer is usable provided signature/quotation/filter errors and remaining duplicate recipients are treated as unresolved, and reply links are not used as observed truth. The **title proxy** is usable as an explicitly noisy seniority comparison. The **gold evaluation** is usable as this release's disclosed, filtered reconstruction—not an exact reproduction of the 2012 benchmark or independent validation of every matched employee. Its new path exclusions and scoring arithmetic reproduce. The **mention network** is a reproducible exploratory adaptation, but not yet a validated clean-authored-language or functional-importance measure: the fresh sample contains wrong referents, quoted headers and many self-signatures. Before interpreting Phase 3 results, freeze population/matching policy, repair or measure those errors, run redaction/exposure ablations, and close the downstream provenance gap. None of the current results alone measures functional importance.

### Scope, preservation and evidence

Source: `/Users/jebfarneth/projects/enron-knowledge-decay` (`R`). Final-run artifacts: `/Users/jebfarneth/projects/enron-knowledge-decay-fixes` (`F`); I did **not** use the older main-checkout processed tables as current data. Scratch evidence: `/tmp/enron-audit4-20260926.pdyhRK` (`S`), including a pinned source copy at `S/pinned_project` (`P`). Private release-derived records remain in scratch and are not reproduced here. Short identifiers below identify counterexamples, not released records.

I read all eight preceding audit/response documents and the supplied 2014 paper. The prior archives were extracted into `S/prior/{audit1,audit2,gold,audit3}`. Probes below either replay their scripts with path adapters or explicitly adapt their fixtures to current schemas/APIs; this does not mean every historical scratch script was rerun. Initial and final manifests cover 102 main-checkout files, 37 fixes-worktree files and the supplied paper: **all 140 hashes are unchanged**. Main HEAD remains the pinned commit. The only added repository file is this uncommitted report; no pipeline code, tests, configuration, data or history was changed.

All manually read samples below were labelled by this AI auditor using corpus context, not independently blinded human annotators. They are screening estimates with recorded uncertainty, not a new gold annotation set.

Commands below use this setup; scripts contain the exact queries, sampling rules, mutations and independent calculations:

```sh
S=/tmp/enron-audit4-20260926.pdyhRK
P="$S/pinned_project"
F=/Users/jebfarneth/projects/enron-knowledge-decay-fixes
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$P/src"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR="$S/mpl"
"$F/.venv/bin/python" "$S/provenance.py"
"$F/.venv/bin/python" "$S/old_provenance_replay.py"
"$F/.venv/bin/python" "$S/oracles.py" title
"$F/.venv/bin/python" "$S/reproduce.py"
```

The fresh scratch `uv sync --locked --group dev` succeeds with Python 3.12.13 and 68 packages. Their versions equal the fixes-worktree environment; the old main environment has only 26 packages and lacks the mention dependencies. Full unit runs in **both the fixes environment and the freshly installed scratch environment pass 166 tests, with 13 corpus tests deselected** (`provenance/headless_unit.log`, `fresh_unit_result.txt`). A macOS font inventory initially stalled test collection; reusing an existing font cache in scratch resolved it. This is an execution-environment issue, not a research finding. **All 14 scratch stage/check subprocesses exit successfully, including all 13 real-corpus tests.** The cached stage replay takes 4,660.7 seconds (77.7 minutes) under host contention; this is not an uncached-run timing benchmark.

## 2. Audit-3 fix verification

All rows of `audits/response_audit3_2026-09-26.md` are covered below. “Fixed” refers only to the claimed counterexample, not to perfect corpus-wide accuracy.

| Finding | Claimed status | Verified status | Evidence and result |
|---|---|---|---|
| M1: hierarchy paths through merged records | Fixed as a reported policy | Path-dependence policy implemented and reproduced; ownership validity still conditional | `gold_identity/gold_verify.py`: independent BSON adjacency and closure reproduce 2,397 immediate relations, 13,241 reconstructed pairs, 8 mixed-position records, 20 multiple-person flags and their 23-record union. Main 7,338; strict 4,939; endpoint-only 10,041. Path flags and alternative constructions agree with current tables. These policies do not establish that all remaining labels are correct. |
| M2: mailbox order determines matching | Fixed; blinded sample open | Narrow order bug fixed; general matching precision remains open | Same script and `synthetic.py`: reversing every mailbox list changes **zero** employee matches; the conflicting-mailbox fixture abstains in both orders. Current statuses: 923 name+address, 68 name-only, 424 address-node, 68 ambiguous and 35 absent. This is not an independent validation of all 1,415 assigned identities. |
| M3: recipient union duplicates people | Fixed for demonstrated cases | **Partly fixed even for demonstrated cases** | `gold_identity/recipient_scan.py`, `forney_retest.json`: Brown is no longer doubled; Calger remains recovered; the Anderson extra is suppressed. The explicitly claimed Phillips repair still fails: the current graph counts the known person and surname-first address separately. Fresh raw headers confirm fourteen network-message cases double one recipient. Component grouping is order-invariant in tested fixtures, but the reverse Message-ID/content-copy chain still dangles (latent: zero current secondary removals). |
| M4: bulletins and signature-only messages | Partly fixed | Partly fixed, with new false exclusions | `text/extract.py`, archived probe replay and fresh samples: all 195 previously demonstrated signature-only person-text cases are now excluded. 1,366 signature flags reproduce; only 794 are marginal analysis exclusions because filters overlap. Fresh positives include substantive text wrongly removed. Ordinary signatures and copied text remain. |
| M5: departmental accounts become people | Fixed | Demonstrated fixes reproduce; not population-wide identity validation | `gold_identity/identity_verify.py` and original attack fixtures reproduce all sender-person, identity, alias, type and person-text artifacts. All 57 original departmental examples are excluded from person-text; all 610 shared-MBX messages type as roles. Twelve directory-ID and two go-by aliases reproduce; all 66 original Palmer ambiguous-cohort records remain ambiguous. 165,105 messages/5,504 keys pass person-text. These checks do not prove every lexical classification correct. |
| M6: wrong reply parents | Partly fixed | Partly fixed; not reliable observed reply labels | `text/retention_counts.json`: original 24/27 true direct replies retain their parent and reply kind; 24/31 retained reply-kind links are correct. Audit-3 50/50 supported links survive, but all four known wrong-parent links survive too. Fresh sample: 47/60 supported, six wrong parents, three relays, four uncertain. |
| M7: cleaning and structured rules | Fixed for demonstrated cases | Narrow fixes, not universal boundary correctness | `text/replay.py`, `text/probes.py`: day-first date, wrapped headers, agenda prose and PEP ACCESS counterexamples checked. The old 200-message sample changes four outputs; the original 120 thread bodies have no cleaner difference. Wider header rules can still cut address-like prose in a synthetic negative control. Inline answers remain lost. |
| M8: stale artifacts pass corpus checks | Fixed | **Only partly fixed; status is overstated** | `provenance.py gate`: altered config and three preparation-output hashes are caught. Corrupting seven downstream artifacts is not; the actual freshness test passes. Removing `funnel.json` skips checks despite generated files. `gold_identity/stale_probe.py`: skipped gold stages delete three processed files but retain all four result files unchanged. |
| Minor: empty draws and mutation gaps | Fixed | Empty draws fixed; test coverage improved but incomplete | `gold_identity/synthetic.py`: no-valid-draw paired resamples return NaN limits and zero draws rather than crash. New numeric/bootstrap/path/mailbox tests kill several old mutants. Current mention tests and quote-author extraction retain important blind spots; mutation results below. |
| Documentation | Fixed | Listed wording repairs largely present; new overclaims remain | README states private-release dependency, reconstruction mismatch and thread denominator. It still overstates whole-pipeline freshness/deletion, mentions “own text” despite residual quotation, and does not disclose the 5,000-character NER limit. See findings and numerical table. |

### Reproduced headline numbers

The complete scratch replay reproduces the current counts. Of 35 compared files, **33 regenerated data/result/figure files are byte-identical**, as is the one reused mention-tag cache. Only `funnel.json` differs: its counts and output checksums match exactly, while its configuration hash reflects scratch paths and its source hash reflects the final figure-label edit described below. All four figures also reproduce byte-for-byte in a second separate-process control. Evidence: `reproduction/stages.json`, `comparison.json`, `figure_control.json` and `corpus_regress.log`.

| Claim / quantity | Audited value | Assessment |
|---|---:|---|
| Parsed / in-window / retained messages | 517,401 / 516,359 / 254,110 | Scratch preparation replay matches; verified parse cache reused |
| Candidate separate sends / probable shifted copies | 233 / 1,531 | Scratch preparation replay matches |
| Estimated authored messages | 234,296 | Scratch preparation replay matches |
| Automated / structured / signature-only / long-routine flags | 9,429 / 8,639 / 1,366 / 3,313 | Independent column counts match; flag classes are not validated truth |
| Analysis messages / sender addresses | 168,170 / 6,320 | Current counts match |
| Person-text messages / keys | 165,105 / 5,504 | Identity rerun matches |
| Internal sender addresses / keys | 6,455 / 5,871 | Identity rerun matches |
| Address-table key types | 5,596 people; 145 roles; 127 address keys; two lists; one ambiguous | Match; four placeholder addresses are not additional person keys |
| Directory-ID / go-by aliases | 12 / two | Match |
| Title-list rows / matched rows / distinct labelled keys | 161 / 160 / 129 | Table rerun matches |
| Replies / forwards / threads | 28,989 / 8,504 / 216,617 | Rebuilt link table byte-identical; semantic reply precision is lower |
| Communication nodes and types | 20,752 = 5,562 people +139 roles +305 lists +two ambiguous +14,744 addresses | Rebuilt graph and centrality byte-identical; 219,327 directed edges |
| Gold immediate relations / reconstructed closure | 2,397 / 13,241 | Independent BSON reconstruction matches; not the paper's 2,155 /13,724 |
| Mixed / multiple-person / union flags | Eight /20 /23 | Rule reproduction matches; flags are not independently adjudicated ownership |
| Main / strict / endpoint-only gold pairs | 7,338 /4,939 /10,041 | Independent closures and population masks match |
| Main gold pair categories | 169 core /2,591 inter /4,578 non-core | Match |
| Tagger messages / PERSON strings / resolved rows | 166,977 /271,566 /985,288 | Independent counts match |
| Cc proxy agreement | 13,446 /19,016 =70.7089% | Match; not manual referent precision |
| Cleaner agreement / empty outputs on 5,000 | 77.22%; ours 7.38%, ERP 3.54% | Full stage replay matches; neither cleaner is ground truth |
| Residual original-message / forwarded / header markers, ours versus ERP | 0.08%/2.00%; 0.04%/5.98%; 0.96%/7.82% | Full stage replay matches README rounding; empty-cleaner control is zero |

The following complete main-score table is independently reproduced from the supplied current graph/labels, not merely copied from the README. All confidence intervals and paired arithmetic below agree within CSV rounding.

| Measure | Title proxy: accuracy, 95% interval | Gold main: accuracy, 95% interval |
|---|---:|---:|
| Degree | 66.58% [59.02,73.37] | 89.55% [82.54,93.79] |
| PageRank | 62.89% [55.70,70.10] | 91.70% [85.88,95.13] |
| Weighted received | 62.28% [55.45,68.74] | 88.81% [82.49,93.12] |
| Messages sent | 52.90% [44.69,60.10] | 75.67% [67.58,83.06] |
| Betweenness | 58.29% [50.51,65.64] | 78.97% [67.38,87.39] |
| Mention degree | 73.06% [66.29,79.11] | 90.45% [83.41,94.70] |
| Mentioned-to | 70.43% [63.09,76.59] | 92.20% [86.91,95.20] |
| Third-party mentioned-to | 69.58% [62.09,75.87] | 92.04% [87.14,94.89] |
| Custodian | Not a title-table row | 65.60% [53.45,77.23] |

### Main versus strict hierarchy policy

The new implementation removes all incident relations of the selected flagged records **before** recomputing reachability: the main policy uses the eight mixed-position records; strict uses the 23-record union. Independent adjacency-list reconstruction verifies those operations and dependence flags (`gold_identity/gold_verify.py`; `gold_standard.py`, population selection at `gold_evaluation.py:170–186`). It is no longer just excluding endpoints.

Treating mixed support/other positions as stronger ownership evidence than several name components behind a record's addresses is a **defensible exploratory distinction**. It is not independent proof that the eight flagged records are the only bad paths or that every multiple-person flag is a real merge. There are 20 multiple-person flags, overlapping five mixed-position flags: 15 additional records, not 20. For example, same-surname near-spellings remain a plausible false-flag mechanism; inspected record `31382` is a candidate, not an established false flag. I found no evidence establishing that the main choice was made to inflate the score; the strict choice actually gives a higher score. That observation also does not establish preregistration. Freeze the policy now and obtain author/adjudicator guidance.

| Population / weighting | Pairs | Degree |
|---|---:|---:|
| Main: mapped, no dependence on mixed-position records | 7,338 | 89.55% |
| Strict: no dependence on any of the 23 uncertain records | 4,939 | 92.88% |
| Earlier endpoint-only exclusions | 10,041 | 83.79% |
| Matched including uncertain records | 11,037 | 84.85% |
| All reconstructed pairs, unmatched scores zero | 13,241 | 77.11% |
| Name+address matches only | 4,328 | 89.49% |
| Without Lay and Skilling | 5,377 | 85.78% |
| Main, equal weight per dominant employee | 7,338; 265 dominants | 76.27% |
| Position nodes closed before mapping, evaluated subset | 6,608 | 94.58% |
| Cycle arcs removed before closure, evaluated subset | 9,996 | 83.72% |

Main→strict removes 2,399 pairs; endpoint-only→main removes 2,703. Changes in these scores are **changes of evaluated population**, not model improvements. The independent constructions produce 8,916 position-first and 12,606 cycle-removed raw pairs; no construction here recovers the original historical pair count. Current matching still includes 424 address nodes and four employee records sharing two graph keys; treat uncertainty and bootstrap identity units explicitly rather than inferring perfect identities from successful arithmetic.

### Mention gains versus coverage

The supplied 2014 paper and `mentions.py` were compared directly. The implementation tags estimated authored text with spaCy, constructs name-compatible candidates, and resolves separately for each recipient by minimizing the sum of unweighted, undirected communication-graph distances from sender and recipient to the candidate; tied minima abstain. Mention degree counts distinct neighbors in the recipient–mentioned-person graph, whereas mentioned-to counts directed outgoing neighbors from the recipient. This captures the paper's central distance heuristic, but substitutes spaCy for its entity detector, changes the corpus/graph and eligibility rules, and adds a 5,000-character text cap. It is an adaptation, not an exact historical replication; unspecified details such as tie handling must remain explicit in Methods.

| Main-gold subgroup | Pairs | Degree | Mentioned-to | Paired gain, 95% interval (percentage points) | Custodian |
|---|---:|---:|---:|---:|---:|
| All | 7,338 | 89.55% | 92.20% | +2.64 [0.74,5.47] | 65.60% |
| Core | 169 | 90.53% | 84.02% | −6.51 [−22.73,7.22] | 50.00% |
| Inter | 2,591 | 95.47% | 95.79% | +0.33 [−1.33,2.50] | 94.17% |
| Non-core | 4,578 | 86.17% | 90.47% | +4.29 [1.88,8.06] | 50.00% |

These paired intervals independently reproduce. The reported non-core advantage is supported by this conditional calculation; universal subgroup superiority is not. Gold **mention-degree** gains only +0.90 points [−1.04,2.78]; the positive gold headline specifically concerns **mentioned-to**. The title headline concerns mention-degree, +6.47 points [3.18,10.13], on its different 6,235-pair target. Comparisons are conditional on fixed reconstructed identities/labels and are exploratory, not corrected for all model/policy selection.

## 3. Findings by severity

### Critical

No newly demonstrated critical scoring or hierarchy-closure error. The previous endpoint-only path defect is repaired in the current declared main population. The following issues still block stronger empirical interpretations or a reliable unattended reproduction certificate.

### Major 1 — The freshness gate still cannot certify downstream results

**Evidence.** `prepare.py:45–57` checks only entries present in the manifest; `:150` writes entries only for messages, senders and copies. `tests/test_corpus_regressions.py:20–27` checks five filenames exist but skips based solely on the absence of `funnel.json`. Run `python "$S/provenance.py" gate`; `provenance/gate.json` records:

- Deliberately wrong configuration and all three recorded output checksums are rejected: the old narrow defect is repaired.
- Replacing identities, sender attribution, person types, links, centrality, mention centrality and gold pairs with invalid bytes gives `stale_reasons=[]`; the actual freshness test passes.
- An empty `outputs` mapping also passes; missing the manifest skips checks while generated artifacts remain.

Separately, `gold_standard.py:259–264` removes processed gold files when the source is absent, but `gold_evaluation.py:159–162` returns without clearing result CSVs or coverage. `gold_identity/stale_probe.py` confirms three processed deletions and four unchanged stale result hashes.

**Impact.** This does not show that the current supplied artifacts are wrong. It shows the claimed certificate can accept a mixed or damaged run, and old hierarchy scores can remain available after a public-only rebuild. The response's M8 “fixed” and README's “any output file”/“delete their outputs” claims are too broad.

**Fix.** A stage-aware manifest must enumerate mandatory inputs/outputs and checksums through identities, threads, graphs, mentions, labels, results and figures; validate its schema, not just present entries. Distinguish a genuinely empty checkout from a missing manifest. Remove or explicitly mark stale result artifacts when a stage is skipped. Tests must corrupt each downstream product, not just the preparation tables.

### Major 2 — Current mention rows are not clean evidence of whom employees discuss

**Evidence.** `mentions/extract.py`, `label_sample.py`, `sample60_private.json` and `sample60_labels_private.json`: seed 2026092604, 60 uniformly sampled resolved rows from 985,288, spanning 59 messages. **51 supported referents, five definite errors, four uncertain: 85.0% supported, Wilson 95% 73.9–91.9%.** Accepting every uncertain case gives 91.7%. This estimates row-level referent support, not NER recall, unique-edge precision or correct authorship. Two supported cases have only moderate evidence; the label file records them rather than silently treating all decisions as certain.

Three sampled references to Governor Gray Davis resolve to Dana Davis; a Williams pipeline-company mention resolves to Jo Williams; “Ste.” in a company name resolves to Clemens Ste. Four otherwise correctly resolved rows come from residual quoted headers. Fourteen are sender signatures, three further sender self-contact lines; ten involve rosters/tables. These categories are not all errors, but neither are they all fresh discussion of other employees. Two rows refer to a person explicitly identified as an IBM contractor: a person key is not verified Enron employment.

`mentions.py:78–90,111–122` chooses among compatible in-inventory people or abstains on reachability/ties, without a contextual none-of-the-above decision. `:224–227` uses analysis/non-null-sender eligibility rather than person-text: **1,872 non-person-sender messages** contribute **8,403** resolved rows. The exact type counts are 1,115 role, 515 address, 181 list and 61 ambiguous messages. This is an eligibility decision requiring disclosure and sensitivity analysis, not proof all those references are invalid.

**Impact.** The network can attribute public-news names and old correspondents to present employee discourse. Signatures and rosters can encode identity, participation and collection structure without measuring organizational dependence. Reproducing 92.2% ordering accuracy does not resolve that construct problem.

**Fix.** Add validated residual-quote/signature redaction, contextual NIL/non-person handling, person-text-only sensitivity, and a blinded message/edge-level validation sample. Preserve a separate raw noisy baseline rather than silently changing the measured object. Re-run the same fixed evaluation pairs after each ablation.

**Important counterevidence:** the existing third-party-only measure scores **92.04%**, versus 92.20% for all mentioned-to; its paired gain over degree is +2.49 points [0.44, 5.58]. Thus I cannot claim the entire gain is sender signatures. That variant still allows quoted third-party names and wrong referents, so it is not a substitute for redaction/validation.

The pipeline is a **method adaptation**, not a replication of 2014 accuracy: spaCy replaces AceJet, candidates and graph coverage differ, only estimated authored text is tagged, the first 5,000 characters are used, and equal-distance cases abstain. `mentions.py:55,125–128,224–246` defines those choices. The minimum combined sender/recipient hop distance, per-recipient resolution and distinct-neighbor measures agree with the paper's intended construction; those algorithmic correspondences do not validate every detected entity or referent.

### Major 3 — The signature filter deletes substantive messages, while ordinary signatures remain

**Evidence.** `text/extract.py`, `filter_labels.py`, `signature_flagged30_labels.json`: fresh seed 202609265, 30 random flags from all 1,366. Two are substantive false exclusions (**6.7%, Wilson 1.8–21.3%**): `maildir/zufferli-j/sent_items/98.` is an analyst/associate ranking table; `maildir/jones-t/notes_inbox/3821.` contains the answer **“Not I.”** followed by a signature. Both otherwise satisfy analysis eligibility. The latter is precisely the short speech-act signal Phase 3 aims to retain. `senders.py:107–121` tests capitalization, word counts and contact/title-like lines, not whether the first line actually names the sender; period-bearing “Not I.” passes. This contradicts the categorical speech-act-preservation description at `:100–103`.

A separate 60-message random analysis-set sample (seed 202609267) contains one missed calendar record and one retained quoted-prose case. No pure signature-only false negative appears in that SRS (0/60; Wilson upper bound 6.0%); that does **not** imply signatures inside prose are absent. An enriched short-contact-text sample finds a pure signature beginning “Cordially”; it demonstrates a miss but cannot estimate corpus prevalence.

For newsletters, 28/30 random marker positives are newsletters/feeds/ads; two are substantive mailing-list conversations with an unsubscribe footer (6.7%; same interval). Both are external senders, so this sample does **not** demonstrate an incremental internal-person analysis loss from those two false positives. The sampling frame is all 6,159 marker matches, not just newly excluded messages. These distinctions matter: 1,366 signature flags translate to **794 marginal analysis exclusions**, not 1,366 unique removals.

**Impact.** Removing actual short responses can bias speech-act frequencies, while retained quotes inflate the wrong person's text. Current errors are not all in the conservative direction.

**Fix.** Require a sender-name/contact anchor for a signature and preserve any preceding utterance; add the ranking table and “Not I.” as regressions. Distinguish transport footers from wholesale copied newsletters. Validate marginal internal-person exclusions separately from all raw flags, and report precision/recall with labelled negative samples.

### Major 4 — Inferred replies still include wrong parents and relays

**Evidence.** Fresh seed 202609264, simple random sample of 60 current reply-kind links; full child/parent bodies in `text/fresh_reply60.json`, row labels and explanations in `text/fresh_reply60_labels.json`. **47/60 supported direct replies (78.3%; Wilson 95% 66.4–86.9%)**, six wrong immediate parents, three relays, four uncertain. Even accepting all four uncertain cases gives 51/60, 85%. This is a confirmed-support fraction with unresolved annotation uncertainty, not fully identified true precision or recall.

The original audit's 24/31 regression statistic reproduces. Of audit-3's supported examples, 50/50 remain; all four known wrong immediate parents remain too. The fresh 47/60 does not establish a deterioration from 50/60—the intervals and samples are too small—but it does not establish improvement either. No current link has a probable-copy child/parent or identical sender, so those mechanical exclusions work.

Examples: `lavorato-j/sent_items/591.` first quotes Louise but links Kevin's nested ancestor; `kitchen-l/_americas/netco_legal/46.` substitutes an older ancestor after a self-sender candidate is skipped; `kaminski-v/stanford/7.` forwards Susan's message but links Christie's separate decline. `threads.py:112–120` permits an ancestor text match to override the quoted-author restriction, which applies only when the candidate text is absent. `:124` treats an addressed recipient as sufficient for reply-kind, which also admits relays. `text/probes.py` reproduces both problems in tiny controls. `_LOTUS_FROM` at `threads.py:136–156` also requires slash/@ decoration, so a valid bare-name first quote followed by a nested Outlook header can return the nested author instead. Angle-only quote inversion remains a tested negative boundary, not a measured fresh-sample prevalence.

**Impact.** Thread-dependent speech acts, response latency, delegation or dependence features inherit wrong causal ordering. These links should not be described as observed replies or used as truth for model evaluation. README lines 79–81 overstate the quoted-author constraint: a quoted author does not always determine the parent under the implemented text-match exception.

**Fix.** Keep confidence/evidence categories and abstain where the immediate quoted author conflicts with an older matching body. Validate author extraction itself; add independently labelled true-reply sampling to estimate recall. Report precision and abstention by evidence type rather than recycling the tuned first sample.

### Major 5 — The explicitly claimed Phillips recipient repair still fails

**Evidence.** `identity.py:328–333` computes surnames differently for known person keys and unresolved addresses. In `maildir/forney-j/sent_items/96.`, the kept recipient `phillips.george@enron.com` contributes “george” to the surname set, so the extra known person George Phillips is admitted. `gold_identity/forney_retest.json` calls production `build_edges` on the current row: both targets receive weight 0.1 among ten targets. Rereading both relevant messages from the pinned raw tar reproduces all nine archived header fields; the display header contains one George Phillips, not two people. That recipient gets combined weight 0.2 while other recipients get 0.1 instead of 1/9.

`recipient_scan.py` identifies **12 Forney/Phillips and two Beck/Hughes network messages**. Fresh raw-tar headers confirm all 14 duplicate one display-header recipient (`extra_header_review.json`, `extra_current_headers.json`); they are not merely spelling-based candidates. Removing those 14 admitted extras, leaving the kept representations unchanged, changes weights/counts but removes **zero aggregate directed edges**, so this narrow sensitivity changes no degree values or degree accuracies (`duplicate_impact.json`). Replacing/merging the base aliases is a different intervention and must not be conflated with that result.

**Impact.** The response specifically says Phillips's second spelling is not added; that claim is false. Person-level weights remain wrong even where aggregate degree is unaffected. The surname guard also has an unvalidated coverage cost: a fixture with two known distinct Smith recipients drops the second, while its frozen surname set can admit two same-surname extras beside another surname. No current natural false exclusion of two proven distinct same-surname people was established.

**Fix.** Resolve recipient identities using original display headers and verified alias evidence before union/weighting. Do not use shared surname alone as proof of identity. Add the real reversed-name Phillips case and distinct same-surname negative controls; quantify ambiguous additions rather than silently treating them as settled people.

### Major 6 — Tightened header syntax reintroduces quoted text into analysis

**Evidence.** Fresh unflagged #56, `maildir/jones-t/notes_inbox/964.`: audit-3 cleaner isolates 143 authored characters, current cleaner returns 772 and includes Tana's quoted header/question. `text/supplementary.py`, `audit3_semantic_clean_comparison.json` reproduce the old/current strings and equality with the current artifact. The last wrapped recipient line is a plain company-name word without slash/@; `clean.py:38–39,59–60` requires that decoration on continuation lines. This is a semantic rule regression, not a tok2vec or quote-start-precomputation defect.

**Impact.** The sender inherits another person's words and named entities. That directly contaminates speech acts, topic ownership and the mention baseline. Of 193 old/new natural bodies checked, four change: this harmful expansion and three intended cuts. This is evidence of a concrete regression, not a population error-rate estimate.

**Fix.** Recognize valid wrapped headers with bounded structural parsing and negative prose controls rather than requiring punctuation on every line. Add this exact multiline header; then validate quoted-span precision and recall on a fresh sample, including inline answers.

### Minor findings and test gaps

1. **Name compatibility is not full-name compatibility.** `mentions.py:67` entirely omits **37/5,562** graph-person keys, all hyphenated, even from surname lookup. `:83–90` discards explicit middle/final initials; Mark A. and Mark E. Taylor both produce both candidates. The shared short-name/initial namespace makes Ed and E.D. ambiguous in a controlled fixture. There are 1,241 two-letter detected strings, not 1,241 established errors. `mentions/fixtures.py`, `initial_examples_private.json`, `unsupported_people_private.json` supply examples/counts. Normalize punctuation consistently; retain explicit distinguishing initials; keep nickname and initial indexes separate; measure changed real resolutions before claiming benefit.
2. **Cc agreement is endogenous weak-label agreement, not independent validation.** `mentions.py:179–183` evaluates only the first To recipient; `network.py:63–70` includes Cc edges in the same graph used for distance. A fixture adding only that Cc edge changes abstention to the proxy label. Exact 70.71% comprises 84.70% on 8,104 single-candidate cases and **60.32% on 10,912 ambiguous cases**; 2,406 necessarily abstain because their first To is external and absent from the graph. This does not establish that including those nodes would resolve them correctly. No observed label came from To/Cc-extra mixing, despite that latent implementation risk. Call it a transductive proxy check, stratify ambiguity/coverage, and use withheld-edge or independent annotation checks. Its numerical proximity to the paper's 69.7% on a different graph/sample is not validation.
3. **Mention cache invalidation is incomplete for future changes.** `mentions.py:131–147` keys on truncated text and model name/version, not tokenizer/config, spaCy version, weights, tagger code or lockfile. A same-name/version fake tagger changes output but is never called for a cache hit (`mentions/fixtures.json`). This is a demonstrated invalidation hole, not demonstrated current cache corruption: all 300 independently retagged sample texts matched. Include model/config/implementation digests in the cache stamp.
4. **A secondary dedupe chain remains noncanonical.** `dedupe.py:144–149`; `gold_identity/synthetic.py` reverse-chain fixture A(id1/bodyA), B(id1/bodyB), C(id2/bodyB): A survives, B maps to A, C maps to removed B, and C's extra recipient is lost. The current corpus has zero secondary Message-ID removals, so no present headline effect is asserted. Chase every copy to a final live keeper and fold recipients at that representative; test both orderings.
5. **Passing tests still miss important behavior.** Mention tests: five baseline passes, **eight of 13 mutants survive**, including sender-only distance, directed distance, first-recipient reuse, Cc leakage/deletion, model-version invalidation removal and truncation to ten characters. Text tests: 64 baseline passes, eight of nine mutants killed, but disabling quoted-author extraction survives because the test supplies `quoted_from` directly. Gold arithmetic tests kill 16/17 historical mutants, versus 11/17 before; all ten historical identity/dedupe mutants are killed. Across the combined gold/identity probes, 30/32 unique mutants are killed: resampling shared graph keys and accepting unresolved extra addresses without checking person membership survive. Preparation tests kill checksum/config bypasses but allow constant Python/lock stamp values. These are gaps in protection, not evidence those mutations exist in production. See all three agents' `mutations.py/json` and `provenance/mutations.json`; add end-to-end extraction, separate-recipient and shared-identity oracles.
6. **Disclosure needs tightening.** README's “own text” is an estimate, not guaranteed exclusion of old quotes; “people” includes unresolved recipient nodes in some mention outputs; the 5,000-character tag cap needs Methods disclosure. Exactly 1,755 analysis texts exceed that length, but this includes texts without a resolved sender, so it is not an exact count of tagged messages truncated. Its statement that degree has the highest title-proxy estimate should specify *email-only* measures. The claim that any output is checked/deleted is disproven above. The mention gains and rounded gold scores themselves reproduce; they are not numerical overclaims.
7. **The supplied final-run stamp predates the final code edit.** `python "$S/stamp_snapshot_probe.py"` reproduces `stale_reasons=["built by different code"]` against the fixes-worktree artifacts. Their saved code hash, `41446e21…`, exactly matches regeneration commit `1c7a75b`; pinned current code hashes to `42671c7c…`. The intervening source diff adds only three mention-measure labels in `figures/baselines.py:22–24`. This is a release-packaging/stamp discrepancy, not evidence of changed numerical results: all regenerated tables and figures match the supplied outputs. The figures already have the new labels; `figure_control.py` confirms old labels produce different Figure 6 bytes. The reported 13 passing corpus checks describe the earlier regeneration state, not a current-source freshness certificate; the fresh scratch replay does pass all 13. Regenerate the complete manifest after the last source edit and validate all stage outputs; do not disable the check to make the old stamp pass.

## 4. Phase 3 risks and required tests

1. **Freeze the target and population.** Keep title-proxy, reconstructed-main and strict hierarchy results separate. Resolve or explicitly retain uncertainty about mixed positions, names and custodians before comparing new models; do not select exclusions by which raises accuracy. Request author clarification about the 13,241/13,724 and immediate-relation discrepancy and the eight mixed records. A hierarchy-prediction score is not validation of functional importance.
2. **Redaction and negative controls.** Compare raw, current-cleaned, signature/quoted-header-redacted, and signature-only text on identical pairs. Mask names, addresses, explicit titles, department identifiers and templated footers in separate ablations; report what actually drives prediction. Title words in available email are not automatically train/test leakage, but they are a direct-rank shortcut rather than evidence of dependence.
3. **Coverage controls.** Retain custodian, messages-sent/received, observation span and missingness baselines. Report core/inter/non-core and equal-manager macro scores; compare on matched exposure or adjust for observation volume. The inter custodian baseline alone is 94.17%, so a large pooled score is insufficient.
4. **Proper model splits.** Use employee-disjoint and time-respecting splits, group duplicates/threads, and fit preprocessing/selection only within training data. The current mention resolver is transductive over the full email graph; a claimed prospective result needs a graph built only from information available at prediction time.
5. **Independent annotations.** Have blinded human annotators validate entity referents, employees versus outsiders, true authored spans, and true replies; estimate both precision and recall. Keep uncertain cases and adjudication logs. Validate unique edges as well as mention instances so large recipient lists do not determine the entire error estimate.
6. **Interpret paired intervals narrowly.** Current employee-bootstrap arithmetic is correct conditional on fixed identities/pairs; its intervals do not propagate matching, annotation or population-selection uncertainty. Predeclare a primary mention measure and comparison; report all measures rather than present different winners as a single universal superiority claim.
7. **Independent functional-importance outcome.** Before claiming functional importance, specify an outcome not algebraically defined by the same graph/text score—plus a credible temporal design and exposure controls. Rank disagreement alone does not establish that either side measures operational value.

## 5. Reproducibility, performance and limits

The copied Makefile was exercised with a logging-only `uv` shim under `make -j8 all` (`provenance/make_trace.jsonl`): all 16 commands ran in the intended dependency order, with maximum one active command. This checks scheduling, not numerical execution. The actual scratch replay uses separate stage subprocesses and redirected output paths, rather than running `make all` against either protected checkout.

The independent title-pair oracle (`oracles.py`) reproduces all eight measures and person-bootstrap intervals within CSV rounding (maximum discrepancy below 5e-11). It reproduces mention-degree minus communication degree as **+0.0647153**, paired interval **[0.0318043, 0.1012869]**. The independent gold oracle (`gold_identity/numerical.py`) explicitly materializes repeated pair copies rather than calling production scoring functions: **36 main, 288 sensitivity, 32 paired and nine macro rows** agree within 5.01e-11. The separate raw-address oracle reproduces all four rows, including **83.094177%** on 13,241 pairs. This is a local-method comparison, not recovery of the paper's exact network/population.

Controlled performance checks (`text/probes.py`, `supplementary.py`): 204 raw/fixture cases, **203 old/new regex outputs identical**, one old-regex timeout even at five seconds, no observed completed mismatch. Start-precomputation yields identical authored text and quote-presence flags on all 204; a 480-message subset gives identical 200 linked rows and null-normalized quoted authors. An initial comparison treated NaN versus None as different; those 206 representation differences are not changed author assignments. A separate synthetic CR-only body **does** change the quote-presence flag (false→true), because the new caller normalizes line endings first; authored text is unchanged. Thus universal byte-domain equality is false, although the observed corpus sample agrees. Separately, semantic cleaning-rule changes since audit 3 introduce a natural quoted-text miss; that is not attributed to the tok2vec optimization.

`mentions/spacy_control.py`: 359 texts, 3,689 entity spans including 1,043 PERSON spans; disabling shared tok2vec changes **zero** documents/spans. Separately, 300 newly tagged sampled texts match the saved tag cache exactly. The configured NER has its own embedding layer. This supports the claimed optimization on this model and these samples; it is not a fresh full-corpus NER run or a guarantee across future model versions.

### What I could not establish

- The authors' intended owner for every merged/multi-position record, the exact historical 2012 graph/pair population, or whether release-version changes explain every discrepancy. No author contact was attempted. The private source was hash-checked and decoded locally, with adjacency and closure independently reconstructed; it was not redistributed.
- Blinded human precision/recall for identity, gold matching, authorship spans, NER or reply reconstruction. The fresh samples are AI-auditor readings; an SRS of predicted positives cannot determine recall. No global current false-exclusion rate for same-surname recipients was established.
- That the 20 multiple-person flags all identify different people rather than name variants; that 424 address-node matches are all the intended employee; or that corpus mailboxes are a fully verified historical custodian definition. Numeric agreement does not answer those questions.
- A fresh parse of every raw message or a completely uncached NER pass. The scratch rebuild reuses checksum-verified parsed/tag caches and recomputes later stages; the separate 300-text retag and 359-text tok2vec control test different, narrower claims. All cache reuse is explicit.
- Full-domain equivalence or a stable speedup factor for the performance changes. One old regex comparison times out at five seconds, the CR-only counterexample differs, and timings are under host contention. Chunked-cache checkpointing was read and cache tests run, but no process-kill test was performed at every write boundary.
- A causal interpretation of rank agreement as functional importance, robustness to unseen institutions, or uncertainty that includes annotation/identity/population selection. Those require subsequent research, not another arithmetic replay.

### Evidence index

`setup.py`, `extract.py`, `initial_*_hashes.json`, `initial_git.json`: pinning, source copy and archive extraction. `provenance.py`, `old_provenance_replay.py`, `runtime.py`, `oracles.py`: tests, poisoned-cache replay, gate mutations, package inventory and independent title calculations. `reproduce.py`, `compare_rebuild.py`, `figure_control.py`, `stamp_snapshot_probe.py`, `final_hashes.py`: scratch stage replay, output comparison, separate-process figure reproduction, source-stamp diagnosis and preservation checks. `gold_identity/{gold_verify,identity_verify,synthetic,recipient_scan,stale_probe,numerical,raw_degree_oracle,mutations}.py`: structural/numerical/identity probes and original counterexamples. `text/{extract,replay,replay_light,probes,supplementary,labels,filter_labels,mutations}.py`: original/new text checks, all row labels and performance controls. `mentions/{extract,normalize_summary,cc_recheck,fixtures,label_sample,spacy_control,mutations}.py`: paper-method checks, mentions, proxy stratification and fresh samples. Private or message-level evidence in these folders must not be copied into a public repository wholesale.

