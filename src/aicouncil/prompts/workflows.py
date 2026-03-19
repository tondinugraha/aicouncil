"""Workflow-specific prompt enhancements for BMM and general development workflows."""


class WorkflowPrompts:
    """Workflow-aware prompt additions that enhance base prompts for specific contexts."""

    # Content type specific guidance
    CONTENT_TYPE_GUIDANCE = {
        "code": """
When reviewing code, specifically look for:
- Security vulnerabilities (injection, XSS, auth issues, secrets)
- Performance bottlenecks and inefficiencies
- Error handling gaps
- Race conditions and concurrency issues
- Memory leaks
- Missing input validation
- Breaking changes to APIs
- Test coverage gaps
- Code that's hard to maintain""",
        "plan": """
When reviewing plans, specifically look for:
- Unclear or ambiguous requirements
- Missing success criteria
- Unrealistic timelines or estimates
- Resource constraints not addressed
- Dependencies not identified
- Risk mitigation gaps
- Stakeholder concerns not addressed
- Scope creep indicators""",
        "architecture": """
When reviewing architecture, specifically look for:
- Scalability limitations
- Single points of failure
- Security architecture gaps
- Performance bottlenecks by design
- Over-engineering / unnecessary complexity
- Under-engineering / missing necessary abstractions
- Integration challenges
- Deployment and operations concerns
- Technology choices that may not age well""",
        "ux": """
When reviewing UX designs, specifically look for:
- Accessibility issues (WCAG compliance)
- Mobile responsiveness concerns
- Cognitive load problems
- Inconsistent patterns
- Missing error states
- Edge case user flows not covered
- Onboarding gaps
- User feedback mechanisms missing
- Performance perception issues""",
        "prd": """
When reviewing PRDs, specifically look for:
- Vague or unmeasurable requirements
- Missing user stories or personas
- Scope that's too broad or unclear
- Success metrics not defined
- Technical feasibility concerns
- Market validation gaps
- Competitive analysis missing
- Prioritization issues""",
        "story": """
When reviewing user stories, specifically look for:
- Acceptance criteria that aren't testable
- Missing edge cases in AC
- Dependencies not documented
- Story too large (should be split)
- Technical approach unclear
- Missing non-functional requirements
- Definition of done gaps""",
        "epic": """
When reviewing epics, specifically look for:
- Stories that don't align with epic goals
- Missing stories for complete functionality
- Dependencies between stories unclear
- Prioritization within epic
- MVP scope unclear
- Technical debt stories missing
- Testing strategy gaps""",
        "general": """
Analyze with a general critical eye for:
- Logical consistency
- Completeness
- Clarity
- Feasibility
- Risks""",
    }

    # Brainstorming context enhancers
    BRAINSTORM_CONTEXTS = {
        "product": """
Consider ideas across these dimensions:
- User experience improvements
- Technical innovations
- Business model variations
- Market positioning options
- Feature prioritization alternatives""",
        "technical": """
Consider technical approaches including:
- Different architectural patterns
- Alternative technology choices
- Build vs buy decisions
- Scalability strategies
- Performance optimization approaches""",
        "ux": """
Consider UX approaches including:
- Different interaction patterns
- Information architecture options
- Visual design directions
- Accessibility-first alternatives
- Mobile-first vs responsive strategies""",
        "strategy": """
Consider strategic options including:
- Go-to-market approaches
- Pricing strategies
- Partnership opportunities
- Competitive positioning
- Growth tactics""",
    }

    # Research depth configurations
    RESEARCH_DEPTH = {
        "quick": """
Provide a quick overview covering:
- Key facts and definitions
- Main considerations
- Top 3 most important points
- Immediate next steps""",
        "thorough": """
Provide thorough analysis covering:
- Comprehensive background
- Multiple perspectives
- Detailed implications
- Common pitfalls to avoid
- Best practices
- Relevant examples
- Action recommendations""",
        "exhaustive": """
Provide exhaustive analysis covering:
- Complete historical context
- All relevant perspectives and stakeholders
- Deep technical/domain details
- Edge cases and exceptions
- Comprehensive risk analysis
- Industry benchmarks and comparisons
- Academic/research perspectives
- Long-term implications
- Detailed action plan with contingencies""",
    }

    @classmethod
    def get_content_guidance(cls, content_type: str) -> str:
        """Get content-type specific guidance."""
        return cls.CONTENT_TYPE_GUIDANCE.get(
            content_type.lower(),
            cls.CONTENT_TYPE_GUIDANCE["general"],
        )

    @classmethod
    def get_brainstorm_context(cls, context_type: str) -> str:
        """Get brainstorming context enhancer."""
        return cls.BRAINSTORM_CONTEXTS.get(context_type.lower(), "")

    @classmethod
    def get_research_depth(cls, depth: str) -> str:
        """Get research depth configuration."""
        return cls.RESEARCH_DEPTH.get(depth.lower(), cls.RESEARCH_DEPTH["thorough"])
