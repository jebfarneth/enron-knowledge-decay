"""Custodian-selection experiment (collection/PLAN.md).

Rebuilds Paper 1's measures from the messages a chosen set of mailboxes
holds, and scores them on Paper 1's main gold population, for random,
busiest-first, senior-first and junior-first collections of 10 to 125 of the
150 mailboxes.

A message belongs to a collection when any stored copy of it sits in one of
the collection's mailboxes: the kept message, its exact duplicates
(`copies.parquet`) and its probable time-shifted copies. The network uses
Paper 1's messages and rules (`network.network_messages`, `build_edges`: To
and Cc, a message to n internal people adding 1/n to each edge) and
`centrality` without betweenness; the mention measures use Paper 1's
resolved mention links (`mentions.parquet`, rows with no exclusion) of the
collection's messages. Both are computed from per-message rows, so each
collection takes seconds; before anything else the script checks that the
full collection reproduces Paper 1's edges, mention measures and gold
accuracies exactly.

An employee absent from a collection's graph scores 0 (two absent employees
tie). The custodian baseline is 1 for employees whose mailbox is in the
collection.

Runs with the main project's environment and reads only the certified run
(it stops unless `provenance.stale_reasons` is empty); it writes nothing
under data/.

Writes collection/results/collections.csv (one row per collection) and
collection/results/summary.json.

Usage: .venv/bin/python collection/experiment.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from enron_importance.config import load_config
from enron_importance.evaluate import MENTION_MEASURES
from enron_importance.gold_evaluation import pair_credit
from enron_importance.gold_standard import MAPPED
from enron_importance.network import centrality, network_messages, recipient_resolver
from enron_importance.provenance import stale_reasons

OUT = Path(__file__).resolve().parent / "results"
SIZES = [10, 25, 50, 75, 100, 125]
DRAWS = 200
SEED = 20261014
MEASURES = ["degree", "pagerank", "mention_degree", "mentioned_to", "third_party_mentioned_to", "custodian"]
TYPES = ["all", "core", "inter", "non-core"]
TOP = 20
LEAD_GAP = 2.7          # largest difference between leading measures on the full corpus (Paper 1)


def custodian_of(path: str) -> str:
    return path.split("/")[1]


def edge_rows(messages: pd.DataFrame, resolve, domain: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-message edges as `build_edges` makes them: (message, source, target, share), and senders that count."""
    suffix = "@" + domain
    rows, senders = [], []
    for i, (source, to, cc, extra) in enumerate(zip(messages["sender_person"], messages["to"], messages["cc"],
                                                   messages["recipient_extra"])):
        if not isinstance(source, str):
            continue
        addresses = sorted({r for r in list(to) + list(cc) if isinstance(r, str) and r.endswith(suffix)})
        targets = sorted(({t for t in map(resolve, addresses) if t is not None} | set(extra)) - {source})
        if not targets:
            continue
        senders.append((i, source))
        share = 1.0 / len(targets)
        rows += [(i, source, t, share) for t in targets]
    return (pd.DataFrame(rows, columns=["message", "source", "target", "share"]),
            pd.DataFrame(senders, columns=["message", "source"]))


def membership(paths: pd.Series, holders: dict[str, set[str]], mailboxes: list[str]) -> np.ndarray:
    """Boolean matrix: message (row) has a copy in mailbox (column)."""
    column = {m: j for j, m in enumerate(mailboxes)}
    matrix = np.zeros((len(paths), len(mailboxes)), dtype=bool)
    for i, path in enumerate(paths):
        for m in holders.get(path, {custodian_of(path)}):
            matrix[i, column[m]] = True
    return matrix


def network_measures(edges: pd.DataFrame, senders: pd.DataFrame, keep: np.ndarray) -> pd.DataFrame:
    e = edges[keep[edges["message"].to_numpy()]]
    if e.empty:
        return pd.DataFrame(columns=["person_key", "degree", "pagerank"])
    aggregated = e.groupby(["source", "target"], sort=True)["share"].sum().rename("weight").reset_index()
    sent = senders[keep[senders["message"].to_numpy()]]["source"].value_counts()
    return centrality(aggregated, sent, betweenness=False)[["person_key", "degree", "pagerank"]]


