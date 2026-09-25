# Response to the 2026-09-25 gold-standard audit

The audit ([report](gold_audit_codex_2026-09-25.md)) reviewed the evaluation
against the Agarwal et al. (2012) hierarchy gold standard at commit
`e476f68` and concluded it could not be reported as it stood. Its evidence
archive is kept locally, not in git, because it contains records derived
from the privately shared release. Numbers below come from the full rerun on
branch `rebuild/reaudit-fixes`.

| Finding | Status | Commit | Change and effect |
|---|---|---|---|
| C1 labels assigned to the wrong human; some release records merge several people's positions | fixed for matching; open for the release's merged records | `b96e663` | Executives' release records list their assistants' addresses, so employees are now matched by their principal name (the name matching their mailbox, else the most frequent, else ambiguous), never by an assistant's address. Phillip Allen and John Lavorato now match themselves, Lou Pai matches `lou.pai@enron.com`. Records combining an assistant position with another (8, including Sally Beck, Steven Kean and Mike McConnell) are flagged and excluded from the main population. **Open:** those records cannot be split without the original charts; a question to the authors is listed below. |
| M1 coverage overstated; unmatched employees scored 0 | fixed | `b96e663`, `4e057d0` | Every employee has a match status (1,518 with email: 933 name+address, 70 name, 424 address node, 56 ambiguous, 35 absent) and graph presence is checked. The main population is the 11,372 pairs whose two employees are matched and unmixed; scoring unmatched employees 0 over all 13,241 pairs is a sensitivity run. |
| M2 alphabetical tie-breaking decides results | fixed | `b96e663` | No tie is broken by spelling order: tied principal names are ambiguous; among several address nodes only the one spelled exactly as the normalized name is chosen (Thomas White), otherwise ambiguous. The claim that matching "cannot favour" a measure was removed. |
| M3 position aggregation and cycle policy unresolved | partly fixed | `b96e663`, `4e057d0` | The main construction is unchanged and stated as a choice; two alternatives are evaluated: positions closed before mapping (8,916 pairs; degree 94.8% on its matched pairs) and cycle arcs removed before closure (12,606 pairs; 84.3%). The docstring no longer asserts why the Whalley–Frevert cycle exists. **Open:** the intended construction must come from the authors. |
| M4 the 83.1% figure is not a replication | fixed | `4e057d0` | It is reported as "raw-address degree over all mail, max over release addresses", a sensitivity run (83.1% on all pairs), and no document calls it a replication or a check of the pair construction. |
| M5 intervals and executive weighting | fixed (reporting) | `4e057d0` | Adds the custodian baseline (65.1% overall; 88.9% on inter pairs against degree's 91.9%), a leave-Lay-and-Skilling-out run (degree 80.3%), a per-dominant macro average (degree 77.0%), and paired differences against degree by pair type (PageRank − degree +0.6 points, interval −1.0 to +2.5). The documentation states that intervals cover person resampling only. |
| M6 tests miss consequential failures | fixed | `b96e663`, `4e057d0` | New tests: edges stored only at the top level, multiple positions per record, cycle handling, mixed-position flags, principal-name matching with assistants' addresses, address nodes, ambiguous and absent employees, a brute-force bootstrap oracle, near ties, a graph node shared by two employees, and empty pair types. |
| m1 empty pair types crash | fixed | `4e057d0` | Empty groups give NaN with the number of bootstrap draws used. |
| m2 documentation and provenance | fixed | `b96e663`, `8f1a42c`, README | Docstrings, config and README describe the reconstruction as related to, not a replication of, the paper; the stage skips cleanly when the private release is absent, and the config says to request it from the authors. |

## Result, main population

11,372 pairs whose two employees are matched and unmixed (360 core, 4,411
inter, 6,601 non-core): degree 85.0% (73.3–93.9%), PageRank 85.6%, email
received 82.5%, betweenness 75.4%, messages sent 69.0%, custodian baseline
65.1%.

## Questions for the release authors

- Can they share the exact pair list, core-ID list and construction code
  behind Table 1 (2,155 immediate relations, 13,724 pairs)?
- Were all positions sharing a record merged before the closure, and how were
  executive/assistant records (Beck, Kean, McConnell), vacant positions and
  different chart dates handled?
- How was the Whalley–Frevert cycle resolved?
- Which mailbox-to-person mapping gave 440 / 6,436 / 6,847 core, inter and
  non-core pairs?
