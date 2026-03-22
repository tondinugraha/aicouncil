"""Auto-scaffold the ./.aicouncil/ project directory on first run."""

import json
import logging
import shutil
from datetime import datetime
from importlib import resources
from pathlib import Path

from aicouncil.roots import get_project_root

logger = logging.getLogger(__name__)

README_CONTENT = """# AI Council Knowledge Store

This directory contains learned knowledge about your project that AI Council
uses to provide better, project-specific analysis and recommendations.

## Structure

- `knowledge/` - JSONL files containing learned insights by type
  - `patterns.jsonl` - Code patterns discovered
  - `architecture.jsonl` - Architectural insights
  - `relations.jsonl` - File/module relationships
  - `issues.jsonl` - Known issues and tech debt
  - `conventions.jsonl` - Project conventions
  - `insights.jsonl` - General insights
- `index.json` - Quick lookup index
- `config.yaml` - Memory configuration

## Should I commit this?

**Yes!** Sharing project knowledge across your team helps everyone get
better AI assistance. The knowledge is specific to your codebase.

## Clearing knowledge

Delete specific entries using the `forget` tool, or delete this entire
directory to start fresh.
"""


def ensure_scaffold(project_root: Path | None = None) -> Path:
    """Create ./.aicouncil/ with defaults on first run. Idempotent.

    Creates the project-local aicouncil directory with:
    - config.yaml (default config template)
    - history/ (empty, for council addendum files)
    - agents/ (empty, for user-created agent overrides)
    - knowledge/ (empty, for learned project knowledge)
    - index.json (empty knowledge index)
    - README.md (knowledge store documentation)

    Args:
        project_root: Root directory for the project. Defaults to detected project root.

    Returns:
        Path to the aicouncil directory.
    """
    root = project_root or get_project_root()
    aicouncil_dir = root / ".aicouncil"

    created_dir = False
    if not aicouncil_dir.exists():
        logger.info(f"Auto-scaffolding {aicouncil_dir} directory with default config")
        aicouncil_dir.mkdir(parents=True)
        logger.debug(f"Created directory: {aicouncil_dir}")
        created_dir = True

    history_dir = aicouncil_dir / "history"
    if not history_dir.exists():
        history_dir.mkdir()
        logger.debug(f"Created directory: {history_dir}")

    agents_dir = aicouncil_dir / "agents"
    if not agents_dir.exists():
        agents_dir.mkdir()
        logger.debug(f"Created directory: {agents_dir}")

    knowledge_dir = aicouncil_dir / "knowledge"
    if not knowledge_dir.exists():
        knowledge_dir.mkdir()
        logger.debug(f"Created directory: {knowledge_dir}")

    # Copy default config from package resources (only if missing)
    config_dest = aicouncil_dir / "config.yaml"
    if not config_dest.exists():
        default_config_ref = resources.files("aicouncil.defaults") / "default-config.yaml"
        with resources.as_file(default_config_ref) as default_config_path:
            shutil.copy2(default_config_path, config_dest)
        logger.debug(f"Copied default config to: {config_dest}")

    # Create empty knowledge index (only if missing)
    index_path = aicouncil_dir / "index.json"
    if not index_path.exists():
        index = {
            "updated_at": datetime.utcnow().isoformat(),
            "counts": {},
            "tags": [],
        }
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)
        logger.debug(f"Created knowledge index: {index_path}")

    # Create README (only if missing)
    readme_path = aicouncil_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(README_CONTENT)
        logger.debug(f"Created README: {readme_path}")

    if not created_dir:
        logger.debug(f"Directory already exists: {aicouncil_dir}")

    return aicouncil_dir
