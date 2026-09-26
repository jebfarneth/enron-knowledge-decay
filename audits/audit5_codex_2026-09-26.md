# Independent audit 5 — Enron data, evaluations and mention baseline

Audit date: 2026-09-26. Target: `7bd652b09ad85675fd1311c12f11f9d70f83f8f5` on `main`. The certified-data worktree is `62da63e703e41e3d43107567eb119d64992450e4`; the two source trees initially matched (`e5d9dda0c4c621302e3195288fa7f87a76fe7685`). The older processed data in the main checkout was not used as the current run.

Evidence directory: `/tmp/enron-audit5-20260926.RIaA4K` (hereafter `S`). It contains private-derived evidence and must **not** be committed or published. Paths below are relative to `S` unless identified as repository source paths. All reported source lines refer to the pinned commit. No production code, tests, configuration, data or Git history was edited.

## 1. Executive verdict

**Yes with conditions for exploratory Phase 3 development; no unconditional clearance for confirmatory text-model claims.** The data layer needs the input-provenance gaps closed and documented handling of residual signature/mention/reply errors. The title evaluation is usable as a noisy title proxy, not ground truth. The reconstructed gold evaluation is usable with its fixed population and strict/macro/custodian sensitivities, not as an exact replication or a functional-importance label. The mention baseline is usable as a disclosed exploratory comparator, but its referents and exclusions are not sufficiently validated to call it clean employee-discussion evidence. Independent calculations reproduce the numerical tables, including the primary gain's interval crossing zero; new samples still show wrong referents, genuine colleagues filtered out, substantive messages removed as signatures, and wrong/missed reply parents. Those empirical validity questions require blinded human labels, not just another passing test suite or another round of regex patches.

The relevant distinction is between reproducing the current arithmetic, validating inferred observations, and validating functional importance. These are separate tasks. A hierarchy benchmark can test hierarchy ordering; it does not establish that a mention, inferred reply, or employee-dependence interpretation is correct.

## Audit procedure and evidence conventions

- Used the audit history and responses already read in the preceding audit, checking unchanged bytes with `prior_document_continuity.json`; this is continuity of that reading, not a claim to have reread every older document this time. Reread the current response, README and affected implementations. Extracted the prior audit-4 scripts, labels and outputs into `prior_audit4/`; extracted regular files only and recorded skipped symlinks.
- Recorded initial source, raw-data, certified-data, results, figure, evidence-archive and paper hashes in `initial_*_hashes.json`, plus both Git states in `initial_git.json`. End checks find **all 141 prehashed files plus the separately hashed prior-run links unchanged**, with both Git HEADs and source trees unchanged. The **47 copied source/test/configuration files** also match their initial originals. `final_hash_check.json` and `replay_comparison.json` retain the checks; this report is the only new repository file and is uncommitted.
- Installed a separate environment with `uv sync --locked --group dev --project S/pinned_project`. Python **3.12.13**, **68 installed distributions**; `environment_fresh.json` and `environment_certified.json` agree exactly. No dependency installation was performed in either worktree.
- Ran the complete non-corpus test suite from the pinned scratch copy: **237 passed, 17 deselected**. Command/result: `test_run.txt`. Mutation tests use isolated scratch fixtures or in-memory module replacements; passing tests are not treated as evidence of empirical classifier accuracy.
- Completed every pipeline stage and the corpus checks in **57.1 minutes**: all exits zero, **35/35 declared outputs byte-identical** to the certified run, including tables and PDF/PNG figures, and `stale_reasons()` returns **`[]`**. `reproduce.py` redirects all generated outputs to `reproduction/`, reads raw files from the main checkout, and uses verified copies of the certified parsed table and NER tag cache. This is a cached replay, not a from-zero reparsing and retagging claim. Evidence: `reproduction/stages.json`, stage logs and `replay_comparison.json`.
- `numeric.py title` and `numeric.py gold` independently construct scalar pair credits and literal repeated-pair/person-bootstrap calculations without calling production scoring or interval functions. All **10 title rows, 10 title paired comparisons, 44 main gold rows, 352 gold sensitivity rows, 40 gold paired comparisons and 11 macro averages** match stored results within **5×10⁻¹¹**, their CSV rounding precision. Raw-address scoring is outside this independent oracle and is covered only by the production-stage replay.
- Fresh sample labels are **auditor judgments from corpus context, not a blinded human gold set**. Uncertain cases remain uncertain. Wilson intervals describe sampled rows in the stated frame; they are not intervals for accuracy on new organizations. Repeated recipients can produce several rows from one message. These samples do not establish whole-corpus recall, and previously disclosed/tuned examples are regression evidence, not held-out validation.

### Reproduction summary

