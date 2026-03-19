"""
AI Council - Main entry point.

Multi-model deliberation MCP server routing through OpenRouter.
"""

import logging
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from aicouncil.client import get_client
from aicouncil.schemas.responses import (
    AlternativesResult,
    BrainstormResult,
    ChallengeResult,
    CodebaseScanResult,
    CritiqueResult,
    DependencyAnalysisResult,
    DocumentResearchResult,
    FileAnalysisResult,
    GapsResult,
    MemoryResult,
    RecallResult,
    ResearchResult,
    ValidationResult,
)
from aicouncil.tools import (
    build_alternatives_prompt,
    build_brainstorm_prompt,
    build_challenge_prompt,
    build_critique_prompt,
    build_document_research_prompt,
    build_gaps_prompt,
    build_research_prompt,
    build_validate_prompt,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "aicouncil",
    instructions="AI partner for brainstorming, critique, and validation",
)


# ============================================================================
# Helper Functions
# ============================================================================


def get_project_root() -> Path:
    """Get the project root directory."""
    from aicouncil.scanner import ProjectDetector

    detector = ProjectDetector()
    info = detector.detect()
    return Path(info.root)


def get_knowledge_context(
    file_paths: list[str] | None = None,
    tags: list[str] | None = None,
    context_type: str = "general",
) -> str:
    """Get relevant knowledge for prompt context."""
    try:
        from aicouncil.memory import KnowledgeRetriever

        retriever = KnowledgeRetriever()

        if context_type == "architecture":
            entries = retriever.get_context_for_architecture()
        elif context_type == "code":
            entries = retriever.get_context_for_code()
        elif context_type == "scan":
            entries = retriever.get_context_for_scan(file_paths=file_paths)
        else:
            entries = retriever.store.get_for_context(file_paths=file_paths, tags=tags)

        return retriever.format_for_prompt(entries)
    except Exception as e:
        logger.warning(f"Failed to load knowledge context: {e}")
        return ""


# ============================================================================
# Analysis Tools
# ============================================================================


@mcp.tool()
async def critique(
    content: str,
    content_type: Literal[
        "code", "plan", "architecture", "ux", "prd", "story", "epic", "general"
    ] = "general",
    context: str = "",
    severity_threshold: Literal["all", "medium", "high", "critical"] = "all",
) -> CritiqueResult:
    """
    Critical review finding flaws, risks, improvements in content.
    Supports: code, plans, architecture, UX, PRDs, stories, epics.
    """
    logger.info(f"Critique requested for {content_type} content")

    knowledge_context = ""
    if content_type in ["code", "architecture"]:
        knowledge_context = get_knowledge_context(context_type=content_type)

    full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

    prompt = build_critique_prompt(content, content_type, full_context, severity_threshold)
    client = get_client("reasoning")

    result = await client.generate(prompt, response_model=CritiqueResult, context=full_context)

    if isinstance(result, CritiqueResult):
        logger.info(f"Critique complete: {result.verdict} with {len(result.issues)} issues")
        return result

    return CritiqueResult(
        verdict="needs_revision",
        summary="Review completed with parsing issues",
        issues=[],
        strengths=[],
    )


@mcp.tool()
async def brainstorm(
    topic: str,
    context: str = "",
    num_ideas: int = 5,
    constraints: list[str] | None = None,
    brainstorm_type: Literal["product", "technical", "ux", "strategy", "general"] = "general",
) -> BrainstormResult:
    """
    Generate 3-10 ideas with pros/cons on a topic.
    Types: product, technical, ux, strategy, general.
    """
    logger.info(f"Brainstorming requested: {topic}")

    num_ideas = max(3, min(10, num_ideas))

    full_context = context
    if brainstorm_type == "technical":
        knowledge_context = get_knowledge_context(context_type="code")
        full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

    prompt = build_brainstorm_prompt(topic, full_context, num_ideas, constraints, brainstorm_type)
    client = get_client("fast")

    result = await client.generate(prompt, response_model=BrainstormResult, context=full_context)

    if isinstance(result, BrainstormResult):
        logger.info(f"Brainstorm complete: {len(result.ideas)} ideas generated")
        return result

    return BrainstormResult(
        ideas=[],
        synthesis="Brainstorming completed with parsing issues",
        recommended=None,
    )


