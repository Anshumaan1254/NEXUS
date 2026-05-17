"""
Nexus - Neo4j Graph Loader
Loads DPRs and CTG edges from nexus_layer1_dprs.json into Neo4j.
Works with any repository's analysis output.

Usage:
  py nexus_layer2/neo4j_loader.py postgres-analysis/output/nexus_layer1_dprs.json
  py nexus_layer2/neo4j_loader.py analyses/WordPress/output/nexus_layer1_dprs.json

Environment:
  NEO4J_URI      (default: bolt://localhost:7687)
  NEO4J_USER     (default: neo4j)
  NEO4J_PASSWORD (default: nexus2024)
"""
import json, sys, os, argparse
from pathlib import Path

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass


def get_neo4j_driver():
    """Connect to Neo4j."""
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")

    # Support auth=none (empty password)
    if password:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    else:
        driver = GraphDatabase.driver(uri)
    # Test connection
    driver.verify_connectivity()
    return driver


def clear_graph(driver):
    """Clear all nodes and relationships."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("   🗑️  Cleared existing graph")


def create_constraints(driver):
    """Create uniqueness constraints."""
    with driver.session() as session:
        try:
            session.run(
                "CREATE CONSTRAINT dpr_id_unique IF NOT EXISTS "
                "FOR (d:DPR) REQUIRE d.dpr_id IS UNIQUE"
            )
        except Exception:
            pass  # Constraint might already exist
        try:
            session.run(
                "CREATE CONSTRAINT component_name_unique IF NOT EXISTS "
                "FOR (c:Component) REQUIRE c.name IS UNIQUE"
            )
        except Exception:
            pass
    print("   🔑 Constraints created")


def load_dprs(driver, dprs, repo_url):
    """Load DPR nodes into Neo4j."""
    with driver.session() as session:
        # Create Repository node
        session.run(
            "MERGE (r:Repository {url: $url}) SET r.name = $name",
            url=repo_url,
            name=repo_url.rstrip("/").split("/")[-1],
        )

        for dpr in dprs:
            # Create Component node
            component = dpr.get("component", "Unknown")
            session.run(
                "MERGE (c:Component {name: $name})",
                name=component,
            )

            # Create DPR node
            session.run("""
                MERGE (d:DPR {dpr_id: $dpr_id})
                SET d.title = $title,
                    d.component = $component,
                    d.decision = $decision,
                    d.decision_date = $decision_date,
                    d.blast_radius = $blast_radius,
                    d.decay_risk = $decay_risk,
                    d.durability = $durability,
                    d.workaround_count = $workaround_count,
                    d.assumption_count = $assumption_count
            """,
                dpr_id=dpr["dpr_id"],
                title=dpr.get("title", ""),
                component=component,
                decision=dpr.get("decision", ""),
                decision_date=dpr.get("decision_date", ""),
                blast_radius=dpr.get("blast_radius_estimate", ""),
                decay_risk=dpr.get("assumption_decay_risk", ""),
                durability=dpr.get("intended_durability", ""),
                workaround_count=len(dpr.get("active_workarounds", [])),
                assumption_count=len(dpr.get("implicit_assumptions", [])),
            )

            # Link DPR → Component
            session.run("""
                MATCH (d:DPR {dpr_id: $dpr_id}), (c:Component {name: $component})
                MERGE (d)-[:BELONGS_TO]->(c)
            """, dpr_id=dpr["dpr_id"], component=component)

            # Link DPR → Repository
            session.run("""
                MATCH (d:DPR {dpr_id: $dpr_id}), (r:Repository {url: $url})
                MERGE (d)-[:ANALYZED_FROM]->(r)
            """, dpr_id=dpr["dpr_id"], url=repo_url)

            # Create Assumption nodes
            for i, assumption in enumerate(dpr.get("implicit_assumptions", [])):
                a_id = f"{dpr['dpr_id']}_A{i+1}"
                session.run("""
                    MERGE (a:Assumption {id: $id})
                    SET a.text = $text, a.dpr_id = $dpr_id
                """, id=a_id, text=assumption, dpr_id=dpr["dpr_id"])
                session.run("""
                    MATCH (d:DPR {dpr_id: $dpr_id}), (a:Assumption {id: $id})
                    MERGE (d)-[:HAS_ASSUMPTION]->(a)
                """, dpr_id=dpr["dpr_id"], id=a_id)

            # Create Workaround nodes
            for i, wa in enumerate(dpr.get("active_workarounds", [])):
                w_id = f"{dpr['dpr_id']}_W{i+1}"
                session.run("""
                    MERGE (w:Workaround {id: $id})
                    SET w.text = $text, w.dpr_id = $dpr_id
                """, id=w_id, text=wa, dpr_id=dpr["dpr_id"])
                session.run("""
                    MATCH (d:DPR {dpr_id: $dpr_id}), (w:Workaround {id: $id})
                    MERGE (d)-[:HAS_WORKAROUND]->(w)
                """, dpr_id=dpr["dpr_id"], id=w_id)

    print(f"   📦 Loaded {len(dprs)} DPR nodes")


def load_edges(driver, edges):
    """Load CTG edges as relationships."""
    edge_count = 0
    with driver.session() as session:
        for edge in edges:
            rel_type = edge.get("relationship", "RELATED_TO").upper()
            # Neo4j relationship names can't have special characters
            rel_type = rel_type.replace("-", "_").replace(" ", "_")

            try:
                session.run(f"""
                    MATCH (a:DPR {{dpr_id: $from_id}}), (b:DPR {{dpr_id: $to_id}})
                    MERGE (a)-[r:{rel_type}]->(b)
                    SET r.explanation = $explanation
                """,
                    from_id=edge["from_dpr"],
                    to_id=edge["to_dpr"],
                    explanation=edge.get("explanation", ""),
                )
                edge_count += 1
            except Exception as e:
                print(f"   ⚠️  Edge {edge['from_dpr']}→{edge['to_dpr']}: {e}")

    print(f"   🔗 Loaded {edge_count} CTG edges")


def load_decay_alerts(driver, alerts):
    """Load decay alerts as DecayAlert nodes."""
    with driver.session() as session:
        for alert in alerts:
            session.run("""
                MERGE (da:DecayAlert {dpr_id: $dpr_id, assumption: $assumption})
                SET da.already_decaying = $already_decaying,
                    da.evidence = $evidence,
                    da.earliest_signal = $earliest_signal
            """,
                dpr_id=alert["dpr_id"],
                assumption=alert.get("assumption", ""),
                already_decaying=alert.get("already_decaying", False),
                evidence=alert.get("decay_evidence", ""),
                earliest_signal=alert.get("earliest_signal_date", ""),
            )
            session.run("""
                MATCH (d:DPR {dpr_id: $dpr_id}), (da:DecayAlert {dpr_id: $dpr_id})
                MERGE (d)-[:HAS_DECAY_ALERT]->(da)
            """, dpr_id=alert["dpr_id"])

    print(f"   ⚠️  Loaded {len(alerts)} decay alerts")


def get_graph_stats(driver):
    """Return graph statistics."""
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) as c").single()["c"]
        dprs = session.run("MATCH (d:DPR) RETURN count(d) as c").single()["c"]
        comps = session.run("MATCH (c:Component) RETURN count(c) as c").single()["c"]
        return {"nodes": nodes, "relationships": rels, "dprs": dprs, "components": comps}


def load_into_neo4j(layer1_path, clear=True):
    """Load a Layer 1 JSON file into Neo4j."""
    layer1_path = Path(layer1_path)
    print(f"\n🔷 Loading into Neo4j: {layer1_path.name}")

    # Load data
    with open(layer1_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    l1 = data.get("nexus_layer1_output", data)
    dprs = l1.get("dprs", [])
    edges = l1.get("ctg_edges", [])
    alerts = l1.get("assumption_decay_prescan", [])
    repo_url = l1.get("repository", "unknown")

    # Connect
    driver = get_neo4j_driver()
    print(f"   ✅ Connected to Neo4j")

    try:
        if clear:
            clear_graph(driver)
        create_constraints(driver)
        load_dprs(driver, dprs, repo_url)
        load_edges(driver, edges)
        if alerts:
            load_decay_alerts(driver, alerts)

        stats = get_graph_stats(driver)
        print(f"\n   📊 Graph Stats:")
        print(f"      Nodes: {stats['nodes']}")
        print(f"      Relationships: {stats['relationships']}")
        print(f"      DPRs: {stats['dprs']}")
        print(f"      Components: {stats['components']}")
        print(f"   ✅ Neo4j load complete!")

        return stats
    finally:
        driver.close()


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Nexus data into Neo4j")
    parser.add_argument("input", help="Path to nexus_layer1_dprs.json")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing graph")
    args = parser.parse_args()

    print("=" * 60)
    print("  NEXUS → NEO4J LOADER")
    print("=" * 60)

    load_into_neo4j(args.input, clear=not args.no_clear)
