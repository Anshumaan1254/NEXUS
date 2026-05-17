"""
Repository Scanner - Phase 1
Clones GitHub repositories and indexes all files with metadata
"""
import os
import re
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
import logging

from github import Github, Repository
from git import Repo  # type: ignore
import aiofiles  # type: ignore

from nexus.models.scan import FileRecord, RepoScanResult

logger = logging.getLogger(__name__)


class RepoScanner:
    """
    Scans GitHub repositories and extracts file metadata.
    
    Phase 1 of the Nexus pipeline:
    - Clones repository to temporary directory
    - Indexes all files with metadata
    - Extracts design comments
    - Detects language and framework
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize repository scanner.
        
        Args:
            github_token: GitHub personal access token for API access
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_client = Github(self.github_token) if self.github_token else Github()
        
    async def scan_repository(self, repo_url: str, target_dir: Optional[Path] = None) -> RepoScanResult:
        """
        Scan a GitHub repository and return structured metadata.
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo)
            target_dir: Optional target directory for cloning (uses temp if None)
            
        Returns:
            RepoScanResult with all indexed files and metadata
            
        Raises:
            ValueError: If repo_url is invalid
            Exception: If cloning or scanning fails
        """
        logger.info(f"Starting repository scan: {repo_url}")
        
        # Parse repository URL
        owner, repo_name = self._parse_repo_url(repo_url)
        
        # Create temporary directory if not provided
        if target_dir is None:
            temp_dir = tempfile.mkdtemp(prefix=f"nexus_{repo_name}_")
            target_dir = Path(temp_dir)
            cleanup_temp = True
        else:
            cleanup_temp = False
            
        try:
            # Clone repository
            logger.info(f"Cloning repository to {target_dir}")
            repo = self._clone_repository(repo_url, target_dir)
            
            # Index all files
            logger.info("Indexing files...")
            files = await self._index_files(target_dir)
            
            # Extract design comments
            logger.info("Extracting design comments...")
            design_comments = await self._extract_design_comments(target_dir)
            
            # Find documentation files
            logger.info("Finding documentation files...")
            readme_files = self._find_readme_files(target_dir)
            
            # Detect primary language
            logger.info("Detecting primary language...")
            primary_language = self._detect_primary_language(files)
            
            # Detect framework
            logger.info("Detecting framework...")
            framework = self._detect_framework(target_dir, primary_language)
            
            result = RepoScanResult(
                repository=repo_url,
                files=files,
                design_comments=design_comments,
                readme_files=readme_files,
                primary_language=primary_language,
                framework=framework
            )
            
            logger.info(f"Scan complete: {len(files)} files indexed")
            return result
            
        finally:
            # Cleanup temporary directory if created
            if cleanup_temp and target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
                
    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo_name)
            
        Raises:
            ValueError: If URL format is invalid
        """
        pattern = r"https://github\.com/([\w-]+)/([\w-]+)/?$"
        match = re.match(pattern, repo_url)
        
        if not match:
            raise ValueError(
                f"Invalid GitHub URL: {repo_url}. "
                "Expected format: https://github.com/owner/repo"
            )
            
        return match.group(1), match.group(2)
        
    def _clone_repository(self, repo_url: str, target_dir: Path) -> Repo:
        """
        Clone a GitHub repository to local directory.
        
        Args:
            repo_url: GitHub repository URL
            target_dir: Target directory for cloning
            
        Returns:
            GitPython Repo object
            
        Raises:
            Exception: If cloning fails
        """
        try:
            # Add authentication if token is available
            if self.github_token:
                auth_url = repo_url.replace(
                    "https://",
                    f"https://{self.github_token}@"
                )
                repo = Repo.clone_from(auth_url, target_dir, depth=1)
            else:
                repo = Repo.clone_from(repo_url, target_dir, depth=1)
                
            return repo
            
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise
            
    async def _index_files(self, repo_dir: Path) -> List[FileRecord]:
        """
        Index all files in the repository with metadata.
        
        Args:
            repo_dir: Repository directory path
            
        Returns:
            List of FileRecord objects
        """
        files = []
        
        # Walk through all files
        for file_path in repo_dir.rglob("*"):
            # Skip directories and hidden files
            if file_path.is_dir() or file_path.name.startswith("."):
                continue
                
            # Skip .git directory
            if ".git" in file_path.parts:
                continue
                
            try:
                # Get file stats
                stats = file_path.stat()
                
                # Detect language from extension
                language = self._detect_file_language(file_path)
                
                # Create relative path from repo root
                relative_path = file_path.relative_to(repo_dir)
                
                file_record = FileRecord(
                    path=str(relative_path).replace("\\", "/"),
                    size=stats.st_size,
                    language=language,
                    last_modified=datetime.fromtimestamp(
                        stats.st_mtime,
                        tz=timezone.utc
                    )
                )
                
                files.append(file_record)
                
            except Exception as e:
                logger.warning(f"Failed to index file {file_path}: {e}")
                continue
                
        return files
        
    def _detect_file_language(self, file_path: Path) -> str:
        """
        Detect programming language from file extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            Language name or "Unknown"
        """
        extension_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "JavaScript",
            ".tsx": "TypeScript",
            ".c": "C",
            ".h": "C",
            ".cpp": "C++",
            ".hpp": "C++",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".sql": "SQL",
            ".sh": "Shell",
            ".bash": "Shell",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".xml": "XML",
            ".html": "HTML",
            ".css": "CSS",
        }
        
        return extension_map.get(file_path.suffix.lower(), "Unknown")
        
    async def _extract_design_comments(self, repo_dir: Path) -> List[str]:
        """
        Extract design comment blocks from file headers.
        
        Looks for multi-line comments at the top of source files that
        contain design or architecture information.
        
        Args:
            repo_dir: Repository directory path
            
        Returns:
            List of design comment strings
        """
        design_comments = []
        design_keywords = ["design:", "architecture:", "overview:", "purpose:"]
        
        # Look for source files
        source_extensions = [".py", ".c", ".h", ".cpp", ".hpp", ".java", ".js", ".ts"]
        
        for ext in source_extensions:
            for file_path in repo_dir.rglob(f"*{ext}"):
                if ".git" in file_path.parts:
                    continue
                    
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = await f.read()
                        
                    # Extract first 20 lines
                    lines = content.split("\n")[:20]
                    header = "\n".join(lines).lower()
                    
                    # Check if any design keyword is present
                    if any(keyword in header for keyword in design_keywords):
                        # Extract the comment block
                        comment = self._extract_comment_block(content)
                        if comment and len(comment) > 50:  # Meaningful length
                            design_comments.append(comment)
                            
                except Exception as e:
                    logger.warning(f"Failed to read file {file_path}: {e}")
                    continue
                    
        return design_comments[:50]  # Limit to 50 comments
        
    def _extract_comment_block(self, content: str) -> Optional[str]:
        """
        Extract the first comment block from file content.
        
        Args:
            content: File content
            
        Returns:
            Comment block text or None
        """
        lines = content.split("\n")
        comment_lines = []
        in_comment = False
        
        for line in lines[:30]:  # Check first 30 lines
            stripped = line.strip()
            
            # Python/Shell style comments
            if stripped.startswith("#"):
                comment_lines.append(stripped[1:].strip())
                in_comment = True
            # C-style single line comments
            elif stripped.startswith("//"):
                comment_lines.append(stripped[2:].strip())
                in_comment = True
            # C-style multi-line comments
            elif "/*" in stripped:
                in_comment = True
                comment_lines.append(stripped.split("/*")[1].strip())
            elif "*/" in stripped:
                comment_lines.append(stripped.split("*/")[0].strip())
                break
            elif in_comment and stripped.startswith("*"):
                comment_lines.append(stripped[1:].strip())
            elif in_comment and not stripped:
                continue
            elif in_comment:
                break
                
        return "\n".join(comment_lines) if comment_lines else None
        
    def _find_readme_files(self, repo_dir: Path) -> List[str]:
        """
        Find all README, TODO, ARCHITECTURE, and similar documentation files.
        
        Args:
            repo_dir: Repository directory path
            
        Returns:
            List of relative file paths
        """
        doc_patterns = [
            "README*",
            "TODO*",
            "HISTORY*",
            "CHANGES*",
            "ARCHITECTURE*",
            "CONTRIBUTING*",
            "DESIGN*",
        ]
        
        readme_files = []
        
        for pattern in doc_patterns:
            for file_path in repo_dir.rglob(pattern):
                if file_path.is_file() and ".git" not in file_path.parts:
                    relative_path = file_path.relative_to(repo_dir)
                    readme_files.append(str(relative_path).replace("\\", "/"))
                    
        return sorted(set(readme_files))
        
    def _detect_primary_language(self, files: List[FileRecord]) -> str:
        """
        Detect the most common programming language in the repository.
        
        Args:
            files: List of indexed files
            
        Returns:
            Primary language name
        """
        language_counts = {}
        
        for file in files:
            if file.language != "Unknown":
                language_counts[file.language] = language_counts.get(file.language, 0) + 1
                
        if not language_counts:
            return "Unknown"
            
        return max(language_counts, key=language_counts.get)
        
    def _detect_framework(self, repo_dir: Path, primary_language: str) -> Optional[str]:
        """
        Detect framework based on configuration files and primary language.
        
        Args:
            repo_dir: Repository directory path
            primary_language: Detected primary language
            
        Returns:
            Framework name or None
        """
        # Check for common framework indicators
        framework_indicators = {
            "Django": ["manage.py", "settings.py"],
            "Flask": ["app.py", "requirements.txt"],
            "FastAPI": ["main.py", "requirements.txt"],
            "React": ["package.json", "src/App.jsx"],
            "Vue": ["package.json", "src/App.vue"],
            "Angular": ["angular.json", "package.json"],
            "Express": ["package.json", "app.js"],
            "Spring": ["pom.xml", "build.gradle"],
            "Rails": ["Gemfile", "config/routes.rb"],
        }
        
        for framework, indicators in framework_indicators.items():
            if all((repo_dir / indicator).exists() for indicator in indicators):
                return framework
                
        return None

# Made with Bob
