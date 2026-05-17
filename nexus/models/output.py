"""
Nexus Output Pydantic Models
Complete analysis output structure with all phases
"""
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from nexus.models.dpr import DPR
from nexus.models.decay import AssumptionDecayRecord


class CausalGraphEdge(BaseModel):
    """
    Represents a causal relationship between two DPRs.
    
    Used in Phase 4 to build the Causal Temporal Graph (CTG).
    """
    
    from_dpr: str = Field(
        ...,
        pattern=r"^DPR-\d{3}$",
        description="Source DPR ID",
        examples=["DPR-001"]
    )
    
    to_dpr: str = Field(
        ...,
        pattern=r"^DPR-\d{3}$",
        description="Target DPR ID",
        examples=["DPR-002"]
    )
    
    relationship: Literal[
        "constrains", "enables", "required_by", "assumption_of", "temporal_precedes"
    ] = Field(
        ...,
        description="Type of causal relationship"
    )
    
    explanation: str = Field(
        ...,
        min_length=1,
        description="One sentence explaining the causal link",
        examples=["DPR-001 constrains the implementation of DPR-002"]
    )
    
    within_window: bool = Field(
        ...,
        description="True if both DPRs are within the analysis window"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "from_dpr": "DPR-001",
                "to_dpr": "DPR-002",
                "relationship": "constrains",
                "explanation": "MVCC tuple versioning constrains autovacuum design",
                "within_window": True
            }
        }
    }


class NexusOutput(BaseModel):
    """
    Complete Nexus analysis output containing all phases.
    
    This is the top-level container returned by the analysis pipeline.
    """
    
    # Metadata
    repository: str = Field(
        ...,
        description="GitHub repository URL analyzed"
    )
    
    analysis_window: str = Field(
        ...,
        description="Time window used for analysis"
    )
    
    window_cutoff_date: str = Field(
        ...,
        description="Cutoff date for analysis window (YYYY-MM-DD)"
    )
    
    analysis_timestamp: str = Field(
        ...,
        description="When this analysis was performed (ISO 8601)"
    )
    
    # Counts
    total_dprs: int = Field(
        ...,
        ge=0,
        description="Total number of DPRs extracted"
    )
    
    dprs_within_window: int = Field(
        ...,
        ge=0,
        description="Number of DPRs made within the analysis window"
    )
    
    dprs_pre_window_active: int = Field(
        ...,
        ge=0,
        description="Number of pre-window DPRs still actively maintained"
    )
    
    # Phase Results
    dprs: List[DPR] = Field(
        default_factory=list,
        description="All extracted Decision Provenance Records"
    )
    
    assumption_decay_prescan: List[AssumptionDecayRecord] = Field(
        default_factory=list,
        description="Decay monitoring results for high-risk assumptions"
    )
    
    ctg_edges: List[CausalGraphEdge] = Field(
        default_factory=list,
        description="Causal Temporal Graph edges"
    )
    
    @field_validator("ctg_edges")
    @classmethod
    def validate_minimum_edges(cls, v: List[CausalGraphEdge]) -> List[CausalGraphEdge]:
        """Ensure minimum 20 edges as per specification"""
        if len(v) < 20:
            raise ValueError(
                f"Must have at least 20 CTG edges, got {len(v)}. "
                "This is a requirement from the Nexus specification."
            )
        return v
    
    @field_validator("dprs")
    @classmethod
    def validate_counts_match(cls, v: List[DPR], info) -> List[DPR]:
        """Ensure DPR counts match the actual list length"""
        if hasattr(info, 'data') and 'total_dprs' in info.data:
            expected = info.data['total_dprs']
            actual = len(v)
            if expected != actual:
                raise ValueError(
                    f"total_dprs ({expected}) doesn't match actual DPR count ({actual})"
                )
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "repository": "https://github.com/postgres/postgres",
                "analysis_window": "2 years",
                "window_cutoff_date": "2024-05-17",
                "analysis_timestamp": "2026-05-17T07:00:00Z",
                "total_dprs": 28,
                "dprs_within_window": 18,
                "dprs_pre_window_active": 10,
                "dprs": [],
                "assumption_decay_prescan": [],
                "ctg_edges": []
            }
        }
    }


class NexusOutputWrapper(BaseModel):
    """
    Wrapper for the complete Nexus output JSON structure.
    
    This matches the expected output format from the specification.
    """
    
    nexus_output: NexusOutput = Field(
        ...,
        description="Complete Nexus analysis output"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "nexus_output": {
                    "repository": "https://github.com/postgres/postgres",
                    "analysis_window": "2 years",
                    "window_cutoff_date": "2024-05-17",
                    "analysis_timestamp": "2026-05-17T07:00:00Z",
                    "total_dprs": 28,
                    "dprs_within_window": 18,
                    "dprs_pre_window_active": 10,
                    "dprs": [],
                    "assumption_decay_prescan": [],
                    "ctg_edges": []
                }
            }
        }
    }

# Made with Bob
