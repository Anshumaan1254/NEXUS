"""
Nexus Causal Intelligence Platform — FastAPI Backend
Wraps all existing pipeline scripts into REST endpoints.
Serves the dashboard and provides API for any-repo analysis.
"""
import json, sys, os, shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ── Fix encoding on Windows ────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Ensure our modules are importable ──────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "nexus_layer2"))

# ── App ────────────────────────────────────────────────────
app = FastAPI(
    title="Nexus API",
    description="Causal Intelligence Platform — REST API",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ──────────────────────────────────────────────────
OUTPUT_DIR = ROOT / "postgres-analysis" / "output"
DASHBOARD_DIR = ROOT / "nexus-dashboard"


# ═══════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════
class AnalyzeRequest(BaseModel):
    repo_url: str = "https://github.com/postgres/postgres"
    period_years: int = 2

class QueryRequest(BaseModel):
    question: str

class CounterfactualRequest(BaseModel):
    dpr_id: str
    alternative: str
    question: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════════════
def load_nexus_data():
    """Load the merged nexus_data.json (from dashboard dir = active repo)."""
    # Dashboard dir has the currently active repo's data
    for p in [DASHBOARD_DIR / "nexus_data.json", OUTPUT_DIR / "nexus_data.json"]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    raise HTTPException(404, "nexus_data.json not found. Run the pipeline first.")

def load_json_file(name):
    p = OUTPUT_DIR / name
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════

# ── Health ─────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nexus_data_exists": (OUTPUT_DIR / "nexus_data.json").exists(),
        "dprs_json_exists": (OUTPUT_DIR / "nexus_layer1_dprs.json").exists(),
    }


# ── Full nexus_data.json ───────────────────────────────────
@app.get("/api/data")
def get_data():
    """Return the full nexus_data.json."""
    return load_nexus_data()


# ── DPRs ───────────────────────────────────────────────────
@app.get("/api/dprs")
def get_dprs(component: Optional[str] = None, risk: Optional[str] = None):
    """List DPRs with optional filters."""
    data = load_nexus_data()
    dprs = data.get("dprs", [])
    if component:
        dprs = [d for d in dprs if d.get("component", "").lower() == component.lower()]
    if risk:
        dprs = [d for d in dprs if d.get("assumption_decay_risk", "").lower() == risk.lower()]
    return {"count": len(dprs), "dprs": dprs}


@app.get("/api/dprs/{dpr_id}")
def get_dpr(dpr_id: str):
    """Get a single DPR by ID."""
    data = load_nexus_data()
    for d in data.get("dprs", []):
        if d["dpr_id"].upper() == dpr_id.upper():
            # Enrich with risk score
            scores = {s["dpr_id"]: s for s in data.get("risk_scores", [])}
            result = {**d, "risk_score": scores.get(d["dpr_id"])}
            return result
    raise HTTPException(404, f"DPR {dpr_id} not found")


