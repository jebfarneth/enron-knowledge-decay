# Independent audit 3 — Enron data and hierarchy evaluations

Audited revision: `a3599244c2431dc6f88c585ec096c4f10e632a87` (`main`). Audit date: 2026-09-25. Scratch evidence: `/tmp/enron-audit3-20260925.dnpSbE`.

## 1. Executive verdict

**Data layer: yes with conditions for exploratory Phase 3 development, not as a validated person-authored dataset. Title-proxy evaluation: yes with conditions as a descriptive, noisy formal-title baseline, not a validation of functional importance. Gold-standard evaluation: no, not yet as a validated hierarchy benchmark.** The specific identity fixes and many reported counts reproduce, and an independent calculation reproduces the title accuracy and bootstrap intervals. Nevertheless, recipient union introduces demonstrable duplicate-recipient targets; a previously flagged long bulletin, non-person accounts and signature-only records pass the person-text gate; reply links still include wrong immediate parents; and quote/signature contamination persists. In the gold evaluation, mailbox order changes the evaluation population, and excluding flagged mixed-position endpoints leaves 3,103 pairs that depend on flagged mixed-position intermediaries. These are measurement and population-definition problems, not evidence that every affected label is false. Before confirmatory text-model results: rebuild a provenance-consistent artifact set; repair or explicitly quarantine the demonstrated identity/recipient errors; validate authored spans, automation and person attribution on held-out labels; and resolve or prespecify conservative sensitivity treatments for gold matching and mixed-owner paths. Neither title agreement nor hierarchy agreement, by itself, establishes functional importance.

### Scope, preservation and reproduction conventions

The main checkout was clean and at the requested revision at entry. It did **not** contain the final regenerated data described in the request: `links.parquet`, `links.json`, `person_types.parquet`, `person_text.json` and `gold_coverage.json` were missing, and other processed tables were older. The permitted fixes worktree held the final-run artifacts. I hash-pinned those artifacts and used them **read-only**, with the requested main source, for current-data probes; I did not treat the fixes worktree's evolving source as audited code. `initial_hashes.json`, `initial_git.json`, `fixes_hashes.json` and `main_fixes_differences.json` record this distinction.

All scripts, generated fixtures, mutated implementations and private-release evidence are outside the repository. Mutations run in scratch/in memory, never against the working tree. This report is the only repository file added by this audit; it is left uncommitted. The final hash check is reported below.

In the evidence references below, `R=/Users/jebfarneth/projects/enron-knowledge-decay`, `S=/tmp/enron-audit3-20260925.dnpSbE`, and `F=/Users/jebfarneth/projects/enron-knowledge-decay-fixes`. Notation such as `python S/text/attacks.py` abbreviates the **exact executable commands in the command index below**, rather than a literal shell path named S. Unless noted, commands run from R using `.venv/bin/python`, with `PYTHONDONTWRITEBYTECODE=1`; pytest uses `-p no:cacheprovider`. Later runs also set `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1` after severe host resource pressure. Evidence paths are relative to S; source lines refer to `src/enron_importance/` at the audited revision. All abbreviated public message paths are relative to the raw corpus's `maildir/`.

The old archives were extracted as ordinary files/directories only; two archived absolute symlinks were deliberately not followed. `prior/extraction.json` records this. Original probes were rerun with documented scratch/input-path substitutions and API/schema adapters where the current code changed. An adapted probe is not represented as a byte-for-byte execution of an incompatible old interface. Older before-values are distinguished from current reruns.

All five identity/dedupe originals (`probe.py`, `quantify.py`, `initial_probe.py`, `dedupe_probe.py`, `dedupe_review.py`) exit successfully under the recorded adapters (`identity/replay/adaptations.json`). Two old diagnostics need interpretation: modal-address-only type derivation reports obsolete 166,035/60 person-text/ambiguous counts rather than the current all-key 166,034/61; raw-keeper-only recipient comparison still reports the historical 82 groups/141 assignments, while current processed unions lose zero of those assignments. All 262,249 current copy mappings point to surviving messages. The original gold hierarchy, matching, absent-key, raw-degree, name-sensitivity, score-policy, quick-diagnostic and literal-copy oracle probes were replayed; expensive superseded full private-email-network evaluation and old automatic labeling blocks were not represented as rerun.

### Environment and artifact reproduction

`uv sync --locked --group dev --project "$S/pinned_project"` succeeds against a scratch copy of the pinned source and lockfile. All 26 installed package versions match the existing environment; both use Python 3.12.13 (`uv_sync.log`, `provenance/runtime.json`). Executing the freshly installed environment stalled in macOS native-library loading under severe host load; the subsequent stage rebuild uses the existing environment with `PYTHONPATH="$S/pinned_project/src"`, not a silently changed dependency set. This verifies lock resolution and matching versions, **not a completed pipeline run in the fresh environment**.

The downstream rebuild uses the checksum-verified existing parsed cache, SHA-256 `2460bc2b9a5be00d36a1d8769b1b1d072fe7779071eef27d40eba0676f7bd607`. A fresh archive parse was attempted but stopped under resource pressure; its partial output remains in scratch. I do **not** claim a completed fresh parse. The compressed raw archive was independently reread/hash-checked in full by the header replay: `b3da1b3fe0369ec3140bb4fbce94702c33b7da810ec15d718b3fadf5cd748ca7`, 443,254,787 bytes. Matplotlib uses the archived same-machine font cache; cross-platform rendering determinism is not established.

All **12 downstream stages complete successfully in separate processes**, from preparation through both figure modules (20:22:44–21:21:14 EDT, approximately 58.5 minutes; `reproduction/run.log`, `reproduction/stages.json`). The post-build corpus suite passes **13/13** on these scratch outputs (`reproduction/corpus_regress.log`), unlike the skipped suite on main's stale data. The existing 136 non-corpus tests also pass.

`reproduction/comparison.json` compares every output against the **initial** fixes-worktree hashes: all **30 regenerated data/result/figure files other than `funnel.json` are byte-identical**. That manifest's only changed field is `config_sha256`, because scratch output paths differ; its source hash, 21 funnel counts and output checksums match. The two reused cache files also match, but are not counted as regenerated. This establishes same-machine, locked-version reproducibility from the existing parsed cache—not fresh-parse or cross-platform reproducibility.

