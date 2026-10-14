"""Name resolution inside each collection (collection/PLAN_resolution.md, Part 3).

Parts 1 and 2 rebuilt the mention measures from Paper 1's resolved mention
links, and those links were resolved with the whole corpus: a name's
candidates were everyone in the full email network, and the closest one was
found with full-network hop distances. An analyst holding only some mailboxes
would know only the people in those mailboxes' network. This script resolves
every name again inside each collection, with `mentions.py`'s own rules
(`name_index`, `compatible`, `nil_reason`, `Distances.resolve`) applied to the
collection's network, and recomputes Paper 1's mention measures and talked
about from the new links.

Before anything else it checks that resolving inside the full collection
reproduces `mentions.parquet` row for row, exclusions included. For every
collection it also recomputes the measures from Paper 1's links and checks
them against Part 1's and Part 2's results, so the collections are the same.

The spaCy tags are read from the run's tag cache (`mention_tags.parquet`,
through `cached_mentions`), so nothing is tagged again.

Writes collection/results/resolution.csv and resolution_summary.json.

Usage: .venv/bin/python collection/resolution.py [--workers 3] [--limit N]
"""

from __future__ import annotations

import argparse
import gc
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corrections as co  # noqa: E402
import experiment as ex  # noqa: E402

from enron_importance.gold_evaluation import pair_credit  # noqa: E402
from enron_importance.identity import extra_recipients, resolve_recipient  # noqa: E402
from enron_importance.mentions import Distances, cached_mentions, compatible, name_index, nil_reason  # noqa: E402

MEASURES = ["mention_degree", "mentioned_to", "third_party_mentioned_to", "talked_about"]
ALL_DRAWS = {10, 25}    # sizes run with all 200 random draws; larger sizes run the first LARGE_DRAWS (PLAN, scope)
LARGE_DRAWS = 50
CTX: dict = {}


def tagged_messages(config: dict) -> pd.DataFrame:
    """The messages `mentions.main` resolves, prepared exactly as it prepares them."""
    import spacy

    processed = config["paths"]["processed"]
    messages = pd.read_parquet(processed / "messages.parquet",
                               columns=["path", "to", "cc", "to_extra", "cc_extra", "authored", "analysis"])
    messages = messages[messages["analysis"]].merge(pd.read_parquet(processed / "sender_people.parquet"), on="path")
    messages = messages[messages["sender_person"].notna()].reset_index(drop=True)
    identities = pd.read_parquet(processed / "identities.parquet")
    address_person = dict(zip(identities["address"], identities["person_key"]))
    types = pd.read_parquet(processed / "person_types.parquet")
    people = set(types.loc[types["entity_type"] == "person", "person_key"])
    resolve = lambda a: resolve_recipient(a, address_person, people)  # noqa: E731
    messages["to_people"] = messages["to"].map(lambda xs: [p for p in map(resolve, xs) if p])
    messages["cc_people"] = [
        [p for p in map(resolve, cc) if p] + extra_recipients([p for p in map(resolve, list(to) + list(cc)) if p],
                                                              list(te) + list(ce), resolve, people)
        for to, cc, te, ce in zip(messages["to"], messages["cc"], messages["to_extra"], messages["cc_extra"])
    ]
    nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer", "attribute_ruler", "tagger", "tok2vec"])
    messages["mentions"] = cached_mentions(messages, processed / "mention_tags.parquet", nlp)
    messages.attrs["people"] = people
    return messages


def compile_mentions(messages: pd.DataFrame, index: dict) -> list[tuple]:
    """Per message: (sender, recipients, [(mention, reason, full-corpus candidates)]); collection-independent parts."""
    candidates: dict[str, frozenset] = {}
    compiled = []
    person_text = messages["person_text"] if "person_text" in messages else pd.Series(True, index=messages.index)
    for sender, to, cc, mentions, own, text in zip(messages["sender_person"], messages["to_people"],
                                                   messages["cc_people"], messages["mentions"], person_text,
                                                   messages["authored"]):
        recipients = [r for r in dict.fromkeys(list(to) + list(cc)) if r != sender]
        items = []
        for mention, start in mentions:
            if mention not in candidates:
                candidates[mention] = frozenset(compatible(mention, index))
            reason = None if own else "not_person_text"
            items.append((mention, reason or nil_reason(mention, text, start), candidates[mention]))
        compiled.append((sender, recipients, items))
    return compiled


