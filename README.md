# NEXUS — Causal Intelligence Platform for Codebases

NEXUS traces *why* a codebase looks the way it does. Instead of analyzing code at the file or function level, it reconstructs the causal chain of decisions, constraints, and assumptions behind a system's architecture — and tracks when those original assumptions stop holding true as the live repository evolves.

It relies on full-repository ingestion to extract decisions, plus Google Gemini for the semantic reasoning layers (counterfactual simulation, knowledge concentration, assumption re-evaluation). The demo target is `postgres/postgres`, specifically its MVCC, WAL, and storage subsystems.

## The core idea

A decision made in one part of a codebase years ago can quietly constrain decisions made in a completely unrelated part of the codebase later, even when neither file references the other. NEXUS calls these **Decision Provenance Records (DPRs)** — structured records of a decision, the assumptions it depended on, and what it causally enables or constrains downstream. DPRs are linked into a **Causal Temporal Graph (CTG)**, a directed graph stored in Neo4j where edges represent relationships like `CONSTRAINS`, `ENABLES`, `REQUIRES`, and `ASSUMPTION_OF`.

Once that graph exists, two things become possible that aren't possible with file-level analysis:

- **Assumption decay detection** — re-checking whether the assumptions behind an old decision still hold given the repo's current state, and flagging the ones that don't.
- **Counterfactual simulation** — asking "what if decision X had gone differently?" and tracing which downstream decisions would have changed.

## Repository layout

```
nexus-frontend/        React dashboard (the UI a team actually uses)
nexus_layer2/           Python backend: graph ingestion, FastAPI service, analysis engines
postgres-analysis/      PowerShell scripts + output from the layer-1 analysis run against postgres/postgres
```

### `nexus_layer2/` — backend and analysis pipeline

This is where most of the actual logic lives.

- `repo_analyzer.py` — clones an arbitrary GitHub repo, walks its git history and codebase, and uses Gemini to extract DPRs from it. This is the layer-1 ingestion step.
- `models.py` — Pydantic v2 schemas for DPRs, CTG edges, and decay alerts. Everything coming out of layer 1 is validated against these before it touches the graph.
- `graph_builder.py` — loads validated DPRs and edges into Neo4j: creates indexes, DPR nodes, relationship edges, and `DecayAlert` nodes.
- `cypher_queries.py` / `nl_query.py` — a library of predefined Cypher queries (critical blast radius, decay risk, causal chains, etc.) plus a keyword-based natural-language interface on top of them, no LLM call required for this part.
- `decay_monitor.py` — re-fetches current repo state and re-sends each tracked assumption to Gemini with essentially the question "does this still hold?", returning a confidence score and reasoning.
- `counterfactual_engine.py` — given the CTG and a decision node, simulates an alternate timeline by reasoning over what downstream decisions would change.
- `knowledge_concentration.py` — runs blame-style analysis across the repo to compute, per decision, which contributor(s) hold the most context on it, and flags single points of failure (bus-factor risk).
- `build_nexus_data.py` — merges the layer-1 JSON output with the Neo4j graph state into one `nexus_data.json` file. This single file is what the frontend actually reads — there's no live database query from the UI.
- `generate_risk_report.py` — turns `nexus_data.json` into a PDF report (via ReportLab) summarizing decay risk and knowledge concentration for non-technical stakeholders.
- `weaviate_ingest.py` / `gemini_query.py` — optional semantic search layer: pushes DPR content into Weaviate so decisions/assumptions can be queried by meaning rather than keyword.
- `api.py` — the FastAPI service that exposes all of the above to the frontend (`/api/dprs`, `/api/graph`, `/api/data`, etc.), plus endpoints to trigger a fresh analysis run.

### `nexus-frontend/` — dashboard

A Vite + React 19 single-page app, deployed to Vercel, that reads from `nexus_data.json` (via the FastAPI backend) and nothing else — no direct database connection from the client.

Views (`src/views/`):
- `Overview.jsx` — summary stats and headline risk numbers.
- `CausalGraph.jsx` — interactive visualization of the CTG, built with D3 and three.js.
- `DecayAlerts.jsx` — list of assumptions flagged as decaying, with evidence.
- `KnowledgeMap.jsx` — knowledge concentration / bus-factor view.
- `CounterfactualLab.jsx` — interface for running and viewing "what if" simulations.

### `postgres-analysis/`

PowerShell-based scripts used to run the layer-1 analysis pass against `postgres/postgres` and the resulting output (`NEXUS_LAYER1_COMPLETE_ANALYSIS.md`, raw DPR JSON). This is the actual data the rest of the pipeline was built and demoed against.

## Data flow

```
repo_analyzer.py (or equivalent full-repo ingestion)
   -> raw DPRs + git history + issue/PR context
   -> models.py (Pydantic validation)
   -> graph_builder.py
   -> Neo4j (CTG: nodes + weighted, time-indexed edges)
   -> decay_monitor.py / counterfactual_engine.py / knowledge_concentration.py (Gemini reasoning)
   -> build_nexus_data.py merges everything
   -> nexus_data.json
   -> api.py (FastAPI) serves it
   -> React dashboard
```

`nexus_data.json` is intentionally the single source of truth for the frontend — it means the dashboard has no real backend dependency for read paths and could in principle be served as a static file.

## Tech stack

**Backend / analysis**
- Python 3, FastAPI, Uvicorn
- Pydantic v2 for schema validation
- Neo4j (Community Edition) as the graph database, via the official `neo4j` driver
- Google Gemini (`google-genai`) for semantic reasoning: assumption decay checks, counterfactual simulation, knowledge concentration
- Weaviate (cloud free tier) for optional vector/semantic search over DPRs
- GitPython for repository and commit history parsing
- ReportLab for PDF risk report generation

**Frontend**
- React 19 + Vite
- react-router-dom for client-side routing
- D3.js and three.js for the causal graph visualization
- lucide-react for icons
- Deployed via Vercel

**Other**
- PowerShell scripts for the layer-1 batch analysis run

## Running it locally

### Backend

```bash
cd nexus_layer2
pip install -r requirements.txt
# add a .env with your GOOGLE_API_KEY / Gemini credentials if running decay_monitor.py or counterfactual_engine.py

# Neo4j (no auth, dev mode)
docker run -p7474:7474 -p7687:7687 neo4j:community

python models.py          # validates layer-1 output
python graph_builder.py   # loads it into Neo4j
python build_nexus_data.py
uvicorn api:app --reload
```

### Frontend

```bash
cd nexus-frontend
npm install
npm run dev
```

The frontend expects the FastAPI service to be reachable and `nexus_data.json` to already exist in `nexus_layer2/`.

## Notes

- Neo4j is run without authentication — this is a development/demo setup, not production configuration.
- The natural-language query interface (`nl_query.py`) does keyword matching against the predefined Cypher queries; it does not call an LLM. `gemini_query.py` is the LLM-backed alternative if Weaviate is set up.
- The pipeline currently targets a single repository per run (`postgres/postgres` for the demo); multi-repo support would require namespacing the graph.
