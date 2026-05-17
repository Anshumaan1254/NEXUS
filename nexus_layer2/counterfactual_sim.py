"""
Nexus Layer 4 - Counterfactual Simulation Engine
Traces what would change if key decisions had been made differently.
Uses NetworkX for graph traversal of downstream effects.
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timezone
import networkx as nx

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

SCENARIOS = [
    {"scenario_id":"CF-001","target_dpr":"DPR-001","question":"What if PostgreSQL used 16KB pages instead of 8KB?","alternative":"Use 16KB fixed page size","reasoning":"Modern NVMe SSDs use 16-32KB internal pages. 16KB would reduce TOAST usage and improve I/O efficiency."},
    {"scenario_id":"CF-002","target_dpr":"DPR-003","question":"What if PostgreSQL used undo logs instead of in-heap tuple versioning?","alternative":"Use undo tablespace for old row versions","reasoning":"Undo-based MVCC eliminates table bloat, removes need for aggressive vacuum, prevents XID wraparound."},
    {"scenario_id":"CF-003","target_dpr":"DPR-004","question":"What if PostgreSQL used 64-bit transaction IDs?","alternative":"Use 64-bit XIDs eliminating wraparound","reasoning":"64-bit XIDs never wrap around, eliminating vacuum freeze and forced shutdown risk."},
    {"scenario_id":"CF-004","target_dpr":"DPR-009","question":"What if PostgreSQL adopted multi-threaded architecture?","alternative":"Thread-per-connection with shared address space","reasoning":"Threading reduces memory per connection, eliminates need for external poolers like pgBouncer."},
    {"scenario_id":"CF-005","target_dpr":"DPR-007","question":"What if PostgreSQL used shadow paging instead of WAL?","alternative":"Copy-on-write shadow paging for crash recovery","reasoning":"Shadow paging eliminates WAL writes but complicates streaming replication."},
]

def load_data(p=None):
    if p is None: p = Path(__file__).resolve().parent.parent/"postgres-analysis"/"output"/"nexus_layer1_dprs.json"
    else: p = Path(p)
    with open(p,"r",encoding="utf-8") as f: return json.load(f)["nexus_layer1_output"]

def build_graph(out):
    G = nx.DiGraph()
    for d in out["dprs"]:
        G.add_node(d["dpr_id"],title=d["title"],component=d["component"],decision=d["decision"],
                    blast_radius_estimate=d["blast_radius_estimate"],assumption_decay_risk=d["assumption_decay_risk"])
    for e in out["ctg_edges"]:
        G.add_edge(e["from_dpr"],e["to_dpr"],relationship=e["relationship"],explanation=e["explanation"])
    return G

def trace(G, sc, dprs):
    tid = sc["target_dpr"]
    if tid not in G: return None
    downstream = sorted(nx.descendants(G, tid))
    impacts = []
    for did in downstream:
        if did not in dprs: continue
        d = dprs[did]
        try:
            sp = nx.shortest_path(G, tid, did)
            rel = G.edges[sp[0],sp[1]]["relationship"]
            dist = len(sp)-1
        except: rel,dist = "unknown",0
        impacts.append({"dpr_id":did,"title":d["title"],"component":d["component"],
                        "relationship":rel,"distance":dist,"blast_radius":d["blast_radius_estimate"],
                        "would_change":f"Change to '{sc['alternative'][:50]}...' propagates via '{rel}' to {d['title']}."})
    crit = sum(1 for i in impacts if i["blast_radius"]=="critical")
    comps = sorted(set(dprs[d]["component"] for d in downstream if d in dprs))
    risk = "extreme" if crit>=2 or len(impacts)>=5 else "high" if crit>=1 else "medium" if len(impacts)>=2 else "low"
    return {"scenario_id":sc["scenario_id"],"target_dpr":tid,"target_title":dprs.get(tid,{}).get("title",""),
            "question":sc["question"],"original_decision":dprs.get(tid,{}).get("decision",""),
            "alternative":sc["alternative"],"reasoning":sc["reasoning"],
            "affected_count":len(downstream),"affected_components":comps,"impacts":impacts,
            "risk":{"level":risk,"critical":crit,"total":len(impacts)}}

def main():
    print("="*60+"\nNEXUS LAYER 4 - COUNTERFACTUAL SIMULATION ENGINE\n"+"="*60)
    out = load_data()
    G = build_graph(out)
    dprs = {d["dpr_id"]:d for d in out["dprs"]}
    print(f"\nLoaded {len(out['dprs'])} DPRs, {len(out['ctg_edges'])} edges")
    traces = []
    for sc in SCENARIOS:
        t = trace(G, sc, dprs)
        if t:
            traces.append(t)
            icon = {"extreme":"🔴","high":"🟠","medium":"🟡","low":"🟢"}[t["risk"]["level"]]
            print(f"\n{icon} {sc['scenario_id']}: {sc['question']}")
            print(f"   Risk: {t['risk']['level'].upper()} | Affected: {t['affected_count']} DPRs | Components: {', '.join(t['affected_components'])}")
    result = {"timestamp":datetime.now(timezone.utc).isoformat(),"repository":out["repository"],"traces":traces}
    op = Path(__file__).resolve().parent.parent/"postgres-analysis"/"output"/"counterfactual_traces.json"
    with open(op,"w",encoding="utf-8") as f: json.dump(result,f,indent=2,default=str)
    print(f"\n💾 Saved to {op}\n✅ Done")

if __name__=="__main__": main()
