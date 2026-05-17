"""
Nexus - Generic Repository Analyzer
Clones any GitHub repo, scans its structure, and uses LLM (Gemini or WatsonX)
to generate Decision Provenance Records (DPRs).

Usage:
  py repo_analyzer.py https://github.com/WordPress/WordPress --focus "REST API,Database,Authentication"
  py repo_analyzer.py https://github.com/WordPress/WordPress --llm watsonx

Requires: GEMINI_API_KEY or WATSONX_API_KEY environment variable
"""
import json, sys, os, shutil, subprocess, re, argparse, textwrap
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

# ── LLM Provider ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent / "nexus_layer2"))

def get_gemini_client():
    """Backwards-compatible: returns provider name."""
    return get_llm_provider()

def get_llm_provider(preferred=None):
    """Get the configured LLM provider."""
    if preferred:
        return preferred
    if os.environ.get("WATSONX_API_KEY"):
        return "watsonx"
    elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    else:
        print("ERROR: No LLM provider configured.")
        print("  Set one of:")
        print("    $env:GEMINI_API_KEY='...'")
        print("    $env:WATSONX_API_KEY='...' + $env:WATSONX_PROJECT_ID='...'")
        sys.exit(1)


# ── Repo Cloning ──────────────────────────────────────────
def clone_repo(repo_url, target_dir, depth=1):
    """Download a repo. Tries git first, falls back to GitHub zip download."""
    target_dir = Path(target_dir)
    print(f"\n📥 Downloading {repo_url}...")
    if target_dir.exists() and any(target_dir.iterdir()):
        print(f"   Already exists at {target_dir}, reusing.")
        return target_dir

    # Try git clone first
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", str(depth), repo_url, str(target_dir)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print(f"   Cloned via git to {target_dir}")
            return target_dir
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # git not available or timed out

    # Fallback: download zip from GitHub
    print("   git not available, downloading zip archive...")
    import urllib.request, zipfile, io

    # Convert GitHub URL to zip download URL
    # https://github.com/owner/repo -> https://github.com/owner/repo/archive/refs/heads/master.zip
    zip_url = repo_url.rstrip("/")
    if not zip_url.endswith(".git"):
        zip_url_main = zip_url + "/archive/refs/heads/main.zip"
        zip_url_master = zip_url + "/archive/refs/heads/master.zip"
    else:
        base = zip_url[:-4]
        zip_url_main = base + "/archive/refs/heads/main.zip"
        zip_url_master = base + "/archive/refs/heads/master.zip"

    target_dir.mkdir(parents=True, exist_ok=True)

    for url in [zip_url_main, zip_url_master]:
        try:
            print(f"   Trying {url}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Nexus/1.0"})
            response = urllib.request.urlopen(req, timeout=120)
            zip_data = response.read()

            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Extract — zip contains a single top-level dir like "repo-main/"
                top_dirs = set(n.split("/")[0] for n in zf.namelist() if "/" in n)
                top_dir = top_dirs.pop() if len(top_dirs) == 1 else None

                for member in zf.namelist():
                    if top_dir and member.startswith(top_dir + "/"):
                        rel_path = member[len(top_dir) + 1:]
                    else:
                        rel_path = member

                    if not rel_path:
                        continue

                    out_path = target_dir / rel_path
                    if member.endswith("/"):
                        out_path.mkdir(parents=True, exist_ok=True)
                    else:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(out_path, "wb") as f:
                            f.write(zf.read(member))

            print(f"   ✅ Downloaded and extracted to {target_dir}")
            return target_dir
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        except Exception as e:
            print(f"   ⚠️  Failed: {e}")
            continue

    print("   ❌ Could not download repository")
    sys.exit(1)


