"""Pydantic models for the agent system."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Agent(BaseModel):
    """A single agent persona with frontmatter metadata and Markdown body."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Agent display name from YAML frontmatter (override key)")
    role: str = Field(description="Agent role title")
    type: Literal["expert", "builder", "user"] = Field(description="Agent type category")
    tier: Literal[1, 2, 3] = Field(description="Agent tier level")
    domains: list[str] = Field(description="Agent domain expertise areas")
    include_flag: bool = Field(description="Whether agent is included by default")
    persona: str = Field(default="", description="Markdown body (persona prompt)")


class AgentRoster(BaseModel):
    """Merged collection of agents with query methods."""

    model_config = ConfigDict(frozen=True)

    agents: list[Agent] = Field(default_factory=list, description="All loaded agents")

    def by_type(self, agent_type: str) -> list[Agent]:
        """Filter agents by type."""
        return [a for a in self.agents if a.type == agent_type]

    def by_tier(self, tier: int) -> list[Agent]:
        """Filter agents by tier."""
        return [a for a in self.agents if a.tier == tier]

    def by_domain(self, domain: str) -> list[Agent]:
        """Filter agents that have the given domain."""
        return [a for a in self.agents if domain in a.domains]

    def experts(self) -> list[Agent]:
        """Get all expert agents."""
        return self.by_type("expert")

    def builders(self) -> list[Agent]:
        """Get all builder agents."""
        return self.by_type("builder")

    def users(self, include_flagged_only: bool = True) -> list[Agent]:
        """Get user agents, optionally filtered by include_flag."""
        user_agents = self.by_type("user")
        if include_flagged_only:
            return [a for a in user_agents if a.include_flag]
        return user_agents

    def get_by_name(self, name: str) -> Agent | None:
        """Get agent by name (case-insensitive)."""
        name_lower = name.lower()
        for agent in self.agents:
            if agent.name.lower() == name_lower:
                return agent
        return None
