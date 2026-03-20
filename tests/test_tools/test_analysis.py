"""Tests for analysis tool functions."""

from unittest.mock import patch

import pytest

from aicouncil.exceptions import OpenRouterError
from aicouncil.schemas.responses import (
    AlternativesResult,
    BrainstormResult,
    ChallengeResult,
    CritiqueResult,
    GapsResult,
    ValidationResult,
)
from aicouncil.tools.analysis import (
    brainstorm,
    challenge_assumptions,
    critique,
    find_gaps,
    propose_alternatives,
    validate,
)

MODULE = "aicouncil.tools.analysis"


@pytest.fixture
def _patch_analysis(mock_config, mock_client):
    """Patch get_config and OpenRouterClient in the analysis module."""
    with (
        patch(f"{MODULE}.get_config", return_value=mock_config),
        patch(f"{MODULE}.OpenRouterClient", return_value=mock_client) as client_cls,
        patch(f"{MODULE}.get_knowledge_context", return_value=""),
    ):
        client_cls.return_value = mock_client
        yield client_cls


class TestCritique:
    @pytest.mark.asyncio
    async def test_critique_returns_critique_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = CritiqueResult(
            verdict="approved", summary="Looks good", issues=[], strengths=["Clear code"]
        )
        result = await critique("some code", content_type="code")
        assert isinstance(result, CritiqueResult)
        assert result.verdict == "approved"

    @pytest.mark.asyncio
    async def test_critique_uses_resolve_model(self, _patch_analysis, mock_config):
        """critique has tool_override → uses test/critique-model."""
        from aicouncil.tools import analysis as mod

        with patch.object(mod, "OpenRouterClient") as cls:
            cls.return_value.generate = lambda *a, **kw: CritiqueResult(
                verdict="approved", summary="ok", issues=[], strengths=[]
            )
            # Need to make generate async
            from unittest.mock import AsyncMock

            inst = cls.return_value
            inst.generate = AsyncMock(
                return_value=CritiqueResult(
                    verdict="approved", summary="ok", issues=[], strengths=[]
                )
            )
            with patch.object(mod, "get_config", return_value=mock_config):
                await critique("content")
            cls.assert_called_with(model="test/critique-model", config=mock_config)

    @pytest.mark.asyncio
    async def test_critique_per_invocation_override(
        self, _patch_analysis, mock_client, mock_config
    ):
        mock_client.generate.return_value = CritiqueResult(
            verdict="approved", summary="ok", issues=[], strengths=[]
        )
        await critique("content", model="override/model")
        _patch_analysis.assert_called_with(model="override/model", config=mock_config)

    @pytest.mark.asyncio
    async def test_critique_error_returns_structured_response(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("API down")
        result = await critique("content")
        assert isinstance(result, CritiqueResult)
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_critique_unexpected_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = TypeError("boom")
        result = await critique("content")
        assert isinstance(result, CritiqueResult)
        assert result.confidence == 0.0


class TestBrainstorm:
    @pytest.mark.asyncio
    async def test_brainstorm_returns_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = BrainstormResult(
            ideas=[], synthesis="Good ideas", recommended=None
        )
        result = await brainstorm("new feature")
        assert isinstance(result, BrainstormResult)

    @pytest.mark.asyncio
    async def test_brainstorm_uses_brainstorm_model(
        self, _patch_analysis, mock_client, mock_config
    ):
        mock_client.generate.return_value = BrainstormResult(
            ideas=[], synthesis="ok", recommended=None
        )
        await brainstorm("topic")
        _patch_analysis.assert_called_with(model="test/brainstorm-model", config=mock_config)

    @pytest.mark.asyncio
    async def test_brainstorm_clamps_num_ideas(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = BrainstormResult(
            ideas=[], synthesis="ok", recommended=None
        )
        await brainstorm("topic", num_ideas=1)
        await brainstorm("topic", num_ideas=20)

    @pytest.mark.asyncio
    async def test_brainstorm_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await brainstorm("topic")
        assert isinstance(result, BrainstormResult)
        assert result.ideas == []


class TestValidate:
    @pytest.mark.asyncio
    async def test_validate_returns_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = ValidationResult(
            is_valid=True, score=0.9, passed_checks=["all"], failed_checks=[]
        )
        result = await validate("content")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_uses_default_model(self, _patch_analysis, mock_client, mock_config):
        """validate has no tool_override → uses default_model."""
        mock_client.generate.return_value = ValidationResult(
            is_valid=True, score=1.0, passed_checks=[], failed_checks=[]
        )
        await validate("content")
        _patch_analysis.assert_called_with(model="test/default-model", config=mock_config)

    @pytest.mark.asyncio
    async def test_validate_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await validate("content")
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert result.score == 0.0


class TestChallengeAssumptions:
    @pytest.mark.asyncio
    async def test_empty_assumptions_returns_early(self, _patch_analysis, mock_client):
        result = await challenge_assumptions([])
        assert isinstance(result, ChallengeResult)
        assert "No assumptions" in result.summary
        mock_client.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_challenge_returns_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = ChallengeResult(
            challenged=[], validated=["A is sound"], summary="ok", recommendation="go"
        )
        result = await challenge_assumptions(["A is true"])
        assert isinstance(result, ChallengeResult)

    @pytest.mark.asyncio
    async def test_challenge_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await challenge_assumptions(["A"])
        assert isinstance(result, ChallengeResult)
        assert result.challenged == []


class TestFindGaps:
    @pytest.mark.asyncio
    async def test_find_gaps_returns_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = GapsResult(
            gaps=[], coverage_score=0.8, well_covered=["auth"], summary="Good coverage"
        )
        result = await find_gaps("requirements doc")
        assert isinstance(result, GapsResult)
        assert result.coverage_score == 0.8

    @pytest.mark.asyncio
    async def test_find_gaps_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await find_gaps("content")
        assert isinstance(result, GapsResult)
        assert result.coverage_score == 0.0


class TestProposeAlternatives:
    @pytest.mark.asyncio
    async def test_propose_alternatives_returns_result(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = AlternativesResult(
            current_approach_assessment="Solid",
            alternatives=[],
            comparison_matrix={},
            recommendation="Keep current",
        )
        result = await propose_alternatives("use REST API")
        assert isinstance(result, AlternativesResult)

    @pytest.mark.asyncio
    async def test_propose_alternatives_clamps_count(self, _patch_analysis, mock_client):
        mock_client.generate.return_value = AlternativesResult(
            current_approach_assessment="ok",
            alternatives=[],
            comparison_matrix={},
            recommendation="ok",
        )
        await propose_alternatives("approach", num_alternatives=1)
        await propose_alternatives("approach", num_alternatives=10)

    @pytest.mark.asyncio
    async def test_propose_alternatives_error(self, _patch_analysis, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await propose_alternatives("approach")
        assert isinstance(result, AlternativesResult)
        assert result.alternatives == []