@mcp.tool()
async def validate(
    content: str,
    validation_type: Literal[
        "completeness", "consistency", "feasibility", "alignment"
    ] = "completeness",
    reference_context: str | None = None,
) -> ValidationResult:
    """
    Check content for completeness, consistency, feasibility, or alignment.
    Returns pass/fail with score and suggestions.
    """
    logger.info(f"Validation requested: {validation_type}")

    prompt = build_validate_prompt(content, validation_type, reference_context)
    client = get_client("fast")

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


@mcp.tool()
async def challenge_assumptions(
    assumptions: list[str],
    domain: str = "software development",
    context: str = "",
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

    prompt = build_challenge_prompt(assumptions, domain, context)
    client = get_client("reasoning")

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


@mcp.tool()
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
) -> GapsResult:
    """
    Find missing elements, edge cases, blind spots in content.
    Returns gaps list with coverage score.
    """
    logger.info(f"Gap analysis requested for {content_type}")

    knowledge_context = ""
    if content_type in ["code", "architecture"]:
        knowledge_context = get_knowledge_context(context_type=content_type)

    prompt = build_gaps_prompt(content, content_type, expected_coverage)
    if knowledge_context:
        prompt = f"{knowledge_context}\n\n{prompt}"

    client = get_client("reasoning")

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


@mcp.tool()
async def propose_alternatives(
    current_approach: str,
    constraints: list[str] | None = None,
    context: str = "",
    num_alternatives: int = 3,
) -> AlternativesResult:
    """
    Generate 2-5 alternative approaches with comparison matrix.
    Assesses current approach and recommends best option.
    """
    logger.info("Generating alternative approaches")

    num_alternatives = max(2, min(5, num_alternatives))
    constraints = constraints or []

    full_context = context
    if any(kw in context.lower() for kw in ["code", "architecture", "technical", "implementation"]):
        knowledge_context = get_knowledge_context(context_type="architecture")
        full_context = f"{context}\n\n{knowledge_context}" if knowledge_context else context

    prompt = build_alternatives_prompt(
        current_approach, constraints, full_context, num_alternatives
    )
    client = get_client("reasoning")

    result = await client.generate(prompt, response_model=AlternativesResult, context=full_context)

    if isinstance(result, AlternativesResult):
        logger.info(f"Generated {len(result.alternatives)} alternatives")
        return result

    return AlternativesResult(
        current_approach_assessment="Unable to assess",
        alternatives=[],
        comparison_matrix={},
        recommendation="Alternative generation encountered issues",
    )


@mcp.tool()
async def research_assist(
    query: str,
    context: str = "",
    depth: Literal["quick", "thorough", "exhaustive"] = "thorough",
) -> ResearchResult:
    """
    Research any topic with configurable depth (quick/thorough/exhaustive).
    Returns findings, knowledge gaps, and next steps.
    """
    logger.info(f"Research assistance requested ({depth}): {query[:50]}...")

    prompt = build_research_prompt(query, context, depth)
    client = get_client("reasoning")

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


