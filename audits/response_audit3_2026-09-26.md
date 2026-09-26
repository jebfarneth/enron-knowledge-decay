# Response to audit 3 (2026-09-25)

Audit 3 ([report](audit3_codex_2026-09-25.md)) reviewed commit `a359924` and
found the data layer fit for exploratory Phase 3 work with conditions, the
title-proxy evaluation fit with conditions, and the gold-standard evaluation
not yet fit. Each finding is listed with its commits, effect on the
regenerated data (full rerun on branch `rebuild/audit3-fixes`; 166 unit
tests and all 13 real-corpus checks pass) and what remains open.

| Finding | Status | Commits | Change and effect |
|---|---|---|---|
| M1 gold paths through merged records | fixed as a reported policy | `6cab87c`, `ba79e5b` | Records mixing an assistant's position with another (8) and records whose addresses resolve to several people across several positions (20; 23 uncertain in all) are flagged. Pairs are marked by whether they still follow with every relation touching those records removed before the closure. The main population excludes pairs that start, end or run through the 8 mixed-position records (7,338 pairs); excluding paths through all 23 is a strict sensitivity run (4,939 pairs, degree 92.9%), and the earlier endpoint-only definition is kept too (10,041 pairs, 83.8%). The strict run is not the main result because several people behind a record's addresses (usually an executive and an assistant) is weaker evidence about positions than a merged position. **Open:** author guidance on merged records. |
| M2 mailbox order decides identity | fixed | `6cab87c` | All of a record's mailboxes are pooled; two different mailbox-matched names make it ambiguous. Mailbox initials match first names as written ("Bob" for Robert). A permutation test covers it. **Open:** a blinded identity-match sample. |
| M3 recipient union duplicates people | fixed for the demonstrated cases | `6643d6b`, `af81016` | The kept copy's recipients stay unchanged; addresses only other copies list are stored apart and added only when they resolve to a new person sharing no surname with a recipient (Calger still added; second spellings of Brown, Phillips, Palmer, Anderson not). Send grouping uses connected components, so copy order no longer matters; Message-ID duplicates map to kept messages. **Open:** Robert/Gary Anderson needs X-To display names. |
| M4 bulletins and signature-only records | partly fixed | `8d50c1d`, `fe3c610` | Signature-only messages (a name line followed only by title, department, company, address, phone or e-mail lines) are excluded: 1,366. Copied newsletters ("daily service of", unsubscribe lines) are structured records. The four long bulletins from placeholder senders are excluded from person text by attribution. **Open:** signatures inside ordinary messages (Phase 3 redaction). |
| M5 department accounts pass person text | fixed | `7746bb5` | Department words (hotline, console, parking, transportation, payroll, registrar, security, …) make role keys, and a name an address also sends through a shared mailbox becomes that mailbox in every rendering. |
| M6 wrong reply parents | partly fixed | `a24b780` | Candidates from the message's own sender are skipped, and when the quoted header names its author and no candidate's text is found in the quote, only that author's messages qualify. On the first audit's labelled sample 24 of 31 same-parent reply links are direct replies (77.4%). **Open:** a fresh, human-labelled precision and recall sample. |
| M7 cleaner and structured rules | fixed for the demonstrated cases | `c3f6a8f`, `79827b7`, `8d50c1d` | Day-first 24-hour Lotus dates and wrapped recipient lists of up to 80 address lines are cut; prose between a To: line and a later Subject: is kept; the patterns are written so each line matches one way (the earlier form backtracked badly on long messages). "PEP ACCESS" openings are no longer structured. **Open:** inline answers inside quoted messages. |
| M8 stale artifacts pass corpus checks | fixed | `a33873e`, `6cab87c` | Corpus checks skip only when nothing is built; missing files fail, and the run fails when the code hash, configuration hash or any output checksum differs from the manifest. A skipped gold stage deletes its earlier outputs. |
| Minor: empty paired draws; mutation gaps | fixed | `6cab87c`, `a33873e` | Paired differences survive resamples without pairs. New tests: interior-interval and paired-interval brute-force oracles, mailbox permutation, genuinely different constructions, path dependency, cache stamp fields, digit-only roles, two-word titles, Cc copies, and a probable copy that must not become a reply parent. |
| Documentation | fixed | `0988e2b`, `105472a`, `7746bb5`, README | Config comments describe the whole-text routine rule and which parameters live in the file; the raw-address run names its input; title-list aliases state their evidence; the README no longer says every number comes from the public corpus and reports the thread figure with its denominator. |

## Other changes in this round

- The mention network of Agarwal et al. (2014) (`b4fad2b`, `02ac2d4`,
  `b2600e1`, `0822460`, `a814f8a`): resolution matches the paper's Cc check
  (70.7% against 69.7%); people mentioned to someone orders 92.2% of the main
  gold pairs (degree 89.6%; paired +2.6, interval +0.7 to +5.5) and
  mention-network degree 73.1% of the title-proxy pairs (degree 66.6%;
  +6.5, +3.2 to +10.1).
- Speed: the quoted-section search now runs once per message (`ac1e801`)
  and the name tagger skips an unused component (`a814f8a`).