The closing preservation check (`provenance/final_preservation_before_report.json`) finds **all 153 initially hashed main files unchanged**, main still at the requested commit and clean before adding this report. Of 33 initially pinned fixes-worktree artifacts, its **three gold result CSVs changed during concurrent work** (`baselines_gold_standard.csv`, `gold_standard_paired.csv`, `gold_standard_sensitivity.csv`); the other 30, including every relied-on input table, remained unchanged. Those later CSVs were not substituted into this audit. The freshly regenerated gold CSVs match the initial hashes and the unchanged committed main results. The hash differences are preserved rather than concealed. No pipeline code, configuration, input data or git history was changed by this audit.

The completed preparation rerun (`reproduction/prepare.log`) reproduces all 21 funnel values. Messages, senders and copies are byte-identical to the pinned final-run artifacts. Key counts:

| Quantity | Fresh preparation value |
|---|---:|
| Parsed-cache rows / in window / outside / undated | 517,401 / 516,359 / 1,042 / 0 |
| Content copies removed / secondary Message-ID removals | 262,249 / 0 |
| Unique messages / candidate separate sends / added recipient assignments | 254,110 / 233 / 141 |
| Probable shifted copies / messages with quoted material / with authored text | 1,531 / 112,281 / 234,316 |
| Sender addresses / flagged senders | 20,293 / 312 |
| Messages from flagged senders / message-level automation | 9,464 / 9,429 |
| Structured / routine / routine excluded | 3,297 / 6,745 / 3,308 |
| Analysis messages / sender addresses | 169,044 / 6,337 |

Subsequent fresh stages reproduce 166,034 person-text messages, 5,524 person-text keys, 40,073 links and 214,037 threads. The regenerated graph has **20,782 nodes and 219,398 directed edges**: 5,572 person-typed, 130 role, 305 list, two ambiguous and 14,773 unresolved-address nodes. Both edges and exact centrality tables are byte-identical to the pinned final-run versions (`reproduction/network.log`; centrality SHA-256 `82c38beb86a767a3f500c3c5fc1707463804929b4988ac9cae574dbd58069278`). Gold pair construction also regenerates byte-identically.

## 2. Verification of the claimed fixes

“Fixed narrowly” means the reported counterexample was reproduced and corrected; it does not certify the whole heuristic. A response can accurately describe a code change while overstating closure of the underlying research problem.

