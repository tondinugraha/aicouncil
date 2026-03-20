"""Tests for memory tool functions."""

from unittest.mock import MagicMock, patch

import pytest

from aicouncil.exceptions import AiCouncilError
from aicouncil.schemas.responses import MemoryResult, RecallResult
from aicouncil.tools.memory import forget, recall, remember, show_knowledge_summary

# Deferred imports go through aicouncil.memory.__init__ re-exports
LEARNER = "aicouncil.memory.KnowledgeLearner"
STORE = "aicouncil.memory.KnowledgeStore"
RETRIEVER = "aicouncil.memory.KnowledgeRetriever"


class TestRemember:
    @pytest.mark.asyncio
    async def test_remember_success(self):
        mock_learner = MagicMock()
        mock_learner.learn_explicit.return_value = "entry-123"

        with patch(LEARNER, return_value=mock_learner):
            result = await remember("Python uses duck typing", knowledge_type="insight")

        assert isinstance(result, MemoryResult)
        assert result.success is True
        assert result.entry_id == "entry-123"

    @pytest.mark.asyncio
    async def test_remember_with_tags(self):
        mock_learner = MagicMock()
        mock_learner.learn_explicit.return_value = "entry-456"

        with patch(LEARNER, return_value=mock_learner):
            result = await remember(
                "REST API pattern",
                knowledge_type="pattern",
                tags=["api", "rest"],
                references=["server.py"],
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_remember_error(self):
        mock_learner = MagicMock()
        mock_learner.learn_explicit.side_effect = AiCouncilError("store broken")

        with patch(LEARNER, return_value=mock_learner):
            result = await remember("content")

        assert isinstance(result, MemoryResult)
        assert result.success is False
        assert "store broken" in result.message


class TestRecall:
    @pytest.mark.asyncio
    async def test_recall_success(self):
        mock_entry = MagicMock()
        mock_entry.type = "insight"
        mock_entry.model_dump.return_value = {"id": "1", "content": "found"}

        mock_store = MagicMock()
        mock_store.search.return_value = [mock_entry]

        mock_retriever = MagicMock()
        mock_retriever.format_for_prompt.return_value = "context"

        with (
            patch(STORE, return_value=mock_store),
            patch(RETRIEVER, return_value=mock_retriever),
        ):
            result = await recall("duck typing")

        assert isinstance(result, RecallResult)
        assert result.total_found == 1
        assert result.query == "duck typing"

    @pytest.mark.asyncio
    async def test_recall_with_type_filter(self):
        mock_entry_match = MagicMock()
        mock_entry_match.type = "pattern"
        mock_entry_match.model_dump.return_value = {"id": "1"}

        mock_entry_miss = MagicMock()
        mock_entry_miss.type = "insight"
        mock_entry_miss.model_dump.return_value = {"id": "2"}

        mock_store = MagicMock()
        mock_store.search.return_value = [mock_entry_match, mock_entry_miss]

        mock_retriever = MagicMock()
        mock_retriever.format_for_prompt.return_value = ""

        with (
            patch(STORE, return_value=mock_store),
            patch(RETRIEVER, return_value=mock_retriever),
        ):
            result = await recall("test", knowledge_type="pattern")

        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_recall_error(self):
        mock_store = MagicMock()
        mock_store.search.side_effect = AiCouncilError("store error")

        with patch(STORE, return_value=mock_store):
            result = await recall("query")

        assert isinstance(result, RecallResult)
        assert result.total_found == 0


class TestForget:
    @pytest.mark.asyncio
    async def test_forget_success(self):
        mock_store = MagicMock()
        mock_store.delete.return_value = True

        with patch(STORE, return_value=mock_store):
            result = await forget("entry-123")

        assert isinstance(result, MemoryResult)
        assert result.success is True
        assert result.entry_id == "entry-123"

    @pytest.mark.asyncio
    async def test_forget_not_found(self):
        mock_store = MagicMock()
        mock_store.delete.return_value = False

        with patch(STORE, return_value=mock_store):
            result = await forget("nonexistent")

        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_forget_error(self):
        mock_store = MagicMock()
        mock_store.delete.side_effect = AiCouncilError("fail")

        with patch(STORE, return_value=mock_store):
            result = await forget("entry-123")

        assert result.success is False


class TestShowKnowledgeSummary:
    @pytest.mark.asyncio
    async def test_summary_success(self):
        mock_summary = MagicMock()
        mock_summary.total_entries = 5
        mock_summary.entries_by_type = {"insight": 3, "pattern": 2}
        mock_summary.validated_count = 4
        mock_summary.stale_count = 1

        mock_store = MagicMock()
        mock_store.get_summary.return_value = mock_summary

        with patch(STORE, return_value=mock_store):
            result = await show_knowledge_summary()

        assert isinstance(result, MemoryResult)
        assert result.success is True
        assert "5" in result.message
        assert "insight" in result.message

    @pytest.mark.asyncio
    async def test_summary_error(self):
        mock_store = MagicMock()
        mock_store.get_summary.side_effect = AiCouncilError("store unavailable")

        with patch(STORE, return_value=mock_store):
            result = await show_knowledge_summary()

        assert result.success is False
