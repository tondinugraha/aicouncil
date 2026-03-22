"""Pydantic models for structured AI Council responses."""

from typing import Literal

from pydantic import BaseModel, Field


class Issue(BaseModel):
    """A single issue identified during critique or validation."""

    category: str = Field(description="Category of issue (e.g., security, performance, logic)")
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        description="Severity level of the issue"
    )
    description: str = Field(description="Clear description of the problem")
    suggestion: str = Field(description="Actionable suggestion to fix the issue")
    location: str | None = Field(default=None, description="Location in content where issue exists")


class CritiqueResult(BaseModel):
    """Result of an adversarial critique review."""

    verdict: Literal["approved", "needs_revision", "rejected"] = Field(
        description="Overall verdict on the content"
    )
    summary: str = Field(description="Brief summary of the review findings")
    issues: list[Issue] = Field(default_factory=list, description="List of identified issues")
    strengths: list[str] = Field(default_factory=list, description="Positive aspects worth noting")
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence in this assessment (0-1)"
    )


class Idea(BaseModel):
    """A single brainstormed idea."""

    title: str = Field(description="Short title for the idea")
    description: str = Field(description="Detailed description of the idea")
    rationale: str = Field(description="Why this idea could work")
    pros: list[str] = Field(default_factory=list, description="Advantages of this idea")
    cons: list[str] = Field(default_factory=list, description="Potential drawbacks")
    effort: Literal["low", "medium", "high"] = Field(
        default="medium", description="Estimated implementation effort"
    )


class BrainstormResult(BaseModel):
    """Result of a brainstorming session."""

    ideas: list[Idea] = Field(description="Generated ideas")
    synthesis: str = Field(description="Overall synthesis connecting the ideas")
    recommended: str | None = Field(
        default=None, description="Title of the recommended idea, if one stands out"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list, description="Questions to explore further"
    )


class ValidationResult(BaseModel):
    """Result of content validation."""

    is_valid: bool = Field(description="Whether the content passes validation")
    score: float = Field(ge=0.0, le=1.0, description="Validation score (0-1)")
    passed_checks: list[str] = Field(default_factory=list, description="Checks that passed")
    failed_checks: list[str] = Field(default_factory=list, description="Checks that failed")
    warnings: list[str] = Field(default_factory=list, description="Non-blocking warnings")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


class Assumption(BaseModel):
    """An assumption being challenged."""

    original: str = Field(description="The original assumption")
    challenge: str = Field(description="Why this assumption might be wrong")
    counter_evidence: list[str] = Field(
        default_factory=list, description="Evidence against the assumption"
    )
    alternative_view: str = Field(description="An alternative perspective to consider")
    risk_if_wrong: Literal["critical", "high", "medium", "low"] = Field(
        description="Risk level if assumption proves incorrect"
    )


class ChallengeResult(BaseModel):
    """Result of challenging assumptions."""

    challenged: list[Assumption] = Field(description="Assumptions that were challenged")
    validated: list[str] = Field(default_factory=list, description="Assumptions that seem sound")
    summary: str = Field(description="Overall assessment of the assumptions")
    recommendation: str = Field(description="What to do next based on this analysis")


class Gap(BaseModel):
    """An identified gap or missing element."""

    category: str = Field(description="Category of gap (e.g., edge_case, requirement, test)")
    description: str = Field(description="What is missing or incomplete")
    impact: Literal["critical", "high", "medium", "low"] = Field(description="Impact of this gap")
    suggested_addition: str = Field(description="What should be added to fill the gap")


class GapsResult(BaseModel):
    """Result of gap analysis."""

    gaps: list[Gap] = Field(description="Identified gaps")
    coverage_score: float = Field(ge=0.0, le=1.0, description="Estimated coverage (0-1)")
    well_covered: list[str] = Field(default_factory=list, description="Areas that are well covered")
    summary: str = Field(description="Summary of the gap analysis")


