"""
Decision Provenance Record (DPR) Pydantic Model
Complete type-safe model with all 20 required fields and validation
"""
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class DPR(BaseModel):
    """
    Decision Provenance Record - captures a single architectural decision
    with all context, constraints, assumptions, and risk assessments.
    
    All 20 fields are required. Implicit assumptions must be prefixed with "INFERRED:".
    """
    
    # Identification
    dpr_id: str = Field(
        ...,
        pattern=r"^DPR-\d{3}$",
        description="Unique identifier in format DPR-XXX",
        examples=["DPR-001", "DPR-042"]
    )
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Short, descriptive title of the decision",
        examples=["MVCC tuple versioning strategy"]
    )
    
    component: Literal[
        "Storage", "Optimizer", "WAL", "MVCC", "Replication",
        "LockManager", "IndexAM", "Parser", "ProcessModel",
        "Autovacuum", "ExtensionAPI", "Checkpointing", "TOAST", "Other"
    ] = Field(
        ...,
        description="Primary component affected by this decision"
    )
    
    within_window: bool = Field(
        ...,
        description="True if decision was made within the analysis window"
    )
    
    decision_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$|^pre-window$",
        description="Date decision was made (YYYY-MM) or 'pre-window'",
        examples=["2024-03", "pre-window"]
    )
    
    # Core Decision Content
    decision: str = Field(
        ...,
        min_length=1,
        description="What was chosen - one clear sentence",
        examples=["Use tuple versioning for MVCC implementation"]
    )
    
    rejected_alternatives: List[str] = Field(
        default_factory=list,
        description="Alternatives considered but not chosen, with reasons",
        examples=[["Timestamp-based versioning - rejected due to clock skew issues"]]
    )
    
    explicit_constraints: List[str] = Field(
        default_factory=list,
        description="Constraints explicitly stated in code, docs, or commits",
        examples=[["Must support concurrent transactions", "Must maintain ACID properties"]]
    )
    
    implicit_assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions inferred from context - must be prefixed with 'INFERRED:'",
        examples=[["INFERRED: Assumes sufficient disk space for tuple versions"]]
    )
    
    # Durability Assessment
    intended_durability: Literal["temporary", "medium-term", "foundational"] = Field(
        ...,
        description="Expected lifespan of this decision"
    )
    
    durability_reasoning: str = Field(
        ...,
        min_length=1,
        description="Why this durability classification was chosen"
    )
    
    # Relationships
    causal_dependencies: List[str] = Field(
        default_factory=list,
        description="Other DPR IDs this decision depends on",
        examples=[["DPR-007", "DPR-012"]]
    )
    
    # Traceability
    files_involved: List[str] = Field(
        default_factory=list,
        description="File paths related to this decision",
        examples=[["src/backend/access/heap/heapam.c"]]
    )
    
    commit_refs: List[str] = Field(
        default_factory=list,
        description="Commit hashes or distinctive message fragments",
        examples=[["a1b2c3d4", "Fix MVCC visibility bug"]]
    )
    
    involved_humans: List[str] = Field(
        default_factory=list,
        description="Authors/committers involved in this decision",
        examples=[["Tom Lane", "Bruce Momjian"]]
    )
    
    # Risk Assessment
    assumption_decay_risk: Literal["low", "medium", "high"] = Field(
        ...,
        description="Risk that assumptions will become invalid"
    )
    
    decay_risk_reasoning: str = Field(
        ...,
        min_length=1,
        description="What external change would invalidate assumptions"
    )
    
    blast_radius_estimate: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="How many downstream decisions depend on this"
    )
    
    blast_radius_reasoning: str = Field(
        ...,
        min_length=1,
        description="Why this blast radius estimate was chosen"
    )
    
    # Active Issues
    active_workarounds: List[str] = Field(
        default_factory=list,
        description="Code paths, config knobs, or escape hatches added due to this decision",
        examples=[["Added --disable-mvcc flag for legacy compatibility"]]
    )
    
    @field_validator("implicit_assumptions")
    @classmethod
    def validate_inferred_prefix(cls, v: List[str]) -> List[str]:
        """Ensure all implicit assumptions are prefixed with 'INFERRED:'"""
        for assumption in v:
            if not assumption.startswith("INFERRED:"):
                raise ValueError(
                    f"Implicit assumption must start with 'INFERRED:': {assumption}"
                )
        return v
    
    @field_validator("causal_dependencies")
    @classmethod
    def validate_dpr_ids(cls, v: List[str]) -> List[str]:
        """Ensure causal dependencies are valid DPR IDs"""
        import re
        pattern = re.compile(r"^DPR-\d{3}$")
        for dpr_id in v:
            if not pattern.match(dpr_id):
                raise ValueError(
                    f"Invalid DPR ID in causal_dependencies: {dpr_id}"
                )
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dpr_id": "DPR-001",
                "title": "MVCC tuple versioning strategy",
                "component": "MVCC",
                "within_window": True,
                "decision_date": "2024-03",
                "decision": "Use tuple versioning for MVCC implementation",
                "rejected_alternatives": [
                    "Timestamp-based versioning - rejected due to clock skew issues"
                ],
                "explicit_constraints": [
                    "Must support concurrent transactions",
                    "Must maintain ACID properties"
                ],
                "implicit_assumptions": [
                    "INFERRED: Assumes sufficient disk space for tuple versions",
                    "INFERRED: Assumes autovacuum will clean up dead tuples"
                ],
                "intended_durability": "foundational",
                "durability_reasoning": "Core MVCC design, unlikely to change",
                "causal_dependencies": ["DPR-007"],
                "files_involved": ["src/backend/access/heap/heapam.c"],
                "commit_refs": ["a1b2c3d4"],
                "involved_humans": ["Tom Lane"],
                "assumption_decay_risk": "low",
                "decay_risk_reasoning": "Well-established pattern, no external dependencies",
                "blast_radius_estimate": "critical",
                "blast_radius_reasoning": "Affects all transaction processing",
                "active_workarounds": []
            }
        }
    }


def create_dpr_from_dict(data: dict) -> DPR:
    """
    Helper function to create a DPR from a dictionary with validation.
    
    Args:
        data: Dictionary containing DPR fields
        
    Returns:
        Validated DPR instance
        
    Raises:
        ValidationError: If data doesn't match schema
    """
    return DPR(**data)


def validate_dpr_list(dprs: List[dict]) -> List[DPR]:
    """
    Validate a list of DPR dictionaries.
    
    Args:
        dprs: List of DPR dictionaries
        
    Returns:
        List of validated DPR instances
        
    Raises:
        ValidationError: If any DPR is invalid
    """
    return [DPR(**dpr) for dpr in dprs]

# Made with Bob
