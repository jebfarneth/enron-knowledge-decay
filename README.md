# Enron Organizational Knowledge Decay Modeling

*Quantifying institutional knowledge risk, departure cascades, and AI substitution exposure across 517,000 emails and 200 employees.*

## Abstract

This project develops an original analytical framework for measuring organizational knowledge concentration risk using the Enron Corporation email corpus (517,401 emails, 200 employees, 1998–2002). Employees are scored on two independent axes, Knowledge Risk and Positional Impact, producing a four-quadrant classification system (Organizational Emergency, Silent Threat, Replaceable Executive, Low Priority). A 12-month decay simulation models recovery trajectories following individual and simultaneous departures, with a non-linear cascade amplification formula that penalizes topic overlap between departing employees. An AI substitution layer scores 13 knowledge categories on three dimensions of automability and projects residual human knowledge gaps from 2024 to 2032. The model's predictions were validated retrospectively against documented Enron collapse outcomes sourced from the Powers Report, FBI investigation records, Senate Permanent Subcommittee findings, DOJ indictments, FERC reports, and the Supreme Court opinion in Skilling v. United States. Final concordance: 72% across 18 testable predictions (13 hits, 2 partial, 1 contextual, 2 known misses).

## Methodology

The analytical pipeline proceeds in six stages. Stage 1 preprocesses the raw email corpus, resolving employee identities and filtering system accounts. Stage 2 applies BERTopic with sentence-transformer embeddings (all-MiniLM-L6-v2) to extract 191 raw topics, consolidated into 13 meaningful knowledge categories. Stage 3 constructs a weighted knowledge graph from email communication patterns (79,318 nodes, edges weighted by volume). Stage 4 computes Knowledge Risk Scores from topic monopoly concentration, graph centrality, and communication uniqueness, alongside Positional Impact Scores verified against SEC filings. Stage 5 runs agent-based departure simulations with role-gated successor matching, ramp-up curves, and permanent loss detection. Stage 6 projects AI substitution exposure across three capability dimensions (base LLM, agentic orchestration, codifiability) with an adjustable capability timeline from 2024 to 2032.

## Key Findings

The model identifies four employees as Organizational Emergency classifications (Lay, Skilling, Kaminski, Hyatt) and ten as Silent Threats, including two whose risk profiles contradict their organizational titles. Pete Davis, an Energy Scheduling Coordinator, produces the second-highest Knowledge Risk Score in the corpus (43/100) with a 100% external hire gap and 4.8% twelve-month recovery rate. No other employee held equivalent knowledge in his topic domains. The cascade simulation demonstrates that simultaneous departures produce non-linear knowledge loss through topic overlap amplification, with the compounding penalty capped at 0.5 to reflect conservative modeling assumptions. Historical validation against litigation-grade documentation achieves 72% concordance. Both known misses are attributable to corpus limitations: Andrew Fastow's deliberate concealment of SPE activities and Cliff Baxter's pre-corpus resignation.

## Tech Stack

Single-file HTML/JavaScript dashboard (D3.js v7), Python data pipeline (BERTopic, sentence-transformers, HDBSCAN, pandas, NetworkX). All visualization and simulation logic executes client-side with no backend dependencies.

## Data Source

Enron Email Corpus. Originally prepared by the CALO Project at Carnegie Mellon University. 517,401 emails from 150 senior Enron employees, collected and made public by the Federal Energy Regulatory Commission during the Enron investigation.

## Author

Jeb Farneth · Independent Research · March 2026