def resolve_links(compiled: list[tuple], paths: pd.Series, keep: np.ndarray, known: set[str] | None,
                  distances: Distances, main_only: bool) -> pd.DataFrame:
    """`mentions.mention_links` over the kept messages, candidates limited to `known` (None: no limit)."""
    rows, memo = [], {}
    for i in np.flatnonzero(keep):
        sender, recipients, items = compiled[i]
        for mention, reason, full in items:
            candidates = full if known is None else full & known
            if not candidates or (main_only and reason):
                continue
            for recipient in recipients:
                key = (sender, recipient, mention)
                if key not in memo:
                    memo[key] = distances.resolve(sender, recipient, set(candidates))
                person = memo[key]
                if person is None:
                    continue
                excluded = reason or ("self" if person == sender else None)
                if main_only and excluded:
                    continue
                rows.append((i, paths.iat[i], sender, recipient, mention, person, excluded))
    return pd.DataFrame(rows, columns=["message", "path", "sender", "recipient", "mention", "person", "excluded"])


def measures(links: pd.DataFrame, parties: list[set]) -> pd.DataFrame:
    """Paper 1's three mention measures and Part 2's talked about from main links (no exclusion, not to oneself)."""
    l = links[links["excluded"].isna() & (links["recipient"] != links["person"])].copy()
    l["third"] = [p not in parties[m] for m, p in zip(l["message"], l["person"])]
    everything = np.ones(len(parties), bool)
    out = ex.mention_measures(l, everything).set_index("person_key")
    return out.join(co.talked_about(l, everything), how="outer").fillna(0.0)


def score(table: pd.DataFrame) -> pd.DataFrame:
    keys = CTX["employees"]["person_key"]
    s = pd.DataFrame(index=CTX["employees"]["gold_id"].to_numpy())
    for m in MEASURES:
        s[m] = keys.map(table[m]).fillna(0.0).to_numpy(float) if m in table else 0.0
    return s


def accuracy(s: pd.DataFrame, prefix: str = "") -> dict[str, float]:
    population = CTX["population"]
    types = population["type"].to_numpy()
    out = {}
    for m in MEASURES:
        credit = pair_credit(population["dominant"].map(s[m]).to_numpy(float),
                             population["subordinate"].map(s[m]).to_numpy(float))
        for group in ex.TYPES:
            mask = np.ones(len(credit), bool) if group == "all" else types == group
            out[f"{prefix}{m}|{group}"] = float(credit[mask].mean())
    return out


def stability(s: pd.DataFrame, collected: pd.Index) -> dict[str, float]:
    people, full = CTX["people"], CTX["full_scores"]
    inside = people.intersection(collected)
    out = {}
    for m in ("mentioned_to", "talked_about"):
        now, before = s.loc[people, m].rank(pct=True), full.loc[people, m].rank(pct=True)
        out[f"bias|{m}"] = float((now[inside] - before[inside]).mean()) if len(inside) else float("nan")
        out[f"spearman|{m}"] = ex.spearman(s.loc[people, m], full.loc[people, m])
        top_full = set(full.loc[people, m].nlargest(ex.TOP).index)
        out[f"top20|{m}"] = len(top_full & set(s.loc[people, m].nlargest(ex.TOP).index)) / ex.TOP
    return out


def run_one(item: tuple) -> dict:
    policy, k, draw, chosen = item
    keep_messages, keep_mentions = ex.selection(CTX, chosen)
    # Paper 1's links (full-corpus resolution), for the check against Parts 1 and 2 and the paired comparison.
    before = score(CTX["old_measures"](keep_mentions))
    # The collection's own network, people and distances.
    e = CTX["edges"][keep_messages[CTX["edges"]["message"].to_numpy()]]
    pairs = e[["source", "target"]].drop_duplicates()
    known = CTX["people_set"] & (set(pairs["source"]) | set(pairs["target"]))
    column = {m: j for j, m in enumerate(CTX["mailboxes"])}
    selected = np.zeros(len(CTX["mailboxes"]), bool)
    selected[[column[m] for m in chosen]] = True
    keep_tagged = (CTX["member_tagged"] & selected).any(axis=1)
    links = resolve_links(CTX["compiled"], CTX["paths"], keep_tagged, known, Distances(pairs), main_only=True)
    after = score(measures(links, CTX["parties"]))
    collected = pd.Index([CTX["owner"][m] for m in chosen if m in CTX["owner"]])
    return {"policy": policy, "mailboxes": k, "draw": draw, "links": len(links),
            "links_full_resolution": int(CTX["old_link_counts"](keep_mentions)), "people_known": len(known),
            **accuracy(after), **accuracy(before, "full_resolution:"), **stability(after, collected)}


