# Independent re-audit: Enron data layer and network baselines

Audit date: 2026-09-25. Repository: `/Users/jebfarneth/projects/enron-knowledge-decay`. Requested and inspected revision: `main`, `1ab1b2bd714ee11dd4959132e97f0b9c95664cdb`. Comparison revision: `8c595e7`. Evidence directory: **`/tmp/enron-reaudit-20260925.WVW9gE`**.

**Revision boundary:** The worktree was clean at the start. During the final long-running checks, another process began adding an Agarwal gold-standard module and modifying configuration, evaluation code, tests and dependencies. Those changes are outside this audit and were neither altered nor reverted. Findings and source line references describe the pinned revision and its captured inputs, not that concurrent next version. The scratch source/environment snapshot and original SHA-256 inventory preserve this boundary.

## 1. Executive verdict

**No—not yet as a frozen data layer for person-level Phase 3 inference.** The principal counts and numerical graph/evaluation calculations reproduce, and several original counterexamples are corrected. However, independently checked corpus examples still split one labelled employee across identities, assign another employee's PR work to the wrong person, classify shared accounts as people, admit long routine bulletins through a purported four-word exemption, and newly retain quoted colleagues' text after a cleaning change. A fresh sample supports only 43 of 60 reply-kind links as direct replies. Correcting one corroborated identity split alone changes degree accuracy from 65.493% to 66.560%, illustrating sensitivity that the existing bootstrap does not represent. Exploratory model scaffolding can proceed, but do not treat the present person labels, authored text, routine filter or inferred responses as validated training/evaluation data. Before substantive Phase 3 results: correct the demonstrated defects, audit the 129 title-to-person joins, define person-text eligibility, freeze independently annotated extraction/linkage validation samples, and implement the leakage and split checks in section 4. This verdict does not mean every record or every network statistic is wrong.

## 2. Fix verification and reproduction

### Scope and execution record

All audit-generated scripts and execution outputs were written outside the repository. The only intended repository addition is this report. The original evidence archive was extracted to `original_evidence/` beneath the new evidence directory after checking its member paths and types. The original report, response and tests were treated as claims and leads, not evidence of correctness.

The shorthand **S** below means `/tmp/enron-reaudit-20260925.WVW9gE`; **R** means `/Users/jebfarneth/projects/enron-knowledge-decay`. Commands were run from R unless noted. These variables are notation for readability, not changes to system environment variables.

Displayed email paths omit the leading `maildir/`; they identify archive members and Parquet `path` values, not files relative to R. Source-file references without a directory refer to `src/enron_importance/` unless explicitly under `tests/`.

```sh
git rev-parse HEAD
git status --porcelain=v1 --untracked-files=all
git diff 8c595e7..HEAD --stat
git log --format='%h %s' 8c595e7..HEAD
uv sync --locked --group dev --project /tmp/enron-reaudit-20260925.WVW9gE/environment_project
MPLCONFIGDIR=/tmp/enron-reaudit-20260925.WVW9gE/mplconfig PYTHONPYCACHEPREFIX=/tmp/enron-reaudit-20260925.WVW9gE/pycache .venv/bin/python -m pytest -q -p no:cacheprovider
```

`environment_project/` contains copies of the unmodified source, tests, manifests and configuration, with a separate virtual environment. Its corpus-test data link is read-only in the tests. Fresh installation succeeded with CPython 3.12.13 and the pinned dependencies. **113/113 tests passed** in that environment and in the original environment (`pytest_fresh.log`, `pytest_originalenv.log`, `uv_sync.log`). Test success is distinguished from validity below.

Reproduction scripts call the requested-revision implementation, redirecting write destinations into scratch. Independent probes separately reconstruct edges, scores, sample labels or counterfactuals. No pipeline stage was allowed to overwrite the repository's generated data. Relevant exact commands:

```sh
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/reproduce_prepare.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/identity/probe.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/identity/quantify.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/identity/counterfactual.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/dedupe_probe.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/dedupe_followup.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/text/probe.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/text/label_threads.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/text/clean_regressions.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/text/targeted.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/text/routine_probe.py
PYTHONHASHSEED=101 .venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/reproduce.py run1
PYTHONHASHSEED=202 .venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/reproduce.py run2
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/probes.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/all_metric_oracle.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/tolerance_checks.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/original_mutants.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/test_safety_mutations.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/identity/mutations.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/network/mutate_bootstrap.py
.venv/bin/python /tmp/enron-reaudit-20260925.WVW9gE/provenance_probe.py
```

These scripts are the executable specification of the probes; the associated JSON/CSV/log files preserve inputs selected for inspection, labels, denominators and results. Sub-audit narratives in `identity/findings.md`, `text/findings.md` and `network/findings.md` provide additional commands and checked negative results. Some lengthy processes were paused or restarted to manage memory pressure; only completed outputs are counted as reproductions.

The commands above record the actual executions at the audited revision. A later rerun must use that revision or the captured `environment_project/src`, configuration and lockfile—not the concurrently edited live package. Before the long graph runs reached evaluation, their relevant inputs were copied to `network/frozen_inputs/`, checked against the audit-start hashes, and their scratch links retargeted. Both processes had already imported the original code and loaded the original configuration before external edits began. `network/frozen_inputs/verification.json` records the five input hashes.

### A. Every row of the response document

“Fixed narrowly” means the demonstrated original defect is corrected, not that the surrounding heuristic is validated. “Partly fixed” is not a synonym for “all results invalid.” References M1–M7 and m1–m5 point to findings below.

