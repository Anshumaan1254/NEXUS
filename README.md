# Nexus Decision Provenance Engine

**AI-Powered Architectural Decision Analysis for GitHub Repositories**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Problem Statement

Software teams lose critical architectural knowledge over time:

- **Hidden Decisions**: Architectural choices are never documented
- **Implicit Assumptions**: Key assumptions exist only in developers' heads
- **Knowledge Loss**: When developers leave, their reasoning disappears
- **Technical Debt**: Workarounds accumulate without understanding why

**Cost:** Teams spend 30-40% of development time rediscovering past decisions.

---

## 💡 Solution

Nexus automatically extracts Decision Provenance Records (DPRs) from any GitHub repository by analyzing:

- Git commit history with reasoning signal detection
- Code comments and design documentation
- File changes and their relationships
- Temporal evolution of decisions

**Output:** Machine-readable DPRs with causal graphs and risk assessments.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                              │
│  React + TypeScript Dashboard                           │
│  - Analysis Input Form                                  │
│  - Live Progress Tracking                               │
│  - DPR Results Table                                    │
│  - Causal Graph Visualization                           │
│  - Decay Risk Monitoring                                │
└─────────────────────────────────────────────────────────┘
                        ↕ REST API
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                         │
│  8 REST Endpoints + Background Tasks                    │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                  CORE ENGINE                             │
│  Phase 1: Repository Scanner                            │
│  Phase 2: Git History Analyzer (15 reasoning signals)   │
│  Phase 3: DPR Extractor (LLM-powered)                   │
│  Phase 4: Causal Graph Builder (networkx)               │
│  Phase 5: Assumption Decay Monitor                      │
└─────────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────────┐
│                  LLM BACKENDS                            │
│  OpenAI GPT-4 | Anthropic Claude | IBM Granite          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- GitHub Personal Access Token
- OpenAI API Key (or Anthropic/IBM Granite)

### Installation

```bash
# Clone repository
git clone https://github.com/pranshujain8532/bob-hackathon.git
cd bob-hackathon

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: GITHUB_TOKEN, OPENAI_API_KEY (or ANTHROPIC_API_KEY)
```

### Run Analysis

```bash
# Start FastAPI server
uvicorn nexus.api.main:app --reload

# Open browser
http://localhost:8000

# Or use CLI
python -m nexus.cli analyze \
  --repo https://github.com/psf/requests \
  --window "2 years" \
  --min-dprs 25
```

---

## 📊 Example Output

### Decision Provenance Record (DPR)

```json
{
  "dpr_id": "DPR-001",
  "title": "MVCC tuple versioning strategy",
  "component": "MVCC",
  "within_window": true,
  "decision_date": "2024-03",
  "decision": "Use tuple versioning for MVCC implementation",
  "rejected_alternatives": [
    "Timestamp-based versioning - rejected due to clock skew issues"
  ],
  "explicit_constraints": [
    "Must support concurrent transactions",
    "Must maintain ACID properties"
  ],
  "implicit_assumptions": [
    "INFERRED: Assumes sufficient disk space for tuple versions",
    "INFERRED: Assumes autovacuum will clean up dead tuples"
  ],
  "intended_durability": "foundational",
  "blast_radius_estimate": "critical",
  "assumption_decay_risk": "low",
  "active_workarounds": []
}
```

### Causal Graph Edge

```json
{
  "from_dpr": "DPR-001",
  "to_dpr": "DPR-007",
  "relationship": "constrains",
  "explanation": "MVCC tuple versioning constrains autovacuum design",
  "within_window": true
}
```

---

## 🎨 Features

### ✅ Implemented

1. **Multi-Backend LLM Support**
   - OpenAI GPT-4
   - Anthropic Claude
   - IBM Granite (watsonx.ai)

2. **Reasoning Signal Detection**
   - 15 keywords: because, workaround, TODO, FIXME, HACK, etc.
   - Commit scoring algorithm
   - High-reasoning commit flagging

3. **Complete DPR Schema**
   - 20 required fields
   - Pydantic v2 validation
   - INFERRED: prefix for implicit assumptions

4. **Causal Graph Construction**
   - 5 relationship types
   - Minimum 20 edges guaranteed
   - networkx integration
   - Centrality metrics

5. **Assumption Decay Monitoring**
   - High-risk assumption tracking
   - Decay signal detection
   - Monitoring query generation

