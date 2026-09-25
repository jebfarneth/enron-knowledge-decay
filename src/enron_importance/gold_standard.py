"""Dominance pairs from the Agarwal et al. (2012) Enron hierarchy gold standard.

The Columbia release (shared by Owen Rambow, 2026-09-25) is a MongoDB dump;
its `entities` collection holds org-chart positions transcribed from Enron
org charts, as position nodes joined by "contains", "manages" and
"supervises" edges through organizational units. Following the paper, an
employee immediately dominates another when a path leads from one's
position to the other's through units only, and the dominance pairs are the
transitive closure of those immediate relations, restricted to the 1,518
employees with email addresses. Pairs recorded in both directions (a cycle
in the transcription) are dropped.

The paper reports 13,724 pairs; this release yields slightly fewer (see
`main`'s output), so results are compared with the paper's as related, not
identical, benchmarks.

Employees are matched to graph nodes through their email addresses, using
the same address table and recipient resolution as the network (see
`match_people` for how several candidate nodes are resolved).
Custodians (people whose mailboxes are in the corpus, the paper's "core")
are marked so accuracy can be split into core, inter and non-core pairs.

Usage: uv run python -m enron_importance.gold_standard
"""

from __future__ import annotations

import sys

import bson
import networkx as nx
import pandas as pd

from .config import load_config
from .download import sha256_of
from .identity import resolve_recipient


def read_entities(path) -> list[dict]:
    with open(path, "rb") as handle:
        return list(bson.decode_file_iter(handle))


def dominance_pairs(entities: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Employees table and (dominant, subordinate) pairs among employees with email."""
    edges = set()
    owner: dict[str, str] = {}
    rows = []
    for doc in entities:
        for node in doc.get("position_nodes") or []:
            for edge in node.get("incident_edges") or []:
                edges.add((edge["ffrom"], edge["to"]))
        for edge in doc.get("incident_edges") or []:
            edges.add((edge["ffrom"], edge["to"]))
        if "position" in doc:
            person = str(doc.get("uid", doc["_id"]))
            owner.update({node["uid"]: person for node in doc["position_nodes"]})
            rows.append({"gold_id": person, "has_email": "uid" in doc, "position": doc["position"],
                         "addresses": [a.lower() for a in doc.get("email_addresses") or [] if "@" in a],
                         "names": list(doc.get("email_names") or []), "custodian": bool(doc.get("mailboxes"))})
    graph = nx.DiGraph(edges)
    immediate = set()
    for node, person in owner.items():
        stack, seen = list(graph.successors(node)) if node in graph else [], set()
        while stack:  # walk down through units until the next employees
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            if current in owner:
                if owner[current] != person:
                    immediate.add((person, owner[current]))
            else:
                stack.extend(graph.successors(current))
    closure = nx.DiGraph(immediate)
    employees = pd.DataFrame(rows)
    emailers = set(employees.loc[employees["has_email"], "gold_id"])
    pairs = {(a, b) for a in closure for b in nx.descendants(closure, a) if a in emailers and b in emailers}
    pairs = sorted((a, b) for a, b in pairs if (b, a) not in pairs)
    return employees, pd.DataFrame(pairs, columns=["dominant", "subordinate"])


def match_people(employees: pd.DataFrame, identities: pd.DataFrame, nodes=frozenset()) -> pd.Series:
    """Corpus node for each gold employee, or None.

    An employee's addresses can resolve to several nodes. Resolved people
    are preferred to bare address nodes, then nodes present in the graph
    (`nodes`), then the node most of their addresses resolve to, then the
    alphabetically first. No measure's value is used, so the choice cannot
    favour one measure.
    """
    address_person = dict(zip(identities["address"], identities["person_key"]))
    people = set(identities.loc[identities["entity_type"] == "person", "person_key"])

    def match(addresses):
        keys = [resolve_recipient(a, address_person, people) for a in addresses if a.endswith("@enron.com")]
        counts = pd.Series([k for k in keys if isinstance(k, str)]).value_counts()
        if counts.empty:
            return None
        return min(counts.index, key=lambda k: (k not in people, k not in nodes, -counts[k], k))

    return employees["addresses"].map(match)


def main() -> None:
    config = load_config()
    spec = config["gold_standard"]
    source = config["paths"]["raw"] / spec["entities"]
    if not source.exists():
        sys.exit(f"{source} missing: download the Columbia release (see config.yaml gold_standard)")
    if sha256_of(source) != spec["sha256"]:
        sys.exit(f"{source.name}: SHA-256 mismatch")
    employees, pairs = dominance_pairs(read_entities(source))
    processed = config["paths"]["processed"]
    nodes = set(pd.read_parquet(processed / "centrality.parquet", columns=["person_key"])["person_key"])
    employees["person_key"] = match_people(employees, pd.read_parquet(processed / "identities.parquet"), nodes)
    key = dict(zip(employees["gold_id"], employees["person_key"]))
    custodian = dict(zip(employees["gold_id"], employees["custodian"]))
    pairs["dominant_key"] = pairs["dominant"].map(key)
    pairs["subordinate_key"] = pairs["subordinate"].map(key)
    core = pairs["dominant"].map(custodian).astype(int) + pairs["subordinate"].map(custodian).astype(int)
    pairs["type"] = core.map({2: "core", 1: "inter", 0: "non-core"})
    employees.to_parquet(processed / "gold_employees.parquet", index=False)
    pairs.to_parquet(processed / "gold_pairs.parquet", index=False)
    emailers = employees[employees["has_email"]]
    print(f"{len(employees):,} org-chart employees, {len(emailers):,} with email; {len(pairs):,} dominance pairs "
          f"(paper: 13,724)")
    print(pairs["type"].value_counts().to_string())
    matched = pairs["dominant_key"].notna() & pairs["subordinate_key"].notna()
    print(f"employees with email matched to a graph node: {emailers['person_key'].notna().sum():,}; "
          f"pairs with both matched: {matched.sum():,}")


if __name__ == "__main__":
    main()
