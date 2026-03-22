"""Agent system loader — dual-directory overlay, CSV + Markdown parsing.

This module is the sole owner of agent data loading. No other module should
read agent manifest CSV or persona Markdown files directly.
"""

import csv
import io
import logging
from importlib import resources
from pathlib import Path

import yaml

from aicouncil.exceptions import AgentLoadError
from aicouncil.schemas.agents import Agent, AgentRoster

logger = logging.getLogger(__name__)

# Required headers in agent-manifest.csv
_REQUIRED_CSV_HEADERS = {"name", "role", "type", "tier", "domains", "include_flag"}

# Required fields in YAML frontmatter
_REQUIRED_FRONTMATTER_FIELDS = {"name", "role", "type", "tier", "domains", "include_flag"}

_VALID_TYPES = {"expert", "builder", "user"}
_VALID_TIERS = {1, 2, 3}


def parse_manifest(csv_path: Path) -> list[dict]:
    """Parse a CSV agent manifest into a list of row dicts.

    Args:
        csv_path: Path to the agent-manifest.csv file.

    Returns:
        List of dicts, one per row.

    Raises:
        AgentLoadError: If CSV is missing, empty, or has missing required headers.
    """
    if not csv_path.exists():
        raise AgentLoadError(f"{csv_path.name}: manifest file not found")

    try:
        content = csv_path.read_text()
    except OSError as e:
        raise AgentLoadError(f"{csv_path.name}: failed to read manifest: {e}") from e

    return _parse_manifest_text(content, csv_path.name)


def _parse_manifest_text(text: str, source_name: str) -> list[dict]:
    """Parse CSV manifest content from a string (for importlib.resources)."""
    if not text.strip():
        raise AgentLoadError(f"{source_name}: manifest file is empty")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise AgentLoadError(f"{source_name}: manifest has no headers")

    headers = set(reader.fieldnames)
    missing = _REQUIRED_CSV_HEADERS - headers
    if missing:
        raise AgentLoadError(
            f"{source_name}: missing required headers: {', '.join(sorted(missing))}"
        )

    rows = list(reader)
    logger.debug("Parsed %d rows from %s", len(rows), source_name)
    return rows


def parse_persona(md_path: Path) -> Agent:
    """Parse a single Markdown persona file into an Agent model.

    Args:
        md_path: Path to the .md persona file.

    Returns:
        Agent model instance.

    Raises:
        AgentLoadError: If frontmatter is missing, malformed, or has invalid fields.
    """
    try:
        content = md_path.read_text()
    except OSError as e:
        raise AgentLoadError(f"{md_path.name}: failed to read persona file: {e}") from e

    return _parse_persona_text(content, md_path.name)


def _parse_persona_text(content: str, source_name: str) -> Agent:
    """Parse persona content from a string."""
    if not content.startswith("---"):
        raise AgentLoadError(f"{source_name}: missing YAML frontmatter (must start with ---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise AgentLoadError(f"{source_name}: malformed frontmatter (missing closing ---)")

    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        raise AgentLoadError(f"{source_name}: invalid YAML frontmatter: {e}") from e

    if not isinstance(frontmatter, dict):
        raise AgentLoadError(f"{source_name}: frontmatter must be a YAML mapping")

    missing = _REQUIRED_FRONTMATTER_FIELDS - set(frontmatter.keys())
    if missing:
        raise AgentLoadError(
            f"{source_name}: missing required fields: {', '.join(sorted(missing))}"
        )

    agent_type = frontmatter["type"]
    if agent_type not in _VALID_TYPES:
        valid = ", ".join(sorted(_VALID_TYPES))
        raise AgentLoadError(
            f"{source_name}: invalid type '{agent_type}' (must be one of: {valid})"
        )

    tier = frontmatter["tier"]
    try:
        tier = int(tier)
    except (TypeError, ValueError) as e:
        raise AgentLoadError(f"{source_name}: tier must be an integer, got '{tier}'") from e
    if tier not in _VALID_TIERS:
        raise AgentLoadError(
            f"{source_name}: invalid tier {tier} (must be one of: {sorted(_VALID_TIERS)})"
        )

    domains = frontmatter["domains"]
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(";") if d.strip()]
    elif not isinstance(domains, list):
        raise AgentLoadError(f"{source_name}: domains must be a list or semicolon-separated string")

    include_flag = frontmatter["include_flag"]
    if isinstance(include_flag, str):
        include_flag = include_flag.strip().lower() == "true"

    # Validate non-null required string fields
    for field in ("name", "role"):
        if frontmatter[field] is None:
            raise AgentLoadError(f"{source_name}: '{field}' must not be null")

    body = parts[2].strip()

    return Agent(
        name=str(frontmatter["name"]),
        role=str(frontmatter["role"]),
        type=agent_type,
        tier=tier,
        domains=domains,
        include_flag=bool(include_flag),
        persona=body,
    )


