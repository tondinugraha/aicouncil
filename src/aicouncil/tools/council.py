"""Council tools — ai_council, council_speak, and save_council_addendum MCP tools."""

import logging
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from aicouncil.agent_loader import get_agents
from aicouncil.client import OpenRouterClient
from aicouncil.config import get_config
from aicouncil.council.assembler import (
    CouncilAssembler,
    build_classification_prompt,
    extract_available_domains,
)
from aicouncil.council.context import build_context_managed_history
from aicouncil.council.history import write_council_addendum
from aicouncil.council.schemas import (
    AddendumMetadata,
    AddendumSaveResult,
    CompactCouncilResult,
    CouncilAssemblyResult,
    TopicClassification,
)
from aicouncil.council.session import (
    ConversationEntry,
    get_session,
    store_session,
)
from aicouncil.exceptions import AiCouncilError, CouncilError
from aicouncil.roots import get_project_root
from aicouncil.schemas.responses import CouncilSpeakResult
from aicouncil.tools import build_council_speak_prompt

logger = logging.getLogger(__name__)

MAX_ADDENDUM_CONTENT_BYTES = 1_048_576  # 1 MB


async def ai_council(
    topic: str,
    agents: list[str] | None = None,
    council_size: int = 7,
    include_user_agents: bool = True,
    include_wildcard: bool = True,
    model: str | None = None,
) -> CompactCouncilResult:
    """Assemble a multi-agent, multi-model council for deliberation on a topic.

    Classifies the topic, selects relevant agents from the roster,
    assigns models using capability-weighted routing, and returns
    everything the host AI needs to orchestrate the deliberation.

    The assembly result is cached server-side so that subsequent
    council_speak calls only need session_id and agent_name.

    Args:
        topic: The question or topic for the council to deliberate.
        agents: Optional list of agent names to pin in the council.
        council_size: Target number of agents (default: 7).
        include_user_agents: Include user-perspective agents (default: True).
        include_wildcard: Include wildcard cross-domain agents (default: True).
        model: Override model for the classification LLM call.
    """
    session_id = str(uuid.uuid4())
    logger.info("[council:%s] Council session started for topic: %s", session_id, topic[:100])

    try:
        if not topic or not topic.strip():
            raise CouncilError("Topic is required for council assembly")

        config = get_config()

        # Step 1: Classify topic via LLM
        available_domains = extract_available_domains(config)
        if not available_domains:
            raise CouncilError(
                "No capability domains found in config — check capability_weights in config.yaml"
            )

        classification_prompt = build_classification_prompt(topic, available_domains)
        resolved_model = config.resolve_model(tool_name="ai_council", per_invocation=model)

        async with OpenRouterClient(model=resolved_model, config=config) as client:
            classification = await client.generate(
                classification_prompt,
                response_model=TopicClassification,
            )

        if not isinstance(classification, TopicClassification):
            raise CouncilError("Topic classification failed — invalid response from LLM")

        logger.info(
            "[council:%s] Topic classified: domains=%s",
            session_id,
            classification.domains,
        )
        logger.debug(
            "[council:%s] Classification scores: %s",
            session_id,
            classification.domain_scores,
        )

        # Step 2: Load agent roster
        roster = get_agents()

        # Step 3: Assemble council
        assembler = CouncilAssembler(config=config)
        composition = assembler.assemble(
            classification=classification,
            roster=roster,
            session_id=session_id,
            council_size=council_size,
            pinned_agents=agents,
            include_user_agents=include_user_agents,
            include_wildcard=include_wildcard,
        )

        # Step 4: Build orchestration data
        orchestration = assembler.build_orchestration_data(composition)

        logger.info(
            "[council:%s] Council assembled: %d agents", session_id, len(composition.assignments)
        )

        result = CouncilAssemblyResult(
            composition=composition,
            orchestration=orchestration,
        )

        # Step 5: Cache session for council_speak
        store_session(session_id, result)

        return CompactCouncilResult.from_assembly(result)

    except CouncilError as e:
        logger.error("[council:%s] Council error: %s", session_id, e)
        raise
    except AiCouncilError as e:
        logger.error("[council:%s] Council assembly failed: %s", session_id, e)
        raise CouncilError(f"Council assembly failed: {e}") from e
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error("[council:%s] Unexpected error during assembly: %s", session_id, e)
        raise CouncilError(f"Council assembly error: {e}") from e


