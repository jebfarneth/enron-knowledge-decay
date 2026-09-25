"""Communication network and standard centrality measures per person.

Graph: nodes are people (resolved identities); a directed edge u -> v exists
when u emailed v (To or Cc) from an internal, non-automated sender address.
A message to n internal recipients adds 1/n to each of its edges, so one
broadcast does not outweigh sustained one-to-one work.

Measures (all standard, all exact):
  degree          number of distinct people a person exchanged email with
                  (undirected), the baseline used by Agarwal et al. (2012)
  in_strength     weighted email received
  out_strength    weighted email sent
  pagerank        PageRank on the weighted directed graph (Brin & Page 1998),
                  damping 0.85
  betweenness     exact betweenness (Freeman 1977; Brandes 2001) on the
                  undirected graph, edge length = 1 / weight, so frequent
                  contacts are close

Usage: uv run python -m enron_importance.network
"""

from __future__ import annotations

from collections import defaultdict

import igraph as ig
import pandas as pd

from .config import load_config


def build_edges(messages: pd.DataFrame, address_to_person: dict[str, str], internal_domain: str) -> pd.DataFrame:
    """Directed weighted edges between people. `messages` needs sender, to, cc."""
    suffix = "@" + internal_domain
    weight: dict[tuple[str, str], float] = defaultdict(float)
    count: dict[tuple[str, str], int] = defaultdict(int)
    for sender, to, cc in zip(messages["sender"], messages["to"], messages["cc"]):
        recipients = {r for r in list(to) + list(cc) if isinstance(r, str) and r.endswith(suffix)}
        source = address_to_person.get(sender, sender)
        targets = {address_to_person.get(r, r) for r in recipients} - {source}
        if not targets:
            continue
        share = 1.0 / len(targets)
        for target in targets:
            weight[(source, target)] += share
            count[(source, target)] += 1
    return pd.DataFrame(
        [(s, t, w, count[(s, t)]) for (s, t), w in weight.items()],
        columns=["source", "target", "weight", "messages"],
    )


def centrality(edges: pd.DataFrame) -> pd.DataFrame:
    """One row per person with degree, strengths, PageRank and exact betweenness."""
    directed = ig.Graph.TupleList(edges[["source", "target", "weight"]].itertuples(index=False), directed=True, edge_attrs=["weight"])
    names = directed.vs["name"]
    undirected = directed.as_undirected(mode="collapse", combine_edges={"weight": "sum"})
    lengths = [1.0 / w for w in undirected.es["weight"]]
    return pd.DataFrame({
        "person_key": names,
        "degree": undirected.degree(),
        "in_strength": directed.strength(mode="in", weights="weight"),
        "out_strength": directed.strength(mode="out", weights="weight"),
        "pagerank": directed.pagerank(weights="weight", damping=0.85),
        "betweenness": undirected.betweenness(weights=lengths, directed=False),
    })


def main() -> None:
    config = load_config()
    processed = config["paths"]["processed"]
    messages = pd.read_parquet(processed / "messages.parquet", columns=["sender", "to", "cc", "sender_internal", "sender_automated"])
    messages = messages[messages["sender_internal"] & ~messages["sender_automated"]]
    identities = pd.read_parquet(processed / "identities.parquet")
    edges = build_edges(messages, dict(zip(identities["address"], identities["person_key"])), config["senders"]["internal_domain"])
    edges.to_parquet(processed / "edges.parquet", index=False)
    measures = centrality(edges)
    measures.to_parquet(processed / "centrality.parquet", index=False)
    print(f"{len(measures):,} people, {len(edges):,} directed edges")


if __name__ == "__main__":
    main()
