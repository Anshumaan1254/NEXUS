"""
Nexus Layer 3 - Assumption Decay Monitor
Monitors DPR assumptions for decay signals using NetworkX blast radius computation.
Designed to run nightly — re-checks each assumption and computes downstream impact.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

import networkx as nx

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_layer1_data(json_path=None):
    """Load Layer 1 DPR data."""
    if json_path is None:
        script_dir = Path(__file__).resolve().parent
        json_path = script_dir.parent / "postgres-analysis" / "output" / "nexus_layer1_dprs.json"
    else:
        json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Layer 1 output not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output = data["nexus_layer1_output"]
    return output


def build_ctg_graph(output):
    """Build a NetworkX directed graph from CTG edges."""
    G = nx.DiGraph()

    # Add DPR nodes
    for dpr in output["dprs"]:
        G.add_node(
            dpr["dpr_id"],
            title=dpr["title"],
            component=dpr["component"],
            blast_radius_estimate=dpr["blast_radius_estimate"],
            assumption_decay_risk=dpr["assumption_decay_risk"],
            implicit_assumptions=dpr["implicit_assumptions"],
            active_workarounds=dpr["active_workarounds"],
        )

    # Add edges
    for edge in output["ctg_edges"]:
        G.add_edge(
            edge["from_dpr"],
            edge["to_dpr"],
            relationship=edge["relationship"],
            explanation=edge["explanation"],
        )

    return G


def compute_blast_radius(G, dpr_id):
    """
    Compute blast radius for a DPR: count all downstream nodes
    reachable via directed edges.
    """
    try:
        downstream = nx.descendants(G, dpr_id)
        return {
            "downstream_count": len(downstream),
            "downstream_dprs": sorted(list(downstream)),
            "total_graph_nodes": len(G.nodes),
            "impact_percentage": round(100.0 * len(downstream) / max(len(G.nodes) - 1, 1), 1),
        }
    except nx.NetworkXError:
        return {
            "downstream_count": 0,
            "downstream_dprs": [],
            "total_graph_nodes": len(G.nodes),
            "impact_percentage": 0.0,
        }


def check_assumption_decay(dpr, existing_alerts):
    """
    Check if a DPR's assumptions show decay signals.
    Uses existing decay alerts + heuristic rules.
    Returns decay status for each assumption.
    """
    results = []
    dpr_id = dpr["dpr_id"]

    # Check existing alerts for this DPR
    dpr_alerts = [a for a in existing_alerts if a["dpr_id"] == dpr_id]
    alerted_assumptions = {a["assumption"] for a in dpr_alerts}

    for assumption in dpr["implicit_assumptions"]:
        status = {
            "assumption": assumption,
            "holds": True,
            "confidence": 0.8,
            "reason": "No decay signals detected in current monitoring cycle",
            "severity": "stable",
        }

        # Check if this assumption matches an existing decay alert
        for alert in dpr_alerts:
            if _assumption_matches(assumption, alert["assumption"]):
                status["holds"] = not alert["already_decaying"]
                status["confidence"] = 0.3 if alert["already_decaying"] else 0.6
                status["reason"] = alert["decay_evidence"]
                status["severity"] = "critical" if alert["already_decaying"] else "warning"
                break

        # Heuristic: high decay risk DPRs with many workarounds are likely decaying
        if (
            status["holds"]
            and dpr["assumption_decay_risk"] == "high"
            and len(dpr["active_workarounds"]) >= 3
        ):
            status["confidence"] = 0.5
            status["reason"] = (
                f"High decay risk with {len(dpr['active_workarounds'])} active workarounds "
                f"suggests assumption pressure. Workarounds: {', '.join(dpr['active_workarounds'][:3])}"
            )
            status["severity"] = "warning"

        results.append(status)

    return results


def _assumption_matches(implicit_assumption, alert_assumption):
    """Check if an implicit assumption text matches an alert assumption."""
    # Simple keyword overlap check
    impl_words = set(implicit_assumption.lower().split())
    alert_words = set(alert_assumption.lower().split())
    overlap = impl_words & alert_words
    # If more than 30% of alert words appear in assumption, consider it a match
    if len(alert_words) > 0 and len(overlap) / len(alert_words) > 0.3:
        return True
    return False


def run_decay_monitor(json_path=None):
    """
    Run the full decay monitoring cycle.
    Returns a structured report.
    """
    print("=" * 60)
    print("NEXUS LAYER 3 - ASSUMPTION DECAY MONITOR")
    print("=" * 60)

    # Load data
    output = load_layer1_data(json_path)
    print(f"\n📂 Loaded {len(output['dprs'])} DPRs")
    print(f"   {len(output['assumption_decay_prescan'])} existing decay alerts")
    print(f"   {len(output['ctg_edges'])} CTG edges")

    # Build graph
    G = build_ctg_graph(output)
    print(f"\n🔗 Built CTG graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Monitor each DPR
    report = {
        "monitor_run_timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": output["repository"],
        "total_dprs_monitored": len(output["dprs"]),
        "dpr_reports": [],
        "summary": {},
    }

    critical_count = 0
    warning_count = 0
    stable_count = 0

    for dpr in output["dprs"]:
        dpr_id = dpr["dpr_id"]

        # Compute blast radius
        blast = compute_blast_radius(G, dpr_id)

        # Check assumptions
        assumption_checks = check_assumption_decay(
            dpr, output["assumption_decay_prescan"]
        )

        # Determine overall DPR status
        severities = [a["severity"] for a in assumption_checks]
        if "critical" in severities:
            overall_status = "critical"
            critical_count += 1
        elif "warning" in severities:
            overall_status = "warning"
            warning_count += 1
        else:
            overall_status = "stable"
            stable_count += 1

        dpr_report = {
            "dpr_id": dpr_id,
            "title": dpr["title"],
            "component": dpr["component"],
            "overall_status": overall_status,
            "blast_radius": blast,
            "assumption_checks": assumption_checks,
            "active_workarounds": dpr["active_workarounds"],
            "recommendation": _generate_recommendation(dpr, blast, assumption_checks),
        }

        report["dpr_reports"].append(dpr_report)

        # Print status
        status_icon = {"critical": "🔴", "warning": "🟡", "stable": "🟢"}[overall_status]
        print(f"\n{status_icon} {dpr_id}: {dpr['title']}")
        print(f"   Status: {overall_status} | Blast radius: {blast['downstream_count']} downstream DPRs ({blast['impact_percentage']}%)")

        for check in assumption_checks:
            if check["severity"] != "stable":
                print(f"   ⚠️  {check['assumption'][:80]}...")
                print(f"      → {check['reason'][:100]}...")

    # Summary
    report["summary"] = {
        "critical": critical_count,
        "warning": warning_count,
        "stable": stable_count,
        "most_impactful_dprs": _get_most_impactful(report["dpr_reports"]),
    }

    print(f"\n{'=' * 60}")
    print(f"📊 MONITORING SUMMARY:")
    print(f"   🔴 Critical: {critical_count}")
    print(f"   🟡 Warning:  {warning_count}")
    print(f"   🟢 Stable:   {stable_count}")
    print(f"{'=' * 60}")

    return report


def _generate_recommendation(dpr, blast, assumption_checks):
    """Generate an actionable recommendation for a DPR."""
    severities = [a["severity"] for a in assumption_checks]

    if "critical" in severities and blast["downstream_count"] >= 3:
        return (
            f"URGENT: {dpr['title']} has decaying assumptions with {blast['downstream_count']} "
            f"downstream dependencies. Schedule immediate architectural review. "
            f"Consider: {', '.join(dpr['active_workarounds'][:2]) if dpr['active_workarounds'] else 'No existing workarounds'}."
        )
    elif "critical" in severities:
        return (
            f"HIGH PRIORITY: {dpr['title']} shows assumption decay. "
            f"Review and document current state. Monitor downstream effects."
        )
    elif "warning" in severities:
        return (
            f"MONITOR: {dpr['title']} shows early warning signs. "
            f"Track metrics and prepare contingency plan."
        )
    else:
        return f"STABLE: {dpr['title']} assumptions appear to hold. Continue routine monitoring."


def _get_most_impactful(dpr_reports):
    """Get top 3 most impactful DPRs by blast radius."""
    sorted_dprs = sorted(
        dpr_reports,
        key=lambda x: x["blast_radius"]["downstream_count"],
        reverse=True,
    )
    return [
        {
            "dpr_id": d["dpr_id"],
            "title": d["title"],
            "downstream_count": d["blast_radius"]["downstream_count"],
            "status": d["overall_status"],
        }
        for d in sorted_dprs[:3]
    ]


def main():
    """Run decay monitor and save report."""
    report = run_decay_monitor()

    # Save report
    output_path = Path(__file__).resolve().parent.parent / "postgres-analysis" / "output" / "decay_monitor_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n💾 Report saved to: {output_path}")
    print("✅ Decay monitoring cycle complete")


if __name__ == "__main__":
    main()