| Audit | Finding | Claimed status | Verified status | Reproduced effect and evidence |
|---|---|---|---|---|
| Re-audit | M1: go-by names, minority initials, title joins | Fixed demonstrated cases; joins open | **Fixed narrowly; broader ambiguity remains open** | Dana/Mark-Dana internal records unify (351 + 13); the 66 uninitialled Palmer messages remain ambiguous rather than inheriting the minority initial. Old named counterexamples resolve as described. Regenerated title joins equal current artifacts: 161 rows, 160 matched rows, 129 distinct titled keys. Independent degree = 66.5838%. `identity/verify.py`, `identity/verify.json`, `identity/title_joins.csv`; `provenance/title_oracle.py`. All 129 keys being person-typed does not independently validate all joins. |
| Re-audit | M2: title suffixes, shared mailboxes, person-text | Fixed demonstrated cases | **Partly fixed at the dataset level** | Wasaff/Knight/room examples corrected; all 610 messages with parsed CN=MBX_ IDs are role-typed. Exact funnel: 169,044 analysis messages → 166,034 person-text messages, 5,524 keys. Excluded type counts: unknown 1,194; role 1,057; address 517; list 181; ambiguous 61. But 57 records from four demonstrably non-person accounts still pass person-text under other header renderings (M5 below). `identity/verify.json`, `identity/targeted.json`. |
| Re-audit | M3: full utterance and whole-text routine rule | Fixed | **Code defect fixed; original contamination partly moved** | Current routine count 6,745; excluded 3,308. The old long examples are no longer short speech acts, but all five still enter analysis because `routine=False`, but the new person-text gate excludes four; one remains in person-text. Another 195 signature-only records enter person-text. The response's “no longer exempt” is narrower than removing the demonstrated contamination. `text/rerun_archived.py`, current routine/attack outputs; M4 below. |
| Re-audit | M4: wrapped headers, structured records, daemon | Fixed demonstrated formats | **Fixed narrowly; broader cleaner/classifier unvalidated** | All four old wrapped-header counterexamples now cut at the intended boundary; original Received/agenda negatives survive. Structured count 3,297 reproduces. New broad PEP ACCESS rule removes substantive announcements, and new header variants still leak quotations; fresh boundary review finds no definite false cut in its 60-analysis-message sample, which excludes empty outputs by design. This is not a proof of zero deletion error. `text` replay, labels and attack evidence; M7 below. |
| Re-audit | M5: person-level threads, addressed-back rule | Partly fixed | **Partly fixed, correctly left open** | 40,073 links = 31,238 replies + 8,835 forwards. Old first-audit positives: 24/27 retain same-parent reply links; two become forwards, one changes parent. Of the previous re-audit's 43 supported links, 42 remain same-parent replies, one becomes forward. Fresh 60-link sample: 50 supported direct, six negative, four uncertain. The old 72.7% is 24/33 same-parent reply-kind links, not all 36 currently reply-kind children. `text/fresh_reply60_labels.json`; `validate_threads.py:34–58`. |
| Re-audit | M6: union recipients across copies | Partly fixed, Anderson open | **Partly fixed, with new confirmed graph regression** | 141 address assignments restored across 82 groups; 233 candidate separate sends across 194 groups. Calger is restored. Anderson remains unresolved/misattributed as acknowledged. Union now also counts verified duplicate-recipient representations as separate graph targets (M3). `identity/attacks.json`, `identity/union_changes.json`; fresh raw-tar check in `identity/raw_union_header_verification.json`. |
| Re-audit | M7: integration and corpus regressions | Fixed | **Improved, not fully closed** | Current 136 non-corpus tests pass. Generated-pipeline tests catch several old faults. Yet main's stale artifacts cause all 13 corpus checks to skip successfully; the freshness function ignores deliberately invalid configuration and output hashes. Consequential mutants survive focused suites. `provenance/main_corpus.log`, `provenance/unit.log`, `provenance/gate.json`; mutation results below. |
| Re-audit | m1: people-only sent counts | Fixed | **Fixed for reproduced defect** | Rebuilt people-only graph has 5,522 nodes and 163,054 edges; exact sent counts total 150,427, versus 155,779 carried from the old full-graph subsetting approach; 487 sending-node counts differ. Source uses rebuilt counts. `provenance/title_oracle.json`; `evaluate.py` people-only branch. |
| Re-audit | m2: asymmetric relative ties | Fixed | **Fixed for reproduced defect** | Archived numerical-boundary probe finds 220 asymmetric `np.isclose` cases, but current scorer returns 0.5 in either person order on the demonstrated boundaries. No nonexact tolerance ties in the current title pairs. `provenance/old_tolerance.py`, `.log`; independent title oracle. |
| Re-audit | m3: probable copies in threads | Fixed | **Fixed on current artifacts; regression coverage weak** | Zero current links use flagged copies as child or parent; tiny stage controls verify both exclusions. Removing the gate nevertheless survives 56 focused/integration tests. `text` stage controls and mutation logs. |
| Re-audit | m4: cache stamp and Makefile | Fixed | **Original cache corruption/order defects fixed; downstream provenance incomplete** | Original poisoned-cache probe rebuilds four correct rows; stamp now includes Python, lock hash and cached-table hash. Trace of `make -j8 all` with scratch stub executables records all 15 commands sequentially, including post-identity threads, threadcheck and final regressions. This trace tests orchestration, not stage correctness. Configuration/artifact freshness remains unchecked at the corpus gate. `provenance/old_provenance.log`, `provenance/make_trace.jsonl`, `provenance/gate.json`. |
| Re-audit | m5: documentation | Fixed | **Partly fixed** | Many current totals and uncertainty labels match; person-text is separately reported and candidate separate sends are qualified. Remaining inaccuracies include the thread-denominator wording, stale config comments, and public-corpus/all-mail claims listed below. |
| Gold | C1: assistants/mixed people | Matching fixed; release merging open | **Partly fixed, not closed** | The original assistant-selected cases now select the principal; eight mixed-support records are flagged. However, other multi-human records remain unflagged, and 3,103 retained main pairs depend on flagged mixed intermediaries. `gold/current.py`, `gold/structural.py`, `gold/structural_private.json`; M1 below. |
| Gold | M1: coverage and population | Fixed | **Counts fixed; identity precision not established** | 1,518 email employees = 933 name+address + 70 name + 424 address-node + 56 ambiguous + 35 absent. All 1,427 selected nodes exist. Main = 11,372 pairs (360 core; 4,411 inter; 6,601 non-core). Fresh 60-employee review supports 32 and cannot adjudicate 28; graph presence/name agreement is not verified human identity. `gold/current.py`, `gold/manual60.tsv`; M2. |
| Gold | M2: tie-breaking | Fixed | **Partly fixed** | Original lexical arbitration removed; frequency ties abstain and identity ambiguity is respected. But first-matching-mailbox order silently arbitrates conflicts: three records change on reversal, 959 main pairs disappear. `gold/attacks.py`, `gold/attacks_accuracy.csv`; `gold_standard.py:155–169`. |
| Gold | M3: pair construction | Partly fixed | **Partly fixed as acknowledged** | Independent BSON/BFS replay reproduces 13,241 main pairs; alternatives have 8,916 and 12,606. Neither validates the unavailable historical 13,724-pair construction. Position graph is acyclic; owner merging introduces the contradictory employee relation. `gold/replay.py`, `gold/structural.py`, archived decoder outputs. |
| Gold | M4: purported replication | Fixed | **Partly fixed documentation** | Sensitivity now exposes maximum raw-address degree, but README still likens it to the paper's setup; the paper co-references aliases into people. Production sensitivity reads windowed/deduplicated processed messages while calling them “all mail.” See documentation findings. |
| Gold | M5: custodian, macro, leave-two-out, paired intervals | Fixed reporting | **Numerically reproduced; conditional interpretation remains necessary** | Main degree 84.9982%, PageRank 85.5874%, custodian 65.1029%; inter degree 91.8613% versus custodian 88.9367%. Macro, executive deletion and paired comparisons are computed, not independent validation of identity or hierarchy labels. All 168 rows across seven populations match an independent oracle exactly (counts, scores, intervals, retained draws); `gold/numerical_differences.json`. |
| Gold | M6: tests | Fixed | **Partly fixed** | New fixtures catch several prior errors but do not protect mailbox-order conflicts, mixed intermediaries or all alternative-construction/bootstrap behaviors. Focused mutation results below distinguish killed/surviving mutants from harness failures. |
| Gold | m1: empty groups/draws | Fixed | **Partly fixed** | `gold_table` handles empty draws, but `paired_gold` still crashes on a valid one-pair, one-replicate case with no retained pair, and on zero replicates. Main 1,000-replicate output is not shown to be affected. `gold/attacks.py`; `gold_evaluation.py:114–129`. |
| Gold | m2: access/provenance wording | Fixed | **Partly fixed** | Private-release/access and non-replication warnings are present; they do not resolve historical release equivalence, matching uncertainty, or stale-artifact handling. Source SHA verifies supplied bytes, not the claimed private delivery or the 2012 labeling decisions. |

### Independently reproduced title results

`provenance/title_oracle.py` constructs all 6,235 unordered different-level pairs among 129 people, computes half-credit ties directly, and obtains bootstrap intervals by multiplicity-weighting those pairs under seeded person resamples. It does not call the production accuracy/bootstrap functions.

| Measure | Accuracy | 95% interval |
|---|---:|---:|
| Degree | 66.5838% | 59.0068–73.3709% |
| PageRank | 62.8869% | 55.6982–70.0989% |
| In-strength | 62.2935% | 55.4484–68.7773% |
| Betweenness | 58.3079% | 50.5161–65.6445% |
| Out-strength | 52.9030% | 44.6921–60.1026% |

Degree minus PageRank = 3.6969 percentage points, paired interval −0.7729 to +8.1290 points. The CSV values reproduce; README's in-strength lower limit is slightly misrounded (55.5% versus 55.4484%, which rounds to 55.4%). This interval does not establish equality between methods, nor include label/matching/model-construction uncertainty.

### Independently reproduced gold results

`gold/numerical.py` directly enumerates credited pairs and applies per-employee draw multiplicities; `gold/numerical_differences.json` records zero differences from production on **168 rows across seven populations**, including counts, points, interval endpoints and retained draws. Main population results (all 11,372 pairs):