# ── Repo Scanning ─────────────────────────────────────────
def scan_repo(repo_dir, max_files=500):
    """Scan the repo structure and collect key files."""
    print(f"\n🔍 Scanning repo structure...")
    repo_dir = Path(repo_dir)

    file_tree = []
    readme_content = ""
    config_files = []
    key_source_files = []
    total_files = 0

    # File extensions to focus on by language
    code_exts = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".php", ".rb", ".go", ".rs",
        ".java", ".c", ".h", ".cpp", ".cs", ".swift", ".kt",
    }
    config_exts = {
        ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml",
        ".env", ".conf",
    }
    config_names = {
        "Dockerfile", "docker-compose.yml", "Makefile", "CMakeLists.txt",
        "package.json", "composer.json", "Cargo.toml", "go.mod",
        "requirements.txt", "setup.py", "pyproject.toml",
        "webpack.config.js", "vite.config.ts", ".github",
    }

    for root, dirs, files in os.walk(repo_dir):
        # Skip hidden/vendor dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in (
            "node_modules", "vendor", "__pycache__", ".git", "dist", "build"
        )]

        rel_root = Path(root).relative_to(repo_dir)
        for f in files:
            total_files += 1
            rel_path = str(rel_root / f)
            ext = Path(f).suffix.lower()

            # Collect file tree (limited)
            if len(file_tree) < max_files:
                file_tree.append(rel_path)

            # README
            if f.lower().startswith("readme"):
                try:
                    content = (Path(root) / f).read_text(encoding="utf-8", errors="ignore")
                    if len(content) > len(readme_content):
                        readme_content = content[:8000]
                except: pass

            # Config files
            if f in config_names or ext in config_exts:
                try:
                    content = (Path(root) / f).read_text(encoding="utf-8", errors="ignore")
                    config_files.append({
                        "path": rel_path,
                        "content": content[:2000],
                    })
                except: pass

            # Key source files (sample up to 30)
            if ext in code_exts and len(key_source_files) < 30:
                try:
                    content = (Path(root) / f).read_text(encoding="utf-8", errors="ignore")
                    # Only include files with substantial content
                    if len(content) > 200:
                        key_source_files.append({
                            "path": rel_path,
                            "content": content[:3000],
                            "lines": content.count("\n"),
                        })
                except: pass

    print(f"   Total files: {total_files}")
    print(f"   Config files found: {len(config_files)}")
    print(f"   Key source files sampled: {len(key_source_files)}")

    return {
        "total_files": total_files,
        "file_tree": file_tree[:300],
        "readme": readme_content,
        "config_files": config_files[:15],
        "key_source_files": key_source_files[:20],
    }


# ── Gemini DPR Generation ────────────────────────────────
DPR_GENERATION_PROMPT = textwrap.dedent("""\
You are Nexus, a causal intelligence engine for software architecture comprehension.

Analyze the following repository and generate Decision Provenance Records (DPRs).

## Repository Context
{repo_context}

## Focus Areas
{focus_areas}

## Instructions
Generate exactly {num_dprs} DPRs as a JSON array. Each DPR must have this EXACT structure:

```json
{{
  "dpr_id": "DPR-001",
  "title": "Short descriptive title",
  "component": "ComponentName",
  "within_window": true,
  "decision_date": "2023-Q1",
  "decision": "What was decided and implemented",
  "rejected_alternatives": ["Alt 1", "Alt 2"],
  "constraints_inherited": ["Constraint 1"],
  "implicit_assumptions": ["Assumption 1", "Assumption 2"],
  "blast_radius_estimate": "critical|high|medium|low",
  "blast_radius_reasoning": "Why this blast radius",
  "assumption_decay_risk": "high|medium|low",
  "decay_risk_reasoning": "Why this decay risk level",
  "intended_durability": "foundational|medium-term|short-term",
  "durability_reasoning": "Why this durability",
  "active_workarounds": ["Workaround 1"],
  "files_involved": ["path/to/file.ext"],
  "involved_humans": ["Author Name"],
  "key_commits": ["commit description"]
}}
```

CRITICAL RULES:
- blast_radius_estimate must be one of: critical, high, medium, low
- assumption_decay_risk must be one of: high, medium, low
- intended_durability must be one of: foundational, medium-term, short-term
- Each DPR must have at least 2 implicit_assumptions
- Focus on ARCHITECTURAL decisions, not trivial code choices
- Be specific to THIS codebase, not generic patterns

Return ONLY the JSON array, no markdown fences, no explanation.
""")