| Response finding | Claimed status | Verified status | Reproduced effect and counterexample check |
|---|---|---|---|
| M-ID1: `no.address` assigned to Don Miller | Fixed | **Fixed narrowly** | All 778 messages re-attributed: 98 Don Miller, 639 null, 41 other keys. Original `arnold-j/inbox/31.`, `41.`, `arora-h/inbox/67.` are no longer Don. Degree 491 in original evidence → 346 now. New per-message errors are separate problems, M1–M2. `identity/probe.txt`, `quantify.txt`; `identity.py:150–223`. |
| M-ID2: numbered temp/role mailboxes merged | Fixed | **Numbered-temp case fixed; general typing partial** | 96 role keys; legal.1/.2/.3/.4/.5/.7 remain distinct, with 22/16/4/5/1/30 messages. Shared conference rooms and service accounts still become people (M2). `identity/probe.txt`, `more_probes.txt`; `identity.py:93–111,139–146`. |
| M-ID3: aliases split despite common directory ID | Fixed | **Specified merges verified** | All 12 alias rules recomputed; Albert/Bert unified and title join follows alias. Inspected suspicious Brian/Binkley Oxley, Katherine/Renee Perry and Abenaa/Monica Clay signatures support the merges. No actual false merge among the 12 was proved. A separate corroborated Dana/Mark Dana split remains (M1). `identity/probe.txt`, `inspect_targets.txt`; `identity.py:166–178`. |
| M-ID4: Mark A/E Taylor merged | Fixed | **Taylor case fixed; initial-imputation rule partial** | `.taylor` → Mark E; `a.taylor` → Mark A. The explicit Charles A message is no longer Mark. Three initial-split bases reproduce: Taylor, Palmer, Miller. Mark Palmer's inferred initial is wrong in at least two corroborated messages (M1). `identity/initial_probe.txt`, `palmer_review.txt`; `identity.py:180–197`. |
| Graph represented as 21,047 validated people | Partly fixed | **Partly fixed** | New graph has 20,757 nodes: 5,606 person-typed, 91 roles, 305 lists, 14,755 unresolved addresses. People-only degree 67.1612% verified. Types remain heuristic; two ambiguous base names and shared rooms are still person-typed. `network/probes.log`, `identity/more_probes.txt`. |
| Placeholder aliases corrupt named scores | Fixed | **Original error fixed; wording needs precision** | Placeholder address nodes/recipients are dropped; no placeholder address occurs as a graph node. Named messages originating from such addresses can intentionally remain: 98 Don Miller messages do. “All placeholder-origin messages are dropped” would be false. `network/probes.log`, `identity/quantify.txt`; `network.py:45–73,95–101`. |
| M-RANK1: contradictory titles resolved by maximum; notes ignored | Fixed | **Policy fixed; title truth remains open** | Both disputed VP duplicate rows are dropped, Trader rows retained, notes preserved, four disputed keys flagged. 161 source rows, 160 matched names, 129 distinct titled keys. Old higher-title policy gives degree 65.07%; removing disputed labels gives 66.53%. All 11 original correction targets plus Mark E have corpus evidence. M1 still changes one title-to-person alignment. `identity/probe.txt`, `quantify.txt`; `formal_rank.py:61–76`. |
| Label population / mailbox availability | Open | **Open; original concern not disproved** | Recomputed same access proxy: 104/129 labelled people overlap; custodian indicator 43.31%, mailbox-file count 49.05%, degree 65.49%. The response's 43.9%/48.2% are correctly described as old-audit values, not new outputs. Simple controls do not reproduce degree, but selection/visibility bias remains. `network/custodian_baselines_dominant_plus_named_executives.csv`. |
| Fractional weights do not neutralize broadcast degree | Documentation fixed; definition open | **As claimed** | At most 10 recipients: 62.8869%; at most 50: 65.4691%. Independent adjacency reconstruction matches both. Degree still counts every distinct contact; 1/n changes weighted measures only. `network/probes.log`; `network.py:11–13,45–73`. |
| Floating summation changes ties/results across processes | Fixed | **Main defect corrected; boundary comparator defect remains** | Main outgoing count is exact integer; independently reconstructed edge weights/counts match. Separate-process outcome is reported below. A synthetic near-tie still depends on row order because `np.isclose` is asymmetric; no effect found in current ranked scores (m2). `network/tolerance_checks.log`; `evaluate.py:34–37`. |
| Highest point estimate treated as superiority | Fixed | **Verified** | Degree−PageRank 0.0374499, paired CI [−0.0055911, 0.0781966]. README limits its claim accordingly. Independent multiplicity bootstrap matches all 1,000 draws. `network/probes.log`; `evaluate.py:65–98`. |
| Tests accepted incorrect bootstrap/modal name | Fixed | **Original mutants caught; broader coverage partial** | Unconditional (0,1) CI and first-name-instead-of-mode mutants now fail their new checks (`original_mutants.json`). A non-bootstrap implementation special-casing perfect/reversed data still passes 9 evaluation tests; removing the initial-share threshold passes 28 relevant tests (M7). |
| Deduplication loses recipient evidence | Fixed | **Partial, not general resolution** | 233 extra kept records across 194 groups and 262,249 copy→keeper mappings reproduce; every mapping points to a survivor. Bass 69/70 both survive. Overlapping lists still leave 141 raw recipient assignments outside the selected keeper in 82 groups; many are aliases/self, not 141 proven lost contacts. Confirmed attribution loss and alias-rendering ambiguity are examined below (M6). `dedupe_summary.json`, `dedupe_headers.json`; `dedupe.py:84–126`. |
| Timestamp-shifted copies missed | Partly fixed | **Partly fixed, as labelled** | All seven original raw-header examples now point to their earlier copy; 1,531 flagged, none in analysis, 895 already automated. Fresh 60 sampled pairs are consistent with export copies; zero confirmed genuine resends, but transport evidence cannot rule resends out. No referenced gap exceeds 8 hours. Threading still uses some flagged copies (m3). `dedupe_followup_summary.json`, `shifted_sample60_labels.json`. |
| S1: account-level feed exclusion deletes human work | Partly fixed | **Partial; response explanation inaccurate** | Six human Pete Davis messages and two human ipayit replies remain in analysis. Of all 11 retained feed-account analysis records, three are machine alerts. ipayit is **not** excluded whole, contrary to the response. `text/feed_kept.json`; `senders.py:105–110`. |
| S2: calendar records/personalized notices survive | Fixed | **Only partly fixed** | 3,113 structured records reproduce; all 60 randomly inspected flagged records match intended machine formats. At least 16 targeted machine records still survive, plus one explicit automated message in fresh random 100-message analysis sample (M4). `text/machine_candidates.json`, sample labels; `senders.py:49–54`. |
| S3: routine filter removes speech acts | Fixed | **Partly fixed; new implementation defect** | Boolean exemption count 3,296 reproduces, but 503 have >4 actual words and 139 enter analysis. Word count uses an 80-character prefix. Short signed requests and substantive legal prose remain excluded (M3). `text/speechact_truncation.json`, `routine_5to8words.json`; `senders.py:57–61,119–121`. |
| Inferred links not validated responses | Partly fixed | **Partly fixed** | Old sample: 25/27 direct replies remain same-parent reply-kind; 25/35 surviving same-parent reply links are direct (71.43%). Fresh current sample: 43/60 direct, Wilson 95% 59.23–81.49%; two old correct parent/reply decisions are lost (M5). `text/old_outcomes.json`, `fresh_reply60_labels.json`. |
| Quote truncation loses inline answers / misses flat headers | Partly fixed | **Partial, with new regressions** | Old prose-negative controls now survive; three original-sample outputs improve. Two original 200-message outputs and two fresh-pair messages now retain large quote blocks because To lists wrap. Inline and bottom-posted answers still disappear (M4). `text/old 200-message sample_clean_changes.json`, `fresh_thread_clean_changes.json`; `clean.py:33–36`. |
| Signature and copied-source leakage | Open | **Open, reproduced** | All 41 prior sender-title signature examples remain in analysis. New quote failures add other people's names/titles. `text/signature_retest.json`; section 4. |
| Cleaner agreement not gold | Reporting fixed; gold open | **Reporting correction verified** | Exact configured-sample fields reproduce: 77.48% whitespace agreement; empty 366/5,000 vs 177/5,000. Empty control is present. Real authored losses remain; no human span accuracy was established. `text/cleaning_reproduced.json`; `validate_cleaning.py:39–93`. |
| Cache bypass / make only first stage | Fixed | **Archive check fixed; provenance/orchestration partial** | Corrupted archive now rejected on cached parse. Matching stamp still accepts altered parsed data and changed parser dependencies; parallel make has no stage dependencies; corpus tests run before regeneration; validate_threads omitted (M7,m4). `provenance_probe.json`, `make_trace.jsonl`; `prepare.py:41–55`, `Makefile:9–43`. |
| README / commit claims overstated | Fixed | **Partly fixed** | Functional importance remains explicitly an objective, title proxy and fixed source rules disclosed. Remaining factual/definition mismatches are itemized below, notably short-message length, ipayit, unresolved senders, reply counters and complete make coverage. |
| Passing tests are not corpus validity | Partly fixed | **Partial, accurately acknowledged but integration gap remains** | All 113 pass; all 9 corpus regressions also pass with seven key functions replaced by exceptions, because tests read old Parquet outputs. No blinded human validation set exists. `corpus_mutation.json`, `corpus_mutation.log`; `tests/test_corpus_regressions.py:12–25`, M7. |