def prepare(started: float) -> None:
    ctx = ex.prepare(started)
    config = ctx["config"]
    processed = config["paths"]["processed"]
    messages = tagged_messages(config)
    people = messages.attrs["people"]
    full_edges = pd.read_parquet(processed / "edges.parquet")
    graph_people = people & (set(full_edges["source"]) | set(full_edges["target"]))
    compiled = compile_mentions(messages, name_index(graph_people))
    print(f"tagged messages: {len(messages):,}; {time.time() - started:.0f} s", flush=True)

    # Check: resolving inside the full collection reproduces mentions.parquet row for row.
    links = resolve_links(compiled, messages["path"], np.ones(len(messages), bool), None, Distances(full_edges),
                          main_only=False)
    reference = pd.read_parquet(processed / "mentions.parquet")
    columns = ["path", "sender", "recipient", "mention", "person", "excluded"]
    mine = links[columns].fillna("").reset_index(drop=True)
    theirs = reference[columns].fillna("").reset_index(drop=True)
    if not (len(mine) == len(theirs) and (mine.to_numpy() == theirs.to_numpy()).all()):
        raise SystemExit(f"full-collection resolution does not reproduce mentions.parquet ({len(mine):,} vs {len(theirs):,})")
    # The same check with the collection code path: full graph people as the known set, main rows only.
    main = resolve_links(compiled, messages["path"], np.ones(len(messages), bool), graph_people,
                         Distances(full_edges[["source", "target"]]), main_only=True)
    expected = reference[reference["excluded"].isna()]
    if len(main) != len(expected) or not (main[["path", "recipient", "mention", "person"]].to_numpy()
                                          == expected[["path", "recipient", "mention", "person"]].to_numpy()).all():
        raise SystemExit("the collection code path does not reproduce mentions.parquet's main rows")
    print(f"check passed: resolution reproduces mentions.parquet ({len(links):,} links); "
          f"{time.time() - started:.0f} s", flush=True)

    holders: dict[str, set[str]] = {}
    copies = pd.read_parquet(processed / "copies.parquet")
    shifted = pd.read_parquet(processed / "messages.parquet", columns=["path", "probable_copy_of"]).dropna()
    for path, original in list(zip(copies["path"], copies["kept_path"])) + list(zip(shifted["path"], shifted["probable_copy_of"])):
        holders.setdefault(original, {ex.custodian_of(original)}).add(ex.custodian_of(path))
    parties = [{s, *t, *c} for s, t, c in zip(messages["sender_person"], messages["to_people"], messages["cc_people"])]

    CTX.update(ctx)
    CTX.update({"compiled": compiled, "paths": messages["path"], "parties": parties, "people_set": people,
                "member_tagged": ex.membership(messages["path"], holders, ctx["mailboxes"])})
    old = ctx["links"]
    CTX["old_measures"] = lambda keep: ex.mention_measures(old, keep).set_index("person_key").join(
        co.talked_about(old, keep), how="outer").fillna(0.0)
    CTX["old_link_counts"] = lambda keep: keep[old["message"].to_numpy()].sum()
    full_scores = score(measures(main, parties))
    if not np.allclose(full_scores.to_numpy(), score(CTX["old_measures"](np.ones(len(ctx["member_mentions"]), bool))).to_numpy()):
        raise SystemExit("full-collection measures differ from Paper 1's")
    CTX["full_scores"] = full_scores


def in_scope(plan: list[tuple]) -> list[tuple]:
    """The full corpus, the ordered collections, all random draws at 10 and 25, the first 50 above."""
    return [p for p in plan if p[0] != "random" or p[1] in ALL_DRAWS or p[2] < LARGE_DRAWS]


