# Independent adversarial audit — Enron data and network baselines

Date: September 25, 2026. Repository: `/Users/jebfarneth/projects/enron-knowledge-decay`, branch `main`, audited commit `8c595e7e6cc842260843d49547f20b796994db6a`. Scope: `src/enron_importance/`, tests, configuration, raw/intermediate/processed data, current results/figures and relevant non-legacy history. `legacy/` is out of scope.

Evidence root: `/tmp/enron-audit-20260925.Xj3qoO`. Commands below assume the repository as working directory unless stated otherwise. Code references such as`identity.py:67–78` mean`src/enron_importance/identity.py`; line ranges refer to the audited commit. Scratch scripts contain the executable probes and preserve selected records/labels; they are not repository changes. Manual email judgments are explicitly distinguished from deterministic counts and independently calculated numerical checks.

## 1. Executive verdict

**No—not yet as a frozen, person-level data foundation for Phase 3.** All claimed funnel counts reproduce, but reproducible counts do not establish valid people, authored language, replies or organizational rank. The audit finds mixed-author identity merges, unresolved recipient/list nodes, contradictory title labels, discarded recipient evidence, timestamp-shifted probable copies, human operational work removed as automation/routine, and low direct-parent validity in inspected reply links. Those errors directly affect the proposed speech-act/topic-ownership research. Independent edge, PageRank, betweenness and bootstrap-oracle checks pass, while floating out-strength ties cause a small, real reproducibility failure. Simple custodian/mailbox-volume predictors do **not** explain away degree's observed title-ordering result. Freeze inferential text-model claims until identity/entity typing, label provenance, text/filter validation and reply-link validation are repaired and baselines rerun. Current evidence supports an exploratory association between a partially resolved communication graph and a noisy title proxy—not measurement of functional importance or post-departure validation.

## 2. Methods derived from implementation

The following descriptions were derived from source, then checked against actual data and independent probes. Plain-language and technical versions are both supplied. A paper must report the hard-coded choices as well as `config.yaml`; the statement that **every** parameter is in configuration is false.

### Download and source verification

**Plain language.** The downloader keeps the public CMU archive locally and checks its byte count and SHA-256 fingerprint against the configuration. This establishes that the bytes match the project's pinned copy, not that every email or claimed author is authentic. The normal pipeline only invokes this check when the parsed cache is absent.

**Technical Methods.** `download.py:18–23,26–56` reads/downloads the configured archive, transfers in 1 MiB blocks to a `.part` path, renames the completed transfer, and exits on size/hash mismatch or an unpinned hash. The configured source is CMU's May 7, 2015 release, 443,254,787 bytes, SHA-256 `b3da1b3fe0369ec3140bb4fbce94702c33b7da810ec15d718b3fadf5cd748ca7` (`config.yaml:4–12`). The checksum was recorded by the project, not published independently by CMU. `prepare.py:29–32` trusts an existing `messages_raw.parquet` without checking its producing code/config/archive. Report the source release, source URL, checksum provenance, cached-input policy, and public-corpus limitations in the paper. CMU states that attachments are absent, some mail was redacted, and malformed addresses were synthesized; a domain suffix alone is therefore not proof of employment or identity. Source: [CMU Enron corpus description](https://www.cs.cmu.edu/~enron/).

### Parsing (`ingest.py`)

**Plain language.** Every regular file under the archive's `maildir/` tree becomes a row. The parser records the mailbox owner and folder, email addresses, subject, date and body. Addresses are lowercased; dates become UTC. It does not recover missing attachments or conversational headers.

**Technical Methods.** `ingest.py:27–40,82–130` uses Python's email parser with `compat32` policy on each regular tar member starting `maildir/`. Path component 1 is `custodian`, component 2 is `folder`; nested subfolders survive in `path` only. Message-ID is stripped or null. Address extraction unfolds/collapses header whitespace, calls `getaddresses`, strips quotes/brackets, lowercases, rejects strings without `@`, and deduplicates while preserving order (`43–51`); the first From address becomes sender. `parsedate_to_datetime` dates lacking a timezone or failing parsing become null; otherwise `pd.Timestamp` converts to UTC (`54–63`). For multipart input only the first text/plain part is read; single-part payloads are decoded using declared charset or UTF-8, with replacement errors, falling back to Latin-1 only on an unknown charset (`66–79`). X-From and Subject header whitespace is collapsed but RFC encoded-word decoding is not explicitly performed. Rows are written in archive order, batches of 20,000, Arrow schema with UTC microsecond timestamps, Zstandard compression. These batching/decoding decisions are hard-coded, not config parameters. The paper must state absent attachment content, unretained In-Reply-To/References, address rewriting inherited from CMU, and the handling of missing or malformed fields.

### Windowing and deduplication (`dedupe.py`)

**Plain language.** The pipeline keeps dates from 1998 through 2002 and treats messages with the same sender, timestamp, simplified subject and simplified body as copies. It chooses one folder's copy rather than combining information across copies. This can remove genuine repeated sends or discard recipient information if those copies disagree.

**Technical Methods.** `dedupe.py:58–79` retains UTC timestamps in `[1998-01-01 00:00, 2003-01-01 00:00)`, separately counting null and out-of-window dates (`config.yaml:21–25`). The content key is SHA-1 of sender, ISO-format UTC timestamp, normalized subject and body separated by U+001F (`41–50`). Subject normalization removes repeated leading Re/Fw/Fwd prefixes, collapses all whitespace, trims and lowercases; body normalization collapses whitespace, trims and lowercases, but neither performs Unicode normalization or attachment hashing (`24–38`). Missing nonstring text becomes empty. Selection sorts by the hard-coded folder priority `sent`, `_sent_mail`, `sent_items`, `inbox`, `notes_inbox`, `all_documents`, `discussion_threads`, `deleted_items`, then other folders, breaking ties lexicographically by full path (`19–23,53–55,73`). All but the first content-key occurrence are dropped; nonnull Message-ID duplicates are additionally dropped where not already counted. Surviving rows are sorted by path and assigned a new sequential index. Recipient lists, X-From and custodian are not in the key and are not unioned or retained as provenance for discarded copies. The paper must disclose normalization and copy priority, recipient-conflict handling, whether residual near-copies cross future train/test boundaries, and independently measured precision/recall rather than calling every removal a verified duplicate.

### Authored text (clean.py)

Plain language: Each deduplicated email is treated as a top-posted message: retain everything before the first recognized older-message header, remove lines beginning with `>`, remove selected disclaimer/advertising patterns, collapse excess blank lines, and trim the result. This is a rule-based estimate of authored text, not attribution of each sentence to an author. It does not remove ordinary signatures. `prepare.py:43–46` applies this to every retained message before sender filtering.

Technical: `clean.py:83–92` converts a non-string body to the empty string, normalizes CRLF/CR to LF, then truncates at the minimum first-match offset among eleven regular expressions (`clean.py:20–55,77–80`). The markers cover (1) two-or-more-hyphen Original Message delimiters; (2) three-or-more-hyphen Forwarded by banners; (3) From followed by Sent after at most two arbitrary intervening lines plus whitespace; (4) a 1–80-character non-newline name-like line, US slash date with AM/PM, and To after at most two arbitrary intervening lines plus whitespace; (5) a 1–160-character line containing `on` plus that date and To after at most one arbitrary intervening line plus whitespace; (6) From and date on one line, optionally preceded by an indented company banner (uppercase initial plus 0–60 characters ending Corp., Inc., LLC or Ltd.), then To; (7) consecutive To/cc/(blank lines)/Subject; (8) Inline attachment follows between at least three hyphens on either side; (9) line-initial Received: from, Return-path, or Content-transfer-encoding; (10) From with a day-first date and optional timezone; and (11) On ... wrote, with 5–120 intervening characters. US date patterns accept 1–2 digit month/day/hour, 2–4 digit year, 2-digit minute, optional 2-digit seconds and an optional space before uppercase AM/PM; the day-first pattern accepts hyphen/slash/dot separators and optional 2–4 uppercase-letter timezone. Date patterns 4/5/6/10 are case-sensitive; Original/Forwarded/From-Sent/bare headers/attachment/transport/On-wrote patterns are case-insensitive. These thresholds/patterns are hard-coded in Python, not config.yaml. After truncation it strips a webmail advertising suffix beginning with at least ten underscores and containing a specified provider phrase after at most three intervening lines (`clean.py:68–72`): Yahoo, MSN, Hotmail, private/free email or AOL messenger phrases. The first Enron disclaimer begins with at least five asterisks and extends to the next at-least-five-asterisk delimiter or end; the second confidentiality/privilege disclaimer extends to the first blank line or end (`57–67`). It then removes every `^\s*>` line and collapses runs of excess blank lines (`73–74`). `has_quoted_material` uses the same header rules or the `>` pattern but does not perform the newline normalization done by `authored_text` (`95–97`). For a paper, disclose the top-posting assumption, removal of all downstream content rather than only quoted spans, exact pattern inventory/version, retention of signatures, and that this is not labeled ground truth.



**Line-limit precision:** the `{0,2}`/`{0,1}` wildcard-line limits in `clean.py:26,30,36` are not bounds on the total number of intervening physical lines: adjacent `\s*` can consume arbitrary blank lines. The wording “within two lines” in the source comment is therefore too strict. This was tested, not inferred only from the regex:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from enron_importance.clean import _MARKERS, authored_text
x = 'Original text\nFrom: Alice\n' + '\n'*100 + 'Sent: Monday\nTo: Bob\nEarlier text'
y = 'Original text\nAlice\n05/14/2001 09:00 AM\n' + '\n'*100 + 'To: Bob\nEarlier text'
for text, pattern in [(x, 2), (y, 3)]:
    print(pattern, bool(_MARKERS[pattern].search(text)), repr(authored_text(text)))
PY
```

Both match and return only `'Original text'` despite100 blank lines. This is a documentation/Methods precision issue, not an estimated natural false-cut rate. The actual natural and adversarial boundary checks are reported in Section 4.

### Automated senders and routine messages (`senders.py`)

**Plain language.** A sender is excluded wholesale either because its address resembles a system mailbox or because almost all of its messages start with a few repeated templates. Among other senders, frequently repeated openings are marked routine and removed from text analysis, but retained in the network. These are heuristics, not verified person/automation labels.

**Technical Methods.** `senders.py:24–42` applies a hard-coded boundary-aware local-part regex for no-reply variants, mailer-daemon, postmaster, announce/announcements, administrator/admin, bounce(s), newsletter, listserv, majordomo, helpdesk variants, system, notification(s), alert(s) and mailbox. Templates are the first 80 characters AFTER lowercasing, replacing digit runs with `#`, whitespace collapse and stripping (`34–37`). Per nonnull sender, `sender_profiles` counts all mail and nonempty templates; a feed has at least 50 text-bearing messages and at least 0.90 of those messages in its three most frequent templates (`45–66`; `config.yaml:27–40`). Automated = system-name OR feed. Internal is exact `@enron.com` suffix. Routine = nonempty sender-template combination occurring at least 10 times over the entire retained window, then excluding automated senders (`69–74`; `prepare.py:57`). The final text mask is internal sender AND nonautomated AND nonroutine AND nonempty authored text (`prepare.py:64–67`); 6,348 is an ADDRESS count, not a resolved-person count. The paper must state the 80-character prefix choice, full-window fitting of template frequencies, address-level rather than person-level decisions, and that routine filtering can remove speech acts such as acknowledgments.

### Reply links and threads (threads.py)

Plain language: Emails with the same stripped/lowercased subject are sorted in time. A message is linked to the most recent older message in that subject group that included its sender among the To/Cc recipients and was sent no more than 14 days earlier. Empty subjects are never linked. Connected messages form a thread. This does not use Message-ID relationships, actual quotations, resolved person identities, Bcc recipients, or explicit Re: status.

Technical: `threads.py:26–30` calls `dedupe.normalize_subject` (remove repeated Re/Fw/Fwd prefixes, collapse whitespace, lowercase), allocates nullable integer parent indices and nullable floating response seconds, and constructs a time window from config `threads.max_reply_days=14` (`config.yaml:42–45`). For each nonempty normalized-subject group (`threads.py:32`), stable-sort by timestamp and scan all prior group members in reverse order. Stop when the age exceeds the window; accept the first strict-earlier message containing the current nonempty raw sender string in the union of its To/Cc addresses (`35–46`). No body agreement, current recipient agreement with prior sender, or reply prefix is required. Equal timestamps cannot link. Union-find joins all accepted links; the representative is the minimum integer frame index, not necessarily earliest timestamp (`52–66`). `prepare.py:60` runs linking on all deduplicated messages, including automated/external/routine messages, before defining the text analysis mask. For a paper, call these inferred candidate links, state the address/subject/window assumptions, how missing/empty subjects and aliases are handled, whether response-time analysis excludes forwards/feeds, and validate direct-parent precision/recall separately from same-conversation membership.