### B. Numerical and byte reproduction

The full `prepare` stage completed in scratch from the verified raw parsed cache: **every funnel count matches**, and **all three output Parquets are byte-identical** to the audit-start files. `prepare_reproduction.json` records `funnel_equal: true` and `output_hashes_equal: true`; the command and complete log are `reproduce_prepare.py` and `prepare_reproduction.log`. The raw archive was checked again at **443,254,787 bytes**, SHA-256 **`b3da1b3fe0369ec3140bb4fbce94702c33b7da810ec15d718b3fadf5cd748ca7`**.

```text
messages.parquet  672193af5ba219d8cadc9da9f2e94e48be5f70dadd21a732c8d9b0b9233353e8
senders.parquet   9525441615ea0442a9d3f08166e57fd5512ee77cb9104d0522a189c997454bcc
copies.parquet    f127ad8577680aea51c6adc8f01a7bd52bcda318205017ef5f2eb259274802d8
```

This is a fresh downstream preparation run, not a fresh archive parse: the raw-cache hash exactly matches the preceding audit's independently regenerated table, and the parser was unchanged. The full `funnel.json` is **not** claimed byte-identical: scratch output paths deliberately change the configuration fingerprint, and its completion-time whole-package source hash sees the concurrent gold-standard additions. The running preparation functions and loaded configuration predate those edits; all Phase 1 source files remain unchanged, and the regenerated data bytes match the pinned inventory exactly. Metadata fingerprint differences are disclosed rather than counted as data differences.

| Funnel or current-output claim | Re-audit value | Comparison |
|---|---:|---|
| Parsed files / in-window / outside / undated | 517,401 / 516,359 / 1,042 / 0 | Matches |
| Content duplicates / extra Message-ID duplicates | 262,249 / 0 | Matches |
| Heuristic additional separate sends / unique survivors | 233 / 254,110 | Counts match; distinct-send semantics not established |
| Probable shifted copies | 1,531 | Matches |
| With quote markers / with estimated authored text | 111,295 / 234,341 | Matches |
| Sender addresses / flagged accounts / messages from flagged accounts | 20,293 / 311 / 9,457 | Matches |
| Automated messages / structured records | 9,422 / 3,113 | Matches |
| Routine records / excluded / exempted | 12,230 / 8,934 / 3,296 | Matches flags; length interpretation is wrong (M3) |
| All parent links / reply-kind / forward-kind | 39,032 / 32,326 / 6,706 | Matches; all-links counter is misnamed |
| Threads | 215,078 | Matches |
| Analysis messages / sender addresses | 167,970 / 6,343 | Matches |
| Internal addresses / non-null address-map keys | 6,455 / 5,869 | Matches |
| Source title rows / matched names / titled keys | 161 / 160 / 129 | Matches |

**Separate-process determinism is verified for the graph, evaluation tables and figures.** Runs with `PYTHONHASHSEED=101` and `202` independently rebuilt the graph, including exact betweenness, then evaluation and both figures. Every one of the nine files is byte-identical between runs and to the initial committed artifact inventory. Full SHA-256 values are in `network/run1/hashes.json`, `network/run2/hashes.json` and the comparison evidence; abbreviated hashes below are only for readability.

| Artifact | SHA-256 prefix | Run 1 = Run 2 = audit-start artifact |
|---|---|---|
| `edges.parquet` | `5e9a22916fa94893` | Yes |
| `centrality.parquet` | `d62ed9019c609788` | Yes |
| `baselines_formal_rank.csv` | `1059ca98b8706bff` | Yes |
| `baselines_paired_differences.csv` | `b938e1a743d829c7` | Yes |
| `baselines_sensitivity.csv` | `d621f9473529fd7c` | Yes |
| `fig01_data_funnel.pdf` | `2e08bada995818d0` | Yes |
| `fig01_data_funnel.png` | `abd11ca88a67ba13` | Yes |
| `fig06_baselines_formal_rank.pdf` | `27f802fce7bbd044` | Yes |
| `fig06_baselines_formal_rank.png` | `07e10fb863fdb31c` | Yes |

This establishes fixed-input, same-platform reproducibility—not correctness of the identities or heuristics. Both graph runs used the same existing local Matplotlib font cache, disclosed above. The seeds in the configured bootstrap and cleaning sample were applied and their outputs reproduce; hash-seed variation did not alter these artifacts.

The full requested-revision graph/evaluation rerun reproduces all five baseline results below. A standalone scalar-pair and multiplicity-weight bootstrap oracle, `network/all_metric_oracle.py`, imports no pipeline code and independently reproduces all five accuracies and intervals at CSV precision from the frozen ranks and regenerated scores. A separate paired oracle verifies the degree–PageRank difference. All use **129 labelled keys and 6,235 different-level pairs**; score ties receive one-half credit. The person bootstrap is algebraically equivalent to weighting each distinct original-person pair by the product of its two resampling multiplicities. Across all **1,000** configured draws the independent degree oracle agrees exactly. Resampled copies of one person do not become distinct same-rank comparison evidence. This verifies computation, not frequentist coverage under network dependence or uncertainty from erroneous identities, titles and mailbox selection.

