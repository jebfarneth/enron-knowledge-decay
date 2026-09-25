# Independent audit: Agarwal hierarchy evaluation

Date: 2026-09-25. Audited commit: `e476f688c323b7b6ad06b86f93f5e2737b40cbac`, branch `main`. Component-introducing commit: `48d200fa85045d0a80369af256b7509952be2392`.

Repository: `/Users/jebfarneth/projects/enron-knowledge-decay`.

Scratch evidence: `/tmp/enron-gold-audit-20260925.obXnMh`.

## 1. Verdict

**No—not as a validated person-level gold-standard result or replication of the published benchmark.** The stored 13,241 pairs and all 20 accuracy/interval rows reproduce, including an independent reconstruction of the hierarchy and an independent bootstrap oracle. However, the matcher demonstrably assigns executive labels to assistants; some release UIDs themselves combine executives and assistants, including their hierarchy positions; non-null keys are misreported as graph matches; and a single plausible Lou Pai address remapping changes degree accuracy by 2.34 percentage points. The 83.1% check is reproducible but uses maximum-degree raw aliases, not the paper's person network, and does not authenticate the pair construction. The result can become reportable after identity/position adjudication or explicit uncertain-case exclusion, coverage-aware reporting, documented hierarchy-policy sensitivity, and removal of the replication claim. Until then, it is a reproducible calculation on an inadequately validated reconstructed benchmark—not evidence that the system measures functional importance with 80–84% accuracy.

### Scope, evidence and preservation

I audited this component, not the previous data-layer findings. Prior reports supplied leads only; implicated current records were reread. No source, tests, configuration, input data, generated data, results or Git history were edited. This report is the only intended repository addition.

`initial_hashes.json` records SHA-256 hashes of 141 relied-upon files: tracked non-legacy files, processed/interim data, and the supplied hierarchy release. `initial_git.json` records the initially clean worktree, HEAD and introducing commit message. Final verification is recorded in `integrity_result.json` and `final_hashes.json`; the check is repeated after writing this report. All evidence paths below are relative to the scratch directory unless identified as repository paths. The separate `enron-knowledge-decay-fixes` worktree was not used.