| Claim / artifact family | Observed value | Assessment |
|---|---:|---|
| Parsed; in window; retained after dedupe | 517,401; 516,359; 254,110 | Current-data counts reproduced; cached replay recorded below. |
| Authored text; analysis; person text | 234,295; 168,377; 165,300 | Match. Analysis has 6,326 sender addresses; person-text has 5,508 person keys. |
| Automated; structured/newsletter; signature-only; long routine; probable copies | 9,429; 6,763; 1,161; 3,313; 1,531 | Match. Flags overlap; these are not disjoint subtraction counts. |
| Identity addresses / non-null keys | 6,455 / 5,871 | Match: 5,596 person, 145 role, 127 bare-address, two list, one ambiguous; four placeholder addresses separately. |
| Network nodes / directed edges | 20,755 / 219,345 | Match: nodes are 5,563 person, 140 role, 305 list, two ambiguous, 14,745 address. Edge and centrality files are byte-identical in the scratch rerun. |
| Links / replies / forwards / high confidence of all kinds | 34,749 / 26,889 / 7,860 / 26,442 | Match. High-confidence **replies alone**: 19,068. Threads: 219,361. |
| First-audit reply regression | 24/27 old direct replies retain same-parent reply; 24/28 retained same-parent reply-kind links supported | Match, with the documented old-label/tuning limitation. |
| Resolved mention rows / unexcluded / contributing | 985,038 / 649,922 / 596,542 | Match; final difference removes recipient-self edges. |
| Cc all / singleton / ambiguous | 70.74% / 84.71% / 60.36% | Match, denominators 19,037 / 8,111 / 10,926. Not independent resolution accuracy. |
| Title-proxy people / pairs | 129 / 6,235 | Match. All ten scores and intervals independently reproduced. |
| Title degree / mention degree / primary mentioned-to | 66.5838% / 73.3440% / 69.3986% | Match. Mention-degree gain +6.7602 [2.9159,11.1294] points; primary gain +2.8148 [-0.9937,6.7854]. |
| Gold main / strict populations | 7,338 / 4,939 pairs | Match; broader reconstruction 13,241. |
| Gold degree / primary mentioned-to | 89.5544% / 91.2783% | Match. Paired +1.7239 [-0.4194,4.9129] points. |
| Gold unfiltered mentioned-to / third-party mentioned-to | 92.2049% / 92.2527% | Match. Paired +2.6506 [0.7366,5.4158] and +2.6983 [0.5996,5.8919] points. |
| Primary sensitivity gain range | +0.3027 to +3.7215 points | Match; these are point estimates, not claims all intervals exclude zero. |
| Raw-address degree diagnostic, all 13,241 pairs | 83.0942% | Matches 83.1% after rounding; reproduced by the production-stage replay, not a separate raw-address implementation in this audit. |
| Cleaning check, n=5,000 | Agreement 77.22%; empty output 7.38% versus 3.54% | Match stored check; neither comparison parser is gold truth. Marker rates 0.08/2.00%, 0.04/5.98%, 0.96/7.82% reproduce at displayed precision. |
| Non-corpus tests / post-rerun corpus checks | 237 / 17 pass | Reproduced in fresh locked environment; the 17 checks ran against the newly rebuilt scratch data, with no skips. |
| Exact intermediate 1,190-link recovery; five changes in author's 20,000-body sample | Not independently obtained | Do not treat these two historical effects as verified. |

Numbers are supported by `documentation_check.py/json`, `text/counts.json`, `mentions/sample_frames_corrected.json`, `numeric/{title,gold}_comparison.json`, the retained exact tables and the cached replay comparison. `numeric/gold_tables.csv` contains subgroup/custodian and alternative-population results; the 352 sensitivity-row comparison excludes the separate raw-address diagnostic, whose reproduction is a production replay rather than an independent implementation in audit 5.

## 2. Verification of every audit-4 response row