class Alternative(BaseModel):
    """An alternative approach."""

    title: str = Field(description="Name for this alternative")
    description: str = Field(description="How this alternative works")
    trade_offs: str = Field(description="Trade-offs compared to current approach")
    pros: list[str] = Field(default_factory=list, description="Advantages")
    cons: list[str] = Field(default_factory=list, description="Disadvantages")
    when_to_use: str = Field(description="Scenarios where this alternative excels")


class AlternativesResult(BaseModel):
    """Result of alternative generation."""

    current_approach_assessment: str = Field(description="Assessment of the current approach")
    alternatives: list[Alternative] = Field(description="Generated alternatives")
    comparison_matrix: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Matrix comparing alternatives across criteria"
    )
    recommendation: str = Field(description="Which approach is recommended and why")


class ResearchFinding(BaseModel):
    """A single research finding."""

    topic: str = Field(description="Topic of this finding")
    insight: str = Field(description="The key insight discovered")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in this finding")
    sources_suggested: list[str] = Field(
        default_factory=list, description="Suggested sources to verify"
    )
    implications: list[str] = Field(
        default_factory=list, description="Implications of this finding"
    )


class ResearchResult(BaseModel):
    """Result of research assistance."""

    findings: list[ResearchFinding] = Field(description="Research findings")
    summary: str = Field(description="Executive summary of research")
    knowledge_gaps: list[str] = Field(
        default_factory=list, description="Areas needing more research"
    )
    next_steps: list[str] = Field(default_factory=list, description="Recommended next steps")
    confidence_overall: Literal["high", "medium", "low"] = Field(
        description="Overall confidence in findings"
    )


# ============================================================================
# Codebase Scanning Response Models
# ============================================================================


class FileAnalysis(BaseModel):
    """Analysis of a single file."""

    path: str = Field(description="File path relative to project root")
    summary: str = Field(description="Brief summary of file purpose")
    issues: list[Issue] = Field(default_factory=list, description="Issues found in this file")
    patterns: list[str] = Field(default_factory=list, description="Patterns identified")
    complexity: Literal["low", "medium", "high"] = Field(
        default="medium", description="Code complexity assessment"
    )


class CodebaseScanResult(BaseModel):
    """Result of scanning a codebase."""

    project_name: str = Field(description="Detected project name")
    project_type: str = Field(description="Detected project type (python, javascript, etc)")
    framework: str | None = Field(default=None, description="Detected framework")
    total_files: int = Field(description="Total files scanned")
    total_lines: int = Field(description="Total lines of code")
    languages: dict[str, int] = Field(default_factory=dict, description="Language breakdown")
    key_files: list[FileAnalysis] = Field(default_factory=list, description="Analysis of key files")
    architecture_summary: str = Field(description="Summary of project architecture")
    issues: list[Issue] = Field(default_factory=list, description="Project-wide issues")
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )
    dependencies: list[str] = Field(default_factory=list, description="Key dependencies")
    knowledge_learned: list[str] = Field(
        default_factory=list, description="New knowledge entries created"
    )


class FileAnalysisResult(BaseModel):
    """Result of analyzing a specific file."""

    file_path: str = Field(description="Path to analyzed file")
    file_summary: str = Field(description="Summary of file purpose and content")
    structure: dict = Field(default_factory=dict, description="Code structure (classes, functions)")
    issues: list[Issue] = Field(default_factory=list, description="Issues found")
    patterns: list[str] = Field(default_factory=list, description="Patterns identified")
    related_files: list[str] = Field(default_factory=list, description="Related files analyzed")
    recommendations: list[str] = Field(default_factory=list, description="Specific recommendations")
    knowledge_learned: list[str] = Field(
        default_factory=list, description="New knowledge entries created"
    )