### Identity resolution (`identity.py`)

**Plain language.** Each internal sender address is assigned a name using its most frequent usable sender display name. Names are reduced to first and last names and common nicknames are combined. All addresses sharing that reduced name become one identity. Recipients who never send mail are not resolved by this procedure.

**Technical Methods.** `identity.py:22–59` removes angle-bracket/parenthesized routing strings, rejects remaining `@` or `/`, reorders comma-separated last/first forms, lowercases, retains ASCII letters, spaces, apostrophes and hyphens, removes one-character tokens and suffixes jr/sr/ii/iii/iv, then joins nickname-canonicalized first token to last token. The nickname dictionary is hard-coded (`28–41`), includes spelling variants as well as nicknames, and discards middle names. `build_identities` restricts to internal sender addresses, counts normalized names per address, selects the maximum-frequency usable name (ties follow pre-sorted group order), and falls back to the address if none exists (`62–79`). The result contains address, person_key and title-cased key; display_name is synthesized rather than preserving original evidence. The paper must call these inferred entities, document collisions and role/unknown-address handling, distinguish recipient-only addresses, and provide confidence/provenance and error rates for merges and splits.

### Formal-rank labels (`formal_rank.py`)

**Plain language.** A historic spreadsheet supplies job titles, which the project converts into seven ordered levels. The spreadsheet names are matched to inferred identities, with eleven configured name corrections. Contradictory titles for the same inferred person are resolved by taking the highest level for evaluation. This is a title-ordering proxy, not an organization chart or a measure of functional importance.

**Technical Methods.** `formal_rank.py:24–34` fetches the configured 2013-09-18 Internet Archive capture if the local XLS is absent and always verifies SHA-256 `5f67ea06209a51a57c5b05608cc9f56c58c97e62892735eed4232313ff54c071`. It reads XLS without a header as name/title/note, but the note column is not used (`59–65`). Exact configured corrections override `normalize_name`; keys absent from sender identities become unmatched, and blank/unmapped titles have null level (`37–56`). Config levels are CEO6; President5; Managing Director4; Vice President3; Director and Director of Trading2; Manager and In House Lawyer1; Trader and Employee0 (`config.yaml:47–81`). Evaluation excludes unmatched/unleveled rows and groups by key with maximum level (`evaluate.py:58–60`). No organizational-unit context, date of tenure, or reporting-line constraints enters the label. A Methods section must disclose that this ordering is researcher-assigned, how contradictory/unknown titles are adjudicated, the list's selected-custodian coverage, and the distinction between title labels and reporting relationships.

### Network and centrality (`network.py`)

**Plain language.** For internal, nonautomated senders, every retained To/Cc communication contributes to a directed graph. Recipients known under several addresses are combined; unknown recipients remain address nodes. Each message contributes a total weight of one across its distinct nonself internal recipient entities. The pipeline measures how many neighbors each node has, weighted messages received/sent, weighted PageRank, and shortest-path betweenness.

**Technical Methods.** `network.py:69–78` filters sender_internal AND NOT sender_automated but retains empty authored text and routine messages. `build_edges:32–50` unions To/Cc addresses with exact internal suffix, maps endpoints through the sender-derived identity dictionary with address fallback, deduplicates targets AFTER mapping and removes self targets. A message with n remaining target keys contributes 1/n to each directed edge and increments each edge's message count. Messages with no targets contribute nothing. This is not 1/n raw addresses if aliases/self copies occur. For centrality, igraph builds the directed weighted graph, collapses reciprocal edges by summing weights for an undirected graph, uses its unique-neighbor degree and unnormalized all-pairs weighted betweenness with length `1/(summed reciprocal weight)`, and computes directed strengths and PageRank damping0.85 (`53–66`). No betweenness sampling/cutoff is requested. Degree and betweenness are undirected despite the stored edge table being directed. Paper Methods must distinguish entity types, excluded external/subdomain/Bcc communication, denominator conventions, full-period aggregation, and the asymmetric mailbox sampling frame. PageRank damping and graph choices are hard-coded, not config entries.

### Evaluation (`evaluate.py`)

**Plain language.** Every pair of differently titled people is scored: did the network measure put the higher title first? A tie earns half credit. Uncertainty is calculated by repeatedly sampling people, not treating their many overlapping pairs as independent observations. This evaluates association with title levels in the observed graph, not prediction of employee departure or operational dependence.

**Technical Methods.** `evaluate.py:25–42` compares signs of title/score differences over the upper triangle of the matrix, excludes equal-title pairs, awards1 for matching order,0.5 for tied scores and0 otherwise; no eligible pairs returns NaN. It draws n indices with replacement from n ranked people for each of 1,000 replicates using `np.random.default_rng(42)`; all eligible pairs in each multiset are recomputed and the 2.5th/97.5th nanpercentiles retained. Repeated copies of the same person share a title and do not pair with one another; repeated cross-person occurrences receive their bootstrap multiplicity. The same seed is restarted for each measure, aligning replicate index samples (`45–53`). Left-joined missing centrality scores are filled with 0 (`56–63`); CSV rounds to four decimal places (`72`). Baselines are degree, in_strength, out_strength, pagerank, betweenness. These are conditional person-resampling intervals on one fixed graph/label table; they do not resample archive availability, email edges, identity errors, title uncertainty or organizational clusters. State this uncertainty target, the selected label population and any post hoc model-selection inference in the paper.

### Cleaning cross-check (validate_cleaning.py)

Plain language: A reproducible 5,000-message sample is cleaned twice: with this project's regex cleaner and with email_reply_parser. The comparison reports whitespace-normalized agreement, overlap of unique lowercase whitespace-delimited tokens, and whether four selected quotation markers remain. It does not know which output is correct and it does not measure loss of genuine authored text.

Technical: Load raw path/body plus retained processed paths; filter raw rows by path membership; sample 5,000 without replacement with pandas `random_state=42` (`validate_cleaning.py:73–78`, `config.yaml:87–91`). Run `authored_text` and `EmailReplyParser.parse_reply` (`44–53`). Equality collapses all whitespace; token Jaccard uses sets of lowercase whitespace-delimited tokens and gives 1 for two empty strings (`23,33–41`). Four hard-coded presence regexes screen Original Message, Forwarded by, line-initial From/To/Sent/cc/Subject headers, and `>` (`24–30`). Summaries round to four decimals and report agreement, median Jaccard, fraction >=0.9, and each residue prevalence (`56–69`); output JSON plus 40 lowest-Jaccard disagreements (`79–85`). No bootstrap, labeled span precision/recall, signature evaluation, or independent withheld annotation sample is implemented. A paper should say this is agreement/marker detection, not cleaning accuracy. Note the tests explicitly describe some cleaning rules as added after this comparison (`tests/test_clean.py:119–140`), so the fixed sample cannot simultaneously serve as an untouched benchmark.

## 3. Reproduction table and repeatability

### Executed scope and environment

One **fresh archive parse and complete, unmodified `prepare(config)` execution** finished successfully with output paths redirected to scratch. Its raw parquet, processed message parquet, sender parquet and funnel manifest are all **byte-identical to the existing repository artifacts**. This verifies the actual current data against source execution; the cache-bypass finding below is not evidence that these particular files are stale.

Identity resolution, title mapping, edge construction, **full exact betweenness and every other centrality**, evaluation and figure6 were then independently rebuilt in two processes with `PYTHONHASHSEED=101` and`202`. The cleaning cross-check and figure1 render were also repeated twice. A redundant second full Phase 1 pass was started with a hardlink to the fresh raw parse, then deliberately terminated after the first pass completed; **that incomplete pass and its hardlinked raw file are not counted as independent verification**. This audit uses the user's allowance to repeat the relevant stages, not a claim of two complete fresh end-to-end builds. Timing of the first pass includes a deliberate resource-management pause and concurrent jobs; it is not a clean performance benchmark.

Environment reproduction used a source/config/test/lockfile copy outside the repository. `uv sync --locked --group dev` succeeded; original and freshly synced installed-version inventories are identical. Both use Python3.12.13. **All65 tests passed** in the freshly synced environment. Logs and inventories: `uv_sync.log`, `pytest.log`, `environment.log`, `packages_original.json`, `packages_synced.json`. The command was stricter than plain `uv sync`: it refused lockfile updates. Cross-platform reproducibility was not tested.

Core commands, run from the repository:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/check_environment.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/reproduce.py
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=101 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/reproduce.py run1
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=202 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/reproduce.py run2
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/funnel_figures.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/header_audit.py
```

`reproduce.py` still contains the originally planned two-pass loop; on this audit execution PID3037 was stopped with`kill -TERM 3037` only after `reproduction.json` contained the successfully completed first pass. Its completed result is preserved as`run1`; the scope is also recorded in`reproduction_scope.txt`. The pipeline source was not changed.

### Data funnel

Every value in the obtained column below comes from the completed fresh run, not a reading of the existing funnel alone.

| Claim | Obtained | Status |
|---|---:|---|
|Files parsed:517,401|517,401|Match|
|In1998–2002 window:516,359|516,359|Match|
|Outside window:1,042|1,042|Match|
|Undated:0|0|Match|
|Content-duplicate copies removed:262,482|262,482|Match to rule; removal validity audited separately|
|Unique messages:253,877|253,877|Match to rule; residual probable copies remain|
|Additional Message-ID duplicates:0|0|Match|
|Nonempty authored estimates:234,078|234,078|Match; not verified authorship|
|Automated sender flags:312|312|Match; all domains, only 21 internal|
|Routine messages from unflagged senders:11,799|11,799|Match;6,269 internal, not all reports|
|Messages linked as replies:47,130|47,130|Match; not47,130 validated replies|
|Threads:206,747|206,747|Match to inferred-link components|
|Analysis messages:167,905|167,905|Match|
|Analysis senders:6,348|6,348|Match as addresses;5,766 inferred keys under current map|

Additional reproduced funnel fields:112,277 quotation-flagged messages;20,293 sender profiles;9,505 messages from flagged automated addresses. Exact hashes:

```text
messages_raw.parquet  2460bc2b9a5be00d36a1d8769b1b1d072fe7779071eef27d40eba0676f7bd607
messages.parquet      36ab7b73beb8ff61893f4446bfd1bcd5aaf9f7c162e4988b8d19c3100567baa1
senders.parquet       363fdd3a733034f73809fcd16fefa1f1c0157156368edd970f8e193a7790ca85
funnel.json           76e47cd516c7a00f7fb269d33d96ceafbf3410e6112e63653147892490a23519
```

An independent streaming scan of **all 517,401 archive files' top-level headers** found517,401 Message-ID headers and **zero In-Reply-To, References, multipart Content-Type, or attachment-disposition headers** (`header_audit.py`, `header_audit.json`). Thus standard reply headers really are unavailable in this release; proposing their simple reuse would not repair threading. This scan is not a reconstruction of attachment payloads or pre-release original mail.

### Identity and title labels

| Claim | Obtained independently | Status |
|---|---:|---|
|Internal sender addresses:6,455|6,455|Match|
|Resolved people:5,866|5,866 keys|Numeric match; person interpretation fails in verified cases|
|People with multiple addresses:525|525 keys|Match to identity rule|
|Names in title list:161|161 rows|Match|
|Matched title-list names:160|160 rows:149 normalization +11 corrections|Match; not160 distinct verified people|
|Distinct titled people:129|129 inferred keys from 131 matched titled rows|Match under current label policy|

Identity and rank parquet files are byte-identical across both independent reruns and existing files. Independent identity diagnostics and the eleven correction checks were run with:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/identity_rank/audit_identity.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/identity_rank/deep_identity.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/identity_rank/splits.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/identity_rank/mark_taylor_evidence.py
```

### Network and evaluation

| Claim | First full rerun | Second full rerun | Status |
|---|---:|---:|---|
|21,047 people|21,047 nodes|21,047 nodes|Numeric match; not all people|
|220,807 directed edges|220,807|220,807|Match|
|6,285 different-level pairs|6,285|6,285|Match|
|Degree0.647, CI0.568–0.719|0.6474940334;[0.5679609760,0.7193037872]|Same|Match|
|PageRank0.614|0.6140015911;[0.5332828772,0.6845796014]|Same|Match|
|Weighted in-strength0.604|0.6035003978;[0.5250726997,0.6743004272]|Same|Match at quoted precision|
|Betweenness0.567|0.5673826571;[0.4831074615,0.6384996627]|Same|Match|
|Weighted out-strength0.517|0.5170246619;[0.4388527642,0.5947447841]|0.5172633254;[0.4388654782,0.5947707149]|Three-decimal match, **but committed CSV0.5172 becomes0.5170/0.5173**|

