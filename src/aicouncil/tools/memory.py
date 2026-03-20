"""Memory tools — remember, recall, forget, show_knowledge_summary."""

import logging
from typing import Literal

from pydantic import ValidationError

from aicouncil.exceptions import AiCouncilError
from aicouncil.schemas.responses import MemoryResult, RecallResult

logger = logging.getLogger(__name__)


async def remember(
    content: str,
    knowledge_type: Literal[
        "pattern", "architecture", "relation", "issue", "convention", "insight"
    ] = "insight",
    tags: list[str] | None = None,
    references: list[str] | None = None,
) -> MemoryResult:
    """
    Save knowledge to project memory.
    Types: pattern, architecture, relation, issue, convention, insight.
    """
    if not content or not content.strip():
        return MemoryResult(
            success=False,
            message="No content provided to remember",
        )

    logger.info(f"Saving knowledge: {knowledge_type}")

    try:
        from aicouncil.memory import KnowledgeLearner

        learner = KnowledgeLearner()
        entry_id = learner.learn_explicit(
            content=content,
            knowledge_type=knowledge_type,
            tags=tags,
            references=references,
        )

        return MemoryResult(
            success=True,
            entry_id=entry_id,
            message=f"Knowledge saved as {knowledge_type} (ID: {entry_id})",
        )

    except AiCouncilError as e:
        logger.error(f"Failed to save knowledge: {e}")
        return MemoryResult(
            success=False,
            message=f"Failed to save: {e}",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError, OSError) as e:
        logger.error(f"Unexpected error in remember: {e}")
        return MemoryResult(
            success=False,
            message=f"Unexpected error: {e}",
        )


async def recall(
    query: str,
    knowledge_type: Literal["pattern", "architecture", "relation", "issue", "convention", "insight"]
    | None = None,
    limit: int = 10,
) -> RecallResult:
    """
    Search project memory by query. Optional filter by knowledge_type.
    """
    if not query or not query.strip():
        return RecallResult(
            query=query,
            total_found=0,
            entries=[],
            context_snippet="No query provided for recall",
        )

    logger.info(f"Recalling knowledge: {query}")

    try:
        from aicouncil.memory import KnowledgeRetriever, KnowledgeStore

        store = KnowledgeStore()
        retriever = KnowledgeRetriever()

        if knowledge_type:
            # Fetch more results before filtering to ensure we get enough matches
            fetch_limit = limit * 5
            entries = store.search(query, limit=fetch_limit)
            entries = [e for e in entries if e.type == knowledge_type][:limit]
        else:
            entries = store.search(query, limit=limit)

        return RecallResult(
            query=query,
            total_found=len(entries),
            entries=[e.model_dump() for e in entries],
            context_snippet=retriever.format_for_prompt(entries),
        )

    except AiCouncilError as e:
        logger.error(f"Failed to recall knowledge: {e}")
        return RecallResult(
            query=query,
            total_found=0,
            entries=[],
            context_snippet=f"Recall failed: {e}",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"Unexpected error in recall: {e}")
        return RecallResult(
            query=query,
            total_found=0,
            entries=[],
            context_snippet=f"Unexpected error: {e}",
        )


async def forget(
    entry_id: str,
) -> MemoryResult:
    """
    Delete a knowledge entry by ID.
    """
    logger.info(f"Forgetting knowledge: {entry_id}")

    try:
        from aicouncil.memory import KnowledgeStore

        store = KnowledgeStore()
        success = store.delete(entry_id)

        if success:
            return MemoryResult(
                success=True,
                entry_id=entry_id,
                message=f"Knowledge entry {entry_id} deleted",
            )
        else:
            return MemoryResult(
                success=False,
                entry_id=entry_id,
                message=f"Entry {entry_id} not found",
            )

    except AiCouncilError as e:
        logger.error(f"Failed to delete knowledge: {e}")
        return MemoryResult(
            success=False,
            message=f"Delete failed: {e}",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError, OSError) as e:
        logger.error(f"Unexpected error in forget: {e}")
        return MemoryResult(
            success=False,
            message=f"Unexpected error: {e}",
        )


async def show_knowledge_summary() -> MemoryResult:
    """
    List all saved project knowledge with counts by type.
    """
    logger.info("Showing knowledge summary")

    try:
        from aicouncil.memory import KnowledgeStore

        store = KnowledgeStore()
        summary = store.get_summary()
        type_breakdown = ", ".join(f"{k}: {v}" for k, v in summary.entries_by_type.items())
        msg = (
            f"Total: {summary.total_entries} entries. "
            f"By type: {type_breakdown or 'none'}. "
            f"Validated: {summary.validated_count}, Stale: {summary.stale_count}."
        )
        return MemoryResult(success=True, message=msg)

    except AiCouncilError as e:
        logger.error(f"Failed to get knowledge summary: {e}")
        return MemoryResult(success=False, message=f"Failed to load knowledge summary: {e}")
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError, OSError) as e:
        logger.error(f"Unexpected error in show_knowledge_summary: {e}")
        return MemoryResult(success=False, message=f"Unexpected error: {e}")
