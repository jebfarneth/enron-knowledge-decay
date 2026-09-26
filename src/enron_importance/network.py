"""Communication network and standard centrality measures per entity.

Graph: a directed edge u -> v exists when u emailed v (To or Cc) from an
internal message that is neither automated, a structured record nor a
probable time-shifted copy. Senders are the per-message attribution
from `identity.py`; recipients are resolved through the address table, and
recipients never seen as senders stay as unresolved address nodes. Every node
carries an entity type (person, role, list, address), so analyses can report
people only or the whole graph. Placeholder addresses are dropped.

A message to n internal recipients adds 1/n to each of its edges. This
weighting affects the weighted measures (strengths, PageRank, betweenness);
degree counts distinct contacts and so still credits broadcasts in full.

Measures:
  degree          number of distinct entities a node exchanged email with
                  (undirected), the baseline used by Agarwal et al. (2012)
  in_strength     weighted email received
  out_strength    messages sent to at least one internal recipient; each
                  message's weights sum to 1, so this is the weighted
                  out-strength, counted as an exact integer
  pagerank        PageRank on the weighted directed graph (Brin & Page 1998),
                  damping 0.85
  betweenness     exact all-pairs betweenness (Freeman 1977; Brandes 2001),
                  no sampling, on the undirected graph with edge length =
                  1 / weight, so frequent contacts are close

Edges are sorted before any computation, so reruns give identical output.

Usage: uv run python -m enron_importance.network
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

import igraph as ig
import pandas as pd

from .config import load_config
from .identity import entity_type, extra_recipients, resolve_recipient
from .provenance import record_stage


def build_edges(messages: pd.DataFrame, recipient: Callable[[str], str | None], internal_domain: str,
                max_recipients: int | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Directed weighted edges and exact sent-message counts.

    `messages` needs sender_person, to and cc, and optionally
    recipient_extra (people added from other copies of the message).
    `recipient` maps an address to its node (None to drop it). Messages with
    more than `max_recipients` internal targets are skipped when a limit is
    given.
    """
    suffix = "@" + internal_domain
    weight: dict[tuple[str, str], float] = defaultdict(float)
    count: dict[tuple[str, str], int] = defaultdict(int)
    sent: dict[str, int] = defaultdict(int)
    extras = messages["recipient_extra"] if "recipient_extra" in messages else [[]] * len(messages)
    for source, to, cc, extra in zip(messages["sender_person"], messages["to"], messages["cc"], extras):
        if not isinstance(source, str):
            continue
        addresses = sorted({r for r in list(to) + list(cc) if isinstance(r, str) and r.endswith(suffix)})
        targets = sorted(({t for t in map(recipient, addresses) if t is not None} | set(extra)) - {source})
        if not targets or (max_recipients is not None and len(targets) > max_recipients):
            continue
        sent[source] += 1
        share = 1.0 / len(targets)
        for target in targets:
            weight[(source, target)] += share
            count[(source, target)] += 1
    edges = pd.DataFrame(
        [(s, t, weight[(s, t)], count[(s, t)]) for s, t in sorted(weight)],
        columns=["source", "target", "weight", "messages"],
    )
    return edges, pd.Series(sent, dtype="int64").sort_index()


def centrality(edges: pd.DataFrame, sent: pd.Series | None = None, betweenness: bool = True) -> pd.DataFrame:
    """One row per node with degree, strengths, PageRank and (optionally) exact betweenness."""
    edges = edges.sort_values(["source", "target"], kind="stable")
    directed = ig.Graph.TupleList(edges[["source", "target", "weight"]].itertuples(index=False), directed=True, edge_attrs=["weight"])
    names = directed.vs["name"]
    undirected = directed.as_undirected(mode="collapse", combine_edges={"weight": "sum"})
    lengths = [1.0 / w for w in undirected.es["weight"]]
    out_strength = (sent.reindex(names, fill_value=0).to_numpy() if sent is not None
                    else directed.strength(mode="out", weights="weight"))
    return pd.DataFrame({
        "person_key": names,
        "degree": undirected.degree(),
        "in_strength": directed.strength(mode="in", weights="weight"),
        "out_strength": out_strength,
        "pagerank": directed.pagerank(weights="weight", damping=0.85),
        "betweenness": undirected.betweenness(weights=lengths, directed=False) if betweenness else float("nan"),
    })


def network_messages(config: dict) -> pd.DataFrame:
    """Internal messages that are neither automated nor structured records, with their sender person."""
    processed = config["paths"]["processed"]
    columns = ["path", "to", "cc", "to_extra", "cc_extra", "sender_internal", "automated", "structured", "probable_copy"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=columns)
    messages = messages.merge(pd.read_parquet(processed / "sender_people.parquet"), on="path", how="left")
    messages = messages[messages["sender_internal"] & ~messages["automated"] & ~messages["structured"]
                        & ~messages["probable_copy"]].copy()
    resolve = recipient_resolver(config)
    domain = "@" + config["senders"]["internal_domain"]
    people = set(pd.read_parquet(processed / "identities.parquet").query("entity_type == 'person'")["person_key"])
    messages["recipient_extra"] = [
        extra_recipients([p for p in (resolve(a) for a in list(to) + list(cc) if a.endswith(domain)) if p],
                         [a for a in list(te) + list(ce) if a.endswith(domain)], resolve, people)
        for to, cc, te, ce in zip(messages["to"], messages["cc"], messages["to_extra"], messages["cc_extra"])
    ]
    return messages


def recipient_resolver(config: dict) -> Callable[[str], str | None]:
    identities = pd.read_parquet(config["paths"]["processed"] / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    people = set(identities.loc[identities["entity_type"] == "person", "person_key"])
    cache: dict[str, str | None] = {}

    def resolve(address: str) -> str | None:
        if address not in cache:
            cache[address] = resolve_recipient(address, address_person, people)
        return cache[address]

    return resolve


def main() -> None:
    config = load_config()
    processed = config["paths"]["processed"]
    edges, sent = build_edges(network_messages(config), recipient_resolver(config), config["senders"]["internal_domain"])
    edges.to_parquet(processed / "edges.parquet", index=False)
    types = pd.read_parquet(processed / "person_types.parquet")
    types = dict(zip(types["person_key"], types["entity_type"]))
    measures = centrality(edges, sent)
    measures["entity_type"] = measures["person_key"].map(lambda k: types.get(k) or entity_type(k))
    measures.to_parquet(processed / "centrality.parquet", index=False)
    print(f"{len(measures):,} nodes, {len(edges):,} directed edges")
    print(measures["entity_type"].value_counts().to_string())
    record_stage(config, "network")


if __name__ == "__main__":
    main()