| Audit-4 finding | Claimed status | Verified status | Reproduced effect / original probe / evidence |
|---|---|---|---|
| M1 downstream freshness | Fixed | **Substantially fixed for declared outputs; incomplete for inputs.** | All 35 output corruptions, 13 missing stages, blank inventories, wrong ordering and obsolete gold artifacts rejected. Actual skipped gold/goldeval removes three processed and four result files. External-label, lock and tag-cache changes still pass the full gate; see new M1. `provenance/attack.py`, `provenance/replay_tiny.py`, `provenance/attacks.json`, `provenance/certified_check.json`. |
| M2 mention validity | Partly fixed | **Partly fixed is accurate; remains open.** | All 17 prior self-reference cases removed; office example fixed. 985,038 rows partition as 318,914 self + 8,403 non-person + 6,024 office + 1,775 company + 649,922 unexcluded; zero abbreviation exclusions. Prior Williams/Davis/Ste/quote examples partly remain. New 300-row samples and numerical oracles above/below. `mentions/old60_replay.json`, labels, `numeric/`. |
| M3 signature/newsletter exclusions | Fixed for demonstrated cases | **Signature examples fixed; newsletter claim only partly fixed; broader precision open.** | “Not I.” and Zufferli ranking retained; Cordially-only signature excluded. Counts 1,366→1,161 signatures and 8,639→6,763 structured/newsletters reproduce. One of two original conversational-newsletter examples still flagged. Fresh marginal signature sample: three definite false exclusions in 60. `text/known_cases.json`, `text/old_fixture_replay.json`, labels; `documentation_check.json`. |
| M4 thread parents/relays | Fixed for demonstrated cases | **Named false-link examples repaired; remaining counterexamples and validation open.** | Lavorato/Kitchen/Kaminski named wrong links removed; author-over-ancestor tiny control repaired, angle-quote inversion not repaired. 37,493→34,749 links; 26,889 replies/7,860 forwards; 26,442 high-confidence links of all kinds. Original 24/28=85.7% regression reproduces. Fresh samples expose lost true replies and wrong parents. Exact 1,190 counterfactual recovery count unverified. `text/old_thread_fixture_replay.json`, `text/counts.json`, retention files, fresh labels. |
| M5 Phillips recipient repair | Fixed, with coverage limitation | **Demonstrated duplicate cases fixed; stated conservative limitation remains.** | All 14 old raw-confirmed Phillips/Hughes network cases repaired. Forney `sent_items/96.` now nine targets at 1/9, not ten at 1/10. Across 82 copy groups/141 extra-address entries (88 distinct addresses), 28 person assignments accepted, 24 in 21 eligible network groups. Same-surname genuine-extra exclusion remains a demonstrated synthetic limitation, not a newly quantified corpus error. `provenance/recipient_check.py/json`, `provenance/recipient_extras.json`. |
| M6 wrapped headers | Fixed, fresh span validation open | **Named case fixed; broad guarantee not established.** | Jones `notes_inbox/964.` retains a 143-character response/signature beginning “I know nothing!” rather than the quoted message. Fresh 3,000 old/new comparison: one changed correct cut. Quoted-person sample 60: no observed substantive false cut, one residual header. Original five-of-20,000 count not verified; constructed prose boundary still fails. `text/cleaner_fresh3000_changes.json`, `text/controls.json`, labels. |
| Minor 1 name compatibility | Fixed | **Demonstrated cases fixed.** | Hyphenated keys, Mark A/E initials, Ed versus E.D. and per-recipient choice reproduce in `mentions/fixtures.py/json`; not proof all real identities are correct. |
| Minor 2 endogenous Cc check | Reported as such | **Disclosure fixed; independent validation still open.** | 13,466/19,037=70.74%; singleton 6,871/8,111=84.71%; ambiguous 6,595/10,926=60.36%. A tiny graph changes resolution when the same Cc edge is added. README explicitly calls it consistency, not independent accuracy. `mentions/fixtures.json`, replay `mention_resolution.json`. |
| Minor 3 tag cache | Fixed | **Metadata-based invalidation fixed; broader integrity remains incomplete.** | Current digest contains model/spaCy versions, components, cap and tagging code. Old-format/changed-text/component/cap checks work. Retained-key, corrupt-payload cache is reused; model weights are not hashed. `mentions/fixtures.py/json`; new M1. |
| Minor 4 secondary dedupe chain | Fixed | **Demonstrated chain fixed.** | Original reverse-chain maps B and C to live A and retains C's recipient, in the tested input orders. Existing disjoint-send/recipient-bridge controls also run. `provenance/replay_tiny.py`, mutation logs. |
| Minor 5 surviving mutants | Fixed | **Substantially improved, not completely closed.** | All 32 historical gold/identity/dedupe, five prepare/provenance and nine text probes caught; 11/13 mention probes caught, with one apparently equivalent survivor under tested canonical-key normalization and one unpinned cap. New meaningful cache, text and paired-bootstrap mutants survive; detailed inventory below. |
| Minor 6 disclosure | Fixed | **README substantially improved; several categorical descriptions still too strong.** | Adaptation, 5,000-character cap, estimated authorship, Cc dependence and weaker primary result disclosed. Source still guarantees no quoted re-counting; self exclusions are not exclusively signatures, and first recognized author is not necessarily first actual author. Documentation section below. |
| Minor 7 last-edit freshness | Fixed | **Supplied current source/config/output snapshot verified; general input certification remains conditional.** | Certified worktree and fresh scratch run return empty stale reasons and have package hash `a40ae88938179f463b767124dc7b5df5e3baba94fe128162559a454d972eee30`; all 35 declared outputs match byte-for-byte and all 17 post-rerun corpus checks pass. Missing-manifest/nonempty-corpus and damaged-centrality test fixtures fail rather than skip. See `provenance/certified_check.json`, `replay_comparison.json` and end hashes. |

## 3. Findings

### Critical

No new critical finding established. This is not a certification of construct validity or all unseen records.

### Major M1 — The manifest protects declared outputs, but omits consequential inputs

**Evidence.** `provenance/attack.py` constructs a complete 13-stage run and attacks it. Every one of **35 declared-output corruptions**, all **13 missing-stage cases**, blank output inventories, missing manifests, upstream-only reruns and damaged upstream outputs followed by a later-stage rerun are detected by the full gate. The supplied certified manifest itself returns `[]`; this audit does **not** allege that supplied outputs are stale.

However, `provenance.py:29–53,60–66,99–102` records package-source/configuration hashes and generated outputs, not all stage inputs. `validate_threads.py:26,42` reads `audits/labels/thread_links_sample60.json`, which is outside that inventory. In a real `validate_threads.main()` fixture, changing its annotation from `direct_reply` to `wrong_parent` leaves the complete `stale_reasons()` equal to **`[]`**. Rerunning that stage changes the supported-reply fraction **1/1 → 0/1**, and the resulting full manifest also passes. See `provenance/attacks.json`, keys `changed_labels_before_recheck` and `real_threadcheck_label_effect`.

Changing the isolated project's **`uv.lock`** also leaves the full gate empty. The parsed-cache stamp does check Python and lock identity when prepare is run (`prepare.py:39–52`); that does not make a previously generated stage manifest current after those inputs change. These are separate checks.

`mention_tags.parquet` is an undeclared input/output cache (`mentions.py:200–229,341`). Its corruption likewise leaves the full gate empty. `mentions/fixtures.py` additionally demonstrates consequential cache reuse: keep a valid text key and tagger ID, replace the payload with `FORGED PERSON` at offset **999999**, and `cached_mentions()` accepts it with **zero NLP calls**. Neither payload integrity nor span bounds are checked. This is a controlled counterexample, not an allegation of corruption in the supplied cache. Raw archive/BSON/spreadsheet bytes are verified by individual stages but not rechecked by `stale_reasons`; model payload and external annotations are likewise outside the certificate.