class DependencyNode(BaseModel):
    """A node in the dependency graph."""

    name: str = Field(description="Module/file name")
    path: str = Field(description="File path")
    imports: list[str] = Field(default_factory=list, description="What this module imports")
    imported_by: list[str] = Field(default_factory=list, description="What imports this module")


class DependencyAnalysisResult(BaseModel):
    """Result of dependency analysis."""

    total_modules: int = Field(description="Total modules analyzed")
    external_dependencies: list[str] = Field(default_factory=list, description="External packages")
    internal_modules: list[DependencyNode] = Field(
        default_factory=list, description="Internal module graph"
    )
    circular_dependencies: list[list[str]] = Field(
        default_factory=list, description="Detected circular dependencies"
    )
    hub_modules: list[str] = Field(
        default_factory=list, description="Modules with many connections"
    )
    isolated_modules: list[str] = Field(
        default_factory=list, description="Modules with no connections"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Dependency recommendations"
    )


# ============================================================================
# Memory/Knowledge Response Models
# ============================================================================


class MemoryResult(BaseModel):
    """Result of a memory operation."""

    success: bool = Field(description="Whether operation succeeded")
    entry_id: str | None = Field(default=None, description="ID of created/affected entry")
    message: str = Field(description="Description of what happened")


class RecallResult(BaseModel):
    """Result of recalling knowledge."""

    query: str = Field(description="The search query used")
    total_found: int = Field(description="Total matching entries")
    entries: list[dict] = Field(default_factory=list, description="Matching knowledge entries")
    context_snippet: str = Field(default="", description="Formatted snippet for prompt context")


# ============================================================================
# Document Research Response Models
# ============================================================================


# ============================================================================
# Council Deliberation Response Models
# ============================================================================


class CouncilSpeakResult(BaseModel):
    """Response from a single agent speaking in a council deliberation round."""

    agent_name: str = Field(description="Name of the speaking agent")
    agent_role: str = Field(description="Role title of the speaking agent")
    model: str = Field(description="Model that generated this response")
    response: str = Field(description="Full natural language response in the agent's voice")
    stance: str = Field(
        description="One-line stance summary (e.g., 'Cautiously in favor with security concerns')"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="2-5 extractable key points from the response",
    )


class DocumentInsight(BaseModel):
    """A key insight extracted from the document."""

    category: str = Field(
        description="Category of insight (e.g., main_argument, methodology, finding)"
    )
    content: str = Field(description="The actual insight")
    importance: Literal["critical", "high", "medium", "low"] = Field(
        description="Importance level of this insight"
    )
    page_reference: str | None = Field(
        default=None, description="Page or section reference if available"
    )


class DocumentResearchResult(BaseModel):
    """Result of document research and analysis."""

    document_title: str = Field(description="Title or name of the document")
    document_type: str = Field(
        description="Type of document (research paper, article, report, etc.)"
    )
    executive_summary: str = Field(description="High-level summary of the document")

    key_insights: list[DocumentInsight] = Field(
        description="Key insights extracted from the document"
    )

    main_arguments: list[str] = Field(default_factory=list, description="Main arguments or themes")

    findings: list[str] = Field(default_factory=list, description="Key findings or conclusions")

    methodology: str | None = Field(default=None, description="Research methodology if applicable")

    strengths: list[str] = Field(default_factory=list, description="Strengths of the document")

    limitations: list[str] = Field(
        default_factory=list, description="Limitations or weaknesses identified"
    )

    questions_raised: list[str] = Field(
        default_factory=list, description="Questions or areas needing further research"
    )

    related_topics: list[str] = Field(default_factory=list, description="Related topics to explore")

    practical_applications: list[str] = Field(
        default_factory=list, description="How this knowledge can be applied"
    )

    citations_mentioned: list[str] = Field(
        default_factory=list, description="Key citations or references mentioned"
    )

    knowledge_learned: list[str] = Field(
        default_factory=list, description="New knowledge entries created"
    )

    output_file_path: str | None = Field(default=None, description="Path where analysis was saved")