| Measure | Accuracy | 95% interval |
|---|---:|---:|
| Degree | 84.9982% | 73.3118–93.9142% |
| PageRank | 85.5874% | 73.4104–95.2635% |
| In-strength | 82.4745% | 69.2911–92.8888% |
| Betweenness | 75.3605% | 60.6834–87.1569% |
| Out-strength | 68.9632% | 54.7893–80.9822% |
| Release custodian indicator | 65.1029% | 53.1364–77.0121% |

PageRank minus degree = +0.5892 percentage points, paired interval −0.9941 to +2.4935 points. Macro degree across 273 dominant IDs = 76.9771%. Removing Lay/Skilling leaves 8,669 pairs, degree 80.3438%. Cycle-arc removal leaves 10,779 eligible pairs, degree 84.2657%; position-first closure leaves 7,678 eligible pairs, degree 94.7577%. These match the response's rounded effects. These are **different populations**, not interchangeable accuracies on fixed labels. The custodian indicator is `bool(release.mailboxes)` (`gold_standard.py:130`), not independent verification that every named mailbox is available in this CMU release.

The independent all-raw-address calculation gives **83.1017295%**, 86,538 nodes and 331,029 edges; production's processed/windowed/deduplicated input gives **83.0941772%**, 86,370 nodes and 330,474 edges. Both round to 83.1%. Thus the “all mail” label is inaccurate, but its numerical difference here is small. Neither reconstructs the paper's co-referenced person graph. Evidence: `gold/replay_raw.py` and its adapted archived raw-degree outputs.

## 3. Findings ordered by severity

No critical arithmetic corruption has been established. The following major validity defects must be addressed before confirmatory claims; reproducible scores alone do not resolve them.

### M1 — Endpoint filtering leaves paths through unresolved mixed owners

**Evidence.** `gold_evaluation.py:164–167` filters mapped/unmixed endpoints only, after `gold_standard.py` has taken closure through merged employee owners. Run `python S/gold/structural.py`. Independent closure of the archived adjacency equals current main pairs. Removing edges incident to the eight flagged mixed-position/unresolved owners **before** closure eliminates 3,103 currently included main pairs: 93 core, 979 inter, 2,031 non-core. The remainder has 8,269 pairs. Degree changes from 84.9982% to 90.168%; PageRank from 85.5874% to 92.079%. `gold/structural_accuracy.csv`, `gold/structural_private.json` and `gold/mixed_path_dependent.csv` retain the exact calculations privately. These eight flags are not eight independently proven multi-human records: some title combinations could represent career transitions.

Other multi-human release records, including short IDs 43716 and 71768, still combine distinct corpus sender components and multiple positions while passing the support-title heuristic. The absence of “assistant” in titles does not certify one person per UID.

**Impact.** “Unmixed” currently means only *unflagged endpoints*, not independently validated employees or uncontaminated reporting paths. The 3,103 are **not 3,103 proven wrong labels**: this is a conservative dependency sensitivity, not a repair. It demonstrates that known owner ambiguity propagates into a large part of the supposedly restricted benchmark.

**Fix.** Preserve position/person/path provenance; independently disambiguate merged owners where possible; flag path dependence on uncertain owners and report prespecified alternatives. Obtain author guidance on merged records and chronology. Do not choose the construction because its baseline accuracy is highest.

### M2 — Mailbox order decides gold identity, and overall matching precision remains unidentified

**Evidence.** `gold_standard.py:159–163` returns the first mailbox yielding one name. `principal_name(['Alice Smith','Bob Jones'], ['Smith-A','Jones-B'])` changes when the mailbox list is reversed. Current reversal changes IDs 6428, 11370 and 27104, affecting 1,047 full pairs. The changed main population is 10,413 pairs (959 fewer); degree is 83.8807% instead of 84.9982%. Treating all three records as uncertain leaves 10,395 pairs and 83.9202%. Commands: `python S/gold/attacks.py`; evidence `gold/attacks_private.json`, `gold/attacks_accuracy.csv`. Some conflicting spellings may represent aliases, so this is not a claim of three proved wrong humans.

Fresh sample: `.sample(n=60, random_state=20261004)` from 1,427 matched email employees. Review against corpus correspondence/signatures/directory and role evidence supports 32 selected identity components (not every alias, message or position merged into each record), identifies zero definite wrong matches, and leaves 28 unresolved. `gold/manual60.tsv` records every decision. Conditional precision among adjudicable cases is 32/32, Wilson 95% interval 89.3–100%, **not** a population precision estimate: evidence-rich cases are selectively adjudicable. Identification bounds for all 60 are 53.3–100%; the lower extreme's Wilson interval is 40.9–65.4%, the upper extreme's 94.0–100%. Those intervals do not include label uncertainty. Canonical first.last spelling and node existence alone were not counted as independent proof.

**Impact.** Input list order is not identity evidence. Name-only matches, canonical address nodes, and unresolved homonyms can change who receives hierarchy labels. Excluding ambiguous/absent records also changes the target population; 11,372 is not a random sample of the full 13,241 pairs.

**Fix.** Pool all mailbox-derived candidates; reconcile documented aliases; abstain on distinct unresolved candidates. Add permutation tests and a blinded match-validation sample with additional external/corpus evidence. Report adjudicability/coverage and sensitivity, not a certified 100% matching precision from the supported subset.

### M3 — Recipient union creates duplicate-recipient graph targets

**Evidence.** Run `python S/identity/attacks.py`. The new union restores 141 To/Cc address assignments in 82 groups, but `dedupe.py:128–138` unions address strings while `network.py:58–69` deduplicates only after imperfect address resolution (`identity.py:286–296`). In `campbell-l/inbox/1027.`, raw X-To evidence identifies one Michael Brown, but `.brown` and `michael brown` become separate targets among 27, each receiving 1/27. In `forney-j/sent_items/96.`, George Phillips appears as one resolved and one unresolved target, and Isaac Wong as two unresolved targets, among 11 targets. The FERC/Calger case now includes both resolved and ambiguous Palmer targets; the acknowledged Anderson case gains two distinct nodes for the same header recipient. All four cases qualify for the network. This verifies duplicate recipient representations within these messages, not global equivalence of every use of those address strings.

