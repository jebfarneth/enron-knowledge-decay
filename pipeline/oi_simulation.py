#!/usr/bin/env python3
"""
oi_simulation.py

Runs the organizational-impact recovery simulation used by the Enron dashboard.

The simulation models how knowledge work is rerouted after employee departure,
including successor capacity, ramp-up curves, partial/full routing quality,
memory accumulation, expertise upgrades, permanent knowledge loss detection,
and capped routing logs for dashboard inspection.

Inputs:
    knowledge_graph.graphml
    expertise_profiles.parquet
    risk_scores.parquet

Outputs:
    organizational_impact_simulation.json

Usage:
    python pipeline/oi_simulation.py

Notes:
    The simulation uses fixed random seeds for reproducibility. Agent memory,
    bandwidth, and ramp-up parameters are intentionally explicit so the recovery
    model can be audited and adjusted.
"""

import warnings
warnings.filterwarnings("ignore")

import json
import random
import time
import math
from collections import defaultdict
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────────
MEMORY_GAIN_FULL      = 0.03   # added to memory per successful full route
MEMORY_GAIN_PARTIAL   = 0.015  # added to memory per successful partial route
MEMORY_UPGRADE_THRESH = 0.30   # memory threshold that triggers expertise upgrade
# Request volume: count/12 per topic (see simulate_departure)
PERM_LOSS_WINDOW      = 6      # consecutive months below threshold → permanent loss
PERM_LOSS_THRESHOLD   = 0.30   # recovery quality below this = structural failure
MAX_LOG_ENTRIES       = 5_000  # cap routing log entries per simulation

# Ramp-up effectiveness: how capable a successor is at absorbing work each month.
# Index 0 = month 1, index 11 = month 12.
RAMP_UP = [0.40, 0.55, 0.65, 0.75, 0.82, 0.88, 0.93, 0.96, 0.98, 1.0, 1.0, 1.0]


# ── Agent class ────────────────────────────────────────────────────────────────
class Agent:
    __slots__ = ("name", "knowledge_scope", "memory", "bandwidth", "bandwidth_used")

    def __init__(self, name: str, knowledge_scope: dict, monthly_bandwidth: float):
        self.name = name
        self.knowledge_scope: dict[int, float] = dict(knowledge_scope)
        self.memory: dict[int, float] = defaultdict(float)
        self.bandwidth      = max(monthly_bandwidth, 1.0)  # at least 1 request/month
        self.bandwidth_used = 0.0

    def effective_score(self, topic: int) -> float:
        return min(1.0, self.knowledge_scope.get(topic, 0.0) + self.memory[topic])

    def route(self, topic: int, penalty: float = 1.0) -> str:
        score = self.effective_score(topic) * penalty
        if score > 0.7:
            return "full"
        if score > 0.4:
            return "partial"
        return "none"

    def has_capacity(self) -> bool:
        return self.bandwidth_used < self.bandwidth

    def use_capacity(self, amount: float = 1.0):
        self.bandwidth_used += amount

    def reset_bandwidth(self):
        self.bandwidth_used = 0.0

    def learn(self, topic: int, route_quality: str) -> bool:
        """Update memory after handling a request. Returns True if expertise upgraded."""
        gain = MEMORY_GAIN_FULL if route_quality == "full" else MEMORY_GAIN_PARTIAL
        self.memory[topic] = min(1.0, self.memory[topic] + gain)
        if self.memory[topic] >= MEMORY_UPGRADE_THRESH:
            old = self.knowledge_scope.get(topic, 0.0)
            self.knowledge_scope[topic] = max(old, self.memory[topic])
            return self.knowledge_scope[topic] > old
        return False


# ── Topic index ────────────────────────────────────────────────────────────────
class TopicIndex:
    """Inverted index: topic_id → list of (agent_name, base_score) sorted desc."""

    def __init__(self, ep: pd.DataFrame, active: set):
        self._idx: dict[int, list] = defaultdict(list)
        for row in ep.itertuples(index=False):
            person = row[0]   # 'from'
            topic  = row[1]   # 'topic'
            score  = row[3]   # 'score'
            if person in active and score > 0:
                self._idx[topic].append((person, score))
        # Sort each bucket descending by base score
        for t in self._idx:
            self._idx[t].sort(key=lambda x: x[1], reverse=True)

    def candidates(self, topic: int) -> list:
        return self._idx.get(topic, [])

    def add_candidate(self, agent_name: str, topic: int, score: float):
        bucket = self._idx[topic]
        # Replace or insert
        for i, (n, _) in enumerate(bucket):
            if n == agent_name:
                bucket[i] = (agent_name, score)
                bucket.sort(key=lambda x: x[1], reverse=True)
                return
        bucket.append((agent_name, score))
        bucket.sort(key=lambda x: x[1], reverse=True)


