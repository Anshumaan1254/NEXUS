"""Audit all project Python files for syntax errors and import issues."""
import ast, sys, os
sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))

files = [
    "api_server.py",
    "repo_analyzer.py",
    "nexus_layer2/llm_provider.py",
    "nexus_layer2/neo4j_loader.py",
    "nexus_layer2/decay_monitor.py",
    "nexus_layer2/counterfactual_sim.py",
    "nexus_layer2/knowledge_concentration.py",
    "nexus_layer2/merge_nexus_data.py",
    "nexus_layer2/risk_report_pdf.py",
    "nexus_layer2/submission_export.py",
    "nexus_layer2/models.py",
    "nexus_layer2/cypher_queries.py",
    "nexus_layer2/graph_builder.py",
    "nexus_layer2/weaviate_ingest.py",
    "nexus_layer2/nl_query.py",
]

print("=" * 60)
print("  NEXUS PROJECT AUDIT")
print("=" * 60)

errors = []
for f in files:
    path = os.path.join(ROOT, f.replace("/", os.sep))
    if not os.path.exists(path):
        print(f"  SKIP  {f} (not found)")
        continue
    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        ast.parse(source)
        print(f"  OK    {f}")
    except SyntaxError as e:
        print(f"  ERROR {f}: {e}")
        errors.append((f, str(e)))

# Check imports
print("\n--- Import Checks ---")
import_tests = [
    ("fastapi", "FastAPI backend"),
    ("uvicorn", "ASGI server"),
    ("pydantic", "Data validation"),
    ("networkx", "Graph analysis"),
    ("reportlab", "PDF generation"),
    ("neo4j", "Neo4j driver"),
]

for mod, desc in import_tests:
    try:
        __import__(mod)
        print(f"  OK    {mod} ({desc})")
    except ImportError:
        print(f"  MISS  {mod} ({desc})")
        errors.append((mod, f"Missing dependency: {desc}"))

# Check data files
print("\n--- Data Files ---")
data_files = [
    "postgres-analysis/output/nexus_layer1_dprs.json",
    "postgres-analysis/output/nexus_data.json",
    "nexus-dashboard/index.html",
    "nexus-dashboard/nexus_data.json",
    "analyses/WordPress/output/nexus_data.json",
]
for f in data_files:
    path = os.path.join(ROOT, f.replace("/", os.sep))
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  OK    {f} ({size/1024:.1f} KB)")
    else:
        print(f"  MISS  {f}")

# Check API endpoints
print("\n--- API Server Test ---")
try:
    import urllib.request
    r = urllib.request.urlopen("http://localhost:8000/api/health", timeout=3)
    data = r.read().decode()
    print(f"  OK    /api/health -> {data[:80]}")
except Exception as e:
    print(f"  FAIL  API not reachable: {e}")

# Check Neo4j
print("\n--- Neo4j Test ---")
try:
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver("bolt://localhost:7687")
    driver.verify_connectivity()
    with driver.session() as s:
        nodes = s.run("MATCH (n) RETURN count(n) as c").single()["c"]
        rels = s.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
    print(f"  OK    Neo4j connected: {nodes} nodes, {rels} relationships")
    driver.close()
except Exception as e:
    print(f"  FAIL  Neo4j: {e}")

print(f"\n{'=' * 60}")
if errors:
    print(f"  ERRORS FOUND: {len(errors)}")
    for name, err in errors:
        print(f"    - {name}: {err}")
else:
    print("  ALL CHECKS PASSED")
print("=" * 60)