# ── Graph ──────────────────────────────────────────────────
@app.get("/api/graph")
def get_graph():
    """Return graph data for visualization (nodes + edges)."""
    data = load_nexus_data()
    dprs = data.get("dprs", [])
    edges = data.get("ctg_edges", [])
    scores = {s["dpr_id"]: s for s in data.get("risk_scores", [])}

    nodes = []
    for d in dprs:
        score = scores.get(d["dpr_id"], {})
        nodes.append({
            "id": d["dpr_id"],
            "title": d["title"],
            "component": d["component"],
            "blast_radius": d["blast_radius_estimate"],
            "decay_risk": d["assumption_decay_risk"],
            "composite_risk": score.get("composite_risk", 0),
            "workaround_count": len(d.get("active_workarounds", [])),
        })

    return {
        "nodes": nodes,
        "edges": [
            {
                "from": e["from_dpr"],
                "to": e["to_dpr"],
                "relationship": e["relationship"],
                "explanation": e["explanation"],
            }
            for e in edges
        ],
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


# ── Risk Scores ───────────────────────────────────────────
@app.get("/api/risks")
def get_risks():
    """Return risk scores sorted by composite risk."""
    data = load_nexus_data()
    return {"risk_scores": data.get("risk_scores", [])}


# ── Decay Alerts ──────────────────────────────────────────
@app.get("/api/decay")
def get_decay():
    """Return assumption decay alerts."""
    data = load_nexus_data()
    alerts = data.get("assumptions", [])
    return {
        "total": len(alerts),
        "already_decaying": sum(1 for a in alerts if a.get("already_decaying")),
        "alerts": alerts,
    }


# ── Decay Monitor Report ─────────────────────────────────
@app.get("/api/decay/monitor")
def get_decay_monitor():
    """Return the full decay monitor report."""
    data = load_nexus_data()
    return data.get("decay_monitor", {})


# ── Counterfactual Traces ─────────────────────────────────
@app.get("/api/counterfactual")
def get_counterfactual():
    """Return all counterfactual simulation traces."""
    data = load_nexus_data()
    traces = data.get("counterfactual_traces", [])
    return {"total": len(traces), "traces": traces}


@app.get("/api/counterfactual/{scenario_id}")
def get_counterfactual_by_id(scenario_id: str):
    """Get a single counterfactual trace."""
    data = load_nexus_data()
    for t in data.get("counterfactual_traces", []):
        if t.get("scenario_id", "").upper() == scenario_id.upper():
            return t
    raise HTTPException(404, f"Scenario {scenario_id} not found")


# ── Knowledge Concentration ───────────────────────────────
@app.get("/api/knowledge")
def get_knowledge():
    """Return knowledge concentration report."""
    data = load_nexus_data()
    return data.get("knowledge_concentration", {})


# ── Remediation Backlog ───────────────────────────────────
@app.get("/api/backlog")
def get_backlog(priority: Optional[str] = None):
    """Return remediation backlog, optionally filtered by priority."""
    data = load_nexus_data()
    backlog = data.get("remediation_backlog", [])
    if priority:
        backlog = [b for b in backlog if b.get("priority", "").upper() == priority.upper()]
    return {"count": len(backlog), "items": backlog}


# ── Natural Language Query ────────────────────────────────
@app.post("/api/query")
def nl_query(req: QueryRequest):
    """Answer a natural language question about the CTG."""
    try:
        from nl_query import map_question_to_query
        from cypher_queries import NEXUS_QUERIES

        query_name, params = map_question_to_query(req.question)

        if query_name is None:
            # Fall back to searching DPRs by keyword
            data = load_nexus_data()
            q = req.question.lower()
            results = [
                d for d in data.get("dprs", [])
                if q in d.get("title", "").lower()
                or q in d.get("decision", "").lower()
                or q in d.get("component", "").lower()
            ]
            return {
                "question": req.question,
                "method": "keyword_search",
                "results": results[:10],
                "count": len(results),
            }

        query_info = NEXUS_QUERIES.get(query_name, {})
        return {
            "question": req.question,
            "method": "pattern_match",
            "matched_query": query_name,
            "description": query_info.get("description", ""),
            "cypher": query_info.get("cypher", ""),
            "parameters": params if isinstance(params, dict) else {},
            "note": "Execute this Cypher against Neo4j for results",
        }
    except Exception as e:
        return {
            "question": req.question,
            "method": "error",
            "error": str(e),
        }


# ── Search DPRs ───────────────────────────────────────────
@app.get("/api/search")
def search_dprs(q: str = Query(..., description="Search query")):
    """Search DPRs by keyword across all fields."""
    data = load_nexus_data()
    query = q.lower()
    results = []

    for dpr in data.get("dprs", []):
        searchable = " ".join([
            dpr.get("title", ""),
            dpr.get("decision", ""),
            dpr.get("component", ""),
            dpr.get("decay_risk_reasoning", ""),
            dpr.get("blast_radius_reasoning", ""),
            " ".join(dpr.get("implicit_assumptions", [])),
            " ".join(dpr.get("active_workarounds", [])),
        ]).lower()

        if query in searchable:
            results.append({
                "dpr_id": dpr["dpr_id"],
                "title": dpr["title"],
                "component": dpr["component"],
                "blast_radius": dpr["blast_radius_estimate"],
                "decay_risk": dpr["assumption_decay_risk"],
                "snippet": dpr["decision"][:200],
            })

    return {"query": q, "count": len(results), "results": results}


# ── Run Pipeline ──────────────────────────────────────────
@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    """
    Run the full Nexus pipeline.
    For now, re-runs enrichment on existing Layer 1 data.
    In production, this would clone the repo and generate DPRs via Gemini.
    """
    try:
        results = {"steps": []}

        # Step 1: Decay monitor
        try:
            from decay_monitor import run_decay_monitor
            report = run_decay_monitor()
            # Save
            with open(OUTPUT_DIR / "decay_monitor_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            results["steps"].append({"step": "decay_monitor", "status": "ok",
                                     "summary": report.get("summary", {})})
        except Exception as e:
            results["steps"].append({"step": "decay_monitor", "status": "error", "error": str(e)})

        # Step 2: Counterfactual simulation
        try:
            from counterfactual_sim import run_counterfactual_simulations
            cf = run_counterfactual_simulations()
            with open(OUTPUT_DIR / "counterfactual_traces.json", "w", encoding="utf-8") as f:
                json.dump(cf, f, indent=2, default=str)
            results["steps"].append({"step": "counterfactual", "status": "ok",
                                     "traces": len(cf.get("traces", []))})
        except Exception as e:
            results["steps"].append({"step": "counterfactual", "status": "error", "error": str(e)})

        # Step 3: Knowledge concentration
        try:
            from knowledge_concentration import load_data, compute_knowledge_concentration
            out = load_data()
            kc = compute_knowledge_concentration(out)
            with open(OUTPUT_DIR / "knowledge_concentration.json", "w", encoding="utf-8") as f:
                json.dump(kc, f, indent=2, default=str)
            results["steps"].append({"step": "knowledge", "status": "ok",
                                     "spof_alerts": len(kc.get("spof_alerts", []))})
        except Exception as e:
            results["steps"].append({"step": "knowledge", "status": "error", "error": str(e)})

        # Step 4: Merge
        try:
            from merge_nexus_data import merge_nexus_data
            merge_nexus_data()
            results["steps"].append({"step": "merge", "status": "ok"})
        except Exception as e:
            results["steps"].append({"step": "merge", "status": "error", "error": str(e)})

        # Step 5: Copy to dashboard
        src = OUTPUT_DIR / "nexus_data.json"
        dst = DASHBOARD_DIR / "nexus_data.json"
        if src.exists():
            shutil.copy2(src, dst)
            results["steps"].append({"step": "dashboard_sync", "status": "ok"})

        results["status"] = "complete"
        results["timestamp"] = datetime.now(timezone.utc).isoformat()
        return results

    except Exception as e:
        raise HTTPException(500, f"Pipeline error: {e}")


