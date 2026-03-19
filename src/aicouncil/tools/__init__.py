"""MCP Tools for AI Council tools."""

# Tools are registered via decorators in server.py
# This module provides helper functions used by the tools

from aicouncil.prompts.base import BasePrompts
from aicouncil.prompts.workflows import WorkflowPrompts


def build_critique_prompt(
    content: str,
    content_type: str,
    context: str,
    severity_threshold: str = "all",
) -> str:
    """Build a critique prompt with workflow-aware enhancements."""
    severity_filter = BasePrompts.SEVERITY_FILTERS.get(
        severity_threshold, BasePrompts.SEVERITY_FILTERS["all"]
    )

    content_guidance = WorkflowPrompts.get_content_guidance(content_type)

    prompt = BasePrompts.CRITIQUE.format(
        content_type=content_type,
        content=content,
        context=f"{context}\n\n{content_guidance}",
        severity_filter=severity_filter,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_brainstorm_prompt(
    topic: str,
    context: str,
    num_ideas: int = 5,
    constraints: list[str] | None = None,
    brainstorm_type: str = "general",
) -> str:
    """Build a brainstorming prompt."""
    constraints_text = ""
    if constraints:
        constraints_text = "CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in constraints)

    type_context = WorkflowPrompts.get_brainstorm_context(brainstorm_type)
    full_context = f"{context}\n\n{type_context}" if type_context else context

    prompt = BasePrompts.BRAINSTORM.format(
        topic=topic,
        context=full_context,
        constraints=constraints_text,
        num_ideas=num_ideas,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_validate_prompt(
    content: str,
    validation_type: str,
    reference_context: str | None = None,
) -> str:
    """Build a validation prompt."""
    reference_section = ""
    if reference_context:
        reference_section = f"REFERENCE MATERIAL:\n```\n{reference_context}\n```"

    validation_criteria = BasePrompts.VALIDATION_CRITERIA.get(
        validation_type, BasePrompts.VALIDATION_CRITERIA["completeness"]
    )

    prompt = BasePrompts.VALIDATE.format(
        validation_type=validation_type,
        content=content,
        reference_section=reference_section,
        validation_criteria=validation_criteria,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_challenge_prompt(
    assumptions: list[str],
    domain: str,
    context: str,
) -> str:
    """Build a challenge assumptions prompt."""
    assumptions_text = "\n".join(f"{i + 1}. {a}" for i, a in enumerate(assumptions))

    prompt = BasePrompts.CHALLENGE.format(
        assumptions=assumptions_text,
        domain=domain,
        context=context,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_gaps_prompt(
    content: str,
    content_type: str,
    expected_coverage: list[str] | None = None,
) -> str:
    """Build a gap analysis prompt."""
    coverage_section = ""
    if expected_coverage:
        coverage_section = "EXPECTED COVERAGE (check if these are addressed):\n" + "\n".join(
            f"- {c}" for c in expected_coverage
        )

    content_guidance = WorkflowPrompts.get_content_guidance(content_type)

    prompt = BasePrompts.FIND_GAPS.format(
        content=content,
        content_type=content_type,
        expected_coverage_section=coverage_section,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}\n\n{content_guidance}"


def build_alternatives_prompt(
    current_approach: str,
    constraints: list[str],
    context: str,
    num_alternatives: int = 3,
) -> str:
    """Build an alternatives generation prompt."""
    constraints_text = "\n".join(f"- {c}" for c in constraints) if constraints else "None specified"

    prompt = BasePrompts.ALTERNATIVES.format(
        current_approach=current_approach,
        constraints=constraints_text,
        context=context,
        num_alternatives=num_alternatives,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_research_prompt(
    query: str,
    context: str,
    depth: str = "thorough",
) -> str:
    """Build a research assistance prompt."""
    depth_config = WorkflowPrompts.get_research_depth(depth)

    prompt = BasePrompts.RESEARCH.format(
        query=query,
        context=context,
        depth=depth_config,
    )

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"


def build_document_research_prompt(
    focus_areas: list[str] | None = None,
    research_depth: str = "thorough",
    extract_citations: bool = True,
) -> str:
    """Build a document research and analysis prompt."""
    focus_section = ""
    if focus_areas:
        focus_section = "FOCUS AREAS:\nPay special attention to:\n" + "\n".join(
            f"- {area}" for area in focus_areas
        )

    depth_guidance = {
        "quick": "Provide a concise overview with key takeaways only.",
        "thorough": "Conduct detailed analysis of main points, arguments, and findings.",
        "exhaustive": (
            "Perform comprehensive deep-dive analysis covering all aspects, "
            "nuances, and implications."
        ),
    }.get(
        research_depth,
        "Conduct detailed analysis of main points, arguments, and findings.",
    )

    citations_guidance = ""
    if extract_citations:
        citations_guidance = (
            "Extract and list any key citations or references mentioned in the document."
        )

    prompt = f"""Analyze this document thoroughly and provide comprehensive research insights.

{depth_guidance}

{focus_section}

Your analysis should include:

1. **Document Overview**
   - Title and document type
   - Executive summary of the content

2. **Key Insights**
   - Extract the most important insights, categorized by type
     (main arguments, methodology, findings, etc.)
   - Indicate importance level for each insight

3. **Main Arguments & Findings**
   - Identify the main arguments or themes
   - List key findings or conclusions

4. **Methodology** (if applicable)
   - Describe the research methodology or approach used

5. **Critical Analysis**
   - Strengths of the document
   - Limitations or weaknesses
   - Questions raised that need further investigation

6. **Practical Applications**
   - How can this knowledge be applied?
   - Related topics to explore
   - {citations_guidance}

Provide your analysis in a structured format that can be saved as a comprehensive research document.
"""

    return f"{BasePrompts.SYSTEM_PERSONA}\n\n{prompt}"
