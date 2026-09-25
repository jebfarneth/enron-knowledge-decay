# Legacy version (March–May 2026)

The original pipeline and D3 dashboard behind the first working paper,
*Mapping Organizational Knowledge at Enron*. Kept for reference and for
comparison against the rebuilt pipeline. It is not maintained.

Known issues that motivated the rebuild (details in the project audit):

- Positional Impact came from hand-assigned titles for 41 people, and the
  validation scored those same people, so part of the validation was circular.
- Betweenness treated email volume as distance and was sampled without a seed.
- Emails were not deduplicated, and quoted replies and signatures were kept.
- The topic model was unseeded, and intermediate artifacts were not saved.
- The AI automation scores were hand-entered, not modeled.

`dashboard_data.json` is the only surviving output of this version.
