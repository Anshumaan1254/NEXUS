# Nexus Decision Provenance Engine - Architecture Document

**Version:** 1.0.0  
**Date:** 2026-05-17  
**IBM Bob Hackathon Project**

---

## Executive Summary

The Nexus Decision Provenance Engine analyzes GitHub repositories to extract hidden architectural decisions, implicit assumptions, and causal chains. It transforms unstructured code history into structured Decision Provenance Records (DPRs) and builds a queryable Causal Temporal Graph (CTG).

### Key Capabilities

- Automated DPR extraction from git history and code
- Causal graph construction mapping decision dependencies
- Assumption decay monitoring for risk analysis
- Real-time analysis with live progress updates
- Interactive React dashboard
- Multi-LLM support (OpenAI, Anthropic, IBM Granite)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                        │
│  React + TypeScript + Vite Dashboard                    │
│  - Home (Input Form)                                    │
│  - Analysis Progress (Live Updates)                     │
│  - DPR Results (Filterable Table)                       │
│  - Causal Graph (react-flow)                            │
│  - Decay Panel (Risk Monitoring)                        │
└─────────────────────────────────────────────────────────┘
                        ↕ HTTP/REST
┌─────────────────────────────────────────────────────────┐
│                     API LAYER                            │
│  FastAPI Backend                                        │
│  - POST /analyze                                        │
│  - GET /analyze/:id/status                              │
│  - GET /analyze/:id/dprs                                │
│  - GET /analyze/:id/graph                               │
│  - GET /analyze/:id/decay                               │
│  - GET /analyze/:id/export                              │
│  Background Task Pipeline (SSE)                         │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                  CORE ENGINE LAYER                       │
│  Phase 1: Repository Scanner                            │
│  Phase 2: Git History Analyzer                          │
│  Phase 3: DPR Extraction Engine (LLM)                   │
│  Phase 4: Causal Graph Builder (LLM)                    │
│  Phase 5: Assumption Decay Monitor                      │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                   SERVICE LAYER                          │
│  LLM Client (OpenAI/Claude/Granite)                     │
│  GitHub Client (PyGithub)                               │
│  Cache Service (In-Memory TTL)                          │
└─────────────────────────────────────────────────────────┘
```

---

## Module Responsibilities

### 1. Frontend (`frontend/`)

**Tech Stack:** React 18, TypeScript, Vite, TailwindCSS, React Query, React Flow, Recharts

**Pages:**

- **Home.tsx**: Input form (repo URL, window, priority areas, min_dprs)
- **AnalysisProgress.tsx**: Live progress polling, animated progress bar
- **Results.tsx**: DPR table with filters, expandable details, export
- **Graph.tsx**: React Flow visualization, node/edge interactions
- **DecayPanel.tsx**: High-risk assumptions, decay signals, monitor queries

### 2. API Layer (`api/`)

**Tech Stack:** FastAPI, Pydantic v2, CORS, Background Tasks, SSE

**Endpoints:**

| Method | Path                  | Description                                   |
| ------ | --------------------- | --------------------------------------------- |
| POST   | `/analyze`            | Submit repo + config, returns analysis_id     |
| GET    | `/analyze/:id/status` | Progress polling (progress_pct, current_step) |
| GET    | `/analyze/:id/dprs`   | Full DPR list                                 |
| GET    | `/analyze/:id/graph`  | CTG edges                                     |
| GET    | `/analyze/:id/decay`  | Decay alerts                                  |
| GET    | `/analyze/:id/export` | Download full JSON                            |
| GET    | `/health`             | Health check                                  |

**Background Pipeline (`api/pipeline.py`):**

```python
async def run_analysis(analysis_id, config):
    # Phase 1: Scan (20%)
    scan_result = await scanner.scan(config.repository)

    # Phase 2: Git Analysis (40%)
    commits = await git_analyzer.analyze(scan_result, config.window)

    # Phase 3: DPR Extraction (60%)
    dprs = await dpr_extractor.extract(commits, config.min_dprs)

    # Phase 4: Causal Graph (80%)
    edges = await graph_builder.build(dprs)

    # Phase 5: Decay Analysis (90%)
    alerts = await decay_monitor.analyze(dprs, commits)

    # Phase 6: Finalize (100%)
    cache_result(analysis_id, NexusOutput(...))
```

### 3. Core Engine (`core/`)

#### `core/scanner/repo_scanner.py`

- Clone GitHub repo to temp directory
- Index files (path, size, language, last_modified)
- Extract design comments from file headers
- Find README, TODO, ARCHITECTURE files
- Detect primary language/framework
- Returns `RepoScanResult`

#### `core/git/history_analyzer.py`

- Fetch git log via GitHub API
- Filter by analysis_window date range
- Score commits for "reasoning density"
- Keywords: because, workaround, temporary, assume, constraint, TODO, FIXME, HACK
- Flag top-N high-reasoning commits
- Returns `List[CommitRecord]`

#### `core/dpr/extractor.py`

- Takes RepoScanResult + CommitRecords
- Calls LLM with structured prompts
- Extracts minimum MIN_DPRS records
- Validates against Pydantic DPR schema
- Marks inferred fields with "INFERRED:" prefix
- Retry logic with exponential backoff
- Returns `List[DPR]`

**LLM Prompt Template:**

```
Analyze this commit and extract a Decision Provenance Record.

