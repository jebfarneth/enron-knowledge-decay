"""Collection-resistant measures (collection/PLAN_corrections.md).

On exactly Part 1's collections (`experiment.plan_collections`), computes
three measures built so that being collected adds no visibility, and Part 1's
degree and PageRank for comparison:

  anchored_degree    distinct collection owners (other than the person) the person
                     exchanged mail with, To or Cc, either direction
  anchored_strength  the same ties weighted by Part 1's 1/n message weights
  talked_about       distinct people who mention the person in messages the person
                     is not on (Paper 1's mention links with no exclusion)

A mailbox's owner is the person who is the sender or a To or Cc recipient on
the most of the person-text messages kept in that mailbox.

For each collection and measure: accuracy on Paper 1's main pairs (all and by
pair type), collection bias (collected gold employees' mean percentile in the
collection minus under the same measure on the full corpus), Spearman
correlation and top-20 overlap with the same measure on the full corpus.
Degree and PageRank must equal Part 1's results/collections.csv for every
collection, which checks that the collections are the same.

Writes collection/results/corrections.csv and corrections_summary.json.

Usage: .venv/bin/python collection/corrections.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment as ex  # noqa: E402

from enron_importance.gold_evaluation import pair_credit  # noqa: E402

MEASURES = ["degree", "pagerank", "anchored_degree", "anchored_strength", "talked_about"]
CORRECTED = ["anchored_degree", "anchored_strength", "talked_about"]


def mailbox_owners(processed: Path) -> tuple[dict[str, str], dict[str, float]]:
    """Owner of each mailbox: the person on the most of its kept person-text messages, and that share."""
    messages = pd.read_parquet(processed / "messages.parquet", columns=["path", "custodian", "to", "cc"])
    people = pd.read_parquet(processed / "sender_people.parquet", columns=["path", "sender_person", "person_text"])
    identities = pd.read_parquet(processed / "identities.parquet", columns=["address", "person_key", "entity_type"])
    persons = identities[identities["entity_type"] == "person"]
    person_of = dict(zip(persons["address"].str.lower(), persons["person_key"]))
    mail = messages.merge(people, on="path")
    mail = mail[mail["person_text"]]
    owners, shares = {}, {}
    for mailbox, group in mail.groupby("custodian"):
        counts: Counter = Counter()
        for sender, to, cc in zip(group["sender_person"], group["to"], group["cc"]):
            on = {sender} | {person_of.get(str(a).strip().lower()) for a in list(to) + list(cc)}
            counts.update(on - {None})
        person, n = counts.most_common(1)[0]
        owners[mailbox], shares[mailbox] = person, n / len(group)
    return owners, shares


def anchored(edges: pd.DataFrame, keep: np.ndarray, anchors: set[str]) -> pd.DataFrame:
    e = edges[keep[edges["message"].to_numpy()]]
    to_anchor = e[e["target"].isin(anchors)][["source", "target", "share"]].set_axis(["person", "other", "share"], axis=1)
    from_anchor = e[e["source"].isin(anchors)][["target", "source", "share"]].set_axis(["person", "other", "share"], axis=1)
    ties = pd.concat([to_anchor, from_anchor])
    ties = ties[ties["person"] != ties["other"]]
    grouped = ties.groupby("person")
    return pd.DataFrame({"anchored_degree": grouped["other"].nunique(), "anchored_strength": grouped["share"].sum()})


def talked_about(links: pd.DataFrame, keep: np.ndarray) -> pd.Series:
    l = links[keep[links["message"].to_numpy()] & links["third"].to_numpy()]
    l = l[l["sender"] != l["person"]].drop_duplicates(["sender", "person"])
    return l.groupby("person").size().rename("talked_about")


def scores(ctx: dict, keep_messages: np.ndarray, keep_mentions: np.ndarray, anchors: set[str]) -> pd.DataFrame:
    network = ctx["edges_measures"](keep_messages).set_index("person_key")
    extra = anchored(ctx["edges"], keep_messages, anchors).join(talked_about(ctx["links"], keep_mentions), how="outer")
    table = network[["degree", "pagerank"]].join(extra, how="outer")
    keys = ctx["employees"]["person_key"]
    out = pd.DataFrame(index=ctx["employees"]["gold_id"].to_numpy())
    for m in MEASURES:
        out[m] = keys.map(table[m]).fillna(0.0).to_numpy(float)
    return out


def accuracy(population: pd.DataFrame, s: pd.DataFrame) -> dict[str, float]:
    types = population["type"].to_numpy()
    out = {}
    for m in MEASURES:
        credit = pair_credit(population["dominant"].map(s[m]).to_numpy(float),
                             population["subordinate"].map(s[m]).to_numpy(float))
        for group in ex.TYPES:
            mask = np.ones(len(credit), bool) if group == "all" else types == group
            out[f"{m}|{group}"] = float(credit[mask].mean())
    return out


def stability(s: pd.DataFrame, full: pd.DataFrame, people: pd.Index, collected: pd.Index) -> dict[str, float]:
    out = {}
    inside = people.intersection(collected)
    for m in MEASURES:
        now, before = s.loc[people, m].rank(pct=True), full.loc[people, m].rank(pct=True)
        out[f"bias|{m}"] = float((now[inside] - before[inside]).mean()) if len(inside) else float("nan")
        out[f"spearman|{m}"] = ex.spearman(s.loc[people, m], full.loc[people, m])
        top_full = set(full.loc[people, m].nlargest(ex.TOP).index)
        out[f"top20|{m}"] = len(top_full & set(s.loc[people, m].nlargest(ex.TOP).index)) / ex.TOP
    return out


def summarize(results: pd.DataFrame) -> dict:
    full = results[results["policy"] == "full"].iloc[0]
    random = results[results["policy"] == "random"]
    out = {"full_corpus_accuracy": {m: round(float(full[f"{m}|all"]), 4) for m in MEASURES}, "by_size": {}}
    for k, group in random.groupby("mailboxes"):
        entry = {}
        for m in MEASURES:
            entry[m] = {}
            for metric in (f"{m}|all", f"bias|{m}", f"spearman|{m}", f"top20|{m}"):
                v = group[metric].dropna()
                entry[m][metric.split("|")[0] if "|" in metric and metric.split("|")[0] != m else "accuracy"] = {
                    "median": round(float(v.median()), 4),
                    "range_95": [round(float(v.quantile(0.025)), 4), round(float(v.quantile(0.975)), 4)]}
        out["by_size"][str(int(k))] = entry
    closer = lambda m: {str(int(k)): bool(abs(g[f"bias|{m}"].median()) < abs(g["bias|degree"].median()))  # noqa: E731
                        for k, g in random.groupby("mailboxes")}
    r25 = random[random["mailboxes"] == 25]
    width = lambda m: round(float(100 * (r25[f"{m}|all"].quantile(0.975) - r25[f"{m}|all"].quantile(0.025))), 2)  # noqa: E731
    f1, f2 = closer("anchored_degree"), closer("talked_about")
    out["expectations"] = {
        "F1_anchored_degree_bias_closer_to_zero_than_degree": f1, "F1_met": all(f1.values()),
        "F2_talked_about_bias_closer_to_zero_than_degree": f2, "F2_met": all(f2.values()),
        "F3_range_at_25_points": {"anchored_degree": width("anchored_degree"), "degree": width("degree")},
        "F3_met": width("anchored_degree") < width("degree"),
    }
    return out


def main() -> None:
    started = time.time()
    ctx = ex.prepare(started)
    processed = ctx["config"]["paths"]["processed"]
    owners, shares = mailbox_owners(processed)
    print(f"mailbox owners: {len(owners)} mapped; skilling-j -> {owners.get('skilling-j')}; "
          f"weakest {min(shares, key=shares.get)} ({min(shares.values()):.0%})", flush=True)
    ctx["edges_measures"] = lambda keep: ex.network_measures(ctx["edges"], ctx["senders"], keep)
    everything = np.ones(len(ctx["messages"]), bool), np.ones(len(ctx["member_mentions"]), bool)
    full = scores(ctx, *everything, set(owners.values()))
    part1 = pd.read_csv(ex.OUT / "collections.csv")
    rows = []
    plan = ex.plan_collections(ctx)
    for n, (policy, k, draw, chosen) in enumerate(plan, start=1):
        keep_messages, keep_mentions = ex.selection(ctx, chosen)
        s = scores(ctx, keep_messages, keep_mentions, {owners[m] for m in chosen})
        collected = pd.Index([ctx["owner"][m] for m in chosen if m in ctx["owner"]])
        row = {"policy": policy, "mailboxes": k, "draw": draw, **accuracy(ctx["population"], s),
               **stability(s, full, ctx["people"], collected)}
        before = part1[(part1["policy"] == policy) & (part1["mailboxes"] == k) & (part1["draw"] == draw)].iloc[0]
        for mine, theirs in (("degree|all", "degree|all"), ("pagerank|all", "pagerank|all"),
                             ("bias|pagerank", "collection_bias")):
            if abs(row[mine] - before[theirs]) > 1e-5:
                raise SystemExit(f"{policy} k={k} draw={draw}: {mine} {row[mine]:.6f} differs from Part 1 {before[theirs]:.6f}")
        rows.append(row)
        if n % 100 == 0 or n == len(plan):
            print(f"{n} of {len(plan)} collections, {time.time() - started:.0f} s", flush=True)
    results = pd.DataFrame(rows)
    results.to_csv(ex.OUT / "corrections.csv", index=False, float_format="%.6f")
    summary = summarize(results)
    (ex.OUT / "corrections_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["expectations"], indent=2))


if __name__ == "__main__":
    main()