**Impact.** The gate now verifies declared output integrity and ordering, but cannot certify a current complete computation across changing annotations, dependencies and cache inputs. The original missing-output defect is repaired; the broader provenance claim remains conditional.

**Fix.** Declare external annotations, raw inputs, runtime/lock/model identity and read/write caches; store/check their hashes alongside upstream artifact identities. Validate cached entity spans against the text and checksum cache payloads. Add a regression exercising a real changed label input and a retained-key/changed-payload cache, not only corrupted declared outputs.

### Major M2 — Filtered mention rows still contain wrong referents, and the company filter deletes genuine colleagues

**Fresh samples.** `mentions/extract.py` uses new seeds **2026092651–2026092655**, with labels/rationales in `mentions/kept_labels_private.json` and `mentions/excluded_labels_private.json`. The main contributing frame correctly excludes recipient=referent rows as well as all filter reasons: **596,542 rows**, not the intermediate 649,922 unexcluded rows.

| Sample frame | Sample / distinct messages | Auditor result and descriptive 95% Wilson interval |
|---|---:|---|
| Main contributing rows | 60 / 59 | **43 supported, 11 wrong, six uncertain**. Supported fraction 71.7% [59.2,81.5]; unknown-label range 71.7–81.7%. Definite wrong fraction 18.3% [10.6,29.9]. |
| Company exclusions | 60 / 24 | **27 marginal false exclusions**, 45.0% [33.1,57.5]. Those 27 rows come from ten messages. Another 25 would independently be removed as sender-self, one as recipient-self, and seven have wrong referents. |
| Office exclusions | 60 / 45 | 0 observed false exclusions; upper Wilson bound 6.0%. Sampled rows describe public figures wrongly resolved to Enron namesakes. |
| Self exclusions | 60 / 60 | All 60 referents match the sender: 47 signatures, nine contact instructions, three mixed contexts and **one roster**. They comply with a sender-excluded policy, but are not all noise or signatures. |
| Non-person-text exclusions | 60 / 29 | 53 supported referents, six wrong and one uncertain; exclusions follow sender-type policy, not referent validity. Signed human prose can originate from shared mailboxes. |
| Abbreviation exclusions | 0 / 0 | Empty resolved-row frame; no rate can be estimated. See failed original counterexample below. |

These are 300 reviewed rows, with reason precedence respected when assessing marginal exclusions. The Wilson intervals are row-level and are not adjusted for message or recipient clusters; the company sample especially has repeated rows from the same messages. These row rates weight broadcast messages by their resolved recipient rows and are not unique-edge precision estimates. Do not report 43/54 determinate cases as overall precision. Nor does comparison with audit 4's differently mixed/unfiltered sample estimate the causal effect of filtering. Current wrong examples include Williams→John Williams, Edison→Andrew Edison, Gray Davis→Dana Davis, a gas-location mention Katy→Katy Lomax, and a letter to `fdiebold@sas.upenn.edu` resolving Frank to Frank Hayden. Exact corpus identifiers and contextual rationales are in the labels. Correctly resolved rows also include **12 roster/table entries, four other-author signatures and one quoted header**; referent correctness is different from authorship.

**New false-exclusion mechanism.** `mentions.py:79–82,132–146` treats a following bare `&`, `power`, `gas`, `capital`, `bank`, etc. as evidence of a company. Its `^\s*` crosses newlines and tabs. This excludes colleague names followed by a department, heading or conjunction, not just company names. Fresh examples include a name followed by `Power Group`, another followed by `Gas Group`, a name before a new paragraph headed `Capital Calls`, and `email Sally & let her know`. Exact message paths, offsets and labels are in `mentions/samples_corrected_private.json` and the label file; no private-release records are needed for these examples.

The reviewed marginal false-exclusion cohort comprises **554 resolved rows from 10 messages**. Restoring only those reviewed message/person combinations adds **456 distinct directed mention edges affecting 299 recipients**, but leaves the main gold `mentioned_to` point estimate unchanged. Evidence: `mentions/extract.py`, `mentions/company_confirmed_cohort_private.json`, `mentions/company_cohort_impact.json`. This is demonstrated loss of input evidence; it is **not** evidence that fixing these cases will improve the headline result.

**Original counterexamples not all fixed.** The archived 60-row probe was replayed by message/mention/recipient/person in `mentions/old60_replay.json`. All 17 previously labelled sender-self cases are now excluded. The explicitly titled Governor Davis case M32 is excluded (five matching rows), but all six matching Williams-company M11 rows and all 11 Davis M35 rows remain; M16 filters only one of 13 matching Davis rows. Old quoted-header cases M18/M20/M26/M31 survive. Repeated equal spans preclude a fabricated one-to-one old-row ordinal mapping, so the replay reports every matching tuple. The abbreviation gate requires the period inside the recognized entity (`mentions.py:83,137`). The old `Ste. Aurelie Timberlands` counterexample (`kitchen-l/_americas/legal/7.`) has a spaCy entity of **`Ste`**, without the period, so the `Ste → Clemens Ste` link survives. No resolved row in this run receives the abbreviation exclusion reason. `mentions/ste_boundary.py` reproduces this actual span; a fixture including the period is not a test of it.

**Impact.** The primary measure is reproducible but remains an operational graph statistic containing misresolved organizations, public figures, quotations and contact material. The new context blacklist creates its own role/department-dependent missingness. A higher hierarchy score would not repair that measurement defect.