The last discrepancy is genuine: floating summation breaks mathematically equal outgoing-message totals. An independent exact integer count gives accuracy**0.5175815434**, CI**[0.4397790954,0.5953736687]**. This does not rescue the near-chance baseline, but it refutes exact repeatability and the implemented interpretation of some ties. See the numerical finding below.

### Cleaning cross-check

Both5000-message runs reproduce the committed summary exactly: whitespace-normalized agreement**76.4%**, median token-set Jaccard**1.0**, and Jaccard≥0.9 for**79.66%**.

| Residue marker prevalence | Project cleaner | email_reply_parser | Status |
|---|---:|---:|---|
|Original Message|0.02%|2.12%|Match|
|Forwarded by|0.02%|6.36%|Match|
|Quoted-header regex|1.08%|7.90%|Match|
|Angle-quoted line|0.00%|0.10%|Match|

Both summary files have SHA-256`dee6b18ded54f9f0af6ec6af2e2f7bf11ba5ec93641a601ecade743cb1a04c9c`. These are marker/agreement measurements, not an authored-span accuracy estimate. The fresh200-message review and detector-negative stratum are reported separately below.

### Is every output deterministic? **No.**

- The fresh Phase 1 artifacts match existing data byte-for-byte. Two identity/rank rebuilds and two cleaning summaries are also byte-identical to each other and existing outputs.
- `edges.parquet` differs across the existing artifact and both reruns because unsorted recipient sets change row insertion order. Sorting by`(source,target)` yields exactly equal endpoints, weights and counts. This is ordering nondeterminism, not a different edge set.
- After sorting centrality by person, degree, in-strength and betweenness are exactly equal. Between reruns, maximum out-strength difference is5.68434e−13 across890 nodes; PageRank difference is3.91354e−15 across21,042 nodes. Those tiny differences change some out-strength tie credits, but do not change PageRank accuracy here.
- Consequently centrality parquet, baseline CSV and figure6 are not byte-stable. Figure 6 PDFs differ; run1 PNG matches the existing PNG, but run2 differs. The actual figure entrypoint was rerun against each regenerated CSV and confirmed the same renderings: changed plotted inputs explain this, not an invented plotting-randomness diagnosis.
- Figure 1 PDF and PNG are each identical across two renders and the existing files (`funnel_figures.json`). Their input counts were subsequently verified by the fresh rebuild.
- Config seed42 is actually passed to the 5000-message sampling and1000 bootstrap resamples. Those repeat correctly on fixed inputs. It does not control Python hash/set iteration order or eliminate floating-point summation effects. There is no sampled betweenness random seed: all nodes are evaluated exactly.

Complete hash/numerical comparison: `network_eval/comparison.json`; numerical outputs: `network_eval/run1/summary.json`, `run2/summary.json`; actual figure entrypoint checks: `figure_main_output.txt`. Do not interpret exact data-file reproduction as proof of construct validity.


### Independent mathematical oracles

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/investigate.py` (stdout `investigate_output.txt`; an unrelated last-step scratch-script error was corrected in `controls.py`; all reported checks precede it).

- Independent scalar edge aggregation, without calling the project's edge builder: same 220,807 (source,target) keys; maximum weight difference 0.0; message-count mismatches 0. Network selection includes 191,814 messages, of which 6,269 are routine; 159,157 contribute at least one nonself internal target; total edge weight 159,157.0.
- There are zero self-loops; all 15,240 recipient-only fallback keys are internal-domain strings, not outside-domain addresses. This checks syntactic domain filtering, not whether CMU's addresses are genuinely Enron employees.
- Independently enumerated all 729 three-person level/score combinations with values 0/1/2: exact agreement with a scalar pair-by-pair oracle, including mixed ties and undefined all-same-level cases.
- Independently tested 1,000 four-person bootstrap resamples against the weighted-unique-pair formula c_i c_j. Exact agreement. Repeated copies of one original person share a level and are excluded from comparison with themselves; their cross-person multiplicities are correctly retained. Duplicated people are **not** a bootstrap bug.
- Hand graph a→b weight2, b→a8, b→c10, a→c1 gives undirected a–b weight10; path a–b–c length0.2 beats direct a–c length1. Code returns b betweenness1, others0, validating inverse weights and reciprocal collapse on a case with a known answer.
- Alias normalization example: To contains self, b, an alias of b, c. Code yields b0.5, c0.5, not four address shares. The actual algorithm weights unique nonself **identities**, so paper wording should say that explicitly.

Further independent numerical oracles: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/numeric_oracles.py` → `numeric_oracles_output.txt`. A separately coded PageRank power iteration using NumPy `bincount` (uniform teleportation, uniform redistribution of dangling-node mass, damping0.85) converged on the full21,047-node graph in113 iterations to L1 step9.828e−14, maximum discrepancy6.155e−14 from committed PageRank. Independent enumeration of **every simple path** for all source-target pairs on 30 random five-node graphs, with exact dyadic lengths and shortest-path tie accounting, matched the project's weighted betweenness with maximum error0. This goes beyond trusting igraph or the project's fixtures.


## 4. Findings ordered by severity

### Severity calibration

No arithmetic defect that destroys the complete baseline result was established. The following are **Major: must fix before person-level Phase 3 inference**; smaller numerical/reporting defects follow as Minor. Calling an issue major rather than critical does not make the data ready. A paper claiming validated functional importance from these outputs would make an unsupported central claim; the intended later research has not supplied that validation.

### Major — M-ID1. The generic missing-address mailbox becomes Don Miller and assigns unrelated people and feeds to him

Code: `identity.py:67–78` ignores unusable names when voting and propagates the winning name to the entire address. Evidence: `deep_identity.py`, `PLACEHOLDER IDENTITY` output. `no.address@enron.com` has **778 deduplicated messages**, all marked `sender_automated=False`. Only 138 have usable normalized names: 98 Don Miller, 17 Mark Evans, 12 Aaron Brown, 3 Clemens Ste, 2 David Oxley, and one each Jennifer Rub, Mark Palmer, Mark Taylor, Donna Lowry, Charla Stuart and Sally Beck. The remaining **640** have unusable names, often corporate feeds. All 778 nevertheless become `don miller`, together with the 161 messages genuinely using `don.miller@enron.com`.

Examples: `maildir/arnold-j/inbox/31.` has `X-From: Public Relations@ENRON`; `maildir/arnold-j/inbox/41.` is `Corporate Security@ENRON`; `maildir/arora-h/inbox/67.` is `Corporate Benefits@ENRON`. These are all assigned to Don Miller, not just a speculative homonym ambiguity. Stored centrality gives the combined Don Miller node degree **491**, betweenness **7,855,152**. The separate network audit now reports a placeholder-exclusion ablation: degree falls **491→128**, while aggregate title-ordering accuracy remains similar. See `network_eval/noaddress.py` and `noaddress_output.txt`; these are not claimed to be his true fully adjudicated centralities.

Impact: person-level language profiles and network structure mix distinct authors and system traffic. Phase 3 models could infer role, topics, and importance from misattributed corporate announcements. Fix: quarantine source-placeholder addresses, distinguish record-specific author identity from mailbox identity, use confidence/evidence fields, and never let an address-level plurality classify a generic missing-address address. Audit all sixteen addresses with multiple usable name keys; the spreadsheet `sender_name_conflicts.csv` lists them.

### Major — M-ID2. Number stripping collapses six different temporary/legal mailboxes into one person

Code: `identity.py:23,54–59` drops digits, then retains only first/last tokens. Evidence: `deep_identity.py` `KEY legal temp`. Addresses `legal.1`, `.2`, `.3`, `.4`, `.5`, and `.7` at enron.com, with original names `Legal Temp 1/2/3/4/5/7`, collapse into one `legal temp` key: **78 messages** (22,16,4,5,1,30). `maildir/haedicke-m/notes_inbox/450.` is signed `Regards, Keegan Farrell`; `maildir/sager-e/notes_inbox/123.` directs contact to Lavon Wilson; `maildir/shackleton-s/notes_inbox/3226.` is signed `Gaby`. The numbered account distinction is erased despite distinct author evidence. The combined node's degree is **68**. The source also contains role nodes `office chairman` (87 messages across four addresses) and `enron chairman` (47 across two), which are not individual employees.

Impact: individual functional-importance and topic-ownership analyses acquire artificial composite people; common-role names are especially exposed. Fix: classify role/shared mailboxes separately, preserve numeric identity-bearing tokens, retain full-name/CN evidence, and refuse merges based solely on generic labels. Do not simply map corporate-office mail to the executive: delegation must be modeled explicitly.

### Major — M-ID3. Display-name-only linking splits aliases even when the original directory identifier provides corroboration

Code: `identity.py:22,48,55–59` discards directory identifiers then uses a small nickname dictionary. Evidence: `splits.py` finds **19 directory CN values associated with multiple person keys**; these are candidate collisions/splits, not nineteen adjudicated people (some are role mailboxes). Concrete high-confidence example: `albert.meyers@enron.com` and `bert.meyers@enron.com` share `/O=ENRON/OU=NA/CN=RECIPIENTS/CN=BMEYERS`, with **44 and 53** such sender headers, yet remain `albert meyers` and `bert meyers`. Examples include `maildir/dean-c/deleted_items/10.` (Albert); all exact CN groups are in `splits.txt`. Stored degrees are **33 and 40**; unioning their graph neighbors yields **58**, excluding the two aliases themselves. Albert Meyers is a labeled evaluation person.

Other corroborated name variants sharing directory CN include Alex/Alexandra Villarreal (`AVILLAR4`), Georganne/Georgeanne Hodges (`GHODGES`), Laura O'Keefe/OKeefe (`LOKEEFE`), Mathew/Matt Smith (`MSMITH18`). Avoid mechanically merging all shared CN: announcement mailboxes use them for multiple authors.

Impact: per-person connectivity and text samples are fragmented, including at least one evaluation target; author-disjoint evaluation can leak through unresolved aliases. Fix: retain directory identifiers as evidence, develop a documented probabilistic or rule-plus-review linker, classify shared-account exceptions, then validate on labeled merge/non-merge pairs and rerun all results.

### Major — M-ID4. Two explicitly distinguished people, Mark A and Mark E Taylor, are merged