Read sources include the complete hierarchy/evaluation implementation and tests, current identity/network code, config/comments, README references, introducing commit, supplied DOCX release notes and v1.1 release documentation. The primary paper was read and saved as `documentation/P12-2032.pdf`: [Agarwal et al. (2012)](https://aclanthology.org/P12-2032.pdf).

The scratch `pinned_project` contains a source/config/lock copy. `uv sync --locked --group dev --project /tmp/enron-gold-audit-20260925.obXnMh/pinned_project` succeeded with CPython 3.12.13 and 26 installed packages. The 14 focused tests pass both in the existing environment and the fresh environment (`fresh_environment_tests.log`). This is not a rerun of the entire data pipeline or every test.

For the exact replay commands used below, define:

```sh
TASK_REPO=/Users/jebfarneth/projects/enron-knowledge-decay
TASK_EVIDENCE=/tmp/enron-gold-audit-20260925.obXnMh
TASK_PY="$TASK_REPO/.venv/bin/python"
cd "$TASK_REPO"
```

Scripts contain the complete calculations and input paths; logs/CSVs/JSON preserve outputs. Nothing requires an undocumented replacement implementation inside the repository.

## 2. Reproduction

### Claimed numbers

“Match” below means numerical reproduction, not validation of the scientific interpretation.

| Claim/reference | Independently obtained | Assessment |
|---|---:|---|
| Complete `entities.bson` read | 95,941 documents, through EOF; independent BSON decoder agrees on every document | Verified |
| Pinned entity SHA-256 | `a43fa4bfa4b09f23ceec03881f549d1725d28e912806ba0a6f27228d2fceea94` | Match |
| 1,518 hierarchy employees with email | 1,518, out of 2,200 hierarchy records | Match |
| 682 hierarchy records without email | 682; 76 actually bridge email-linked ancestors and descendants | Count matches; not all are intermediaries |
| Published 2,155 immediate relations | 2,397 across all employee records; 1,430 with email endpoints; 1,708 if no-email nodes are traversed between emailers | Historical count not reproduced |
| 13,241 reconstructed pairs | 13,243 before removing two mutual directions; 13,241 afterward | Match |
| Published 13,724 pairs | No tested construction reproduces it; published categories sum to 13,723 | Mismatch, unresolved |
| 1,484 employees “matched to a graph node” | 1,484 non-null keys, but **1,419 graph-present** | Wording false; overcounts by 65 |
| 12,937 pairs with both matched | 12,937 non-null/non-null; **11,605 graph-present/graph-present** | Non-null count matches; actual graph coverage overstated |
| Core/inter/non-core 487 / 5,633 / 7,121 | 487 / 5,633 / 7,121 | Match |
| Published core/inter/non-core 440 / 6,436 / 6,847 | Not reproduced | Different benchmark composition |
| Degree 80.5% | 80.5113% | Match |
| PageRank 81.5% | 81.4704% | Match |
| Betweenness 75.6% | 75.6476% | Match |
| Messages sent 69.2% | 69.1828% | Match, for stored `out_strength` |
| Raw-address degree 83.1% | **83.1017% using maximum raw-alias degree per gold employee** | Numerical match; not the paper's graph method |
| All stored gold results reproducible | All 20 rows; independent numeric maximum difference 0.0 | Match |

### Reproduced accuracy table

Percentages; these retain the current mappings and missing-score-zero convention.

| Measure | All 13,241 | Core 487 | Inter 5,633 | Non-core 7,121 | All-pair bootstrap interval |
|---|---:|---:|---:|---:|---:|
| Degree | 80.51 | 74.02 | 86.76 | 76.01 | 66.73–90.50 |
| Weighted in-strength | 79.02 | 58.73 | 86.54 | 74.46 | 66.24–89.23 |
| Messages sent / out-strength | 69.18 | 50.92 | 82.20 | 60.13 | 57.54–80.25 |
| PageRank | 81.47 | 64.68 | 87.59 | 77.78 | 68.06–91.74 |
| Betweenness | 75.65 | 64.89 | 88.47 | 66.24 | 63.08–86.06 |

`evaluation/reproduced1.csv`, `reproduced2.csv` and the committed CSV are byte-identical, SHA-256 `7d851b2137eb14c113f40065f9c7dcb895e054ebb726566060942102b72a4217`. The second process used `PYTHONHASHSEED=997`. `evaluation/independent_oracle.csv` independently reproduces the numeric values, including all CI endpoints.

The entire gold stage was also redirected to scratch and repeated in the fresh locked environment. Both runs match the original Parquet bytes:

- Employees: `455de108a1dca6ab6b0dc4cfeaffe94d15b01965116ab4a98578f21cb459c971`.
- Pairs: `e340066298a3b37c7d9ee5fb2975869a48970fe36a090c81f81b503e9075b765`.

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/reproduce_gold_stage.py" stage_run1
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=997 "$TASK_EVIDENCE/pinned_project/.venv/bin/python" "$TASK_EVIDENCE/reproduce_gold_stage.py" stage_run2
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/reproduce.py" "$TASK_EVIDENCE/evaluation/reproduced1.csv"
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=997 "$TASK_PY" "$TASK_EVIDENCE/evaluation/reproduce.py" "$TASK_EVIDENCE/evaluation/reproduced2.csv"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/audit.py"
```

### What the hierarchy reader actually does

`gold_standard.py:49–79` unions top-level and nested `incident_edges`, reads `ffrom → to`, identifies employee ownership of every position node, and traverses successors through non-employee nodes until the next employee. It builds an employee-level immediate graph, computes transitive reachability, restricts endpoints to email-linked employees, and removes pairs whose reverse also exists. Multiple positions are merged into one employee **before closure**. No-email records remain as intermediate employee nodes during closure. `bool(mailboxes)` supplies core status. In this release, the UID-based `has_email` test agrees with actual email availability on every hierarchy record.

An independent decoder in `hierarchy/audit_hierarchy.py` checks BSON framing, supported types, complete record consumption, array indexes and duplicate keys; its decoded documents agree with PyMongo. It then constructs its own adjacency lists/BFS, without importing the production hierarchy function. Inventory: 987 units, 3,479 unique positions, 3,458 unique typed edges, 207 multi-position employees. No duplicate position ownership or dangling edge endpoint was found.

The documentation defines the current direction correctly. Observed relations are 1,860 `contains`, 549 `manages`, 1,049 `supervises`; their endpoints are not uniformly employee-to-employee. Top-level fields supply 117 edges absent from nested fields, so both locations are necessary. `position_id` is an occupation-category string, not the unique position-node ID or numerical management rank. There are 66 distinct employee-level values and a maximum position-DAG path of 25 nodes including units; the paper's “65 levels” is not verified as graph depth.

### Alternative constructions and the historical count gap

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/hierarchy/audit_hierarchy.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/hierarchy/extended.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/hierarchy/policies.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/hierarchy/name_sensitivity.py"
```

| Construction | Immediate all / email endpoints | Final asymmetric email pairs |
|---|---:|---:|
| Current, independently reconstructed | 2,397 / 1,430 | 13,241 |
| Drop no-email employees before closure | 1,430 / 1,430 | 8,970 |
| Traverse no-email records between emailers | 1,708 / 1,708 | 13,241 |
| Position closure first, then map to employees | — | 8,916 |
| Nested-node edge fields only | 1,902 / 1,101 | 8,608 |
| `supervises` only | 1,035 / 581 | 816 |
| `contains` + `manages` only | 1,365 / 852 | 2,329 |
| Highest-title nodes, delete other positions | 2,049 / 1,185 | 5,134 |
| Highest-title nodes, traverse other positions | 2,240 / 1,281 | 8,188 |
| First position only, traverse others | 2,172 / 1,228 | 7,570 |
| Last position only, traverse others | 2,166 / 1,211 | 6,820 |

Reversing all edges preserves the count but reverses every prediction target; reversing unit containment is contradicted by documentation and destroys paths. Continuing past another position of the same owner does not change current counts. Immediate position-to-position relations through units count 2,471, including 10 between positions belonging to the same owner. None recovers 2,155. Merging 25 repeated non-placeholder names among no-email records produces 13,285 pairs, also not the paper; it is an exploratory sensitivity, not a validated correction.

The 682 no-email records include 101 literal `(vacant)` and ten `?` names, so they should not all be described as known distinct people. Preserving them contributes 4,271 pairs. A `???` VP record bridges nine email-linked ancestors and 192 descendants; `Michael Brown (when?)` bridges five and 267. These are actual unresolved identity/temporal annotations, not evidence that the paths should simply be discarded. Exact witnesses are in `hierarchy/extended_results.json`.

Core inventory: **143 mailbox-tagged UIDs cover 158 distinct mailbox names; 105 are hierarchy employees**. Some UIDs carry multiple mailbox names, including ordinary spelling/name variants as well as mixed identities. `affiliation` is not a replacement core definition: only 27 total entities/14 hierarchy employees say `Core`; among the 105 mailbox-tagged hierarchy records, 86 lack affiliation and five say `NonCore`. Using affiliation yields four core and 288 inter pairs. The current mailbox flag is a reproducible observable definition, but the historical core-ID list has not been recovered.

Mailbox tags are not independently adjudicated personal ownership: Skilling UID20805 carries `KING-J`, while mixed-name UID7016 carries `SKILLING-J` and `WILLIAMS-J` (`hierarchy/minimal_graph.json`, `results.json`). These unexpected assignments warrant review. Both UIDs already qualify as core under the implemented flag; this observation does not establish a numerical correction to the core counts.

Only `entities`, `emails` and `threads` collections are supplied; neither the collection metadata nor the documentation source archive contains an additional hierarchy pair table or original name-bearing charts. `emails` can validate message/recipient/core context and is needed for a closer network reconstruction; `threads` documents message links, not a separate organizational hierarchy. I did not independently reconstruct every thread. Nothing found justifies silently adding relations from those collections to force the published count.

The paper's Table 1 category counts sum to 13,723 despite its 13,724 total; §5 also uses 13,723, and its communicating-pair count differs between prose and Table 2. These small internal inconsistencies do not explain the 482/483-pair gap. The current category differences are +47 core, −803 inter, +274 non-core. A changed release is plausible, but not established; historical construction choices or source errors remain possible. [Primary paper, §§3–5](https://aclanthology.org/P12-2032.pdf).

## 3. Findings by severity

### Critical C1 — Gold-to-person mapping assigns labels to the wrong human; some gold UIDs contain multiple humans' positions

**Source:** `gold_standard.py:55–60,83–102`; downstream scoring `evaluate.py:175–176`. Release documentation `_sources/Enron.txt:76–79` itself warns about executive/assistant coreference merges. That warning was tested, not accepted as sufficient evidence.

**Commands/evidence:**

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/matching/audit_matching.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/matching/detail_checks.py"
```

`matching/employees.jsonl` contains every candidate and chosen key. `sample60_review.md` records all 60 seeded reviews (`random_state=20260925`), before targeted additions; `review.jsonl` adds 46 targeted records. Current message bodies, metadata and position nodes are separately corroborated in `corroboration.txt` and `targeted_current_bodies.json`.

Confirmed assistant errors and a separately corroborated initial/position conflict:

| Gold ID / position | Chosen node | Evidence |
|---|---|---|
| 2937, Phillip Allen, sole `Trader, Lead` node `pz5Yyg10v9f`, Allen mailbox | `ina rangel` | `maildir/allen-p/sent/226.` says “My assistant is Ina Rangel.” `sent/25.` lists Allen as VP and Rangel as Assistant. |
| 2273, John Lavorato, sole COO node `b6vaRQijtA6`, Lavorato mailboxes | `angela mcculloch` | `tycholiz-b/deleted_items/99.` identifies Angela as an assistant; `jones-t/notes_inbox/127.` distinguishes Angela from John. The gold position is COO, not an assistant position. |
| 1277, Mark Palmer, five public-relations occupational-code nodes | `mark s palmer` | Gold names include Mark A; `kaminski-v/all_documents/1661.` has Mark S distinguishing mail intended for Mark A. Mark A uses CN=MPALMER and PR work; Mark S uses CN=MPALMER3/ENW. The modal match conflicts with the PR evidence. Ownership of every position in this six-position UID is not independently established. |

Correcting only the two assistant assignments, with unchanged pair set and graph, changes degree **80.5113→82.3541%** and PageRank **81.4704→83.6077%**. This is a benchmark-sensitivity demonstration, not a claim that the rest is now correct.

The problem is deeper for some UIDs. Sally Beck UID46153 owns both Managing Director `cZ82Q5upFH7` and Sr Administrative Assistant `diA_bfyZFk9`; the former supervises the latter, yet they are merged as one employee. Steven Kean UID18327 similarly owns Executive VP `lg-qNr0SCLL` and Exec Assistant `eVcd0xlkFEO`. Michael McConnell UID18533 owns President/CEO and Executive Assistant nodes. Selecting the executive's graph key cannot repair a hierarchy that already merged the executive's and assistant's positions. The position nodes lack independent person-name fields needed to disentangle them locally.

There are **39 gold employees with multiple resolved person-key candidates**, touching **5,416 pairs**, including **446/487 core pairs**. This does **not** mean 39 proven distinct-human errors; some candidates are aliases of one human. Conversely, a single candidate does not certify correctness: Mark Palmer and several merged records expose only one resolvable component. The seeded sample independently encounters Thomas Martin/Martin Lin, Fletcher Sturm/Casey Evans and Hunter Shively/Geoff Storey conflations. It is not defensible to report a match-precision percentage from unauthenticated recipient-only aliases.

**Impact:** The evaluation can compare one person's network score with another person's organizational label. Core evaluation is especially exposed. Error propagation also affects hierarchy construction before matching.

**Concrete fix:** Export and freeze an adjudicated position→human→graph-key crosswalk, with all aliases, ambiguity status and evidence. Repair the two confirmed assistant errors and Palmer's underlying graph attribution. Obtain original charts/author clarification for merged position owners; unresolved UIDs must remain uncertain, not be silently assigned one favored person. Report a prespecified unambiguous subset and full-set sensitivity, including its changed population. Do not choose remappings by the accuracy they produce.

Negative checks: Dana/Mark Dana Davis5075 already selects the larger `dana davis` graph fragment; the underlying split remains, but this is not the earlier title-join mistake. Michael Anderson8466 is corroborated by `kaminski-v/all_documents/4064.`, which discusses Azurix analysis and is signed Michael Anderson, agreeing with its sole Azurix gold position. I did **not** establish a wrong Anderson match.

### Major M1 — Coverage is overstated, and zero-filling turns unresolved identity into a low-rank prediction

**Source:** `gold_standard.py:95–102,129–131`; `evaluate.py:175–176`.

**Command:**

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/matching/absent_probe.py"
```

Also see `matching/counts.json`, `detail_counts.json`, `absent65.jsonl`, `accuracy.csv`, `absent_accuracy.csv`.

Of 1,518 email-linked employees: **985 map to named-person keys; 499 to bare addresses, including 65 absent from the graph; 34 to null**. These are employee counts, not counts of distinct chosen keys. Selected role/list keys are **zero/zero**. Thus graph-present employee coverage is 1,419, not 1,484. Actual both-present pair coverage is 11,605, not 12,937. The 65 false-presence cases touch 1,348 pairs. Fifty-nine have at least one graph key suggested by a release name; those are candidates, not 59 adjudicated identities.

Lou Pai896 is consequential. Its release supplies only synthetic internal alias `29bd17ed-b5df4365-862564c2-52a939@enron.com` and an external address. The chosen synthetic key is absent. The current graph contains **`lou.pai@enron.com`, degree 41**. Substituting that literal-name node alone changes degree **80.5113→82.8525%** and PageRank **81.4704→83.7097%**. It is still a sparse recipient-only fragment, not a complete repaired Lou Pai network. The current missing-score convention gives Lou only 2.62% accuracy on his 745 dominant pairs.

The convention means **missing score = 0**, not missing pair = incorrect. A known dominant can receive full credit against an unmapped subordinate; two unmapped endpoints get half credit. It is not conservative in a uniform direction.

| Evaluation population | Pairs | Degree | PageRank | Betweenness |
|---|---:|---:|---:|---:|
| Current, missing scores zero | 13,241 | 80.5113% | 81.4704% | 75.6476% |
| Both non-null keys | 12,937 | 80.3973% | 81.3790% | 75.5237% |
| Both graph-present | 11,605 | 84.9461% | 86.0405% | 78.0267% |
| Both named graph persons | 7,790 | 84.2940% | 85.8665% | 77.7022% |
| Named persons, exclude 39 multiple-person-key cases | 3,990 | 83.7845% | 86.8170% | 68.2707% |
| Exclude those 39, otherwise retain current matches/zeros | 7,825 | 75.2332% | 76.6837% | 65.4760% |

These are different populations, not proof that exclusion improves a model.

**Impact:** Missingness affects scores and executive influence while being hidden behind a reassuring “matched” count. The historical paper does not establish the current cross-corpus zero-imputation policy.

**Concrete fix:** Separate verified person, unresolved address, ambiguous, absent graph key, and no candidate statuses. Assert actual graph membership. Report graph coverage and conditional accuracy beside any all-pair estimate; label zero-imputation as an explicit sensitivity. Review missing high-leverage identities before inference, and keep a prespecified abstention policy instead of treating a failed lookup as observed lack of importance.

### Major M2 — Alphabetical tie-breaking materially determines the reported results

**Source:** `gold_standard.py:86–101`, especially the claim that not reading measure values means selection cannot favor a measure.

**Evidence/command:** `matching/audit_matching.py` and `matching/detail_checks.py` above; `counterfactual_accuracy.csv` preserves all groups and measures. Address-order reversal changes **zero** selections, so this is not incidental input-order nondeterminism.

There are 82 final lexical ties: 22 among person keys and 60 among bare addresses. Reversing only the person ties changes degree **80.51→83.42%**, PageRank **81.47→84.44%**. Reversing only address ties gives degree **78.28%**. Reversing all 82 gives degree **81.19%** and PageRank **83.71%**. Thomas White113114 alone has equally ranked graph-present `thomas.white@enron.com` (degree 50) and `tom.white@enron.com` (degree 2); choosing the latter reduces overall degree to **78.2569%**.

The matcher does not read metric values or dominance directions. I found no intentional score-maximizing selection. Nevertheless, its arbitrary choices change metrics unequally; the docstring's implication of measurement neutrality is not supported. Presence-first instead of person-first changes zero current matches, so that hypothetical preference bug is not an observed cause here.

**Impact:** The evaluation is stable across reruns but unstable across equally ranked candidates under the implemented rule. Evidence can distinguish candidates even when the rule does not. Reproducibility is not identity validity.

**Concrete fix:** Resolve ties using independently adjudicated identity evidence, not spelling or accuracy. Where candidates are genuine aliases, merge their underlying graph identities and recompute measures rather than select one fragment. Where candidates are different humans, preserve ambiguity. Publish mapping-policy sensitivity and remove the “cannot favour” assertion.

### Major M3 — Position aggregation and post-closure cycle filtering leave an unresolved label-policy problem

**Source:** `gold_standard.py:55–79`; docstring lines 10–11. Evidence: `hierarchy/extended_results.json`, `cycle_attribution.json`, `policy_pairs.json`, `evaluation/hierarchy_policy_accuracy.csv`. Replay with the hierarchy commands in §2.

The position graph is a **DAG**. The only nontrivial employee SCC appears after merging positions: Greg Whalley27104 ↔ Mark Frevert76045. Exact paths:

- Frevert Chairman/CEO `fXGf9E6hCSM` → Whalley President/COO `aEY-ymu9hdS`, `supervises`.
- Whalley `aEY-ymu9hdS` → unit `iQkvCXyjeKj`, `manages` → Frevert Chairman of Board `lbAxrQpKngY`, `contains`.

Thus “cycle in the transcription” is an unverified causal explanation. Different positions or chart times, or UID conflation, are alternatives. Removing the mutual pair only after closure does not remove inferred paths through the contradictory component.

| Policy | Pairs | Degree | PageRank |
|---|---:|---:|---:|
| Current, remove final mutual pairs | 13,241 | 80.511% | 81.470% |
| Remove Whalley→Frevert immediate arc before closure | 12,664 | 79.742% | 80.745% |
| Remove reverse immediate arc | 13,185 | 80.429% | 81.392% |
| Remove both arcs | 12,606 | 79.657% | 80.664% |
| Position closure before employee mapping | 8,916 | 90.237% | 90.663% |

Important limit: 635 current pairs require at least one disputed immediate arc, but **625 already have a position-graph path**. Only ten are outside position-level closure. It would be false to call all 635 invalid cycle contamination. Likewise, the 4,325 pairs added by merging positions before closure are policy-dependent, not 4,325 proven false relations; 4,315 remain even after deleting both SCC arcs. Legitimate multiple roles can support employee-level transitivity. Confirmed executive/assistant mergers make an unqualified one-UID/one-human assumption untenable, however.

**Impact:** There is no validated explanation of the historical pair mismatch or of which cross-role/temporal paths are valid employee relations. The 90.24% sensitivity uses a different pair population on which these fixed scores perform better—not an improved model on the same task.

**Concrete fix:** Preserve path provenance, chart/time metadata if recoverable, and all position owners. Obtain the intended collapse/cycle policy from the authors or prespecify a defensible reconstructed benchmark. Handle uncertainty before closure or flag every dependent target, not just mutual endpoints. Report the alternative populations without selecting the one that improves accuracy.

### Major M4 — The 83.1% result is not a replication or a correctness test for the hierarchy

**Claim location:** introducing commit `48d200f`; adjacent benchmark framing in `gold_standard.py:13–15`. There is no committed script specifying the claimed raw-address calculation.

**Command:**

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/network_replication.py"
```

Evidence: `network/accuracy.csv`, `network/release_stats.json`, per-variant score JSONs, `network_replication.log`. The scratch script independently builds adjacency sets; it does not call production network or evaluation functions. All scores below use the reconstructed 13,241 pairs and half credit for ties.

The paper constructs a co-referenced person network with To/Cc/Bcc and no stated internal-domain restriction; it reports 279,844 messages, 93,421 nodes and 407,095 links. Degree normalization cannot affect ordering. Its overall/core/inter/non-core accuracies are 83.88/79.31/93.75/74.57%. [Primary paper, §§3–4](https://aclanthology.org/P12-2032.pdf).

My raw CMU reconstruction uses **86,538 address nodes and 331,029 undirected links**, selecting each gold employee's highest raw-alias degree. It gives **83.1017%** overall, **83.9836%** core, **92.8013%** inter, **75.3686%** non-core. Thus the numerical 83.1% is reproducible, but its node representation, graph, alias aggregation and target pairs differ from the published experiment.

Sensitivity to raw-mail choices, using the same max-alias rule:

| Input / recipient choice | Address nodes | Links | All | Core | Inter | Non-core |
|---|---:|---:|---:|---:|---:|---:|
| All CMU mail, To+Cc+Bcc | 86,538 | 331,029 | 83.102 | 83.984 | 92.801 | 75.369 |
| All CMU mail, To+Cc | 86,538 | 331,029 | 83.102 | 83.984 | 92.801 | 75.369 |
| All CMU mail, To only | 79,023 | 286,558 | 82.822 | 83.881 | 92.686 | 74.947 |
| Internal addresses at both endpoints | 21,932 | 209,240 | 83.415 | 88.706 | 92.881 | 75.565 |
| 1998–2002 window, before deduplication | 86,370 | 330,474 | 83.094 | 83.778 | 92.810 | 75.362 |
| Same window, current deduplication | 86,339 | 330,409 | 83.094 | 83.778 | 92.810 | 75.362 |
| Also remove probable shifted copies | 86,339 | 330,409 | 83.094 | 83.778 | 92.810 | 75.362 |

Bcc adds no distinct raw-CMU adjacency beyond To/Cc in this data. Deduplication changes some graph edges but not these aggregate accuracy results. External-address removal changes the estimand. The additional `cmu_analysis_toccbcc` row in the evidence is a text-analysis-filter sensitivity, **not** the production network's filtering rule.

On the all-mail raw-address graph, alternative per-employee aggregation gives 83.1017% maximum alias, 83.2112% union of raw neighbors, 83.1433% sum, 80.6359% most-sent alias, 79.4804% average over all listed aliases, 71.4523% canonical release address. These are diagnostic choices, not equally good identity methods. Summing or unioning only a focal person's raw aliases does not merge their correspondents' aliases; neither reconstructs a person graph. I do not use the script's conditional-coverage column for canonical/most-sent policies, because availability of some alias is not availability of the particular selected alias.

The supplied release independently contains **276,279 email documents**, including **10,587 reconstructed/bubble records**, and **94,272 emailer UIDs**. Those are already different populations from the paper. A direct `from → recipients` UID graph gives **91,692 incident-node UIDs / 348,652 non-self links** and **83.9136%**, split **82.1355 / 92.8102 / 76.9976%**. Using `sender` where present instead gives 83.7097%; To-only gives 83.4982%; retaining only UID entities with internal addresses gives 84.2610%. Entity-universe size and incident-node size are distinct; isolated/self-only identities do not establish a historical node-count reconstruction.

An additional independent stream verifies that **Bcc is not omitted**: all 2,417 header-Bcc entries (2,415 distinct UID/message occurrences) are already in To∪Cc. Explicitly adding Bcc, or all header To/Cc/Bcc UIDs, changes no edge. There are 91,681 positive non-self-degree UIDs plus 11 self-only UIDs; the full 94,272-UID universe includes 2,591 with zero non-self degree. The graph's non-self weights sum to 1,565,994 email-edge incidences; degree uses distinct neighbors, not these weight magnitudes.

All **10,587 bubble records lack a usable `from`, sender or header-from UID and lack recipient UIDs**. The other 2,105 missing-from messages also have no sender/header-from fallback. The tested header-based source fallbacks therefore restore no edges. This does not establish that every possible thread/text reconstruction would fail; such a reconstruction was not performed. There are 2,425 distinct UID self-loops; retaining them with the standard undirected degree contribution of two gives **83.8683%** overall, **82.1355% core, 92.8013% inter, 76.9204% non-core**. It still does not reproduce the historical benchmark.

Exact verification command and outputs:

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/release_bcc_verification.py"
```

See `evaluation/release_bcc_stats.json`, `release_bcc_accuracy.csv`, and `release_bcc_verification.log`. Neither a near-83.88 score nor a particular header convention identifies the original pair list.

**Impact:** A nearby scalar accuracy cannot verify pair identities, directions, person matching or historical equivalence. It can occur despite the concrete wrong-person assignments and different graph populations demonstrated here.

**Concrete fix:** Commit a reproducible benchmark script with pinned release artifacts, exact sender/recipient/bubble rules, alias/person mapping, tie policy and coverage. Call the existing result a **raw-address max-alias sensitivity**. Call the release-UID result a **release-derived reconstruction**, not an exact replication. Obtain the original pair list, graph recipe and core IDs before claiming reproduction of Table 1.

### Major M5 — The intervals are computationally reproducible, but the scientific estimand and collection effects need explicit limits

**Source:** `evaluate.py:166–186`; `gold_standard.py:60,119–122`. Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/audit.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/quickdiagnostics.py"
```

Evidence: `independent_oracle.csv`, `executive_influence.csv`, `per_dominant_accuracy.csv`, `bootstrap_sensitivity.csv`, `gold_pagerank_minus_degree.csv`, `collection_baselines.csv`.

**No arithmetic defect found:** hand/scalar cases include strict wins, losses, exact/near ties, absent endpoints, two absent endpoints, and different gold IDs sharing a graph key. The independent small oracle explicitly enumerates ordered pairs of sampled employee copies; the full oracle materializes repeated pair rows. Both agree with endpoint multiplicity weights `c[i] * c[j]`. The current graph-key collision involves two Richard/Rick Johnson gold IDs, touches 13 pairs and includes no direct pair between those two IDs. It remains an identity question, not evidence of a bootstrap multiplication error.

There are 1,518 endpoint IDs but only 298 distinct dominants. Lay and Skilling contribute 2,889 pairs, **21.82%**; the top ten contribute **67.56%**. Removing Lay/Skilling pairs changes degree from 80.51 to 75.09%; removing Lou Pai alone raises it to 85.15%. Lou's bootstrap multiplicity correlates −0.708 with accuracy; mean draw accuracy is 84.98% when omitted, 80.06% with one copy, 75.36% with two. This explains much of the broad interval, especially given his failed mapping.

| Diagnostic | Degree estimate | Percentile interval |
|---|---:|---:|
| Implemented endpoint bootstrap | 80.51% | 66.73–90.50% |
| Dominant-cluster resampling sensitivity | 80.51% | 67.09–90.50% |
| Equal-dominant macro average/bootstrap | 72.60% | 68.29–76.49% |
| IID pair bootstrap, inappropriate comparator | 80.51% | 79.85–81.20% |

The first two widths are consistent with executive influence. The narrower IID-pair interval is not a better answer. The macro row changes the target population/weighting. One weak hierarchy component contains **99.43% of pairs**, so there is no demonstrated collection of independent, comparable hierarchy clusters supporting a simple department bootstrap. No audit calculation establishes frequentist coverage for this single dependent hierarchy; the supplied intervals also omit mapping, label and graph-construction uncertainty.

The overall paired PageRank−degree difference is **+0.959 percentage points**, interval **−0.792 to +3.285** under the existing endpoint procedure. That procedure does not establish an overall PageRank advantage. Core is different: −9.343 points, interval −17.417 to −2.629.

Collection diagnostics are substantial. A score consisting only of `bool(mailboxes)` obtains **67.28% overall, 90.63% on inter pairs**, with 5,105 wins and 528 losses there. That inter score exceeds every communication measure in the current table. Mailbox count obtains 67.80% overall. Pure graph-node presence gives only 49.88% overall, so simple observed/missing status alone does not explain the 80% headline. These checks demonstrate the importance of collection strata; they do not establish a causal decomposition.

**Impact:** Transitive-pair micro accuracy is heavily executive-weighted and partly aligned with corpus selection. It is not a population-wide estimate of employee functional importance. Formal hierarchy is the target being predicted here, not an independently measured functional-importance construct.

**Concrete fix:** State the exact conditional estimand and bootstrap assumptions; report per-dominant, core/inter/non-core, collection-only and leave-executive-out diagnostics, plus paired differences. Address mapping failures before interpreting intervals. For Phase 3, evaluate incremental signal over collection/network controls and do not present random pair splits sharing people/hierarchy paths as independent generalization.

### Major M6 — The gold tests miss consequential implementation failures

**Source:** `tests/test_gold_standard.py:6–52`; `tests/test_evaluate.py:78–88`.

Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" -m pytest -q -p no:cacheprovider tests/test_gold_standard.py tests/test_evaluate.py
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/hierarchy/mutate_fixtures.py"
PYTHONDONTWRITEBYTECODE=1 "$TASK_PY" "$TASK_EVIDENCE/evaluation/audit.py"
```

Mutations are in-memory/scratch only. Original tests: **14 pass**. The four hierarchy/matching fixtures reject reversed edges, missing traversal/closure, early no-email removal and retained mutual pairs. But they all still pass when **top-level incident edges are ignored**—a real-data loss of **4,633 pairs**—or when ownership uses only an employee's first position.

All ten existing evaluation tests also pass eight deliberately wrong gold implementations: hardcoded `[0,1]` CIs; endpoint-presence rather than multiplicity weights; dominant-only weights; subordinate-only weights; IID pair-row bootstrap; graph-key rather than gold-ID sampling; exact-only ties; ignored seed. The gold fixture checks a point estimate, one tie, a count and a CI containing the estimate, not an exact seeded resampling result.

This does not mean those mutations exist in production; the independent oracle found the actual arithmetic correct. It means the suite cannot certify it or protect it from these regressions.

**Impact:** Test passage leaves precisely the multi-position, real-identity and uncertainty errors important to this benchmark uncovered.

**Concrete fix:** Add top-level-only edge fixtures, multiple positions, incoming/outgoing cycle paths, mixed-human and missing-present-key joins, same-graph-key/different-gold-ID cases, explicit sampled-copy bootstrap expectations, seed/near-tie assertions and an independently specified real-release inventory. Include failure fixtures derived from the corroborated assistant cases without publishing private release content unnecessarily.

### Minor m1 — Empty pair-type groups crash rather than producing a defined result

**Source:** `evaluate.py:177–184`. `evaluation/audit.py` reproduces `IndexError: index -1 is out of bounds for axis 0 with size 0` for valid subsets lacking one group, empty input, and zero bootstrap replicates. All current groups are nonempty and all 1,000 draws survive, so this does not invalidate the stored table.

**Impact/fix:** Sensitivity or adjudicated subsets can crash. Specify skip/NaN behavior for absent groups, validate positive replicates and report retained replicate counts. The small oracle shows valid employee resamples with no eligible subgroup pair being discarded for that subgroup's interval; expose that conditioning instead of hiding it.

### Minor m2 — Documentation and provenance claims are incomplete or stronger than the evidence

Exact review commands: `git show --no-patch --format=fuller 48d200f`; `git show e476f688c323b7b6ad06b86f93f5e2737b40cbac:src/enron_importance/gold_standard.py`; `rg -n 'gold|Agarwal' README.md config.yaml src/enron_importance/evaluate.py Makefile`.

| Location | Finding |
|---|---|
| `gold_standard.py:3–9` | Local BSON, three relation types, employee closure and 1,518 endpoints verified. The detailed unit traversal is supported by release documentation, not explicitly described in the paper. |
| `gold_standard.py:10–11` | “Cycle in the transcription” assigns an unverified cause; actual position graph is acyclic. |
| `gold_standard.py:13–15` | Related/not-identical warning is necessary, but “slightly fewer” omits changed composition, immediate-count discrepancy and identity uncertainty. |
| `gold_standard.py:89–90` | No score value is read: verified. Therefore no measure can be favored: overclaim; demonstrated policy sensitivity. |
| `gold_standard.py:130–131` | Graph-match wording counts non-null strings, not graph membership. |
| `config.yaml:128–134` | Path/hash match and entities-only hierarchy construction are verified. Private sender/date provenance is not authenticated by the hash. |
| `evaluate.py:14–18,160–186` | Half-credit, bootstrap and stored scores reproduce. Missingness is zero **score**, not automatically zero pair credit. The paper does not explicitly establish this half-credit/relative-tolerance tie convention; “as in Table 1” should distinguish it. |
| `README.md:108–111` | Still says evaluation will be added if authors share the hierarchy; stale at this commit. |
| `48d200f` message | 1,518/13,241 and rounded degree/PageRank numbers reproduce. “Paper's way” and “checks the pairs were read correctly” are unsupported by the reproduced raw-address calculation. |
| `Makefile:33–35` | Comment says “if” the release is present, but target unconditionally runs the stage, which exits if the private source is missing. External reproduction requires access instructions, not an apparently optional prerequisite. |

**Impact/fix:** Update the Methods, status and release-access instructions. Preserve a reproducible script/manifest for every reported comparison. A local checksum freezes supplied bytes; it does not certify authorship or equivalence to a historical release.

## 4. Leakage and circularity checks

Command: `rg -n 'gold_standard|gold_pairs|gold_employees|agarwal|Agarwal|position_nodes' src tests config.yaml README.md Makefile`, plus direct reading of `identity.py:240–249`, `network.py:118–127`, and the complete gold module.

I found **no direct gold-hierarchy input to identity resolution, filtering or communication centralities**. Gold matching consumes the graph afterward and checks node presence; it does not feed hierarchy edges or ranks back into network construction. No score magnitudes or pair directions enter the current match decision. Using held-out-label identities to join a fixed unsupervised graph is not inherently target leakage.

However, the release's identity mappings originate partly from the same email headers/mailboxes. They are not an independent gold standard for human identity, and they demonstrably contain mixed people. Graph-aware candidate selection is an observation-dependent evaluation join. Its uncertainty must not be concealed as independent truth.

Before any Phase 3 result:

- Freeze an adjudicated crosswalk independently of model scores; separate ambiguous/no-evidence cases and preserve pair-path provenance.
- Split by actual people/alias groups, not just messages or dominance-pair rows. Account for shared ancestors and overlapping subordinate groups; report which overlap remains.
- Do not supply gold titles, chart positions, core labels or gold-derived alias/name decisions as NLP predictive features. Compare models with and without signature/title/name tokens, mailbox/custodian identifiers and address-format artifacts.
- Compare text models against collection-only baselines and the same network baselines on identical covered pairs. Report core, inter, non-core and macro-person results.
- Establish separate evidence for functional importance; disagreement with a formal hierarchy is not itself validation of that construct.

## 5. What remains unverified

1. **The exact 2012 target and graph.** No supplied artifact establishes which historical pairs, core IDs or network-generation options produced the publication. Tested alternatives do not reproduce the immediate/category totals. A later release is plausible, not proven.
2. **Full identity truth.** The seeded 60 plus 46 targeted reviews do not adjudicate all 1,518 employees. Many recipient-only aliases remain unverified. Candidate-name diagnostics are not confirmed corrections. Original charts are needed for mixed position owners.
3. **True organizational chronology.** Available position nodes do not establish when each relation held or whether cross-chart roles can be composed. Ambiguity cannot be repaired by selecting a favorable closure policy.
4. **Private delivery authenticity.** The files, schema, release notes and documentation are internally consistent; I did not authenticate the private author-to-user transfer or obtain an author-signed historical manifest.
5. **Inferential coverage/generalization.** Numerical reproduction proves the declared bootstrap distribution, not nominal 95% coverage under this dependent, selected hierarchy or robustness to labeling errors. There is no independent functional-importance gold standard here.
6. **Corrected end-to-end scores.** Remap/exclusion/policy tables deliberately keep the existing graph fixed. They are sensitivities, not results from rebuilding a corrected identity graph. Concurrent fixes were outside scope.
7. **All corpus acquisition/parsing and thread reconstruction.** Existing parsed CMU inputs were hash-pinned and queried; raw parsing, all prior data-layer stages, exact centralities and every thread were not rerun in this component audit.

### Questions for the release authors

- Can they provide the exact immediate/transitive pair files, core-ID list, source version and construction code for Table 1, reconciling 2,155 and 13,723/13,724 with this release?
- Were all positions sharing a UID merged before closure, and how were executive/assistant conflations, vacant nodes and different chart times handled?
- How was Whalley↔Frevert resolved, if at all?
- Which original mailbox/person mapping produced 440/6,436/6,847 pairs, versus the supplied 143 owner UIDs spanning 158 mailbox names?
- What exact sender, recipient/Bcc, reconstructed-message, alias-coreference, self-loop and tie rules produced the historical network and degree score?
- Can the original name-bearing charts or corrected position-to-person mappings be shared for the concrete mixed-UID examples?

### Evidence index

- `setup.py`, `initial_hashes.json`, `initial_git.json`, `check_integrity.py`, `final_hashes.json`, `integrity_result.json`: pinned-input and worktree verification.
- `pinned_project/`, `uv_sync.log`, `fresh_environment_tests.log`: isolated dependency/test reproduction.
- `reproduce_gold_stage.py`, `stage_run1/`, `stage_run2/`: complete redirected stage outputs and hashes.
- `hierarchy/`: independent BSON decoder, graph reconstruction, alternative policies, cycle witnesses, mutation results and detailed findings.
- `matching/`: exhaustive candidate enumeration, 60 seeded reviews, targeted message/position evidence, coverage and score sensitivities.
- `evaluation/`: separate-process reproduction, independent numerical oracle, mutation testing, executive/cluster diagnostics, paired differences, collection baselines and header/Bcc checks.
- `network_replication.py`, `network/`, `network_replication.log`: independent raw-address and release-UID network reconstructions.
- `documentation/`: extracted supplied documentation and independently fetched primary paper.

All fixes above are recommendations. None was implemented in the audited repository.
