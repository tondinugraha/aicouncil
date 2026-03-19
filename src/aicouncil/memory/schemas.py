"""Schemas for knowledge storage."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

KnowledgeType = Literal[
    "pattern",  # Code patterns discovered
    "architecture",  # Architectural insights
    "relation",  # File/module relationships
    "issue",  # Known issues, tech debt
    "convention",  # Project conventions
    "insight",  # General insights
]


class KnowledgeEntry(BaseModel):
    """A single piece of learned knowledge."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: KnowledgeType
    content: str = Field(description="The insight/knowledge itself")
    context: str = Field(default="", description="How/where this was discovered")
    tags: list[str] = Field(default_factory=list, description="Tags for retrieval")
    references: list[str] = Field(default_factory=list, description="Related file paths")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence 0-1")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    file_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Hash of referenced files when learned (for staleness detection)",
    )
    source_tool: str = Field(default="", description="Tool that generated this knowledge")
    validated: bool = Field(default=False, description="Whether user validated this")


class KnowledgeSummary(BaseModel):
    """Summary of all project knowledge."""

    total_entries: int = 0
    entries_by_type: dict[str, int] = Field(default_factory=dict)
    recent_entries: list[KnowledgeEntry] = Field(default_factory=list)
    top_tags: list[tuple[str, int]] = Field(default_factory=list)
    stale_count: int = 0
    validated_count: int = 0
    project_root: str = ""
    last_updated: datetime | None = None


class MemoryConfig(BaseModel):
    """Configuration for knowledge storage."""

    auto_learn: bool = Field(default=True, description="Automatically extract knowledge")
    max_entries: int = Field(default=1000, description="Max knowledge entries")
    stale_threshold_days: int = Field(default=30, description="Days before entry considered stale")
    min_confidence: float = Field(default=0.5, description="Min confidence to keep")
