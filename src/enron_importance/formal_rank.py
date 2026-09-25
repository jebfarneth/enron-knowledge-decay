"""Formal-rank labels from the Shetty & Adibi (2004) title list.

Each listed employee gets an ordinal seniority level from their title
(config.yaml `formal_rank.levels`) and is matched to a corpus identity by
normalized name, with reviewed name corrections applied first. The labels
are a noisy, undated title proxy, not ground truth: rank *level*, not
reporting lines, taken from a generic title column.

Two kinds of known label problems are handled explicitly rather than
silently:

* Duplicate rows with conflicting titles for one person: the rows listed in
  `formal_rank.dropped_rows` are removed, following Diesner & Carley (2005,
  footnote 3), who checked the same two conflicts against FERC files.
* Disputed labels, where the list's own note or the person's signature
  contradicts the title column (`formal_rank.disputed`), are flagged so the
  evaluation can be rerun without them.

Usage: uv run python -m enron_importance.formal_rank
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request

import pandas as pd

from .config import load_config
from .identity import normalize_name


def fetch_title_list(config: dict):
    spec = config["formal_rank"]
    target = config["paths"]["raw"] / spec["filename"]
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(spec["url"]) as response:
            target.write_bytes(response.read())
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != spec["sha256"]:
        sys.exit(f"{target.name}: SHA-256 mismatch ({actual})")
    return target


def formal_ranks(titles: pd.DataFrame, identities: pd.DataFrame, levels: dict, corrections: dict,
                 aliases: dict | None = None, dropped_rows=(), disputed=()) -> pd.DataFrame:
    """Match title-list rows to identities and attach seniority levels.

    `titles` has name, title and (optionally) note columns; returns one row
    per source row with person_key (None if unmatched), level (None if the
    title is blank, unknown or the row is dropped), how the match was made
    and whether the label is disputed. `aliases` maps name keys to the person
    key they were merged into by directory ID.
    """
    aliases = aliases or {}
    known = set(identities["person_key"].dropna())
    notes = titles["note"] if "note" in titles else pd.Series([None] * len(titles), index=titles.index)
    rows = []
    for name, title, note in zip(titles["name"], titles["title"], notes):
        name = str(name).strip()
        title = title.strip() if isinstance(title, str) else None
        if name in corrections:
            key, method = corrections[name], "reviewed correction"
        else:
            key, method = normalize_name(name), "normalized name"
            if key in aliases:
                key, method = aliases[key], "directory-ID alias"
        if key not in known:
            key, method = None, "unmatched"
        level = levels.get(title)
        if name in dropped_rows:
            level, method = None, "dropped conflicting row"
        rows.append({"name": name, "title": title, "note": note if isinstance(note, str) else None, "level": level,
                     "person_key": key, "match": method, "disputed": key in disputed})
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    spec = config["formal_rank"]
    titles = pd.read_excel(fetch_title_list(config), header=None, names=["name", "title", "note"])
    out = config["paths"]["processed"]
    identities = pd.read_parquet(out / "identities.parquet")
    aliases = pd.read_parquet(out / "name_aliases.parquet")
    ranks = formal_ranks(titles, identities, spec["levels"], spec["corrections"],
                         dict(zip(aliases["name_key"], aliases["person_key"])), spec["dropped_rows"], spec["disputed"])
    ranks.to_parquet(out / "formal_rank.parquet", index=False)
    usable = ranks.dropna(subset=["person_key", "level"])
    print(f"Listed {len(ranks)}; matched {ranks['person_key'].notna().sum()}; "
          f"with a title level {len(usable)} ({usable['person_key'].nunique()} distinct people)")
    print(ranks["match"].value_counts().to_string())
    print(f"Disputed labels: {sorted(usable.loc[usable['disputed'], 'person_key'])}")


if __name__ == "__main__":
    main()