Source rule: `identity.py:54–59` drops middle initials, and `:67–78` propagates a modal normalized key over a whole raw address. Independent thread-review lead was then checked with a targeted parquet query, without reloading the corpus. Exact command:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/identity_rank/mark_taylor_evidence.py > /tmp/enron-audit-20260925.Xj3qoO/identity_rank/mark_taylor_evidence.txt
```

`maildir/taylor-m/sent_items/336.` is sent by `.taylor@enron.com`, X-From `Taylor, Mark E (Legal)` with directory CN `MTAYLO1`. Its authored text explicitly requests deletion of **Mark A Taylor** from a distribution and adding the writer as **Mark E Taylor**. The raw quoted chain also shows Mark A forwarding to Mark E, independently establishing two people rather than merely two spellings. The identities table nevertheless maps `.taylor@enron.com` (465 messages), `a.taylor@enron.com` (10), and `mark.taylor@enron.com` (1,966) into the same `mark taylor` key.

All465 `.taylor` X-From headers identify Mark E/MTAYLO1. Nine of 10 `a.taylor` headers identify Mark A with distinct directory CN `NOTESADDR/CN=947B69F4-7B3595B3-86256879-579CBC`; examples are `maildir/taylor-m/archive/2001_06/5.` and `/6.`. The remaining `a.taylor` row, `maildir/neal-s/deleted_items/399.`, identifies Charles A Taylor/CN `CTAYLOR6`, exposing another synthetic-address ambiguity. `mark.taylor` itself includes19 explicit `Mark A Taylor` and40 explicit `Mark E Taylor` headers, as well as generic and legal forms. Thus separating only the three raw addresses would not completely repair the mixed authorship. Counts quantify the **2,441-record combined key**, not2,441 false records; ambiguous generic-name records remain unadjudicated. Evidence: `mark_taylor_evidence.json/.txt` and the raw-body excerpt in `clean_threads/unlinked_quoted_candidate_pairs.json` (record with index233345).

Impact: this is a directly established first/last-name collision between real individuals, beyond role mailboxes/placeholders. It also shows why blindly making thread matching identity-aware can add false recipient matches: Mark A's presence on a list is not proof Mark E received it. Fix: preserve initials and directory identifiers, assign record-level evidence/confidence for synthetic address collisions, adjudicate ambiguous generic rows, and validate negative homonym pairs before alias-aware threading. No graph-repair effect size was computed for this new case.

### Major — M-RANK1. Title conflict handling is unsupported, and source notes contradict coarse assigned levels

Code: `formal_rank.py:46–55` ignores `note`; `evaluate.py:59–60` selects max level. In the raw spreadsheet, `Micheal Swerzzbin` is Vice President while `Mike Swerzbin` is Trader, and `James Schweiger` is Vice President while `Jim Schwieger` is Trader. The corrected identities are reasonable but selecting the higher title is not a verified correction. A primary contemporary source explicitly identified these **same two conflicts** and dropped the Vice President versions after comparison to FERC files: [Diesner & Carley, 2005, p.5 footnote 3](https://jdiesnerlab.ischool.illinois.edu/publications/diesner_carley_siam_enron_03_05.pdf).

The source XLS also says `Sally Beck | Employee | Chief Operating Officer`, `Rick Buy | Manager | Chief Risk Management Officer`, and `Rod Hayslett | Vice President | Also Chief Financial Officer and Treasurer`. The pipeline assigns levels 0,1,3, respectively, without using those notes. This is an observable mismatch between a generic title column and richer source information, not proof of the correct global rank of each subsidiary role. Independently inspected corpus evidence is stronger than notes alone: sender-authored `maildir/kaminski-v/all_documents/11199.` (2000-06-02) and `/5603.` (2000-06-19) contain the signature `Vincent Kaminski / Managing Director`, yet the benchmark assigns Manager, level 1. `maildir/buy-r/sent_items/208.` (2001-03-21) contains `Executive Vice President / Chief Risk Officer and member of VP PRC Committee`, while Richard Buy is level 1. Sally Beck's source messages contain both Vice President and later Managing Director descriptions. The benchmark is not a faithful representation of even its observed historical titles.

Sensitivity (`deep_identity.py`, original measures held fixed): max-title version has 6,285 pairs and degree **0.647494**, PageRank **0.614002**; setting only the two conflicted people to Trader produces 6,235 pairs, degree **0.651724**, PageRank **0.616359**. Excluding them produces 6,081 pairs, degree **0.651044**. Thus this correction does **not** erase the numerical degree result; the issue is invalid confidence in labels and their meaning. `audit_identity.py` additionally finds removing CEO/President rows leaves 121 people/5,301 pairs, degree **0.594793** versus 0.647494 overall. Treat this as subgroup sensitivity, not cherry-picked replacement.

Fix: preserve source rows and provenance, create an explicit conflict/unknown flag, consult dated independent roles or reporting lines, evaluate corrected/excluded alternatives, and report a title-proxy sensitivity analysis. Do not collapse job family and seniority into one unqualified ground truth for all Enron employees.

### Alias-disjointness and custodian checks: findings versus non-findings

All **664** address pairs inside multi-address keys were checked for To/Cc communication-partner overlap (incoming and outgoing). **94** pairs have zero overlapping partners, but only **3** zero-overlap pairs have at least 10 sent messages from both addresses. Sparse observation explains many such cases, so disjointness alone is **not** counted as a false merge. Example candidate `christopher smith`: 35 messages from `a..smith`, five from `christopher.smith`, disjoint partners/custodians, with IT-infrastructure versus valuation subject matter. This warrants adjudication, but the current audit does not establish two individuals. The full `alias_pairs.json` contains overlaps, message counts, custodians and sent-folder counts.

An in-process ablation clearing `NICKNAMES` without editing source yields **5,906** keys rather than 5,866; **41** current key groups pool multiple no-nickname keys. The difference is not simply41 because normalization can also change which key wins an address-level plurality. The tested candidates are listed in `deep_identity.txt`. I did not prove an additional false merge attributable to NICKNAMES alone; the Christopher Smith case remains unadjudicated. Blanket expansion of the nickname table is not the recommended fix because it could worsen homonym merging.

A dominant-internal-sender estimate of mailbox owners covered 148 of 150 custodians, yielded 147 keys, and overlaps **102/129** labeled identities. It is **not a gold owner map**: Kenneth Lay and Jeff Skilling's sent folders contain more assistant-sent mail than executive-sent mail (Lay: Rosalee Fleming497 versus Kenneth15; Skilling: Sherri Sera380 versus Jeff76). `hodge-j` contains Jeffrey T Hodge93 and John Hodge44 with different directory CNs; `hernandez-j` contains Judy442 and Juan215. Consequently the 102 count is an approximate diagnostic, not a final exact estimate of evaluation-set representativeness. Completed network controls use this102 baseline and explicit broader104/106 mailbox-access proxies; their trivial custodian/volume predictors do not match degree's ordering accuracy. See `network_eval/controls_output.txt`. The original hierarchy paper explicitly identifies title-list coverage as core-mailbox-centric: [Agarwal et al. 2012](https://aclanthology.org/P12-2032.pdf), p.161. No claim of population-representative labels is justified.

### Title-source provenance and the eleven corrections

Independent network retrieval command (successful, 25,088 bytes):

```sh
curl -L --max-time 25 --fail -o /tmp/enron-audit-20260925.Xj3qoO/identity_rank/title_refetched.xls 'https://web.archive.org/web/20130918164648id_/http://www.isi.edu:80/~adibi/Enron/Enron_Employee_Status.xls'
shasum -a 256 /tmp/enron-audit-20260925.Xj3qoO/identity_rank/title_refetched.xls
```

It matches the pinned SHA byte for byte. [Agarwal et al. 2012](https://aclanthology.org/P12-2032.pdf) cites the original exact XLS filename; [Diesner & Carley 2005](https://jdiesnerlab.ischool.illinois.edu/publications/diesner_carley_siam_enron_03_05.pdf) reports 161 names/132 titled rows, exactly matching the raw sheet, and the same conflicting names. This strongly corroborates artifact provenance. It is not authentication of every historical title; no publisher-signed checksum or row-level underlying court-document provenance was available.

All eleven target spellings are independently present in sender/X-From evidence. Counts below refer to deduplicated processed messages assigned the target key, not independent evidence of job title:

| Source name → key | Messages | Corpus path and observed sender evidence |
|---|---:|---|
| Micheal Swerzzbin → michael swerzbin |75| `maildir/swerzbin-m/sent_items/1.`; `mike.swerzbin@enron.com`, `Swerzbin, Mike .../CN=MSWERZB` |
| James Schweiger → james schwieger |184| `maildir/schwieger-j/sent_items/1.`; `jim.schwieger@enron.com`, `Jim Schwieger` |
| TimothyHeizenrader → timothy heizenrader |58| `maildir/allen-p/notes_inbox/29.`; `tim.heizenrader@enron.com`, `Tim Heizenrader`; other headers explicitly `Heizenrader, Timothy` |
| Douglas Gilberth-Smith → douglas gilbert-smith |115| `maildir/gilbertsmith-d/sent_items/1.`; `doug.gilbert-smith@enron.com`, `Gilbert-smith, Doug .../CN=DSMITH3` |
| Thomos Alonso → thomas alonso |8| `maildir/salisbury-h/holden_s/4.`; `tom.alonso@enron.com`, `Alonso, Tom .../CN=TALONSO` |
| Cristopher Foster → christopher foster |267| `maildir/dasovich-j/notes_inbox/12101.`; `chris.foster@enron.com`, `Chris H Foster` |
| John Lloldra → john llodra |29| `maildir/baughman-d/deleted_items/360.`; `john.llodra@enron.com`, `Llodra, John .../CN=JLLODRA` |
| Eric Lynder → eric linder |12| `maildir/linder-e/_sent_mail/1.`; `eric.linder@enron.com`, `Eric Linder` |
| Daron Giron → darron giron |1,092| `maildir/giron-d/sent/1.`; `darron.giron@enron.com`, `Darron C Giron` |
| John Giffith → john griffith |312| `maildir/griffith-j/sent_items/1.`; `john.griffith@enron.com`, `Griffith, John .../CN=JGRIFFIT` |
| Harpreet Arora → harry arora |87| `maildir/arora-h/sent/1.`; `harry.arora@enron.com`, `Harry Arora`; raw `maildir/arora-h/inbox/saved_mail/53.` quotes Harry explaining it is a short form of his real name Harpreet |

For Heizenrader, Alonso, Foster and Llodra, retained deduplicated examples were in recipients' folders rather than a custodian's sent folder. They are sender-authored message records, not proof the author inspected an own-mailbox sent copy as config commentary might imply. Harpreet/Harry is an alias rather than a spelling error. None of these verification results validates the attached seniority label.

### Major — Graph is not 21,047 validated people

Evidence: `investigate.py`, stdout lines beginning `network address unresolved`, `node_zero...`; code `identity.py:67–79` creates identities only for senders while `network.py:39–40` uses raw-address fallback for unknown recipients. Among 21,047 nodes, **15,240 (72.41%) are recipient-only addresses absent from the identity table**; only 5,807 nodes match an identity key. **15,301 have zero out-strength**. A node named `center.dl-portland@enron.com` has degree49, in-strength357.983369, and betweenness1,050,047. Actual correspondence and identity evidence are needed before treating role/list addresses as people. `cliff.baxter@enron.com` is a recipient-only node with degree84; `berney.aucoin@enron.com` is a separate unresolved recipient node with degree58 despite a ranked `berney aucoin` identity with degree81. The last example warrants identity evidence before merging, but definitively shows the current node table does not complete recipient-side resolution.

Impact: the title-accuracy computation remains a reproducible calculation on this graph, but whole-network centralities/claims about employees inherit unvalidated receiver aliases, administrative/list nodes, and source address synthesis. Fix: extend resolution to recipient metadata, maintain uncertainty/role-mailbox classifications, and call the current object an address/identity hybrid graph; report sensitivity excluding unresolved and role nodes.

### Major — CMU placeholder aliases directly corrupt a named person's network score

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/noaddress.py` → `noaddress_output.txt`. Code: `identity.py:69–77`, `network.py:39–40`. The identities table maps `no.address@enron.com` to `don miller`; the identity audit supplies independent raw X-From conflicts. Excluding the placeholder as both sender and recipient removes 778 messages from network candidates. Don Miller's degree falls **491→128**; original degree rank is66. Graph becomes21,032 nodes/220,441 edges; 364 node degrees change. Aggregate title degree accuracy changes only **0.647494→0.647971**, and PageRank becomes0.614320. Therefore this is a demonstrable person-attribution failure, not evidence that the entire aggregate rank result vanishes.

Fix: quarantine placeholder/synthetic addresses before person resolution and graph construction; do not assign them to the plurality display name. Keep evidence and unknown identity explicitly.

### Major — Labeled population and mailbox availability are unmodeled selection mechanisms

Commands: `custodians.py` constructs sent-folder candidates; `controls.py` evaluates three operational definitions. Outputs: `custodian_candidates.csv`, `custodian_owners.csv`, `controls_output.txt`, and `controls_*.csv`. Source lines: network selection `network.py:72–75`; fixed-label evaluation `evaluate.py:56–63`.

Define a conservative mailbox-access proxy as the dominant mapped sender in `sent`, `sent_items`, `_sent_mail`, or `_sent`, adding Kenneth Lay and Jeffrey Skilling based on their named mailbox and actual sent records. This is **not** a validated owner roster: assistants share executive mailboxes, 2/150 custodians have no sent-folder data, and conflicting name/owner evidence exists. Under that proxy **104/129** ranked people are linked to corpus mailboxes. Their median degree is201 versus 3 for other graph nodes; labeled-person Spearman correlation of mailbox-file count and degree is0.599. Broader access proxy (top sender candidates accounting for≥10% of sent-folder messages, plus named executives) gives106/129 and median degree198.5 versus 3. Dominant-sender-only gives102/129. Report the range and qualification rather than assert an exact gold count.

Crucial negative control: under the conservative proxy, `is_custodian` accuracy is**0.439220** (95% CI0.390726–0.483697), raw mailbox-file-count accuracy **0.482100** (0.401620–0.557182), compared with degree**0.647494** (0.567961–0.719304). Across all three proxy definitions those trivial accuracies stay below degree. Degree restricted to the 104 proxy-custodian labeled people is0.693660 on 3,896 pairs; nonproxy25 people give0.653680 on 231 pairs. Partial rank correlation of degree/title controlling mailbox size and access is0.40611. These checks **do not support** the hypothesis that the reported ranking accuracy is just raw mailbox size. They do show a highly selected, availability-dependent graph, not a representative measurement of employees' functional importance. Require mailbox-aware validation, documented population boundaries, and title/role strata before generalization.

### Major — Fractional edge weights do not neutralize broadcasts for degree

