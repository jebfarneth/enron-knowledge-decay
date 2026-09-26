"""Dominance pairs from the Agarwal et al. (2012) Enron hierarchy gold standard.

The Columbia release (shared privately by Owen Rambow, 2026-09-25) is a
MongoDB dump; its `entities` collection holds org-chart positions
transcribed from Enron org charts, as position nodes joined by "contains",
"manages" and "supervises" edges through organizational units. Edges are
read from both the position nodes and the top level of each record. An
employee immediately dominates another when a path leads from one of their
positions to one of the other's through units only; the dominance pairs are
the transitive closure of those immediate relations, restricted to the 1,518
employees with email addresses. Positions sharing an employee record are
merged before the closure, and a pair recorded in both directions is dropped.
The 682 records without email (including vacant and "?" positions) stay in
the closure as intermediaries.

This does not reproduce the paper's counts (2,155 immediate relations and
13,724 pairs), and the release does not say which construction the paper
used, so two alternatives are also written for sensitivity runs:
positions closed before mapping to employees, and arcs inside any
contradictory cycle removed before the closure (the one cycle joins Greg
Whalley and Mark Frevert through different positions).

Matching employees to graph nodes. For executives the release's address
list often holds their assistants' addresses (Phillip Allen's record lists
Ina Rangel's, John Lavorato's Angela McCulloch's), so employees are matched
by their principal name, not by address:

1. The principal name is the release name whose surname and first initial
   match the employee's mailbox (Allen-P), or else the name the release
   gives most often. A tie leaves the employee ambiguous.
2. The name is normalized and aliased as in `identity.py`. A graph person
   with that key is the match ("name+address" when one of the release's
   addresses also resolves to it, otherwise "name"); a `first.last@`
   address node spelled from one of the release's own names is the match
   when no person node exists ("address node"; among several, the one
   spelled exactly as the normalized name). A key the identity stage marks
   ambiguous, or several address nodes none spelled that way, leaves the
   employee "ambiguous"; no candidate in the graph is "absent".

No tie is broken by spelling or mailbox order and no measure's value is
read, though any matching rule still affects measures unequally (see the
sensitivity runs).

Uncertain records. A record whose known positions combine a support
position (a title ending in Assistant, Asst or Secretary) with a different
one (Sally Beck, Steven Kean, Mike McConnell) is flagged `mixed_positions`;
a record holding several positions whose addresses resolve to two or more
different people is flagged `multiple_people`. Either makes the record an
`uncertain_owner`: the release merged two people's positions, or one
person's over time, which matching cannot undo. Pairs are marked
`independent_of_uncertain` when they still follow with every relation
touching an uncertain record removed before the closure, so a pair whose
dominance runs through such a record can be excluded, not only a pair with
one at an end. Mixed positions are direct evidence that positions were
merged, so the main population excludes pairs that run through them;
several people behind one record's addresses (often an executive and an
assistant) is weaker evidence about positions, so excluding those paths too
is a stricter sensitivity run. Custodians
(records with mailboxes in the corpus, the paper's "core") are marked so
accuracy can be split into core, inter and non-core pairs.

Usage: uv run python -m enron_importance.gold_standard
"""

from __future__ import annotations

import json
import re
from collections import Counter

import bson
import networkx as nx
import pandas as pd

from .config import load_config
from .download import sha256_of
from .identity import normalize_name, resolve_recipient

MAPPED = {"name+address", "name", "address node"}
# A support position: the title ends in Assistant, Asst or Secretary ("Sr Admin Asst",
# "Executive Secretary"), not "Asst General Counsel" or the officer "Corporate Secretary".
_ASSISTANT = re.compile(r"\b(assistant|asst|secretary)(\s+i+)?\s*$", re.IGNORECASE)
_UNKNOWN_TITLE = re.compile(r"^\W*\?")


