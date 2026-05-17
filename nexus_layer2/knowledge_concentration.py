"""
Nexus Layer 5 - Knowledge Concentration Report
Maps authors to DPRs and flags single-points-of-failure.
Simulates git-fame/git-blame analysis.
"""
import json, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass

def load_data(p=None):
    if p is None: p = Path(__file__).resolve().parent.parent/"postgres-analysis"/"output"/"nexus_layer1_dprs.json"
    else: p = Path(p)
    with open(p,"r",encoding="utf-8") as f: return json.load(f)["nexus_layer1_output"]

def compute_knowledge_concentration(output):
    """Compute knowledge concentration per DPR and per author."""
    print("="*60+"\nNEXUS LAYER 5 - KNOWLEDGE CONCENTRATION REPORT\n"+"="*60)
    
    dprs = output["dprs"]
    author_dprs = defaultdict(list)       # author -> [dpr_ids]
    author_files = defaultdict(set)       # author -> {files}
    dpr_authors = {}                      # dpr_id -> {author: percentage}
    component_authors = defaultdict(lambda: defaultdict(int))  # component -> {author: count}
    spof_alerts = []
    
    for dpr in dprs:
        dpr_id = dpr["dpr_id"]
        humans = dpr.get("involved_humans", [])
        files = dpr.get("files_involved", [])
        component = dpr["component"]
        
        if not humans:
            humans = ["Unknown"]
        
        # Distribute ownership — first-listed gets more weight
        total_weight = sum(range(len(humans), 0, -1))  # e.g. [3,2,1] for 3 authors
        author_pcts = {}
        for i, author in enumerate(humans):
            weight = len(humans) - i
            pct = round(100.0 * weight / total_weight, 1)
            author_pcts[author] = pct
            author_dprs[author].append(dpr_id)
            for f in files:
                author_files[author].add(f)
            component_authors[component][author] += 1
        
        dpr_authors[dpr_id] = author_pcts
        
        # Flag SPOF: anyone >60% on a critical-path DPR
        for author, pct in author_pcts.items():
            if pct >= 60.0 and dpr["blast_radius_estimate"] in ("critical", "high"):
                spof_alerts.append({
                    "author": author,
                    "dpr_id": dpr_id,
                    "dpr_title": dpr["title"],
                    "component": component,
                    "ownership_pct": pct,
                    "blast_radius": dpr["blast_radius_estimate"],
                    "risk": "SPOF" if pct >= 80 else "HIGH_CONCENTRATION",
                    "recommendation": (
                        f"Engineer '{author}' holds {pct}% of causal knowledge about "
                        f"{dpr['title']} ({component}). "
                        f"{'Their departure is a critical SPOF.' if pct >= 80 else 'Knowledge transfer recommended.'}"
                    ),
                })
    
    # Build author summary
    author_summary = []
    for author in sorted(author_dprs.keys()):
        dpr_list = author_dprs[author]
        files_count = len(author_files[author])
        components = set()
        for did in dpr_list:
            for d in dprs:
                if d["dpr_id"] == did:
                    components.add(d["component"])
        
        author_summary.append({
            "author": author,
            "total_dprs": len(dpr_list),
            "dpr_ids": sorted(dpr_list),
            "files_touched": files_count,
            "components": sorted(components),
            "is_spof": any(a["author"] == author and a["risk"] == "SPOF" for a in spof_alerts),
        })
    
    # Component concentration
    component_summary = {}
    for comp, authors in component_authors.items():
        total = sum(authors.values())
        comp_authors = [
            {"author": a, "dpr_count": c, "percentage": round(100.0*c/total, 1)}
            for a, c in sorted(authors.items(), key=lambda x: -x[1])
        ]
        component_summary[comp] = {
            "total_dprs": total,
            "authors": comp_authors,
            "concentration_risk": "high" if comp_authors[0]["percentage"] >= 60 else "medium" if comp_authors[0]["percentage"] >= 40 else "low",
        }
    
    # Print report
    print(f"\n📊 Analyzed {len(dprs)} DPRs across {len(component_authors)} components")
    print(f"   Found {len(author_dprs)} unique contributors")
    
    print(f"\n👥 AUTHOR SUMMARY:")
    for a in sorted(author_summary, key=lambda x: -x["total_dprs"]):
        spof = " ⚠️  SPOF" if a["is_spof"] else ""
        print(f"   {a['author']}: {a['total_dprs']} DPRs, {a['files_touched']} files, components: {', '.join(a['components'])}{spof}")
    
    print(f"\n🏗️  COMPONENT CONCENTRATION:")
    for comp, info in sorted(component_summary.items()):
        risk_icon = {"high":"🔴","medium":"🟡","low":"🟢"}[info["concentration_risk"]]
        top = info["authors"][0]
        print(f"   {risk_icon} {comp}: {top['author']} ({top['percentage']}%) — {info['concentration_risk']} risk")
    
    if spof_alerts:
        print(f"\n🚨 SPOF ALERTS ({len(spof_alerts)}):")
        for alert in spof_alerts:
            print(f"   ⚠️  {alert['author']} → {alert['dpr_id']}: {alert['dpr_title']} ({alert['ownership_pct']}%)")
            print(f"      {alert['recommendation']}")
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": output["repository"],
        "total_authors": len(author_dprs),
        "total_dprs": len(dprs),
        "author_summary": author_summary,
        "dpr_ownership": {did: auths for did, auths in dpr_authors.items()},
        "component_concentration": component_summary,
        "spof_alerts": spof_alerts,
    }
    
    print(f"\n{'='*60}\n✅ Knowledge concentration analysis complete")
    return result

def main():
    out = load_data()
    result = compute_knowledge_concentration(out)
    op = Path(__file__).resolve().parent.parent/"postgres-analysis"/"output"/"knowledge_concentration.json"
    with open(op,"w",encoding="utf-8") as f: json.dump(result,f,indent=2,default=str)
    print(f"💾 Saved to {op}")

if __name__=="__main__": main()
