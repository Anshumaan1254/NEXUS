# Nexus — Causal Intelligence Platform
## lablab.ai Hackathon Submission

### Project Name
Nexus — Causal Intelligence Platform

### Tagline
Making the invisible causal chains inside a codebase visible, queryable, and actionable.

### The Problem
Software systems accumulate causally invisible debt. A constraint baked into a 2001 decision silently shapes the 2026 architecture. Every AI coding tool in 2026 competes on velocity — how fast to write the next line. But the faster you build on top of an undocumented, causally opaque foundation, the faster you accumulate assumptions that will eventually detonate.

### The Solution
Nexus is the first software comprehension platform built on a formal computational model of organizational causality. It uses IBM Bob IDE for full-repository ingestion to extract Decision Provenance Records (DPRs), builds a Causal Temporal Graph (CTG) in Neo4j, monitors assumption decay using AI + NetworkX blast radius analysis, runs counterfactual simulations, and generates actionable risk reports.

### How It Works
1. **Layer 1 — Decision Provenance Engine**: Bob IDE ingests the entire repo, git history, issues, and docs to extract structured DPRs.
2. **Layer 2 — Causal Temporal Graph**: DPRs become nodes in a DAG with time as a structural dimension, stored in Neo4j.
3. **Layer 3 — Assumption Decay Monitor**: AI re-checks each assumption against current state. NetworkX computes blast radius.
4. **Layer 4 — Counterfactual Simulation**: Given the CTG, simulate alternative decision timelines.
5. **Layer 5 — Organizational Risk Forecast**: Knowledge concentration analysis flags SPOFs.

### Tech Stack
- IBM Bob IDE (full-repo context, Layers 1-3)
- Claude/Gemini (deep reasoning, Layers 4-5)
- Neo4j Community (Causal Temporal Graph)
- Weaviate Cloud (semantic vector search)
- NetworkX (blast radius computation)
- React + Vite + Tailwind (dashboard)
- ReportLab (PDF risk reports)
- Pydantic v2 (data validation)

### Target Repository
PostgreSQL (psf/postgres) — chosen deliberately because the chardet-to-charset_normalizer migration is a real-world assumption decay event that Nexus surfaces as a Layer 3 alert.

### Key Metrics
- 15 DPRs extracted and validated
- 25 causal relationships mapped
- 5 decay alerts (4 already decaying)
- 5 counterfactual simulations
- Knowledge concentration across 6 components
- Risk report with P0/P1/P2 prioritized remediation backlog

### Team
Solo submission

### Demo
See demo_script.md for the word-for-word demo walkthrough.