@mcp.tool()
async def research_document(
    document_path: str,
    output_path: str,
    focus_areas: list[str] | None = None,
    research_depth: Literal["quick", "thorough", "exhaustive"] = "thorough",
    extract_citations: bool = True,
    save_to_knowledge: bool = True,
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

        client = get_client("reasoning")

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

    except Exception as e:
        logger.error(f"Document research failed: {e}")
        return DocumentResearchResult(
            document_title="Error",
            document_type="unknown",
            executive_summary=f"Analysis failed: {str(e)}",
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


# ============================================================================
# Codebase Scanning Tools
# ============================================================================


@mcp.tool()
async def scan_codebase(
    path: str | None = None,
    scan_type: Literal["overview", "full", "security"] = "overview",
    file_patterns: list[str] | None = None,
    max_files: int = 50,
    include_tests: bool = False,
) -> CodebaseScanResult:
    """
    Analyze codebase structure, issues, architecture (max 50 files default).
    Scan types: overview, full, security. Auto-loads project knowledge.
    """
    logger.info(f"Codebase scan requested: {scan_type} scan of {path or 'entire project'}")

    try:
        from aicouncil.memory import KnowledgeLearner
        from aicouncil.scanner import ContextBuilder

        builder = ContextBuilder(path)
        project_context = builder.build_project_context(
            scan_type=scan_type,
            include_patterns=file_patterns,
            include_tests=include_tests,
            max_files=max_files,
        )

        knowledge_context = get_knowledge_context(
            context_type="scan",
            file_paths=project_context.all_files[:20],
        )

        prompt = f"""Analyze this codebase and provide a comprehensive review.

## Project Information
- Name: {project_context.project.name}
- Type: {project_context.project.type}
- Framework: {project_context.project.framework or "None detected"}
- Total Files: {project_context.total_files}
- Total Lines: {project_context.total_lines}
- Languages: {project_context.languages}

## Key Files
{chr(10).join(f"- {f.path}: {f.summary}" for f in project_context.key_files[:15])}

## Dependencies
{", ".join(project_context.dependencies[:20]) or "None detected"}

{knowledge_context}

## File Contents
{
            chr(10).join(
                f"### {f.path}{chr(10)}```{chr(10)}"
                f"{f.content[:2000] if f.content else 'No content'}{chr(10)}```"
                for f in project_context.key_files[:10]
                if f.content
            )
        }

Provide:
1. Architecture summary
2. Code quality issues found
3. Security concerns (if any)
4. Recommendations for improvement
"""

        client = get_client("reasoning")
        result = await client.generate(prompt, response_model=CodebaseScanResult)

        if isinstance(result, CodebaseScanResult):
            learner = KnowledgeLearner()
            learned_ids = learner.learn_from_scan(result.model_dump(), scan_type)
            result.knowledge_learned = learned_ids
            return result

        return CodebaseScanResult(
            project_name=project_context.project.name,
            project_type=project_context.project.type,
            framework=project_context.project.framework,
            total_files=project_context.total_files,
            total_lines=project_context.total_lines,
            languages=project_context.languages,
            architecture_summary="Scan completed with parsing issues",
            dependencies=project_context.dependencies,
        )

    except Exception as e:
        logger.error(f"Codebase scan failed: {e}")
        return CodebaseScanResult(
            project_name="Unknown",
            project_type="unknown",
            total_files=0,
            total_lines=0,
            architecture_summary=f"Scan failed: {str(e)}",
        )


@mcp.tool()
async def critique_file(
    file_path: str,
    include_related: bool = True,
    related_depth: int = 1,
) -> FileAnalysisResult:
    """
    Deep code review of a file with imported/related files context.
    related_depth: 1-3 levels of import following.
    """
    logger.info(f"File critique requested: {file_path}")

    try:
        from aicouncil.memory import KnowledgeLearner
        from aicouncil.scanner import ContextBuilder

        builder = ContextBuilder()
        main_context, related_contexts = builder.build_file_context(
            file_path,
            include_related=include_related,
            related_depth=min(related_depth, 3),
        )

        knowledge_context = get_knowledge_context(
            file_paths=[file_path] + [r.path for r in related_contexts],
            context_type="code",
        )

        related_section = ""
        if related_contexts:
            related_section = "\n## Related Files\n" + "\n".join(
                f"### {r.path}\n```\n{r.content[:1000] if r.content else 'No content'}\n```"
                for r in related_contexts[:5]
            )

        prompt = f"""Analyze this code file in detail.

## Main File: {main_context.path}
{main_context.summary}

### Code
```
{main_context.content or "Content not available"}
```

{related_section}

{knowledge_context}

Provide:
1. Summary of what this file does
2. Code quality issues
3. Patterns identified (good and bad)
4. Specific recommendations
"""

        client = get_client("reasoning")
        result = await client.generate(prompt, response_model=FileAnalysisResult)

        if isinstance(result, FileAnalysisResult):
            result.file_path = file_path
            result.related_files = [r.path for r in related_contexts]

            if main_context.structure:
                learner = KnowledgeLearner()
                structure_dict = (
                    main_context.structure.model_dump()
                    if hasattr(main_context.structure, "model_dump")
                    else {}
                )
                learned_ids = learner.learn_from_file_analysis(
                    file_path, structure_dict, result.model_dump()
                )
                result.knowledge_learned = learned_ids

            return result

        return FileAnalysisResult(
            file_path=file_path,
            file_summary="Analysis completed with parsing issues",
            related_files=[r.path for r in related_contexts],
        )

    except Exception as e:
        logger.error(f"File critique failed: {e}")
        return FileAnalysisResult(
            file_path=file_path,
            file_summary=f"Analysis failed: {str(e)}",
        )


@mcp.tool()
async def analyze_dependencies(
    path: str | None = None,
) -> DependencyAnalysisResult:
    """
    Map module dependencies, find circular deps, identify hub/isolated modules.
    """
    logger.info(f"Dependency analysis requested for {path or 'entire project'}")

    try:
        from aicouncil.scanner import CodeAnalyzer, FileWalker, ProjectDetector
        from aicouncil.schemas.responses import DependencyNode

        detector = ProjectDetector(path)
        project_info = detector.detect()
        root = Path(project_info.root)

        walker = FileWalker(root)
        analyzer = CodeAnalyzer(root)

        internal_modules = []
        external_deps: set[str] = set()
        import_map: dict[str, list[str]] = {}

        for file_info in walker.get_code_files()[:100]:
            structure = analyzer.analyze_file(root / file_info.path)

            local_imports = []
            for imp in structure.imports:
                if imp.is_local:
                    local_imports.append(imp.module)
                else:
                    external_deps.add(imp.module.split(".")[0])

            import_map[file_info.path] = local_imports

        imported_by_map: dict[str, list[str]] = {}
        for fp, imports in import_map.items():
            for imp in imports:
                if imp not in imported_by_map:
                    imported_by_map[imp] = []
                imported_by_map[imp].append(fp)

        for fp, imports in import_map.items():
            internal_modules.append(
                DependencyNode(
                    name=Path(fp).stem,
                    path=fp,
                    imports=imports,
                    imported_by=imported_by_map.get(fp, []),
                )
            )

        hub_modules = [m.path for m in internal_modules if len(m.imports) + len(m.imported_by) > 5]
        isolated_modules = [
            m.path for m in internal_modules if len(m.imports) == 0 and len(m.imported_by) == 0
        ]

        circular: list[list[str]] = []
        for fp, imports in import_map.items():
            for imp in imports:
                if imp in import_map and fp in import_map.get(imp, []):
                    pair = sorted([fp, imp])
                    if pair not in circular:
                        circular.append(pair)

        return DependencyAnalysisResult(
            total_modules=len(internal_modules),
            external_dependencies=sorted(external_deps)[:50],
            internal_modules=internal_modules[:50],
            circular_dependencies=circular,
            hub_modules=hub_modules[:10],
            isolated_modules=isolated_modules[:10],
            recommendations=[
                (
                    f"Found {len(circular)} circular dependencies - consider refactoring"
                    if circular
                    else "No circular dependencies found"
                ),
                (
                    f"{len(hub_modules)} hub modules detected - may need decomposition"
                    if hub_modules
                    else "No overly connected modules"
                ),
                (
                    f"{len(isolated_modules)} isolated modules - verify they're used"
                    if isolated_modules
                    else "All modules are connected"
                ),
            ],
        )

    except Exception as e:
        logger.error(f"Dependency analysis failed: {e}")
        return DependencyAnalysisResult(
            total_modules=0,
            recommendations=[f"Analysis failed: {str(e)}"],
        )


# ============================================================================
# Memory/Knowledge Tools
# ============================================================================


@mcp.tool()
async def remember(
    content: str,
    knowledge_type: Literal[
        "pattern", "architecture", "relation", "issue", "convention", "insight"
    ] = "insight",
    tags: list[str] | None = None,
    references: list[str] | None = None,
) -> MemoryResult:
    """
    Save knowledge to project memory.
    Types: pattern, architecture, relation, issue, convention, insight.
    """
    logger.info(f"Saving knowledge: {knowledge_type}")

    try:
        from aicouncil.memory import KnowledgeLearner

        learner = KnowledgeLearner()
        entry_id = learner.learn_explicit(
            content=content,
            knowledge_type=knowledge_type,
            tags=tags,
            references=references,
        )

        return MemoryResult(
            success=True,
            entry_id=entry_id,
            message=f"Knowledge saved as {knowledge_type} (ID: {entry_id})",
        )

    except Exception as e:
        logger.error(f"Failed to save knowledge: {e}")
        return MemoryResult(
            success=False,
            message=f"Failed to save: {str(e)}",
        )


@mcp.tool()
async def recall(
    query: str,
    knowledge_type: Literal["pattern", "architecture", "relation", "issue", "convention", "insight"]
    | None = None,
    limit: int = 10,
) -> RecallResult:
    """
    Search project memory by query. Optional filter by knowledge_type.
    """
    logger.info(f"Recalling knowledge: {query}")

    try:
        from aicouncil.memory import KnowledgeRetriever, KnowledgeStore

        store = KnowledgeStore()
        retriever = KnowledgeRetriever()

        entries = store.search(query, limit=limit)

        if knowledge_type:
            entries = [e for e in entries if e.type == knowledge_type]

        return RecallResult(
            query=query,
            total_found=len(entries),
            entries=[e.model_dump() for e in entries],
            context_snippet=retriever.format_for_prompt(entries),
        )

    except Exception as e:
        logger.error(f"Failed to recall knowledge: {e}")
        return RecallResult(
            query=query,
            total_found=0,
            entries=[],
            context_snippet=f"Recall failed: {str(e)}",
        )


@mcp.tool()
async def forget(
    entry_id: str,
) -> MemoryResult:
    """
    Delete a knowledge entry by ID.
    """
    logger.info(f"Forgetting knowledge: {entry_id}")

    try:
        from aicouncil.memory import KnowledgeStore

        store = KnowledgeStore()
        success = store.delete(entry_id)

        if success:
            return MemoryResult(
                success=True,
                entry_id=entry_id,
                message=f"Knowledge entry {entry_id} deleted",
            )
        else:
            return MemoryResult(
                success=False,
                entry_id=entry_id,
                message=f"Entry {entry_id} not found",
            )

    except Exception as e:
        logger.error(f"Failed to delete knowledge: {e}")
        return MemoryResult(
            success=False,
            message=f"Delete failed: {str(e)}",
        )


@mcp.tool()
async def show_knowledge_summary() -> dict:
    """
    List all saved project knowledge with counts by type.
    """
    logger.info("Showing knowledge summary")

    try:
        from aicouncil.memory import KnowledgeStore

        store = KnowledgeStore()
        summary = store.get_summary()
        return summary.model_dump()

    except Exception as e:
        logger.error(f"Failed to get knowledge summary: {e}")
        return {
            "error": str(e),
            "total_entries": 0,
            "message": "Failed to load knowledge summary",
        }


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Run the AI Council server."""
    logger.info("Starting AI Council Server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