| Measure | Reproduced accuracy | 95% person-bootstrap interval in output CSV | Comparison |
|---|---:|---:|---|
| Degree | 0.6549318364 | 0.5775–0.7279 | Matches |
| PageRank | 0.6174819567 | 0.5391–0.6884 | Matches; display double rounding noted in m5 |
| Weighted email received | 0.6125100241 | 0.5337–0.6844 | Matches |
| Exact betweenness | 0.5738572574 | 0.4880–0.6476 | Matches |
| Email sent, message count | 0.5223736969 | 0.4399–0.6001 | Matches |

The unrounded degree interval is **[0.5774760452, 0.7279151858]**. The README's 57.8 lower endpoint comes from rounding the already rounded CSV; direct percentage rounding gives 57.7. This is a display-precision issue, not an arithmetic discrepancy. The degree–PageRank paired difference is **0.0374498797**, interval **[−0.0055910584, 0.0781966486]**. The data do not establish degree's superiority to PageRank.

Independent edge reconstruction, conditional on the production recipient identity resolver audited separately in M1, M2 and M6, yields **219,398 directed edges over 20,757 nodes**, **188,126 eligible rows**, and **157,527 contributing messages**. Edge keys, weights, message multiplicities, degree and outgoing counts match exactly; weights sum to 157,527. There are zero self-loop edges and no external-address or placeholder-address nodes under the syntactic checks. This does not certify that the underlying people are correctly identified.

Sensitivity checks reproduce the reported **60.3–67.2%** degree range: removing CEO/president levels **60.34%**, at most ten recipients **62.8869%**, at most fifty **65.4691%**, old higher-title policy **65.07%**, excluding four disputed keys **66.53%**, and induced people-only graph **67.1612%**. The last changes weighted outgoing-count semantics (m1), not the degree result. Exact values and independent adjacency oracles are in `network/probes.log`.

The configured **5,000-message** cleaning comparison reproduces whitespace-normalized equality **0.7748**, median token Jaccard **1.0**, and share with Jaccard ≥0.9 **0.805**. Empty output is **366 (7.32%)** versus **177 (3.54%)**. Residual rates, pipeline versus comparator: Original Message **0.0008/0.0200**, Forwarded by **0.0004/0.0598**, header lines **0.0170/0.0782**, quote-angle markers **0/0.0006**. These are marker diagnostics, not authored-span accuracy. Two separate scratch runs of `text/clean_repro_light.py` reproduce the complete JSON and disagreement CSV byte-for-byte, both against each other and committed outputs:

```text
cleaning_crosscheck.json
4122f35a2dd476bb5dc3394ab97cd1f8898f825fe99dba3d976718c8a02e2c2a
cleaning_crosscheck_disagreements.csv
cfca71c3c8a46409411188750314edc2971ba1d6369c10df8b673f48c1973ae4
```

The lightweight runner selects the exact configured sample in metadata first, then reads its raw bodies in batches; it does not alter cleaner/comparator code. Commands and ordering are preserved in `text/clean_repro_light.py`, with hashes in `text/repro_a/checksums.json` and `text/repro_b/checksums.json`. The old labelled-thread comparison is **25/27 retained direct replies**, **25/35 same-parent reply links valid**, not 71% of an independently sampled current population; the fresh 60-link estimate is reported in M5.

## 3. Findings ordered by severity

### Critical

No newly demonstrated arithmetic or execution defect invalidates every reported network result. No claim of a critical finding is made merely because a heuristic can fail. The following major defects do prevent treating the data as validated employee-level text evidence.

### M1 — Identity mistakes still change labelled people and their measured functions

**Evidence and commands:** `identity/probe.py`, `inspect_targets.py`, `counterfactual.py`, `initial_probe.py`, `palmer_review.py`, `more_probes.py`; outputs of the same names in S/identity. Source: `identity.py:80–111,166–222`; `formal_rank.py:64–71`.

**Dana / Mark Dana Davis.** The pipeline maps 351 Dana-labelled messages to `dana davis`, but ten messages at the same address displaying “Davis, Mark Dana” to `mark davis`; three further messages at `mark.davis@` are also the latter. Corpus evidence identifies the same person: `benson-r/deleted_items/89.` describes personal desk allocations and signs “Dana” under the full Mark Dana header; `lavorato-j/all_documents/238.`, `455.`, `478.` likewise sign Dana. The title sheet gives Mark Davis Vice President, while its Dana Davis row has no title. Thus the evaluated VP receives degree **63**, while the other fragment has **237**. An independent edge-adjacency merge yields **266**, changes nine other labelled contact counts by one, and moves accuracy **0.6549318364 → 0.6655974338** on the same **6,235 pairs**. This is a sensitivity to a corroborated identity correction, conditional on the existing title—not independent proof of the VP title.

**Mark Palmer.** The shared `mark.palmer@` address has nine explicitly initialled S messages and 66 uninitialled ones. All 66 are assigned S because the share denominator contains only initialled messages. At least two are demonstrably A's PR work: `kean-s/all_documents/708.` and `lay-k/notes_inbox/465.` give the same personal extension ending **4738** as explicit “Mark A. (PR)” records `lay-k/inbox/546.` and `whalley-g/inbox/245.`. Mark S's explicit `kaminski-v/all_documents/1661.` says “Intended for Mark A. Palmer…”, establishing two people. I do **not** label all 66 incorrect simply from their topic.

**Impact:** Same-person fragments can cross a person-disjoint split; wrong-person assignments contaminate topic ownership and apparent functional roles. Confidence intervals over fixed, erroneous person keys do not capture this uncertainty.

**Fix:** Keep evidence-backed entity records and reviewed aliases across names, addresses and directory IDs; audit all 129 labelled joins; preserve uncertainty for shared addresses rather than letting a selected minority of initialled messages assign the rest. Add full-header/signature regression cases, regenerate graph/text aggregates, and report ambiguous-person exclusion sensitivity.

### M2 — Display-name grammar and entity typing still invent people

**Evidence:** `identity/inspect_targets.txt`, `more_probes.txt`, `quantify.txt`, `network/typing_check.log`. Source: `identity.py:80–111,139–146`; `network.py:123–126`.

- Two analysis records, `salisbury-h/read/297.` and `313.`, have “George Wasaff, Global Strategic Sourcing” and become **`global wasaff`**. That invented key has degree 3 / outgoing count 2; ordinary George Wasaff has degree 143. The comma is a title suffix, not surname-first syntax.
- `salisbury-h/read/314.` attributes Robert Knight's message to a role string beginning **`director voice operations…`**. Five other headers and his signature identify Robert Knight; his role suffix is being parsed into a different entity.
- **154** messages under **32** person-typed keys have `CN=MBX_*` headers; **118** enter analysis. Not every one was individually proved non-person, but explicit counterexamples include Executive Compensation, Hottap Helpdesk and conference rooms. `may-l/calendar/1.` is **“Conf.Room ECN2760”**, yet person-typed and analysis=True. Name normalization detects any digit, while role typing only recognizes a wholly numeric word; `ECN2760` falls through.
- Two unresolved initial-base keys, `mark palmer` and `mark taylor`, become people because graph ambiguity is inferred only from modal address-table rows. Each has one edge to a list; neither changes the reported people-only degree result.

