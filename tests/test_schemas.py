"""Tests for Pydantic response schemas."""

from aicouncil.schemas.responses import (
    Alternative,
    AlternativesResult,
    Assumption,
    BrainstormResult,
    ChallengeResult,
    CritiqueResult,
    Gap,
    GapsResult,
    Idea,
    Issue,
    ResearchFinding,
    ResearchResult,
    ValidationResult,
)


class TestIssue:
    def test_valid_issue(self):
        issue = Issue(
            category="security",
            severity="high",
            description="SQL injection vulnerability",
            suggestion="Use parameterized queries",
            location="line 42",
        )
        assert issue.category == "security"
        assert issue.severity == "high"

    def test_issue_without_location(self):
        issue = Issue(
            category="performance",
            severity="medium",
            description="N+1 query problem",
            suggestion="Use eager loading",
        )
        assert issue.location is None


class TestCritiqueResult:
    def test_valid_critique(self):
        result = CritiqueResult(
            verdict="needs_revision",
            summary="Found several issues",
            issues=[
                Issue(
                    category="security",
                    severity="high",
                    description="Test issue",
                    suggestion="Fix it",
                )
            ],
            strengths=["Good structure"],
            confidence=0.85,
        )
        assert result.verdict == "needs_revision"
        assert len(result.issues) == 1
        assert result.confidence == 0.85

    def test_approved_critique(self):
        result = CritiqueResult(
            verdict="approved",
            summary="Looks good",
            issues=[],
            strengths=["Clean code", "Good tests"],
        )
        assert result.verdict == "approved"
        assert len(result.strengths) == 2


class TestBrainstormResult:
    def test_valid_brainstorm(self):
        result = BrainstormResult(
            ideas=[
                Idea(
                    title="Idea 1",
                    description="Description",
                    rationale="Why it works",
                    pros=["Pro 1"],
                    cons=["Con 1"],
                    effort="medium",
                )
            ],
            synthesis="These ideas connect via...",
            recommended="Idea 1",
            follow_up_questions=["What about X?"],
        )
        assert len(result.ideas) == 1
        assert result.recommended == "Idea 1"


class TestValidationResult:
    def test_valid_result(self):
        result = ValidationResult(
            is_valid=True,
            score=0.9,
            passed_checks=["Has all sections", "Consistent terminology"],
            failed_checks=[],
            warnings=["Consider adding examples"],
            suggestions=["Add more detail to section 3"],
        )
        assert result.is_valid is True
        assert result.score == 0.9

    def test_failed_validation(self):
        result = ValidationResult(
            is_valid=False,
            score=0.4,
            passed_checks=["Basic structure"],
            failed_checks=["Missing requirements", "Inconsistent naming"],
            warnings=[],
            suggestions=[],
        )
        assert result.is_valid is False
        assert len(result.failed_checks) == 2


class TestChallengeResult:
    def test_valid_challenge(self):
        result = ChallengeResult(
            challenged=[
                Assumption(
                    original="Users will pay for this",
                    challenge="No market validation yet",
                    counter_evidence=["Similar products failed"],
                    alternative_view="Consider freemium model",
                    risk_if_wrong="critical",
                )
            ],
            validated=["Technology is proven"],
            summary="One critical assumption needs validation",
            recommendation="Conduct user research first",
        )
        assert len(result.challenged) == 1
        assert result.challenged[0].risk_if_wrong == "critical"


class TestGapsResult:
    def test_valid_gaps(self):
        result = GapsResult(
            gaps=[
                Gap(
                    category="edge_case",
                    description="No handling for empty input",
                    impact="medium",
                    suggested_addition="Add input validation",
                )
            ],
            coverage_score=0.75,
            well_covered=["Happy path", "Error handling"],
            summary="Good coverage but missing edge cases",
        )
        assert len(result.gaps) == 1
        assert result.coverage_score == 0.75


class TestAlternativesResult:
    def test_valid_alternatives(self):
        result = AlternativesResult(
            current_approach_assessment="Solid but complex",
            alternatives=[
                Alternative(
                    title="Simpler approach",
                    description="Use existing library",
                    trade_offs="Less control but faster",
                    pros=["Faster implementation"],
                    cons=["Less flexibility"],
                    when_to_use="For MVP or time-constrained projects",
                )
            ],
            comparison_matrix={
                "complexity": {"current": "high", "simpler": "low"},
                "flexibility": {"current": "high", "simpler": "medium"},
            },
            recommendation="Consider simpler approach for MVP",
        )
        assert len(result.alternatives) == 1
        assert "complexity" in result.comparison_matrix


class TestResearchResult:
    def test_valid_research(self):
        result = ResearchResult(
            findings=[
                ResearchFinding(
                    topic="Authentication",
                    insight="JWT is industry standard for APIs",
                    confidence="high",
                    sources_suggested=["OWASP guidelines"],
                    implications=["Need token refresh strategy"],
                )
            ],
            summary="Research indicates JWT is the right choice",
            knowledge_gaps=["Need to research token storage"],
            next_steps=["Review OWASP guidelines", "Design refresh flow"],
            confidence_overall="high",
        )
        assert len(result.findings) == 1
        assert result.confidence_overall == "high"