def is_assistant(title: str) -> bool:
    return bool(_ASSISTANT.search(title)) and not title.strip().lower().startswith("corporate secretary")


def mixed_positions(titles: list[str]) -> bool:
    """True when a record holds an assistant position and a different, known position."""
    known = [t for t in titles if t.strip() and not _UNKNOWN_TITLE.match(t)]
    return any(map(is_assistant, known)) and not all(map(is_assistant, known))


def read_entities(path) -> list[dict]:
    with open(path, "rb") as handle:
        return list(bson.decode_file_iter(handle))


def _walk_to_employees(graph: nx.DiGraph, start: str, owner: dict) -> set[str]:
    """Employee-owned positions reached from `start` through units only."""
    found, stack, seen = set(), list(graph.successors(start)) if start in graph else [], set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in owner:
            found.add(current)
        else:
            stack.extend(graph.successors(current))
    return found


def _asymmetric_closure(immediate: set, keep: set) -> list[tuple[str, str]]:
    closure = nx.DiGraph(immediate)
    pairs = {(a, b) for a in closure for b in nx.descendants(closure, a) if a in keep and b in keep and a != b}
    return sorted((a, b) for a, b in pairs if (b, a) not in pairs)


def dominance_pairs(entities: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame], set]:
    """Employees, the main (dominant, subordinate) pairs, alternative constructions, and the immediate relations."""
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
            titles = [str(node.get("position") or "") for node in doc["position_nodes"]]
            rows.append({
                "gold_id": person, "has_email": "uid" in doc, "position": doc["position"],
                "addresses": [a.lower() for a in doc.get("email_addresses") or [] if "@" in a],
                "names": [n for n in doc.get("email_names") or [] if isinstance(n, str)],
                "mailboxes": [m for m in doc.get("mailboxes") or [] if isinstance(m, str)],
                "custodian": bool(doc.get("mailboxes")),
                "mixed_positions": mixed_positions(titles), "positions": len(titles),
            })
    graph = nx.DiGraph(edges)
    employees = pd.DataFrame(rows)
    emailers = set(employees.loc[employees["has_email"], "gold_id"])

    position_immediate = {(node, target) for node in owner for target in _walk_to_employees(graph, node, owner)}
    immediate = {(owner[a], owner[b]) for a, b in position_immediate if owner[a] != owner[b]}
    main = _asymmetric_closure(immediate, emailers)

    cyclic = set()
    for component in nx.strongly_connected_components(nx.DiGraph(immediate)):
        if len(component) > 1:
            cyclic |= {(a, b) for a, b in immediate if a in component and b in component}
    position_pairs = {(owner[a], owner[b]) for a, b in _asymmetric_closure(position_immediate, set(owner))
                      if owner[a] != owner[b] and owner[a] in emailers and owner[b] in emailers}
    alternatives = {
        "positions closed before mapping": sorted(p for p in position_pairs if (p[1], p[0]) not in position_pairs),
        "cycle arcs removed before closure": _asymmetric_closure(immediate - cyclic, emailers),
    }
    frame = lambda pairs: pd.DataFrame(pairs, columns=["dominant", "subordinate"])  # noqa: E731
    return employees, frame(main), {name: frame(pairs) for name, pairs in alternatives.items()}, immediate


def independent_of(immediate: set, uncertain: set, emailers: set) -> set[tuple[str, str]]:
    """Pairs that still follow when every relation touching an uncertain record is removed before the closure."""
    return set(_asymmetric_closure({(a, b) for a, b in immediate if a not in uncertain and b not in uncertain}, emailers))