Command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/broadcasts.py` → `broadcasts_output.txt`, `broadcast_sensitivity.csv`, `largest_recipient_messages.csv`. Code: weighting `network.py:43–46`, unweighted degree line61; docstring lines5–6 and commit `e164fd2` broadly justify weights as preventing broadcast domination.

Among191,814 network messages,3,573 have>50 unique internal target identities,1,329 have>100; maximum889. `maildir/lay-k/sent_items/10.` alone has879 targets. Removing>50-target messages reduces Kenneth Lay's degree1394→458, Jeffrey Skilling1043→380, Sally Beck1441→781. Aggregate accuracy stays0.646539 (full0.647494), so this sensitivity does not refute aggregate ordering. Restricting to one-recipient messages yields0.555688;≤5 recipients0.602546;≤10 recipients0.624662. This reveals that broad contact exposure and rank-related broadcast affordances contribute substantially to the meaning of the score; it does not prove all broadcast contacts are invalid.

Fix: explicitly state that fractionation affects weighted strengths/PageRank/betweenness, not degree, and include recipient-count-stratified sensitivities or a substantive communication-exchange definition before interpreting degree as functional importance.

### Major — Deduplication discards recipient evidence and misses timestamp-shifted copies

**Code:** `dedupe.py:33–50,68–79`; `ingest.py:54–63`. Exact timestamp is part of the content key, but recipients are not. Folder priority selects one entire row; it does not preserve discarded-copy provenance or reconcile recipients.

**Commands/evidence:** from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/data_attacks.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/dedupe_evidence.py
```

The first recomputes content keys for all 516,359 in-window raw rows, sorts by the production folder/path priority, and compares complete To/Cc sets within each key. `data_attack_summary.json` reports **131,371 groups containing multiple copies; 312 groups with conflicting recipient sets; 526 discarded group-recipient assignments, including 449 internal assignments across 236 groups; 194 groups with at least two nonempty, disjoint recipient sets**. Assignments are counted within groups, not distinct employees across the corpus, and some addresses are alternate renderings of one recipient. These are verified information losses, not 449 verified missing people or 194 adjudicated false merges.

Concrete example: `maildir/bass-e/sent/69.` and `/70.` have the same sender Eric Bass, UTC timestamp 2000-11-15 11:02, subject `Fuzzy Math!`, and normalized short URL body. The first is to Jim Schwieger only; the second has seven disjoint recipients, four internal. Both are in the highest-priority `sent` folder, with corroborating separate `_sent_mail` copies. Lexicographic path selection keeps `/69.` and loses the other distribution. This is consistent with separate repeated sends; whether to call it two sends or conflicting exports, the second distribution's per-message contribution is absent. The net effect on unique graph edges requires a recipient-reconciliation sensitivity run, because aliases and other messages can preserve the same contacts. Sally Beck's `sent/1066.` versus `all_documents/115.` instead contains alternate-looking Casandra/Cassandra routing addresses: blindly unioning strings is not a sufficient fix.

A fresh seed20260925 sample of **40 duplicate-key groups** inspected115 parsed rows out of 118 in those groups, at most five copies per group (three groups actually contain six). All inspected parsed body strings are identical and combined To∪Cc sets agree; this does not prove raw MIME byte identity or identical assignment to To versus Cc. Paths typically show familiar sent/all_documents/discussion_threads or cross-mailbox copies. This supports the ordinary-copy interpretation for that sample, not perfect deduplication precision. No naturally occurring short `Thanks` false merge was established; the observed URL/disjoint-distribution case is the concrete counterexample. Seconds in that example are recorded as`:00`; different sends rounded to one minute remain possible.

Missed-copy search: after exact-key deduplication, **14,378 messages** share sender/normalized subject/body with another retained row at a different timestamp. Among adjacent dates within these groups, restricting bodies to more than 100 normalized characters, **1,499 pairs / 2,992 participating messages** differ by exactly1–8hours: 1hour1pair; 2hours28; 3hours253; 4hours1,198; 5hours16; 8hours3. These are candidates, not all confirmed duplicates: legitimate retransmission remains possible. Group sizes above1,500 are explicitly skipped by this diagnostic, and only adjacent pairs are counted; this is not an exhaustive recall estimate. Selected raw-header corroboration is in `timezone_header_evidence.json`; the final reproduction section records its outcome.

The date parser correctly equates `14 May 2001 16:39 -0700` with `23:39 +0000` in a direct probe (`recipient_invariant_example=true`, awkwardly named in the scratch JSON). Seven targeted candidate pairs were re-extracted directly from the archive: all have identical whitespace-normalized full bodies and the same combined recipients, but differing source wall times with **the same numeric timezone offset**. For example, Bill Williams' `maildir/salisbury-h/inbox/1079.` versus `maildir/williams-w3/sent_items/512.` both say June11,2001 with`-0700`, but16:23:06 versus 19:23:06; `maildir/dean-c/inbox/583.` versus`maildir/williams-w3/sent_items/146.` both say October29,2001 with`-0800`, but07:29:56 versus 11:29:56. Different export-generated Message-IDs prevent ID recovery. These are strong probable-copy/source-export timestamp conflicts, not proven parser timezone errors; genuine delivery history is unavailable.

A relaxed NFKC/HTML-unescape/common MIME-soft-break body comparison finds **one additional same-sender/date/subject copy**; ordinary trailing whitespace is already normalized. There are **three null senders** and **zero bodies containing U+FFFD** in the in-window raw table. This does not prove all encoding was correct. Attachment equivalence cannot be validated from missing attachment payloads.

**Impact:** omitted recipient evidence can change edge weights and possibly unique contacts; residual copies can inflate repeated language and cross future train/test boundaries; timestamp shifts can reverse inferred reply order. **Fix:** preserve a copy-membership/provenance table and competing recipient evidence; validate a timestamp-tolerant, content-and-header linkage model on adjudicated examples; separate repeated sends from storage copies; reconcile recipient identities before unioning address variants. Split future train/test data by reviewed near-duplicate/thread groups. Do not simply merge all same-text messages within eight hours.

### Sender audit: inspected scope and commands

Read `src/enron_importance/senders.py`, `prepare.py:48–67`, `config.yaml:27–40`, and all `tests/test_senders.py`. Independently counted templates from processed authored text by streaming parquet, reproduced the entire sender-flag set, and inspected **all 312 flagged profiles** plus the **40 highest-volume unflagged profiles**. For each profile I read volume, flags, first three modal templates and next three templates where available. I then inspected complete messages for suspicious human/mixed accounts, all 15 non-`Start Date:` Pete Davis messages, all 12 HotTap messages, and selected missed-feed and routine examples. This is not a message-level human gold set and does not establish global automation precision/recall.

Commands (repo cwd, no bytecode/repo writes):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/identity_rank/audit_senders.py > /tmp/enron-audit-20260925.Xj3qoO/identity_rank/audit_senders.txt
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/identity_rank/sender_target_checks.py > /tmp/enron-audit-20260925.Xj3qoO/identity_rank/sender_target_checks.txt
```

Evidence: `sender_profiles_audit.json/.txt`, `routine_profiles_audit.json`, `sender_target_examples.json`, the two scripts and their stdout in the same scratch folder. Full profile text was inspected sequentially with `sed -n '1,355p'`, `'356,710p'`, `'711,1060p'`, and `'1061,1250p'`.

The **20,293 profiles/312 flags** reproduce. Of the 312: **287 name-rule only, 21 feed-rule only, four both**; **21** are internal addresses. The stored routine mask sums to **11,799 messages from 286 sender addresses**, of which **6,269 messages are internal**. A separate Counter recomputation independently obtains **11,799**, matching the stored mask; see `audit_senders.txt`. The total includes external senders: “routine messages from people” means “not flagged by this heuristic,” not verified human authors.

### Major S1 — Account-level feed exclusion deletes verified human technical work

`senders.py:64–65` classifies the sender, and `prepare.py:51–52,64` excludes every message from that address. **Pete Davis has 3,933 messages**, top-three coverage **0.980422**, and all are excluded. A full check of the **15** messages whose authored text does not begin `Start Date:` finds **six visibly human replies/notes**, not just more scheduler notices:

- `maildir/guzman-m/notes_inbox/1236.` describes reproducing a production bug, identifying Schedule Crawler as the cause, removing erroneous finals, and asks colleagues to monitor the next import.
- `maildir/guzman-m/notes_inbox/1255.` asks which process causes the false finals in order to isolate and fix the bug.
- `maildir/causholli-m/deleted_items/104.` confirms removal from a mailing list and asks what group the recipient is now in.
- `maildir/platter-p/inbox/54.` is a personal conversation about remaining at UBS.
- `maildir/salisbury-h/read/294.` says `Done` in response to schedule crawler.
- `maildir/williams-w3/schedule_crawler/1431.` apologizes for omitting a recipient from the original distribution.

These are exactly the sorts of expertise/problem-solving/coordination signals Phase 3 proposes to study. The large majority of Pete's account traffic is genuinely templated; that does not make every message automated. Also `ipayit@enron.com` excludes all **112** messages but contains Sally McAdams' individual troubleshooting replies (`campbell-l/inbox/1057.`, `sturm-f/deleted_items/84.`). `helpdesk.hottap@enron.com` excludes all **12** messages by name despite concrete human work signed Deborah/Kim Perez, including checking allocation data and customer identifiers (`blair-l/deleted_items/296.`, `/300.`, `blair-l/reports___scheduled_quantity_report/1.`). These are shared human-operated mailboxes, not individual identities; the appropriate fix is not silently assign them to an employee.

An external specificity counterexample: all three `postmaster@oceanicrealty.com` messages are marked automated although they are individualized rental replies signed Melissa/Sam (`dasovich-j/notes_inbox/1195.`, `/1235.`, `/1498.`). External senders are excluded from the main internal analysis anyway, so this example is a classifier-validation issue rather than a demonstrated change to its core network.

**Impact:** makes exclusions depend on whether an employee sends alerts from their own address, potentially removing precisely the technical operational contributors of interest. **Fix:** classify messages/streams separately from entity type; keep non-template human communications from mixed accounts; retain role/shared-mailbox labels and provenance; add these corpus examples to regression tests and quantify sensitivity.

### Major S2 — Repetition misses obvious system streams, including 927 calendar artifacts in analysis

`outlook.team@enron.com` has **1,473 messages**, **1,472 nonempty authored texts**, top-three share **0.097826**, and is unflagged. Routine filtering removes **500**, leaving **972** nonempty analysis messages. Exactly **1,321** authored texts start `CALENDAR ENTRY:`, and **927** of these survive routine filtering. Example `maildir/blair-l/meetings/100.` is a structured appointment with description/date/time and chairperson Outlook Migration Team. It is not an employee's authored language. Subject-specific descriptions break the 80-character prefix templates into too many types for the top-three rule.

Exact extra count command:

```python
import pandas as pd
m = pd.read_parquet('data/processed/messages.parquet', columns=['sender','authored','routine','path'], filters=[('sender','==','outlook.team@enron.com')])
c = m.authored.str.startswith('CALENDAR ENTRY:')
print(c.sum(), (c & ~m.routine).sum())  # 1321 927
```

Two further verified false-negative mechanisms:

- `perfmgmt@enron.com`: **412 messages, zero automated, 163 routine, 249 retained in analysis**. Inspected examples are personalized performance-review notifications; salutations containing a different employee's name defeat prefix matching. `maildir/arnold-j/inbox/2.` explicitly says attached evaluation forms are for the recipient's direct reports, then names them. This is also a direct organizational-label/identity leakage source, not just generic boilerplate.
- `community-relations@enron.com`: **14 messages, zero automated/routine, all 14 analysis**. Inspected records are structured contribution receipts with employee name/ID/payment fields, so low volume and personalization defeat both rules. No private fields need to be reproduced in the paper; use path `maildir/white-s/itinerary_receipt/3.`.

`arsystem@mailman.enron.com` (**1,191 messages**, top-three share0.594, unflagged;1,160 routine) illustrates the “more than three templates” failure too, but is external under the exact-suffix policy and not counted in the internal NLP set. `melissa.videtto@enron.com` correctly remains a person account yet retains a TRV report notification (`maildir/mckay-b/deleted_items/167.`), demonstrating need for message-level handling, not simply a longer denylist.

**Impact:** text features and network nodes can describe migration software, notification delivery and mailbox-capture patterns rather than employee function. Performance notifications may encode formal reporting relationships explicitly. **Fix:** distinguish structured calendar/report/receipt data from authored prose; detect known event types and boilerplate below sender level, normalize recipient-specific slots, and evaluate a labeled sample of retained as well as removed messages. Recompute the funnel/network after rules are independently validated.

### Major S3 — “Routine” removes speech acts that are the proposed outcome signal

The rule tests only repeated sender+prefix (`senders.py:69–74`), not whether the text is a report or system-generated. Among internal routine messages, **2,520** fall into93 template groups of at most25 characters; **149** are exactly `thanks`, `thanks.`, `thank you`, or `thank you.`. These are observed literal template counts, not all asserted to be valuable business speech acts.

Specific genuine instructions/commitments removed:

- Jeffrey Shankman: **51 `print` +50 `please print`** messages. Examples `maildir/shankman-j/sent/1006.` (Article on Cattle Industry), `/101.` (Summary of EES Bear Trap).
- Jeff Dasovich: **20 `will do.`** messages (`maildir/dasovich-j/sent/107.`).
- Angela White: **19 `approved` out of 22 messages (86.4%)**, including `maildir/donoho-l/deleted_items/101.` (credit request Sempra Energy Trading) and `/75.` (credit request Astra Power). This directly demonstrates highly uneven person-level removal of a role-relevant speech act.
- Mark Taylor: **15 `looks good to me.`** messages, including `maildir/taylor-m/sent/1077.` about vacation.
- Drew Fossum:34 `pls print. thanks df` and19 punctuated variant; Elizabeth Sager:19 `please print`.

The same utterance is retained for a sender using it nine times and excluded for one using it ten times, across the entire research window, regardless of date, context or addressee. Therefore an NLP model of requests, approvals, delegation or responsiveness would lose classes of behavior disproportionately for frequent users. This is a demonstrated selection mechanism, not proof of its final effect size on an as-yet unbuilt model.

**Fix:** preserve human speech acts even when text repeats; flag routine content rather than blanket-remove it; separately classify boilerplate/report templates; report per-person/per-role retained fractions and run speech-act/importance results with and without the filter. Hold out the decision rules from the final evaluation sample.

### Cleaning and threading audit: review protocol and commands

Run from `/Users/jebfarneth/projects/enron-knowledge-decay`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/audit_clean_threads.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/negative_controls.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/supplement.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/thread_probes.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/thread_analysis_subset.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/clean_threads/alias_examples.py
python3 /tmp/enron-audit-20260925.Xj3qoO/clean_threads/record_manual_labels.py
```