The **167,970-row analysis mask is not a person-text dataset**: 165,397 person-typed, 1,087 null, 754 role, 551 address-only and 181 list rows. The 2,573 non-person/null rows are not necessarily a Phase 1 bug if Phase 3 explicitly filters them, but even the current person label needs correction before such a filter is sufficient.

**Fix:** Parse personal names separately from title/department suffixes; persist message-level type, ambiguity and evidence; use consistent alphanumeric-role rules; audit shared mailboxes. Define and publish a separate person-text eligibility funnel. Do not call heuristic keys verified employees.

### M3 — The four-word speech-act exemption actually counts an 80-character prefix

**Evidence/command:** run `text/routine_probe.py`; inspect `speechact_truncation.json` and `routine_5to8words.json`. Source: `senders.py:57–61,119–121`; `prepare.py:92–94,103–104`.

`speech_act` calls `template_of`, which truncates at 80 characters before splitting into words. Consequently **503** of the 3,296 supposedly short routine records contain more than four actual words; **180** are internal and **139** enter analysis. Examples include `baughman-d/inbox/304.` (**1,067 words**), `beck-s/inbox/390.` (**434**) and `benson-r/inbox/116.` (**1,739**). A long divider occupies the entire counted prefix. A long URL similarly exempts an **866-word** news digest in `causholli-m/deleted_items/106.`. Some count discrepancies involve salutations; these long examples do not.

Conversely, prefix repetition still suppresses real work. The probe finds **251 internal, non-automated, non-structured excluded messages** in 12 groups with 5–8 prefix words. Checked examples include a **21-record** James Derrick group represented by “Please print the attachment. Thank you.”, a **24-record** Wendi LeBrocq group whose representative signature makes “Please see attached” too long, and a **16-record** Britt Davis group sharing a privilege notice whose inspected representative contains substantive legal analysis (`sanders-r/all_documents/336.`). Group counts are reproduced; distinct substantive contents were not independently inspected in every member.

**Impact:** Both speech-act frequency and topic ownership are systematically distorted by formatting, signature length and professional boilerplate.

**Fix:** Measure full utterance length after explicit signature handling. Do not equate a shared short opening with a repeated full message; distinguish boilerplate from substantive remainder. Add divider/URL, signed-request and different-legal-body fixtures. Recompute per-person and per-title retention rates.

### M4 — Cleaner tightening introduces quote leakage; machine-text filtering remains incomplete

**Cleaning evidence:** `text/clean_regressions.py` executes both old and current cleaners on identical saved raw bodies. Source `clean.py:33–36` now requires cc/Subject within two intervening lines of To. Real recipients wrap longer. Two of the old 200-message sample outputs regress: `hodge-j/all_documents/56.` **43→1,359 characters**, and `jones-t/sent/6034.` **57→1,090**. Three other changed outputs improve. Two further regressions occur among the fresh reply sample's 120 raw records: `dasovich-j/notes_inbox/3435.` **300→1,176**, and `3440.` **108→979**. Both retain Susan Mara's quoted prose/signature under another sender because To wraps over five lines. Original agenda and “Received: from supplier” negative controls now survive; that real correction does not negate the new failures.

**Empty output is not automatically wrongful deletion.** On the configured 5,000-message sample, ours is empty on 366, email_reply_parser on 177, and both on 155: **211 ours-only empties**, **22 ERP-only**. First-cut mechanisms for the 211: **189 Lotus forward banners**, 12 Outlook, five Lotus headers, four transport headers, one On…wrote. The text auditor inspected the 22 non-banner cases plus 20 randomly selected banner cases (seed 2026092510). Much excess emptiness is expected forward removal. But `beck-s/sent_items/87.` loses Beck's own questionnaire answers inside the form, and external-list `richey-c/deleted_items/23.` loses a bottom-posted technical answer. The latter demonstrates extraction behavior, not prevalence among internal analysis messages. These are not grounds to call all 366 empties erroneous.

**Automation evidence:** `text/targeted.py`, `label_analysis.py`, `feed_kept.json`, `machine_candidates.json`; source `senders.py:49–54,105–110`. Of all 11 retained feed-account analysis messages, eight are human and three machine-generated: Pete Davis parsing/error records in `platter-p/deleted_items/13.` and `williams-w3/bill_williams_iii/621.`, plus ipayit routing notification `skilling-j/inbox/1195.`. Two genuine ipayit replies are also retained, refuting the response's whole-account-exclusion explanation.

Targeted inspection confirms at least 16 additional surviving structured records: seven performance-management notices with unmatched openings, two colon-free “Calendar Entry” records (`nemec-g/notes_inbox/2242.`, `2435.`), one automatic NEST notice, and six daemon.extra leave approvals. The regex requires narrow literal openings. A fresh **100-row analysis sample**, seed 2026092508, independently contains one explicit machine message (`bass-e/all_documents/701.`), two retained-quote cases, a copied news story and contact/help boilerplate. Two institutional notices and one completion notice are uncertain; 92 have no definite contamination identified in this inspection, not a guarantee of cleanliness. A separate random 60 flagged structured records yielded no definite human false positive; synthetic prefix controls show possible false positives but do not establish corpus prevalence.

**Impact:** Later language models can learn colleagues' or institutional text as an employee's contribution. The count 3,113 is reproduced, not a validation of detector coverage.

**Fix:** Recognize folded header blocks rather than fixed line proximity. Build blinded authored/quoted span labels and stratified automation gold (including singleton feed templates and high-volume unflagged accounts). Measure both deletion and contamination; preserve mixed-account human prose while detecting unique alerts. Use format/provenance evidence, not template uniqueness as proof of human authorship.

### M5 — Reply-kind edges remain unreliable as response observations

**Source/commands:** `threads.py:87–109`; `text/probe.py`, `label_threads.py`, `targeted.py`; full labels `fresh_reply60_labels.json`, raw pairs `fresh_reply60.json`.

A fresh simple random sample of 60 current reply-kind links, seed 2026092507, gives **43 direct, 10 wrong immediate parent, two forwards/relays, one same-author update, four uncertain**. Supported precision **71.67%**, Wilson 95% **59.23–81.49%**; counting every uncertain case as valid gives 78.33%. This is a small AI-labelled sample; the interval does not cover annotation error or person/thread clustering.

