"""Tests for research tool functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from aicouncil.exceptions import OpenRouterError
from aicouncil.schemas.responses import DocumentResearchResult, ResearchResult
from aicouncil.tools.research import research_assist, research_document

MODULE = "aicouncil.tools.research"


@pytest.fixture
def _patch_research(mock_config, mock_client):
    """Patch get_config and OpenRouterClient in the research module."""
    with (
        patch(f"{MODULE}.get_config", return_value=mock_config),
        patch(f"{MODULE}.OpenRouterClient", return_value=mock_client) as client_cls,
        patch(f"{MODULE}.get_project_root", return_value=Path("/")),
    ):
        client_cls.return_value = mock_client
        yield client_cls


class TestResearchAssist:
    @pytest.mark.asyncio
    async def test_research_returns_result(self, _patch_research, mock_client):
        mock_client.generate.return_value = ResearchResult(
            findings=[],
            summary="Found things",
            knowledge_gaps=[],
            next_steps=[],
            confidence_overall="high",
        )
        result = await research_assist("what is MCP?")
        assert isinstance(result, ResearchResult)
        assert result.summary == "Found things"

    @pytest.mark.asyncio
    async def test_research_uses_default_model(self, _patch_research, mock_client, mock_config):
        """research_assist has no tool_override → uses default_model."""
        mock_client.generate.return_value = ResearchResult(
            findings=[],
            summary="ok",
            knowledge_gaps=[],
            next_steps=[],
            confidence_overall="low",
        )
        await research_assist("query")
        _patch_research.assert_called_with(model="test/default-model", config=mock_config)

    @pytest.mark.asyncio
    async def test_research_per_invocation_override(
        self, _patch_research, mock_client, mock_config
    ):
        mock_client.generate.return_value = ResearchResult(
            findings=[],
            summary="ok",
            knowledge_gaps=[],
            next_steps=[],
            confidence_overall="low",
        )
        await research_assist("query", model="custom/model")
        _patch_research.assert_called_with(model="custom/model", config=mock_config)

    @pytest.mark.asyncio
    async def test_research_error(self, _patch_research, mock_client):
        mock_client.generate.side_effect = OpenRouterError("fail")
        result = await research_assist("query")
        assert isinstance(result, ResearchResult)
        assert result.confidence_overall == "low"


class TestResearchDocument:
    @pytest.mark.asyncio
    async def test_document_not_found(self, _patch_research, mock_client):
        result = await research_document("/nonexistent/file.txt", "/tmp/out.md")
        assert isinstance(result, DocumentResearchResult)
        assert "not found" in result.executive_summary.lower()
        mock_client.generate_with_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_research_success(self, tmp_path, _patch_research, mock_client):
        doc = tmp_path / "test.md"
        doc.write_text("# Test Document\n\nSome content.")
        output = tmp_path / "output.md"

        mock_client.generate_with_file.return_value = DocumentResearchResult(
            document_title="Test",
            document_type="markdown",
            executive_summary="A test doc",
            key_insights=[],
        )

        result = await research_document(str(doc), str(output), save_to_knowledge=False)

        assert isinstance(result, DocumentResearchResult)
        assert result.document_title == "Test"
        assert result.output_file_path == str(output)
        assert output.exists()

    @pytest.mark.asyncio
    async def test_document_research_error(self, tmp_path, _patch_research, mock_client):
        doc = tmp_path / "test.md"
        doc.write_text("content")
        mock_client.generate_with_file.side_effect = OpenRouterError("fail")
        result = await research_document(str(doc), "/tmp/out.md")
        assert isinstance(result, DocumentResearchResult)
        assert "failed" in result.executive_summary.lower()

    @pytest.mark.asyncio
    async def test_document_research_uses_resolve_model(
        self, tmp_path, _patch_research, mock_client, mock_config
    ):
        doc = tmp_path / "test.md"
        doc.write_text("content")
        mock_client.generate_with_file.return_value = DocumentResearchResult(
            document_title="T", document_type="md", executive_summary="ok", key_insights=[]
        )
        await research_document(str(doc), str(tmp_path / "out.md"), save_to_knowledge=False)
        _patch_research.assert_called_with(model="test/default-model", config=mock_config)