# ── Build topic profile for nodes without expertise records ────────────────────
def infer_topic_profile(person: str, G: nx.Graph, ep: pd.DataFrame) -> dict:
    """Infer topic profile from 1st-degree neighbors' expertise."""
    neighbors = list(G.neighbors(person)) if person in G else []
    if not neighbors:
        return {}
    neighbor_set = set(neighbors)
    nb_ep = ep[ep["from"].isin(neighbor_set)]
    if nb_ep.empty:
        return {}
    # Weight by frequency (how many neighbors know this topic) and avg score
    topic_freq  = nb_ep.groupby("topic")["score"].mean()
    topic_count = nb_ep.groupby("topic").size()
    profile = {}
    for t in topic_freq.index:
        freq_weight = min(1.0, topic_count[t] / max(len(neighbors), 1) * 5)
        profile[t] = round(topic_freq[t] * freq_weight, 4)
    # Keep top 20 topics, rescale to max = 0.5 (inferred, not first-hand)
    top = sorted(profile.items(), key=lambda x: x[1], reverse=True)[:20]
    if not top:
        return {}
    mx = top[0][1]
    return {t: round(s / mx * 0.5, 4) for t, s in top}


# ── Role category mapping for successor gating ─────────────────────────────────
_REAL_TITLES_LOCAL = {
    "kenneth.lay": "Chairman & CEO", "jeff.skilling": "President & COO",
    "j..kean": "EVP & Chief of Staff", "rick.buy": "EVP & Chief Risk Officer",
    "james.derrick": "EVP & General Counsel", "louise.kitchen": "COO, Enron Wholesale Services",
    "sally.beck": "COO, Enron Wholesale Operations", "jeff.dasovich": "Government Relations Executive",
    "richard.shapiro": "VP, Regulatory & Government Affairs",
    "mark.haedicke": "Managing Director, ENA Legal", "kevin.hyatt": "VP, Pipeline Operations",
    "barry.tycholiz": "VP, Trading", "stanley.horton": "CEO, Enron Transportation Services",
    "john.lavorato": "CEO, Enron Americas", "kevin.presto": "VP, Trading",
    "sara.shackleton": "Legal Specialist, ENA Legal", "tana.jones": "Legal Specialist, ENA Legal",
    "debra.perlingiere": "Legal Specialist, ENA Legal", "gerald.nemec": "Legal Counsel",
    "kay.mann": "Legal Counsel", "elizabeth.sager": "Legal Counsel",
    ".taylor": "Legal Counsel, ECT Legal", "leslie.hansen": "Legal Counsel",
    "j.kaminski": "Managing Director, Research Group", "chris.germany": "Director, East Gas Trading",
    "lance.schuler": "Managing Director & General Counsel",
    "pete.davis": "Energy Scheduling Coordinator, Portland/West Desk",
    "don.baughman": "Director, Trading", "tracey.kozadinos": "Executive Assistant, Office of the Chairman",
    "kim.ward": "Director, Trading Operations", "rhonda.denton": "Legal Specialist",
    "lee.wright": "VP, Enron Global Markets", "lynette.crawford": "IT Operations Coordinator",
    "greg.whalley": "President, Enron Wholesale", "richard.sanders": "VP, Legal",
    "mike.grigsby": "Director, Gas Trading", "john.arnold": "VP, Trading",
    "drew.fossum": "VP & General Counsel, Enron Transportation",
    "mark.palmer": "VP, Communications", "jeffrey.shankman": "VP, Global Risk Markets",
    "michelle.cash": "VP, Human Resources Legal",
}