def load_agents_from_directory(directory: Path) -> list[Agent]:
    """Load all agents from a single directory.

    Reads manifest CSV to discover agents, then loads each persona .md file.
    If no manifest exists but .md files exist, loads .md files directly.
    If manifest references a missing file, logs WARNING and skips.
    If .md files exist outside manifest, still loads them.

    Args:
        directory: Path to the agents directory.

    Returns:
        List of Agent instances.
    """
    if not directory.exists() or not directory.is_dir():
        logger.debug("Agent directory does not exist: %s", directory)
        return []

    manifest_path = directory / "agent-manifest.csv"
    agents: dict[str, Agent] = {}  # keyed by lowercase name

    # Load from manifest if it exists
    if manifest_path.exists():
        try:
            rows = parse_manifest(manifest_path)
        except AgentLoadError as e:
            logger.warning("Failed to parse manifest, falling back to .md discovery: %s", e)
            rows = []

        for row in rows:
            md_name = row.get("name", "")
            if not md_name or "/" in md_name or "\\" in md_name or ".." in md_name:
                logger.warning("Manifest contains invalid agent name '%s' — skipping", md_name)
                continue
            md_file = directory / f"{md_name}.md"
            if not md_file.exists():
                logger.warning(
                    "Manifest references '%s' but %s not found — skipping", md_name, md_file.name
                )
                continue
            try:
                agent = parse_persona(md_file)
                agents[agent.name.lower()] = agent
                logger.debug("Loaded agent from manifest: %s", agent.name)
            except AgentLoadError as e:
                logger.error("Skipping malformed agent: %s", e)

    # Also load any .md files not already loaded (covers files outside manifest)
    for md_file in sorted(directory.glob("*.md")):
        try:
            agent = parse_persona(md_file)
            if agent.name.lower() not in agents:
                agents[agent.name.lower()] = agent
                logger.debug("Loaded agent from .md discovery: %s", agent.name)
        except AgentLoadError as e:
            logger.error("Skipping malformed agent: %s", e)

    return list(agents.values())


def load_builtin_agents() -> list[Agent]:
    """Load built-in agents from the package resources.

    Returns:
        List of Agent instances from src/aicouncil/agents/.
    """
    agents_ref = resources.files("aicouncil.agents")
    agents: dict[str, Agent] = {}

    # Try to load manifest first
    manifest_ref = agents_ref / "agent-manifest.csv"
    manifest_rows: list[dict] = []
    try:
        manifest_text = manifest_ref.read_text(encoding="utf-8")
        manifest_rows = _parse_manifest_text(manifest_text, "agent-manifest.csv")
    except (AgentLoadError, FileNotFoundError, TypeError) as e:
        logger.warning("Built-in manifest not available, falling back to .md discovery: %s", e)

    # Load agents referenced by manifest
    for row in manifest_rows:
        md_name = row.get("name", "")
        if not md_name or "/" in md_name or "\\" in md_name or ".." in md_name:
            logger.warning("Built-in manifest contains invalid agent name '%s' — skipping", md_name)
            continue
        md_ref = agents_ref / f"{md_name}.md"
        try:
            content = md_ref.read_text(encoding="utf-8")
            agent = _parse_persona_text(content, f"{md_name}.md")
            agents[agent.name.lower()] = agent
            logger.debug("Loaded built-in agent from manifest: %s", agent.name)
        except (AgentLoadError, FileNotFoundError, TypeError) as e:
            logger.warning("Skipping built-in agent '%s': %s", md_name, e)

    # Also discover .md files not in manifest
    try:
        for item in agents_ref.iterdir():
            if hasattr(item, "name") and item.name.endswith(".md"):
                try:
                    content = item.read_text(encoding="utf-8")
                    agent = _parse_persona_text(content, item.name)
                    if agent.name.lower() not in agents:
                        agents[agent.name.lower()] = agent
                        logger.debug("Loaded built-in agent from discovery: %s", agent.name)
                except (AgentLoadError, TypeError) as e:
                    logger.error("Skipping malformed built-in agent %s: %s", item.name, e)
    except (TypeError, AttributeError):
        logger.debug("Could not iterate built-in agents directory for discovery")

    return list(agents.values())


def load_user_agents(project_root: Path | None = None) -> list[Agent]:
    """Load user-created agents from the project-local directory.

    Args:
        project_root: Project root path. Defaults to cwd.

    Returns:
        List of Agent instances from ./.aicouncil/agents/.
    """
    root = project_root or Path.cwd()
    user_agents_dir = root / ".aicouncil" / "agents"
    return load_agents_from_directory(user_agents_dir)


def load_all_agents(project_root: Path | None = None) -> AgentRoster:
    """Load and merge agents from built-in and user directories.

    User agents with the same name (case-insensitive) override built-in agents.

    Args:
        project_root: Project root path. Defaults to cwd.

    Returns:
        AgentRoster with all merged agents.
    """
    builtin = load_builtin_agents()
    user = load_user_agents(project_root)

    # Start with built-in agents, override with user agents by name
    merged: dict[str, Agent] = {}
    for agent in builtin:
        merged[agent.name.lower()] = agent

    for agent in user:
        key = agent.name.lower()
        if key in merged:
            logger.info("User agent '%s' overrides built-in agent", agent.name)
        merged[key] = agent

    all_agents = list(merged.values())

    # Log summary
    type_counts = {}
    for agent in all_agents:
        type_counts[agent.type] = type_counts.get(agent.type, 0) + 1
    summary_parts = [f"{count} {atype}" for atype, count in sorted(type_counts.items())]
    logger.info("Loaded %d agents: %s", len(all_agents), ", ".join(summary_parts))

    return AgentRoster(agents=all_agents)


# Singleton
_agents: AgentRoster | None = None
_agents_project_root: Path | None = None


def get_agents(project_root: Path | None = None) -> AgentRoster:
    """Get the agent roster (lazy-loaded singleton).

    Reloads automatically if called with a different project_root.
    """
    global _agents, _agents_project_root
    if _agents is None or project_root != _agents_project_root:
        _agents_project_root = project_root
        _agents = load_all_agents(project_root)
    return _agents


def reset_agents() -> None:
    """Reset the agent singleton (for testing)."""
    global _agents, _agents_project_root
    _agents = None
    _agents_project_root = None
