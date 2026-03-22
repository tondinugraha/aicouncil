"""Tests for council context window management."""

import pytest

from aicouncil.council.context import (
    CHARS_PER_TOKEN,
    PROMPT_TEMPLATE_TOKENS,
    build_context_managed_history,
    estimate_tokens,
    summarize_entry,
)
from aicouncil.council.session import ConversationEntry
from aicouncil.exceptions import CouncilError


def _make_entry(
    agent_name: str = "Agent",
    agent_role: str = "Role",
    model: str = "model-a",
    round_number: int = 1,
    response: str = "A short response.",
    stance: str = "In favor",
    key_points: list[str] | None = None,
) -> ConversationEntry:
    return ConversationEntry(
        agent_name=agent_name,
        agent_role=agent_role,
        model=model,
        round_number=round_number,
        response=response,
        stance=stance,
        key_points=key_points or ["Point one", "Point two"],
    )


def _make_long_entry(
    agent_name: str = "Agent",
    round_number: int = 1,
    length: int = 2000,
) -> ConversationEntry:
    """Create an entry with a response of approximately `length` characters."""
    return _make_entry(
        agent_name=agent_name,
        round_number=round_number,
        response="x" * length,
        stance="Long stance",
        key_points=["Long point"],
    )


class TestEstimateTokens:
    def test_basic_estimation(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        # Fewer than CHARS_PER_TOKEN chars rounds down
        assert estimate_tokens("abc") == 0


class TestSummarizeEntry:
    def test_produces_condensed_format(self):
        entry = _make_entry(
            agent_name="Architect",
            agent_role="Principal Architect",
            stance="Strongly in favor",
            key_points=["Clean APIs matter", "Boundaries are key"],
        )
        result = summarize_entry(entry)
        assert "**Architect** (Principal Architect): Strongly in favor" in result
        assert "- Clean APIs matter" in result
        assert "- Boundaries are key" in result

    def test_much_shorter_than_full_response(self):
        entry = _make_entry(response="x" * 1000, stance="Short", key_points=["One"])
        summary = summarize_entry(entry)
        assert len(summary) < len(entry.response)

    def test_empty_key_points(self):
        entry = ConversationEntry(
            agent_name="Agent",
            agent_role="Role",
            model="model-a",
            round_number=1,
            response="A response.",
            stance="In favor",
            key_points=[],
        )
        result = summarize_entry(entry)
        assert "**Agent** (Role): In favor" in result
        assert "- " not in result


class TestBuildContextManagedHistory:
    def test_empty_entries_returns_empty(self):
        result = build_context_managed_history(
            entries=[],
            agent_persona="persona",
            context_window=100000,
            max_output_tokens=8192,
        )
        assert result == []

    def test_no_context_window_returns_full_history(self):
        entries = [_make_entry(), _make_entry(agent_name="B")]
        result = build_context_managed_history(
            entries=entries,
            agent_persona="persona",
            context_window=None,
            max_output_tokens=8192,
        )
        assert len(result) == 2
        assert result[0]["response"] == entries[0].response
        assert result[1]["response"] == entries[1].response

    def test_zero_context_window_returns_full_history(self):
        entries = [_make_entry()]
        result = build_context_managed_history(
            entries=entries,
            agent_persona="persona",
            context_window=0,
            max_output_tokens=8192,
        )
        assert len(result) == 1

    def test_within_budget_returns_full_history(self):
        entries = [_make_entry(response="Short.")]
        result = build_context_managed_history(
            entries=entries,
            agent_persona="Short persona",
            context_window=100000,
            max_output_tokens=8192,
        )
        assert len(result) == 1
        assert result[0]["response"] == "Short."

    def test_older_rounds_summarized(self):
        """When history exceeds budget, older rounds get summarized."""
        # Create entries that will exceed a small budget
        entries = [
            _make_long_entry(agent_name="A", round_number=1, length=3000),
            _make_long_entry(agent_name="B", round_number=1, length=3000),
            _make_long_entry(agent_name="A", round_number=2, length=3000),
            _make_long_entry(agent_name="B", round_number=2, length=3000),
        ]
        persona = "x" * 100

        # Budget: context_window // 2 - persona - template - output
        # Need a window where full history (~12000 chars = ~3000 tokens) exceeds budget
        # but summarized round 1 + full round 2 fits
        # Window of 20000: budget = 10000 - 25 - 300 - 1000 = 8675 tokens (~34700 chars)
        # Full: ~12000 chars = ~3000 tokens — fits
        # Window of 8000: budget = 4000 - 25 - 300 - 1000 = 2675 tokens (~10700 chars)
        # Full: ~12000 chars — exceeds. Summarized R1 + full R2 should fit.

        result = build_context_managed_history(
            entries=entries,
            agent_persona=persona,
            context_window=8000,
            max_output_tokens=1000,
        )

        # Round 2 entries should be full, round 1 entries should be summarized
        assert len(result) == 4
        # Round 1 entries should be condensed (stance + key_points, much shorter)
        assert len(result[0]["response"]) < 3000
        assert len(result[1]["response"]) < 3000
        # Round 2 entries should be full
        assert len(result[2]["response"]) == 3000
        assert len(result[3]["response"]) == 3000

    def test_oldest_rounds_dropped_when_still_over(self):
        """When summarized history still exceeds budget, oldest rounds are dropped."""
        entries = [
            _make_long_entry(agent_name="A", round_number=1, length=5000),
            _make_long_entry(agent_name="A", round_number=2, length=5000),
            _make_long_entry(agent_name="A", round_number=3, length=5000),
        ]

        # Very tight budget: only latest round should fit
        result = build_context_managed_history(
            entries=entries,
            agent_persona="x" * 100,
            context_window=6000,
            max_output_tokens=500,
        )

        # Should have dropped older rounds, keeping at least the latest
        assert len(result) >= 1
        # The last entry should be from round 3
        assert result[-1]["response"] == "x" * 5000

    def test_raises_when_persona_exceeds_budget(self):
        """CouncilError when persona alone blows the context budget."""
        entries = [_make_entry()]
        with pytest.raises(CouncilError, match="exceeds 50% of context window"):
            build_context_managed_history(
                entries=entries,
                agent_persona="x" * 100000,
                context_window=1000,
                max_output_tokens=8192,
            )

    def test_single_round_with_pressure_truncates(self):
        """When only one round exists and it exceeds budget, entries are truncated."""
        entries = [
            _make_long_entry(agent_name="A", round_number=1, length=5000),
            _make_long_entry(agent_name="B", round_number=1, length=5000),
            _make_long_entry(agent_name="C", round_number=1, length=5000),
        ]

        # Budget that fits ~1-2 entries but not 3
        # Window 8000: budget = 4000 - 25 - 300 - 500 = 3175 tokens = ~12700 chars
        # 3 entries x 5000 chars = 15000 chars — exceeds budget
        result = build_context_managed_history(
            entries=entries,
            agent_persona="x" * 100,
            context_window=8000,
            max_output_tokens=500,
        )

        # Should have fewer than 3 entries
        assert len(result) < 3
        # Most recent entries should be preserved
        assert result[-1]["agent_name"] == "C"

    def test_preserves_entry_format(self):
        """Each entry in the result has the expected dict keys."""
        entries = [_make_entry()]
        result = build_context_managed_history(
            entries=entries,
            agent_persona="p",
            context_window=100000,
            max_output_tokens=8192,
        )
        assert len(result) == 1
        entry = result[0]
        assert "agent_name" in entry
        assert "agent_role" in entry
        assert "response" in entry
