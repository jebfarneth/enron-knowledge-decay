"""Signals and baselines measured before each absence (PLAN.md, "Signals"; decisions 4 to 9).

For each absence, over the `days` days before its first day away (56; 182 for
the sensitivity run), from internal person-text mail:

  sent, received    messages the person sent; messages with the person in To
  degree            distinct people the person exchanged mail with (To or Cc)
  betweenness       exact betweenness on the undirected people graph, a message to n
                    people adding 1/n to each of its edges and edge length 1/weight
  constraint        Burt's constraint on the same weighted graph (1 when the person
                    has no edge)
  topic_ownership   the person's largest share of a topic's messages, among topics
                    with at least 20 messages in the window (0 when none)
  pointed_to        messages pointing a reader to the person (`referrals.py`)
  named_backup      absence notices by other people naming the person as covering

Topics: scikit-learn KMeans (k = 100, random_state 20261013, n_init 1) on the
search embeddings, fitted once; the embeddings' stamp must match the main
pipeline's manifest.

Signals are computed for absences of people who sent at least 10 person-text
messages in the 56 days before (every absence the main sample or a sensitivity
run uses), for 56 days, and for 182 days for the main sample.

Writes data/topics.parquet and data/signals.parquet.

Usage: uv run python -m enron_functional.signals
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
from collections import defaultdict

import igraph as ig
import numpy as np
import pandas as pd

from .config import ROOT, load_config
from .corpus import MAIL_SOURCES, certified_sources, person_mail

K_TOPICS = 100
SEED = 20261013
MIN_TOPIC_MESSAGES = 20
SEARCH_DATA = ROOT.parent / "search" / "data"

_STATE: dict = {}


def fit_topics(source, data) -> pd.DataFrame:
    """Topic of every person-text message, from the search embeddings (fitted once, then reused)."""
    out = data / "topics.parquet"
    if out.exists():
        return pd.read_parquet(out)
    from sklearn.cluster import KMeans
    stamp = json.loads((SEARCH_DATA / "embeddings.json").read_text())
    manifest = json.loads((source / "manifest.json").read_text())
    recorded = {name: digest for stage in manifest["stages"].values() for name, digest in stage["outputs"].items()}
    for name, digest in stamp["sources"].items():
        if recorded.get(name) != digest:
            raise RuntimeError(f"the search embeddings were built from another {name}; rerun make -C search embed")
    vectors = np.load(SEARCH_DATA / "embeddings.npy")
    if hashlib.sha256(vectors.tobytes()).hexdigest() != stamp["embeddings_sha256"]:
        raise RuntimeError("embeddings.npy does not match its stamp")
    rows = pd.read_parquet(SEARCH_DATA / "rows.parquet", columns=["path"])
    labels = KMeans(n_clusters=K_TOPICS, random_state=SEED, n_init=1).fit_predict(vectors)
    topics = pd.DataFrame({"path": rows["path"], "topic": labels.astype(np.int16)})
    topics.to_parquet(out, index=False)
    return topics


def _init(source, data) -> None:
    mail = person_mail(source)
    mail["day"] = mail["local"].dt.normalize()
    mail = mail.merge(pd.read_parquet(data / "topics.parquet"), on="path", how="left")
    referrals = pd.read_parquet(data / "referrals.parquet", columns=["date", "person"])
    referrals["day"] = referrals["date"].dt.tz_convert("America/Chicago").dt.tz_localize(None).dt.normalize()
    notices = pd.read_parquet(data / "absence_notices.parquet", columns=["date", "absent", "backups"])
    notices["day"] = notices["date"].dt.tz_convert("America/Chicago").dt.tz_localize(None).dt.normalize()
    _STATE.update(mail=mail.sort_values("day").reset_index(drop=True), referrals=referrals, notices=notices)


def window_measures(task: tuple[pd.Timestamp, int, list[str]]) -> list[dict]:
    """Signals and baselines of `people` over the `days` days before `end`."""
    end, days, people = task
    begin = end - pd.Timedelta(days=days)
    mail = _STATE["mail"]
    w = mail.iloc[np.searchsorted(mail["day"].values, np.datetime64(begin)):
                  np.searchsorted(mail["day"].values, np.datetime64(end))]
    weight: dict[tuple[str, str], float] = defaultdict(float)
    for sender, to, cc in zip(w["sender_person"], w["to_people"], w["cc_people"]):
        recipients = list(to) + list(cc)
        for r in recipients:
            pair = (sender, r) if sender < r else (r, sender)
            weight[pair] += 1.0 / len(recipients)
    edges = sorted(weight.items())
    graph = ig.Graph.TupleList(((a, b, v) for (a, b), v in edges), directed=False, edge_attrs=["weight"])
    index = {name: i for i, name in enumerate(graph.vs["name"])} if graph.vcount() else {}
    between = graph.betweenness(weights=[1.0 / v for v in graph.es["weight"]], directed=False) if graph.ecount() else []
    constraint = graph.constraint(weights="weight") if graph.ecount() else []
    topic_size = w["topic"].value_counts()
    eligible = set(topic_size[topic_size >= MIN_TOPIC_MESSAGES].index)
    by_sender = w[w["topic"].isin(eligible)].groupby(["sender_person", "topic"]).size()
    received = w.explode("to_people")["to_people"].value_counts()
    sent = w["sender_person"].value_counts()
    ref = _STATE["referrals"]
    pointed = ref[(ref["day"] >= begin) & (ref["day"] < end)]["person"].value_counts()
    notes = _STATE["notices"]
    notes = notes[(notes["day"] >= begin) & (notes["day"] < end)]
    rows = []
    for person in people:
        i = index.get(person)
        shares = (by_sender[person] / topic_size.reindex(by_sender[person].index)) if person in by_sender.index else None
        c = constraint[i] if i is not None else float("nan")
        rows.append({"person": person, "end": end, "days": days, "sent": int(sent.get(person, 0)),
                     "received": int(received.get(person, 0)),
                     "degree": graph.degree(i) if i is not None else 0,
                     "betweenness": between[i] if i is not None else 0.0,
                     "constraint": 1.0 if c != c else c,
                     "topic_ownership": float(shares.max()) if shares is not None and len(shares) else 0.0,
                     "pointed_to": int(pointed.get(person, 0)),
                     "named_backup": int(sum(person in b for a, b in zip(notes["absent"], notes["backups"])
                                             if a != person))})
    return rows


def main() -> None:
    config = load_config()
    source, data = config["paths"]["source"], config["paths"]["data"]
    certified_sources(source, MAIL_SOURCES)
    fit_topics(source, data)
    windows = pd.read_parquet(data / "windows.parquet")
    away = windows[(windows["window"] == "away") & (windows["baseline_sent"] >= 10)]
    main_sample = away["main_period"] & ~away["holiday_week"] & (away["baseline_sent"] >= 20)
    tasks = [(end, 56, sorted(set(group["person"]))) for end, group in away.groupby("start")]
    tasks += [(end, 182, sorted(set(group["person"]))) for end, group in away[main_sample].groupby("start")]
    tasks.sort(key=lambda t: (t[1], t[0]))
    rows = []
    with mp.get_context("spawn").Pool(2, initializer=_init, initargs=(source, data)) as pool:
        for done, result in enumerate(pool.imap_unordered(window_measures, tasks), start=1):
            rows += result
            if done % 25 == 0 or done == len(tasks):
                print(f"{done} of {len(tasks)} windows", flush=True)
    measures = pd.DataFrame(rows)
    signals = away[["absence_id", "person", "start"]].merge(
        measures.rename(columns={"end": "start"}), on=["person", "start"], how="inner")
    signals.to_parquet(data / "signals.parquet", index=False)
    print(f"{len(signals):,} rows: {signals.groupby('days').size().to_dict()}")


if __name__ == "__main__":
    main()