`identity/reread_union_headers.py` independently rereads all 11 original-tar messages for these four cases. All nine checked header fields match the archived evidence exactly (Campbell 5/5 copies; Forney, FERC and Anderson 2/2 each), and a full compressed-archive hash matches the initial SHA-256. `identity/raw_union_header_verification.json`, `identity/union_changes.json` and `identity/attacks.json` preserve the raw-header and current list/resolver/edge checks. Across changed groups there are 127 additional internal graph-target assignments after resolution (including unresolved-address and ambiguous nodes) and 63 network-eligible groups gaining a target; **not all 127 are claimed erroneous**. The 233 distinct-send candidates remain heuristic, not independently validated true sends.

**Impact.** Corroborated duplicate recipient representations receive multiple shares and other recipients receive reduced weights. This can inflate contacts and distort graph-derived comparisons. The per-message weight distortion is demonstrated; its isolated aggregate-degree or evaluation-score effect was not measured.

**Fix.** Retain X-To/CN provenance from copies, resolve recipient aliases conservatively before union, and represent unresolved ambiguity explicitly. Add the verified multi-spelling cases to an end-to-end graph regression. Report a no-union/validated-union sensitivity until coverage is adjudicated.

### M4 — Routine-message repair still admits the original bulletins and signature-only records

**Evidence.** `senders.py:106–146` switches to exact whole-text repetition and strips up to three final lines solely because each has at most three words. Current 6,745 routine/3,308 excluded counts reproduce. Archived probes rerun against current flags show all five old long-bulletin examples (`baughman-d/inbox/304.` and `356.`, `beck-s/inbox/390.`, `benson-r/inbox/116.`, `causholli-m/deleted_items/106.`) have `speech_act=False` but `routine=False` and `analysis=True`. The long legal analysis formerly excluded is correctly retained; one blanket prefix-based rule would not solve both cases.

There are also 195 signature-only messages, across five people, retained in person-text as short utterances (98/50/25/11/11). For example `dasovich-j/deleted_items/265.` contains a signature with “Administrative Coordinator” rather than a speech act. `text` archived routine replays and current attack outputs record flags/text. The corpus test (`tests/test_corpus_regressions.py`, long-message check) asserts only `not (routine and analysis)`, so it passes when all these bulletins remain in analysis.

A targeted current-data join (`text/bulletin_person_text.py`, `text/bulletin_person_text.json`) confirms **one of the five** is person-text: `causholli-m/deleted_items/106.`. The other four have null attributed senders and are excluded by the person-text gate despite remaining analysis rows. This materially limits their direct Phase 3 impact and must not be ignored when evaluating the fix.

**Impact.** The original word-count implementation defect is corrected, and the separate person-text gate does exclude four of the five examples. One long example still reaches person-text; all five remain in the upstream analysis population. The 195 signature-only messages were also explicitly verified as person-text and can masquerade as speech acts, topics or seniority signals. Exact whole-text repetition also lets near-identical notices vary out of the routine class.

**Fix.** Separate signature detection, speech-act classification and bulletin/template detection. Label whole-message and span-level examples, including genuine long human analysis and varying reports, before tuning rules. Assert intended inclusion/exclusion or explicitly relabel ambiguous cases; do not let a changed intermediate flag stand in for fixing the final analysis set.

### M5 — Department/support accounts still pass the new person-text gate

**Evidence.** `identity/inspect_targeted.py`/`identity/targeted.json` verify 57 person-text records under four non-person keys: Parking & Transportation 13; ISC Hotline 24; Security Console 14; SAP Security 6. Bodies identify departmental instructions, outage/support notices and distributed bulletins signed by other authors. Parking records with parsed MBX headers become roles (18 rows, eight in analysis, zero person-text), while other renderings of the same departmental account become people. `identity.py:136–144,178–185,280–282,310–317` detects the shared-mailbox header and projects types without propagating that evidence across renderings.

**Impact.** The 166,034/5,524 counts describe heuristic person-text records/keys, not established authored speech by that many distinct employees. Cohort counts are exact; exemplar bodies, not all 57 spans, were inspected. Whether the prose is handwritten or automated does not change the non-person sender-account finding. Departmental output can look functionally important precisely because it aggregates many people's work.

**Fix.** Propagate substantiated role/shared-mailbox evidence across aliases and header styles; review mixed-author accounts; validate person attribution separately from name normalization. Preserve the uncertainty instead of assigning all aggregate mail to a pseudo-person.

### M6 — Stricter reply links still select wrong immediate parents

**Evidence.** Fresh SRS sample of 60 current reply-kind links, seed 20261003: 50 supported direct replies, four wrong immediate parents, one same-author broadcast, one relay, four uncertain. Supported precision = 83.33%, Wilson 95% 71.97–90.69%; treating all four uncertain as correct gives 90%. The old 43/60 was a different sample; this is **not a controlled estimate of improvement**. Full individual decisions: `text/fresh_reply60_labels.json`; short public message paths/evidence in the accompanying sample files. Every old re-audit wrong-parent example and the same-author update identified in that targeted comparison still survives as reply-kind.

Compared with the original known-positive samples, 24/27 and 42/43 retain the same parent and reply kind. These are conditional retention figures, **not corpus recall**: replies missed by both versions were never sampled. Changed subjects, missing recipients and alias ambiguity remain unmeasured sources of missed links.

For example, `scott-s/all_documents/338.` selects Glen Sullivan's message `335.`, although the nearest quoted parent is Susan Scott's June 8 13:04 acceptance. `threads.py:87,95,99–110` combines To/Cc, permits same-sender candidates, and treats addressed-back membership as sufficient for reply classification before selecting a recognized prefix/latest candidate. The fixed copy gate is at line 168 and person mapping at 163–164. The Wilson interval describes sample-count uncertainty, not uncertainty in AI labels or a validated conversational reconstruction.

**Impact.** A message addressing the previous sender can still be an independent update, reply to another message, or relay. Incorrect parentage can manufacture response-time, conversational-authority and speech-act relationships.

**Fix.** Store competing parent candidates/confidence; validate immediate-parent evidence independently rather than using addressed-back status as truth. For Phase 3, compare high-evidence links only against broader heuristic links, and build a separate positive-reply sample for recall. The fixed probable-copy exclusion itself reproduces.

### M7 — Cleaner/structured rules retain format-dependent leakage and introduce false exclusions

