"""Council history — sole boundary module for council addendum file output.

All council history file writes go through this module.
Uses atomic temp-file-then-rename to prevent partial output from interrupted sessions.
"""

import logging
import re
import tempfile
from datetime import datetime
from pathlib import Path

from aicouncil.council.schemas import AddendumMetadata
from aicouncil.exceptions import CouncilError

logger = logging.getLogger(__name__)


def _slugify_topic(topic: str) -> str:
    """Convert topic to URL-safe slug for filename.

    Lowercase, replace non-alphanumeric with hyphens, collapse multiple hyphens, trim.
    Truncate to 50 chars max for the filename portion.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug[:50].rstrip("-")


def _generate_filename(topic: str, timestamp: datetime | None = None) -> str:
    """Generate timestamped filename: YYYY-MM-DD-topic-slug.md."""
    ts = timestamp or datetime.now()
    date_str = ts.strftime("%Y-%m-%d")
    slug = _slugify_topic(topic)
    if not slug:
        slug = "council-session"
    return f"{date_str}-{slug}.md"


def _format_addendum_markdown(metadata: AddendumMetadata, addendum_content: str) -> str:
    """Format a council addendum as self-contained Markdown with YAML frontmatter.

    The file is readable by non-technical stakeholders without additional context.
    """
    # Build YAML frontmatter agents list
    agents_yaml_lines = []
    for agent_name in metadata.agents:
        model = metadata.model_assignments.get(agent_name, "unknown")
        agents_yaml_lines.append(f"  - name: {agent_name}")
        agents_yaml_lines.append(f"    model: {model}")
    agents_yaml = "\n".join(agents_yaml_lines)

    # Build human-readable agent list
    agent_display_parts = []
    for agent_name in metadata.agents:
        model = metadata.model_assignments.get(agent_name, "unknown")
        agent_display_parts.append(f"{agent_name} ({model})")
    agents_display = ", ".join(agent_display_parts)

    return (
        f"---\n"
        f"session_id: {metadata.session_id}\n"
        f'topic: "{metadata.topic}"\n'
        f"date: {metadata.timestamp}\n"
        f"agents:\n"
        f"{agents_yaml}\n"
        f"---\n"
        f"\n"
        f"# Council Addendum: {metadata.topic}\n"
        f"\n"
        f"**Date:** {metadata.timestamp}\n"
        f"**Session:** {metadata.session_id}\n"
        f"**Participating Agents:** {agents_display}\n"
        f"\n"
        f"---\n"
        f"\n"
        f"{addendum_content}\n"
    )


def _disambiguate_path(target_path: Path) -> Path:
    """If target_path exists, append a numeric suffix to disambiguate."""
    if not target_path.exists():
        return target_path

    stem = target_path.stem  # e.g. "2026-03-22-topic-slug"
    suffix = target_path.suffix  # ".md"
    parent = target_path.parent

    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def write_council_addendum(
    metadata: AddendumMetadata,
    addendum_content: str,
    project_root: Path | None = None,
) -> Path:
    """Write a council addendum as a timestamped markdown file.

    Uses atomic temp-file-then-rename to prevent partial writes.
    This is the sole file output boundary for council history.

    Args:
        metadata: Council session metadata for the file header.
        addendum_content: Full addendum narrative from the host AI.
        project_root: Project root directory (defaults to cwd).

    Returns:
        Path to the written addendum file.

    Raises:
        CouncilError: If file I/O fails.
    """
    root = project_root or Path.cwd()
    history_dir = root / "aicouncil" / "history"

    try:
        history_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise CouncilError(f"Failed to create history directory: {e}") from e

    # Parse timestamp for filename generation
    try:
        ts = datetime.fromisoformat(metadata.timestamp)
    except (ValueError, TypeError):
        ts = datetime.now()

    filename = _generate_filename(metadata.topic, timestamp=ts)
    target_path = _disambiguate_path(history_dir / filename)
    content = _format_addendum_markdown(metadata, addendum_content)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=history_dir,
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        tmp_path.replace(target_path)

        logger.info(
            "[council:%s] Addendum saved successfully (%d bytes)",
            metadata.session_id,
            len(content),
        )
        logger.debug("[council:%s] Addendum metadata: %s", metadata.session_id, metadata)

        return target_path

    except OSError as e:
        # Clean up temp file on error
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        logger.error("[council:%s] Failed to write addendum: %s", metadata.session_id, e)
        raise CouncilError(f"Failed to write council addendum: {e}") from e
