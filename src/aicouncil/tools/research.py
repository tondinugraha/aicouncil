"""Research tools — research_assist, research_document."""

import logging
from pathlib import Path
from typing import Literal

from aicouncil.client import OpenRouterClient
from aicouncil.config import get_config
from aicouncil.exceptions import AiCouncilError
from aicouncil.schemas.responses import DocumentResearchResult, ResearchResult
from aicouncil.tools import build_document_research_prompt, build_research_prompt

logger = logging.getLogger(__name__)


async def research_assist(
    query: str,
    context: str = "",
    depth: Literal["quick", "thorough", "exhaustive"] = "thorough",
    model: str | None = None,
) -> ResearchResult:
    """
    Research any topic with configurable depth (quick/thorough/exhaustive).
    Returns findings, knowledge gaps, and next steps.
    """
    logger.info(f"Research assistance requested ({depth}): {query[:50]}...")

    try:
        prompt = build_research_prompt(query, context, depth)

        config = get_config()
        resolved_model = config.resolve_model("research_assist", per_invocation=model)
        client = OpenRouterClient(model=resolved_model, config=config)

        result = await client.generate(prompt, response_model=ResearchResult, context=context)

        if isinstance(result, ResearchResult):
            logger.info(f"Research complete: {len(result.findings)} findings")
            return result

        return ResearchResult(
            findings=[],
            summary="Research encountered issues",
            knowledge_gaps=["Unable to complete research"],
            next_steps=["Retry with more specific query"],
            confidence_overall="low",
        )
    except AiCouncilError as e:
        logger.error(f"research_assist failed: {e}")
        return ResearchResult(
            findings=[],
            summary=f"Research failed: {e}",
            knowledge_gaps=[],
            next_steps=[],
            confidence_overall="low",
        )
    except Exception as e:
        logger.error(f"research_assist unexpected error: {e}")
        return ResearchResult(
            findings=[],
            summary=f"Unexpected error: {e}",
            knowledge_gaps=[],
            next_steps=[],
            confidence_overall="low",
        )


async def research_document(
    document_path: str,
    output_path: str,
    focus_areas: list[str] | None = None,
    research_depth: Literal["quick", "thorough", "exhaustive"] = "thorough",
    extract_citations: bool = True,
    save_to_knowledge: bool = True,
    model: str | None = None,
) -> DocumentResearchResult:
    """
    Analyze a document (PDF, txt, md, etc.) and create comprehensive research analysis.
    Reads document locally, sends content to model, and saves analysis to output file.
    Optionally saves key insights to knowledge base.
    """
    logger.info(f"Document research requested: {document_path} -> {output_path}")

    try:
        doc_path = Path(document_path)
        if not doc_path.exists():
            return DocumentResearchResult(
                document_title="Error",
                document_type="unknown",
                executive_summary=f"Document not found: {document_path}",
                key_insights=[],
                output_file_path=None,
            )

        prompt = build_document_research_prompt(
            focus_areas=focus_areas,
            research_depth=research_depth,
            extract_citations=extract_citations,
        )

        config = get_config()
        resolved_model = config.resolve_model("research_document", per_invocation=model)
        client = OpenRouterClient(model=resolved_model, config=config)

        result = await client.generate_with_file(
            file_path=str(doc_path.absolute()),
            prompt=prompt,
            response_model=DocumentResearchResult,
        )

        if isinstance(result, DocumentResearchResult):
            markdown_content = _format_document_research(result, document_path)

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(markdown_content, encoding="utf-8")
            result.output_file_path = str(output_path)

            if save_to_knowledge:
                from aicouncil.memory import KnowledgeLearner

                learner = KnowledgeLearner()
                learned_ids = []
                for insight in result.key_insights:
                    if insight.importance in ["critical", "high"]:
                        entry_id = learner.learn_explicit(
                            content=f"{insight.category}: {insight.content}",
                            knowledge_type="insight",
                            tags=[result.document_type, "research", insight.category],
                            references=[document_path],
                        )
                        learned_ids.append(entry_id)
                result.knowledge_learned = learned_ids

            logger.info(f"Document research complete: saved to {output_path}")
            return result

        return DocumentResearchResult(
            document_title=doc_path.stem,
            document_type="unknown",
            executive_summary="Analysis completed with parsing issues",
            key_insights=[],
            output_file_path=None,
        )

    except AiCouncilError as e:
        logger.error(f"Document research failed: {e}")
        return DocumentResearchResult(
            document_title="Error",
            document_type="unknown",
            executive_summary=f"Analysis failed: {e}",
            key_insights=[],
            output_file_path=None,
        )
    except Exception as e:
        logger.exception(f"Unexpected error in research_document: {e}")
        return DocumentResearchResult(
            document_title="Error",
            document_type="unknown",
            executive_summary=f"Unexpected error: {e}",
            key_insights=[],
            output_file_path=None,
        )


def _format_document_research(result: DocumentResearchResult, document_path: str) -> str:
    """Format document research result as markdown."""
    parts = [
        f"# {result.document_title}\n",
        f"**Document Type:** {result.document_type}\n",
        f"## Executive Summary\n\n{result.executive_summary}\n",
        "## Key Insights\n",
    ]

    for insight in result.key_insights:
        parts.append(
            f"### {insight.category.replace('_', ' ').title()} "
            f"[{insight.importance.upper()}]\n\n{insight.content}\n"
        )
        if insight.page_reference:
            parts.append(f"*Reference: {insight.page_reference}*\n")

    parts.append("## Main Arguments\n")
    for arg in result.main_arguments:
        parts.append(f"- {arg}\n")

    parts.append("\n## Key Findings\n")
    for finding in result.findings:
        parts.append(f"- {finding}\n")

    if result.methodology:
        parts.append(f"\n## Methodology\n\n{result.methodology}\n")

    parts.append("\n## Critical Analysis\n\n### Strengths\n")
    for strength in result.strengths:
        parts.append(f"- {strength}\n")

    parts.append("\n### Limitations\n")
    for limitation in result.limitations:
        parts.append(f"- {limitation}\n")

    parts.append("\n## Questions for Further Research\n")
    for question in result.questions_raised:
        parts.append(f"- {question}\n")

    parts.append("\n## Practical Applications\n")
    for application in result.practical_applications:
        parts.append(f"- {application}\n")

    if result.related_topics:
        parts.append("\n## Related Topics to Explore\n")
        for topic in result.related_topics:
            parts.append(f"- {topic}\n")

    if result.citations_mentioned:
        parts.append("\n## Key Citations\n")
        for citation in result.citations_mentioned:
            parts.append(f"- {citation}\n")

    parts.append(f"\n---\n*Analysis generated by AI Council on {Path(document_path).name}*\n")

    return "\n".join(parts)
