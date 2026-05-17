"""
Assumption Decay Record Pydantic Model
Represents decay monitoring results from Phase 5
"""
from typing import List
from pydantic import BaseModel, Field


class AssumptionDecayRecord(BaseModel):
    """
    Tracks a high-risk assumption and its decay signals.
    
    Used in Phase 5 to monitor assumptions that may become invalid over time.
    """
    
    dpr_id: str = Field(
        ...,
        pattern=r"^DPR-\d{3}$",
        description="Associated DPR ID",
        examples=["DPR-003"]
    )
    
    assumption: str = Field(
        ...,
        min_length=1,
        description="The assumption being monitored (should start with INFERRED:)",
        examples=["INFERRED: Assumes 8KB page size is optimal"]
    )
    
    decay_signals_found: List[str] = Field(
        default_factory=list,
        description="Signals found in commits indicating potential decay",
        examples=[["TODO: revisit page size for NVMe", "FIXME: page size breaks on cloud"]]
    )
    
    earliest_signal_date: str = Field(
        ...,
        description="Date of earliest decay signal (YYYY-MM) or 'not found'",
        examples=["2025-11", "not found"]
    )
    
    already_decaying: bool = Field(
        ...,
        description="True if assumption is actively breaking down"
    )
    
    decay_evidence: str = Field(
        ...,
        description="Direct quote or reference from commits if already_decaying=true",
        examples=["Multiple commits mention page size issues with cloud storage"]
    )
    
    recommended_monitor_query: str = Field(
        ...,
        min_length=1,
        description="Natural language query to run weekly to detect if assumption still holds",
        examples=["Check for commits mentioning page size in last month"]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dpr_id": "DPR-003",
                "assumption": "INFERRED: Assumes 8KB page size is optimal",
                "decay_signals_found": [
                    "TODO: revisit page size for NVMe",
                    "FIXME: page size assumption breaks on cloud storage"
                ],
                "earliest_signal_date": "2025-11",
                "already_decaying": True,
                "decay_evidence": "Multiple commits mention page size issues with cloud storage",
                "recommended_monitor_query": "SELECT COUNT(*) FROM commits WHERE message LIKE '%page size%' AND date > NOW() - INTERVAL '1 month'"
            }
        }
    }

# Made with Bob