def check_against_parts(results: pd.DataFrame) -> None:
    """Measures from Paper 1's links must equal Part 1's and Part 2's results for every collection."""
    keys = ["policy", "mailboxes", "draw"]
    part1 = pd.read_csv(ex.OUT / "collections.csv").set_index(keys)
    part2 = pd.read_csv(ex.OUT / "corrections.csv").set_index(keys)
    r = results.set_index(keys)
    for mine, table, theirs in (("mentioned_to|all", part1, "mentioned_to|all"),
                                ("mention_degree|all", part1, "mention_degree|all"),
                                ("third_party_mentioned_to|all", part1, "third_party_mentioned_to|all"),
                                ("talked_about|all", part2, "talked_about|all")):
        gap = (r[f"full_resolution:{mine}"] - table.loc[r.index, theirs]).abs().max()
        if gap > 1e-5:
            raise SystemExit(f"{mine}: full-resolution values differ from earlier results by {gap:.6f}")


def summarize(results: pd.DataFrame) -> dict:
    keys = ["policy", "mailboxes", "draw"]
    random = results[results["policy"] == "random"]
    # Degree on exactly the same collections (Part 2's results).
    degree = pd.read_csv(ex.OUT / "corrections.csv").merge(random[keys], on=keys)
    out = {"collections": len(results), "random_draws": random.groupby("mailboxes").size().to_dict(), "by_size": {}}
    band = lambda v: {"median": round(float(v.median()), 4),  # noqa: E731
                      "range_95": [round(float(v.quantile(0.025)), 4), round(float(v.quantile(0.975)), 4)]}
    for k, group in random.groupby("mailboxes"):
        entry = {}
        for m in MEASURES:
            entry[m] = {"in_collection": band(group[f"{m}|all"]), "full_corpus_resolution": band(group[f"full_resolution:{m}|all"]),
                        "median_paired_change": round(float((group[f"{m}|all"] - group[f"full_resolution:{m}|all"]).median()), 4)}
        for m in ("mentioned_to", "talked_about"):
            entry[m].update({"bias": band(group[f"bias|{m}"].dropna()), "spearman": band(group[f"spearman|{m}"]),
                             "top20": band(group[f"top20|{m}"])})
        entry["links_kept_share"] = band(group["links"] / group["links_full_resolution"])
        out["by_size"][str(int(k))] = entry
    width = lambda v: round(float(100 * (v.quantile(0.975) - v.quantile(0.025))), 2)  # noqa: E731
    r25 = random[random["mailboxes"] == 25]
    d25 = degree[degree["mailboxes"] == 25]
    closer = {str(int(k)): bool(abs(g["bias|talked_about"].median())
                                < abs(degree[degree["mailboxes"] == k]["bias|degree"].median()))
              for k, g in random.groupby("mailboxes")}
    out["expectations"] = {
        "R1_range_at_25_points": {"talked_about_in_collection": width(r25["talked_about|all"]),
                                  "talked_about_full_corpus_resolution": width(r25["full_resolution:talked_about|all"]),
                                  "degree": width(d25["degree|all"])},
        "R1_met": width(r25["talked_about|all"]) < width(d25["degree|all"]),
        "R2_talked_about_bias_closer_to_zero_than_degree": closer, "R2_met": all(closer.values()),
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None, help="time the first N collections only; writes nothing")
    args = parser.parse_args()
    started = time.time()
    prepare(started)
    plan = in_scope(ex.plan_collections(CTX))
    print(f"{len(plan)} collections in scope", flush=True)
    if args.limit:
        sample = [plan[0]] + [p for p in plan if p[0] == "random" and p[1] == 25][:args.limit]
        for item in sample:
            t = time.time()
            row = run_one(item)
            print(f"{item[0]} k={item[1]}: {row['links']:,} links, {time.time() - t:.1f} s", flush=True)
        return
    rows = []
    for name in ("messages", "senders"):   # not needed by run_one; less memory to share with the workers
        CTX.pop(name, None)
    gc.collect()
    gc.freeze()   # keeps the workers from copying shared objects when the collector runs
    with mp.get_context("fork").Pool(args.workers) as pool:
        for n, row in enumerate(pool.imap(run_one, plan, chunksize=4), start=1):
            rows.append(row)
            if n % 50 == 0 or n == len(plan):
                print(f"{n} of {len(plan)} collections, {time.time() - started:.0f} s", flush=True)
    results = pd.DataFrame(rows)
    check_against_parts(results)
    results.to_csv(ex.OUT / "resolution.csv", index=False, float_format="%.6f")
    summary = summarize(results)
    (ex.OUT / "resolution_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["expectations"], indent=2))


if __name__ == "__main__":
    main()