# ── PDF Report ────────────────────────────────────────────
@app.get("/api/report/pdf")
def get_pdf_report():
    """Download the risk report PDF."""
    pdf = OUTPUT_DIR / "nexus_risk_report.pdf"
    if not pdf.exists():
        # Generate it
        try:
            from risk_report_pdf import load_nexus_data as load_nd, build_pdf
            data = load_nd()
            build_pdf(data)
        except Exception as e:
            raise HTTPException(500, f"Failed to generate PDF: {e}")
    return FileResponse(str(pdf), media_type="application/pdf",
                        filename="nexus_risk_report.pdf")


# ── Stats ─────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    """Return summary statistics."""
    data = load_nexus_data()
    dprs = data.get("dprs", [])
    risks = data.get("risk_scores", [])
    alerts = data.get("assumptions", [])
    backlog = data.get("remediation_backlog", [])
    cf = data.get("counterfactual_traces", [])

    components = {}
    for d in dprs:
        c = d.get("component", "Unknown")
        components[c] = components.get(c, 0) + 1

    blast = {}
    for d in dprs:
        b = d.get("blast_radius_estimate", "unknown")
        blast[b] = blast.get(b, 0) + 1

    return {
        "total_dprs": len(dprs),
        "total_edges": len(data.get("ctg_edges", [])),
        "total_decay_alerts": len(alerts),
        "already_decaying": sum(1 for a in alerts if a.get("already_decaying")),
        "critical_risk_dprs": sum(1 for r in risks if r.get("composite_risk", 0) >= 70),
        "p0_items": sum(1 for b in backlog if b.get("priority") == "P0"),
        "counterfactual_scenarios": len(cf),
        "components": components,
        "blast_radius_breakdown": blast,
        "top_risk": risks[0] if risks else None,
    }


