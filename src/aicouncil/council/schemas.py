"""Council-specific Pydantic models for assembly, classification, and composition."""

from typing import Any

from pydantic import BaseModel, Field, computed_field


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


class ChairpersonInstructions(BaseModel):
    """Structured instructions for the host AI acting as chairperson."""

    speaking_order: str = Field(description="Instructions for managing agent speaking turns")
    debate_triggers: str = Field(description="When and how to introduce adversarial debate")
    conclusion_driving: str = Field(description="How to drive the council toward conclusion")
    topic_framing: str = Field(description="How to frame the topic for the council")


class ToneGuidance(BaseModel):
    """Rules for dynamic tone shifting during deliberation."""

    default_tone: str = Field(description="Starting tone for the deliberation")
    adversarial_triggers: str = Field(
        description="Conditions that should trigger adversarial/devil's advocate mode"
    )
    agreement_triggers: str = Field(
        description="Conditions that should trigger agreement-seeking mode"
    )
    tone_shift_rules: str = Field(description="Rules for when and how to shift between tones")


class ConvergenceGuidance(BaseModel):
    """Criteria for evaluating when to continue vs. drive toward consensus."""

    evaluation_criteria: str = Field(description="How to evaluate whether positions are converging")
    continue_signals: str = Field(description="Signals that deliberation should continue")
    consensus_signals: str = Field(description="Signals that it's time to drive toward consensus")
    no_fixed_rounds: str = Field(
        description="Reminder: no fixed round count — evaluate dynamically"
    )


class ContextWindowInfo(BaseModel):
    """Per-model context window metadata for adaptive context management."""

    model: str = Field(description="Model identifier")
    context_window: int = Field(description="Total context window in tokens")

    @computed_field(description="50% threshold for context summarization")  # type: ignore[misc]
    @property
    def half_window(self) -> int:
        return self.context_window // 2


class OrchestrationData(BaseModel):
    """Complete orchestration data package for the host AI chairperson."""

    chairperson: ChairpersonInstructions = Field(
        description="Instructions for directing the deliberation"
    )
    tone: ToneGuidance = Field(description="Dynamic tone shifting guidance")
    convergence: ConvergenceGuidance = Field(description="When to continue vs. drive to consensus")
    context_windows: list[ContextWindowInfo] = Field(
        description="Per-model context window metadata"
    )
    agent_count: int = Field(description="Number of agents in the council")
    summary: str = Field(description="Brief human-readable orchestration summary")


class CouncilAssemblyResult(BaseModel):
    """MCP tool return — everything the host AI needs to orchestrate."""

    composition: CouncilComposition = Field(description="Who is on the council")
    orchestration: OrchestrationData = Field(
        description="Orchestration data for the host AI chairperson"
    )
