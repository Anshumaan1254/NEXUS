"""
Nexus Pydantic Models Package
All type-safe data models with validation
"""
from nexus.models.dpr import DPR, create_dpr_from_dict, validate_dpr_list
from nexus.models.config import AnalysisConfig
from nexus.models.commit import CommitRecord
from nexus.models.scan import FileRecord, RepoScanResult
from nexus.models.decay import AssumptionDecayRecord
from nexus.models.output import CausalGraphEdge, NexusOutput, NexusOutputWrapper

__all__ = [
    # DPR Models
    "DPR",
    "create_dpr_from_dict",
    "validate_dpr_list",
    
    # Configuration
    "AnalysisConfig",
    
    # Commit & Scan
    "CommitRecord",
    "FileRecord",
    "RepoScanResult",
    
    # Decay Monitoring
    "AssumptionDecayRecord",
    
    # Output Models
    "CausalGraphEdge",
    "NexusOutput",
    "NexusOutputWrapper",
]

# Made with Bob