# ── Neo4j Integration ────────────────────────────────────
@app.post("/api/neo4j/load")
def neo4j_load(repo_name: str = Query("postgres", description="Repo to load")):
    """Load a repo's DPR data into Neo4j."""
    try:
        from neo4j_loader import load_into_neo4j

        if repo_name == "postgres":
            path = OUTPUT_DIR / "nexus_layer1_dprs.json"
        else:
            path = ROOT / "analyses" / repo_name / "output" / "nexus_layer1_dprs.json"

        if not path.exists():
            raise HTTPException(404, f"No Layer 1 data for '{repo_name}'")

        stats = load_into_neo4j(str(path))
        return {"status": "loaded", "repo": repo_name, "graph_stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Neo4j load failed: {e}")


@app.get("/api/neo4j/stats")
def neo4j_stats():
    """Get Neo4j graph statistics."""
    try:
        from neo4j_loader import get_neo4j_driver, get_graph_stats
        driver = get_neo4j_driver()
        try:
            stats = get_graph_stats(driver)
            return {"status": "connected", **stats}
        finally:
            driver.close()
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


class CypherRequest(BaseModel):
    query: str
    params: Optional[dict] = None

@app.post("/api/neo4j/query")
def neo4j_query(req: CypherRequest):
    """Execute a Cypher query against Neo4j."""
    # Safety: block destructive queries
    q = req.query.strip().upper()
    if any(kw in q for kw in ["DELETE", "DETACH", "DROP", "CREATE INDEX", "REMOVE"]):
        raise HTTPException(400, "Destructive queries are not allowed via API")

    try:
        from neo4j_loader import get_neo4j_driver
        driver = get_neo4j_driver()
        try:
            with driver.session() as session:
                result = session.run(req.query, **(req.params or {}))
                records = [dict(r) for r in result]
                # Convert Neo4j types to JSON-serializable
                clean = []
                for rec in records:
                    row = {}
                    for k, v in rec.items():
                        if hasattr(v, "__dict__"):
                            row[k] = dict(v)
                        else:
                            row[k] = v
                    clean.append(row)
                return {"count": len(clean), "results": clean}
        finally:
            driver.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Cypher query failed: {e}")


# ── LLM Provider Info ────────────────────────────────────
@app.get("/api/llm/status")
def llm_status():
    """Check which LLM provider is configured."""
    providers = []
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        providers.append("gemini")
    if os.environ.get("WATSONX_API_KEY"):
        providers.append("watsonx")
    return {
        "configured_providers": providers,
        "active": providers[0] if providers else None,
        "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")),
        "watsonx_key_set": bool(os.environ.get("WATSONX_API_KEY")),
        "watsonx_project_set": bool(os.environ.get("WATSONX_PROJECT_ID")),
    }


class RepoAnalyzeRequest(BaseModel):
    repo_url: str
    focus: Optional[str] = None
    num_dprs: int = 10