The last command serializes the recorded manual judgments; it does not automatically recreate human/Codex judgments from rules. The first command regenerates exact sampled raw/authored pairs and both cleaner outputs. Review commands: `python3 SCRATCH/review.py clean 0 20` (and subsequent intervals), `python3 SCRATCH/review.py thread 0 15` (and subsequent intervals). Full raw/authored bodies, including omitted middles from the display helper, were subsequently inspected directly from the JSON for all 200 cleaner cases. Thread review inspected the portions establishing the parent relationship, not every long newsletter appendix.

### Major: inferred reply links cannot be treated as validated responses

**Code:** `src/enron_importance/threads.py:32–46`; docstring `:3–11`; `prepare.py:60`. The rule accepts any same-subject message sent to the current raw sender in the last14days, without requiring the current message to address the earlier sender, a reply prefix, or quotation evidence. Linking happens before automation/routine exclusion. This is not an implementation departure from the documented heuristic; the defect is treating its outputs as observed reply/response-time ground truth.

**Checked evidence:** simple random sample of 60 of 47,130 links, seed20260925, recorded in `manual_thread_sample60.json` and `manual_thread_labels60.json`:

| Manual class | Count |
|---|---:|
| Supported direct reply |27|
| Forward/relay with the correct source, not a direct reply |10|
| Wrong immediate parent |12|
| Independent broadcast or unrelated topic |4|
| Same-author related update, not a reply |1|
| Uncertain immediate parent |6|

Confirmed direct replies are27/60=45%; counting every uncertain case as valid gives33/60=55%. These are descriptive sample bounds, not a globally calibrated precision confidence interval. Same-conversation linkage is a different, more permissive target and must not be assigned the 45% number. At least16/60 have a wrong immediate parent or independent/unrelated message; forwards and update messages are separate categories rather than falsely calling them unrelated.

The problem is not confined to excluded messages: there are **35,568 linked messages in the text-analysis set**. Forty-five of the 60 sampled children pass that analysis mask; their classes are 22 supported direct replies, 10 wrong immediate parents, 2 independent/unrelated broadcasts, 5 forwards, 1 same-author update, and 5 uncertain. The descriptive direct-reply fraction in this nested subset is 22/45 = 48.9%, or 27/45 = 60% if all uncertain cases are counted. This is a subset of the same sample, not additional independent validation. Evidence: `thread_analysis_subset.py` and `manual_thread_analysis_subset.json`.

Reproducible examples:

- ID44: `maildir/hodge-j/deleted_items/466.` (Carol St.Clair, **Netting agreement**,2001-11-16) is linked to `maildir/heard-m/inbox/255.` (John Viverito). The child concerns Carolina Power & Light/Florida Power/North Carolina Natural Gas; the selected parent lists Dreyfuss/Richardson/Navajo/Unocal. This is a generic-subject collision, not a response.
- ID11: `maildir/dasovich-j/sent/662.` answers a quoted Jacqueline Kelly 14:03 message, addressed to Jeff's external `dasovich@haas.berkeley.edu` alias. The inferred parent is Kimberly Kupiecki 10:16, `maildir/dasovich-j/notes_inbox/959.`, not the quoted person/message.
- ID13: `maildir/bass-e/sent/1335.` quotes Bryan Hull 12/21 14:01 while the selected parent is Matthew Lenhart 12/20, `maildir/lenhart-m/sent/112.`, under **Happy Hour**. Exact pairs and quotes are stored in the sample JSON.
- IDs36 and52 are causally inverted: selected parents already quote the entirety of their purported children. ID52 `maildir/kaminski-v/var/2.` at 22:57 is linked to `maildir/kaminski-v/sent/8.` at 13:00, whose quoted original is David Port12:57. Stored timestamp/duplicate artifacts can therefore turn original messages into apparent responses.
- ID2, `maildir/guzman-m/notes_inbox/581.` linked to `582.`, is a self-addressed **Schedule Crawler: HourAhead Failure** alert linked to the prior hour's independent alert. ID24, `maildir/dasovich-j/notes_inbox/4677.` linked to `4723.`, is a March 28 Enron Mentions digest linked to the March 23 digest. ID29, `maildir/watson-k/e_mail_bin/657.` linked to `maildir/schoolcraft-d/inbox/junk/333.`, consists of two independently distributed copies of a travel-services announcement.

Full paths for every case, classification, and semantic evidence are in `manual_thread_labels60.json`; preserve those along with the report for reproducibility.

**Structural census:**4,150/47,130 linked pairs have identical raw sender strings, and13,908/47,130 do not address the selected parent sender in current To/Cc. These are diagnostic strata, not automatic error counts. Generic groups in `largest_subject_groups.csv`: empty normalized subject17,443 messages/0 links (7,293 quote-flagged); Schedule Crawler623/622 links and the `<codesite>` variant229/226; Lunch302/73; `(no subject)`297/47; Hi278/47; Enron Mentions285/34. Empty/Re:/FW:-only subjects are excluded outright byline32.

**Full rerun sensitivity and runtime:** Canonicalizing sender/To/Cc through the existing identity map before calling the unmodified `link_replies` yields 47,513 links: 383 previously unlinked messages gain a link and 20 existing links change parents. Adding Bcc to the raw recipient union yields **zero additional links** on this corpus. Alias-run elapsed wall time was 365.15 seconds under concurrent audit load; this is reproducible-run timing, not an isolated performance benchmark. The implementation loops over prior messages within subject groups (`threads.py:39–46`) and has quadratic worst-case comparisons within a dense nonmatching group. Empty subjects are explicitly skipped rather than scanned. No hang or exception occurred in either counterfactual rerun. Evidence: `thread_alias_bcc.json` and `thread_probes.py`.

**Missed-link investigation:** From 75,325 unlinked, quote-flagged messages, a fresh sample of 300 (seed 20260926) was searched for exact, whitespace/case-normalized, unique 80-character authored prefixes (at least 12 words) inside the quoted suffix. This yielded 72 candidate predecessor pairs for 57 messages, using 145,248 unique prefix keys; 11 pairs have changed normalized subjects, 12 have empty current subjects, two are alias-only recipient matches, and zero are Bcc-only recipient matches. These are **candidate-source overlaps, not true-reply counts**: they include ancestors, forwarded articles, boilerplate collisions and sources outside 14 days. Global reply recall cannot be estimated from this search.

Four checked candidates are real missed direct replies: candidate 14 `maildir/kaminski-v/deleted_items/1328.` replies to `maildir/kaminski-v/sent_items/929.` (Kevin Presto alias mismatch); candidate 42 `maildir/maggi-m/sent_items/94.` replies to `maildir/maggi-m/deleted_items/2280.`; candidate 60 `maildir/arnold-j/sent_items/25.` replies to `maildir/arnold-j/notes_inbox/81.`; and candidate 71 `maildir/ring-r/inbox/59.` replies to `maildir/ring-r/sent_items/19.`. The last three are omitted solely because the normalized subject is empty despite matching recipient and time conditions. Separate purposive inspection of five alias-added pairs (`alias_examples.json`) confirms five matching quoted immediate sources, including `maildir/allen-p/sent_items/114.` / `maildir/dasovich-j/sent/11755.` and `maildir/campbell-l/sent_items/42.` / `maildir/campbell-l/notes_inbox/509.`. Do not generalize five selected examples to all 383 additions.

The other alias-only candidate is a warning against blindly applying identity normalization: `maildir/taylor-m/sent_items/336.` explicitly asks Janette to **"delete Mark A Taylor and add me as Mark E Taylor"** and quotes a Mark A → Mark E (Legal) forward. The map treats current Mark E as equivalent to broadcast recipient Mark A, even though the raw message itself establishes that they are different people. Candidate 63 links this text to `maildir/nemec-g/inbox/1204.`. Ten reviewed missed-source dispositions are in `manual_missed_link_examples.json`; raw examples and metadata in `unlinked_quoted_candidate_pairs.json`. This confirms at least one false identity equivalence without assuming the alias map is ground truth.

**Impact/fix:** Phase 3 speech-act dependencies and response speed would mix replies, routing/forwarding, repeated alerts, and wrong ancestors. Do not use `response_seconds` as behavioral evidence without a held-out annotated parent-link benchmark and explicit reply/forward classification. Use canonical identities cautiously, recover quoted sender/time/body where possible, distinguish thread membership from direct parent, and abstain on low-information generic subjects. Exclude feeds before response-time analysis. Test sensitivity to alias, window, and empty-subject handling. Do not simply add Bcc to improve recall without privacy/recipient semantics and false-positive checks.

### Major: quote truncation drops real inline answers and misses flat headers

**Code:** `clean.py:77–92` cuts all content after the earliest marker. `:29–31` is broad Lotus detection,`:50` cuts at Received/Return-path/Content-transfer-encoding. No reconstruction of bottom-posted or interleaved answers exists.

**Fresh detector-positive sample:**200 random messages from 112,277 `has_quoted=True`, seed20260925. Seven retain quoted headers (3.5%), zero retain confirmed quoted-body prose, one drops confirmed substantive current-author prose (0.5%), and one has ambiguous copied-table authorship. This is conditional on the cleaner itself detecting quotation, so it cannot establish corpus-wide quote recall. Exact full-case labels: `manual_clean_combined.json`.

- Definite false cut ID49, `maildir/shackleton-s/sent_items/27.`: starts with an Original Message block; genuine inline Sara replies are marked `[Shackleton, Sara]`, including **"not yet"** and a sentence about engaging bankruptcy lawyers. Both cleaners produce the empty string. This is a real example, not just a synthetic bottom-posting attack.
- ID20, `maildir/farmer-d/sent/369.` retains the quoted Aimee Lannou name/date line after Daren's own message. ID82, `maildir/shackleton-s/notes_inbox/4.` retains Spanish original-message/De/Para/Fecha/Asunto headers; email_reply_parser removes them. The otherfive cases are IDs140,141,162,174,186, recorded in the combined JSON.

**Fresh detector-negative analysis stratum:**40 messages sampled seed20260927 from 88,186 internal/nonautomated/nonroutine/nonempty analysis messages with`has_quoted=False`. Full raw/authored inspection found one full multi-author chain retained by both cleaners: `maildir/shackleton-s/nelson/336.`. Its Lotus headers have name/date/To/cc/Subject on a single line. Authored output is4,132characters versus 4,156 raw characters, with several older messages credited to the current sender. This is1/40=2.5% in a small, restricted sample, not a precise global error estimate. Two additional messages retain explicitly copied non-email sources (contract text and third-party memorandum); these are not classified as failed email-quote detection but matter to an authorship/topic-ownership construct. All40labels: `manual_unflagged_labels40.json`.

**Targeted Lotus/Received checks:** `marker_diagnostics.json` counts 34,694 Lotus pattern 3 matches and 14,100 earliest cuts; 1,550 transport-header pattern 8 matches and 888 earliest cuts. Inspected 20 seeded examples per pattern, drawn from the first 250 earliest-hit examples saved in archive order: 0 confirmed natural false-boundary cases among these 40. Exact boundary contexts and manual dispositions are in `manual_marker_boundaries40.json`, reproduced by `record_manual_labels.py`. This is a convenience-stratum check, not a random population prevalence estimate. It does not invalidate the broader false-cut finding above. Synthetic negative controls do demonstrate overbreadth: a current-author `Received: from supplier, 20 barrels.` line deletes itself and following text, and `Meeting agenda\n05/14/2001 09:00 AM\nTo: operations staff\n...` loses all content. These controls are in `negative_controls.py/json`; do not report their occurrence as a measured corpus rate.