Commit: {hash}
Date: {date}
Author: {author}
Message: {message}
Files: {files}

Extract DPR with 20 fields:
- dpr_id, title, component, within_window, decision_date
- decision, rejected_alternatives, explicit_constraints
- implicit_assumptions (prefix with "INFERRED:")
- intended_durability, durability_reasoning
- causal_dependencies, files_involved, commit_refs
- involved_humans, assumption_decay_risk, decay_risk_reasoning
- blast_radius_estimate, blast_radius_reasoning
- active_workarounds

Return valid JSON.
```

#### `core/graph/causal_graph.py`

- Takes List[DPR]
- Calls LLM to identify relationships
- Builds networkx DiGraph
- Relationship types: constrains, enables, required_by, assumption_of, temporal_precedes
- Computes centrality metrics (in-degree, out-degree, betweenness)
- Ensures minimum 20 edges
- Returns `List[CTGEdge]`

#### `core/decay/decay_monitor.py`

- Filters DPRs where assumption_decay_risk = "high"
- Searches commit history for decay signals
- Signals: TODO, FIXME, workaround, deprecated, obsolete
- Computes already_decaying flag
- Generates recommended_monitor_query
- Returns `List[AssumptionDecayRecord]`

### 4. Service Layer (`services/`)

#### `services/llm_client.py`

**Supported Backends:**

1. **OpenAI GPT-4**: `gpt-4-turbo-preview`, JSON mode
2. **Anthropic Claude**: `claude-3-opus-20240229`
3. **IBM Granite**: `ibm/granite-13b-chat-v2` via watsonx.ai

**Key Functions:**

```python
async def extract_dprs(commits, min_dprs, backend="openai") -> List[DPR]
async def build_causal_graph(dprs, backend="openai") -> List[CTGEdge]
async def analyze_commit(commit, backend="openai") -> Dict
```

**Features:**

- Structured output extraction
- Token limit handling (chunking)
- Exponential backoff on rate limits
- Cost estimation and logging
- Response caching (hash-based)

#### `services/github_client.py`

- Repository cloning via PyGithub
- Commit history fetching with pagination
- Rate limit handling (5000 req/hour)
- Authentication via GITHUB_TOKEN

### 5. Data Layer (`models/`)

#### `models/dpr.py` - DPR Model (20 fields)

```python
class DPR(BaseModel):
    dpr_id: str = Field(pattern=r"^DPR-\d{3}$")
    title: str
    component: Literal["Storage", "Optimizer", "WAL", "MVCC", ...]
    within_window: bool
    decision_date: str
    decision: str
    rejected_alternatives: List[str]
    explicit_constraints: List[str]
    implicit_assumptions: List[str]  # Must start with "INFERRED:"
    intended_durability: Literal["temporary", "medium-term", "foundational"]
    durability_reasoning: str
    causal_dependencies: List[str]
    files_involved: List[str]
    commit_refs: List[str]
    involved_humans: List[str]
    assumption_decay_risk: Literal["low", "medium", "high"]
    decay_risk_reasoning: str
    blast_radius_estimate: Literal["low", "medium", "high", "critical"]
    blast_radius_reasoning: str
    active_workarounds: List[str]
```

#### `models/config.py` - AnalysisConfig

```python
class AnalysisConfig(BaseModel):
    repository: str  # GitHub URL
    analysis_window: Literal["1 year", "2 years", "3 years", "5 years", "all time"]
    priority_areas: List[str] = ["all"]
    min_dprs: int = Field(default=25, ge=1, le=100)
```

#### Other Models

- `RepoScanResult`: File index, design comments, language
- `CommitRecord`: Hash, author, date, message, files, reasoning_score
- `CausalGraphEdge`: from_dpr, to_dpr, relationship, explanation
- `AssumptionDecayRecord`: dpr_id, assumption, signals, already_decaying
- `NexusOutput`: Complete analysis result container

---

## Data Flow

### Analysis Request Flow

```
User submits form → POST /analyze
    ↓
Generate analysis_id (UUID)
    ↓
Start background task
    ↓
Return {analysis_id, status: "processing"}
    ↓
Frontend polls GET /analyze/:id/status every 2s
    ↓
Progress updates: 20% → 40% → 60% → 80% → 90% → 100%
    ↓
Frontend redirects to /results/:id
    ↓
