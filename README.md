# Enron Organizational Knowledge Decay Modeling

*Quantifying institutional knowledge risk, departure cascades, and AI substitution exposure across 517,000 emails and 200 employees.*

**Live Demo:** https://www.jebfarneth.com/enron  
**Repository Type:** Python NLP/modeling pipeline + static interactive dashboard  
**Core Techniques:** Topic modeling, graph analytics, organizational simulation, retrospective validation

## What This Project Demonstrates

This project demonstrates an end-to-end analytical product workflow: raw corpus ingestion, identity resolution, NLP topic modeling, graph construction, employee-level risk scoring, simulation design, historical validation, and browser-based dashboard deployment. The result is not a notebook or static report, but an interactive system for exploring organizational knowledge concentration and departure risk.

## Abstract

This project develops an original analytical framework for measuring organizational knowledge concentration risk using the Enron Corporation email corpus (517,401 emails, 200 employees, 1998–2002). Employees are scored on two independent axes, Knowledge Risk and Positional Impact, producing a four-quadrant classification system: Organizational Emergency, Silent Threat, Replaceable Executive, and Low Priority.

A 12-month decay simulation models recovery trajectories following individual and simultaneous departures, with a non-linear cascade amplification formula that penalizes topic overlap between departing employees. An AI substitution layer scores 13 knowledge categories on three dimensions of automability and projects residual human knowledge gaps from 2024 to 2032.

The model's predictions were validated retrospectively against documented Enron collapse outcomes sourced from the Powers Report, FBI investigation records, Senate Permanent Subcommittee findings, DOJ indictments, FERC reports, and the Supreme Court opinion in *Skilling v. United States*. Final concordance: 72% across 18 testable predictions: 13 hits, 2 partial, 1 contextual, and 2 known misses.

## Scoring and Simulation Framework

The model scores each employee on two independent axes: Knowledge Risk and Positional Impact.

**Knowledge Risk** estimates how difficult an employee's knowledge would be to replace:

```text
KR = 0.35M + 0.25B + 0.20D + 0.20S
```

Where:

```text
M = topic monopoly
B = betweenness centrality
D = weighted communication degree
S = topic spread
```

**Positional Impact** estimates structural importance inside the communication network and organizational hierarchy:

```text
PI = f(Cd, Cb, Rs)
```

Where:

```text
Cd = degree centrality
Cb = betweenness centrality
Rs = role seniority
```

The departure simulation models monthly knowledge recovery over a 12-month horizon:

```text
R(t) = C · (1 − e^(−λt))
```

Where:

```text
C = successor capacity
λ = learning rate
t = month after departure
```

Simultaneous departures apply a non-linear cascade penalty:

```text
A = Σrᵢ · (1 + 0.06n) · (1 + τ)
```

Where:

```text
rᵢ = individual departure risk
n = number of simultaneous departures
τ = topic-overlap penalty between departing employees
```

The AI substitution layer estimates automability by topic:

```text
α = 0.40L + 0.35(G · λ) + 0.25F
```

Where:

```text
L = base LLM capability
G = agentic orchestration capability
λ = capability projection multiplier
F = codifiability
```

Employee-level AI exposure is computed as the weighted average across that employee's topic distribution.

## Methodology

The analytical pipeline proceeds in six stages.

Stage 1 preprocesses the raw email corpus, resolving employee identities and filtering system accounts.

Stage 2 applies BERTopic with sentence-transformer embeddings using `all-MiniLM-L6-v2` to extract 191 raw topics, consolidated into 13 meaningful knowledge categories.

Stage 3 constructs a weighted knowledge graph from email communication patterns: 79,318 nodes, with edges weighted by communication volume.

Stage 4 computes Knowledge Risk Scores from topic monopoly concentration, graph centrality, and communication uniqueness, alongside Positional Impact Scores verified against SEC filings.

Stage 5 runs agent-based departure simulations with role-gated successor matching, ramp-up curves, and permanent loss detection.

Stage 6 projects AI substitution exposure across three capability dimensions: base LLM capability, agentic orchestration, and codifiability, with an adjustable capability timeline from 2024 to 2032.

## Key Findings

