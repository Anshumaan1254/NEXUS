"""
Analysis Configuration Pydantic Model
Validates user input for repository analysis
"""
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator
import re


class AnalysisConfig(BaseModel):
    """
    Configuration for Nexus repository analysis.
    
    Validates repository URL, analysis window, priority areas, and minimum DPRs.
    """
    
    repository: str = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/postgres/postgres"]
    )
    
    analysis_window: Literal["1 year", "2 years", "3 years", "5 years", "all time"] = Field(
        ...,
        description="Time window for git history analysis"
    )
    
    priority_areas: List[str] = Field(
        default=["all"],
        description="Components to prioritize in analysis",
        examples=[["MVCC", "WAL", "Storage"], ["all"]]
    )
    
    min_dprs: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Minimum number of DPRs to extract"
    )
    
    @field_validator("repository")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        """Validate GitHub repository URL format"""
        pattern = r"^https://github\.com/[\w-]+/[\w-]+/?$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid GitHub URL: {v}. Must be in format: "
                "https://github.com/owner/repo"
            )
        return v.rstrip("/")  # Remove trailing slash
    
    @field_validator("priority_areas")
    @classmethod
    def validate_priority_areas(cls, v: List[str]) -> List[str]:
        """Validate priority areas against known components"""
        valid_areas = {
            "all", "MVCC", "WAL", "Storage", "Optimizer", "Replication",
            "LockManager", "IndexAM", "Parser", "ProcessModel",
            "Autovacuum", "ExtensionAPI", "Checkpointing", "TOAST"
        }
        
        for area in v:
            if area not in valid_areas:
                raise ValueError(
                    f"Invalid priority area: {area}. "
                    f"Valid areas: {', '.join(sorted(valid_areas))}"
                )
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "repository": "https://github.com/postgres/postgres",
                "analysis_window": "2 years",
                "priority_areas": ["MVCC", "WAL", "Storage"],
                "min_dprs": 25
            }
        }
    }

# Made with Bob
