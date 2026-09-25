"""Formal rank ground truth from the Shetty & Adibi (2004) title list.

Each listed employee gets an ordinal seniority level from their title
(config.yaml `formal_rank.levels`) and is matched to a corpus identity by
normalized name, with reviewed spelling corrections applied first. This is
rank *level*, not reporting lines: it says who is more senior, not who
manages whom.

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
                 aliases: dict | None = None) -> pd.DataFrame:
    """Match title-list rows to identities and attach seniority levels.

    `titles` has name and title columns; returns one row per listed person with
    person_key (None if unmatched), level (None if the title is blank or
    unknown) and how the match was made. `aliases` maps name keys to the
    person key they were merged into by directory ID.
    """
    aliases = aliases or {}
    known = set(identities["person_key"].dropna())
    rows = []
    for name, title in zip(titles["name"], titles["title"]):
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
        rows.append({"name": name, "title": title, "level": levels.get(title), "person_key": key, "match": method})
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()
    spec = config["formal_rank"]
    titles = pd.read_excel(fetch_title_list(config), header=None, names=["name", "title", "note"])
    out = config["paths"]["processed"]
    identities = pd.read_parquet(out / "identities.parquet")
    aliases = pd.read_parquet(out / "name_aliases.parquet")
    ranks = formal_ranks(titles, identities, spec["levels"], spec["corrections"],
                         dict(zip(aliases["name_key"], aliases["person_key"])))
    ranks.to_parquet(out / "formal_rank.parquet", index=False)
    usable = ranks.dropna(subset=["person_key", "level"])
    print(f"Listed {len(ranks)}; matched {ranks['person_key'].notna().sum()}; "
          f"with a title level {len(usable)} ({usable['person_key'].nunique()} distinct people)")
    print(ranks["match"].value_counts().to_string())


if __name__ == "__main__":
    main()
