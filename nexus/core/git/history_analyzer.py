"""
Git History Analyzer - Phase 2
Analyzes git commit history and scores commits for reasoning density
"""
import os
import re
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from github import Github
from git import Repo  # type: ignore

from nexus.models.commit import CommitRecord
from nexus.models.config import AnalysisConfig

logger = logging.getLogger(__name__)


# Reasoning signal keywords
REASONING_SIGNALS = [
    "because", "workaround", "temporary", "assume", "constraint",
    "limitation", "TODO", "FIXME", "HACK", "legacy",
    "backward compat", "cannot", "must not", "always", "never"
]


class HistoryAnalyzer:
    """
    Analyzes git commit history and scores commits for reasoning density.
    
    Phase 2 of the Nexus pipeline:
    - Fetches git log via GitHub API
    - Filters commits by analysis window
    - Scores each commit for reasoning density
    - Flags high-reasoning commits
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """Initialize history analyzer."""
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_client = Github(self.github_token) if self.github_token else Github()
        
    async def analyze_history(
        self,
        repo_url: str,
        config: AnalysisConfig
    ) -> List[CommitRecord]:
        """
        Analyze git history and return scored commits.
        
        Args:
            repo_url: GitHub repository URL
            config: Analysis configuration
            
        Returns:
            List of CommitRecord objects sorted by reasoning score
        """
        logger.info(f"Analyzing git history for {repo_url}")
        
        # Parse repo URL
        owner, repo_name = self._parse_repo_url(repo_url)
        
        # Get repository
        repo = self.github_client.get_repo(f"{owner}/{repo_name}")
        
        # Calculate date range
        cutoff_date = self._calculate_cutoff_date(config.analysis_window)
        
        # Fetch commits
        commits = []
        for commit in repo.get_commits(since=cutoff_date):
            commit_record = self._create_commit_record(commit)
            commits.append(commit_record)
            
        logger.info(f"Fetched {len(commits)} commits")
        
        # Score commits
        for commit in commits:
            commit.reasoning_score = self._score_commit(commit)
            
        # Sort by reasoning score
        commits.sort(key=lambda c: c.reasoning_score, reverse=True)
        
        logger.info(f"Top reasoning score: {commits[0].reasoning_score if commits else 0:.2f}")
        
        return commits
        
    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name."""
        pattern = r"https://github\.com/([\w-]+)/([\w-]+)/?$"
        match = re.match(pattern, repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub URL: {repo_url}")
        return match.group(1), match.group(2)
        
    def _calculate_cutoff_date(self, analysis_window: str) -> datetime:
        """Calculate cutoff date from analysis window."""
        if analysis_window == "all time":
            return datetime(1970, 1, 1)
            
        match = re.match(r'(\d+)\s+years?', analysis_window)
        if match:
            years = int(match.group(1))
            return datetime.now() - timedelta(days=years * 365)
            
        return datetime.now() - timedelta(days=730)  # Default 2 years
        
    def _create_commit_record(self, commit) -> CommitRecord:
        """Create CommitRecord from GitHub commit object."""
        return CommitRecord(
            hash=commit.sha[:12],
            author=commit.commit.author.name,
            date=commit.commit.author.date,
            message=commit.commit.message,
            files_changed=[f.filename for f in commit.files[:10]],  # Limit to 10
            reasoning_score=0.0
        )
        
    def _score_commit(self, commit: CommitRecord) -> float:
        """
        Score commit for reasoning density.
        
        Factors:
        - Keyword count (weighted)
        - Message length (longer = more reasoning)
        - Number of files changed
        
        Returns: 0.0 to 1.0
        """
        score = 0.0
        message_lower = commit.message.lower()
        
        # Keyword scoring (0-0.6)
        keyword_count = sum(1 for keyword in REASONING_SIGNALS if keyword in message_lower)
        score += min(keyword_count * 0.1, 0.6)
        
        # Message length scoring (0-0.2)
        if len(commit.message) > 200:
            score += 0.2
        elif len(commit.message) > 100:
            score += 0.1
            
        # Files changed scoring (0-0.2)
        if len(commit.files_changed) > 5:
            score += 0.2
        elif len(commit.files_changed) > 2:
            score += 0.1
            
        return min(score, 1.0)

# Made with Bob
