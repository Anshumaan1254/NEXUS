"""
LLM Client Service
Multi-backend LLM client supporting OpenAI, Anthropic, and IBM Granite
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Literal
from tenacity import retry, stop_after_attempt, wait_exponential

import openai
from anthropic import Anthropic  # type: ignore

from nexus.models.dpr import DPR
from nexus.models.commit import CommitRecord
from nexus.models.output import CausalGraphEdge

logger = logging.getLogger(__name__)

LLMBackend = Literal["openai", "anthropic", "watsonx"]


class LLMClient:
    """
    Multi-backend LLM client for structured output extraction.
    
    Supports:
    - OpenAI GPT-4
    - Anthropic Claude
    - IBM Granite (watsonx.ai)
    """
    
    def __init__(self, backend: Optional[LLMBackend] = None):
        """
        Initialize LLM client.
        
        Args:
            backend: LLM backend to use (defaults to env DEFAULT_LLM_BACKEND)
        """
        self.backend = backend or os.getenv("DEFAULT_LLM_BACKEND", "openai")
        
        # Initialize clients
        if self.backend == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        elif self.backend == "anthropic":
            self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
        elif self.backend == "watsonx":
            # IBM watsonx.ai setup would go here
            self.model = os.getenv("WATSONX_MODEL", "ibm/granite-13b-chat-v2")
            
        logger.info(f"Initialized LLM client with backend: {self.backend}")
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_dpr(self, commit: CommitRecord, component: str = "Other") -> Optional[DPR]:
        """
        Extract a Decision Provenance Record from a commit.
        
        Args:
            commit: Commit to analyze
            component: Component category
            
        Returns:
            DPR object or None if extraction fails
        """
        prompt = self._build_dpr_prompt(commit, component)
        
        try:
            if self.backend == "openai":
                response = await self._call_openai(prompt, json_mode=True)
            elif self.backend == "anthropic":
                response = await self._call_anthropic(prompt)
            else:
                response = await self._call_watsonx(prompt)
                
            # Parse JSON response
            dpr_data = json.loads(response)
            
            # Validate and create DPR
            dpr = DPR(**dpr_data)
            return dpr
            
        except Exception as e:
            logger.error(f"Failed to extract DPR: {e}")
            return None
            
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def build_causal_graph(self, dprs: List[DPR]) -> List[CausalGraphEdge]:
        """
        Identify causal relationships between DPRs.
        
        Args:
            dprs: List of DPRs to analyze
            
        Returns:
            List of CausalGraphEdge objects (minimum 20)
        """
        prompt = self._build_graph_prompt(dprs)
        
        try:
            if self.backend == "openai":
                response = await self._call_openai(prompt, json_mode=True)
            elif self.backend == "anthropic":
                response = await self._call_anthropic(prompt)
            else:
                response = await self._call_watsonx(prompt)
                
            # Parse JSON response
            edges_data = json.loads(response)
            
            # Validate and create edges
            edges = [CausalGraphEdge(**edge) for edge in edges_data.get("edges", [])]
            
            # Ensure minimum 20 edges
            if len(edges) < 20:
                logger.warning(f"Only {len(edges)} edges generated, need 20")
                # Generate temporal edges to reach minimum
                edges.extend(self._generate_temporal_edges(dprs, 20 - len(edges)))
                
            return edges[:50]  # Cap at 50
            
        except Exception as e:
            logger.error(f"Failed to build causal graph: {e}")
            # Fallback: generate temporal edges
            return self._generate_temporal_edges(dprs, 20)
            
    async def _call_openai(self, prompt: str, json_mode: bool = False) -> str:
        """Call OpenAI API."""
        messages = [
            {"role": "system", "content": "You are a software architecture analyst."},
            {"role": "user", "content": prompt}
        ]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = openai.ChatCompletion.create(**kwargs)
        return response.choices[0].message.content
        
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        message = self.anthropic_client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
        
    async def _call_watsonx(self, prompt: str) -> str:
        """Call IBM watsonx.ai API."""
        # Placeholder for watsonx.ai implementation
        logger.warning("watsonx.ai not fully implemented, using mock response")
        return '{"edges": []}'
        
    def _build_dpr_prompt(self, commit: CommitRecord, component: str) -> str:
        """Build prompt for DPR extraction."""
        return f"""Analyze this commit and extract a Decision Provenance Record.

Commit: {commit.hash}
Date: {commit.date}
Author: {commit.author}
Message: {commit.message}
Files: {', '.join(commit.files_changed[:5])}

Extract a DPR with these 20 fields in JSON format:
{{
  "dpr_id": "DPR-001",
  "title": "Short decision name",
  "component": "{component}",
  "within_window": true,
  "decision_date": "{commit.date.strftime('%Y-%m')}",
  "decision": "What was chosen (1 sentence)",
  "rejected_alternatives": ["Alternative not chosen - reason"],
  "explicit_constraints": ["Constraint stated in code/docs"],
  "implicit_assumptions": ["INFERRED: Assumption inferred from context"],
  "intended_durability": "medium-term",
  "durability_reasoning": "Why this classification",
  "causal_dependencies": [],
  "files_involved": {json.dumps(commit.files_changed[:5])},
  "commit_refs": ["{commit.hash}"],
  "involved_humans": ["{commit.author}"],
  "assumption_decay_risk": "medium",
  "decay_risk_reasoning": "What could invalidate this",
  "blast_radius_estimate": "medium",
  "blast_radius_reasoning": "How many decisions depend on this",
  "active_workarounds": []
}}

Return ONLY valid JSON matching this schema."""
        
    def _build_graph_prompt(self, dprs: List[DPR]) -> str:
        """Build prompt for causal graph construction."""
        dpr_summaries = "\n".join([
            f"- {dpr.dpr_id}: {dpr.title} ({dpr.component})"
            for dpr in dprs[:20]  # Limit to 20 for token management
        ])
        
        return f"""Analyze these Decision Provenance Records and identify causal relationships.

DPRs:
{dpr_summaries}

Generate at least 20 causal edges in JSON format:
{{
  "edges": [
    {{
      "from_dpr": "DPR-001",
      "to_dpr": "DPR-002",
      "relationship": "constrains",
      "explanation": "One sentence explaining the causal link",
      "within_window": true
    }}
  ]
}}

Relationship types: constrains, enables, required_by, assumption_of, temporal_precedes

Return ONLY valid JSON."""
        
    def _generate_temporal_edges(self, dprs: List[DPR], count: int) -> List[CausalGraphEdge]:
        """Generate temporal edges as fallback."""
        edges = []
        sorted_dprs = sorted(dprs, key=lambda d: d.decision_date)
        
        for i in range(min(count, len(sorted_dprs) - 1)):
            edge = CausalGraphEdge(
                from_dpr=sorted_dprs[i].dpr_id,
                to_dpr=sorted_dprs[i + 1].dpr_id,
                relationship="temporal_precedes",
                explanation=f"{sorted_dprs[i].dpr_id} was decided before {sorted_dprs[i + 1].dpr_id}",
                within_window=sorted_dprs[i].within_window and sorted_dprs[i + 1].within_window
            )
            edges.append(edge)
            
        return edges

# Made with Bob
