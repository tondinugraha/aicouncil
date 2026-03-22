"""Council history — sole boundary module for council addendum file output.

All council history file writes go through this module.
Uses atomic temp-file-then-link to prevent partial output and TOCTOU races.
"""

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from aicouncil.council.schemas import AddendumMetadata
from aicouncil.exceptions import CouncilError

logger = logging.getLogger(__name__)

MAX_DISAMBIGUATE_ATTEMPTS = 100


def _yaml_escape(value: str) -> str:
    """Escape a string for safe inclusion as a YAML double-quoted scalar."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


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
        logger.warning("Topic produced empty slug, falling back to 'council-session': %s", topic)
        slug = "council-session"
    return f"{date_str}-{slug}.md"


def _format_addendum_markdown(metadata: AddendumMetadata, addendum_content: str) -> str:
    """Format a council addendum as self-contained Markdown with YAML frontmatter.

    The file is readable by non-technical stakeholders without additional context.
    All YAML values are properly escaped to prevent injection.
    """
    # Build YAML frontmatter agents list with escaped values
    agents_yaml_lines = []
    for agent_name in metadata.agents:
        model = metadata.model_assignments.get(agent_name, "unknown")
        agents_yaml_lines.append(f'  - name: "{_yaml_escape(agent_name)}"')
        agents_yaml_lines.append(f'    model: "{_yaml_escape(model)}"')
    agents_yaml = "\n".join(agents_yaml_lines)

    # Build human-readable agent list for inline display
    agent_display_parts = []
    for agent_name in metadata.agents:
        model = metadata.model_assignments.get(agent_name, "unknown")
        agent_display_parts.append(f"{agent_name} ({model})")
    agents_display = ", ".join(agent_display_parts)

    # Build model assignments table
    model_table_lines = ["| Agent | Model |", "| --- | --- |"]
    for agent_name in metadata.agents:
        model = metadata.model_assignments.get(agent_name, "unknown")
        model_table_lines.append(f"| {agent_name} | {model} |")
    model_table = "\n".join(model_table_lines)

    return (
        f"---\n"
        f'session_id: "{_yaml_escape(metadata.session_id)}"\n'
        f'topic: "{_yaml_escape(metadata.topic)}"\n'
        f'date: "{_yaml_escape(metadata.timestamp)}"\n'
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
        f"**Model Assignments:**\n"
        f"\n"
        f"{model_table}\n"
        f"\n"
        f"---\n"
        f"\n"
        f"## Council Deliberation\n"
        f"\n"
        f"{addendum_content}\n"
    )


def _atomic_link_with_disambiguation(tmp_path: Path, history_dir: Path, filename: str) -> Path:
    """Atomically link temp file to target, disambiguating on collision.

    Uses os.link() which fails with FileExistsError if target exists,
    eliminating the TOCTOU race of check-then-rename.

    Raises:
        CouncilError: If no unique filename found within MAX_DISAMBIGUATE_ATTEMPTS.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    for attempt in range(MAX_DISAMBIGUATE_ATTEMPTS):
        if attempt == 0:
            candidate = history_dir / filename
        else:
            candidate = history_dir / f"{stem}-{attempt + 1}{suffix}"
        try:
            os.link(tmp_path, candidate)
            return candidate
        except FileExistsError:
            continue

    raise CouncilError(
        f"Failed to find unique filename after {MAX_DISAMBIGUATE_ATTEMPTS} attempts: {filename}"
    )


def write_council_addendum(
    metadata: AddendumMetadata,
    addendum_content: str,
    project_root: Path | None = None,
) -> Path:
    """Write a council addendum as a timestamped markdown file.

    Uses atomic temp-file-then-link to prevent partial writes and TOCTOU races.
    This is the sole file output boundary for council history.

    Args:
        metadata: Council session metadata for the file header.
        addendum_content: Full addendum narrative from the host AI.
        project_root: Project root directory (defaults to cwd).

    Returns:
        Path to the written addendum file.

    Raises:
        CouncilError: If file I/O fails or filename disambiguation exhausted.
    """
    root = project_root or Path.cwd()
    history_dir = root / "aicouncil" / "history"

    if not history_dir.exists():
        logger.warning(
            "[council:%s] History directory missing, creating: %s",
            metadata.session_id,
            history_dir,
        )

    try:
        history_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise CouncilError(f"Failed to create history directory: {e}") from e

    logger.info(
        "[council:%s] Saving addendum to %s",
        metadata.session_id,
        history_dir,
    )

    ts = datetime.fromisoformat(metadata.timestamp)

    filename = _generate_filename(metadata.topic, timestamp=ts)
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

        target_path = _atomic_link_with_disambiguation(tmp_path, history_dir, filename)

        logger.info(
            "[council:%s] Addendum saved successfully (%d bytes)",
            metadata.session_id,
            len(content),
        )
        logger.debug("[council:%s] Addendum metadata: %s", metadata.session_id, metadata)

        return target_path

    except CouncilError:
        raise
    except OSError as e:
        logger.error("[council:%s] Failed to write addendum: %s", metadata.session_id, e)
        raise CouncilError(f"Failed to write council addendum: {e}") from e
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