**Evidence.** The four old wrapped To/Sent-by cases and original negative controls pass. Fresh inspection of 60 current **analysis** messages (seed 20261004) finds one definite residual quote case at inspected boundaries and no definite false cut. This frame excludes empty authored outputs by definition; it is not a sample capable of measuring whole-message deletion error or exhaustive span recall. `jones-t/notes_inbox/467.` retains a dated European-style quoted exchange; `allen-p/sent/300.` exposes a header beyond the 30-line allowance. `clean.py:35–36,57` limits date/header formats and permits arbitrary continuation lines. Synthetic controls demonstrate both a 31-wrap valid header missed and genuine agenda prose with a later Subject field cut. These are distinguished from observed corpus false cuts.

The 5,000-message cross-check independently reproduces **byte-for-byte** (JSON SHA-256 `3a16cccb24d9db49c53408a6271334dfec00c0cf81a2b9266869191845249009`; CSV `cfca71c3c8a46409411188750314edc2971ba1d6369c10df8b673f48c1973ae4`). Normalized agreement is 77.22%; ours empty 367/5,000 (7.34%), email_reply_parser empty 177/5,000 (3.54%), both empty 155, ours-only 212, comparator-only 22. Ours-only first markers are 189 Lotus-forward banners, 12 Outlook separators, six Lotus headers, four transport headers and one On-wrote. All 211 prior ours-only cases remain; the one newly empty case is a wrapped quoted-header message. A separate fresh 20 of the 212 (seed 20261006) show no new top-posted contribution in the boundary screen. Therefore **7.34% is not a false-deletion rate**.

Real deletion counterexamples do remain: `beck-s/sent_items/87.` loses filled-in inline migration-questionnaire answers; `richey-c/deleted_items/23.` loses a bottom-posted technical answer (the latter is external and not part of internal person-text). Conversely, some comparator-only empties are advertising/header residue retained by this cleaner. Run `python S/text/rerun_archived.py clean_repro_light.py`, `python S/text/empty_delta.py` and `python S/text/label_empty.py`; see `text/fresh_empty20_labels.json`, `text/empty_delta.json`, `text/demonstrated_retest.json` and `text/archive_rerun/crosscheck/checksums.json`.

`senders.py:59` matches any `PEP ACCESS` opening: `salisbury-h/read/144.` and `williams-w3/hr/80.` contain substantive, human-style training/RSVP prose signed “Grace,” yet are classified as structured. Their production provenance was not independently authenticated; the demonstrated problem is treating that entire prose format as a machine record solely from its opening. All seven newly excluded daemon-name examples inspected are actual leave-system messages; no human false positive was demonstrated for that change.

**Impact.** Quote contamination can assign another person's knowledge to a sender; signature retention can expose title labels; broad administrative opening rules can remove genuine operational coordination. A lower residue-regex rate or higher empty-output rate alone is not a cleaner-accuracy score.

**Fix.** Validate authored/quoted/signature spans on held-out, stratified labels. Test new format rules against natural negative examples and long recipient lists, and classify notices using more than a generic opening. Require leakage-masked model variants.

### M8 — Stale artifacts can bypass corpus validation

**Evidence.** In the actual main checkout, `python -m pytest tests/test_corpus_regressions.py -q -p no:cacheprovider` returns success with **13 skipped** because `links.parquet` is absent, despite populated older processed data. `tests/test_corpus_regressions.py:19–26` skips the module before freshness checking. `python S/provenance/gate.py` shows the freshness function accepts a deliberately wrong config fingerprint and all wrong output checksums when `code_sha256` matches; changing the code fingerprint does fail. This is a scratch fixture, not tampering with real artifacts. The original poisoned parsed-cache counterexample is genuinely fixed and should not be conflated with this downstream gap.

**Impact.** A green corpus-test exit can mean “nothing checked,” and downstream data built with different parameters or altered artifacts can carry a source-consistent stamp. Main's committed results and local inputs were inconsistent at audit entry.

There is a second, independently reproduced stale-input path. With tiny scratch parquet fixtures and no private source, `gold_standard.main` skips at `gold_standard.py:224–226` and leaves old employee/pair/coverage hashes unchanged. `gold_evaluation.main` checks only for the pair file (`gold_evaluation.py:155–168`), reads these preexisting artifacts, computes scores/filters and reaches evaluation with one eligible pair. `gold/skip_source_probe.py` intercepts `gold_table` at that point with a sentinel; it proves attempted stale-input reuse, **not** a completed stale CSV run. A skipped source stage should not silently license downstream use of arbitrary leftover outputs.

**Fix.** In a dedicated post-build verification command, fail on missing required artifacts; check normalized configuration, input/output hashes and every stage's provenance. Reserve skips for an explicitly data-free unit-test mode. Rebuild main before using its local outputs; do not copy selected files from different runs.

### Minor findings and test coverage

1. **Empty paired bootstrap draws still crash.** `gold/attacks.py` gives one core pair, opposite measure scores, `reps=1, seed=0`: `paired_gold` calls percentile on an empty list (`gold_evaluation.py:114–129`) and raises IndexError; zero replicates also fail. Guard empty retained draws, report their count and test sparse cases. No effect on the reported full-data 1,000-draw point estimates has been demonstrated.
2. **Mutation coverage remains uneven.** Full unit suite: 136 pass, 13 corpus tests deselected. Root's 16 focused tests kill poisoned-cache acceptance, constant intervals, and fake perfect-or-wide bootstrap, but survive replacing the Python or lock stamp with constants. Text tests (56) survive reverting the wrapped allowance 30→2, restoring 80-character routine-prefix matching, and omitting probable-copy exclusion; six other text mutants are killed. The wrapped-header fixtures have only two continuation lines; the whole-text fixture varies before character 80 and therefore does not distinguish the old routine rule. Exact commands: `python S/provenance/mutations.py`, `python S/text/finalize_mutations.py`; per-mutant logs and result tables stay in those directories. A surviving mutant proves a test gap, not that current source contains that mutation. Early harness setup errors were corrected and rerun, not counted as kills.
3. **Latent Message-ID dedupe invariant.** Synthetic content-duplicate A/B plus a different-content C sharing B's Message-ID can leave C's copy mapping pointing at removed B; the secondary Message-ID removal also does not union its recipients. Current corpus has zero secondary-ID removals, so no present-data effect is claimed. Add mixed-key dedupe fixtures and enforce surviving canonical targets. `identity/attacks.py`/`identity/attacks.json`.