**Impact/fix:** Inline answers can disappear entirely, while undetected chains inflate a sender's subject-matter contributions and reproduce other employees' text/titles. Preserve spans and provenance rather than assuming the top prefix is all authorship. Create held-out span annotations covering inline/bottom replies, flat/foreign-language headers, date-like prose, logs, signatures, and copied documents; report retention recall and contamination separately. Until then, call this `estimated top-posted text`, not verified sender-authored text.

### Major for Phase 3: title/signature and copied-source leakage remains

**Code:** `clean.py:83–92` does not remove ordinary signatures. Keyword screen over167,905 analysis messages finds6,761 messages (4.03%) from 1,503resolved people with a broad job-title term, and3,895 messages from 1,068 people have one within the last8lines. This is a **keyword screen, not a measured own-title rate**. Exact known ground-truth title phrases appear somewhere in205 messages from 63titled identities; those may be discussion of somebody else's title and must not be called own signatures.

**Stronger checked lower bound:** `supplement.py` uses four literal name-followed-by-title signature patterns and a matching sender surname: Vincent Kaminski/Managing Director19 analysis messages; Sally Beck/Vice President1; Sally Beck/Chief Operating Officer2; Sue Nord/Sr.Director19. Thus at least41 analysis messages fromthese3 people contain explicit own-name/title signatures. Full paths and patterns in `literal_signature_counts.json`. Examples include `maildir/kaminski-v/all_documents/11199.` and`5603.`. This is a conservative selected-pattern lower bound, not exhaustive classification, and title wording need not equal the formal-rank label (Kaminski's label mismatch is separately audited).

The detector-negative sample also retains Cheryl Nelson's Senior Counsel title inside a multi-author quoted chain and an8,000-character John&Hengerer memorandum copied under another sender. Clean-sample ID1andID80 are signature-only retained text; such messages are nonempty without substantive contribution. Title prediction could therefore learn identity/rank vocabulary or circulating documents rather than functional importance.

**Fix/tests:** Produce signature-stripped, identity/contact-redacted and quoted-document-redacted ablations. Use person-disjoint splits for unseen-person generalization, and past-only, date-disjoint evaluation for temporal claims; report a title-keyword-only baseline and name/contact-only baseline. Test masking against a manual own-title sample rather than treating every occurrence of manager/director as leakage. Retain unredacted source for audit, but not as an uncontrolled feature source.

### Major evaluation limitation: independent cleaner agreement is not a gold standard

**Code:** `validate_cleaning.py:25–30,44–69`; `tests/test_clean.py:119–140`. Four residue regexes are format markers, not quoted-span labels; no retention check is included. `negative_controls.py` obtains zero residues from an empty-string cleaner, which still agrees with email_reply_parser on 4.22% ofsample5000. A destructive cleaner can therefore win every residue column. `README.md:77–78` and commit`7e8f228` acknowledge adding rules identified from the same cross-check, so the final fixed sample is development data, not a pristine external validation set.

**Fairer check actually run:** both cleaners were compared to full raw bodies on the fresh200 cases. Project:7/200 any quote residue (all headers),0/200 confirmed quote prose,1/200 substantive authored deletion. email_reply_parser:80/200any residue,35/200quote prose,1/200substantive authored deletion. One authorship ambiguity inboth. Four email_reply_parser signature/device-footers removals were kept separate, not automatically counted as body-text errors. This suggests relative advantage on the observed detector-positive formats, while the independent detector-negative40 shows both fail a flat-header chain. It does **not** validate a global accuracy rate or prove superiority on all message types. Neither review was blinded/human gold.

**Fix:** replace "less quoted material" with the measured "fewer selected quotation markers" unless supported by held-out annotation. Evaluate blinded span precision/recall or sentence labels for current author, earlier email, boilerplate and signature; stratify by export format and empty outputs. Freeze cleaner rules before final test annotation.

### Major — Cached parsing bypasses verification and provenance; the provided default runner is incomplete

**Code:** `prepare.py:29–32,73–79`; `download.py:26–56`; `Makefile:6–16`. The manifest writes the *configured* archive SHA, even when the archive was not checked on that execution. A preexisting raw parquet is accepted without a hash binding to archive, parser code, or config. The default Makefile target does not run identity/rank/network/evaluation/cross-check/figures.

**Reproduced failure:**

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/cache_probe.py
```

This uses the project's tiny test-corpus constructor strictly in scratch, runs preparation, then replaces the scratch archive's424bytes with 22bytes. Direct `ensure_corpus` correctly exits on the size mismatch. `prepare` nonetheless reuses the cache, succeeds and returns the same manifest (`cache_probe.json`: `prepare_reused_cache_and_succeeded: true`). No real archive was changed. This proves a stale/unverified-cache path; it does **not** establish that the supplied real parquet is stale. The fresh real-corpus rebuild separately checks that.

**Impact/fix:** changes in parser, archive or extraction policy can silently leave old rows under a misleading source hash. Add input/output/code/config provenance and dependency-aware invalidation; verify the archive/cache binding on cached runs; make the documented end-to-end command actually include every reported artifact.

### Minor — Floating arithmetic breaks intended ties and changes the reported evaluation across processes

Commands: `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=101 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/reproduce.py run1`; analogous run2 with `PYTHONHASHSEED=202`; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -u /tmp/enron-audit-20260925.Xj3qoO/network_eval/float_ties.py`. Evidence code: set iteration `network.py:38–45`, igraph strength accumulation `network.py:63`, exact subtraction/sign tie test `evaluate.py:28,33`.

One eligible message contributes total outgoing weight exactly1 mathematically, so weighted out-strength is an integer number of contributing messages per source. Floating sums depart from integers by up to 1.97815e−11. Among the 6,285 evaluated different-level pairs,14 have equal integer totals; run1 treats11 of those as strict orderings. For example Geir Solberg(level 0) and Geoffrey Storey(level 2) both have72 contributing messages: committed scores are72/72 but run1 scores72.00000000000001/72, changing the pair's credit0.5→0. Michael Curry(level 1) and Michael Swerzbin(level 3) likewise change59/59→59.00000000000001/59, credit0.5→0.

Consequently committed out-strength accuracy is0.5171837709 (CSV0.5172) while run1 gives0.5170246619 (CSV0.5170), despite the sorted edge lists matching exactly. Using mathematically exact integer totals gives0.5175815434, CI0.4397790954–0.5953736687. The near-chance conclusion is unchanged; exact reproducibility and the claimed half-credit tie semantics are not. Fix: compute outgoing counts as integers directly; stabilize edge/node order; define scientifically justified numerical tie handling for other floating scores; add cross-process regression tests with equal true totals distributed across different numbers of edges.

The integer totals were subsequently **independently counted from source processed messages**, without using graph weights or rounding: count one unit for each internal/nonautomated message containing at least one nonself internal To/Cc target. Total159,157; zero mismatches between those integer counts and rounded floating out-strength over all 21,047 nodes. Full evidence table is `exact_outgoing_counts.csv`. Run2 confirms the nondeterminism with out-strength accuracy0.5172633254 (CSV0.5173), CI0.4388654782–0.5947707149.

### Minor — Highest point estimate is not demonstrated superiority

Command: `investigate.py` output `degree_minus_pagerank_bootstrap`. Same1,000 paired person resamples/seed42 as shipped. Degree−PageRank=**0.033492**, percentile95% difference CI**−0.009661 to 0.072080**. README58–60 and commit953b4b3 call degree “strongest”; accurate only as highest observed point estimate, not demonstrated superior predictive performance. Fix wording or show paired differences; do not compare overlapping marginal intervals informally.

### Minor — Passing tests are not corpus validity, and two weak assertions survive deliberately wrong implementations

**Command:** `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/test_mutations.py`; code inspected in `tests/test_evaluate.py` and `tests/test_identity.py`. The scratch script changes only imported test namespaces in memory, not any repository file. The existing bootstrap test still passes a stub that always returns `(0,1)`. The identity-builder fixture still passes when the implementation takes the first message per address, ignoring the required normalized-name modal rule. Results are in `test_mutations.json` (both mutations pass).

These do not show that the actual bootstrap or modal rule is wrong: independent oracle checks support the implemented bootstrap arithmetic. They show that these tests cannot detect important wrong alternatives. Likewise, the real Pete Davis human-message exclusion passes a synthetic test that uses his address as a wholly templated sender. Tests of the intended regex outputs are not empirical validation of message authorship, identity, title correctness, thread precision or population representativeness.

**Fix:** assert independently calculated expected intervals/weighted resample results and fixtures with disagreeing first/modal names; add adjudicated real-corpus regression cases for each failure above; maintain a frozen, separately sampled evaluation set rather than repeatedly converting discovered failures into development-only fixtures.

### Additional test coverage checked

`tests/test_identity.py:6–43` comprises hand-made display formats, unusable strings, one constructed alias merge, suffix stripping, and three nickname cases. It does not test placeholder addresses, multi-author addresses, numbered role accounts, conflicting directory identities, false-split CN evidence, or majority confidence. Its suffix test deliberately expects `John Smith III`→`john smith`; it would pass even if two generations were wrongly merged. No data-based error bound follows from those fixtures. `tests/test_formal_rank.py:12–30` tests normalized matches, one supplied correction, and missing/unmatched entries; it does not test conflicting title rows, ignored notes, dated roles, manual correction authenticity, or representativeness. Concrete fixes should add adjudicated real-corpus regression cases, not merely synthetic strings engineered to satisfy the current implementation.

`tests/test_senders.py` verifies hand-made successful string matches, repetitive feeds, low-volume behavior, empty forwards and a human with a minority report template. It has no test protecting minority human messages once a mixed account crosses the feed threshold, no personalized calendar/HR notification case, no human helpdesk case, and no repeated human approval/delegation case. `test_feed_split_across_three_templates_is_flagged` includes60 templated messages and40 distinct note-like messages and intentionally expects whole-account exclusion at feed_share0.5. `test_person_with_weekly_report_keeps_their_other_messages` tests12 reports plus40 human questions below the production0.9 threshold; it does not test an above-threshold mixed account. `test_templated_feed_is_flagged_but_a_person_is_not` uses Pete Davis' real address with invented scheduler messages and confirms account exclusion, so it would pass while the real corpus human-message loss persists. These tests validate the implemented heuristic, not its safety for human speech-act retention.

Docstring `senders.py:9–15` says people do not repeat a handful of templates and that people sending routine reports are kept. Actual code has no such guarantee: a sufficiently template-dominated mixed account loses all human work (Pete Davis), while real approvals/instructions are discarded as routine. Labeling all unflagged addresses “people” and all flagged ones “automated” is overstated without entity-type and message-type validation.

No claim that every312 flagged sender is wrong, no estimated global false-positive rate, and no assertion that fixing these issues must erase baseline degree accuracy. Full labels for312 addresses would require an adjudicated message-level sample; this audit establishes concrete counterexamples and predictable selection biases.

`tests/test_network.py` has3 synthetic graph tests (lines11–42); `tests/test_evaluate.py` has5 arithmetic/bootstrap/table tests (lines8–39); `tests/test_figures.py:14–22` checks ordering/rendering. The graph tests correctly check inverse-weight direction (not merely names); my independent hand case confirms it. Missing coverage: recipient-only aliases/role nodes/placeholder addresses; end-to-end sender filtering; repeat-process byte/numeric determinism; genuine corpus-owner cases; title conflicts and missing-centrality zero filling; bootstrap coverage assumptions or paired differences. A source-placeholder name collapse can be catastrophically wrong for a person while all existing network tests pass. Repeating one deterministic CI and checking it brackets one synthetic estimate is not a coverage test. Add independent corpus regression cases and avoid treating passing fixture tests as validation of identity or construct validity.

`tests/test_clean.py` contains single synthetic format examples and missing-body checks, including headers/disclaimers/ad footers. It does not include a naturally occurring annotated evaluation set, bottom-posted replies, interleaved answers after an Outlook/Lotus delimiter, or ordinary authored text that mimics the date/To or Received patterns. `tests/test_threads.py:10–57` checks a simple chain, Cc, raw nonrecipient rejection, an out-of-window reply, and latest eligible selection. It does not assert alias resolution, empty-subject behavior, generic-subject false links, self-addressed messages, Bcc, or quotation-confirmed parent identity. `tests/test_validate_cleaning.py:6–16` only checks three trivial Jaccard cases and agreement on two simple messages; it cannot detect an overaggressive cleaner that deletes substantial genuine text elsewhere.

### Documentation and commit-claim ledger

Read commands: `nl -ba README.md`; `nl -ba config.yaml`; `cat Makefile`; `git log --format='%h %s%n%b' -- src/enron_importance tests config.yaml README.md Makefile pyproject.toml`. Audit basis is HEAD `8c595e7e6cc842260843d49547f20b796994db6a`, not the legacy implementation. Historical commit counts refer to their historical versions; a different current number alone is not evidence they were false then. The following are unsupported/overbroad current claims or historical promises that the current implementation does not establish.

| Location | Claim / problem | Checked evidence and defensible wording |
|---|---|---|
| README:13–17; commit `6f6fc96` research description | Says the project measures functional importance and validates it using contacts after an employee leaves, in present tense. | `rg --files src/enron_importance` and source review find no departure labels, departure-event design, contact-outcome model or functional-importance validation. Phase 1–2 produces text estimates, a graph and title association only. Say these are research objectives, not results. |
| README:8–9; config:1–2; `Makefile:6–16`; commit `6a83f6c` | Complete regeneration implied through `make`. | `make all` calls setup, tests and `prepare`, not identity/title/network/evaluation/cross-check/figures. Existing cached raw parquet bypasses archive verification. Add a complete dependency-aware runner and source/config/code hashes; do not infer actual stale numeric results just from timestamps. |
| README:26,48–49; commit `67ebf20` | Authored text is described as text written by the sender; NLP will see only sender-written words. | Fresh quoted-message review shows leftover quoted names/text and removed sender answers. Rename to estimated authored text and disclose error/uncertainty. |
| README:49 | 312 automated feeds and 11,799 routine report messages phrased as validated categories. | `sender_profiles` marks name-rule OR template concentration over all domains; `routine_messages` labels repeated first80-character templates, not semantic reports. The counts are heuristic flags, not a labeled classifier evaluation; sender-address flags include external accounts. |
| README:30–32; `network.py:3–6`; commits `87191ca`, `e164fd2` | Addresses resolved to people; a 21,047-person network. | 15,240 nodes are unresolved recipient-only addresses; role mailboxes and the no.address→DonMiller merge are directly observed. Call this a partially resolved address/entity graph until corrected. |
| README:55–62; commit `582da91` | The title list is treated as ground truth. | Source notes, conflicting duplicate rows and own-message signatures contradict several assigned levels. Call it a noisy, time-agnostic title proxy; validate conflict policy. 160 matching rows is not160 distinct verified people. |
| README:58–60; commit `953b4b3` | Degree is the strongest baseline. | Highest observed point estimate is supported, superiority is not: paired degree−PageRank difference .033492,95%person-bootstrap interval[-.009661,.072080]. Use 'highest point estimate'. |
| README:59–62 | Numerical comparison to Agarwal's79.3% core result. | The cited value is correct: [Agarwal et al.2012](https://aclanthology.org/P12-2032.pdf), Table1,79.31% on440 core reporting-line pairs, versus6,285 different-title pairs here with different graph/label construction. This is related work, not replication or a directly comparable benchmark. Their database is stated to be available by contacting authors; lack of a working public download was not proof of permanent unavailability. |
| README:66–78; commit `61fdf7b` | 'Independent' cleaning check and less quoted material. | Independent software is used, but the four residue regexes favor the author's targeted rules; the same seed42 sample informed changes (`tests/test_clean.py:119–140`, commit `7e8f228`). Agreement and fewer selected markers reproduce; cleaning accuracy and preserved authored spans do not follow. |
| README:67–68; commit `61fdf7b` | Exactly identical text for76.4%. | `validate_cleaning.py:33–48` compares whitespace-normalized strings, not exact bytes; report 'whitespace-normalized agreement'. Median token Jaccard100% can occur with different sequence/counts because it compares token sets. |
| README:90; config:1–2; commit `23d4d38` | Every parameter is in config. | Hard-coded folder priorities, prefix/cleaning regex lengths,80-character templates, nickname/suffix rules, PageRank0.85, bootstrap percentiles,0.9Jaccard threshold and figure scales are in source. Say which tunables are configured and version the rest. |
| `senders.py:9–12`; commit `2506e01` | People do not produce a few repeated templates; people who send reports stay in analysis. | No reviewed classification truth supports that universal statement; whole-address feed exclusion can discard minority human mail, and routine detection also removes genuine speech acts. Distinguish message automation from mailbox author identity and validate both. |
| `threads.py:4–11`; commit `539be00` | Qualifying subject/recipient/time match called a reply and response time. | The function establishes only a candidate chronological link; no quotations, aliases, return-recipient agreement or reply prefix is checked. Fresh pair review and counterfactual links expose failures. Call it inferred candidate-parent delay until validated. |
| `network.py:5–6`; commit `e164fd2` | Fractional weights keep broadcasts from dominating. | True only for specific weighted contributions. Degree ignores weights; removing>50-recipient mail reduces Lay1394→458 and Skilling1043→380, even while overall degree accuracy stays.646539. Qualify the metric-specific effect. |
| `network.py:8`; commit `e164fd2` | All measures exact. | Full betweenness uses no sampling/cutoff and passes an inverse-weight hand graph; PageRank/strengths are floating-point numerical computations. Say exact all-source betweenness versus sampled betweenness, not mathematical exactness of all outputs. |
| config:66–69; commit `582da91` | Eleven 'spelling corrections', each checked against own sent mail. | All targets have corpus sender evidence; Harpreet→Harry is a corroborated alias, not spelling. Several retained evidentiary messages sit in recipient mailboxes; this audit cannot establish what the original reviewer inspected. Store the actual evidence and distinguish alias resolution from title validation. |
| commit `61ec27c` | Remaining quote formats caught; residual rate0.0% on 20,000 messages. | This is a historical marker-sample claim without saved sample labels/paths/reproduction manifest in the current tree. Current5000 sample has quoted-header regex residue1.08%, which is not directly comparable without the old exact marker/sample. Do not present the historical0% as general cleaning accuracy. |
| commit `c81bfc9`; README:86 | Environment installs identically on any machine. | Fresh local locked sync reproduces installed package versions; Python is specified as3.12, not a patch/build, and wheels/OS/fonts differ by platform. No cross-platform reproduction was performed. Local package reproducibility is verified; universal byte identity is not. |

The current numerical claims are addressed individually in the reproduction table rather than automatically labeled unsupported. Historical phase1 counts in `e9ec213`, intermediate identity counts in `87191ca`/`221defd`, and the obsolete one-template description in `69f2c07` were read as historical records; the audit did not rerun every historical commit. Legacy-only commits are outside the requested scope. Tool tests, source inspection and modern reruns do not reconstruct an undocumented historical manual-review process.


## 5. Phase 3 leakage risks and required tests

No Phase 3 text model was run, so these are demonstrated input pathways and testable risks, not an assertion of an already measured downstream leakage effect.

| Pathway verified in this audit | Required test before an importance/rank claim |
|---|---|
| Own-title signatures survive:41 literal name/title cases across3 selected people;6,761 analysis messages contain a broad title term. | Annotate own versus others' titles; compare full text against signature-, name-, address-, title- and contact-redacted text. Include title-keyword-only and identity-only baselines. Do not label every occurrence of “manager” as leakage. |
| Incorrect/missing aliases and composite accounts: Don Miller placeholder, Legal Temp numbers, Mark A/Mark E Taylor collision, Albert/Bert Meyers split. | Freeze reviewed identity clusters. Use person-disjoint rather than address-disjoint splits for claims about unseen employees; known-employee temporal prediction may share people but must use past-only evidence. Evaluate with uncertain/shared entities excluded and separately typed. Make identity resolution independent of target labels. |
| Undetected quotations, copied memoranda and residual timestamp-shifted copies. | Annotate attributed text spans; keep near-duplicate families and threads in one split; quantify overlap across folds using normalized and near-duplicate content hashes. Compare top-posted estimates with span-aware extraction. |
| Outlook calendar records and personalized HR notices survive; a performance message explicitly names direct reports. | Exclude or separately model administrative event records; test a metadata/notification-only baseline. Such records may reveal labels directly rather than express an employee's functional contribution. |
| Custodian availability is highly uneven:104/129 labeled identities under a conservative proxy; graph nodes are mostly recipient-only fallbacks. | Evaluate mailbox-access-matched/stratified sets and leave-mailbox-out sensitivity; forbid path/folder/custodian from uncontrolled features; report realistic target population. The tested trivial custodian predictors did **not** match degree's ordering accuracy. |
| There are129 labeled identities and6,285 overlapping different-level pairs, not6,285 independent people. | For supervised rank comparisons, hold out people before forming evaluation pairs when claiming unseen-person generalization. Keep tuning separate from final evaluation and bootstrap at the appropriate entity/cluster level; a random pair split can put the same person's texts and labels on both sides. No Phase 3 pair-split implementation exists yet to audit. |
| Routine/automation flags use all 1998–2002 messages; identities pool all dates; the graph is aggregated over the whole window. | For any temporal prediction, rebuild identity evidence, templates, thresholds and graph features using only pre-cutoff information, then apply frozen rules forward. Compare with the current retrospective version. A full pre/post threshold sensitivity was not run here; the full-window behavior is explicit in the inspected code. |
| Repeated approvals, instructions and acknowledgments are removed, while mixed-account problem-solving text can vanish entirely. | Report retained fraction by person/role and speech-act class; run text models with/without human repeated-utterance filtering. Retain the original flag rather than irreversibly dropping evidence. |
| Formal-rank labels are noisy, undated title levels, not a functional-importance outcome. | Use dated, independently corroborated title/reporting-line labels for rank evaluation. If email signatures help adjudicate labels, segregate/redact that labeling evidence before evaluating text-based prediction. Define a separate importance criterion before modeling. Preregister exclusion/conflict policies, unit scope and label sensitivity. |
| README describes post-departure validation, but current code has no departure labels or outcome analysis. | Before that future design, distinguish departure from archive truncation, mailbox disappearance and organization-wide shocks; require comparable observation windows and negative-control dates/people. This audit does not claim those future confounds have been resolved. |

## 6. What this audit could not verify

- There is no independently adjudicated complete author, identity, hierarchy, reply-parent or functional-importance gold standard. Manual email judgments in this audit were made by Codex agents; two nonoverlapping review partitions are **not** human annotation or inter-rater agreement. Preserve examples and obtain independent expert adjudication before publication.
- The200-message cleaning sample is random within the cleaner's own quotation-positive frame, not a population-wide quote-recall sample. The additional40 detector-negative analysis cases and40 targeted Lotus/transport cases do not yield precise global error rates. A lack of an error in a small stratum is not proof of absence.
- The60-thread sample supports direct-parent precision diagnostics, not global true-reply recall. Alias/Bcc counterfactual counts indicate changed links, not verified recovered replies; changed-subject and omitted-message recall need separate labeled data.
- Most1–8hour duplicate candidates were not individually adjudicated. All312 conflicting-recipient groups were counted but not semantically resolved; raw address loss is not an exact count of lost employee contacts. No comprehensive attachment comparison is possible with absent attachments.
- All eleven corrected title names have corroborating corpus evidence, but underlying job-title tenure, subsidiary/unit scope, all reporting lines, complete custodian ownership and every spreadsheet row's primary provenance remain unverified. Byte-identical archive retrieval authenticates the pinned file, not each historical fact.
- The person bootstrap's arithmetic passed independent checks. Its nominal population coverage, including correlated organizational units, uncertain labels/identities and a selectively observed graph, was not established. There is no evidence here sufficient to call the intervals categorically too narrow or too wide.
- The pipeline has no empirical functional-importance result yet. Reproducing rank association does not validate expertise, replaceability, employee efficiency, causal importance or post-departure effects. The audit does not prove the association disappears after corrections; several targeted corrections leave it similar.
- Historical commit statements were checked against current code, saved artifacts and available source evidence; every historical commit was not rebuilt. Undocumented prior manual samples cannot be reconstructed. `legacy/` was not audited.
- Environment reproduction was local to this macOS/Python installation. Cross-platform numerical/figure/byte identity and other Python3.12 patch builds were not tested. The actual input archive was freshly parsed once; subsequent downstream reruns can reuse that same fresh immutable parse. The reproduction section distinguishes independent work from cache reuse.
- No repository code, config, tests, input data or existing results were repaired. The requested report is the only authorized new repository artifact; scratch scripts and evidence live outside the repository and should be preserved if the audit is to be reproduced later.


### Repository-integrity verification

`verify_unchanged.py` compares SHA-256 values for every preexisting tracked file and all preexisting data/results files against `original_hashes.json`, checks HEAD, and records final git status in `final_integrity.json`. The only new repository artifact is this uncommitted report. The preexisting untracked `results/cleaning_crosscheck_disagreements.csv` is preserved; source, tests, config, data, results and git history are unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python /tmp/enron-audit-20260925.Xj3qoO/verify_unchanged.py
```