**Fix.** Evaluate mention detection and referent resolution separately on blinded, message- and unique-edge-level labels, including an explicit not-an-employee/no-compatible-referent option. Match full context and actual NER offsets; do not treat every `&` or line-broken department label as a company. Keep policy exclusions separate from error exclusions. Freeze changes before a new held-out sample; do not keep tuning the same examples until the reported score improves.

### Major M3 — Reply-confidence labels are not reliable measurements of immediate parenthood

**Fresh sample and denominators.** `text/extract.py`, `text/manual_labels.json` and `text/labels_and_stats.py` draw and adjudicate **20 reply-kind links from each confidence stratum**. The population has 19,068 high, 2,122 medium and 5,699 low reply links (26,889 total). “Direct” requires the selected **immediate** parent, not merely topical relatedness.

| Confidence | Supported direct / sample | Uncertain | Confirmed-direct fraction; Wilson 95% |
|---|---:|---:|---|
| High | 18/20 | 0 | 90.0% [69.9,97.2] |
| Medium | 12/20 | 1 | 60.0% [38.7,78.1] |
| Low | 15/20 | 3 | 75.0% [53.1,88.8] |

Population-weighting the strata gives **84.45% confirmed direct**, or **88.03%** if all uncertain cases are correct. A stratified plug-in bootstrap gives **73.12–93.52%**, sampling uncertainty only. The pooled 45/60 is not the population estimate. The wide, overlapping intervals do not establish that “low” is truly better than “medium.”

Relative to the complete audit-4 output, **2,282 reply links were lost, 182 gained and 75 changed parent**; 26,632 retain the same reply parent. New independent samples of 30 lost and 30 gained links find **14/30 genuine direct replies lost** (46.7% [30.2,63.9]) and **13/30 genuine direct replies gained** (43.3% [27.4,60.8]); one lost case is uncertain. Scaling these samples estimates about **1,065 valid links removed (sampling range 690–1,457) and 79 added (50–111)**, alongside many false links removed. This excludes changed-parent links and is not corpus-wide recall or a complete net-utility estimate. The prior audit-4 labelled 47 direct replies retain 46 correct same-parent reply links and lose one; the earlier audit-1 24/28 regression figure also reproduces. Evidence: `text/counts.json`, `text/audit4_retention.json`, `text/audit1_retention.json`, `text/label_stats.json`.

**New matching defect.** `_same_author()` at `threads.py:161–168` accepts conflicting full first names and middle initials whenever surname and first initial agree. The controlled fixture in `text/controls.py` links a quote attributed to Jane Smith to John Smith and labels it high confidence. This also occurs naturally: of all **34,749 current links**, **three** rely only on this fallback; one selects **Cindy White** as parent when the first quoted author is **Cara White**, with distinct addresses. Public-corpus identifiers: child `beck-s/sent/859.`, selected ancestor `beck-s/all_documents/420.`. The quoted Cindy text occurs deeper in the chain; author plus text is therefore not independent evidence of immediate parenthood. The other two fallback cases were not shown wrong. Do not extrapolate a 1/3 error rate to all links.

**Lost genuine replies.** The first-header restriction can read an older embedded self-quote after missing a nearer inline name/date header, then abstain. Fresh lost examples include `symes-k/all_documents/2479.`, `3487.` and `3304.`. A blanket FW-subject classification can also demote an actual addressed-back response (`watson-k/e_mail_bin/312.`). Source: `threads.py:112–114,127–139,172–181,197–200`; evidence: `text/lost_reply30.json` and labels.

Two high-confidence sampled links choose older same-author messages: `mann-k/sent/3180.` chooses an 08:34 Reagan message although the first quote is 10:10, and `heard-m/inbox/master_netting/283.` chooses a November 6 Marie message although the first quote is November 12. Two gained links point backwards in the conversation because the quoted short response falls below the **40-character inversion check**: `dasovich-j/sent/12120.` and `jones-t/notes_inbox/2394.`. The original angle-quote inversion fixture also still fails (`text/old_thread_fixture_replay.json`). Restricting author names alone does not identify the first quoted message instance.

**Impact.** Reply count reduction is not itself a demonstrated net improvement. Wrong immediate parents invalidate response-time and conversational-obligation features even if the messages belong to the same conversation. Current email-degree and mention calculations do not consume the inferred parent links, so this finding does not by itself invalidate those headline scores.

**Fix.** Reject conflicting complete names before falling back to initials; parse the nearest header and preserve conflicting/unknown evidence. Treat confidence as a feature combination until calibrated against fresh immediate-parent labels. Before Phase 3 reply-derived features, obtain a blinded positive/negative parent sample and a sample of true replies independent of the algorithm; measure both precision and missed-link rates. Abstain when immediate parenthood is unsupported rather than substituting an older ancestor.

### Major M4 — Sender-anchored signature removal still deletes substantive person text

**Fresh evidence.** There are **616 internal-person messages whose analysis inclusion is changed solely by the signature exclusion**. A new SRS of 60 finds **three definite substantive false exclusions** (5.0%; Wilson **1.7–13.7%**) and one ambiguous case; the other 56 are signatures. This is a marginal-exclusion precision check, not an estimate over every flagged message. `text/signature_marginal60.json`, `text/manual_labels.json` and `text/label_stats.json` retain context and decisions.

