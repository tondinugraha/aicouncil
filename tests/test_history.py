"""Tests for council history — addendum file output boundary module."""

import stat
from datetime import datetime
from unittest.mock import patch

import pytest

from aicouncil.council.history import (
    _format_addendum_markdown,
    _generate_filename,
    _slugify_topic,
    write_council_addendum,
)
from aicouncil.council.schemas import AddendumMetadata, AddendumSaveResult
from aicouncil.exceptions import CouncilError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_metadata() -> AddendumMetadata:
    """Sample addendum metadata for testing."""
    return AddendumMetadata(
        session_id="test-session-abc-123",
        topic="Stripe Connect vs Direct Charges",
        agents=["Payment Systems Architect", "Backend Developer"],
        model_assignments={
            "Payment Systems Architect": "openai/gpt-5.2",
            "Backend Developer": "google/gemini-2.5-pro",
        },
        timestamp="2026-03-22T10:30:00+00:00",
    )


# ---------------------------------------------------------------------------
# _slugify_topic tests
# ---------------------------------------------------------------------------


class TestSlugifyTopic:
    def test_basic(self):
        assert _slugify_topic("Stripe Connect vs Direct") == "stripe-connect-vs-direct"

    def test_special_chars(self):
        assert _slugify_topic("What's the best API?!") == "what-s-the-best-api"

    def test_unicode(self):
        result = _slugify_topic("Café résumé naïve")
        assert result == "caf-r-sum-na-ve"

    def test_long_topic(self):
        result = _slugify_topic("a" * 100)
        assert len(result) <= 50

    def test_empty(self):
        assert _slugify_topic("") == ""

    def test_only_special_chars(self):
        assert _slugify_topic("!!!@@@###") == ""

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify_topic("---hello---") == "hello"

    def test_multiple_spaces(self):
        assert _slugify_topic("hello   world") == "hello-world"

    def test_mixed_case(self):
        assert _slugify_topic("Hello World TEST") == "hello-world-test"

    def test_numbers_preserved(self):
        assert _slugify_topic("API v2.0 migration") == "api-v2-0-migration"

    def test_truncation_no_trailing_hyphen(self):
        # Create a topic that when slugified lands a hyphen right at position 50
        topic = "a-" * 30  # 60 chars
        result = _slugify_topic(topic)
        assert len(result) <= 50
        assert not result.endswith("-")


# ---------------------------------------------------------------------------
# _generate_filename tests
# ---------------------------------------------------------------------------


class TestGenerateFilename:
    def test_format(self):
        result = _generate_filename("test topic", datetime(2026, 3, 22))
        assert result == "2026-03-22-test-topic.md"

    def test_empty_topic_fallback(self):
        result = _generate_filename("!!!", datetime(2026, 3, 22))
        assert result == "2026-03-22-council-session.md"

    def test_defaults_to_now(self):
        result = _generate_filename("test")
        today = datetime.now().strftime("%Y-%m-%d")
        assert result.startswith(today)
        assert result.endswith("-test.md")

    def test_long_topic_truncated(self):
        result = _generate_filename("a" * 200, datetime(2026, 1, 1))
        # date (10) + hyphen (1) + slug (max 50) + .md (3) = max 64
        assert len(result) <= 64


# ---------------------------------------------------------------------------
# _format_addendum_markdown tests
# ---------------------------------------------------------------------------


