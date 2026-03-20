"""Auto-scaffold the ./aicouncil/ project directory on first run."""

import logging
import shutil
from importlib import resources
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_scaffold(project_root: Path | None = None) -> Path:
    """Create ./aicouncil/ with defaults on first run. Idempotent.

    Creates the project-local aicouncil directory with:
    - config.yaml (default config template)
    - history/ (empty, for council addendum files)
    - agents/ (empty, for user-created agent overrides)

    Args:
        project_root: Root directory for the project. Defaults to cwd.

    Returns:
        Path to the aicouncil directory.
    """
    root = project_root or Path.cwd()
    aicouncil_dir = root / "aicouncil"

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

    # Copy default config from package resources (only if missing)
    config_dest = aicouncil_dir / "config.yaml"
    if not config_dest.exists():
        default_config_ref = resources.files("aicouncil.defaults") / "default-config.yaml"
        with resources.as_file(default_config_ref) as default_config_path:
            shutil.copy2(default_config_path, config_dest)
        logger.debug(f"Copied default config to: {config_dest}")

    if not created_dir:
        logger.debug(f"Directory already exists: {aicouncil_dir}")

    return aicouncil_dir