def _role_category(email: str) -> str:
    lp = email.strip().lower().split("@")[0]
    t  = _REAL_TITLES_LOCAL.get(lp, "").lower()
    if any(x in t for x in ["legal", "counsel", "attorney", "litigation"]):
        return "Legal"
    if any(x in t for x in ["trading", "trader", "gas trading", "desk"]):
        return "Trading"
    if any(x in t for x in ["research", "quantitative", "analytics"]):
        return "Research"
    if any(x in t for x in ["regulatory", "government", "affairs"]):
        return "Regulatory"
    if any(x in t for x in ["operations", "coordinator", "scheduling",
                              "pipeline", "transportation"]):
        return "Operations"
    if any(x in t for x in ["communications", "investor"]):
        return "Communications"
    if any(x in t for x in ["ceo", "coo", "evp", "chairman", "president",
                              " vp", "managing director"]):
        return "Executive"
    return "Administration"


# ── Successor readiness scoring ────────────────────────────────────────────────
def build_successor_readiness(
    person: str,
    G: nx.Graph,
    ep: pd.DataFrame,
    departed_scores: dict,
    topic_index: TopicIndex,
) -> dict:
    """
    For every topic the departed person knew, score each candidate successor on:
      (a) expertise score on that topic               weight 0.4
      (b) topic overlap with the departed person      weight 0.3
      (c) relationship strength (edge weight, normed) weight 0.3

    Returns {topic_id: [(candidate, readiness_score), ...]} sorted descending.
    """
    departed_topic_set = set(departed_scores.keys())

    # Set of topics per person — used for domain-overlap calculation
    person_topic_sets: dict[str, set] = (
        ep.groupby("from")["topic"].apply(set).to_dict()
    )

    # Direct edge weights from departed and the max (for normalisation)
    if person in G:
        edge_weights = {nb: float(d.get("weight", 1)) for nb, d in G[person].items()}
        max_edge_w   = max(edge_weights.values()) if edge_weights else 1.0
    else:
        edge_weights = {}
        max_edge_w   = 1.0

    dep_cat = _role_category(person)

    result: dict[int, list] = {}
    for topic in departed_topic_set:
        scored = []
        for name, base_score in topic_index.candidates(topic):
            # (a) expertise on this specific topic
            a = base_score

            # (b) fraction of departed's topics also present in candidate's profile
            cand_topics = person_topic_sets.get(name, set())
            b = len(cand_topics & departed_topic_set) / max(len(departed_topic_set), 1)

            # (c) direct relationship strength, normalised by departed's max edge weight
            c = edge_weights.get(name, 0.0) / max_edge_w

            readiness = 0.4 * a + 0.3 * b + 0.3 * c

            # Role-gating: cap cross-role candidates at 0.15
            if _role_category(name) != dep_cat:
                readiness = min(readiness, 0.15)

            scored.append((name, round(readiness, 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        result[topic] = scored

    return result


# ── Core routing for one request ───────────────────────────────────────────────
_TIER_PENALTY = {1: 1.0, 2: 0.7, 3: 0.4}

def route_request(
    topic: int,
    n1: set,
    n2: set,
    agents: dict,
    topic_index: TopicIndex,
) -> tuple:
    """
    Returns (step, quality, agent_name, penalized_eff_score).
    step 1/2/3 = routed; step 4 = dropped (penalized_eff_score = 0.0).
    Agents over their monthly bandwidth budget are skipped.
    """
    best: dict[int, tuple] = {}   # tier → (penalized_eff, quality, name)

    for name, _base in topic_index.candidates(topic):
        agent = agents.get(name)
        if agent is None or not agent.has_capacity():
            continue
        tier    = 1 if name in n1 else (2 if name in n2 else 3)
        penalty = _TIER_PENALTY[tier]
        q       = agent.route(topic, penalty=penalty)
        if q == "none":
            continue
        eff = agent.effective_score(topic) * penalty
        if tier not in best or eff > best[tier][0]:
            best[tier] = (eff, q, name)

    for step in (1, 2, 3):
        if step in best:
            eff, q, name = best[step]
            return step, q, name, eff

    return 4, None, None, 0.0


# ── Find plateau month ─────────────────────────────────────────────────────────
def find_plateau(recovery_rates: list, threshold: float = 0.01) -> Optional[int]:
    for m in range(len(recovery_rates) - 1):
        if all(
            abs(recovery_rates[j] - recovery_rates[j - 1]) < threshold
            for j in range(m + 1, len(recovery_rates))
        ):
            return m + 1   # 1-indexed month
    return None


# ── Main simulation ────────────────────────────────────────────────────────────
def simulate_departure(
    person: str,
    months: int,
    G: nx.Graph,
    ep: pd.DataFrame,
) -> dict:
    t0 = time.time()

    # ── Build departed person's topic profile (scores + email counts) ──────────
    person_ep = ep[ep["from"] == person]
    if not person_ep.empty:
        departed_scores = dict(zip(person_ep["topic"], person_ep["score"]))
        departed_counts = dict(zip(person_ep["topic"], person_ep["count"]))
        profile_inferred = False
    else:
        inferred = infer_topic_profile(person, G, ep)
        departed_scores = inferred
        # Synthetic counts: score used as a proxy for relative email volume
        departed_counts = {t: max(1, round(s * 200)) for t, s in inferred.items()}
        profile_inferred = True

    if not departed_scores:
        print(f"    WARNING: no topic profile found for {person}, skipping")
        return {}

    # ── Adjacency sets (edge-weight filtered) ─────────────────────────────────
    # Step 1: direct neighbors with edge weight >= 5
    n1 = set()
    if person in G:
        for nb, data in G[person].items():
            if float(data.get("weight", 1)) >= 5:
                n1.add(nb)

    # Step 2: two-hop neighbors reachable through an intermediary
    # where BOTH edges (departed→intermediary and intermediary→candidate)
    # have weight >= 3.
    print(f"    Building 2nd-degree set (|n1|={len(n1):,}, w>=5)...")
    n2 = set()
    if person in G:
        for nb in n1:                              # nb already passes w>=5 from departed
            for candidate, data in G[nb].items():
                if float(data.get("weight", 1)) >= 3:
                    n2.add(candidate)
    n2 -= n1
    n2.discard(person)

    print(f"    |n2|={len(n2):,}  |  topics={len(departed_scores)}")

    # ── Request schedule: volume = count / 12 per topic ───────────────────────
    request_schedule = {
        t: max(1, round(departed_counts[t] / 12))
        for t in departed_scores
    }
    print(f"    Requests per month: {sum(request_schedule.values())}")

    # ── Build agents with bandwidth budgets ───────────────────────────────────
    active_nodes      = set(G.nodes()) - {person}
    topic_index       = TopicIndex(ep, active_nodes)
    agent_total_email = ep.groupby("from")["count"].sum().to_dict()

    ep_active = ep[ep["from"].isin(active_nodes)]
    agents: dict[str, Agent] = {}
    for name, grp in ep_active.groupby("from"):
        scope      = dict(zip(grp["topic"], grp["score"]))
        monthly_bw = 1.5 * agent_total_email.get(name, 10) / 12
        agents[name] = Agent(name, scope, monthly_bw)
    # Nodes in graph but absent from expertise_profiles get minimal bandwidth
    for node in active_nodes:
        if node not in agents:
            agents[node] = Agent(node, {}, 1.5 * 10 / 12)

    # ── Successor readiness (computed once before the simulation loop) ─────────
    print(f"    Computing successor readiness scores...")
    topic_readiness = build_successor_readiness(
        person, G, ep, departed_scores, topic_index
    )
    # Flat O(1) lookup used inside the routing loop
    topic_readiness_lookup: dict[int, dict[str, float]] = {
        topic: {name: score for name, score in candidates}
        for topic, candidates in topic_readiness.items()
    }
    # Top 3 topics by departed score, each with their top 3 successors — for output
    top_topics_analysis = [
        {
            "topic":          topic,
            "departed_score": round(dep_score, 4),
            "top_successors": [
                {"candidate": name, "readiness": score}
                for name, score in topic_readiness.get(topic, [])[:3]
            ],
        }
        for topic, dep_score in sorted(
            departed_scores.items(), key=lambda x: x[1], reverse=True
        )[:3]
    ]

    # ── Simulation loop ───────────────────────────────────────────────────────
    monthly_timeline:    list  = []
    routing_log:         list  = []
    permanent_losses:    list  = []
    recovery_rates:      list  = []
    permanently_lost:    set   = set()
    # topic → [monthly avg quality ratio], one entry appended per month
    topic_monthly_q: dict[int, list[float]] = defaultdict(list)

    for month in range(1, months + 1):

        # Reset every agent's bandwidth at month boundary
        for agent in agents.values():
            agent.reset_bandwidth()

        n_recovered = 0
        n_lost      = 0
        quality_sum = 0.0
        n_req       = 0
        upgrades    = 0

        for topic, n_requests in request_schedule.items():
            dept_score       = departed_scores[topic]
            topic_quality    = 0.0

            for _ in range(n_requests):
                step, quality, agent_name, penalized_eff = route_request(
                    topic, n1, n2, agents, topic_index
                )
                n_req += 1

                if step < 4:
                    agent       = agents[agent_name]
                    # Memory-augmented effective score: base expertise + accumulated
                    # memory on this topic, capped at 1.0.  An agent who has handled
                    # many requests closes the gap to the departed expert over time.
                    mem_eff_score   = min(1.0, agent.knowledge_scope.get(topic, 0.0)
                                         + agent.memory[topic])
                    # Proportional recovery uses the memory-augmented score so that
                    # sustained routing genuinely raises quality in later months.
                    base_ratio      = min(1.0, mem_eff_score / dept_score)
                    readiness_score = topic_readiness_lookup.get(topic, {}).get(
                        agent_name,
                        # Fallback for experts upgraded mid-simulation:
                        # expertise-only component (no cached overlap/relationship)
                        0.4 * mem_eff_score,
                    )
                    # Ramp-up factor: early months are naturally less effective
                    ramp            = RAMP_UP[month - 1]
                    ratio           = base_ratio * readiness_score * ramp
                    n_recovered   += 1
                    quality_sum   += ratio
                    topic_quality += ratio

                    agents[agent_name].use_capacity()
                    upgraded = agents[agent_name].learn(topic, quality)
                    if upgraded:
                        topic_index.add_candidate(
                            agent_name, topic,
                            agents[agent_name].knowledge_scope[topic],
                        )
                        upgrades += 1

                    if len(routing_log) < MAX_LOG_ENTRIES:
                        routing_log.append({
                            "month": month, "topic": topic,
                            "step": step, "quality": quality,
                            "base_ratio":    round(base_ratio, 4),
                            "readiness":     round(readiness_score, 4),
                            "ramp":          ramp,
                            "quality_ratio": round(ratio, 4),
                            "agent": agent_name,
                        })
                else:
                    n_lost        += 1
                    topic_quality += 0.0
                    if len(routing_log) < MAX_LOG_ENTRIES:
                        routing_log.append({
                            "month": month, "topic": topic,
                            "step": 4, "quality": None,
                            "base_ratio": 0.0, "readiness": 0.0,
                            "ramp": RAMP_UP[month - 1],
                            "quality_ratio": 0.0, "agent": None,
                        })

            # Record this topic's average quality for this month
            topic_monthly_q[topic].append(topic_quality / n_requests)

        # ── Permanent loss detection (sliding 6-month window) ─────────────────
        if month >= PERM_LOSS_WINDOW:
            for topic in request_schedule:
                if topic in permanently_lost:
                    continue
                history = topic_monthly_q[topic]
                if (len(history) >= PERM_LOSS_WINDOW
                        and all(q < PERM_LOSS_THRESHOLD
                                for q in history[-PERM_LOSS_WINDOW:])):
                    permanently_lost.add(topic)
                    permanent_losses.append({"topic": topic, "month": month})

        recovery_rate = quality_sum / n_req if n_req else 0.0
        loss_rate     = n_lost / n_req      if n_req else 0.0
        recovery_rates.append(recovery_rate)

        monthly_timeline.append({
            "month":                     month,
            "n_requests":                n_req,
            "n_recovered":               n_recovered,
            "n_lost":                    n_lost,
            "recovery_rate":             round(recovery_rate, 4),
            "loss_rate":                 round(loss_rate,     4),
            "n_permanently_lost_topics": len(permanently_lost),
            "expertise_upgrades":        upgrades,
        })

    final_recovery = sum(recovery_rates) / months if months else 0.0
    plateau_month  = find_plateau(recovery_rates)

    elapsed = time.time() - t0
    print(f"    Done in {elapsed:.1f}s — final_recovery={final_recovery:.3f}, "
          f"plateau={plateau_month}, perm_lost={len(permanently_lost)}")

    return {
        "person":               person,
        "departed_topics":      len(departed_scores),
        "profile_inferred":     profile_inferred,
        "n1_size":              len(n1),
        "n2_size":              len(n2),
        "monthly_timeline":     monthly_timeline,
        "recovery_rates":       [round(r, 4) for r in recovery_rates],
        "final_recovery_score": round(final_recovery, 4),
        "permanent_losses":     permanent_losses,
        "n_permanently_lost":   len(permanently_lost),
        "plateau_month":        plateau_month,
        "top_topics_analysis":  top_topics_analysis,
        "successor_analysis":   {
            t: [{"candidate": n, "readiness": s} for n, s in candidates[:10]]
            for t, candidates in topic_readiness.items()
        },
        "routing_log":          routing_log,
        "routing_log_capped":   len(routing_log) >= MAX_LOG_ENTRIES,
        "sim_seconds":          round(elapsed, 2),
    }


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    wall_start = time.time()

    # ── Load data ──────────────────────────────────────────────────────────────
    print("[1/4] Loading data...")
    G   = nx.read_graphml("knowledge_graph.graphml")
    ep  = pd.read_parquet("expertise_profiles.parquet")
    rs  = pd.read_parquet("risk_scores.parquet")

    for u, v, d in G.edges(data=True):
        d["weight"] = float(d.get("weight", 1))

    print(f"  Graph   : {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges")
    print(f"  Profiles: {len(ep):,} rows, {ep['from'].nunique():,} senders")
    print(f"  Risk    : {len(rs):,} scored people")

    # ── Select top 200 highest-risk people ────────────────────────────────────
    top200 = rs.nlargest(200, "risk_score")
    print(f"\n[2/4] Top 200 highest-risk people loaded (risk range: "
          f"{top200['risk_score'].min():.4f} – {top200['risk_score'].max():.4f})")

    # ── Run simulations ────────────────────────────────────────────────────────
    print(f"\n[3/4] Running 12-month departure simulations for 200 people...")
    all_results = []

    for rank, (_, row) in enumerate(top200.iterrows(), 1):
        person = row["person"]
        print(f"\n  [{rank}/200] Simulating departure of: {person}")
        result = simulate_departure(person, months=12, G=G, ep=ep)
        if not result:
            continue
        result["risk_score"] = round(float(row["risk_score"]), 4)
        all_results.append(result)

        # Print 12-month recovery curve
        rates = result["recovery_rates"]
        curve = "  ".join(f"M{m+1}:{r:.0%}" for m, r in enumerate(rates))
        print(f"    Recovery curve: {curve}")

        # Print top 3 topics with best identified successor
        analysis = result.get("top_topics_analysis", [])
        if analysis:
            print(f"    Successor readiness (top 3 topics by expertise):")
            for t in analysis:
                best = t["top_successors"][0] if t["top_successors"] else None
                if best:
                    short = best["candidate"].split("@")[0]
                    b_str = f"{short}  (ready={best['readiness']:.3f})"
                else:
                    b_str = "no candidate found"
                print(f"      topic {t['topic']:3d} "
                      f"[dept_score={t['departed_score']:.3f}]  best: {b_str}")

    # ── Save JSON ──────────────────────────────────────────────────────────────
    print(f"\n[4/4] Saving results...")
    with open("simulation_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print("  Saved simulation_results.json")

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "─" * 78)
    print(f"{'Person':<45}  {'Risk':>6}  {'RecovFinal':>10}  "
          f"{'PermLoss':>8}  {'Plateau':>7}")
    print("─" * 78)
    # Print top 20 in the summary table; full data is in the JSON
    all_results_sorted = sorted(all_results, key=lambda r: r["risk_score"], reverse=True)
    summary_rows = all_results_sorted[:20]

    for res in summary_rows:
        perm_loss_count = len(set(e["topic"] for e in res["permanent_losses"]))
        plateau = f"M{res['plateau_month']}" if res["plateau_month"] else "never"
        print(
            f"  {res['person']:<43}  {res['risk_score']:>6.4f}  "
            f"{res['final_recovery_score']:>9.1%}  "
            f"{perm_loss_count:>8d}  {plateau:>7}"
        )

    total_elapsed = time.time() - wall_start
    print(f"\nTotal runtime: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