def principal_name(names: list[str], mailboxes: list[str], aliases: dict | None = None) -> str | None:
    """The normalized name the record belongs to, or None when that is ambiguous.

    Names matching any of the record's mailboxes (surname and first
    initial, "Allen-P") are pooled: exactly one such person is the principal,
    two or more is ambiguous whatever the mailboxes' order. Without a
    mailbox match, the most frequent name is the principal; a tie is
    ambiguous.
    """
    aliases = aliases or {}
    written: dict[str, set[str]] = {}  # key -> first names as written ("bob" for "robert jones")
    keys = []
    for name in names:
        key = normalize_name(name)
        if key and "@" not in key:
            key = aliases.get(key, key)
            keys.append(key)
            first = re.findall(r"[a-z]+", name.lower().split(",")[-1] if "," in name else name.lower())
            written.setdefault(key, set()).update(first[:1] + [key.split()[0]])
    counts = Counter(keys)
    matching = set()
    for mailbox in mailboxes:
        surname, _, initial = mailbox.lower().partition("-")
        matching |= {k for k in counts if k.split()[-1] == surname
                     and (not initial or any(f.startswith(initial[0]) for f in written[k]))}
    if matching:
        return matching.pop() if len(matching) == 1 else None
    if not counts:
        return None
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


def match_people(employees: pd.DataFrame, identities: pd.DataFrame, nodes=frozenset(), aliases=None,
                 types=None) -> pd.DataFrame:
    """Graph node (`person_key`) and `match_status` for each gold employee; see the module docstring."""
    aliases, types = aliases or {}, types or {}
    address_person = dict(zip(identities["address"], identities["person_key"]))
    people = set(identities.loc[identities["entity_type"] == "person", "person_key"])

    def match(names, addresses, mailboxes):
        key = principal_name(names, mailboxes, aliases)
        if key is None:
            return None, "ambiguous" if names else "absent"
        if types.get(key) == "ambiguous":
            return None, "ambiguous"
        if key in nodes and types.get(key, "person") == "person":
            resolved = {resolve_recipient(a, address_person, people) for a in addresses if a.endswith("@enron.com")}
            return key, "name+address" if key in resolved else "name"
        spelled = set()
        for name in names:
            if normalize_name(name) is not None and aliases.get(normalize_name(name), normalize_name(name)) == key:
                words = [w for w in re.sub(r"[^a-z\s]", " ", name.lower()).split() if len(w) > 1]
                if len(words) >= 2:
                    spelled.add(f"{words[0]}.{words[-1]}@enron.com")
        present = sorted(a for a in spelled if a in nodes)
        canonical = f"{key.split()[0]}.{key.split()[-1]}@enron.com"
        if len(present) > 1 and canonical in present:
            present = [canonical]  # "thomas.white@" over "tom.white@" for the key "thomas white"
        if len(present) == 1:
            return present[0], "address node"
        return None, "ambiguous" if len(present) > 1 else "absent"

    matched = [match(n, a, m) for n, a, m in zip(employees["names"], employees["addresses"], employees["mailboxes"])]
    return pd.DataFrame(matched, columns=["person_key", "match_status"], index=employees.index)


def label_pairs(pairs: pd.DataFrame, employees: pd.DataFrame) -> pd.DataFrame:
    """Attach graph keys, match statuses and core/inter/non-core type to (dominant, subordinate) pairs."""
    table = employees.set_index("gold_id")
    out = pairs.copy()
    for role in ["dominant", "subordinate"]:
        out[f"{role}_key"] = out[role].map(table["person_key"])
        out[f"{role}_status"] = out[role].map(table["match_status"])
        out[f"{role}_mixed"] = out[role].map(table["mixed_positions"]).astype(bool)
        out[f"{role}_uncertain"] = out[role].map(table["uncertain_owner"]).astype(bool)
    core = out["dominant"].map(table["custodian"]).astype(int) + out["subordinate"].map(table["custodian"]).astype(int)
    out["type"] = core.map({2: "core", 1: "inter", 0: "non-core"})
    return out


