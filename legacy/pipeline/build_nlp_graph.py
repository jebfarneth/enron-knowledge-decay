#!/usr/bin/env python3
"""
build_nlp_graph.py

Builds the Enron organizational knowledge graph from a preprocessed email
parquet file. The pipeline fits a BERTopic model on a sampled subset of emails,
assigns topics across the full corpus, builds per-person expertise profiles,
and exports a weighted communication graph for downstream dashboard generation.

Inputs:
    enron_emails.parquet

Outputs:
    topic_words.json
    bertopic_model/
    sample_embeddings.npy
    full_embeddings.npy
    expertise_profiles.parquet
    knowledge_graph.graphml

Usage:
    python pipeline/build_nlp_graph.py

Notes:
    Large generated artifacts are intentionally excluded from GitHub via
    .gitignore. This file is included to document and reproduce the analytical
    pipeline behind the dashboard.
"""

import warnings
warnings.filterwarnings("ignore")

import json
import os

import networkx as nx
import numpy as np
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer


SAMPLE_EMBEDDINGS_FILE = "sample_embeddings.npy"
FULL_EMBEDDINGS_FILE = "full_embeddings.npy"
SAMPLE_SIZE = 50_000
CHUNK = 10_000


def main():
    # ── 1. Load & filter ──────────────────────────────────────────────────────────
    print("[1/7] Loading enron_emails.parquet...")
    df = pd.read_parquet("enron_emails.parquet")
    print(f"  Raw rows: {len(df):,}")

    df["date"] = pd.to_datetime(df["date"], utc=True)
    start = pd.Timestamp("1998-01-01", tz="UTC")
    end = pd.Timestamp("2002-12-31 23:59:59", tz="UTC")
    df = df[(df["date"] >= start) & (df["date"] <= end)]
    print(f"  After date filter: {len(df):,}")

    df = df.dropna(subset=["from", "to"])
    df["from"] = df["from"].str.strip().str.lower()
    print(f"  After dropping null from/to: {len(df):,}")

    # ── 2. Fit BERTopic on 50k sample ─────────────────────────────────────────────
    print(f"\n[2/7] Sampling {SAMPLE_SIZE:,} emails for BERTopic fitting...")
    sample = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42).copy()
    sample["body"] = sample["body"].fillna("").astype(str)
    sample_docs = sample["body"].tolist()

    print("  Loading sentence-transformer model (all-MiniLM-L6-v2)...")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    if os.path.exists(SAMPLE_EMBEDDINGS_FILE):
        print(f"  Loading cached sample embeddings from {SAMPLE_EMBEDDINGS_FILE}...")
        sample_embeddings = np.load(SAMPLE_EMBEDDINGS_FILE)
    else:
        print(f"  Computing sample embeddings ({len(sample_docs):,} docs)...")
        sample_embeddings = embedding_model.encode(
            sample_docs, show_progress_bar=True, batch_size=64
        )
        np.save(SAMPLE_EMBEDDINGS_FILE, sample_embeddings)
        print(f"  Saved sample embeddings to {SAMPLE_EMBEDDINGS_FILE}")

    print("  Fitting BERTopic on pre-computed sample embeddings...")
    topic_model = BERTopic(
        embedding_model=embedding_model,
        language="english",
        min_topic_size=30,
        verbose=False,
    )
    sample_topics, _ = topic_model.fit_transform(sample_docs, embeddings=sample_embeddings)

    print("\n  Top 10 topics:")
    topic_info = topic_model.get_topic_info()
    top_topics = topic_info[topic_info["Topic"] != -1].head(10)
    topic_words_dict = {}
    for _, row in top_topics.iterrows():
        tid = row["Topic"]
        words = [w for w, _ in topic_model.get_topic(tid)[:8]]
        topic_words_dict[str(tid)] = words
        print(f"  Topic {tid:3d} (count={row['Count']:,}): {', '.join(words)}")

    # Save all topic words for dashboard
    all_topic_rows = topic_info[topic_info["Topic"] != -1]
    all_topic_words = {}
    for _, row in all_topic_rows.iterrows():
        tid = int(row["Topic"])
        all_topic_words[str(tid)] = [w for w, _ in topic_model.get_topic(tid)[:8]]
    with open("topic_words.json", "w") as f:
        json.dump(all_topic_words, f)
    print(f"  Saved topic_words.json ({len(all_topic_words)} topics)")

    # Save model so export_dashboard_data.py can reload topic words without re-fitting
    topic_model.save("bertopic_model", serialization="pickle", save_ctfidf=True)
    print("  Saved bertopic_model/")

    # ── 3. Transform full dataset ─────────────────────────────────────────────────
    print(f"\n[3/7] Transforming full dataset ({len(df):,} emails) with trained model...")
    df["body"] = df["body"].fillna("").astype(str)
    full_docs = df["body"].tolist()

    n_chunks = (len(full_docs) + CHUNK - 1) // CHUNK

    if os.path.exists(FULL_EMBEDDINGS_FILE):
        print(f"  Loading cached full embeddings from {FULL_EMBEDDINGS_FILE}...")
        full_embeddings = np.load(FULL_EMBEDDINGS_FILE)
    else:
        print(f"  Computing full dataset embeddings in {n_chunks} chunks...")
        chunk_arrays = []
        for i in range(0, len(full_docs), CHUNK):
            chunk_embs = embedding_model.encode(
                full_docs[i : i + CHUNK], show_progress_bar=False, batch_size=64
            )
            chunk_arrays.append(chunk_embs)
            if (i // CHUNK) % 5 == 0:
                print(f"  Embedded {min(i + CHUNK, len(full_docs)):,} / {len(full_docs):,}")
        full_embeddings = np.vstack(chunk_arrays)
        np.save(FULL_EMBEDDINGS_FILE, full_embeddings)
        print(f"  Saved full embeddings to {FULL_EMBEDDINGS_FILE}")

    all_topics = []
    for i in range(0, len(full_docs), CHUNK):
        chunk_topics, _ = topic_model.transform(
            full_docs[i : i + CHUNK],
            embeddings=full_embeddings[i : i + CHUNK],
        )
        all_topics.extend(chunk_topics)
        if (i // CHUNK) % 5 == 0:
            print(f"  Transformed {min(i + CHUNK, len(full_docs)):,} / {len(full_docs):,}")

    df["topic"] = all_topics
    print(f"  Done. Unique topics assigned: {df['topic'].nunique()}")

    # ── 4. Expertise profiles ─────────────────────────────────────────────────────
    print("\n[4/7] Building per-person expertise profiles...")

    # Keep only emails with a real topic (not -1 outlier)
    df_topics = df[df["topic"] != -1].copy()

    expertise_raw = (
        df_topics.groupby(["from", "topic"])
        .size()
        .reset_index(name="count")
    )

    # Normalize per person: each topic score = count / max_count_for_that_person
    def normalize_group(grp):
        mx = grp["count"].max()
        grp = grp.copy()
        grp["score"] = grp["count"] / mx if mx > 0 else 0.0
        return grp

    expertise = (
        expertise_raw
        .groupby("from", group_keys=False)
        .apply(normalize_group)
        .reset_index(drop=True)
    )

    expertise.to_parquet("expertise_profiles.parquet", index=False)
    print(f"  Saved expertise_profiles.parquet ({len(expertise):,} rows, "
          f"{expertise['from'].nunique():,} unique senders)")

    # Build a dict: person -> {topic_id: score} for node attributes
    expertise_dict = (
        expertise.groupby("from")
        .apply(lambda g: dict(zip(g["topic"].astype(str), g["score"])))
        .to_dict()
    )

    # ── 5. Build NetworkX graph ───────────────────────────────────────────────────
    print("\n[5/7] Building NetworkX graph...")

    # Explode multi-recipient 'to' field
    df["to_list"] = df["to"].str.split(",")
    edges_df = df[["from", "to_list"]].explode("to_list")
    edges_df["to_list"] = edges_df["to_list"].str.strip().str.lower()
    edges_df = edges_df[edges_df["to_list"].str.len() > 0].dropna(subset=["to_list"])
    # Remove self-loops
    edges_df = edges_df[edges_df["from"] != edges_df["to_list"]]

    print(f"  Edge pairs (before aggregation): {len(edges_df):,}")

    edge_weights = (
        edges_df.groupby(["from", "to_list"])
        .size()
        .reset_index(name="weight")
    )
    print(f"  Unique directed edges: {len(edge_weights):,}")

    G = nx.Graph()

    # Add nodes with expertise attributes
    all_senders = df["from"].unique().tolist()
    for person in all_senders:
        topics_attr = expertise_dict.get(person, {})
        G.add_node(person, topics=json.dumps(topics_attr))

    # Add edges (undirected: combine both directions by summing weights)
    for _, row in edge_weights.iterrows():
        src, dst, w = row["from"], row["to_list"], row["weight"]
        if G.has_edge(src, dst):
            G[src][dst]["weight"] += w
        else:
            G.add_edge(src, dst, weight=w)

    print(f"  Nodes: {G.number_of_nodes():,}  |  Edges: {G.number_of_edges():,}")

    nx.write_graphml(G, "knowledge_graph.graphml")
    print("  Saved knowledge_graph.graphml")

    # ── 6. Summary stats ──────────────────────────────────────────────────────────
    print("\n[6/7] Computing summary statistics...")

    print(f"\n  Graph summary:")
    print(f"    Nodes : {G.number_of_nodes():,}")
    print(f"    Edges : {G.number_of_edges():,}")

    print("\n  Top 10 people by betweenness centrality (using degree as proxy for speed):")
    degree_centrality = nx.degree_centrality(G)
    top_central = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    for rank, (person, score) in enumerate(top_central, 1):
        print(f"    {rank:2d}. {person:<45s}  centrality={score:.4f}")

    print("\n  Top 10 topics by total email count:")
    topic_counts = df[df["topic"] != -1]["topic"].value_counts().head(10)
    for tid, cnt in topic_counts.items():
        words = [w for w, _ in topic_model.get_topic(int(tid))[:6]]
        print(f"    Topic {tid:3d}  ({cnt:,} emails): {', '.join(words)}")

    print("\n[7/7] All done.")
    print("  Outputs: expertise_profiles.parquet, knowledge_graph.graphml")


if __name__ == "__main__":
    main()