A fresh SRS of 60 retained person-text messages finds no pure-signature or newsletter false negatives (upper Wilson bound **6.0%**). An enriched sample of 30 retained short contact/sign-off-like messages finds no pure-signature false negatives (upper bound **11.4%**). These estimate missed-exclusion prevalence in the stated kept-message frames, **not sensitivity among all true signatures/newsletters**.

**Evidence and cause.** `signature_only()` requires only **one overlapping name word**, not the sender's identity (`senders.py:123–127`), and allows any short capitalized lines plus one phone/title/address indicator (`:129–140`). In the fresh marginal internal-person sample, `rogers-b/sent/340.` contains another person's contact details sharing the surname; `rodrique-r/sent/296.` is a completed information request with a supervisor, cost centre and rotation date; `shackleton-s/notes_inbox/948.` is a substantive roster. These are not the sender's empty signature. The reviewer inspected actual text and flag eligibility, not just regex matches.

**Impact.** These exclusions selectively delete short administrative exchanges and structured human answers—the kind of coordination evidence Phase 3 may need. Repairing “Not I.” and one ranking table does not establish the general exclusion's precision.

**Fix.** Require a defensible sender identity match, distinguish contact blocks from lists/forms, and annotate marginal exclusions rather than tuning only known failures. Preserve raw text and reason flags so analyses can include/exclude this class as a sensitivity. Do not count subject-only information as a cleaner failure when evaluating the stated body-only rule; that is a separate scope decision.

### Minor m1 — The newsletter threshold counts URL prefixes, not URLs

`senders.py:83,90–91` uses `https?://|www\.`. Two strings such as `https://www.example.com/a` and `https://www.example.com/b` produce **four matches**, satisfying a supposedly three-URL rule. `text/controls.py` constructs a substantive reply with those two links and a list footer that is incorrectly marked structured. A fresh sample of **30 flagged newsletters** contains no false positives, and a **census of all 19 marginal internal-person newsletter exclusions** finds all 19 justified (18 from Avril Forster). One original external mailing-list counterexample, `lokey-t/inbox/155.`, remains marked structured despite substantive human text; the other, `skilling-j/inbox/1543.`, is repaired. The surviving external case does not change internal analysis inclusion. Fix the counter to match complete non-overlapping URL occurrences, and test one/two/three actual links. The code defect is established; it must not be represented as a measured widespread internal-message loss.

### Minor m2 — A selected-stage freshness check does not verify its ancestors

`stale_reasons(config, stages=[...])` checks only requested entries (`provenance.py:113–141`), not recursively the outputs of their dependencies. Corrupting centrality is caught by the full gate but **`stale_reasons(config, ['figures.baselines']) == []`**. Its docstring promises the selected stages “and what they read from.” Evidence: `provenance/attacks.json`, `corrupt_centrality_full` and `corrupt_centrality_figures_only`. This does not bypass the current full corpus-test gate. Recursively close the dependency set or narrow the API contract.

### Minor m3 — Surviving mutants and documentation qualifications

All **59 historical mutation probes** were rerun (32 gold/identity/dedupe, five prepare/provenance, 13 mentions, nine text/threads). **57 are caught**; two mention mutants survive, one apparently equivalent. Counts are not inflated by syntax/import/collection failures. Two historical dedupe kills are actual missing-column schema failures; the other historical kills are assertions. Exact source substitutions, subprocess commands, baseline logs and outcomes are in `provenance/mutations.py`, `provenance/mutation_summary.json`, `mentions/mutations.py`, `mentions/mutations.json`, `text/mutations.py`, `text/rerun_mutations.py` and `text/mutations.json`.

| Family | Historical results | Additional probes |
|---|---|---|
| Gold / identity / dedupe | 32/32 caught, including the formerly surviving shared-key `gold_table` bootstrap and unresolved recipient extras | Shared-key resampling in **`paired_gold`** survives all 24 gold tests. |
| Prepare / provenance | 5/5 assertion-killed, including constant Python/lock cache stamps | Nine of ten behavior-changing new provenance, recipient/dedupe and paired variants caught. Two additional equivalent/diagnostic variants excluded from this denominator. |
| Mentions | 11/13 caught | Five of seven new probes caught; omitting model metadata or spaCy version from cache identity survives. |
| Cleaner / sender / threads | 9/9 caught, including quoted-author extraction removal | Five of eight extra runs caught, three survive; one caught run repeats the historical author-guard deletion. |

The **behavior-changing survivors** are:

- Change the documented **5,000-character cap to 10**: all 21 mention tests pass because the boundary expectation uses the same mutated constant (`tests/test_mentions.py:118–121`). This is missing coverage of the documented default, not evidence current code uses ten characters.
- Replace model name/version or spaCy version with a constant in `tagger_id`: all 21 mention tests pass. Test each declared invalidation input, not only components and cap.
- Lower the newsletter threshold **3→1**, remove explicit self-quote abstention, or relax author matching to surname-only: each passes the 74 selected text tests. `text/mutant_witnesses.json` demonstrates different and wrong behavior; the existing fixtures are redundant with other constraints or lack the relevant threshold/conflict.
- Resample graph keys instead of gold employee IDs only in **`paired_gold`**: all 24 gold tests pass. A 70-pair independent witness changes a paired interval from **[-0.55122093,0.10208874]** to **[-0.54488028,0.08988659]**, leaving the point difference at -0.25 (`provenance/paired_key_probe.py/json`). The production implementation is currently correct, and the independent full-data intervals match. Extend the shared-key regression from `gold_table` to paired differences and subgroup draw counts.

