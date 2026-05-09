import warnings
warnings.filterwarnings("ignore")

import json
import time
import numpy as np
import pandas as pd
import networkx as nx

wall_start = time.time()

# ── 1. Load data ───────────────────────────────────────────────────────────────
print("[1/7] Loading graph and expertise profiles...")
G = nx.read_graphml("knowledge_graph.graphml")
ep = pd.read_parquet("expertise_profiles.parquet")

# Ensure edge weights are numeric (graphml stores them as strings)
for u, v, d in G.edges(data=True):
    d["weight"] = float(d.get("weight", 1))

print(f"  Graph : {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
print(f"  Expertise : {len(ep):,} rows | "
      f"{ep['from'].nunique():,} senders | {ep['topic'].nunique()} topics")

# ── 2. Pre-compute per-person expertise metrics ────────────────────────────────
print("\n[2/7] Pre-computing expertise metrics from profiles...")

# --- topics as top expert: for each topic, who has the highest score?
topic_top_expert = (
    ep.loc[ep.groupby("topic")["score"].idxmax()]
    .groupby("from")
    .size()
    .rename("topics_top_expert")
)

# --- topic monopoly: topics where person has score > 0.5
#     AND no other person on that topic has score > 0.3
def compute_monopoly_counts(ep: pd.DataFrame) -> pd.Series:
    counts: dict[str, int] = {}
    for topic_id, grp in ep.groupby("topic"):
        above_03 = grp[grp["score"] > 0.3]
        above_05 = grp[grp["score"] > 0.5]
        if len(above_03) == 1 and len(above_05) >= 1:
            person = above_03.iloc[0]["from"]
            counts[person] = counts.get(person, 0) + 1
    return pd.Series(counts, name="topic_monopoly")

monopoly_counts = compute_monopoly_counts(ep)
print(f"  Monopoly topics found for {len(monopoly_counts):,} senders")

# --- topic concentration (Herfindahl index over a person's own topic scores)
#     Higher = expertise is concentrated in fewer topics
concentration = (
    ep.groupby("from")
    .apply(lambda g: float((g["score"] ** 2).sum()) / max(len(g), 1))
    .rename("concentration")
)

# ── 3. Pre-compute graph metrics for all nodes ─────────────────────────────────
print("\n[3/7] Pre-computing graph metrics (degree, weighted degree, betweenness)...")

print("  Degree centrality...")
deg_centrality = pd.Series(nx.degree_centrality(G), name="degree_centrality")

print("  Weighted degree...")
weighted_deg = pd.Series(dict(G.degree(weight="weight")), name="weighted_degree")

print("  Approximate betweenness centrality (k=500, may take a few minutes)...")
t0 = time.time()
betweenness = pd.Series(
    nx.betweenness_centrality(G, k=500, normalized=True, weight="weight"),
    name="betweenness",
)
print(f"  Betweenness done in {time.time() - t0:.1f}s")

# ── 4. Simulate departure of top 200 highest-degree nodes ─────────────────────
print("\n[4/7] Simulating departure of top 200 highest-degree nodes...")

top200 = sorted(G.nodes(), key=lambda n: G.degree(n), reverse=True)[:200]
n_components_before = nx.number_connected_components(G)
print(f"  Connected components before any removal: {n_components_before}")

sim_rows = []
for idx, node in enumerate(top200):
    if idx % 25 == 0:
        print(f"  [{idx+1:3d}/200] simulating {node}")

    # Snapshot edges before removal so we can restore the node
    incident = list(G.edges(node, data=True))

    G.remove_node(node)
    n_components_after = nx.number_connected_components(G)

    # Restore
    G.add_node(node)
    for u, v, d in incident:
        other = v if u == node else u
        G.add_edge(node, other, **d)

    sim_rows.append({
        "person": node,
        "component_delta": n_components_after - n_components_before,
        "simulated": True,
    })

sim_df = pd.DataFrame(sim_rows).set_index("person")

# ── 5. Assemble full metrics table ────────────────────────────────────────────
print("\n[5/7] Assembling metrics for all nodes...")

all_nodes = list(G.nodes())
base = pd.DataFrame(index=pd.Index(all_nodes, name="person"))

base = base.join(deg_centrality.rename_axis("person"))
base = base.join(weighted_deg.rename_axis("person"))
base = base.join(betweenness.rename_axis("person"))
base = base.join(topic_top_expert.rename_axis("person"))
base = base.join(monopoly_counts.rename_axis("person"))
base = base.join(concentration.rename_axis("person"))
base = base.join(sim_df)

base["topics_top_expert"] = base["topics_top_expert"].fillna(0).astype(int)
base["topic_monopoly"]    = base["topic_monopoly"].fillna(0).astype(int)
base["concentration"]     = base["concentration"].fillna(0.0)
base["component_delta"]   = base["component_delta"].fillna(0).astype(int)
base["simulated"]         = base["simulated"].fillna(False)

base = base.reset_index()

print(f"  Metrics table: {len(base):,} rows | "
      f"{base['simulated'].sum()} simulated, {(~base['simulated']).sum():,} estimated")

# ── 6. Composite risk score ────────────────────────────────────────────────────
print("\n[6/7] Computing composite risk scores...")

WEIGHTS = {
    "topic_monopoly":    0.35,
    "betweenness":       0.25,
    "weighted_degree":   0.20,
    "topics_top_expert": 0.15,
    "component_delta":   0.05,
}

def minmax_norm(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo)

for col in WEIGHTS:
    base[f"{col}_norm"] = minmax_norm(base[col])

base["risk_score"] = sum(
    base[f"{col}_norm"] * w for col, w in WEIGHTS.items()
)

# ── 7. Topic vulnerability map ────────────────────────────────────────────────
print("\n[7/7] Building topic vulnerability map...")

vuln_rows = []
for topic_id, grp in ep.groupby("topic"):
    experts = grp[grp["score"] > 0.3].sort_values("score", ascending=False)
    n_experts = len(experts)
    top3 = experts.head(3)[["from", "score"]].to_dict("records")

    scores = experts["score"].values
    if len(scores) > 0:
        total_sq = (scores ** 2).sum()
        denom    = scores.sum() ** 2
        hhi      = total_sq / denom if denom > 1e-9 else 1.0
    else:
        hhi = 1.0

    # Vulnerability: fewer experts + higher concentration = more vulnerable
    vulnerability = (1.0 / max(n_experts, 1)) * (1.0 + hhi)

    vuln_rows.append({
        "topic":        topic_id,
        "n_experts":    n_experts,
        "top3_experts": json.dumps(top3),
        "hhi":          round(hhi, 4),
        "vulnerability": vulnerability,
    })

vuln_df = pd.DataFrame(vuln_rows)
vuln_df["vulnerability_norm"] = minmax_norm(vuln_df["vulnerability"])

# ── Save outputs ──────────────────────────────────────────────────────────────
save_cols = [
    "person", "risk_score",
    "topic_monopoly", "betweenness", "weighted_degree",
    "topics_top_expert", "component_delta",
    "degree_centrality", "concentration", "simulated",
]
(
    base[save_cols]
    .sort_values("risk_score", ascending=False)
    .to_parquet("risk_scores.parquet", index=False)
)
vuln_df.to_parquet("topic_vulnerability.parquet", index=False)
print("  Saved risk_scores.parquet")
print("  Saved topic_vulnerability.parquet")

# ── Print results ─────────────────────────────────────────────────────────────
print("\n── Top 20 highest-risk people ───────────────────────────────────────────")
top20p = base.nlargest(20, "risk_score")
for _, r in top20p.iterrows():
    tag = "[SIM]" if r["simulated"] else "[EST]"
    print(
        f"  {tag} {r['person']:<45s}  risk={r['risk_score']:.4f}"
        f"  monopoly={int(r['topic_monopoly']):2d}"
        f"  top_expert={int(r['topics_top_expert']):2d}"
        f"  btw={r['betweenness']:.4f}"
        f"  Δcomp={int(r['component_delta'])}"
    )

print("\n── Top 20 most vulnerable topics ────────────────────────────────────────")
top20t = vuln_df.nlargest(20, "vulnerability")
for _, r in top20t.iterrows():
    top3 = json.loads(r["top3_experts"])
    top3_str = ", ".join(
        f"{e['from'].split('@')[0]}({e['score']:.2f})" for e in top3
    )
    print(
        f"  Topic {r['topic']:4d}  n_experts={r['n_experts']:3d}"
        f"  hhi={r['hhi']:.3f}  vuln={r['vulnerability']:.4f}"
        f"  top3=[{top3_str}]"
    )

elapsed = time.time() - wall_start
print(f"\nTotal simulation time: {elapsed:.1f}s ({elapsed / 60:.1f} min)")
