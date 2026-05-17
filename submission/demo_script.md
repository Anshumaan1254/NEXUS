# Nexus Demo Script
## Word-for-Word Walkthrough (5 minutes)

### Opening (30 seconds)
"Every AI coding tool in 2026 competes on velocity — how fast from intent to implementation. Nexus competes on a fundamentally different axis: comprehension. We make the invisible causal chains inside a codebase visible, queryable, and actionable."

### The Problem (45 seconds)
"Let me show you what I mean. This is PostgreSQL — one of the most important software systems in the world. It has decisions from 1999 that still silently constrain the 2026 architecture. For example, the decision to use 32-bit transaction IDs was made in 2002 — and it STILL causes production outages in 2026 because databases can wrap around after 4 billion transactions."

"No static analysis tool can see this. No file-level AI can detect it. You need something that reads the ENTIRE repository simultaneously."

### Layer 1 — Decision Extraction (45 seconds)
"That's where IBM Bob comes in. Bob ingests the entire PostgreSQL repository — every file, every commit, every issue. It extracts what we call Decision Provenance Records. Here are 15 DPRs Bob found, each with rejected alternatives, constraints, assumptions, and risk scores."

*[Show nexus_data.json or dashboard DPR list]*

### Layer 2 — Causal Temporal Graph (45 seconds)
"Bob doesn't just find decisions — it maps the causal relationships BETWEEN them. This is the Causal Temporal Graph. 15 nodes, 25 edges. You can see that DPR-001 (the 8KB page size from the 1990s) CONSTRAINS five other decisions. Change that one constant, and the entire storage layer reshapes."

*[Show CTG explorer in dashboard or Neo4j browser]*

### Layer 3 — The Killer Demo Moment (60 seconds)
"But here's the real power. Nexus monitors every assumption for decay. Look at this: DPR-003, MVCC via tuple versioning — the assumption was 'vacuum can keep up with tuple creation rate.' The decay monitor says: ALREADY DECAYING. Evidence: high-update workloads on cloud storage creating bloat faster than vacuum can clean."

"This isn't a guess. This is Bob tracing a decision from 1999 through 27 years of commits to find that its core assumption is breaking RIGHT NOW. And NetworkX tells us the blast radius: it affects the entire MVCC subsystem — 4 downstream DPRs."

*[Show decay alerts in dashboard]*

### Layers 4-5 — Counterfactual + Risk (45 seconds)
"We can even simulate: what if PostgreSQL had used undo logs instead? The counterfactual engine traces through the graph and finds that 6 DPRs across 3 components would change. Risk level: extreme."

"And the knowledge concentration report flags Tom Lane as a single point of failure — he's involved in 80%+ of the foundational decisions."

*[Show counterfactual traces and knowledge concentration]*

### Closing (30 seconds)
"Nexus is not another AI code generator. It's a comprehension engine. It sees what no other tool can see — the invisible causal chains that determine whether your next deployment succeeds or fails. Thank you."
