"""Council assembler — agent selection, model routing, and composition.

Pure logic module — no I/O, no HTTP calls. Receives classification results
and agent roster, returns assembled council composition.
"""

import logging
import random
from collections import Counter
from typing import Any

from aicouncil.config import Config
from aicouncil.council.schemas import (
    AgentAssignment,
    CouncilComposition,
    TopicClassification,
)
from aicouncil.exceptions import CouncilError
from aicouncil.schemas.agents import Agent, AgentRoster

logger = logging.getLogger(__name__)


def build_classification_prompt(topic: str, available_domains: set[str]) -> str:
    """Build the prompt for LLM-powered topic classification.

    Args:
        topic: The user's topic/question.
        available_domains: Domain names from config capability weights.

    Returns:
        Prompt string for the classification LLM call.
    """
    domains_list = ", ".join(sorted(available_domains))
    return (
        f"You are a topic classifier. Analyze the following topic and score its relevance "
        f"to each of the available capability domains.\n\n"
        f"Topic: {topic}\n\n"
        f"Available domains: {domains_list}\n\n"
        f"For each domain, assign a relevance score from 0.0 (not relevant) to 1.0 "
        f"(highly relevant). Include only domains with score > 0.0 in the domains list. "
        f"Provide brief reasoning for your classification.\n\n"
        f"Return a JSON object with these fields:\n"
        f'- "topic": the original topic string\n'
        f'- "domains": list of relevant domain names (score > 0.0)\n'
        f'- "domain_scores": object mapping each domain name to its relevance score\n'
        f'- "reasoning": brief explanation of why these domains are relevant'
    )


def extract_available_domains(config: Config) -> set[str]:
    """Extract all unique domain names from the config's capability weights.

    Args:
        config: Config instance.

    Returns:
        Set of domain names (e.g., {"coding", "analysis", "creative"}).
    """
    model_pool = config.get_model_pool()
    all_domains: set[str] = set()
    for model in model_pool:
        weights = config.get_capability_weights(model)
        if weights:
            all_domains.update(weights.domain_scores().keys())
    return all_domains


