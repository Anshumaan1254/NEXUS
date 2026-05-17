"""Deep functional audit — test every API endpoint."""
import urllib.request, json, sys
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8000"
errors = []

def test(method, path, body=None, expect_status=200):
    url = BASE + path
    try:
        if body:
            data = json.dumps(body).encode()
            req = urllib.request.Request(url, data=data, method=method,
                                        headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(url, method=method)
        r = urllib.request.urlopen(req, timeout=10)
        result = json.loads(r.read().decode())
        print(f"  OK    {method:4s} {path}")
        return result
    except urllib.error.HTTPError as e:
        if e.code == expect_status:
            print(f"  OK    {method:4s} {path} (expected {e.code})")
            return None
        print(f"  FAIL  {method:4s} {path} -> HTTP {e.code}")
        errors.append(f"{method} {path}: HTTP {e.code}")
        return None
    except Exception as e:
        print(f"  FAIL  {method:4s} {path} -> {e}")
        errors.append(f"{method} {path}: {e}")
        return None

print("=" * 60)
print("  API ENDPOINT AUDIT")
print("=" * 60)

# Core endpoints
test("GET", "/api/health")
data = test("GET", "/api/data")
if data:
    assert "dprs" in data, "Missing dprs in /api/data"
    assert "ctg_edges" in data, "Missing ctg_edges in /api/data"

test("GET", "/api/stats")
test("GET", "/api/dprs")
test("GET", "/api/dprs?component=Authentication")
test("GET", "/api/dprs/DPR-001")
test("GET", "/api/dprs/NONEXISTENT", expect_status=404)
test("GET", "/api/graph")
test("GET", "/api/risks")
test("GET", "/api/decay")
test("GET", "/api/decay/monitor")
test("GET", "/api/counterfactual")
test("GET", "/api/knowledge")
test("GET", "/api/backlog")
test("GET", "/api/backlog?priority=P0")
test("GET", "/api/search?q=database")
test("GET", "/api/repos")

# POST endpoints
test("POST", "/api/query", {"question": "What about authentication?"})

# Neo4j
test("GET", "/api/neo4j/stats")
test("POST", "/api/neo4j/query", {"query": "MATCH (d:DPR) RETURN d.dpr_id, d.title LIMIT 3"})

# LLM
test("GET", "/api/llm/status")

# Dashboard
try:
    r = urllib.request.urlopen(BASE + "/", timeout=5)
    html = r.read().decode()
    assert "NEXUS" in html, "Dashboard HTML missing NEXUS"
    print(f"  OK    GET  / (dashboard, {len(html)} bytes)")
except Exception as e:
    print(f"  FAIL  GET  / -> {e}")
    errors.append(f"Dashboard: {e}")

# Swagger
try:
    r = urllib.request.urlopen(BASE + "/docs", timeout=5)
    print(f"  OK    GET  /docs (swagger)")
except Exception as e:
    print(f"  FAIL  GET  /docs -> {e}")
    errors.append(f"Swagger: {e}")

print(f"\n{'=' * 60}")
if errors:
    print(f"  ERRORS: {len(errors)}")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ALL ENDPOINTS PASSED")
print("=" * 60)