CTG_GENERATION_PROMPT = textwrap.dedent("""\
Given these DPRs, generate the Causal Temporal Graph edges.

## DPRs
{dprs_json}

## Instructions
Generate CTG edges as a JSON array. Each edge:
```json
{{
  "from_dpr": "DPR-001",
  "to_dpr": "DPR-002",
  "relationship": "constrains|enables|requires|required_by|temporal_precedes|assumption_of",
  "explanation": "Why this relationship exists"
}}
```

Rules:
- relationship must be one of: constrains, enables, requires, required_by, temporal_precedes, assumption_of
- Generate {num_edges} meaningful edges
- Focus on causal relationships, not just temporal ordering

Return ONLY the JSON array.
""")

DECAY_PROMPT = textwrap.dedent("""\
Given these DPRs, identify assumptions that are decaying or at risk.

## DPRs
{dprs_json}

## Instructions
Generate assumption decay alerts as a JSON array. Each alert:
```json
{{
  "dpr_id": "DPR-001",
  "assumption": "The specific assumption text",
  "already_decaying": true,
  "decay_evidence": "Evidence that this assumption is breaking",
  "earliest_signal_date": "2024-Q1",
  "decay_signals_found": ["Signal 1", "Signal 2"],
  "recommended_monitor_query": "How to monitor this"
}}
```

Generate {num_alerts} alerts, focusing on the most critical assumptions.
Return ONLY the JSON array.
""")


