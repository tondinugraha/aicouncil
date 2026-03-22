"""Context window management for council deliberations.

Ensures conversation history stays within a model's context budget by
summarizing older rounds when the total prompt would exceed 50% of the
model's context window. Summarization is rule-based — it uses the
structured stance + key_points already captured in each ConversationEntry,
so no additional LLM calls are needed.
"""

import logging
from itertools import groupby
from operator import attrgetter

from aicouncil.council.session import ConversationEntry
from aicouncil.exceptions import CouncilError

logger = logging.getLogger(__name__)

# Rough estimate: ~4 chars per token (works across most models)
CHARS_PER_TOKEN = 4

# Static estimate for the fixed prompt template wrapper
# (preamble, JSON instructions, section headers, etc.)
PROMPT_TEMPLATE_TOKENS = 300


def estimate_tokens(text: str) -> int:
    """Estimate token count from character length."""
    return len(text) // CHARS_PER_TOKEN


def summarize_entry(entry: ConversationEntry) -> str:
    """Condense a ConversationEntry into stance + key points.

    Produces ~80-90% size reduction vs the full response while
    preserving the actionable content.
    """
    lines = [f"**{entry.agent_name}** ({entry.agent_role}): {entry.stance}"]
    for point in entry.key_points:
        lines.append(f"- {point}")
    return "\n".join(lines)


def _format_full_entry(entry: ConversationEntry) -> dict[str, str]:
    """Format a ConversationEntry as a full history dict for the prompt builder."""
    return {
        "agent_name": entry.agent_name,
        "agent_role": entry.agent_role,
        "response": entry.response,
    }


def _format_summarized_entry(entry: ConversationEntry) -> dict[str, str]:
    """Format a ConversationEntry as a summarized history dict."""
    return {
        "agent_name": entry.agent_name,
        "agent_role": entry.agent_role,
        "response": summarize_entry(entry),
    }


def _entries_by_round(
    entries: list[ConversationEntry],
) -> list[tuple[int, list[ConversationEntry]]]:
    """Group entries by round_number, preserving order."""
    sorted_entries = sorted(entries, key=attrgetter("round_number"))
    return [
        (round_num, list(group))
        for round_num, group in groupby(sorted_entries, key=attrgetter("round_number"))
    ]


def _estimate_history_tokens(history: list[dict[str, str]]) -> int:
    """Estimate total tokens across all history entries."""
    total = 0
    for entry in history:
        total += estimate_tokens(entry.get("response", ""))
        total += estimate_tokens(entry.get("agent_name", ""))
        total += estimate_tokens(entry.get("agent_role", ""))
    return total


def build_context_managed_history(
    entries: list[ConversationEntry],
    agent_persona: str,
    context_window: int | None,
    max_output_tokens: int,
) -> list[dict[str, str]]:
    """Build conversation history that fits within the model's context budget.

    Strategy (tiered):
      1. If everything fits, return full history.
      2. Summarize older rounds (keep latest round in full).
      3. If still over, drop oldest summarized rounds progressively.
      4. If still over, truncate latest round to most recent K entries.

    Args:
        entries: All conversation entries from the session.
        agent_persona: Full markdown persona for the speaking agent.
        context_window: Model's total context window in tokens (None = no limit).
        max_output_tokens: Reserved tokens for the model's response.

    Returns:
        List of history dicts compatible with build_council_speak_prompt.

    Raises:
        CouncilError: If the persona + prompt alone exceed the budget.
    """
    if not entries:
        return []

    # No context window info — return full history (can't manage what we can't measure)
    if context_window is None or context_window <= 0:
        return [_format_full_entry(e) for e in entries]

    # Budget = 50% of context window minus persona, prompt template, and output reservation
    persona_tokens = estimate_tokens(agent_persona)
    budget = (context_window // 2) - persona_tokens - PROMPT_TEMPLATE_TOKENS - max_output_tokens

    if budget <= 0:
        raise CouncilError(
            f"Agent persona ({persona_tokens} est. tokens) + output reservation "
            f"({max_output_tokens} tokens) exceeds 50% of context window "
            f"({context_window} tokens). Cannot fit any conversation history."
        )

    # Try full history first
    full_history = [_format_full_entry(e) for e in entries]
    full_tokens = _estimate_history_tokens(full_history)

    if full_tokens <= budget:
        logger.debug("Context OK: %d est. tokens within budget of %d", full_tokens, budget)
        return full_history

    logger.info(
        "Context pressure: %d est. tokens exceeds budget of %d — summarizing older rounds",
        full_tokens,
        budget,
    )

    # Tier 1: Summarize older rounds, keep latest round in full
    rounds = _entries_by_round(entries)
    if len(rounds) <= 1:
        # Only one round — can't summarize older rounds, try truncating entries
        return _truncate_latest_round(entries, budget)

    latest_round_num = rounds[-1][0]
    history: list[dict[str, str]] = []

    # Summarize all rounds except the latest
    for round_num, round_entries in rounds:
        if round_num == latest_round_num:
            for entry in round_entries:
                history.append(_format_full_entry(entry))
        else:
            for entry in round_entries:
                history.append(_format_summarized_entry(entry))

    current_tokens = _estimate_history_tokens(history)
    if current_tokens <= budget:
        logger.info(
            "Context resolved via summarization: %d est. tokens (budget: %d)",
            current_tokens,
            budget,
        )
        return history

    # Tier 2: Drop oldest summarized rounds progressively
    summarized_rounds = [r for r in rounds if r[0] != latest_round_num]
    latest_entries = [_format_full_entry(e) for e in rounds[-1][1]]

    for i in range(len(summarized_rounds)):
        # Keep only the most recent summarized rounds
        kept_rounds = summarized_rounds[i + 1 :]
        history = []
        for _, round_entries in kept_rounds:
            for entry in round_entries:
                history.append(_format_summarized_entry(entry))
        history.extend(latest_entries)

        current_tokens = _estimate_history_tokens(history)
        if current_tokens <= budget:
            dropped = i + 1
            logger.warning(
                "Context resolved by dropping %d oldest round(s): %d est. tokens (budget: %d)",
                dropped,
                current_tokens,
                budget,
            )
            return history

    # Tier 3: Even latest round alone exceeds budget — truncate to most recent K entries
    logger.warning("Context pressure: even latest round exceeds budget — truncating entries")
    return _truncate_latest_round(rounds[-1][1], budget)


def _truncate_latest_round(
    entries: list[ConversationEntry],
    budget: int,
) -> list[dict[str, str]]:
    """Keep only the most recent K entries that fit within the budget."""
    history: list[dict[str, str]] = []

    # Work backwards from the most recent entry
    for entry in reversed(entries):
        candidate = _format_full_entry(entry)
        candidate_tokens = _estimate_history_tokens([candidate])
        remaining = budget - _estimate_history_tokens(history)

        if candidate_tokens <= remaining:
            history.insert(0, candidate)
        else:
            break

    if not history and entries:
        # At minimum, include the last entry even if it's over budget
        # (the model will truncate, but at least it has the most recent context)
        history = [_format_full_entry(entries[-1])]
        logger.warning("Context critical: only most recent entry fits within budget")

    return history
