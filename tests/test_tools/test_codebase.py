"""Tests for codebase tool functions."""

from unittest.mock import MagicMock, patch

import pytest

from aicouncil.exceptions import OpenRouterError
from aicouncil.schemas.responses import (
    CodebaseScanResult,
    DependencyAnalysisResult,
    FileAnalysisResult,
)
from aicouncil.tools.codebase import analyze_dependencies, critique_file, scan_codebase

MODULE = "aicouncil.tools.codebase"
# Deferred imports go through __init__ re-exports
CONTEXT_BUILDER = "aicouncil.scanner.ContextBuilder"
PROJECT_DETECTOR = "aicouncil.scanner.ProjectDetector"
FILE_WALKER = "aicouncil.scanner.FileWalker"
CODE_ANALYZER = "aicouncil.scanner.CodeAnalyzer"
KNOWLEDGE_LEARNER = "aicouncil.memory.KnowledgeLearner"


@pytest.fixture
def _patch_codebase(mock_config, mock_client):
    """Patch get_config and OpenRouterClient in the codebase module."""
    with (
        patch(f"{MODULE}.get_config", return_value=mock_config),
        patch(f"{MODULE}.OpenRouterClient", return_value=mock_client) as client_cls,
        patch(f"{MODULE}.get_knowledge_context", return_value=""),
    ):
        client_cls.return_value = mock_client
        yield client_cls


def _mock_project_context():
    ctx = MagicMock()
    ctx.project.name = "test"
    ctx.project.type = "python"
    ctx.project.framework = None
    ctx.total_files = 10
    ctx.total_lines = 500
    ctx.languages = {"python": 500}
    ctx.key_files = []
    ctx.dependencies = []
    ctx.all_files = []
    return ctx


class TestScanCodebase:
    @pytest.mark.asyncio
    async def test_scan_returns_result(self, _patch_codebase, mock_client):
        mock_client.generate.return_value = CodebaseScanResult(
            project_name="test",
            project_type="python",
            total_files=10,
            total_lines=500,
            architecture_summary="Clean architecture",
        )

        with (
            patch(CONTEXT_BUILDER) as builder_cls,
            patch(KNOWLEDGE_LEARNER) as learner_cls,
        ):
            builder_cls.return_value.build_project_context.return_value = _mock_project_context()
            learner_cls.return_value.learn_from_scan.return_value = []
            result = await scan_codebase()

        assert isinstance(result, CodebaseScanResult)
        assert result.project_name == "test"

    @pytest.mark.asyncio
    async def test_scan_uses_resolve_model(self, _patch_codebase, mock_client, mock_config):
        mock_client.generate.return_value = CodebaseScanResult(
            project_name="t",
            project_type="p",
            total_files=0,
            total_lines=0,
            architecture_summary="ok",
        )
        with (
            patch(CONTEXT_BUILDER) as builder_cls,
            patch(KNOWLEDGE_LEARNER) as learner_cls,
        ):
            builder_cls.return_value.build_project_context.return_value = _mock_project_context()
            learner_cls.return_value.learn_from_scan.return_value = []
            await scan_codebase()
        _patch_codebase.assert_called_with(model="test/default-model", config=mock_config)

    @pytest.mark.asyncio
    async def test_scan_error(self, _patch_codebase, mock_client):
        with patch(CONTEXT_BUILDER, side_effect=OpenRouterError("fail")):
            result = await scan_codebase()
        assert isinstance(result, CodebaseScanResult)
        assert "fail" in result.architecture_summary.lower()


class TestCritiqueFile:
    @pytest.mark.asyncio
    async def test_critique_file_returns_result(self, _patch_codebase, mock_client):
        mock_client.generate.return_value = FileAnalysisResult(
            file_path="test.py",
            file_summary="A test file",
        )
        mock_main = MagicMock()
        mock_main.path = "test.py"
        mock_main.summary = "Test"
        mock_main.content = "print('hello')"
        mock_main.structure = None

        with patch(CONTEXT_BUILDER) as builder_cls:
            builder_cls.return_value.build_file_context.return_value = (mock_main, [])
            result = await critique_file("test.py")

        assert isinstance(result, FileAnalysisResult)
        assert result.file_path == "test.py"

    @pytest.mark.asyncio
    async def test_critique_file_error(self, _patch_codebase, mock_client):
        with patch(CONTEXT_BUILDER, side_effect=OpenRouterError("fail")):
            result = await critique_file("test.py")
        assert isinstance(result, FileAnalysisResult)
        assert "fail" in result.file_summary.lower()


class TestAnalyzeDependencies:
    @pytest.mark.asyncio
    async def test_analyze_dependencies_returns_result(self):
        mock_detector = MagicMock()
        mock_detector.detect.return_value = MagicMock(root="/tmp/project")
        mock_walker = MagicMock()
        mock_walker.get_code_files.return_value = []

        with (
            patch(PROJECT_DETECTOR, return_value=mock_detector),
            patch(FILE_WALKER, return_value=mock_walker),
            patch(CODE_ANALYZER),
        ):
            result = await analyze_dependencies()

        assert isinstance(result, DependencyAnalysisResult)
        assert result.total_modules == 0

    @pytest.mark.asyncio
    async def test_analyze_dependencies_no_llm_call(self):
        """analyze_dependencies should NOT call OpenRouterClient."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = MagicMock(root="/tmp/project")
        mock_walker = MagicMock()
        mock_walker.get_code_files.return_value = []

        with (
            patch(PROJECT_DETECTOR, return_value=mock_detector),
            patch(FILE_WALKER, return_value=mock_walker),
            patch(CODE_ANALYZER),
            patch(f"{MODULE}.OpenRouterClient") as client_cls,
        ):
            await analyze_dependencies()
            client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_dependencies_error(self):
        with patch(PROJECT_DETECTOR, side_effect=TypeError("no project")):
            result = await analyze_dependencies()
        assert isinstance(result, DependencyAnalysisResult)
        assert result.total_modules == 0