def mention_measures(links: pd.DataFrame, keep: np.ndarray) -> pd.DataFrame:
    """Paper 1's `mention_centrality` from the kept rows: distinct neighbours, people mentioned to, third parties."""
    l = links[keep[links["message"].to_numpy()]]
    both = pd.concat([l[["recipient", "person"]].set_axis(["a", "b"], axis=1),
                      l[["person", "recipient"]].set_axis(["a", "b"], axis=1)]).drop_duplicates()
    out = pd.DataFrame({"mention_degree": both.groupby("a")["b"].size()})
    out["mentioned_to"] = l.drop_duplicates(["recipient", "person"]).groupby("recipient").size()
    out["third_party_mentioned_to"] = l[l["third"]].drop_duplicates(["recipient", "person"]).groupby("recipient").size()
    return out.fillna(0).rename_axis("person_key").reset_index()


def scores_for(employees: pd.DataFrame, network: pd.DataFrame, mentions: pd.DataFrame, chosen: set[str]) -> pd.DataFrame:
    measures = network.merge(mentions, on="person_key", how="outer")
    by_key = measures.set_index("person_key")
    scores = pd.DataFrame(index=employees["gold_id"].to_numpy())
    for name in MEASURES[:-1]:
        scores[name] = employees["person_key"].map(by_key[name]).fillna(0.0).to_numpy(float)
    scores["custodian"] = employees["mailboxes"].map(lambda ms: float(any(m.lower() in chosen for m in ms))).to_numpy()
    return scores


def accuracies(population: pd.DataFrame, scores: pd.DataFrame) -> dict[str, float]:
    out = {}
    types = population["type"].to_numpy()
    for name in MEASURES:
        credit = pair_credit(population["dominant"].map(scores[name]).to_numpy(float),
                             population["subordinate"].map(scores[name]).to_numpy(float))
        for group in TYPES:
            mask = np.ones(len(credit), bool) if group == "all" else types == group
            out[f"{name}|{group}"] = float(credit[mask].mean())
    return out


def spearman(a: pd.Series, b: pd.Series) -> float:
    return float(np.corrcoef(a.rank(), b.rank())[0, 1])


def ranking(scores: pd.DataFrame, full: pd.DataFrame, people: pd.Index, collected: pd.Index) -> dict[str, float]:
    out = {f"spearman_{m}": spearman(scores.loc[people, m], full.loc[people, m]) for m in ("degree", "pagerank")}
    now, before = scores.loc[people, "pagerank"].rank(pct=True), full.loc[people, "pagerank"].rank(pct=True)
    inside = people.intersection(collected)
    out["collection_bias"] = float((now[inside] - before[inside]).mean()) if len(inside) else float("nan")
    top_full = set(full.loc[people, "pagerank"].nlargest(TOP).index)
    out["top20_overlap"] = len(top_full & set(scores.loc[people, "pagerank"].nlargest(TOP).index)) / TOP
    return out