def generate_dprs_with_gemini(provider, scan_data, repo_url, focus_areas, num_dprs=10):
    """Use LLM (Gemini or WatsonX) to generate DPRs from scanned repo data."""
    from llm_provider import call_llm, parse_json_response

    print(f"\n🤖 Generating {num_dprs} DPRs with {provider}...")

    # Build repo context
    repo_context = f"Repository: {repo_url}\n"
    repo_context += f"Total files: {scan_data['total_files']}\n\n"

    repo_context += "## README (excerpt)\n"
    repo_context += scan_data["readme"][:4000] + "\n\n"

    repo_context += "## File Tree (top-level structure)\n"
    dirs = defaultdict(int)
    for f in scan_data["file_tree"]:
        top = f.split("/")[0] if "/" in f else f
        dirs[top] += 1
    for d, count in sorted(dirs.items(), key=lambda x: -x[1])[:30]:
        repo_context += f"  {d}/ ({count} files)\n"

    repo_context += "\n## Config Files\n"
    for cf in scan_data["config_files"][:8]:
        repo_context += f"\n### {cf['path']}\n{cf['content'][:1000]}\n"

    repo_context += "\n## Key Source Files (excerpts)\n"
    for sf in scan_data["key_source_files"][:12]:
        repo_context += f"\n### {sf['path']} ({sf['lines']} lines)\n{sf['content'][:1500]}\n"

    # Step 1: Generate DPRs
    prompt = DPR_GENERATION_PROMPT.format(
        repo_context=repo_context[:25000],
        focus_areas=focus_areas or "All major architectural decisions",
        num_dprs=num_dprs,
    )
    dprs_text = call_llm(prompt, provider)
    dprs = parse_json_response(dprs_text)
    print(f"   ✅ Generated {len(dprs)} DPRs")

    # Step 2: Generate CTG edges
    print(f"   🔗 Generating CTG edges...")
    num_edges = min(len(dprs) * 2, 30)
    edge_prompt = CTG_GENERATION_PROMPT.format(
        dprs_json=json.dumps(dprs, indent=2)[:15000],
        num_edges=num_edges,
    )
    edges_text = call_llm(edge_prompt, provider)
    edges = parse_json_response(edges_text)
    print(f"   ✅ Generated {len(edges)} CTG edges")

    # Step 3: Generate decay alerts
    print(f"   ⚠️  Generating decay alerts...")
    num_alerts = max(3, len(dprs) // 3)
    decay_prompt = DECAY_PROMPT.format(
        dprs_json=json.dumps(dprs, indent=2)[:15000],
        num_alerts=num_alerts,
    )
    decay_text = call_llm(decay_prompt, provider)
    decay_alerts = parse_json_response(decay_text)
    print(f"   ✅ Generated {len(decay_alerts)} decay alerts")

    return dprs, edges, decay_alerts


# ── Output Builder ────────────────────────────────────────
def build_layer1_output(dprs, edges, decay_alerts, repo_url):
    """Build the nexus_layer1_dprs.json format."""
    return {
        "nexus_layer1_output": {
            "repository": repo_url,
            "analysis_window": "2023-01-01 to present",
            "total_dprs": len(dprs),
            "dprs": dprs,
            "ctg_edges": edges,
            "assumption_decay_prescan": decay_alerts,
        }
    }


def run_full_pipeline(output_dir):
    """Run the enrichment pipeline (decay monitor, counterfactual, knowledge, merge)."""
    print(f"\n🔄 Running enrichment pipeline...")
    sys.path.insert(0, str(Path(__file__).resolve().parent / "nexus_layer2"))

    # Decay monitor
    try:
        from decay_monitor import run_decay_monitor
        report = run_decay_monitor(output_dir / "nexus_layer1_dprs.json")
        with open(output_dir / "decay_monitor_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print("   ✅ Decay monitor complete")
    except Exception as e:
        print(f"   ⚠️  Decay monitor: {e}")

    # Counterfactual simulation (LLM-powered for any repo)
    try:
        l1_data = json.loads((output_dir / "nexus_layer1_dprs.json").read_text(encoding="utf-8"))
        l1 = l1_data["nexus_layer1_output"]
        dprs_list = l1["dprs"]
        edges_list = l1["ctg_edges"]

        # Generate scenarios via LLM
        from llm_provider import call_llm, parse_json_response, get_llm_provider
        import networkx as nx

        provider = get_llm_provider()
        dprs_summary = json.dumps([{
            "dpr_id": d["dpr_id"], "title": d["title"],
            "component": d["component"], "decision": d["decision"][:200],
            "blast_radius_estimate": d["blast_radius_estimate"]
        } for d in dprs_list], indent=2)

        cf_prompt = textwrap.dedent(f"""\
        Given these architectural DPRs, generate 5 counterfactual "what-if" scenarios.
        Each scenario explores what would change if a key decision had been made differently.

        ## DPRs
        {dprs_summary[:8000]}

        ## Instructions
        Generate 5 scenarios as JSON array:
        ```json
        [{{
          "scenario_id": "CF-001",
          "target_dpr": "DPR-001",
          "question": "What if X was chosen instead of Y?",
          "alternative": "The alternative approach",
          "reasoning": "Why this alternative matters"
        }}]
        ```
        Return ONLY the JSON array.
        """)

        cf_text = call_llm(cf_prompt, provider)
        scenarios = parse_json_response(cf_text)

        # Build graph and trace impacts
        G = nx.DiGraph()
        for d in dprs_list:
            G.add_node(d["dpr_id"], **{k: d.get(k, "") for k in
                ["title", "component", "blast_radius_estimate"]})
        for e in edges_list:
            G.add_edge(e["from_dpr"], e["to_dpr"],
                       relationship=e.get("relationship", "related"))

        dprs_map = {d["dpr_id"]: d for d in dprs_list}
        traces = []
        for sc in scenarios:
            tid = sc["target_dpr"]
            if tid not in G:
                continue
            downstream = sorted(nx.descendants(G, tid))
            impacts = []
            for did in downstream:
                if did not in dprs_map:
                    continue
                d = dprs_map[did]
                try:
                    sp = nx.shortest_path(G, tid, did)
                    rel = G.edges[sp[0], sp[1]].get("relationship", "related")
                    dist = len(sp) - 1
                except Exception:
                    rel, dist = "unknown", 0
                impacts.append({
                    "dpr_id": did, "title": d["title"],
                    "component": d["component"], "relationship": rel,
                    "distance": dist, "blast_radius": d["blast_radius_estimate"],
                    "would_change": f"Change propagates via '{rel}' to {d['title']}."
                })
            crit = sum(1 for i in impacts if i["blast_radius"] == "critical")
            comps = sorted(set(dprs_map[d]["component"]
                             for d in downstream if d in dprs_map))
            risk_level = ("extreme" if crit >= 2 or len(impacts) >= 5
                          else "high" if crit >= 1
                          else "medium" if len(impacts) >= 2 else "low")
            traces.append({
                "scenario_id": sc.get("scenario_id", f"CF-{len(traces)+1:03d}"),
                "target_dpr": tid,
                "target_title": dprs_map.get(tid, {}).get("title", ""),
                "question": sc["question"],
                "original_decision": dprs_map.get(tid, {}).get("decision", ""),
                "alternative": sc["alternative"],
                "reasoning": sc["reasoning"],
                "affected_count": len(downstream),
                "affected_components": comps,
                "impacts": impacts,
                "risk": {"level": risk_level, "critical": crit, "total": len(impacts)},
            })

        cf_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository": l1["repository"],
            "traces": traces,
        }
        with open(output_dir / "counterfactual_traces.json", "w", encoding="utf-8") as f:
            json.dump(cf_result, f, indent=2, default=str)
        print(f"   ✅ Counterfactual simulation: {len(traces)} scenarios")
    except Exception as e:
        print(f"   ⚠️  Counterfactual: {e}")

    # Knowledge concentration
    try:
        from knowledge_concentration import compute_knowledge_concentration
        l1_data = json.loads((output_dir / "nexus_layer1_dprs.json").read_text(encoding="utf-8"))
        kc = compute_knowledge_concentration(l1_data["nexus_layer1_output"])
        with open(output_dir / "knowledge_concentration.json", "w", encoding="utf-8") as f:
            json.dump(kc, f, indent=2, default=str)
        print("   ✅ Knowledge concentration complete")
    except Exception as e:
        print(f"   ⚠️  Knowledge concentration: {e}")

    # Merge
    try:
        from merge_nexus_data import build_risk_scores, build_remediation_backlog
        l1 = json.loads((output_dir / "nexus_layer1_dprs.json").read_text(encoding="utf-8"))["nexus_layer1_output"]

        decay_report = {}
        kc_data = {}
        cf_traces = []
        for name, var in [("decay_monitor_report.json", "decay"),
                          ("knowledge_concentration.json", "kc"),
                          ("counterfactual_traces.json", "cf")]:
            p = output_dir / name
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if var == "decay": decay_report = data
                elif var == "kc": kc_data = data
                elif var == "cf": cf_traces = data.get("traces", [])

        risk_scores = build_risk_scores(l1["dprs"], l1["ctg_edges"], l1["assumption_decay_prescan"])
        backlog = build_remediation_backlog(l1["dprs"], risk_scores, l1["assumption_decay_prescan"])

        nexus_data = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "repository": l1["repository"],
                "analysis_window": l1["analysis_window"],
                "total_dprs": l1["total_dprs"],
                "total_edges": len(l1["ctg_edges"]),
                "total_decay_alerts": len(l1["assumption_decay_prescan"]),
            },
            "dprs": l1["dprs"],
            "ctg_edges": l1["ctg_edges"],
            "assumptions": l1["assumption_decay_prescan"],
            "risk_scores": risk_scores,
            "remediation_backlog": backlog,
            "counterfactual_traces": cf_traces,
            "knowledge_concentration": kc_data,
            "decay_monitor": decay_report,
        }

        with open(output_dir / "nexus_data.json", "w", encoding="utf-8") as f:
            json.dump(nexus_data, f, indent=2, default=str)
        print(f"   ✅ nexus_data.json merged ({(output_dir / 'nexus_data.json').stat().st_size / 1024:.1f} KB)")

        # Copy to dashboard
        dashboard_dir = Path(__file__).resolve().parent / "nexus-dashboard"
        if dashboard_dir.exists():
            shutil.copy2(output_dir / "nexus_data.json", dashboard_dir / "nexus_data.json")
            print("   ✅ Dashboard data synced")
    except Exception as e:
        print(f"   ⚠️  Merge: {e}")


