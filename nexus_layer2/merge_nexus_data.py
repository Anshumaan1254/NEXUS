"""
Nexus - nexus_data.json Merger
Merges Bob Layer 1 output + enrichment data into a single nexus_data.json
that the React dashboard reads as its only data source.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
import networkx as nx

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_risk_scores(dprs, edges, decay_alerts):
    """Compute composite risk scores for each DPR."""
    G = nx.DiGraph()
    for d in dprs: G.add_node(d["dpr_id"])
    for e in edges: G.add_edge(e["from_dpr"], e["to_dpr"])
    
    scores = []
    for dpr in dprs:
        did = dpr["dpr_id"]
        downstream = len(nx.descendants(G, did)) if did in G else 0
        upstream = len(nx.ancestors(G, did)) if did in G else 0
        
        # Blast radius score
        br_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        br_score = br_map.get(dpr["blast_radius_estimate"], 0.5)
        
        # Decay risk score
        dr_map = {"high": 1.0, "medium": 0.5, "low": 0.25}
        dr_score = dr_map.get(dpr["assumption_decay_risk"], 0.5)
        
        # Active decay
        active_decay = any(a["dpr_id"] == did and a["already_decaying"] for a in decay_alerts)
        decay_bonus = 0.3 if active_decay else 0.0
        
        # Workaround pressure
        wa_score = min(len(dpr["active_workarounds"]) / 5.0, 1.0)
        
        # Connectivity score
        conn_score = min((downstream + upstream) / 10.0, 1.0)
        
        # Composite
        composite = round(
            0.3 * br_score + 0.25 * dr_score + 0.2 * conn_score + 0.15 * wa_score + 0.1 * decay_bonus,
            3
        ) * 100
        
        scores.append({
            "dpr_id": did,
            "title": dpr["title"],
            "component": dpr["component"],
            "composite_risk": round(composite, 1),
            "blast_radius_score": round(br_score * 100, 1),
            "decay_risk_score": round(dr_score * 100, 1),
            "connectivity_score": round(conn_score * 100, 1),
            "workaround_pressure": round(wa_score * 100, 1),
            "active_decay": active_decay,
            "downstream_count": downstream,
            "upstream_count": upstream,
        })
    
    return sorted(scores, key=lambda x: -x["composite_risk"])

def build_remediation_backlog(dprs, risk_scores, decay_alerts):
    """Generate prioritized remediation backlog."""
    backlog = []
    scores_dict = {s["dpr_id"]: s for s in risk_scores}
    
    for dpr in dprs:
        did = dpr["dpr_id"]
        score = scores_dict.get(did, {})
        if score.get("composite_risk", 0) < 40:
            continue
        
        active_alerts = [a for a in decay_alerts if a["dpr_id"] == did and a["already_decaying"]]
        
        priority = "P0" if score.get("composite_risk", 0) >= 70 else "P1" if score.get("composite_risk", 0) >= 55 else "P2"
        
        actions = []
        if active_alerts:
            actions.append(f"Address {len(active_alerts)} active decay alert(s)")
        if len(dpr["active_workarounds"]) >= 3:
            actions.append(f"Review {len(dpr['active_workarounds'])} workarounds for consolidation")
        if dpr["blast_radius_estimate"] == "critical":
            actions.append("Add blast radius monitoring and alerts")
        if dpr["assumption_decay_risk"] == "high":
            actions.append("Schedule quarterly assumption review")
        if not actions:
            actions.append("Monitor and reassess next cycle")
        
        backlog.append({
            "priority": priority,
            "dpr_id": did,
            "title": dpr["title"],
            "component": dpr["component"],
            "risk_score": score.get("composite_risk", 0),
            "actions": actions,
            "estimated_effort": "high" if priority == "P0" else "medium" if priority == "P1" else "low",
        })
    
    return sorted(backlog, key=lambda x: ({"P0":0,"P1":1,"P2":2}[x["priority"]], -x["risk_score"]))

def merge_nexus_data():
    """Merge all outputs into a single nexus_data.json."""
    print("="*60+"\nNEXUS DATA MERGER\n"+"="*60)
    
    base = Path(__file__).resolve().parent.parent / "postgres-analysis" / "output"
    
    # Load Layer 1
    l1 = load_json(base / "nexus_layer1_dprs.json")["nexus_layer1_output"]
    print(f"📂 Layer 1: {len(l1['dprs'])} DPRs, {len(l1['ctg_edges'])} edges, {len(l1['assumption_decay_prescan'])} alerts")
    
    # Load enrichments (optional)
    decay_report = {}
    cf_traces = {}
    knowledge = {}
    
    for name, var_name in [("decay_monitor_report.json","decay"),("counterfactual_traces.json","cf"),("knowledge_concentration.json","kc")]:
        p = base / name
        if p.exists():
            data = load_json(p)
            if var_name == "decay": decay_report = data
            elif var_name == "cf": cf_traces = data
            elif var_name == "kc": knowledge = data
            print(f"✅ Loaded {name}")
        else:
            print(f"⚠️  {name} not found, skipping")
    
    # Build risk scores
    risk_scores = build_risk_scores(l1["dprs"], l1["ctg_edges"], l1["assumption_decay_prescan"])
    print(f"📊 Computed risk scores for {len(risk_scores)} DPRs")
    
    # Build remediation backlog
    backlog = build_remediation_backlog(l1["dprs"], risk_scores, l1["assumption_decay_prescan"])
    print(f"📋 Generated {len(backlog)} remediation items")
    
    # Merge
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
        "counterfactual_traces": cf_traces.get("traces", []),
        "knowledge_concentration": knowledge,
        "decay_monitor": decay_report,
    }
    
    # Save
    out_path = base / "nexus_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(nexus_data, f, indent=2, default=str)
    
    print(f"\n💾 nexus_data.json saved to {out_path}")
    print(f"   Size: {out_path.stat().st_size / 1024:.1f} KB")
    print(f"   Keys: {', '.join(nexus_data.keys())}")
    print("✅ Merge complete")
    
    return nexus_data

def main():
    merge_nexus_data()

if __name__ == "__main__": main()
