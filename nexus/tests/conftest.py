"""
Pytest configuration and shared fixtures for Nexus tests.
"""
import pytest
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import shutil

from nexus.models.dpr import DPR
from nexus.models.config import AnalysisConfig
from nexus.models.commit import CommitRecord
from nexus.models.scan import RepoScanResult, FileRecord
from nexus.models.output import CausalGraphEdge, AssumptionDecayRecord


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config() -> AnalysisConfig:
    """Sample analysis configuration."""
    return AnalysisConfig(
        repository="https://github.com/psf/requests",
        analysis_window="2 years",
        priority_areas=["all"],
        min_dprs=25
    )


@pytest.fixture
def temp_repo_dir():
    """Temporary directory for repository cloning."""
    temp_dir = tempfile.mkdtemp(prefix="nexus_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def sample_dpr() -> DPR:
    """Sample Decision Provenance Record."""
    return DPR(
        dpr_id="DPR-001",
        title="MVCC tuple versioning strategy",
        component="MVCC",
        within_window=True,
        decision_date="2024-03",
        decision="Use tuple versioning for MVCC implementation",
        rejected_alternatives=[
            "Timestamp-based versioning - rejected due to clock skew issues"
        ],
        explicit_constraints=[
            "Must support concurrent transactions",
            "Must maintain ACID properties"
        ],
        implicit_assumptions=[
            "INFERRED: Assumes sufficient disk space for tuple versions",
            "INFERRED: Assumes autovacuum will clean up dead tuples"
        ],
        intended_durability="foundational",
        durability_reasoning="Core MVCC design, unlikely to change",
        causal_dependencies=["DPR-007"],
        files_involved=["src/backend/access/heap/heapam.c"],
        commit_refs=["a1b2c3d4"],
        involved_humans=["Tom Lane"],
        assumption_decay_risk="low",
        decay_risk_reasoning="Well-established pattern, no external dependencies",
        blast_radius_estimate="critical",
        blast_radius_reasoning="Affects all transaction processing",
        active_workarounds=[]
    )


@pytest.fixture
def sample_dprs() -> List[DPR]:
    """List of sample DPRs for testing."""
    return [
        DPR(
            dpr_id=f"DPR-{i:03d}",
            title=f"Decision {i}",
            component="Storage",
            within_window=True,
            decision_date="2024-01",
            decision=f"Decision text {i}",
            rejected_alternatives=[],
            explicit_constraints=[],
            implicit_assumptions=[],
            intended_durability="medium-term",
            durability_reasoning="Test reasoning",
            causal_dependencies=[],
            files_involved=[f"file{i}.py"],
            commit_refs=[f"commit{i}"],
            involved_humans=["Test Author"],
            assumption_decay_risk="medium",
            decay_risk_reasoning="Test decay reasoning",
            blast_radius_estimate="medium",
            blast_radius_reasoning="Test blast radius",
            active_workarounds=[]
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_commit() -> CommitRecord:
    """Sample commit record."""
    return CommitRecord(
        hash="a1b2c3d4e5f6",
        author="Test Author",
        date=datetime(2024, 3, 15, tzinfo=timezone.utc),
        message="Fix: workaround for temporary constraint in storage layer",
        files_changed=["src/storage/manager.py", "src/storage/buffer.py"],
        reasoning_score=0.85
    )


@pytest.fixture
def sample_commits() -> List[CommitRecord]:
    """List of sample commits."""
    return [
        CommitRecord(
            hash=f"commit{i}",
            author="Test Author",
            date=datetime(2024, i, 1, tzinfo=timezone.utc),
            message=f"Commit message {i} with workaround and TODO",
            files_changed=[f"file{i}.py"],
            reasoning_score=0.5 + (i * 0.1)
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_file_record() -> FileRecord:
    """Sample file record."""
    return FileRecord(
        path="src/main.py",
        size=1024,
        language="Python",
        last_modified=datetime(2024, 3, 15, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_repo_scan() -> RepoScanResult:
    """Sample repository scan result."""
    return RepoScanResult(
        repository="https://github.com/psf/requests",
        files=[
            FileRecord(
                path=f"src/file{i}.py",
                size=1024 * i,
                language="Python",
                last_modified=datetime(2024, 3, i, tzinfo=timezone.utc)
            )
            for i in range(1, 6)
        ],
        design_comments=[
            "# Design: This module implements the core request handling",
            "# Architecture: Uses async/await for concurrent requests"
        ],
        readme_files=["README.md", "CONTRIBUTING.md"],
        primary_language="Python",
        framework="requests"
    )


@pytest.fixture
def sample_ctg_edge() -> CausalGraphEdge:
    """Sample causal graph edge."""
    return CausalGraphEdge(
        from_dpr="DPR-001",
        to_dpr="DPR-002",
        relationship="constrains",
        explanation="DPR-001 constrains the implementation of DPR-002",
        within_window=True
    )


@pytest.fixture
def sample_decay_alert() -> AssumptionDecayRecord:
    """Sample assumption decay alert."""
    return AssumptionDecayRecord(
        dpr_id="DPR-003",
        assumption="INFERRED: Assumes 8KB page size is optimal",
        decay_signals_found=[
            "TODO: revisit page size for NVMe",
            "FIXME: page size assumption breaks on cloud storage"
        ],
        earliest_signal_date="2025-11",
        already_decaying=True,
        decay_evidence="Multiple commits mention page size issues with cloud storage",
        recommended_monitor_query="SELECT COUNT(*) FROM commits WHERE message LIKE '%page size%'"
    )


# ============================================================================
# Mock LLM Response Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_dpr_response() -> Dict[str, Any]:
    """Mock LLM response for DPR extraction."""
    return {
        "dpr_id": "DPR-001",
        "title": "Test Decision",
        "component": "Storage",
        "within_window": True,
        "decision_date": "2024-03",
        "decision": "Test decision text",
        "rejected_alternatives": ["Alternative 1"],
        "explicit_constraints": ["Constraint 1"],
        "implicit_assumptions": ["INFERRED: Assumption 1"],
        "intended_durability": "medium-term",
        "durability_reasoning": "Test reasoning",
        "causal_dependencies": [],
        "files_involved": ["test.py"],
        "commit_refs": ["abc123"],
        "involved_humans": ["Test Author"],
        "assumption_decay_risk": "medium",
        "decay_risk_reasoning": "Test decay reasoning",
        "blast_radius_estimate": "medium",
        "blast_radius_reasoning": "Test blast radius",
        "active_workarounds": []
    }


@pytest.fixture
def mock_llm_graph_response() -> List[Dict[str, Any]]:
    """Mock LLM response for causal graph construction."""
    return [
        {
            "from_dpr": "DPR-001",
            "to_dpr": "DPR-002",
            "relationship": "constrains",
            "explanation": "Test explanation",
            "within_window": True
        }
        for i in range(20)  # Minimum 20 edges
    ]


# ============================================================================
# API Test Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from nexus.api.main import app
    
    return TestClient(app)


@pytest.fixture
def sample_analysis_request() -> Dict[str, Any]:
    """Sample API analysis request."""
    return {
        "repo_url": "https://github.com/psf/requests",
        "analysis_window": "2 years",
        "priority_areas": ["all"],
        "min_dprs": 25
    }


# ============================================================================
# GitHub Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_github_repo():
    """Mock GitHub repository object."""
    class MockRepo:
        def __init__(self):
            self.name = "requests"
            self.full_name = "psf/requests"
            self.clone_url = "https://github.com/psf/requests.git"
            self.default_branch = "main"
        
        def get_commits(self, since=None, until=None):
            """Mock get_commits method."""
            return []
    
    return MockRepo()


# ============================================================================
# Utility Functions
# ============================================================================

@pytest.fixture
def assert_valid_dpr():
    """Helper function to assert DPR validity."""
    def _assert(dpr: DPR):
        assert dpr.dpr_id.startswith("DPR-")
        assert len(dpr.title) > 0
        assert dpr.component in [
            "Storage", "Optimizer", "WAL", "MVCC", "Replication",
            "LockManager", "IndexAM", "Parser", "ProcessModel",
            "Autovacuum", "ExtensionAPI", "Checkpointing", "TOAST", "Other"
        ]
        assert dpr.intended_durability in ["temporary", "medium-term", "foundational"]
        assert dpr.assumption_decay_risk in ["low", "medium", "high"]
        assert dpr.blast_radius_estimate in ["low", "medium", "high", "critical"]
        
        # Check INFERRED prefix on implicit assumptions
        for assumption in dpr.implicit_assumptions:
            assert assumption.startswith("INFERRED:"), \
                f"Implicit assumption must start with 'INFERRED:': {assumption}"
    
    return _assert

# Made with Bob