class CouncilAssembler:
    """Assembles a council by selecting agents and assigning models.

    This is a pure logic class — it does not make HTTP calls or read files.
    The LLM classification call is owned by the tool layer (tools/council.py).
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    def assemble(
        self,
        classification: TopicClassification,
        roster: AgentRoster,
        session_id: str,
        council_size: int = 7,
        pinned_agents: list[str] | None = None,
        include_user_agents: bool = True,
        include_wildcard: bool = True,
    ) -> CouncilComposition:
        """Assemble a council composition from classification and roster.

        Args:
            classification: LLM-produced topic classification.
            roster: Full agent roster.
            session_id: UUID for this council session.
            council_size: Target number of agents.
            pinned_agents: Optional list of agent names to pin.
            include_user_agents: Whether to include user-type agents.
            include_wildcard: Whether to include wildcard agents.

        Returns:
            CouncilComposition with all assignments and metrics.

        Raises:
            CouncilError: If model pool is empty or roster is empty.
        """
        if council_size < 1:
            raise CouncilError(f"council_size must be >= 1, got {council_size}")

        model_pool = self._config.get_model_pool()
        if not model_pool:
            raise CouncilError("No models in model pool — check config.yaml")

        if not roster.agents:
            raise CouncilError("Agent roster is empty — no agents available for council")

        # Step 1: Handle pinned agents
        pinned_assignments: list[AgentAssignment] = []
        pinned_names: set[str] = set()
        if pinned_agents:
            for name in pinned_agents:
                agent = roster.get_by_name(name)
                if agent:
                    pinned_names.add(agent.name.lower())
                    assignment = self._assign_model(
                        agent, classification, model_pool, is_pinned=True
                    )
                    pinned_assignments.append(assignment)
                    logger.info(
                        "[council:%s] Pinned agent: %s on %s",
                        session_id,
                        agent.name,
                        assignment.assigned_model,
                    )
                else:
                    logger.warning(
                        "[council:%s] Pinned agent '%s' not found in roster", session_id, name
                    )

        remaining_seats = max(0, council_size - len(pinned_assignments))

        # Step 2: Select agents
        selected = self._select_agents(
            classification=classification,
            roster=roster,
            count=remaining_seats,
            exclude_names=pinned_names,
            include_user_agents=include_user_agents,
            include_wildcard=include_wildcard,
            session_id=session_id,
        )

        # Step 3: Assign models to selected agents
        auto_assignments: list[AgentAssignment] = []
        for agent, is_wildcard in selected:
            assignment = self._assign_model(
                agent, classification, model_pool, is_wildcard=is_wildcard
            )
            auto_assignments.append(assignment)

        all_assignments = pinned_assignments + auto_assignments

        # Step 4: Compute diversity metrics
        diversity_metrics = self._compute_diversity_metrics(all_assignments)

        logger.info(
            "[council:%s] Council assembled: %d agents",
            session_id,
            len(all_assignments),
        )

        return CouncilComposition(
            session_id=session_id,
            topic=classification.topic,
            classification=classification,
            assignments=all_assignments,
            council_size=len(all_assignments),
            diversity_metrics=diversity_metrics,
        )

    def _score_agent(self, agent: Agent, classification: TopicClassification) -> float:
        """Score an agent's relevance to the classified topic.

        Uses domain overlap between agent domains and classification domain scores.
        Unmatched domains contribute a small normalized bonus so many-domain agents
        with zero relevance cannot outscore genuinely relevant agents.
        """
        if not agent.domains:
            return 0.0
        score = 0.0
        unmatched_bonus = 0.3 / len(agent.domains)
        for domain in agent.domains:
            domain_lower = domain.lower().replace("_", " ")
            matched = False
            for cls_domain, cls_score in classification.domain_scores.items():
                cls_lower = cls_domain.lower().replace("_", " ")
                if cls_lower in domain_lower or domain_lower in cls_lower:
                    score += cls_score
                    matched = True
                    break
            if not matched:
                score += unmatched_bonus
        return score

    def _select_agents(
        self,
        classification: TopicClassification,
        roster: AgentRoster,
        count: int,
        exclude_names: set[str],
        include_user_agents: bool,
        include_wildcard: bool,
        session_id: str,
    ) -> list[tuple[Agent, bool]]:
        """Select agents based on relevance, category mix, tier, and wildcard rules.

        Returns list of (Agent, is_wildcard) tuples.
        """
        if count <= 0:
            return []

        # Filter available agents
        available = [a for a in roster.agents if a.name.lower() not in exclude_names]

        # Filter user agents based on include_flag
        if include_user_agents:
            available = [a for a in available if a.type != "user" or a.include_flag]
        else:
            available = [a for a in available if a.type != "user"]

        if not available:
            return []

        # Score all agents
        scored = [(a, self._score_agent(a, classification)) for a in available]

        # Separate wildcard candidates (zero domain overlap with topic)
        wildcard_candidates = []
        relevant_candidates = []
        for agent, score in scored:
            has_overlap = any(
                any(
                    cls_d.lower().replace("_", " ") in d.lower().replace("_", " ")
                    or d.lower().replace("_", " ") in cls_d.lower().replace("_", " ")
                    for cls_d in classification.domain_scores
                )
                for d in agent.domains
            )
            if has_overlap:
                relevant_candidates.append((agent, score))
            else:
                wildcard_candidates.append((agent, score))

        # Calculate wildcard seats (5:1 ratio, inclusive of council_size)
        wildcard_seats = 0
        if include_wildcard and wildcard_candidates:
            wildcard_seats = max(1, count // 5)
        relevant_seats = count - wildcard_seats

        # Sort relevant by: score desc, then tier asc (prefer tier 1)
        relevant_candidates.sort(key=lambda x: (-x[1], x[0].tier))

        # Balance category mix: ~60% experts, ~25% builders, ~15% users
        selected: list[tuple[Agent, bool]] = []

        if relevant_seats <= 0:
            # No relevant seats — skip category balancing, only wildcards
            pass
        else:
            # Group by type
            experts = [(a, s) for a, s in relevant_candidates if a.type == "expert"]
            builders = [(a, s) for a, s in relevant_candidates if a.type == "builder"]
            users = [(a, s) for a, s in relevant_candidates if a.type == "user"]

            target_experts = max(1, round(relevant_seats * 0.6))
            target_builders = max(1, round(relevant_seats * 0.25)) if builders else 0
            target_users = max(1, round(relevant_seats * 0.15)) if users else 0

            # Adjust to not exceed relevant_seats
            total_target = target_experts + target_builders + target_users
            if total_target > relevant_seats:
                target_experts = max(0, relevant_seats - target_builders - target_users)

            # Pick from each category
            for agent, _ in experts[:target_experts]:
                selected.append((agent, False))
            for agent, _ in builders[:target_builders]:
                selected.append((agent, False))
            for agent, _ in users[:target_users]:
                selected.append((agent, False))

            # Fill remaining seats from best remaining relevant candidates
            selected_names = {a.name.lower() for a, _ in selected}
            remaining = [
                (a, s) for a, s in relevant_candidates if a.name.lower() not in selected_names
            ]
            remaining.sort(key=lambda x: (-x[1], x[0].tier))
            for agent, _ in remaining:
                if len(selected) >= relevant_seats:
                    break
                selected.append((agent, False))

        # Add wildcard agents
        if wildcard_seats > 0 and wildcard_candidates:
            wildcard_candidates.sort(key=lambda x: x[0].tier)
            for agent, _ in wildcard_candidates[:wildcard_seats]:
                selected.append((agent, True))
                logger.debug(
                    "[council:%s] Wildcard agent: %s (domains: %s)",
                    session_id,
                    agent.name,
                    agent.domains,
                )

        return selected

    def _assign_model(
        self,
        agent: Agent,
        classification: TopicClassification,
        model_pool: list[str],
        is_wildcard: bool = False,
        is_pinned: bool = False,
    ) -> AgentAssignment:
        """Assign a model to an agent using capability-weighted random routing (60/40).

        60% chance of highest-scoring model for the agent's primary domain,
        40% weighted random from all models.
        """
        primary_domain = self._get_primary_domain(agent, classification)

        scored: list[tuple[str, float]] = []
        for model in model_pool:
            weights = self._config.get_capability_weights(model)
            raw_score = weights.get_domain_score(primary_domain) if weights else None
            if raw_score is None:
                logger.debug(
                    "[council] Domain '%s' not found in capability weights for model '%s'",
                    primary_domain,
                    model,
                )
                raw_score = 0.5
            scored.append((model, max(raw_score, 0.01)))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_model = scored[0][0]

        if random.random() < 0.6:
            chosen_model = top_model
        else:
            models, w = zip(*scored)
            chosen_model = random.choices(list(models), weights=list(w), k=1)[0]

        context_window = self._config.get_context_window(chosen_model)

        return AgentAssignment(
            agent_name=agent.name,
            agent_role=agent.role,
            agent_type=agent.type,
            agent_tier=agent.tier,
            assigned_model=chosen_model,
            context_window=context_window,
            assignment_reasoning=(
                f"Domain '{primary_domain}' matched via capability-weighted routing"
            ),
            is_wildcard=is_wildcard,
            is_pinned=is_pinned,
            persona=agent.persona,
        )

    def _get_primary_domain(self, agent: Agent, classification: TopicClassification) -> str:
        """Get the agent's primary domain — highest-scored from classification, or first domain."""
        if not agent.domains:
            logger.warning(
                "[council] Agent '%s' has no domains — falling back to 'general'", agent.name
            )
            return "general"
        best_domain = agent.domains[0]
        best_score = -1.0

        for domain in agent.domains:
            domain_lower = domain.lower().replace("_", " ")
            for cls_domain, cls_score in classification.domain_scores.items():
                cls_lower = cls_domain.lower().replace("_", " ")
                if cls_lower in domain_lower or domain_lower in cls_lower:
                    if cls_score > best_score:
                        best_score = cls_score
                        best_domain = cls_domain
                    break

        return best_domain

    def _compute_diversity_metrics(self, assignments: list[AgentAssignment]) -> dict[str, Any]:
        """Compute diversity metrics for the council composition."""
        type_counts = Counter(a.agent_type for a in assignments)
        tier_counts = Counter(a.agent_tier for a in assignments)
        model_counts = Counter(a.assigned_model for a in assignments)
        wildcard_count = sum(1 for a in assignments if a.is_wildcard)
        pinned_count = sum(1 for a in assignments if a.is_pinned)

        return {
            "type_distribution": dict(type_counts),
            "tier_distribution": dict(tier_counts),
            "model_distribution": dict(model_counts),
            "unique_models": len(model_counts),
            "wildcard_count": wildcard_count,
            "pinned_count": pinned_count,
        }

    def build_orchestration_notes(self, composition: CouncilComposition) -> str:
        """Build orchestration notes string from the composition."""
        assignments = composition.assignments
        type_counts = Counter(a.agent_type for a in assignments)
        unique_models = len(set(a.assigned_model for a in assignments))
        wildcard_count = sum(1 for a in assignments if a.is_wildcard)
        domains = ", ".join(composition.classification.domains)
        sanitized_topic = composition.topic.replace("\n", " ").replace("\r", "")[:100]

        parts = [
            f"Council of {len(assignments)} agents assembled for topic '{sanitized_topic}'.",
            f"Domains: {domains}.",
        ]

        type_parts = []
        for t in ("expert", "builder", "user"):
            if type_counts.get(t, 0) > 0:
                label = f"{type_counts[t]} {t}{'s' if type_counts[t] > 1 else ''}"
                if t == "user":
                    label = f"{type_counts[t]} user perspective{'s' if type_counts[t] > 1 else ''}"
                type_parts.append(label)
        if type_parts:
            parts.append(", ".join(type_parts) + ".")

        if wildcard_count > 0:
            wc_names = [a.agent_name for a in assignments if a.is_wildcard]
            parts.append(
                f"{wildcard_count} wildcard ({', '.join(wc_names)}) for cross-domain insight."
            )

        parts.append(
            f"Models: {unique_models} unique model{'s' if unique_models > 1 else ''} assigned."
        )
        parts.append("Host AI should direct deliberation as chairperson.")

        return " ".join(parts)
