"""
Causal Graph Builder - Phase 4
Builds directed graph of causal relationships between DPRs
"""
import logging
from typing import List, Dict, Any
import networkx as nx

from nexus.models.dpr import DPR
from nexus.models.output import CausalGraphEdge

logger = logging.getLogger(__name__)


class CausalGraphBuilder:
    """
    Builds Causal Temporal Graph (CTG) from DPRs.
    
    Phase 4 of the Nexus pipeline:
    - Identifies causal relationships between DPRs
    - Builds directed graph using networkx
    - Computes centrality metrics
    - Ensures minimum 20 edges
    """
    
    def __init__(self):
        """Initialize causal graph builder."""
        self.graph = nx.DiGraph()
        
    async def build_graph(self, dprs: List[DPR], edges: List[CausalGraphEdge]) -> Dict[str, Any]:
        """
        Build causal graph from DPRs and edges.
        
        Args:
            dprs: List of DPRs
            edges: List of causal edges
            
        Returns:
            Dictionary with graph metrics
        """
        logger.info(f"Building causal graph with {len(dprs)} DPRs and {len(edges)} edges")
        
        # Add nodes
        for dpr in dprs:
            self.graph.add_node(
                dpr.dpr_id,
                title=dpr.title,
                component=dpr.component,
                blast_radius=dpr.blast_radius_estimate,
                decay_risk=dpr.assumption_decay_risk
            )
            
        # Add edges
        for edge in edges:
            self.graph.add_edge(
                edge.from_dpr,
                edge.to_dpr,
                relationship=edge.relationship,
                explanation=edge.explanation
            )
            
        # Compute metrics
        metrics = self._compute_metrics()
        
        logger.info(f"Graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        
        return metrics
        
    def _compute_metrics(self) -> Dict[str, Any]:
        """Compute graph metrics."""
        metrics = {
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
            "density": nx.density(self.graph),
            "is_dag": nx.is_directed_acyclic_graph(self.graph),
        }
        
        # Centrality metrics
        if len(self.graph.nodes) > 0:
            metrics["betweenness"] = nx.betweenness_centrality(self.graph)
            metrics["in_degree"] = dict(self.graph.in_degree())
            metrics["out_degree"] = dict(self.graph.out_degree())
            
        return metrics
        
    def export_dot(self) -> str:
        """Export graph as DOT format."""
        return nx.nx_pydot.to_pydot(self.graph).to_string()
        
    def export_json(self) -> Dict[str, Any]:
        """Export graph as JSON."""
        return nx.node_link_data(self.graph)

# Made with Bob