async def council_speak(
    session_id: str,
    agent_name: str,
    instruction: str = "",
) -> CouncilSpeakResult:
    """Have a single council agent speak in a deliberation round.

    Looks up the agent's persona and model from the cached session,
    includes the full conversation history automatically, and sends
    the prompt to the agent's assigned model. The response is appended
    to the session's conversation history for subsequent calls.

    SEQUENTIAL RULE: The host AI MUST call council_speak ONE AGENT AT A
    TIME. NEVER call multiple council_speak in parallel. Wait for each
    agent's response before calling the next. This applies to ALL rounds
    including Round 1 — each agent builds on the previous speakers.

    DISPLAY RULE: The host AI MUST display the agent's `response` field
    VERBATIM after each call — never summarize, paraphrase, or shorten it.
    Format as: **Agent Name** (model):\\n\\n[exact response text, unchanged]
    \\n\\n**Stance:** [stance text].

    Args:
        session_id: Council session UUID from ai_council assembly.
        agent_name: Name of the agent to speak (must match assembly).
        instruction: Optional chairperson instruction for this turn
            (e.g., 'play devil advocate', 'respond to the Architect').
    """
    session = get_session(session_id)
    agent = session.get_agent(agent_name)
    round_number = session.current_round

    log_prefix = f"[council:{session_id}]"
    logger.info(
        "%s Agent '%s' speaking (round %d, model %s)",
        log_prefix,
        agent_name,
        round_number,
        agent.assigned_model,
    )

    try:
        config = get_config()

        # Context window management: summarize older rounds if history is too large
        managed_history = build_context_managed_history(
            entries=session.conversation_history,
            agent_persona=agent.persona,
            context_window=agent.context_window,
            max_output_tokens=config.max_output_tokens,
        )

        prompt = build_council_speak_prompt(
            agent_persona=agent.persona,
            topic=session.topic,
            round_number=round_number,
            conversation_history=managed_history,
            instruction=instruction,
        )

        async with OpenRouterClient(model=agent.assigned_model, config=config) as client:
            result = await client.generate(
                prompt,
                response_model=CouncilSpeakResult,
                model=agent.assigned_model,
            )

        if isinstance(result, CouncilSpeakResult):
            # Stamp metadata from session (not the LLM's guesses)
            result.agent_name = agent.agent_name
            result.agent_role = agent.agent_role
            result.model = agent.assigned_model

            # Auto-append to session history
            session.add_response(
                ConversationEntry(
                    agent_name=agent.agent_name,
                    agent_role=agent.agent_role,
                    model=agent.assigned_model,
                    round_number=round_number,
                    response=result.response,
                    stance=result.stance,
                    key_points=result.key_points,
                )
            )

            logger.info(
                "%s Agent '%s' responded: stance='%s'",
                log_prefix,
                agent_name,
                result.stance[:80],
            )
            return result

        # Fallback: LLM returned something unexpected
        logger.warning("%s Agent '%s' returned non-structured response", log_prefix, agent_name)
        return CouncilSpeakResult(
            agent_name=agent.agent_name,
            agent_role=agent.agent_role,
            model=agent.assigned_model,
            response=str(result) if result else "Agent failed to respond.",
            stance="unclear",
            key_points=[],
        )

    except CouncilError:
        raise
    except AiCouncilError as e:
        logger.error("%s Agent '%s' failed: %s", log_prefix, agent_name, e)
        raise CouncilError(f"Agent '{agent_name}' failed to respond: {e}") from e
    except (ValidationError, TypeError, KeyError, ValueError) as e:
        logger.error("%s Agent '%s' unexpected error: %s", log_prefix, agent_name, e)
        raise CouncilError(f"Agent '{agent_name}' response error: {e}") from e


async def save_council_addendum(
    session_id: str,
    addendum_content: str,
) -> AddendumSaveResult:
    """Save a council addendum as a timestamped markdown file and return it for inline display.

    Pulls topic, agents, and model assignments from the cached session —
    only session_id and the addendum narrative are needed.

    Args:
        session_id: Council session UUID from the assembly result.
        addendum_content: Full addendum narrative written by the host AI.
    """
    logger.info("[council:%s] Saving addendum to history", session_id)

    try:
        session = get_session(session_id)

        content_size = len(addendum_content.encode("utf-8"))
        if content_size > MAX_ADDENDUM_CONTENT_BYTES:
            raise CouncilError(
                f"Addendum content exceeds maximum size: {content_size} bytes "
                f"(limit: {MAX_ADDENDUM_CONTENT_BYTES} bytes)"
            )

        # Extract metadata from cached session
        agents = [a.agent_name for a in session.assembly.composition.assignments]
        model_assignments = {
            a.agent_name: a.assigned_model for a in session.assembly.composition.assignments
        }

        timestamp = datetime.now(tz=UTC).isoformat()
        metadata = AddendumMetadata(
            session_id=session_id,
            topic=session.topic,
            agents=agents,
            model_assignments=model_assignments,
            timestamp=timestamp,
        )

        project_root = get_project_root()
        file_path = write_council_addendum(metadata, addendum_content, project_root=project_root)
        relative_path = file_path.relative_to(project_root)

        logger.info("[council:%s] Addendum saved to %s", session_id, relative_path)

        return AddendumSaveResult(
            file_path=str(relative_path),
            addendum_content=addendum_content,
            metadata=metadata,
        )

    except CouncilError:
        raise
    except (ValidationError, TypeError, ValueError) as e:
        logger.error("[council:%s] Failed to save addendum: %s", session_id, e)
        raise CouncilError(f"Failed to save council addendum: {e}") from e