def main(config: dict | None = None) -> None:
    config = config or load_config()
    spec = config["gold_standard"]
    source = config["paths"]["raw"] / spec["entities"]
    outputs = [config["paths"]["processed"] / name for name in ["gold_employees.parquet", "gold_pairs.parquet", "gold_coverage.json"]]
    if not source.exists():
        for stale in outputs:  # never leave earlier outputs for later stages to read
            stale.unlink(missing_ok=True)
        print(f"Skipped: {source} not found. The release is not public; request it from the authors (config.yaml).")
        return
    if sha256_of(source) != spec["sha256"]:
        raise SystemExit(f"{source.name}: SHA-256 mismatch")
    employees, pairs, alternatives, immediate = dominance_pairs(read_entities(source))
    processed = config["paths"]["processed"]
    nodes = set(pd.read_parquet(processed / "centrality.parquet", columns=["person_key"])["person_key"])
    aliases = pd.read_parquet(processed / "name_aliases.parquet")
    types = pd.read_parquet(processed / "person_types.parquet")
    employees = employees.join(match_people(employees, pd.read_parquet(processed / "identities.parquet"), nodes,
                                            dict(zip(aliases["name_key"], aliases["person_key"])),
                                            dict(zip(types["person_key"], types["entity_type"]))))
    identities = pd.read_parquet(processed / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    person_keys = set(types.loc[types["entity_type"] == "person", "person_key"])
    resolved = employees["addresses"].map(lambda addresses: {
        p for p in (resolve_recipient(a, address_person, person_keys) for a in addresses if a.endswith("@enron.com"))
        if p in person_keys})
    employees["multiple_people"] = (employees["positions"] >= 2) & (resolved.map(len) >= 2)
    employees["uncertain_owner"] = employees["mixed_positions"] | employees["multiple_people"]
    emailer_ids = set(employees.loc[employees["has_email"], "gold_id"])
    robust = independent_of(immediate, set(employees.loc[employees["uncertain_owner"], "gold_id"]), emailer_ids)
    robust_mixed = independent_of(immediate, set(employees.loc[employees["mixed_positions"], "gold_id"]), emailer_ids)
    employees.to_parquet(processed / "gold_employees.parquet", index=False)
    pairs["independent_of_uncertain"] = [pair in robust for pair in zip(pairs["dominant"], pairs["subordinate"])]
    pairs["independent_of_mixed"] = [pair in robust_mixed for pair in zip(pairs["dominant"], pairs["subordinate"])]
    labelled = pd.concat([label_pairs(pairs, employees).assign(construction="main")]
                         + [label_pairs(p, employees).assign(construction=name) for name, p in alternatives.items()])
    labelled.to_parquet(processed / "gold_pairs.parquet", index=False)

    emailers = employees[employees["has_email"]]
    main_pairs = labelled[labelled["construction"] == "main"]
    usable = (main_pairs["dominant_status"].isin(MAPPED) & main_pairs["subordinate_status"].isin(MAPPED)
              & ~main_pairs["dominant_mixed"] & ~main_pairs["subordinate_mixed"]
              & main_pairs["independent_of_mixed"].astype(bool))
    coverage = {
        "employees": len(employees), "employees_with_email": len(emailers),
        "match_status": {k: int(v) for k, v in emailers["match_status"].value_counts().items()},
        "employees_with_mixed_positions": int(emailers["mixed_positions"].sum()),
        "employees_with_several_people_and_positions": int(emailers["multiple_people"].sum()),
        "employees_uncertain": int(emailers["uncertain_owner"].sum()),
        "pairs": {name: int((labelled["construction"] == name).sum()) for name in labelled["construction"].unique()},
        "main_pairs_by_type": {k: int(v) for k, v in main_pairs["type"].value_counts().items()},
        "main_population_pairs": int(usable.sum()),
        "paper": {"immediate_relations": 2155, "pairs": 13724, "core": 440, "inter": 6436, "non_core": 6847},
    }
    (processed / "gold_coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")
    print(json.dumps(coverage, indent=2))


if __name__ == "__main__":
    main()