Examples: `campbell-l/inbox/995.`→994 is a sender revising his own invitation; `kaminski-v/sent/4441.`→4442 forwards a prior answer to an assistant but inherits Re; `hyvl-d/all_documents/7.`→6 is a delegated relay. `dasovich-j/notes_inbox/3435.` first-quotes Susan Mara but links to James Steffes's sibling reply 3440. `symes-k/sent/893.` links to March 8 material although it first-quotes a March 16 question.

The original sample reproduces **25/27** correct direct replies kept as same-parent reply-kind, and **25/35=71.43%** among old same-parent links still labelled reply. That denominator excludes changed parents; it is not a fresh population estimate. One old correct answer `watson-k/inbox/200.`→`mcconnell-m/tw_projects/misc_tie_ins/6.` becomes forward-kind. Another `sager-e/notes_inbox/448.` changes from correctly quoted 396 to 391. The new 391 raw body was not independently inspected in this re-audit, so no stronger replacement-parent claim is made.

The causal-inversion check searches the child's ≥40-character opening anywhere in the prior body, not just prior quoted text. A synthetic genuine reply repeating the parent's instruction is incorrectly rejected (`synthetic_causal_guard.json`). No population frequency is inferred from that fixture.

**Impact:** Response latency and dialogue supervision cannot treat these links as observed answers. The response's “partly fixed” label is fair, but the remaining uncertainty must accompany any downstream feature.

**Fix:** Resolve identities before matching addresses; separate relay/forward semantics from inherited Re; compare inverse-causality evidence specifically to quotation spans; abstain on missing immediate parents. Evaluate a new blinded human set, including missing-link recall, before using response outcomes. If Phase 3 does not use reply features, explicitly exclude them rather than quietly treating these edges as truth.

### M6 — Deduplication is still address-rendering dependent

**Commands/evidence:** `dedupe_probe.py`, `dedupe_followup.py`, `identity/dedupe_review.py`; `dedupe_summary.json`, `dedupe_headers.json`, `identity/dedupe_review.txt`. Source: `dedupe.py:78–101,110–126`; `identity.py:226–236`; the parsed schema in `ingest.py` omits X-To/CN recipient evidence.

**A distinct recipient's attribution is still lost.** Keeper `haedicke-m/california/3.` and discarded copy `williams-w3/bill_williams_iii/874.` share sender Ray Alvarez, timestamp and the FERC briefing-paper subject. Both raw X-To headers separately name **Carla Hoffman** and **Christopher F. Calger**, the latter with `CN=CCALGER`. The keeper retains `f..carla@enron.com` but no Calger address; the discarded copy has `f..calger@enron.com`, which resolves to Christopher Calger. Selecting one copy's parsed list therefore loses a corroborated recipient attribution. This does not prove that the aggregate Alvarez→Calger graph edge is absent: other messages can supply it.

**A retained recipient is assigned to the wrong person.** In `salisbury-h/inbox/811.`, raw X-To explicitly identifies **Robert E. Anderson**, corroborated by discarded copy `williams-w3/bill_williams_iii/396.`. Its retained `e..anderson@enron.com` resolves instead to **Gary Anderson**, using a modal table built from ten sender messages. This directly demonstrates a failure of global sender-derived recipient mapping in the presence of contradictory per-message recipient evidence. The Calger pair also identifies Mark A. Palmer in one X-To rendering while the other copy's uninitialled address resolves to Mark S, corroborating M1.

Across the corpus, **82** collapsed groups have **141 raw recipient assignments** absent from keepers, **137 internal**. These are diagnostic candidates, **not 137 proven missing people or contacts**. Inspection finds aliases, malformed addresses and degraded renderings: Michael Brown in `campbell-l/inbox/1027.` and George Phillips in `forney-j/sent_items/96.` remain unresolved from keeper addresses despite usable names/addresses in discarded copies.

**The 233 additional records are not 233 verified physical sends.** The rule produces 233 extra survivors in 194 groups, but disjoint address strings do not establish disjoint people. Three checked pairs are alias/rendering-ambiguous: `kaminski-v/discussion_threads/8129.` versus `notes_inbox/55.` uses Vincent Kaminski's long address versus `vkamins@`; `linder-e/all_documents/814.` versus `notes_inbox/131.` uses `eric.linder@` versus `eric_linder@`; `skilling-j/deleted_items/426.` versus `inbox/420.` renders `jskilli@enron.com` as `skilli@enron.com <j>`. Raw headers confirm the ambiguity. All three senders are external, so these particular pairs do not enter the internal-sender analysis/network. Separate delivery to aliases is possible; generated Message-IDs cannot decide SMTP transaction identity. I do not count these as proven false splits.

**Impact:** Folder-priority selection still changes person-level recipient attribution, hence network weights, contacts and future conversational features. The response's blanket “fixed” status is too broad. Both original Bass messages now survive, but that regression does not establish general preservation of recipient evidence.

**Fix:** Preserve provenance-rich recipient evidence from all high-confidence copies, including X-To/CN, and reconcile aliases before selecting or combining recipient lists. Do not blindly union address strings, which can double-count people. Retain uncertainty and test network sensitivity to ambiguous mappings. Describe the 233 as heuristic candidate separate sends until independently adjudicated.

### M7 — Regression tests do not verify freshly generated corpus behavior

**Commands/evidence:** `original_mutants.py`, `test_safety_mutations.py`, `identity/mutations.py`, `network/mutate_bootstrap.py`; `original_mutants.json`, `corpus_mutation.log`, `identity/mutation_dominance.txt`, `network/mutate_bootstrap.log`. Source `tests/test_corpus_regressions.py:12–25,48–51,66–74`, `tests/test_evaluate.py:26–46`, `Makefile:9–15`.

The two simplest original mutants are now caught. However:

- All **nine corpus regression tests pass** when `resolve_people`, `resolve_recipient`, `deduplicate`, `link_replies`, `automated_messages`, `structured_record` and `speech_act` are replaced in memory with functions that raise an exception. The tests never call them; they read precomputed Parquet. This does not mean the ordinary unit suite would pass those mutations.
- Removing the initial-dominance threshold entirely passes **28 identity/formal-rank/corpus tests**.
- A fake bootstrap returning `(accuracy,accuracy)` only for perfect/reversed orderings and `(0,1)` otherwise passes **all nine evaluation tests**. The real mixed-fixture CI is **[0.7165548823,0.8563473352]**. Current production bootstrap is independently verified; the defect is coverage, not demonstrated wrong production arithmetic.

Static artifact tests can be useful if provenance is checked and artifacts are freshly built. Here `make all` runs tests **before** regeneration; on a fresh checkout corpus tests skip, and on a populated checkout they can certify old data. Conditional path assertions can also omit a missing counterexample without failing.

**Fix:** Regenerate a frozen raw-message mini-corpus in integration fixtures, assert required cases exist, run generated-corpus assertions after data/identity stages, and verify source/config/input hashes. Add threshold boundaries and non-degenerate numeric bootstrap oracles. Do not use “113 passed” as evidence of annotation validity.