# ── Main ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Nexus Generic Repository Analyzer")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--focus", default=None, help="Comma-separated focus areas (e.g. 'REST API,Database')")
    parser.add_argument("--dprs", type=int, default=10, help="Number of DPRs to generate (default: 10)")
    parser.add_argument("--output", default=None, help="Output directory (default: auto)")
    parser.add_argument("--clone-dir", default=None, help="Directory to clone into (default: auto)")
    parser.add_argument("--llm", default=None, choices=["gemini", "watsonx"], help="LLM provider (default: auto-detect)")
    parser.add_argument("--neo4j", action="store_true", help="Load results into Neo4j")
    args = parser.parse_args()

    print("=" * 60)
    print("  NEXUS - GENERIC REPOSITORY ANALYZER")
    print("=" * 60)
    llm = get_llm_provider(args.llm)
    print(f"  Repository: {args.repo_url}")
    print(f"  Focus: {args.focus or 'All architectural decisions'}")
    print(f"  DPRs: {args.dprs}")
    print(f"  LLM: {llm}")
    print("=" * 60)

    # Derive repo name
    repo_name = args.repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    # Directories
    base = Path(__file__).resolve().parent
    clone_dir = Path(args.clone_dir) if args.clone_dir else base / ".repos" / repo_name
    output_dir = Path(args.output) if args.output else base / "analyses" / repo_name / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Clone
    clone_repo(args.repo_url, clone_dir)

    # Step 2: Scan
    scan_data = scan_repo(clone_dir)

    # Step 3: Generate DPRs with LLM
    dprs, edges, decay_alerts = generate_dprs_with_gemini(
        llm, scan_data, args.repo_url, args.focus, args.dprs
    )

    # Step 4: Save Layer 1 output
    layer1 = build_layer1_output(dprs, edges, decay_alerts, args.repo_url)
    l1_path = output_dir / "nexus_layer1_dprs.json"
    with open(l1_path, "w", encoding="utf-8") as f:
        json.dump(layer1, f, indent=2, default=str)
    print(f"\n💾 Layer 1 saved: {l1_path} ({l1_path.stat().st_size / 1024:.1f} KB)")

    # Step 5: Run pipeline
    run_full_pipeline(output_dir)

    # Step 6: Optional Neo4j load
    if args.neo4j:
        try:
            from neo4j_loader import load_into_neo4j
            load_into_neo4j(output_dir / "nexus_layer1_dprs.json")
        except Exception as e:
            print(f"   ⚠️  Neo4j load failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"✅ ANALYSIS COMPLETE: {repo_name}")
    print(f"   LLM: {llm}")
    print(f"   DPRs: {len(dprs)}")
    print(f"   Edges: {len(edges)}")
    print(f"   Decay Alerts: {len(decay_alerts)}")
    print(f"   Output: {output_dir}")
    print(f"   Dashboard: http://localhost:8000 (restart api_server.py)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
