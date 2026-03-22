"""Project root detection utility.

Provides a single, cached function that every module uses instead of Path.cwd().
Walks up from cwd looking for root markers (.git, pyproject.toml, etc.) so the
result is correct even when the process cwd is a subdirectory of the project.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Same markers as ProjectDetector — kept in sync deliberately.
_ROOT_MARKERS = [
    ".git",
    "pyproject.toml",
    "package.json",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    ".sln",
]

_cached_root: Path | None = None


def get_project_root() -> Path:
    """Return the project root, caching after first call.

    Walks up from cwd looking for root marker files (.git, pyproject.toml, etc.).
    Falls back to cwd if no marker is found.
    """
    global _cached_root
    if _cached_root is not None:
        return _cached_root

    current = Path.cwd().absolute()

    while current != current.parent:
        for marker in _ROOT_MARKERS:
            if (current / marker).exists():
                _cached_root = current
                logger.debug("Detected project root: %s (marker: %s)", current, marker)
                return current
        current = current.parent

    # Fallback — no marker found
    fallback = Path.cwd().absolute()
    logger.warning("No project root marker found, falling back to cwd: %s", fallback)
    _cached_root = fallback
    return fallback


def reset_project_root() -> None:
    """Reset the cached root (for testing)."""
    global _cached_root
    _cached_root = None