6. **Type-Safe Data Models**
   - 7 Pydantic models
   - Field validators
   - JSON schema export

---

## 🛠️ Tech Stack

| Layer          | Technology                     |
| -------------- | ------------------------------ |
| **Backend**    | FastAPI, Python 3.11+          |
| **Frontend**   | React 18, TypeScript, Vite     |
| **LLM**        | OpenAI, Anthropic, IBM Granite |
| **Graph**      | networkx, matplotlib           |
| **GitHub**     | PyGithub, gitpython            |
| **Validation** | Pydantic v2                    |
| **Testing**    | pytest, pytest-asyncio         |
| **DevOps**     | Docker, GitHub Actions         |

---

## 📖 API Documentation

### POST /analyze

Submit repository for analysis

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

Poll analysis progress

**Response:**

```json
{
  "progress_pct": 60,
  "current_step": "Extracting DPRs",
  "dprs_extracted": 15
}
```

### GET /analyze/:id/dprs

Get all extracted DPRs

### GET /analyze/:id/graph

Get causal graph edges

### GET /analyze/:id/decay

Get decay alerts

### GET /analyze/:id/export

Download complete JSON

### GET /health

Health check

### GET /docs

Interactive API documentation (Swagger UI)

---

## 🤖 IBM Bob Usage

This project was built using IBM Bob IDE across all modes:

### 📝 Plan Mode

- **TASK 1**: Architecture design and documentation
- System design and data flow planning

### 💻 Code Mode

- **TASKS 2-17**: All implementation work
- Models, core engine, API, frontend

### 🛠️ Advanced Mode

- **TASKS 18-28**: Testing and code quality
- Unit tests, integration tests, security audit

### 🎯 Orchestrator Mode

- **TASKS 36-40**: Final coordination
- Test execution, verification, submission

**Bob was essential for:**

- Rapid prototyping of complex architectures
- Type-safe model generation
- Multi-file refactoring
- Test suite creation
- Documentation generation

---

## 📁 Project Structure

```
nexus/
├── api/                    # FastAPI backend
│   ├── main.py            # Routes + app
│   ├── pipeline.py        # Background tasks
│   └── cache.py           # Result caching
├── core/                  # Business logic
│   ├── scanner/           # Phase 1: Repo scanner
│   ├── git/               # Phase 2: History analyzer
│   ├── dpr/               # Phase 3: DPR extractor
│   ├── graph/             # Phase 4: Graph builder
│   └── decay/             # Phase 5: Decay monitor
├── models/                # Pydantic models
│   ├── dpr.py            # DPR (20 fields)
│   ├── config.py         # AnalysisConfig
│   ├── output.py         # NexusOutput
│   └── ...
├── services/              # External clients
│   ├── llm_client.py     # Multi-backend LLM
│   └── github_client.py  # GitHub API
├── tests/                 # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── frontend/              # React dashboard
    └── src/
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=nexus --cov-report=html

# Run specific test suite
pytest nexus/tests/unit/
pytest nexus/tests/integration/
pytest nexus/tests/e2e/

# Run linting
ruff check .
mypy .
black --check .
```

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -t nexus:latest .

# Run with docker-compose
docker-compose up

# Access
http://localhost:8000  # API
http://localhost:3000  # Frontend
```

---

## 🔒 Security

- All API keys loaded from environment variables
- Input validation via Pydantic
- Rate limiting on all endpoints
- CORS configuration for production
- No sensitive data in logs
- Path traversal prevention

See [docs/SECURITY.md](docs/SECURITY.md) for details.

---

## 📈 Performance

| Metric                      | Value         |
| --------------------------- | ------------- |
| Small repo (< 1000 commits) | 60-120s       |
| Large repo (> 5000 commits) | 300-600s      |
| Memory usage                | 500MB - 2GB   |
| LLM tokens per analysis     | 10K - 50K     |
| Estimated cost              | $0.50 - $2.00 |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- **IBM Bob IDE**: Essential for rapid development
- **OpenAI**: GPT-4 for DPR extraction
- **Anthropic**: Claude for alternative backend
- **IBM**: Granite model integration

---

## 📞 Contact

**Project:** Nexus Decision Provenance Engine  
**Repository:** https://github.com/pranshujain8532/bob-hackathon  
**Hackathon:** IBM Bob Hackathon 2026

---

**Built with ❤️ using IBM Bob IDE**