def prepare(started: float) -> dict:
    """Everything a collection run needs, after checking that the full collection reproduces Paper 1."""
    config = load_config()
    reasons = stale_reasons(config)
    if reasons:
        raise SystemExit("the certified run is not current:\n" + "\n".join(reasons))
    processed = config["paths"]["processed"]
    # Paper 1's network messages and per-message edges; their sum must be edges.parquet.
    messages = network_messages(config).reset_index(drop=True)
    edges, senders = edge_rows(messages, recipient_resolver(config), config["senders"]["internal_domain"])
    full_edges = pd.read_parquet(processed / "edges.parquet")
    check = edges.groupby(["source", "target"], sort=True)["share"].agg(["sum", "size"]).reset_index()
    full_edges = full_edges.sort_values(["source", "target"]).reset_index(drop=True)
    if not (len(check) == len(full_edges)
            and (check["source"].to_numpy() == full_edges["source"].to_numpy()).all()
            and (check["target"].to_numpy() == full_edges["target"].to_numpy()).all()
            and np.allclose(check["sum"].to_numpy(), full_edges["weight"].to_numpy())
            and (check["size"].to_numpy() == full_edges["messages"].to_numpy()).all()):
        raise SystemExit("per-message edges do not add up to edges.parquet")

    # Which mailboxes hold a copy of each kept message.
    mailboxes = sorted(pd.read_parquet(processed / "messages.parquet", columns=["custodian"])["custodian"].unique())
    holders: dict[str, set[str]] = {}
    copies = pd.read_parquet(processed / "copies.parquet")
    shifted = pd.read_parquet(processed / "messages.parquet", columns=["path", "probable_copy_of"]).dropna()
    for path, original in list(zip(copies["path"], copies["kept_path"])) + list(zip(shifted["path"], shifted["probable_copy_of"])):
        holders.setdefault(original, {custodian_of(original)}).add(custodian_of(path))
    member_messages = membership(messages["path"], holders, mailboxes)

    links = pd.read_parquet(processed / "mentions.parquet")
    links = links[links["excluded"].isna() & (links["recipient"] != links["person"])].reset_index(drop=True)
    mention_paths = pd.Index(links["path"].unique())
    links["message"] = mention_paths.get_indexer(links["path"])
    sender_people = pd.read_parquet(processed / "sender_people.parquet").set_index("path")["sender_person"]
    analysis = pd.read_parquet(processed / "messages.parquet", columns=["path", "to", "cc", "to_extra", "cc_extra"])
    analysis = analysis[analysis["path"].isin(mention_paths)].set_index("path")
    resolve = recipient_resolver(config)
    from enron_importance.identity import extra_recipients
    types = pd.read_parquet(processed / "person_types.parquet")
    people_set = set(types.loc[types["entity_type"] == "person", "person_key"])
    parties = {}
    for path, row in analysis.iterrows():
        to_people = [p for p in map(resolve, row["to"]) if p]
        cc_people = [p for p in map(resolve, row["cc"]) if p] + extra_recipients(
            [p for p in map(resolve, list(row["to"]) + list(row["cc"])) if p],
            list(row["to_extra"]) + list(row["cc_extra"]), resolve, people_set)
        parties[path] = {sender_people.get(path), *to_people, *cc_people}
    links["third"] = [person not in parties[path] for path, person in zip(links["path"], links["person"])]
    member_mentions = membership(pd.Series(mention_paths), holders, mailboxes)

    full_mentions = mention_measures(links, np.ones(len(mention_paths), bool))
    reference = pd.read_parquet(processed / "mention_centrality.parquet").set_index("person_key")
    mine = full_mentions.set_index("person_key")
    for column in ("mention_degree", "mentioned_to", "third_party_mentioned_to"):
        if not (mine[column].reindex(reference.index, fill_value=0) == reference[column]).all():
            raise SystemExit(f"{column} does not reproduce mention_centrality.parquet")

    # Paper 1's main population and the full-collection reference scores.
    employees = pd.read_parquet(processed / "gold_employees.parquet")
    pairs = pd.read_parquet(processed / "gold_pairs.parquet")
    population = pairs[(pairs["construction"] == "main") & pairs["dominant_status"].isin(MAPPED)
                       & pairs["subordinate_status"].isin(MAPPED) & ~pairs["dominant_mixed"] & ~pairs["subordinate_mixed"]
                       & pairs["independent_of_mixed"].fillna(False).astype(bool)].reset_index(drop=True)
    people = pd.Index(sorted(set(population["dominant"]) | set(population["subordinate"])))
    owner = {m.lower(): gid for gid, ms in zip(employees["gold_id"], employees["mailboxes"]) for m in ms}
    everything = set(mailboxes)
    full_network = network_measures(edges, senders, np.ones(len(messages), bool))
    full = scores_for(employees, full_network, full_mentions, everything)
    reference_accuracy = accuracies(population, full)
    paper = pd.read_csv(config["paths"]["results"] / "baselines_gold_standard.csv")
    for name in ("degree", "pagerank", "mention_degree", "mentioned_to", "third_party_mentioned_to", "custodian"):
        expected = paper[(paper["measure"] == name) & (paper["pairs_type"] == "all")]["accuracy"].iloc[0]
        if abs(reference_accuracy[f"{name}|all"] - expected) > 1e-9:
            raise SystemExit(f"{name}: {reference_accuracy[name + '|all']:.6f} does not reproduce Paper 1's {expected:.6f}")
    print(f"checks passed: edges, mention measures and gold accuracies reproduce Paper 1 "
          f"({len(population):,} pairs, {len(mailboxes)} mailboxes); {time.time() - started:.0f} s", flush=True)

    return {"config": config, "mailboxes": mailboxes, "messages": messages, "edges": edges, "senders": senders,
            "member_messages": member_messages, "links": links, "member_mentions": member_mentions,
            "employees": employees, "population": population, "people": people, "owner": owner, "full": full,
            "full_network": full_network, "full_mentions": full_mentions}


