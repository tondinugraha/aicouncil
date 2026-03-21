"""Council-specific Pydantic models for assembly, classification, and composition."""

from typing import Any

from pydantic import BaseModel, Field


class TopicClassification(BaseModel):
    """Result of LLM-powered topic classification."""

    topic: str = Field(description="Original topic")
    domains: list[str] = Field(description="Identified capability domains")
    domain_scores: dict[str, float] = Field(description="Domain to confidence score (0.0-1.0)")
    reasoning: str = Field(description="Why these domains were identified")


class AgentAssignment(BaseModel):
    """Single agent with assigned model."""

    agent_name: str = Field(description="Agent display name")
    agent_role: str = Field(description="Agent role title")
    agent_type: str = Field(description="Agent type: expert/builder/user")
    agent_tier: int = Field(description="Agent tier: 1/2/3")
    assigned_model: str = Field(description="OpenRouter model ID")
    context_window: int | None = Field(default=None, description="Model context window in tokens")
    assignment_reasoning: str = Field(description="Why this agent + model combo")
    is_wildcard: bool = Field(default=False, description="True if wildcard pick")
    is_pinned: bool = Field(default=False, description="True if user-requested")
    persona: str = Field(description="Full persona Markdown for host AI")


class CouncilComposition(BaseModel):
    """Assembled council ready for deliberation."""

    session_id: str = Field(description="UUID for log correlation")
    topic: str = Field(description="Original topic")
    classification: TopicClassification = Field(description="Topic analysis")
    assignments: list[AgentAssignment] = Field(description="All agent-model pairs")
    council_size: int = Field(description="Number of seats filled")
    diversity_metrics: dict[str, Any] = Field(description="Category mix, tier spread, model spread")


class CouncilAssemblyResult(BaseModel):
    """MCP tool return — everything the host AI needs to orchestrate."""

    composition: CouncilComposition = Field(description="Who is on the council")
    orchestration_notes: str = Field(description="Brief guidance for the host AI")
