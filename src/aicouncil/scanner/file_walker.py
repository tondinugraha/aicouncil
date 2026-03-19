"""File walking with gitignore and security filtering."""

import fnmatch
import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Information about a scanned file."""

    path: str = Field(description="Relative path from project root")
    absolute_path: str = Field(description="Absolute path")
    size: int = Field(description="File size in bytes")
    lines: int = Field(default=0, description="Number of lines")
    extension: str = Field(description="File extension")
    is_test: bool = Field(default=False, description="Whether this is a test file")
    is_config: bool = Field(default=False, description="Whether this is a config file")


class FileWalker:
    """Walk project files respecting .gitignore and security rules."""

    # Never read these files (security)
    BLOCKLIST = [
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "*.crt",
        "*secret*",
        "*credential*",
        "*password*",
        "*.sqlite",
        "*.db",
        "*.sqlite3",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        ".npmrc",
        ".pypirc",
        "*.pfx",
        "*.p12",
    ]

    # Always ignore these directories
    IGNORE_DIRS = [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",
        ".cargo",
        "vendor",
        ".bundle",
        "coverage",
        ".coverage",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        ".eggs",
        "*.egg-info",
        ".idea",
        ".vscode",
        ".aicouncil",  # Our own cache directory
    ]

    # Code file extensions
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".vue",
        ".svelte",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".scala",
        ".cs",
        ".fs",
        ".rb",
        ".php",
        ".swift",
        ".m",
        ".h",
        ".c",
        ".cpp",
        ".hpp",
        ".lua",
        ".r",
        ".jl",
        ".ex",
        ".exs",
        ".erl",
        ".hs",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
    }

    # Config extensions
    CONFIG_EXTENSIONS = {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".xml",
        ".conf",
        ".config",
    }

    # Test file patterns
    TEST_PATTERNS = [
        "*test*",
        "*spec*",
        "*_test.*",
        "*_spec.*",
        "test_*",
        "spec_*",
        "*Test.*",
        "*Spec.*",
    ]

    def __init__(
        self,
        root: str | Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        include_tests: bool = False,
        max_file_size: int = 1_000_000,  # 1MB default
    ):
        """Initialize file walker."""
        self.root = Path(root)
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or []
        self.include_tests = include_tests
        self.max_file_size = max_file_size
        self.gitignore_patterns = self._load_gitignore()

    def _load_gitignore(self) -> list[str]:
        """Load patterns from .gitignore."""
        patterns = []
        gitignore = self.root / ".gitignore"

        if gitignore.exists():
            try:
                with open(gitignore) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
            except Exception:
                pass

        return patterns

    def _is_blocked(self, path: Path) -> bool:
        """Check if file is in security blocklist."""
        name = path.name.lower()
        rel_path = str(path.relative_to(self.root)).lower()

        for pattern in self.BLOCKLIST:
            if fnmatch.fnmatch(name, pattern.lower()):
                return True
            if fnmatch.fnmatch(rel_path, pattern.lower()):
                return True

        return False

    def _is_ignored(self, path: Path) -> bool:
        """Check if path should be ignored."""
        rel_path = str(path.relative_to(self.root))
        name = path.name

        # Check directory blocklist
        if path.is_dir():
            if name in self.IGNORE_DIRS:
                return True
            for pattern in self.IGNORE_DIRS:
                if fnmatch.fnmatch(name, pattern):
                    return True

        # Check gitignore patterns
        for pattern in self.gitignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(name, pattern):
                return True

        # Check custom exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True

        return False

    def _matches_include(self, path: Path) -> bool:
        """Check if file matches include patterns."""
        rel_path = str(path.relative_to(self.root))
        name = path.name

        for pattern in self.include_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(name, pattern):
                return True

        return False

    def _is_test_file(self, path: Path) -> bool:
        """Check if file is a test file."""
        name = path.name.lower()
        rel_path = str(path.relative_to(self.root)).lower()

        # Check if in test directory
        if "/test/" in rel_path or "/tests/" in rel_path or "/__tests__/" in rel_path:
            return True

        for pattern in self.TEST_PATTERNS:
            if fnmatch.fnmatch(name, pattern.lower()):
                return True

        return False

    def _count_lines(self, path: Path) -> int:
        """Count lines in file."""
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def walk(self) -> Iterator[FileInfo]:
        """Walk project and yield file info."""
        for current_path, dirs, files in os.walk(self.root):
            current = Path(current_path)

            # Filter directories in-place to prevent descending
            dirs[:] = [d for d in dirs if not self._is_ignored(current / d)]

            for file in files:
                file_path = current / file

                # Skip ignored and blocked files
                if self._is_ignored(file_path):
                    continue
                if self._is_blocked(file_path):
                    continue

                # Skip files that don't match include patterns
                if not self._matches_include(file_path):
                    continue

                # Check file size
                try:
                    size = file_path.stat().st_size
                    if size > self.max_file_size:
                        continue
                except Exception:
                    continue

                # Check test file status
                is_test = self._is_test_file(file_path)
                if is_test and not self.include_tests:
                    continue

                # Get extension
                ext = file_path.suffix.lower()
                is_config = ext in self.CONFIG_EXTENSIONS

                yield FileInfo(
                    path=str(file_path.relative_to(self.root)),
                    absolute_path=str(file_path.absolute()),
                    size=size,
                    lines=self._count_lines(file_path),
                    extension=ext,
                    is_test=is_test,
                    is_config=is_config,
                )

    def get_code_files(self) -> list[FileInfo]:
        """Get only code files."""
        return [f for f in self.walk() if f.extension in self.CODE_EXTENSIONS]

    def get_config_files(self) -> list[FileInfo]:
        """Get only config files."""
        return [f for f in self.walk() if f.is_config]

    def get_file_tree(self) -> dict:
        """Get file tree structure."""
        tree: dict = {}

        for file_info in self.walk():
            parts = file_info.path.split(os.sep)
            current = tree

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = {
                "size": file_info.size,
                "lines": file_info.lines,
            }

        return tree