Additional identity/dedupe test coverage: **four of eleven functional mutants survive all 47 checks**—digit role detection, TITLE_WORDS recognition, whole-key go-by alias generation and Cc union removal; seven are killed (`identity/mutations.json`). Both old inference-threshold faults are now caught. Two corpus-only exception probes still pass artifact checks because those checks read data, not invoke the patched functions; the source file hash is unchanged by an in-memory patch. That diagnostic does not show the new generated-pipeline test is inert.

Gold tests: **six of 17 mutants survive the 17-test focused suite**, with 11 killed (`gold/mutations.json`). Survivors restrict principal-name lookup to the first mailbox, replace position-first pairs with main pairs, hard-code every nonempty interval to [0,1], replace copy-multiplicity products with binary endpoint presence, weight paired intervals by only the dominant's multiplicity, or resample shared graph keys instead of distinct gold IDs. The brute-force toy at `tests/test_gold_evaluation.py:23–40` has extreme [0,1] limits and cannot detect two wrong interval calculations; the paired test at lines 67–69 checks only the point difference; the collision fixture at lines 57–60 omits graph-key columns. `tests/test_gold_standard.py:51–57` names differing alternatives but asserts identical sets on its fixture. Add nondegenerate interior-quantile, paired-interval, colliding-key and genuinely differing-construction cases. The independent full-data oracle does reproduce current source correctly: these survivors show missing regression protection, not demonstrated current arithmetic corruption.

### Additional attacks with limited or negative results

- Go-by whole-key aliasing can synthetically rewrite another address's unmarked name at 90% full-middle support; **no current false go-by merge was established**. Two new go-by aliases have supporting correspondence/signature evidence, not exhaustive adjudication of every linked row. `identity/attacks.json`; `identity.py:219–235`.
- Unrecognized short title suffixes and compound-surname/full-given-name forms can synthetically misparse. The audit enumerated 160 multiword-comma forms and digit-bearing headers but did not establish a current internal-human digit false positive. External name/location-code cases were not mislabeled as demonstrated internal-network errors. `identity/candidates.json`, `identity/digit_names.csv`; `identity.py:95–144`.
- In a CN-free, address-fallback fixture, the **uninitialled row** abstains with 19 initialled messages, infers with 20 and 70% dominance, and abstains with 20 and 65%. Explicit initialled rows remain split. Exact two-thirds is slightly below configured 0.6667. The minimum applies to address inference, not the separate CN rule at line 243. `identity/threshold_probe.py`, `identity/threshold.json`; `identity.py:237–245`.
- A current-data scan of all 2,571 rows in the three split bases finds 32 uninitialled CN-based assignments. One uses a CN group with only nine initialled records, but its address has 59; the row is not analysis/person-text. **Zero current CN-assigned rows violate the 20-record minimum at the address level.** The stronger-CN override is a real policy distinction, not an established present-data identity error. `identity/cn_threshold_check.py`, `cn_threshold_check.json`.
- The synthetic recipient bridge `{B}`, `{B,C}`, `{C}` changes grouping with copy order because the representative set is not updated (`dedupe.py:88–105`). This is an ambiguity/invariance counterexample, not proof of real resends. All 298 pairs among current separate-send candidates have zero raw and resolved-recipient overlap; disjoint-send controls survive. The older external alias-rendering candidates remain unadjudicated.
- No current aliases form chains. A recipient fallback inconsistency concerns four per-message person keys absent from the modal-address person set; one literal candidate address appears five times, but the underlying human join was not independently corroborated. It remains a candidate, not a confirmed wrong assignment.
- Alias provenance labeling is inaccurate: `formal_rank.py:68–69` calls every name alias “directory-ID alias,” including the new middle-name/address-based go-by merge. Store the real evidence class; this finding does not dispute the supported example's resulting join.

### Documentation corrections

- README's “Every number and figure ... public corpus ... make all” is not true for the privately supplied gold labels. The later access warning is useful but does not make that opening statement accurate.
- README's raw-address sensitivity is not the paper's person-node construction. The primary paper (§3–4) co-references aliases and reports 279,844 messages, 93,421 persons and 407,095 links. Maximum degree over an employee's raw addresses is a different baseline. Source: [Agarwal et al. (2012)](https://aclanthology.org/P12-2032/), independently read from the archived primary paper.
- The paper's own displayed category counts sum to 13,723 (440 + 6,436 + 6,847), versus its stated total of 13,724. That one-pair internal discrepancy does not explain the much larger difference from 13,241 reconstructed pairs; neither historical number determines a unique construction from the supplied release.
- `gold_evaluation.py:185–188` reads `processed/messages.parquet` for a run labeled “all mail”; those messages are windowed and deduplicated. State the exact population rather than implying the entire raw archive.
- The 72.7% thread figure means 24 supported original links among 33 **same-parent** current reply links. There are 36 old sampled children currently labeled reply, including three changed parents not adjudicated by the old labels (`validate_threads.py:39–58`).
- `config.yaml` still describes routine exclusion in terms of a template/word threshold, while code now uses whole-text repetition and sign-off-stripped whole-message word count. Its opening “Every parameter” claim is also too broad: name/title/structured regex vocabularies and the 30-line allowance live in source.
- “Unmixed” and “person-text” must be explicitly operational labels, not independently established human identity/authorship. “Indistinguishable” from a non-significant paired interval is not an equivalence result.
- README line 111 reports the title in-strength interval lower bound as 55.5%; the independently reproduced CSV value is 55.44837126%, or 55.4% to one decimal place. This is a minor reporting error, not a changed inference.

## 4. Phase 3 leakage risks and required tests