The other historical mention survivor removes nickname variants from the name index. A 168-query equivalence probe finds no difference because `compatible()` canonicalizes nicknames separately; it is **not counted as a demonstrated semantic gap**. Tests have improved, but “all surviving mutants fixed” is not supported.

**Numerical reporting:** The current headline values, paired intervals, Cc strata, thread regression figures and **0.3027–3.7215 percentage-point** primary sensitivity range reproduce. The primary overall interval is **[-0.4194,+4.9129] points**; README:189–193 correctly says this gain is not distinguishable from zero. It does not establish equivalence/no effect. The non-core primary difference is **+3.5824 points [0.8862,7.5634]** on the stated population, distinct from the overall comparison. The secondary third-party result is exploratory, not a replacement primary result selected because its interval excludes zero.

The following statements need qualification or correction:

- `mentions.py:7–8` says that using sender-owned text prevents quoted messages from being counted again. Fresh kept rows and the archived quote-header counterexamples contradict that categorical wording. Use “estimated authored text, with residual quotations.”
- README:170 and response M2 describe all sender-self exclusions as signatures/contact lines. The sample includes a roster and mixed contexts. State that **all self-resolving mentions** are excluded, many of which are signatures.
- README:86–92 and `threads.py:185–190` should distinguish the **first recognized header** from the first actual quoted author. Confidence is an evidence category, not a validated probability.
- `senders.py:116` says tables of others' names are not signatures; the natural roster counterexample refutes this guarantee. The response's M3 “fixed for demonstrated cases” is not accurate for both old newsletter examples.
- The response's final “every network-measure accuracy [is] unchanged” is true only at displayed rounding precision for the title results: weighted in-strength changes **0.6227746592 → 0.6229350441** (0.0160 percentage points); degree's lower interval changes **0.5902409830 → 0.5900680104**. All 24 comparable gold email-network/custodian rows are numerically identical. `documentation_check.py/json` and the archived/current CSVs show this small difference; it does not change the substantive conclusion.
- The response's exact **1,190 recovered links** and **five changes in 20,000 bodies** are not independently reproduced here. The associated code changes and old counterexamples were tested, but the intermediate counterfactual run and the exact cleaning sample/seed were not supplied as reproducible evidence. A fresh different sample cannot certify those exact numbers.
- `mentions.py:44` promises invalidation on “any change” to the tagger. The digest covers named metadata/configuration, not model payload changes under the same metadata or altered cache contents; see M1.
- Clarify README:194–195 as “mention degree minus degree: +6.8; primary mentioned-to minus degree: +2.8.” Mention degree minus primary is instead **+3.9455 points [1.6273,6.7519]**. The existing compressed wording is ambiguous, not evidence the stored paired table is wrong.

**Declaration chronology:** `git show 52b34f9 -- src/enron_importance/evaluate.py` introduces the primary contrast at **04:16:47 EDT**, after audit-4's unfiltered results/report (report commit `6d00681`, **04:02:51**; earlier result commit `1c7a75b`, **01:44:23**) and before committed filtered results `62da63e`, **05:09:54**. Commands and output are saved in `mentions/history.json`. This supports the stated commit sequence, not outcome-independent preregistration or proof no private exploratory run occurred. Report the filtered primary comparison as exploratory, selected with earlier unfiltered results already known.

### Minor m4 — Widened header syntax still has a prose-boundary ambiguity

`clean.py:40–43,63` now accepts short plain-word lines in a wrapped quoted header. In `text/controls.py`, an original agenda containing `Meeting notes`, a date/time, `To: team`, two prose lines, and `Subject: proposed plan` is cut to **empty authored text**. The old punctuated-agenda and `Received: from supplier` negative controls survive; this is a new constructed boundary counterexample, not a measured common corpus error.

The fresh controlled old/new comparison over **3,000 bodies** changes one output, correctly removing copied announcement text (`hyvl-d/all_documents/811.`). A fresh sample of **60 quoted retained person-text messages** finds no substantive false cuts (Wilson upper 6.0%) and one residual header (`farmer-d/sent/309.`). That selection excludes unrecognized-quote and already-removed-message frames, so it cannot establish overall recall or safety. Evidence: `text/cleaner_fresh3000_changes.json`, `text/quoted_person60.json`, `text/controls.json`, `text/manual_labels.json`. Keep this prose negative control and use structured header validation; preserve the README's estimated-authorship caveat.

## 4. Phase 3 leakage risks and required tests

1. **Names, titles and signatures.** Redact explicit job titles, signatures, contact blocks, addresses, quoted headers and recipient lists before claiming linguistic importance. Compare unredacted/redacted models and names-only/title-only baselines on the identical population. Current `person_text` verifies a rule-based sender classification, not employee identity or authorship of every surviving span.
2. **Corpus collection and graph-assisted resolution.** The mention resolver uses the email graph and a closed candidate list. Treat the Cc agreement as endogenous consistency, not referent accuracy. Report custodian-only, message-volume and graph-only baselines, within core/inter/non-core, and leave-executive-out/macro comparisons. If predicting unseen people or future periods, rebuild resolution, filters and graph using training/earlier data only; otherwise call the task transductive.
3. **Copies and train/test dependence.** Split by people and time where relevant, group duplicate/near-duplicate messages and threads, and keep quoted copies/newsletter copies out of both sides of the split. A random message split does not test transfer to new employees or future communication.
4. **Inferred replies.** Do not train speech-act/response-time targets as though link kind and parent were observed labels. First obtain blinded immediate-parent and missed-reply labels independent of these heuristics, with separately measured confidence strata.
5. **Selection and repeated use of outcomes.** The primary mention comparison was selected after audit-4 unfiltered results were known, albeit before the filtered rerun. Treat the present program as exploratory. Freeze the population, filters, features, primary measure, null baselines and sensitivity analyses before a new held-out evaluation; report both main and strict gold populations rather than optimizing which one is favourable.
6. **Construct validity.** Neither title ordering nor dominance-pair accuracy validates functional importance, productivity, replacement risk or causal dependence. A departure-based outcome would need justified timing, observation-coverage controls and a separate evaluation design. Do not turn a hierarchy residual into validated functional importance by renaming it.