### Minor findings

#### m1. People-only sensitivity changes the meaning of “messages sent”

`evaluate.py:143–148` filters the full weighted graph and passes `sent=None`; `network.py:83–84` then uses weighted out-strength. The induced graph has **3,085 fractional outgoing values**, total retained mass **146,071.4672**, versus **150,797 actual contributing messages**. Outgoing accuracy is **0.5272654** versus **0.5269447** for message counts. Degree remains **0.6716119**. Evidence: `network/probes.py`, sections `PEOPLE_ONLY_DEFINITION`/`PEOPLE_ONLY_FRACTIONAL_OUT`. The induced weighted graph is defensible, but the outgoing measure must be labelled retained weight, or rebuilt with exact person-target message counts. Add a mixed person/non-person recipient fixture.

#### m2. Relative tie tolerance is asymmetric at a floating-point boundary

`evaluate.py:34–37` uses asymmetric `np.isclose`. `network/tolerance_checks.py` reproduces scores **[17.80489355345007,17.804893571254965]**, levels[0,1]: accuracy **0.5**; reversing both arrays gives **1.0**. A constructed boundary sweep finds 220/100,000 examples, not an estimate of real data frequency. **No such asymmetry or effect was found in the current five ranked score vectors.** Use a symmetric condition such as `abs(a-b) <= rtol*max(abs(a),abs(b))`, and test permutation invariance.

#### m3. Probable copies still participate in threads

`prepare.py:99` excludes automated/structured messages from linking, but not probable copies. `text/targeted.py` finds **45** linked copy-children, **56** copy-parents, **91** links involving either, including **67 reply-kind**. Examples: `beck-s/sent_items/155.`→flagged `beck-s/europe/5.`; `brawner-s/sent_items/2.`→flagged `williams-w3/inbox/56.`. Not every flagged message is proven a duplicate, so not all 67 are necessarily false responses. Thread canonical copy families or propagate uncertainty consistently, and test invariance to adding an export-shifted copy.

#### m4. Cache provenance is incomplete, and Makefile ordering is not encoded

`prepare.py:47` now verifies the archive on every call. But lines 50–55 stamp only archive checksum and `ingest.py` source. `provenance_probe.py` builds the four-message test archive, parses it, changes only the scratch cached table to **one row with “POISONED CACHE TEXT”**, and calls the parser again. The valid archive is verified; the altered row is accepted because the stamp remains unchanged. A runtime dependency patch to `ingest.getaddresses` changes an uncached sender to `changed-parser-dependency@enron.com`, while the cached path still returns Kay Mann. This simulates a changed parsing dependency; it is not evidence that current production data are poisoned. Hash the parsed output and include Python/dependency/schema fingerprints, validate the stamp defensively, and write data/stamp atomically.

The exact copied Makefile was run with a scratch `uv` shim that records starts/ends and sleeps 0.4 seconds:

```sh
PATH=/tmp/enron-reaudit-20260925.WVW9gE/shims:$PATH make -j 9 all
```

Working directory was S/environment_project, never the real pipeline. `make_trace.jsonl` shows identity finishes before prepare starts; evaluate and figures start before network finishes. `Makefile:9` lists sibling prerequisites, not dependency edges. Ordinary serial make traverses the stated order, but inherited parallel MAKEFLAGS can race stages. Encode actual dependencies or explicitly serialize. `validate_threads` has no target, so `results/thread_link_check.json` is not rebuilt by make all; the user explicitly noted this separate stage, but “every stage/artifact” wording remains inaccurate.

#### m5. Remaining documentation mismatches and overstatements

Each item was checked against the probes above rather than inferred from a commit subject:

| Location | Remaining mismatch | Correction |
|---|---|---|
| README:51; response dedupe row | 233 separated records are described as distinct sends, although the rule operates on raw recipient spellings | Call them candidate separate sends; report alias reconciliation and uncertainty (M6). |
| README:53; response S3; sender module prose | “Long”/“short” messages described by full-message length | Current code counts truncated template words; correct implementation and re-count (M3). |
| README:57–58 | From feed accounts “only repeated alerts” removed | Repeated human prefixes can be removed; empty texts are also automated; singleton alerts survive. Describe heuristic behavior, not known alert authorship. |
| README:61–67,87–89 | Person counts read as established entity identities | They are heuristic types and include demonstrated non-person/ambiguous keys (M2). |
| README:88 | All 14,755 unresolved addresses “never sent mail” | **126** occur in the internal-sender table; **119** have positive outgoing graph counts. Examples include sap_security (62), eserver (84) and bodyshop (5). `network/recipient_checks.log`. |
| README:69–73; response thread row | 71% phrasing omits same-parent conditioning | It is 25/35 among old same-parent reply links, not an independent current-population precision estimate. Add fresh sample and uncertainty (M5). |
| README:81–83; config disputed labels | All four labels called contradicted | Hayslett may concurrently be VP/CFO/Treasurer; this establishes ordinal ambiguity, not that VP is factually false. Keep disputed flag without overstating contradiction. |
| response S1 | ipayit whole-account/name-rule excluded | Two human messages and one automated routing message survive; correct explanation. |
| response placeholder row | “Dropped as senders” | Placeholder address nodes are dropped; messages with usable individual evidence remain by design. |
| funnel `messages_linked_as_replies` | Counter includes all non-null reply_to | **39,032 links =32,326 replies +6,706 forwards**. Rename total and report both; source `prepare.py:100`. |
| Makefile:1–2; README:7–8,141; response provenance | Every stage/artifact, “in order” | validate_threads omitted; no parallel dependencies; tests precede new data. |
| README:148; response cache row | Cache rebuilt whenever parser changes | Source-hash change handled, dependency/runtime changes and cache-data integrity not covered (m4). |
| `identity.py:27–29,231–235` | Recipient fallback “literally first.last” | Empty dot components are removed and nicknames canonicalized. Actual `juan.canavati.@` six mentions and `martin..gonzalez@` three resolve; no evidence those matches are wrong. Clarify grammar. |
| config initial_share; response “two thirds” | 0.6667 is not exactly 2/3 | A synthetic 2:1 support case differs; no current corpus difference established. Use intended exact threshold or document approximation. |
| Commit14f43b1 “make evaluation exact” | Too broad read literally | Integer outgoing counts and exact non-sampled betweenness are verified; PageRank is numerical and CIs bootstrap estimates. Commit history is not validation. |

One additional display inconsistency is double rounding: actual PageRank accuracy is **0.6174819567** (61.7% in README), but the CSV rounds to **0.6175** before `figures/baselines.py:36` formats **61.8%**. `network/rounding_check.log` records the extracted plot labels. Preserve full precision in machine-readable results and round once for display; this does not change the substantive result.

