"""
Repository Scan Result Pydantic Models
Represents the output of Phase 1: Repository Scanner
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class FileRecord(BaseModel):
    """Represents a single file in the repository."""
    
    path: str = Field(
        ...,
        description="Relative path from repository root",
        examples=["src/main.py", "include/postgres.h"]
    )
    
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )
    
    language: str = Field(
        ...,
        description="Programming language detected",
        examples=["Python", "C", "JavaScript", "TypeScript"]
    )
    
    last_modified: datetime = Field(
        ...,
        description="Last modification timestamp"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "path": "src/main.py",
                "size": 1024,
                "language": "Python",
                "last_modified": "2024-03-15T10:30:00Z"
            }
        }
    }


class RepoScanResult(BaseModel):
    """Complete result of repository scanning (Phase 1)."""
    
    repository: str = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/postgres/postgres"]
    )
    
    files: List[FileRecord] = Field(
        default_factory=list,
        description="All files indexed in the repository"
    )
    
    design_comments: List[str] = Field(
        default_factory=list,
        description="Design comment blocks extracted from file headers",
        examples=[["# Design: This module implements the core request handling"]]
    )
    
    readme_files: List[str] = Field(
        default_factory=list,
        description="Paths to README, TODO, ARCHITECTURE files found",
        examples=[["README.md", "CONTRIBUTING.md", "docs/ARCHITECTURE.md"]]
    )
    
    primary_language: str = Field(
        ...,
        description="Most common programming language in the repository",
        examples=["Python", "C", "JavaScript"]
    )
    
    framework: Optional[str] = Field(
        default=None,
        description="Detected framework if any",
        examples=["Django", "React", "FastAPI"]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "repository": "https://github.com/psf/requests",
                "files": [
                    {
                        "path": "src/main.py",
                        "size": 1024,
                        "language": "Python",
                        "last_modified": "2024-03-15T10:30:00Z"
                    }
                ],
                "design_comments": [
                    "# Design: This module implements the core request handling"
                ],
                "readme_files": ["README.md", "CONTRIBUTING.md"],
                "primary_language": "Python",
                "framework": "requests"
            }
        }
    }

# Made with Bob