**Items that require human-labelled evidence, not another code-only patch:** whether names denote the intended real person/employee, whether text is genuinely authored or a signature/newsletter, and whether a link is the immediate reply and which true replies were missed. This audit's AI-assisted labels are error-finding evidence, not a substitute for blinded domain-informed annotation with an adjudication protocol.

## 5. What was not verified

- This is a cached replay, not a fresh extraction of all raw messages or a fresh retag with the pinned NER model. Original raw corpus and private-release files are hash-checked; cache metadata/payload protection was attacked in scratch. Passing a cached replay is not independent NER validation.
- Exact **1,190** recovered links cannot be established without the specified intermediate address-only counterfactual and input snapshot; no such full counterfactual was run. The exact original **five-of-20,000** claim lacks the saved sample/seed needed for like-for-like reproduction. I searched the response, relevant commit messages and available earlier scripts; the independent 3,000-body comparison is reported as a different sample, not a replacement verification.
- The prior gold release's provenance, label ambiguity, hierarchy construction and principal-name matching were not re-adjudicated from scratch. This audit reruns the pinned implementation and independent scoring calculations; it does not make the reconstructed pair set equal to the 2012 paper's or establish representativeness of the selected 7,338 pairs. Matching/label uncertainty is not included in the bootstrap intervals.
- No true global precision/recall estimate for all NER entities, signatures, newsletters, quoted spans or replies was established. There are no blinded human labels or inter-annotator reliability estimates. The 75 changed-parent links were extracted but not all manually adjudicated. Sample frames, uncertainty and old-example reuse are stated above.
- The company-case intervention restores only reviewed false exclusions; it is not a complete corrected mention graph, independent evaluation of a new filter, or claim of improved accuracy.
- I did not establish a naturally occurring false exclusion of two genuinely distinct same-surname recipients under the conservative extra-recipient policy. Its synthetic limitation is real and disclosed; the 14 previously demonstrated duplicate additions are repaired.
- Git chronology supports the order of committed declaration/results only. It cannot establish that no uncommitted exploratory run occurred before the declaration.
- The report does not establish functional importance, employee productivity, replacement risk, causal effects of departures or cross-organization generalization. Those require separate constructs and validation designs.

### Reproduction commands

All code used for the findings is retained at the named evidence paths. The pinned package imports were selected with `PYTHONPATH=/tmp/enron-audit5-20260926.RIaA4K/pinned_project/src`; bytecode writing was disabled and numerical thread counts were set to one. These are the entry commands (each script embeds the exact fixed input/scratch paths and seeds):

```sh
cd /tmp/enron-audit5-20260926.RIaA4K
export PYTHONPATH=/tmp/enron-audit5-20260926.RIaA4K/pinned_project/src
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/enron-audit5-20260926.RIaA4K/mpl
pinned_project/.venv/bin/python -B numeric.py title
pinned_project/.venv/bin/python -B numeric.py gold
pinned_project/.venv/bin/python -B documentation_check.py
pinned_project/.venv/bin/python -B reproduce.py
pinned_project/.venv/bin/python -B provenance/attack.py
pinned_project/.venv/bin/python -B provenance/replay_tiny.py
pinned_project/.venv/bin/python -B provenance/recipient_check.py
pinned_project/.venv/bin/python -B provenance/mutations.py all
pinned_project/.venv/bin/python -B provenance/summarize_mutations.py
pinned_project/.venv/bin/python -B provenance/corpus_gate_probe.py
pinned_project/.venv/bin/python -B provenance/paired_key_probe.py
pinned_project/.venv/bin/python -B mentions/extract.py
pinned_project/.venv/bin/python -B mentions/fixtures.py
pinned_project/.venv/bin/python -B mentions/ste_boundary.py
pinned_project/.venv/bin/python -B mentions/mutations.py
pinned_project/.venv/bin/python -B text/extract.py
pinned_project/.venv/bin/python -B text/replay_old.py
pinned_project/.venv/bin/python -B text/replay_old_threads.py
pinned_project/.venv/bin/python -B text/controls.py
pinned_project/.venv/bin/python -B text/context_controls.py
pinned_project/.venv/bin/python -B text/labels_and_stats.py
mkdir -p text/mutation_tmp
pinned_project/.venv/bin/python -B text/mutations.py
pinned_project/.venv/bin/python -B text/mutant_witnesses.py
pinned_project/.venv/bin/python -B final_checks.py replay
pinned_project/.venv/bin/python -B final_checks.py hashes
```

Some tiny fixture scripts intentionally leave corrupted **scratch** payloads. Use a fresh fixture directory/reset the fixture's own file before rerunning; do not point these attacks at the production directories. The scoped logs record that agents used the certified environment's Python while the root rerun/oracles used the independently synchronized environment; the package/version inventories are identical. No code changes, commits, pushes or private-release republication were made.