class TestFormatAddendumMarkdown:
    def test_includes_yaml_frontmatter(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "Test narrative.")
        assert content.startswith("---\n")
        assert "session_id: test-session-abc-123" in content
        assert 'topic: "Stripe Connect vs Direct Charges"' in content

    def test_includes_agents_in_frontmatter(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert "  - name: Payment Systems Architect" in content
        assert "    model: openai/gpt-5.2" in content
        assert "  - name: Backend Developer" in content
        assert "    model: google/gemini-2.5-pro" in content

    def test_includes_human_readable_header(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert "# Council Addendum: Stripe Connect vs Direct Charges" in content
        assert "**Session:** test-session-abc-123" in content
        assert "Payment Systems Architect (openai/gpt-5.2)" in content

    def test_includes_addendum_content(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "The council recommends X.")
        assert "The council recommends X." in content

    def test_metadata_header_fields(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert "**Date:** 2026-03-22T10:30:00+00:00" in content
        assert "**Participating Agents:**" in content


# ---------------------------------------------------------------------------
# write_council_addendum tests
# ---------------------------------------------------------------------------


class TestWriteCouncilAddendum:
    def test_creates_file(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "test content", project_root=tmp_path)
        assert path.exists()
        assert path.name.endswith(".md")

    def test_file_in_history_dir(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert path.parent == tmp_path / "aicouncil" / "history"

    def test_atomic_no_tmp_files(self, tmp_path, sample_metadata):
        write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        tmp_files = list((tmp_path / "aicouncil" / "history").glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_creates_history_dir(self, tmp_path, sample_metadata):
        assert not (tmp_path / "aicouncil" / "history").exists()
        write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert (tmp_path / "aicouncil" / "history").is_dir()

    def test_file_includes_metadata(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "narrative here", project_root=tmp_path)
        content = path.read_text()
        assert "session_id: test-session-abc-123" in content
        assert "narrative here" in content

    def test_filename_format(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert path.name == "2026-03-22-stripe-connect-vs-direct-charges.md"

    def test_wraps_os_error(self, tmp_path, sample_metadata):
        # Point to a non-writable location
        bad_root = tmp_path / "no-write"
        bad_root.mkdir()
        history_dir = bad_root / "aicouncil" / "history"
        history_dir.mkdir(parents=True)
        # Make history dir read-only
        history_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            with pytest.raises(CouncilError, match="Failed to write council addendum"):
                write_council_addendum(sample_metadata, "content", project_root=bad_root)
        finally:
            # Restore permissions for cleanup
            history_dir.chmod(stat.S_IRWXU)

    def test_duplicate_filename_disambiguated(self, tmp_path, sample_metadata):
        path1 = write_council_addendum(sample_metadata, "first", project_root=tmp_path)
        path2 = write_council_addendum(sample_metadata, "second", project_root=tmp_path)
        assert path1 != path2
        assert "-2" in path2.name
        assert path1.exists()
        assert path2.exists()

    def test_triple_duplicate(self, tmp_path, sample_metadata):
        write_council_addendum(sample_metadata, "first", project_root=tmp_path)
        path2 = write_council_addendum(sample_metadata, "second", project_root=tmp_path)
        path3 = write_council_addendum(sample_metadata, "third", project_root=tmp_path)
        assert "-2" in path2.name
        assert "-3" in path3.name

    def test_empty_addendum_content(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "", project_root=tmp_path)
        assert path.exists()
        content = path.read_text()
        assert "session_id: test-session-abc-123" in content

    def test_very_long_topic(self, tmp_path):
        metadata = AddendumMetadata(
            session_id="long-topic-test",
            topic="a" * 500,
            agents=["Agent A"],
            model_assignments={"Agent A": "model-a"},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        path = write_council_addendum(metadata, "content", project_root=tmp_path)
        assert path.exists()
        assert len(path.name) <= 64  # date + slug + .md

    def test_topic_only_special_chars(self, tmp_path):
        metadata = AddendumMetadata(
            session_id="special-chars-test",
            topic="!!!@@@###",
            agents=["Agent A"],
            model_assignments={"Agent A": "model-a"},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        path = write_council_addendum(metadata, "content", project_root=tmp_path)
        assert path.exists()
        assert "council-session" in path.name


# ---------------------------------------------------------------------------
# AddendumSaveResult schema tests
# ---------------------------------------------------------------------------


class TestAddendumSaveResult:
    def test_valid_schema(self, sample_metadata):
        result = AddendumSaveResult(
            file_path="/path/to/file.md",
            addendum_content="narrative",
            metadata=sample_metadata,
        )
        assert result.file_path == "/path/to/file.md"
        assert result.addendum_content == "narrative"
        assert result.metadata.session_id == "test-session-abc-123"

    def test_nested_metadata_validation(self):
        result = AddendumSaveResult(
            file_path="/file.md",
            addendum_content="text",
            metadata=AddendumMetadata(
                session_id="s1",
                topic="t1",
                agents=["a1"],
                model_assignments={"a1": "m1"},
                timestamp="2026-03-22",
            ),
        )
        assert result.metadata.topic == "t1"


# ---------------------------------------------------------------------------
# save_council_addendum tool tests
# ---------------------------------------------------------------------------


class TestSaveCouncilAddendumTool:
    @pytest.mark.asyncio
    async def test_returns_addendum_save_result(self, tmp_path):
        from aicouncil.tools.council import save_council_addendum

        with patch("aicouncil.tools.council.write_council_addendum") as mock_write:
            mock_write.return_value = tmp_path / "aicouncil" / "history" / "2026-03-22-test.md"

            result = await save_council_addendum(
                session_id="tool-test-123",
                topic="Test Topic",
                agents=["Agent A", "Agent B"],
                model_assignments={"Agent A": "model-a", "Agent B": "model-b"},
                addendum_content="The council decided X.",
            )

            assert isinstance(result, AddendumSaveResult)
            assert "2026-03-22-test.md" in result.file_path
            assert result.addendum_content == "The council decided X."
            assert result.metadata.session_id == "tool-test-123"
            assert result.metadata.topic == "Test Topic"

    @pytest.mark.asyncio
    async def test_end_to_end_file_creation(self, tmp_path):
        from aicouncil.tools.council import save_council_addendum

        with patch("aicouncil.tools.council.write_council_addendum", wraps=write_council_addendum):
            result = await save_council_addendum(
                session_id="e2e-test",
                topic="End to End Test",
                agents=["Agent A"],
                model_assignments={"Agent A": "model-a"},
                addendum_content="Full narrative content.",
            )

            assert isinstance(result, AddendumSaveResult)
            assert result.addendum_content == "Full narrative content."