def plan_collections(ctx: dict) -> list[tuple[str, int, int, list[str]]]:
    """(policy, mailboxes, draw, chosen mailboxes) for every collection, random draws in a fixed order."""
    mailboxes, member_messages, population, owner = (ctx[k] for k in ("mailboxes", "member_messages", "population", "owner"))
    size = {m: int(member_messages[:, j].sum()) for j, m in enumerate(mailboxes)}
    dominated = population["dominant"].value_counts()
    seniority = {m: int(dominated.get(owner.get(m), 0)) for m in mailboxes}
    orders = {"busiest first": sorted(mailboxes, key=lambda m: (-size[m], m)),
              "senior first": sorted(mailboxes, key=lambda m: (-seniority[m], m)),
              "junior first": sorted(mailboxes, key=lambda m: (seniority[m], m))}
    rng = np.random.default_rng(SEED)
    plan = [("full", 150, 0, mailboxes)]
    for k in SIZES:
        plan += [("random", k, d, list(rng.choice(mailboxes, k, replace=False))) for d in range(DRAWS)]
        plan += [(policy, k, 0, order[:k]) for policy, order in orders.items()]
    return plan


def selection(ctx: dict, chosen: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Which network messages and which mention messages a collection keeps."""
    column = {m: j for j, m in enumerate(ctx["mailboxes"])}
    selected = np.zeros(len(ctx["mailboxes"]), bool)
    selected[[column[m] for m in chosen]] = True
    return (ctx["member_messages"] & selected).any(axis=1), (ctx["member_mentions"] & selected).any(axis=1)


def main() -> None:
    started = time.time()
    ctx = prepare(started)
    plan = plan_collections(ctx)
    rows = []
    for n, (policy, k, draw, chosen) in enumerate(plan, start=1):
        keep_messages, keep_mentions = selection(ctx, chosen)
        scores = scores_for(ctx["employees"], network_measures(ctx["edges"], ctx["senders"], keep_messages),
                            mention_measures(ctx["links"], keep_mentions), set(chosen))
        collected = pd.Index([ctx["owner"][m] for m in chosen if m in ctx["owner"]])
        rows.append({"policy": policy, "mailboxes": k, "draw": draw, "messages": int(keep_messages.sum()),
                     **accuracies(ctx["population"], scores), **ranking(scores, ctx["full"], ctx["people"], collected)})
        if n % 100 == 0 or n == len(plan):
            print(f"{n} of {len(plan)} collections, {time.time() - started:.0f} s", flush=True)

    results = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    results.to_csv(OUT / "collections.csv", index=False, float_format="%.6f")
    (OUT / "summary.json").write_text(json.dumps(summarize(results), indent=2) + "\n")
    print(json.dumps(summarize(results)["expectations"], indent=2))


def summarize(results: pd.DataFrame) -> dict:
    full = results[results["policy"] == "full"].iloc[0]
    random = results[results["policy"] == "random"]
    out = {"full": {c: round(float(full[c]), 4) for c in results.columns if "|all" in c}, "by_size": {}}
    for k, group in random.groupby("mailboxes"):
        entry = {}
        for c in [c for c in results.columns if "|" in c] + ["spearman_degree", "spearman_pagerank", "collection_bias",
                                                             "top20_overlap", "messages"]:
            values = group[c].dropna()
            entry[c] = {"median": round(float(values.median()), 4),
                        "range_95": [round(float(values.quantile(0.025)), 4), round(float(values.quantile(0.975)), 4)]}
        for policy in ("busiest first", "senior first", "junior first"):
            row = results[(results["policy"] == policy) & (results["mailboxes"] == k)].iloc[0]
            entry[policy] = {c: round(float(row[c]), 4) for c in results.columns if c.endswith("|all")}
        out["by_size"][str(int(k))] = entry
    r25 = random[random["mailboxes"] == 25]["degree|all"]
    width = 100 * (r25.quantile(0.975) - r25.quantile(0.025))
    bias = {str(int(k)): round(float((g["collection_bias"] > 0).mean()), 4) for k, g in random.groupby("mailboxes")}
    senior = {str(int(k)): bool(results[(results["policy"] == "senior first") & (results["mailboxes"] == k)]["degree|all"].iloc[0]
                                > g["degree|all"].median()) for k, g in random.groupby("mailboxes")}
    out["expectations"] = {
        "E1_range_of_degree_accuracy_at_25_points": round(float(width), 2), "E1_threshold_points": LEAD_GAP,
        "E1_met": bool(width > LEAD_GAP),
        "E2_share_of_draws_with_positive_bias": bias, "E2_met": all(v >= 0.95 for v in bias.values()),
        "E3_senior_first_above_random_median": senior, "E3_met": all(senior.values()),
    }
    return out


if __name__ == "__main__":
    main()
