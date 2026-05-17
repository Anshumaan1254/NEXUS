"""
Commit Record Pydantic Model
Represents a git commit with reasoning score
"""
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime


class CommitRecord(BaseModel):
    """
    Represents a single git commit with metadata and reasoning score.
    
    The reasoning_score indicates how much architectural reasoning
    is present in the commit message and diff.
    """
    
    hash: str = Field(
        ...,
        min_length=7,
        max_length=40,
        description="Git commit hash (short or full)",
        examples=["a1b2c3d", "a1b2c3d4e5f6789012345678901234567890abcd"]
    )
    
    author: str = Field(
        ...,
        min_length=1,
        description="Commit author name",
        examples=["Tom Lane", "Bruce Momjian"]
    )
    
    date: datetime = Field(
        ...,
        description="Commit timestamp"
    )
    
    message: str = Field(
        ...,
        min_length=1,
        description="Full commit message",
        examples=["Fix: workaround for temporary constraint in storage layer"]
    )
    
    files_changed: List[str] = Field(
        default_factory=list,
        description="List of file paths modified in this commit",
        examples=[["src/storage/manager.py", "src/storage/buffer.py"]]
    )
    
    reasoning_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score indicating reasoning density (0.0 to 1.0)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "hash": "a1b2c3d4e5f6",
                "author": "Tom Lane",
                "date": "2024-03-15T10:30:00Z",
                "message": "Fix: workaround for temporary constraint in storage layer",
                "files_changed": ["src/storage/manager.py", "src/storage/buffer.py"],
                "reasoning_score": 0.85
            }
        }
    }

# Made with Bob