1. **Title/signature shortcuts.** Targeted current authored/analysis checks retain 41 title-bearing examples: 19 Kaminski Managing Director, one Beck Vice President, two Beck COO, 19 Sue Nord senior-director examples. These are inspected cohorts, not an estimate of all title leakage. Example signature: `kaminski-v/all_documents/11199.` contains “Vincent Kaminski / Managing Director”; `beck-s/sent_items/314.` contains “Chief Operating Officer.” Strip or separately model signatures, names, addresses, directory IDs and job titles; report performance with/without them. Train a title/name-only negative-control model.
2. **Quoted authorship and forwarded knowledge.** Use held-out authored/quoted/signature span labels; evaluate topics and speech acts with conservative quote removal and with contaminated messages excluded. Do not credit quoted specialists' prose to the forwarding employee.
3. **Shared accounts and aliases.** Validate the unit of analysis independently of the NLP target. Exclude/quarantine supported role accounts and uncertain persons; prevent the same human's aliases from crossing train/test splits.
4. **Mailbox/custodian observation bias.** Custodian status alone yields a strong inter-pair baseline. Include mailbox availability, sent/received coverage, counts, tenure/window coverage and missingness baselines; stratify core/inter/non-core and test robustness within coverage bands. Availability is not importance.
5. **Pair and hierarchy dependence.** Split at person/entity/connected-identity level, not random pairs or messages. Prespecify executive deletion, macro weighting and matched-population rules. Bootstrap intervals conditional on one noisy hierarchy do not cover uncertain owners, cycles, ambiguous matches or alternative release constructions.
6. **Evaluation-target circularity.** Keep gold names/mailboxes confined to benchmark matching, not feature engineering or graph construction. Freeze matching rules before comparing models. Title agreement tests formal-rank association; add separately justified outcomes before claiming functional importance or replacement risk.
7. **Rule tuning on audited examples.** Keep the old audit cases as regressions. Collect independent held-out labels with at least a second adjudicator and record disagreements. The fresh labels in this audit were made by an AI auditor, not an independent human panel; they are evidence with stated uncertainty, not definitive ground truth.

## 5. What could not be verified

- The historical 2012 release identity, chart chronology, exact original pair-generation decisions, and private-delivery provenance cannot be authenticated from a local checksum. Author clarification remains necessary.
- Twenty-eight of the 60 sampled gold matches lack sufficient independent corpus evidence for a human-identity judgment. Normalized spellings do not fill that gap. All 129 title joins have not been independently re-adjudicated.
- Fresh reply precision does not estimate recall against all true replies. Fresh cleaning boundary inspection is not a fully labeled span benchmark, and residue regexes do not establish cleaning accuracy.
- I did not establish every alias/homonym/role account, every false or missed duplicate, or a corpus-wide error rate for the synthetic edge cases. Specific confirmed examples are separated from unresolved candidates.
- No Phase 3 NLP model or functional-importance outcome exists in the audited scope. Its future scientific validity cannot be certified by these baseline scores.
- A completed raw-archive reparse, full execution in the newly synced environment and cross-platform byte determinism were not verified; the specific cache/environment limitations are stated above. The downstream rebuild completed; later changes to three fixes-worktree result CSVs are explicitly excluded from the pinned comparison. Their subsequent revisions are outside this audit.

### Exact command index

These commands resolve the abbreviated evidence references above. Scripts contain exact fixtures, seeds, adaptations and output paths; original logs are retained. Do not run old archived scripts directly without their adapters: some originally contain obsolete absolute scratch paths and incompatible data schemas.

```sh
R=/Users/jebfarneth/projects/enron-knowledge-decay
S=/tmp/enron-audit3-20260925.dnpSbE
cd "$R"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
"$R/.venv/bin/python" "$S/identity/verify.py"
"$R/.venv/bin/python" "$S/identity/attacks.py"
"$R/.venv/bin/python" "$S/identity/inspect_targeted.py"
"$R/.venv/bin/python" "$S/identity/candidates.py"
"$R/.venv/bin/python" "$S/identity/threshold_probe.py"
"$R/.venv/bin/python" "$S/identity/cn_threshold_check.py"
"$R/.venv/bin/python" "$S/identity/replay.py"
"$R/.venv/bin/python" "$S/identity/reread_union_headers.py"
"$R/.venv/bin/python" "$S/identity/mutations.py"
"$R/.venv/bin/python" "$S/text/extract.py"
"$R/.venv/bin/python" "$S/text/label_fresh.py"
"$R/.venv/bin/python" "$S/text/label_cleaning.py"
"$R/.venv/bin/python" "$S/text/rerun_archived.py" targeted.py
"$R/.venv/bin/python" "$S/text/rerun_archived.py" routine_probe.py
"$R/.venv/bin/python" "$S/text/rerun_archived.py" clean_regressions.py
"$R/.venv/bin/python" "$S/text/rerun_archived.py" clean_repro_light.py
"$R/.venv/bin/python" "$S/text/attacks.py"
"$R/.venv/bin/python" "$S/text/extra_checks.py"
"$R/.venv/bin/python" "$S/text/bulletin_person_text.py"
"$R/.venv/bin/python" "$S/text/empty_delta.py"
"$R/.venv/bin/python" "$S/text/label_empty.py"
"$R/.venv/bin/python" "$S/text/finalize_mutations.py"
"$R/.venv/bin/python" "$S/gold/current.py"
"$R/.venv/bin/python" "$S/gold/attacks.py"
"$R/.venv/bin/python" "$S/gold/structural.py"
"$R/.venv/bin/python" "$S/gold/replay.py"
"$R/.venv/bin/python" "$S/gold/replay_matching.py"
"$R/.venv/bin/python" "$S/gold/replay_raw.py"
"$R/.venv/bin/python" "$S/gold/replay_extra.py"
"$R/.venv/bin/python" "$S/gold/numerical.py"
"$R/.venv/bin/python" "$S/gold/mutations.py"
"$R/.venv/bin/python" "$S/gold/final_checks.py"
"$R/.venv/bin/python" "$S/gold/skip_source_probe.py"
"$R/.venv/bin/python" "$S/provenance/check.py"
"$R/.venv/bin/python" "$S/provenance/gate.py"
"$R/.venv/bin/python" "$S/provenance/title_oracle.py"
"$R/.venv/bin/python" "$S/provenance/mutations.py"
uv sync --locked --group dev --project "$S/pinned_project"
PYTHONPATH="$S/pinned_project/src" MPLCONFIGDIR="$S/mpl" "$R/.venv/bin/python" "$S/reproduction/run.py"
PYTHONPATH="$S/pinned_project/src" "$R/.venv/bin/python" "$S/reproduction/run.py" corpus_regress
"$R/.venv/bin/python" "$S/reproduction/compare.py"
"$R/.venv/bin/python" "$S/provenance/final_hashes.py"
```

Source-executing probes and numeric oracles are independent of the annotation-writing scripts: the latter preserve the auditor's recorded decisions/rationales and do not generate independent gold labels merely by being rerun.