The model identifies four employees as Organizational Emergency classifications: Kenneth Lay, Jeff Skilling, Vince Kaminski, and Kevin Hyatt.

It also identifies ten Silent Threats, including employees whose risk profiles contradict their organizational titles. Pete Davis, an Energy Scheduling Coordinator, produces the second-highest Knowledge Risk Score in the corpus: 43/100, with a 100% external hire gap and 4.8% twelve-month recovery rate. No other employee held equivalent knowledge in his topic domains.

The cascade simulation demonstrates that simultaneous departures produce non-linear knowledge loss through topic overlap amplification, with the compounding penalty capped at 0.5 to reflect conservative modeling assumptions.

Historical validation against litigation-grade documentation achieves 72% concordance. Both known misses are attributable to corpus limitations: Andrew Fastow's deliberate concealment of SPE activities and Cliff Baxter's pre-corpus resignation.

## Validation

The model was retrospectively evaluated against documented Enron collapse outcomes using legal, investigative, and regulatory records.

Validation sources include the Powers Report, FBI investigation records, Senate Permanent Subcommittee findings, DOJ indictments, FERC reports, and the Supreme Court opinion in *Skilling v. United States*.

Final concordance:

```text
18 testable predictions
13 hits
2 partial matches
1 contextual match
2 known misses
72% concordance
```

The two known misses are explained by limitations in the underlying email corpus rather than by scoring failure: Andrew Fastow's SPE activities were deliberately concealed, and Cliff Baxter resigned before the core corpus window.

## Tech Stack

**Modeling / Data Pipeline:** Python, pandas, NumPy, BERTopic, sentence-transformers, HDBSCAN, NetworkX, parquet, GraphML.

**Dashboard:** Static browser application using HTML, CSS, JavaScript, and D3.js. The dashboard runs client-side with no backend dependencies.

**Pipeline Outputs:** `dashboard_data.json`, `topic_categories.json`, `topic_words.json`, `clean_names.json`.

**Deployment:** Hosted as a static site at `jebfarneth.com/enron`.

## Repository Structure

This repository contains both the analytical pipeline and the generated dashboard layer.

```text
pipeline/                  Python NLP, graph, scoring, and simulation pipeline
prototypes/                Earlier dashboard prototypes retained for development history
index.html                 Static dashboard structure
styles.css                 Dashboard styling
app.js                     Dashboard interaction, visualization, and client-side simulation logic
dashboard_data.json         Exported dashboard data artifact
topic_categories.json       Consolidated topic category mapping
topic_words.json            Topic keyword export
clean_names.json            Cleaned identity-resolution artifact
requirements.txt            Python dependencies
```

Raw Enron corpus files, virtual environments, parquet files, embedding arrays, and graph artifacts are excluded from GitHub for size and cleanliness.

## Pipeline Order

The public dashboard is generated from a multi-stage Python pipeline:

1. `pipeline/ingest.py` converts the raw Enron `emails.csv` export into structured parquet data.
2. `pipeline/clean_data.py` resolves sender identities, removes system accounts, and normalizes duplicate aliases.
3. `pipeline/build_nlp_graph.py` applies BERTopic and sentence-transformer embeddings, builds expertise profiles, and exports the knowledge graph.
4. `pipeline/decay_simulation.py` computes employee-level knowledge-risk and departure-impact metrics.
5. `pipeline/oi_simulation.py` runs the organizational-impact recovery simulation used by the dashboard.
6. `pipeline/export_dashboard_data.py` combines graph outputs, risk scores, topic labels, role metadata, descriptions, and simulation results into `dashboard_data.json`.
7. `pipeline/generate_descriptions.py` is an optional enrichment step that converts already-computed metrics into concise dashboard briefings.

The current public dashboard is implemented as a static browser application using `index.html`, `styles.css`, and `app.js`.

## Data Source

Enron Email Corpus. Originally prepared by the CALO Project at Carnegie Mellon University. 517,401 emails from 150 senior Enron employees, collected and made public by the Federal Energy Regulatory Commission during the Enron investigation.

## Prototypes

`prototypes/streamlit_dashboard.py` preserves an earlier Streamlit dashboard prototype. It is retained for development history only and is not part of the current public dashboard path.

## Author

Jeb Farneth · Independent Research · March 2026
