"""Council tool — ai_council MCP tool for multi-agent council assembly."""

import logging
import uuid

from pydantic import ValidationError

from aicouncil.agent_loader import get_agents
from aicouncil.client import OpenRouterClient
from aicouncil.config import get_config
from aicouncil.council.assembler import (
    CouncilAssembler,
    build_classification_prompt,
    extract_available_domains,
)
from aicouncil.council.schemas import CouncilAssemblyResult, TopicClassification
from aicouncil.exceptions import AiCouncilError, CouncilError

logger = logging.getLogger(__name__)


async def ai_council(
    topic: str,
    agents: list[str] | None = None,
    council_size: int = 7,
    include_user_agents: bool = True,
    include_wildcard: bool = True,
    model: str | None = None,
) -> CouncilAssemblyResult:
    """Assemble a multi-agent, multi-model council for deliberation on a topic.

    Classifies the topic, selects relevant agents from the roster,
    assigns models using capability-weighted routing, and returns
    everything the host AI needs to orchestrate the deliberation.

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

        return CouncilAssemblyResult(
            composition=composition,
            orchestration=orchestration,
        )

    except CouncilError as e:
        logger.error("[council:%s] Council error: %s", session_id, e)
        raise
    except AiCouncilError as e:
        logger.error("[council:%s] Council assembly failed: %s", session_id, e)
        raise CouncilError(f"Council assembly failed: {e}") from e
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error("[council:%s] Unexpected error during assembly: %s", session_id, e)
        raise CouncilError(f"Council assembly error: {e}") from e