The response appropriately leaves functional-importance validation, temporal title truth, mailbox selection and human annotation open. I do not treat those acknowledged future tasks as newly fabricated results. The old 200-message cleaning figures are explicitly about the previous version and match the archived labels; they are not a current-cleaner error estimate. The main baseline, paired-difference, sensitivity and cleaning tables are addressed numerically above; source-code comments still claiming “every parameter” contradict the actual fixed source rules, although README now makes that distinction.

README's related-work number is externally supported: Table 1 of [Agarwal et al. (2012), p. 163](https://aclanthology.org/P12-2032.pdf) reports **79.31% on 440 core-employee dominance pairs**. Its graph includes To/Cc/Bcc, is undirected, and uses a different reporting-line gold standard; the project's warning that this is not a replication is warranted. I checked the primary paper, not a secondary summary.

## 4. Phase 3 leakage risks and required tests

| Risk | Current evidence | Required test before a text-model result |
|---|---|---|
| Title/name/contact leakage | All 41 previously confirmed title-signature examples remain; new quote leakage carries other people's identities too | Blindly annotate signature/quoted spans; compare unredacted, signature-redacted, name/contact-redacted, and title-keyword-only / identity-only baselines. Keep identity evidence in audit metadata, not model inputs. |
| Same employee split across keys | Corroborated Dana/Mark Dana split; invented title-suffix keys | Freeze reviewed person records before person-disjoint splits; test no alias component crosses train/test; audit every labelled join. |
| Different people conflated or misassigned | Mark Palmer personal-extension examples | Abstain on ambiguous metadata; compare excluding all ambiguous/shared-address cases; report attribution confidence and sample error rates. |
| Automation/boilerplate mistaken for expertise | Prefix-length bug, system notices, copied news, room records | Stratified human precision/recall for machine/document filtering; per-person/title retention; compare models with suspected institutional/copy text removed. |
| Quote and answer extraction errors | Folded-header regressions; inline/bottom answers removed | Independently blinded authored-vs-quoted span gold, including negative controls; report span precision/recall and sensitivity to uncertain messages. |
| Copy/thread leakage | Raw-recipient alias splits; 1,531 probable shifted copies; 91 links involving them | Build conservative canonical and near-duplicate families; keep each family/thread in one split; verify no near-identical text crosses split. Do not rely on content_key alone when timestamps or recipient spellings differ. |
| Future information in preprocessing | Template frequency, identity modes/initial support, graph scores computed corpus-wide | For temporal claims fit preprocessing/model choices on pre-cutoff material, transform future data without refitting; use past-only graph features and temporal labels, with explicit look-ahead tests. |
| Mailbox availability / custodian leakage | 104/129 labelled access-proxy overlap; median degree 197 vs 3; degree/mailbox-size rho 0.592 | Leave-mailbox-out/visibility-matched evaluation; mailbox-only and message-volume baselines; audit where sender vs recipient evidence is observable. Low trivial-predictor accuracy does not eliminate selection bias. |
| Invalid response supervision |43/60 fresh supported direct replies | Human-validated linkage precision/recall, confidence gating and uncertainty propagation; omit response-based outcomes until validated. |
| Rank proxy mistaken for functional importance | Undated titles, disputed roles, no validated dependence outcome | Pre-specify the functional construct and an independent outcome; degree/title association alone cannot validate organizational dependence or effects of employee departure. |

Freeze validation labels before tuning new rules. The original 60-message thread set has now informed fixes and should be a regression set, not held-out evidence. Fresh AI labels in this audit are diagnostics, not a substitute for independent human adjudication.

## 5. What could not be verified

- At the audited revision, no personnel directory, time-indexed reporting lines, transport logs, or original stable reply IDs were available to establish all identities, titles, true parents or genuine resends. A source spreadsheet checksum establishes file identity, not correctness of every title. The audited spreadsheet bytes match the prior independently retrieved Archive copy; this re-audit did not refetch it externally. A new Agarwal gold-standard artifact arrived through another process during the audit; its ingestion, mapping and new evaluation are outside this revision's audit.
- No false same-CN alias merge was proved among the 12 applied rules. Suspicious examples inspected were supported by signatures. No actual false first.last recipient match or false automatic-placeholder classification was established; synthetic surname collisions are risks, not observed prevalence.
- Manual sample labels here were produced by Codex, not blinded human annotators. The fresh reply interval excludes annotation and clustering uncertainty. Samples do not establish corpus-wide identity error, true-reply recall, or every false-cut/automation rate.
- The raw archive was checksum-verified again. Parsing itself was not repeated from scratch: the audited raw-Parquet SHA-256 is identical to the previous audit's independently regenerated raw table, and at the requested revision `ingest.py` and `uv.lock` were unchanged from that earlier audit. The concurrent later lockfile change is outside this comparison. This run reproduced downstream preparation from the matching cache. This is explicitly not a new end-to-end raw-parse execution.
- The full-size betweenness call was rerun from the same library, not checked against an independent full-size Brandes implementation. An independent exhaustive-path oracle passed 30 five-node graphs; a separate NumPy PageRank oracle agreed to 4.1e-14. These checks support the implementation, not validity of the graph's identity assumptions.
- No cross-platform reproducibility was tested. Fresh environment installation and tests are macOS-only; fixed local font-cache reuse is disclosed. Runtime duration on this memory-constrained, concurrently used machine is not a benchmark of the author's approximate 30-minute claim.
- The new parent 391 for `sager-e/notes_inbox/448.` was not fully inspected after a follow-up was stopped to relieve memory pressure. The loss of its previously supported 396 link is verified, but the report does not invent a judgment about the unread replacement body.
- No corpus-wide true-“functional importance” outcome has been validated. This remains the planned research question, not an achieved result.

### Repository and evidence integrity

`original_hashes.json` records **69 original files**; the initial Git status was clean. The subsequent integrity check (`final_integrity.py`, `final_integrity.json`) found **63 unchanged** and six changed by the concurrent gold-standard work: `Makefile`, `config.yaml`, `pyproject.toml`, `src/enron_importance/evaluate.py`, `tests/test_evaluate.py`, and `uv.lock`. All original data, results and figures still match their initial hashes. Another process advanced HEAD to **`48d200fa85045d0a80369af256b7509952be2392`**; I did not create that commit or change any of those files. New gold-standard artifacts are outside the 69-file initial inventory and outside this audit.

My only repository addition is this report, left uncommitted. I did not modify pipeline code, tests, configuration, data, prior reports, results or figures, and did not commit, push, open a PR, or revert concurrent work. Scratch scripts, labelled examples, probe logs, frozen source/input snapshots and reproduction hashes remain at **`/tmp/enron-reaudit-20260925.WVW9gE`**. The changed live worktree/HEAD must not be confused with the pinned source and inputs actually audited.
