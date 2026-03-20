"""Analysis tools — critique, brainstorm, validate, challenge, gaps, alternatives."""

import logging
from typing import Literal

from pydantic import ValidationError

from aicouncil.client import OpenRouterClient
from aicouncil.config import get_config
from aicouncil.exceptions import AiCouncilError
from aicouncil.schemas.responses import (
    AlternativesResult,
    BrainstormResult,
    ChallengeResult,
    CritiqueResult,
    GapsResult,
    ValidationResult,
)
from aicouncil.tools import (
    build_alternatives_prompt,
    build_brainstorm_prompt,
    build_challenge_prompt,
    build_critique_prompt,
    build_gaps_prompt,
    build_validate_prompt,
    get_knowledge_context,
)

logger = logging.getLogger(__name__)


async def critique(
    content: str,
    content_type: Literal[
        "code", "plan", "architecture", "ux", "prd", "story", "epic", "general"
    ] = "general",
    context: str = "",
    severity_threshold: Literal["all", "medium", "high", "critical"] = "all",
    model: str | None = None,
) -> CritiqueResult:
    """
    Critical review finding flaws, risks, improvements in content.
    Supports: code, plans, architecture, UX, PRDs, stories, epics.
    """
    logger.info(f"Critique requested for {content_type} content")

    if not content or not content.strip():
        return CritiqueResult(
            verdict="needs_revision",
            summary="No content provided to critique",
            issues=[],
            strengths=[],
            confidence=0.0,
        )

    try:
        knowledge_context = ""
        if content_type in ["code", "architecture"]:
            knowledge_context = get_knowledge_context(context_type=content_type)

        full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

        prompt = build_critique_prompt(content, content_type, full_context, severity_threshold)

        config = get_config()
        resolved_model = config.resolve_model("critique", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(
                prompt, response_model=CritiqueResult, context=full_context
            )

        if isinstance(result, CritiqueResult):
            logger.info(f"Critique complete: {result.verdict} with {len(result.issues)} issues")
            return result

        return CritiqueResult(
            verdict="needs_revision",
            summary="Review completed with parsing issues",
            issues=[],
            strengths=[],
        )
    except AiCouncilError as e:
        logger.error(f"critique failed: {e}")
        return CritiqueResult(
            verdict="needs_revision",
            summary=f"Analysis failed: {e}",
            issues=[],
            strengths=[],
            confidence=0.0,
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"critique unexpected error: {e}")
        return CritiqueResult(
            verdict="needs_revision",
            summary=f"Unexpected error: {e}",
            issues=[],
            strengths=[],
            confidence=0.0,
        )


async def brainstorm(
    topic: str,
    context: str = "",
    num_ideas: int = 5,
    constraints: list[str] | None = None,
    brainstorm_type: Literal["product", "technical", "ux", "strategy", "general"] = "general",
    model: str | None = None,
) -> BrainstormResult:
    """
    Generate 3-10 ideas with pros/cons on a topic.
    Types: product, technical, ux, strategy, general.
    """
    logger.info(f"Brainstorming requested: {topic}")

    if not topic or not topic.strip():
        return BrainstormResult(
            ideas=[],
            synthesis="No topic provided for brainstorming",
            recommended=None,
        )

    try:
        num_ideas = max(3, min(10, num_ideas))

        full_context = context
        if brainstorm_type == "technical":
            knowledge_context = get_knowledge_context(context_type="code")
            full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

        prompt = build_brainstorm_prompt(
            topic, full_context, num_ideas, constraints, brainstorm_type
        )

        config = get_config()
        resolved_model = config.resolve_model("brainstorm", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(
                prompt, response_model=BrainstormResult, context=full_context
            )

        if isinstance(result, BrainstormResult):
            logger.info(f"Brainstorm complete: {len(result.ideas)} ideas generated")
            return result

        return BrainstormResult(
            ideas=[],
            synthesis="Brainstorming completed with parsing issues",
            recommended=None,
        )
    except AiCouncilError as e:
        logger.error(f"brainstorm failed: {e}")
        return BrainstormResult(
            ideas=[],
            synthesis=f"Brainstorming failed: {e}",
            recommended=None,
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"brainstorm unexpected error: {e}")
        return BrainstormResult(
            ideas=[],
            synthesis=f"Unexpected error: {e}",
            recommended=None,
        )


async def validate(
    content: str,
    validation_type: Literal[
        "completeness", "consistency", "feasibility", "alignment"
    ] = "completeness",
    reference_context: str | None = None,
    model: str | None = None,
) -> ValidationResult:
    """
    Check content for completeness, consistency, feasibility, or alignment.
    Returns pass/fail with score and suggestions.
    """
    logger.info(f"Validation requested: {validation_type}")

    if not content or not content.strip():
        return ValidationResult(
            is_valid=False,
            score=0.0,
            passed_checks=[],
            failed_checks=["No content provided to validate"],
            warnings=[],
            suggestions=[],
        )

    try:
        prompt = build_validate_prompt(content, validation_type, reference_context)

        config = get_config()
        resolved_model = config.resolve_model("validate", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(
                prompt, response_model=ValidationResult, context=reference_context
            )

        if isinstance(result, ValidationResult):
            logger.info(
                f"Validation complete: {'PASS' if result.is_valid else 'FAIL'} ({result.score:.0%})"
            )
            return result

        return ValidationResult(
            is_valid=False,
            score=0.0,
            passed_checks=[],
            failed_checks=["Validation encountered parsing issues"],
            warnings=[],
            suggestions=[],
        )
    except AiCouncilError as e:
        logger.error(f"validate failed: {e}")
        return ValidationResult(
            is_valid=False,
            score=0.0,
            passed_checks=[],
            failed_checks=[f"Validation failed: {e}"],
            warnings=[],
            suggestions=[],
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"validate unexpected error: {e}")
        return ValidationResult(
            is_valid=False,
            score=0.0,
            passed_checks=[],
            failed_checks=[f"Unexpected error: {e}"],
            warnings=[],
            suggestions=[],
        )


async def challenge_assumptions(
    assumptions: list[str],
    domain: str = "software development",
    context: str = "",
    model: str | None = None,
) -> ChallengeResult:
    """
    Stress-test assumptions, identify weaknesses and risks.
    Returns challenged vs validated assumptions with recommendations.
    """
    logger.info(f"Challenging {len(assumptions)} assumptions in {domain}")

    if not assumptions:
        return ChallengeResult(
            challenged=[],
            validated=[],
            summary="No assumptions provided to challenge",
            recommendation="Provide a list of assumptions to analyze",
        )

    try:
        prompt = build_challenge_prompt(assumptions, domain, context)

        config = get_config()
        resolved_model = config.resolve_model("challenge_assumptions", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(prompt, response_model=ChallengeResult, context=context)

        if isinstance(result, ChallengeResult):
            logger.info(
                f"Challenge complete: {len(result.challenged)} challenged, "
                f"{len(result.validated)} validated"
            )
            return result

        return ChallengeResult(
            challenged=[],
            validated=[],
            summary="Challenge analysis encountered issues",
            recommendation="Retry with clearer assumptions",
        )
    except AiCouncilError as e:
        logger.error(f"challenge_assumptions failed: {e}")
        return ChallengeResult(
            challenged=[],
            validated=[],
            summary=f"Challenge failed: {e}",
            recommendation="Retry after resolving the error",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"challenge_assumptions unexpected error: {e}")
        return ChallengeResult(
            challenged=[],
            validated=[],
            summary=f"Unexpected error: {e}",
            recommendation="Retry after resolving the error",
        )


async def find_gaps(
    content: str,
    content_type: Literal[
        "code",
        "plan",
        "architecture",
        "ux",
        "prd",
        "story",
        "epic",
        "requirements",
        "general",
    ] = "general",
    expected_coverage: list[str] | None = None,
    model: str | None = None,
) -> GapsResult:
    """
    Find missing elements, edge cases, blind spots in content.
    Returns gaps list with coverage score.
    """
    logger.info(f"Gap analysis requested for {content_type}")

    if not content or not content.strip():
        return GapsResult(
            gaps=[],
            coverage_score=0.0,
            well_covered=[],
            summary="No content provided for gap analysis",
        )

    try:
        knowledge_context = ""
        if content_type in ["code", "architecture"]:
            knowledge_context = get_knowledge_context(context_type=content_type)

        prompt = build_gaps_prompt(content, content_type, expected_coverage)
        if knowledge_context:
            prompt = f"{knowledge_context}\n\n{prompt}"

        config = get_config()
        resolved_model = config.resolve_model("find_gaps", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(prompt, response_model=GapsResult)

        if isinstance(result, GapsResult):
            logger.info(
                f"Gap analysis complete: {len(result.gaps)} gaps found, "
                f"{result.coverage_score:.0%} coverage"
            )
            return result

        return GapsResult(
            gaps=[],
            coverage_score=0.0,
            well_covered=[],
            summary="Gap analysis encountered issues",
        )
    except AiCouncilError as e:
        logger.error(f"find_gaps failed: {e}")
        return GapsResult(
            gaps=[],
            coverage_score=0.0,
            well_covered=[],
            summary=f"Gap analysis failed: {e}",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"find_gaps unexpected error: {e}")
        return GapsResult(
            gaps=[],
            coverage_score=0.0,
            well_covered=[],
            summary=f"Unexpected error: {e}",
        )


async def propose_alternatives(
    current_approach: str,
    constraints: list[str] | None = None,
    context: str = "",
    num_alternatives: int = 3,
    model: str | None = None,
) -> AlternativesResult:
    """
    Generate 2-5 alternative approaches with comparison matrix.
    Assesses current approach and recommends best option.
    """
    logger.info("Generating alternative approaches")

    if not current_approach or not current_approach.strip():
        return AlternativesResult(
            current_approach_assessment="Unable to assess",
            alternatives=[],
            comparison_matrix={},
            recommendation="No current approach provided to generate alternatives for",
        )

    try:
        num_alternatives = max(2, min(5, num_alternatives))
        constraints = constraints or []

        full_context = context
        if any(
            kw in context.lower() for kw in ["code", "architecture", "technical", "implementation"]
        ):
            knowledge_context = get_knowledge_context(context_type="architecture")
            full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

        prompt = build_alternatives_prompt(
            current_approach, constraints, full_context, num_alternatives
        )

        config = get_config()
        resolved_model = config.resolve_model("propose_alternatives", per_invocation=model)
        async with OpenRouterClient(model=resolved_model, config=config) as client:
            result = await client.generate(
                prompt, response_model=AlternativesResult, context=full_context
            )

        if isinstance(result, AlternativesResult):
            logger.info(f"Generated {len(result.alternatives)} alternatives")
            return result

        return AlternativesResult(
            current_approach_assessment="Unable to assess",
            alternatives=[],
            comparison_matrix={},
            recommendation="Alternative generation encountered issues",
        )
    except AiCouncilError as e:
        logger.error(f"propose_alternatives failed: {e}")
        return AlternativesResult(
            current_approach_assessment="Unable to assess",
            alternatives=[],
            comparison_matrix={},
            recommendation=f"Alternative generation failed: {e}",
        )
    except (ValidationError, TypeError, KeyError, ValueError, AttributeError) as e:
        logger.error(f"propose_alternatives unexpected error: {e}")
        return AlternativesResult(
            current_approach_assessment="Unable to assess",
            alternatives=[],
            comparison_matrix={},
            recommendation=f"Unexpected error: {e}",
        )