@app.post("/api/analyze/repo")
def analyze_repo(req: RepoAnalyzeRequest):
    """
    Clone any GitHub repo and generate DPRs using configured LLM (Gemini or WatsonX).
    Requires GEMINI_API_KEY or WATSONX_API_KEY environment variable.
    """

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("WATSONX_API_KEY")
    if not api_key:
        raise HTTPException(400,
            "No LLM key set. Use $env:GEMINI_API_KEY or $env:WATSONX_API_KEY")

    repo_name = req.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    analyses_dir = ROOT / "analyses" / repo_name / "output"
    analyses_dir.mkdir(parents=True, exist_ok=True)

    try:
        from repo_analyzer import clone_repo, scan_repo, generate_dprs_with_gemini
        from repo_analyzer import build_layer1_output, run_full_pipeline, get_llm_provider

        # Clone
        clone_dir = ROOT / ".repos" / repo_name
        clone_repo(req.repo_url, clone_dir)

        # Scan
        scan_data = scan_repo(clone_dir)

        # Generate DPRs using configured LLM
        provider = get_llm_provider()
        dprs, edges, decay_alerts = generate_dprs_with_gemini(
            provider, scan_data, req.repo_url, req.focus, req.num_dprs
        )

        # Save Layer 1
        layer1 = build_layer1_output(dprs, edges, decay_alerts, req.repo_url)
        l1_path = analyses_dir / "nexus_layer1_dprs.json"
        with open(l1_path, "w", encoding="utf-8") as f:
            json.dump(layer1, f, indent=2, default=str)

        # Run pipeline
        run_full_pipeline(analyses_dir)

        # Copy to dashboard only (don't overwrite postgres-analysis/output)
        nexus_path = analyses_dir / "nexus_data.json"
        if nexus_path.exists():
            shutil.copy2(nexus_path, DASHBOARD_DIR / "nexus_data.json")

        return {
            "status": "complete",
            "repo": req.repo_url,
            "dprs_generated": len(dprs),
            "edges_generated": len(edges),
            "decay_alerts": len(decay_alerts),
            "output_dir": str(analyses_dir),
        }

    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Gemini returned invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")


@app.get("/api/repos")
def list_repos():
    """List all analyzed repositories."""
    repos = []
    analyses_dir = ROOT / "analyses"
    if analyses_dir.exists():
        for d in analyses_dir.iterdir():
            if d.is_dir() and (d / "output" / "nexus_data.json").exists():
                data = json.loads((d / "output" / "nexus_data.json").read_text(encoding="utf-8"))
                meta = data.get("metadata", {})
                repos.append({
                    "name": d.name,
                    "repository": meta.get("repository", ""),
                    "total_dprs": meta.get("total_dprs", 0),
                    "generated_at": meta.get("generated_at", ""),
                })
    # Also include the default PostgreSQL analysis
    if (OUTPUT_DIR / "nexus_data.json").exists():
        data = json.loads((OUTPUT_DIR / "nexus_data.json").read_text(encoding="utf-8"))
        meta = data.get("metadata", {})
        repos.insert(0, {
            "name": "postgres",
            "repository": meta.get("repository", ""),
            "total_dprs": meta.get("total_dprs", 0),
            "generated_at": meta.get("generated_at", ""),
            "default": True,
        })
    return {"count": len(repos), "repos": repos}


@app.post("/api/repos/switch")
def switch_repo(repo_name: str = Query(..., description="Repo name to switch to")):
    """Switch the active dashboard data to a different analyzed repo."""
    analyses_dir = ROOT / "analyses" / repo_name / "output"
    nexus_path = analyses_dir / "nexus_data.json"

    if repo_name == "postgres":
        nexus_path = OUTPUT_DIR / "nexus_data.json"

    if not nexus_path.exists():
        raise HTTPException(404, f"No analysis found for '{repo_name}'")

    # Copy to dashboard
    shutil.copy2(nexus_path, DASHBOARD_DIR / "nexus_data.json")
    return {"status": "switched", "active_repo": repo_name}


# ── Serve Dashboard ───────────────────────────────────────
if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  NEXUS API SERVER")
    print("=" * 60)
    print(f"  Dashboard: http://localhost:8000")
    print(f"  API Docs:  http://localhost:8000/docs")
    print(f"  Health:    http://localhost:8000/api/health")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
