"""In-memory session store for active council deliberations.

Caches assembly results so that council_speak only needs a session_id
and agent_name — no need to re-send personas, models, or history on
every call. Lives as long as the MCP server process.
"""

import logging
from dataclasses import dataclass, field

from aicouncil.council.schemas import AgentAssignment, CouncilAssemblyResult
from aicouncil.exceptions import CouncilError

logger = logging.getLogger(__name__)

# Maximum sessions to keep in memory (LRU-style eviction)
MAX_SESSIONS = 50


@dataclass
class ConversationEntry:
    """A single agent statement in the deliberation history."""

    agent_name: str
    agent_role: str
    model: str
    round_number: int
    response: str
    stance: str
    key_points: list[str]


@dataclass
class CouncilSession:
    """Active council session with cached assembly and conversation history."""

    session_id: str
    assembly: CouncilAssemblyResult
    conversation_history: list[ConversationEntry] = field(default_factory=list)
    current_round: int = 1

    @property
    def topic(self) -> str:
        return self.assembly.composition.topic

    def get_agent(self, agent_name: str) -> AgentAssignment:
        """Look up an agent by name from the assembly."""
        for assignment in self.assembly.composition.assignments:
            if assignment.agent_name == agent_name:
                return assignment
        available = [a.agent_name for a in self.assembly.composition.assignments]
        raise CouncilError(
            f"Agent '{agent_name}' not found in session. Available agents: {available}"
        )

    def get_history_for_prompt(self) -> list[dict[str, str]]:
        """Return conversation history formatted for the prompt builder."""
        return [
            {
                "agent_name": entry.agent_name,
                "agent_role": entry.agent_role,
                "response": entry.response,
            }
            for entry in self.conversation_history
        ]

    def add_response(self, entry: ConversationEntry) -> None:
        """Append an agent response to the conversation history."""
        self.conversation_history.append(entry)
        logger.debug(
            "[council:%s] History now has %d entries",
            self.session_id,
            len(self.conversation_history),
        )


# ============================================================================
# Module-level session store (singleton, lives with the MCP server process)
# ============================================================================

_sessions: dict[str, CouncilSession] = {}


def store_session(session_id: str, assembly: CouncilAssemblyResult) -> CouncilSession:
    """Cache a council assembly result for later council_speak calls."""
    # Evict oldest session if at capacity
    if len(_sessions) >= MAX_SESSIONS:
        oldest_key = next(iter(_sessions))
        logger.info("Evicting oldest council session: %s", oldest_key)
        del _sessions[oldest_key]

    session = CouncilSession(session_id=session_id, assembly=assembly)
    _sessions[session_id] = session
    logger.info(
        "[council:%s] Session cached (%d active sessions)",
        session_id,
        len(_sessions),
    )
    return session


def get_session(session_id: str) -> CouncilSession:
    """Retrieve a cached council session by ID."""
    session = _sessions.get(session_id)
    if session is None:
        raise CouncilError(
            f"Council session '{session_id}' not found. "
            f"Call ai_council first to assemble the council."
        )
    return session


def clear_session(session_id: str) -> None:
    """Remove a session from the cache."""
    _sessions.pop(session_id, None)


def clear_all_sessions() -> None:
    """Clear all cached sessions (for testing)."""
    _sessions.clear()
