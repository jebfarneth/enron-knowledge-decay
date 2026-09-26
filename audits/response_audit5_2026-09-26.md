# Response to audit 5 (2026-09-26)

Audit 5 ([report](audit5_codex_2026-09-26.md)) found no critical problem,
reproduced every reported number, and judged the data layer and both
evaluations fit for exploratory Phase 3 work with conditions. It separated
code defects from questions that only blinded human labels can settle. This
round fixes the code defects and nothing else; the pipeline is then frozen,
and the labelling questions become the first Phase 3 task. Full rerun on
branch `rebuild/audit5-fixes`: 254 unit tests and all 17 real-corpus
checks pass, and the stage manifest certifies the run.

| Finding | Status | Commits | Change and effect |
|---|---|---|---|
| M1 manifest omits inputs | fixed | `180a285`, `bedb3ca` | Each stage records checksums of the files it reads besides earlier outputs (raw corpus, title list, gold release, labelled thread sample, NER model files, `uv.lock` for every stage) and the Python version; a change to any makes the stage stale. The name-tag cache is a declared output. A cached tag entry is reused only when each name is at its recorded position in the text (the forged-payload probe is retagged), and the tagger identity includes the model's weight files. |
| M2 mention referents and the company filter | code defects fixed; referent validity open | `bedb3ca` | The company rule no longer crosses line breaks, no longer counts a bare "&", and ignores company words followed by a department word (Power Group, Gas desk); office titles must be on the same line. "Ste" is caught when spaCy's span stops before the period. **Effect:** company exclusions fall from 1,775 to 278 resolved rows and 68 abbreviation exclusions now occur (none before); the primary result is unchanged at the displayed precision (91.3% on the main gold pairs; paired gain over degree +1.7, −0.4 to +4.9). **Open:** 43 of 60 sampled kept rows were right, 11 wrong (public figures, companies and places resolved to employees). Whether a name denotes the intended person, and whether the person is an employee, needs blinded message- and edge-level labels with a none-of-these option; no further filter was tuned on the audit's examples. |
| M3 reply confidence and lost replies | matching defect fixed; calibration and recall open | `766bd8e` | The surname-and-initial fallback now needs compatible first names (equal, nickname or initial) and no conflicting middle initials, so Cara White no longer matches Cindy White. The docstring and README say the rule reads the first *recognized* header and that confidence levels are evidence categories. **Effect:** 14 links gained, 1 lost and 1 changed parent (34,762 links; 26,902 replies); `beck-s/sent/859.` now links to Cara White's message. **Open:** audit 5 estimates that about 1,065 of the 2,282 reply links dropped after audit 4 were genuine, and found wrong parents at every confidence level (high 18/20, medium 12/20, low 15/20 direct). Nearest-header parsing, the FW: rule and the 40-character inversion check were not retuned; immediate-parent precision and missed-reply recall need blinded labels. |
| M4 signature removal deletes content | fixed for the demonstrated classes | `4c15a7a` | A signature's name line must contain two of the sender's name words (first and last), so another person's contact block sharing the surname is kept; a "label: value" line other than phone or e-mail marks a form. **Effect:** signature-only messages fall from 1,161 to 1,026 and structured records and newsletters from 6,763 to 6,434 (with m1); the analysis set grows from 168,377 to 168,510 messages and person text from 165,300 to 165,431. **Open:** a roster opening with the sender's own name can still pass; precision of marginal exclusions needs labels. |
| m1 newsletter URL count | fixed | `4c15a7a` | Whole links are counted, so `https://www.` is one link; tests cover one, two and three links. The external mailing-list example `lokey-t/inbox/155.` is still flagged (it has three or more whole links); it is not an internal analysis message. |
| m2 partial freshness check | fixed | `180a285` | A check limited to some stages covers every stage they read from, directly or not. |
| m3 surviving mutants | fixed | `bedb3ca`, `766bd8e`, `4c15a7a`, `88c6ca7` | New tests fail under each reported survivor: the 5,000-character cap (pinned literally), model name/version, weights and spaCy version in the tagger identity, the newsletter threshold, removal of self-quote abstention, surname-only author matching, and graph-key resampling in `paired_gold`. |
| m3 documentation | fixed | README, `bedb3ca`, `766bd8e`, `4c15a7a` | Authored text is described as containing residual quotations; self-resolving exclusions are "mostly" signatures (the sample had a roster); the rule reads the first recognized header; the title-proxy differences are stated separately (mention degree minus degree +6.8; people mentioned to them minus degree +2.8); the filtered primary comparison is labelled exploratory because it was declared after the unfiltered results were known. |
| m4 prose-boundary cleaner case | open | — | The constructed agenda ("Meeting notes", date, "To: team", prose, "Subject:") is still cut to nothing. The fresh 3,000-body comparison changed one output, correctly; no corpus case was found. Left unchanged rather than adding another header rule without a labelled sample. |

## Corrections to the audit-4 response

- **1,190 recovered links.** This came from comparing the links of an
  intermediate run (built with address-only author matching) with the final
  audit-4 run. The intermediate links were kept only in a local scratch
  folder and are not a reproducible artifact, so the figure is unverified.
- **Five changed outputs in 20,000 bodies.** The sample and seed were not
  saved; audit 5's own 3,000-body comparison (one change, correct) replaces it.
- **"Every network-measure accuracy unchanged."** True at displayed precision;
  in-strength on the title proxy moved from 62.277% to 62.294%.
- **Response M3 "fixed for the demonstrated cases."** One of the two original
  mailing-list examples (`lokey-t/inbox/155.`, an external sender) was, and
  still is, flagged.

## What is frozen

From this commit the population (7,338 main gold pairs, 4,939 strict), the
filters, the primary mention measure (`mentioned_to`, filtered), the null
baselines (degree, custodian) and the sensitivity runs are fixed. Phase 3
starts with blinded labels for mention referents, reply parents (including
missed replies) and signature and newsletter exclusions, and any later
change to these rules will be evaluated on a fresh held-out sample.