Fetch: /dprs, /graph, /decay
```

### Background Processing Flow

```
Phase 1: Repository Scan (20%)
    Clone repo → Index files → Extract comments
    ↓
Phase 2: Git History Analysis (40%)
    Fetch commits → Score reasoning density → Flag high-reasoning
    ↓
Phase 3: DPR Extraction (60%)
    For each commit: Build prompt → Call LLM → Validate → Store
    ↓
Phase 4: Causal Graph (80%)
    Identify relationships → Build graph → Compute metrics
    ↓
Phase 5: Decay Analysis (90%)
    Search signals → Compute decay flags → Generate queries
    ↓
Phase 6: Finalization (100%)
    Build NexusOutput → Cache result → Complete
```

---

## External Dependencies

### APIs

1. **GitHub API**: Repository cloning, commit history (5000 req/hour)
2. **OpenAI API**: GPT-4 for DPR extraction (~$0.01-0.03 per 1K tokens)
3. **Anthropic API**: Claude for alternative LLM (~$0.015-0.075 per 1K tokens)
4. **IBM watsonx.ai**: Granite model for IBM integration

### Python Dependencies

```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0
PyGithub>=2.0.0
gitpython>=3.1.0
openai>=1.0.0
anthropic>=0.18.0
ibm-watsonx-ai>=0.1.0
networkx>=3.0
python-dotenv>=1.0.0
tenacity>=8.2.0
pytest>=7.4.0
```

---

## Folder Structure

```
nexus/
├── api/                    # FastAPI backend
│   ├── main.py            # Routes + app
│   ├── pipeline.py        # Background orchestrator
│   └── cache.py           # In-memory cache
├── core/                  # Business logic
│   ├── scanner/           # Phase 1
│   ├── git/               # Phase 2
│   ├── dpr/               # Phase 3
│   ├── graph/             # Phase 4
│   └── decay/             # Phase 5
├── models/                # Pydantic models
│   ├── dpr.py
│   ├── config.py
│   └── output.py
├── services/              # External clients
│   ├── llm_client.py
│   └── github_client.py
├── tests/                 # All tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md    # This file
│   ├── API_REFERENCE.md
│   └── DEVELOPER_GUIDE.md
├── frontend/              # React dashboard
│   └── src/
│       ├── pages/
│       ├── components/
│       └── api/
├── scripts/               # Utilities
│   ├── setup.sh
│   └── demo.py
├── .github/workflows/     # CI/CD
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## API Contract

### POST /analyze

**Request:**

```json
{
  "repo_url": "https://github.com/postgres/postgres",
  "analysis_window": "2 years",
  "priority_areas": ["MVCC", "WAL"],
  "min_dprs": 25
}
```

**Response:**

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing"
}
```

### GET /analyze/:id/status

**Response:**

```json
{
  "progress_pct": 60,
  "current_step": "Extracting DPRs",
  "dprs_extracted": 15
}
```

### GET /analyze/:id/dprs

**Response:**

```json
{
  "total_dprs": 28,
  "dprs": [
    {
      "dpr_id": "DPR-001",
      "title": "MVCC tuple versioning",
      "component": "MVCC",
      "blast_radius_estimate": "critical",
      ...
    }
  ]
}
```

---

## Security

1. **Input Validation**: All inputs validated via Pydantic
2. **API Keys**: Environment variables only, never logged
3. **Rate Limiting**: 10 req/min for POST, 100 req/min for GET
4. **CORS**: Whitelist in production
5. **Prompt Injection**: Sanitized LLM inputs
6. **Path Traversal**: Sanitized file paths

---

## Performance

### Expected Latency

- POST /analyze: 200ms
- GET /status: 50ms
- Full analysis (small repo): 60-120s
- Full analysis (large repo): 300-600s

### Resource Usage

- Memory: 500MB - 2GB per analysis
- Disk: 100MB - 1GB (temp clone)
- LLM tokens: 10K - 50K per analysis
- Cost: $0.50 - $2.00 per analysis

### Scalability

- Concurrent analyses: 10 (in-memory)
- Max repo size: 1GB
- Max commits: 10,000
- Max DPRs: 100

---

## IBM Bob Usage

### Plan Mode

- TASK 1: Architecture design
- TASK 2: Project structure
- TASK 29-31: Documentation

### Code Mode

- TASK 3-9: Core implementation
- TASK 10-17: API + Frontend
- TASK 32-35: DevOps

### Advanced Mode

- TASK 18-24: Test suite
- TASK 25-28: Quality + Security

### Orchestrator Mode

- TASK 36-40: Final verification

---

## Next Steps

1. ✅ **TASK 1 COMPLETE** - Architecture documented
2. → **TASK 2** - Create project scaffold
3. → **TASK 3** - Implement Pydantic models
4. → Continue through all 40 tasks

---

**End of Architecture Document**
