"""Tests for council history — addendum file output boundary module."""

import os
import stat
from datetime import datetime
from unittest.mock import patch

import pytest

from aicouncil.council.history import (
    MAX_DISAMBIGUATE_ATTEMPTS,
    _atomic_link_with_disambiguation,
    _format_addendum_markdown,
    _generate_filename,
    _slugify_topic,
    _yaml_escape,
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
# _yaml_escape tests
# ---------------------------------------------------------------------------


class TestYamlEscape:
    def test_plain_string(self):
        assert _yaml_escape("hello world") == "hello world"

    def test_double_quotes_escaped(self):
        assert _yaml_escape('say "hello"') == 'say \\"hello\\"'

    def test_backslash_escaped(self):
        assert _yaml_escape("path\\to\\file") == "path\\\\to\\\\file"

    def test_newlines_escaped(self):
        assert _yaml_escape("line1\nline2") == "line1\\nline2"

    def test_combined_special_chars(self):
        result = _yaml_escape('a "b"\nc\\d')
        assert result == 'a \\"b\\"\\nc\\\\d'


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
        assert len(result) <= 64

    def test_slug_fallback_warning_logged(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            _generate_filename("!!!", datetime(2026, 3, 22))
        assert "empty slug" in caplog.text


# ---------------------------------------------------------------------------
# _format_addendum_markdown tests
# ---------------------------------------------------------------------------


class TestFormatAddendumMarkdown:
    def test_includes_yaml_frontmatter(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "Test narrative.")
        assert content.startswith("---\n")
        assert 'session_id: "test-session-abc-123"' in content
        assert 'topic: "Stripe Connect vs Direct Charges"' in content

    def test_includes_agents_in_frontmatter(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert '  - name: "Payment Systems Architect"' in content
        assert '    model: "openai/gpt-5.2"' in content
        assert '  - name: "Backend Developer"' in content
        assert '    model: "google/gemini-2.5-pro"' in content

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

    def test_includes_model_assignments_table(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert "**Model Assignments:**" in content
        assert "| Payment Systems Architect | openai/gpt-5.2 |" in content
        assert "| Backend Developer | google/gemini-2.5-pro |" in content

    def test_includes_deliberation_section_heading(self, sample_metadata):
        content = _format_addendum_markdown(sample_metadata, "narrative")
        assert "## Council Deliberation" in content

    def test_yaml_injection_in_topic(self):
        metadata = AddendumMetadata(
            session_id="s1",
            topic='foo"\nmalicious: injected',
            agents=["a1"],
            model_assignments={"a1": "m1"},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        content = _format_addendum_markdown(metadata, "narrative")
        assert 'topic: "foo\\"\\nmalicious: injected"' in content
        assert "\nmalicious:" not in content.split("---")[1]

    def test_yaml_injection_in_agent_name(self):
        metadata = AddendumMetadata(
            session_id="s1",
            topic="test",
            agents=["evil\nagent"],
            model_assignments={"evil\nagent": "m1"},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        content = _format_addendum_markdown(metadata, "narrative")
        assert '  - name: "evil\\nagent"' in content

    def test_yaml_injection_in_session_id(self):
        metadata = AddendumMetadata(
            session_id='id"\nevil: true',
            topic="test",
            agents=["a1"],
            model_assignments={"a1": "m1"},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        content = _format_addendum_markdown(metadata, "narrative")
        assert 'session_id: "id\\"\\nevil: true"' in content

    def test_missing_model_assignment_shows_unknown(self):
        metadata = AddendumMetadata(
            session_id="s1",
            topic="test",
            agents=["a1"],
            model_assignments={},
            timestamp="2026-03-22T00:00:00+00:00",
        )
        content = _format_addendum_markdown(metadata, "narrative")
        assert '"unknown"' in content


# ---------------------------------------------------------------------------
# _atomic_link_with_disambiguation tests
# ---------------------------------------------------------------------------


class TestAtomicLinkWithDisambiguation:
    def test_links_to_target(self, tmp_path):
        tmp_file = tmp_path / "tmp.tmp"
        tmp_file.write_text("content")
        result = _atomic_link_with_disambiguation(tmp_file, tmp_path, "test.md")
        assert result == tmp_path / "test.md"
        assert result.read_text() == "content"

    def test_disambiguates_existing(self, tmp_path):
        (tmp_path / "test.md").write_text("existing")
        tmp_file = tmp_path / "tmp.tmp"
        tmp_file.write_text("new content")
        result = _atomic_link_with_disambiguation(tmp_file, tmp_path, "test.md")
        assert result == tmp_path / "test-2.md"
        assert result.read_text() == "new content"
        assert (tmp_path / "test.md").read_text() == "existing"

    def test_triple_disambiguate(self, tmp_path):
        (tmp_path / "test.md").write_text("first")
        (tmp_path / "test-2.md").write_text("second")
        tmp_file = tmp_path / "tmp.tmp"
        tmp_file.write_text("third")
        result = _atomic_link_with_disambiguation(tmp_file, tmp_path, "test.md")
        assert result == tmp_path / "test-3.md"

    def test_max_attempts_exceeded(self, tmp_path):
        for i in range(MAX_DISAMBIGUATE_ATTEMPTS):
            suffix = "" if i == 0 else f"-{i + 1}"
            (tmp_path / f"test{suffix}.md").write_text(f"file {i}")
        tmp_file = tmp_path / "tmp.tmp"
        tmp_file.write_text("overflow")
        with pytest.raises(CouncilError, match="Failed to find unique filename"):
            _atomic_link_with_disambiguation(tmp_file, tmp_path, "test.md")


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
        assert path.parent == tmp_path / ".aicouncil" / "history"

    def test_atomic_no_tmp_files(self, tmp_path, sample_metadata):
        write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        tmp_files = list((tmp_path / ".aicouncil" / "history").glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_creates_history_dir(self, tmp_path, sample_metadata):
        assert not (tmp_path / ".aicouncil" / "history").exists()
        write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert (tmp_path / ".aicouncil" / "history").is_dir()

    def test_file_includes_metadata(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "narrative here", project_root=tmp_path)
        content = path.read_text()
        assert "test-session-abc-123" in content
        assert "narrative here" in content

    def test_filename_format(self, tmp_path, sample_metadata):
        path = write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert path.name == "2026-03-22-stripe-connect-vs-direct-charges.md"

    def test_wraps_os_error(self, tmp_path, sample_metadata):
        bad_root = tmp_path / "no-write"
        bad_root.mkdir()
        history_dir = bad_root / ".aicouncil" / "history"
        history_dir.mkdir(parents=True)
        history_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            with pytest.raises(CouncilError, match="Failed to write council addendum"):
                write_council_addendum(sample_metadata, "content", project_root=bad_root)
        finally:
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
        assert "test-session-abc-123" in content

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
        assert len(path.name) <= 64

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

    def test_tmp_cleanup_on_os_error(self, tmp_path, sample_metadata):
        """Temp file cleaned up even on non-OSError failures."""
        history_dir = tmp_path / ".aicouncil" / "history"
        history_dir.mkdir(parents=True)
        with patch(
            "aicouncil.council.history._atomic_link_with_disambiguation",
            side_effect=CouncilError("test error"),
        ):
            with pytest.raises(CouncilError):
                write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        tmp_files = list(history_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_warning_logged_for_missing_dir(self, tmp_path, sample_metadata, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert "History directory missing" in caplog.text

    def test_info_logged_at_save_start(self, tmp_path, sample_metadata, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert "Saving addendum to" in caplog.text

    def test_info_logged_on_success(self, tmp_path, sample_metadata, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            write_council_addendum(sample_metadata, "content", project_root=tmp_path)
        assert "Addendum saved successfully" in caplog.text


# ---------------------------------------------------------------------------
# AddendumMetadata schema validation tests
# ---------------------------------------------------------------------------


class TestAddendumMetadataValidation:
    def test_valid_timestamp_accepted(self):
        m = AddendumMetadata(
            session_id="s1",
            topic="t1",
            agents=["a1"],
            model_assignments={"a1": "m1"},
            timestamp="2026-03-22T10:30:00+00:00",
        )
        assert m.timestamp == "2026-03-22T10:30:00+00:00"

    def test_invalid_timestamp_rejected(self):
        with pytest.raises(Exception, match="ISO 8601"):
            AddendumMetadata(
                session_id="s1",
                topic="t1",
                agents=["a1"],
                model_assignments={"a1": "m1"},
                timestamp="not-a-date",
            )

    def test_empty_agents_rejected(self):
        with pytest.raises(Exception):
            AddendumMetadata(
                session_id="s1",
                topic="t1",
                agents=[],
                model_assignments={},
                timestamp="2026-03-22T00:00:00+00:00",
            )


# ---------------------------------------------------------------------------
# AddendumSaveResult schema tests
# ---------------------------------------------------------------------------


class TestAddendumSaveResult:
    def test_valid_schema(self, sample_metadata):
        result = AddendumSaveResult(
            file_path=".aicouncil/history/file.md",
            addendum_content="narrative",
            metadata=sample_metadata,
        )
        assert result.file_path == ".aicouncil/history/file.md"
        assert result.addendum_content == "narrative"
        assert result.metadata.session_id == "test-session-abc-123"

    def test_nested_metadata_validation(self):
        result = AddendumSaveResult(
            file_path="file.md",
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
            mock_write.return_value = tmp_path / ".aicouncil" / "history" / "2026-03-22-test.md"

            with patch("aicouncil.tools.council.get_project_root", return_value=tmp_path):
                result = await save_council_addendum(
                    session_id="tool-test-123",
                    topic="Test Topic",
                    agents=["Agent A", "Agent B"],
                    model_assignments={"Agent A": "model-a", "Agent B": "model-b"},
                    addendum_content="The council decided X.",
                )

                assert isinstance(result, AddendumSaveResult)
                assert result.addendum_content == "The council decided X."
                assert result.metadata.session_id == "tool-test-123"
                assert result.metadata.topic == "Test Topic"
                mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_to_end_file_creation(self, tmp_path):
        from aicouncil.tools.council import save_council_addendum

        with patch("aicouncil.tools.council.get_project_root", return_value=tmp_path):
            result = await save_council_addendum(
                session_id="e2e-test",
                topic="End to End Test",
                agents=["Agent A"],
                model_assignments={"Agent A": "model-a"},
                addendum_content="Full narrative content.",
            )

            assert isinstance(result, AddendumSaveResult)
            assert result.addendum_content == "Full narrative content."
            assert result.file_path.startswith(".aicouncil/history/")
            assert (tmp_path / result.file_path).exists()

    @pytest.mark.asyncio
    async def test_returns_relative_path(self, tmp_path):
        from aicouncil.tools.council import save_council_addendum

        with patch("aicouncil.tools.council.get_project_root", return_value=tmp_path):
            result = await save_council_addendum(
                session_id="path-test",
                topic="Path Test",
                agents=["Agent A"],
                model_assignments={"Agent A": "model-a"},
                addendum_content="Content.",
            )

            assert not os.path.isabs(result.file_path)
            assert result.file_path.startswith(".aicouncil/history/")

    @pytest.mark.asyncio
    async def test_content_size_limit(self):
        from aicouncil.tools.council import MAX_ADDENDUM_CONTENT_BYTES, save_council_addendum

        with pytest.raises(CouncilError, match="exceeds maximum size"):
            await save_council_addendum(
                session_id="size-test",
                topic="Size Test",
                agents=["Agent A"],
                model_assignments={"Agent A": "model-a"},
                addendum_content="x" * (MAX_ADDENDUM_CONTENT_BYTES + 1),
            )
