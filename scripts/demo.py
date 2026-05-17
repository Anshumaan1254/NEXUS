#!/usr/bin/env python3
"""
Nexus Demo Script for IBM Bob Hackathon
Runs a complete analysis and displays results
"""
import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nexus.models.config import AnalysisConfig
from nexus.core.scanner.repo_scanner import RepoScanner
from nexus.core.git.history_analyzer import HistoryAnalyzer
from nexus.services.llm_client import LLMClient
from nexus.core.graph.causal_graph import CausalGraphBuilder
from nexus.core.decay.decay_monitor import DecayMonitor


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_progress(step: str, progress: int):
    """Print progress bar."""
    bar_length = 50
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r{step}: [{bar}] {progress}%", end="", flush=True)
    if progress == 100:
        print()  # New line when complete


async def run_demo():
    """Run complete Nexus analysis demo."""
    
    print_header("NEXUS DECISION PROVENANCE ENGINE - DEMO")
    print("IBM Bob Hackathon 2026")
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Configuration
    config = AnalysisConfig(
        repository="https://github.com/psf/requests",
        analysis_window="2 years",
        priority_areas=["all"],
        min_dprs=5  # Small number for demo
    )
    
    print(f"📦 Repository: {config.repository}")
    print(f"⏰ Analysis Window: {config.analysis_window}")
    print(f"🎯 Min DPRs: {config.min_dprs}\n")
    
    start_time = time.time()
    
    # Phase 1: Repository Scan
    print_header("PHASE 1: Repository Scan")
    print_progress("Scanning repository", 0)
    
    scanner = RepoScanner()
    scan_result = await scanner.scan_repository(config.repository)
    
    print_progress("Scanning repository", 100)
    print(f"\n✅ Scanned {len(scan_result.files)} files")
    print(f"   Primary Language: {scan_result.primary_language}")
    print(f"   Framework: {scan_result.framework or 'None detected'}")
    print(f"   Design Comments: {len(scan_result.design_comments)}")
    
    # Phase 2: Git History Analysis
    print_header("PHASE 2: Git History Analysis")
    print_progress("Analyzing commits", 0)
    
    analyzer = HistoryAnalyzer()
    commits = await analyzer.analyze_history(config.repository, config)
    
    print_progress("Analyzing commits", 100)
    print(f"\n✅ Analyzed {len(commits)} commits")
    if commits:
        print(f"   Top reasoning score: {commits[0].reasoning_score:.2f}")
        print(f"   High-reasoning commits: {len([c for c in commits if c.reasoning_score > 0.5])}")
    
    # Phase 3: DPR Extraction
    print_header("PHASE 3: DPR Extraction")
    print("⚠️  Note: Using mock DPRs for demo (LLM API not configured)")
    
    # Create mock DPRs for demo
    from nexus.models.dpr import DPR
    dprs = []
    for i in range(config.min_dprs):
        dpr = DPR(
            dpr_id=f"DPR-{i+1:03d}",
            title=f"Decision {i+1}: {commits[i].message[:50] if i < len(commits) else 'Sample decision'}",
            component="Other",
            within_window=True,
            decision_date=commits[i].date.strftime('%Y-%m') if i < len(commits) else "2024-01",
            decision=f"Decision based on commit: {commits[i].hash if i < len(commits) else 'sample'}",
            rejected_alternatives=[],
            explicit_constraints=[],
            implicit_assumptions=["INFERRED: Sample assumption for demo"],
            intended_durability="medium-term",
            durability_reasoning="Demo reasoning",
            causal_dependencies=[],
            files_involved=commits[i].files_changed[:3] if i < len(commits) else [],
            commit_refs=[commits[i].hash if i < len(commits) else "sample"],
            involved_humans=[commits[i].author if i < len(commits) else "Demo Author"],
            assumption_decay_risk="medium",
            decay_risk_reasoning="Demo decay reasoning",
            blast_radius_estimate="medium",
            blast_radius_reasoning="Demo blast radius",
            active_workarounds=[]
        )
        dprs.append(dpr)
    
    print(f"✅ Extracted {len(dprs)} DPRs\n")
    
    # Display top 3 DPRs
    print("📋 Top 3 DPRs:")
    for i, dpr in enumerate(dprs[:3], 1):
        print(f"\n   {i}. {dpr.dpr_id}: {dpr.title}")
        print(f"      Component: {dpr.component}")
        print(f"      Blast Radius: {dpr.blast_radius_estimate}")
        print(f"      Decay Risk: {dpr.assumption_decay_risk}")
    
    # Phase 4: Causal Graph
    print_header("PHASE 4: Causal Graph Construction")
    
    # Generate temporal edges
    from nexus.models.output import CausalGraphEdge
    edges = []
    for i in range(min(20, len(dprs) - 1)):
        edge = CausalGraphEdge(
            from_dpr=dprs[i].dpr_id,
            to_dpr=dprs[i + 1].dpr_id if i + 1 < len(dprs) else dprs[0].dpr_id,
            relationship="temporal_precedes",
            explanation=f"{dprs[i].dpr_id} precedes {dprs[i + 1].dpr_id if i + 1 < len(dprs) else dprs[0].dpr_id}",
            within_window=True
        )
        edges.append(edge)
    
    graph_builder = CausalGraphBuilder()
    metrics = await graph_builder.build_graph(dprs, edges)
    
    print(f"✅ Built causal graph")
    print(f"   Nodes: {metrics['node_count']}")
    print(f"   Edges: {metrics['edge_count']}")
    print(f"   Density: {metrics['density']:.3f}")
    print(f"   Is DAG: {metrics['is_dag']}")
    
    # Phase 5: Decay Analysis
    print_header("PHASE 5: Assumption Decay Analysis")
    
    decay_monitor = DecayMonitor()
    decay_alerts = await decay_monitor.analyze_decay(dprs, commits)
    
    print(f"✅ Analyzed {len(dprs)} DPRs for decay")
    print(f"   Decay alerts: {len(decay_alerts)}")
    print(f"   Already decaying: {len([a for a in decay_alerts if a.already_decaying])}")
    
    # Summary
    elapsed = time.time() - start_time
    
    print_header("ANALYSIS COMPLETE")
    print(f"⏱️  Total Time: {elapsed:.1f} seconds")
    print(f"📊 Results:")
    print(f"   - Files Scanned: {len(scan_result.files)}")
    print(f"   - Commits Analyzed: {len(commits)}")
    print(f"   - DPRs Extracted: {len(dprs)}")
    print(f"   - Graph Edges: {len(edges)}")
    print(f"   - Decay Alerts: {len(decay_alerts)}")
    
    print("\n✨ Demo complete! Full analysis would use LLM for DPR extraction.")
    print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY for production use.\n")
    
    return {
        "scan_result": scan_result,
        "commits": commits,
        "dprs": dprs,
        "edges": edges,
        "decay_alerts": decay_alerts,
        "elapsed_time": elapsed
    }


if __name__ == "__main__":
    print("\n🚀 Starting Nexus Demo...\n")
    
    try:
        result = asyncio.run(run_demo())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
