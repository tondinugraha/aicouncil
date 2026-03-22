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
    AddendumGuidance,
    AgentAssignment,
    AgentDomainWeight,
    ChairpersonInstructions,
    ConsensusAndSynthesisData,
    ConsensusRoundGuidance,
    ContextWindowInfo,
    ConvergenceGuidance,
    CouncilComposition,
    DeadlockResolutionGuidance,
    OrchestrationData,
    TieredConsensusGuidance,
    ToneGuidance,
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

        # Filter available agents — exclude_flag: false agents are never eligible
        available = [
            a
            for a in roster.agents
            if a.name.lower() not in exclude_names and a.include_flag
        ]

        # Filter user-type agents if not requested
        if not include_user_agents:
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
            domains=agent.domains,
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

    def build_orchestration_data(self, composition: CouncilComposition) -> OrchestrationData:
        """Build complete orchestration data from the assembled council."""
        if not composition.assignments:
            raise CouncilError("Cannot build orchestration data for empty council")
        summary = self._build_orchestration_notes(composition)
        chairperson = self._build_chairperson_instructions(composition)
        tone = self._build_tone_guidance(composition)
        convergence = self._build_convergence_guidance()
        context_windows = self._build_context_windows(composition)
        consensus = self._build_consensus_and_synthesis(composition)

        return OrchestrationData(
            chairperson=chairperson,
            tone=tone,
            convergence=convergence,
            consensus=consensus,
            context_windows=context_windows,
            agent_count=len(composition.assignments),
            summary=summary,
        )

    def _build_chairperson_instructions(
        self, composition: CouncilComposition
    ) -> ChairpersonInstructions:
        """Build chairperson instructions from council composition."""
        # Group agents by type for speaking order
        grouped: dict[str, list[str]] = {"expert": [], "builder": [], "user": []}
        for a in composition.assignments:
            grouped.setdefault(a.agent_type, []).append(f"{a.agent_name} ({a.agent_role})")

        known_types = {"expert", "builder", "user"}
        for agent_type in grouped:
            if agent_type not in known_types:
                logger.warning(
                    "[council] Unknown agent type '%s' — agents of this type will not appear "
                    "in chairperson speaking order",
                    agent_type,
                )

        roster_lines = []
        for agent_type in ("expert", "builder", "user"):
            if grouped.get(agent_type):
                roster_lines.append(
                    f"  {agent_type.capitalize()}s: {', '.join(grouped[agent_type])}"
                )

        roster_str = "\n".join(roster_lines)

        speaking_order = (
            "Address agents in rounds. Each round, have every agent respond to the topic or "
            "to the previous round's positions. Vary speaking order between rounds to prevent "
            "anchoring bias. Start with domain experts most relevant to the topic, then builders, "
            "then user perspectives. In subsequent rounds, let dissenters speak first to ensure "
            "minority positions get airtime.\n\n"
            f"Council:\n{roster_str}"
        )

        # Build domain-specific debate trigger
        domains = composition.classification.domains
        domain_trigger = (
            f"A critical perspective from {'/'.join(domains)} is not being challenged"
            if domains
            else "A critical domain perspective is not being challenged"
        )

        debate_triggers = (
            "Introduce adversarial debate when:\n"
            "- All agents agree on a position within the first 1-2 rounds (premature convergence)\n"
            f"- {domain_trigger}\n"
            "- A convenience-first proposal hasn't been stress-tested\n\n"
            "Devil's advocate technique: Ask a specific agent to argue the opposite position. "
            "Choose agents whose domain gives them standing to challenge."
        )

        conclusion_driving = (
            "Drive toward conclusion when:\n"
            "- Key positions are well-established and repeated across agents\n"
            "- New rounds are producing diminishing novel insights\n"
            "- Major disagreements have been explored from multiple angles\n\n"
            "Conclusion technique: Summarize areas of agreement, then explicitly ask each agent "
            "for a one-sentence final position on remaining disagreements."
        )

        # Topic framing from classification
        scores = composition.classification.domain_scores
        score_parts = [f"{d} ({s:.1f})" for d, s in sorted(scores.items(), key=lambda x: -x[1])]
        domains_label = "/".join(domains) if domains else "the primary domain"
        domains_scores_label = ", ".join(score_parts) if score_parts else "unclassified"
        topic_framing = (
            f"Topic: '{composition.topic}'\n"
            f"Primary domains: {domains_scores_label}\n"
            f"Frame this as a {domains_label} question. "
            f"Ensure agents address all domain perspectives."
        )

        return ChairpersonInstructions(
            speaking_order=speaking_order,
            debate_triggers=debate_triggers,
            conclusion_driving=conclusion_driving,
            topic_framing=topic_framing,
        )

    def _build_tone_guidance(self, composition: CouncilComposition) -> ToneGuidance:
        """Build tone guidance based on council composition and topic."""
        scores = composition.classification.domain_scores
        domains = composition.classification.domains
        max_score = max(scores.values()) if scores else 0.0

        # Determine default tone based on topic nature
        safety_domains = {"security", "safety", "risk", "compliance"}
        has_safety = any(d.lower() in safety_domains for d in domains)

        if has_safety:
            default_tone = (
                "Risk-aware: Prioritize surfacing risks and potential failure modes before "
                "evaluating solutions. Safety/security concerns take precedence."
            )
        elif len(domains) > 1 and max_score <= 0.8:
            default_tone = (
                "Structured debate: Each domain expert presents their perspective first, "
                "establishing the multi-faceted nature of the topic before cross-examination."
            )
        else:
            default_tone = (
                "Exploratory: Gather diverse perspectives and approaches before narrowing. "
                "Encourage creative and unconventional viewpoints early."
            )

        adversarial_triggers = (
            "Shift to adversarial/devil's advocate when:\n"
            "- More than 2/3 of agents agree on a position before round 3\n"
            "- A domain expert's core concern is being dismissed by majority\n"
            "- The topic involves risk/cost tradeoffs where the 'easy' option is being favored\n"
            "- Wildcard agent raises a cross-domain concern that gets ignored"
        )

        agreement_triggers = (
            "Shift to agreement-seeking when:\n"
            "- Key disagreements have been explored for 2+ rounds\n"
            "- Agents are repeating positions without new arguments\n"
            "- A compromise position has been proposed and partially endorsed\n"
            "- Domain experts in the most relevant domains are aligned"
        )

        tone_shift_rules = (
            "- Never stay in adversarial mode for more than 2 consecutive rounds\n"
            "- Return to exploratory/structured mode after adversarial challenge\n"
            "- If adversarial mode produces new insights, continue exploring those\n"
            "- Agreement-seeking is the final phase — once entered, don't revert to adversarial "
            "unless a genuinely new concern surfaces"
        )

        return ToneGuidance(
            default_tone=default_tone,
            adversarial_triggers=adversarial_triggers,
            agreement_triggers=agreement_triggers,
            tone_shift_rules=tone_shift_rules,
        )

    def _build_convergence_guidance(self) -> ConvergenceGuidance:
        """Build convergence evaluation criteria."""
        return ConvergenceGuidance(
            evaluation_criteria=(
                "After each round, evaluate:\n"
                "1. Position clustering — Are agents grouping into distinct camps, or is there a "
                "dominant position?\n"
                "2. Novelty — Did this round surface new arguments, or are agents repeating?\n"
                "3. Domain alignment — Are the most domain-relevant experts converging?\n"
                "4. Wildcard insight — Has the wildcard agent contributed a unique perspective?"
            ),
            continue_signals=(
                "Continue deliberation when:\n"
                "- New arguments or perspectives emerged in the last round\n"
                "- A domain expert strongly dissents and hasn't been adequately addressed\n"
                "- The wildcard agent raised a cross-domain concern that hasn't been explored\n"
                "- Less than half the council has stated a clear position"
            ),
            consensus_signals=(
                "Drive toward consensus when:\n"
                "- Agents are restating previous positions with minor variations\n"
                "- Domain experts in the primary domains are aligned\n"
                "- Remaining disagreements are about implementation details, not direction\n"
                "- 3+ rounds have passed with diminishing novelty per round"
            ),
            no_fixed_rounds=(
                "There is no fixed round limit. Evaluate dynamically after each round. A simple "
                "topic with early convergence may conclude in 2 rounds. A complex multi-domain "
                "topic with genuine disagreement may run 5+ rounds. Quality of conclusion matters "
                "more than speed."
            ),
        )

    def _build_context_windows(self, composition: CouncilComposition) -> list[ContextWindowInfo]:
        """Build context window metadata for adaptive context management."""
        seen_models: set[str] = set()
        windows: list[ContextWindowInfo] = []
        for assignment in composition.assignments:
            model = assignment.assigned_model
            if model in seen_models:
                continue
            seen_models.add(model)
            cw = assignment.context_window
            if cw is not None and cw > 0:
                windows.append(
                    ContextWindowInfo(
                        model=model,
                        context_window=cw,
                    )
                )
        return windows

    def _build_consensus_and_synthesis(
        self, composition: CouncilComposition
    ) -> ConsensusAndSynthesisData:
        """Build consensus round guidance and addendum format instructions."""
        agent_weights = self._compute_agent_domain_weights(composition)
        return ConsensusAndSynthesisData(
            consensus_round=self._build_consensus_round_guidance(),
            deadlock_resolution=self._build_deadlock_resolution_guidance(agent_weights),
            tiered_consensus=self._build_tiered_consensus_guidance(),
            addendum=self._build_addendum_guidance(),
        )

    def _compute_agent_domain_weights(
        self, composition: CouncilComposition
    ) -> list[AgentDomainWeight]:
        """Compute per-agent domain relevance from topic classification and agent domains."""
        topic_domains = composition.classification.domain_scores
        # Normalise topic domain keys for case/underscore-insensitive matching
        norm_topic: dict[str, str] = {k.lower().replace("_", " "): k for k in topic_domains}
        weights: list[AgentDomainWeight] = []
        for assignment in composition.assignments:
            matched_original: list[str] = []
            for d in assignment.domains:
                norm_d = d.lower().replace("_", " ")
                if norm_d in norm_topic:
                    matched_original.append(norm_topic[norm_d])
            if matched_original and norm_topic:
                relevance = sum(topic_domains[d] for d in matched_original) / len(norm_topic)
            else:
                relevance = 0.0
            weights.append(
                AgentDomainWeight(
                    agent_name=assignment.agent_name,
                    agent_role=assignment.agent_role,
                    relevance_score=round(min(relevance, 1.0), 2),
                    matched_domains=sorted(matched_original),
                )
            )
        return weights

    def _build_consensus_round_guidance(self) -> ConsensusRoundGuidance:
        """Build consensus round instructions."""
        return ConsensusRoundGuidance(
            format_instructions=(
                "Conduct a final consensus round. Ask each agent for exactly one sentence: "
                "their position (endorse or dissent) and their single most important caveat.\n\n"
                "Format per agent: '[Agent Name]: [Endorse/Dissent] — [One key caveat]'\n\n"
                "Example:\n"
                "'Tax Advisor: Endorse — but only if quarterly filings are automated'\n"
                "'Security Engineer: Dissent — custom JWT creates unacceptable PCI exposure'\n\n"
                "Collect ALL agent statements before evaluating consensus."
            ),
            unanimity_goal=(
                "Primary goal is unanimous consensus. Before accepting dissent:\n"
                "1. Ask dissenters if the majority position addresses their core concern\n"
                "2. Propose a compromise that incorporates the dissenter's caveat\n"
                "3. If the dissenter's concern is domain-specific and the domain experts agree "
                "it's addressed, note the original dissent but record practical consensus\n\n"
                "Only fall back to tiered consensus after genuine attempts at unanimity."
            ),
            dissent_handling=(
                "Dissent is valuable, not a failure. When recording dissent:\n"
                "- State the dissenter's position clearly and charitably\n"
                "- Note their domain authority on the point of disagreement\n"
                "- Explain why the majority position was adopted despite the dissent\n"
                "- Preserve the dissenting argument in the addendum for future reference"
            ),
        )

    def _build_deadlock_resolution_guidance(
        self, agent_weights: list[AgentDomainWeight]
    ) -> DeadlockResolutionGuidance:
        """Build deadlock resolution rules with agent domain weights."""
        weight_lines = (
            "\n".join(
                f"- {w.agent_name} ({w.relevance_score:.2f})"
                f" — {', '.join(w.matched_domains) or 'no domain match'}"
                for w in agent_weights
            )
            or "No agents in council."
        )
        return DeadlockResolutionGuidance(
            resolution_rules=(
                "When agents disagree on a domain-specific point, weight opinions by domain "
                "relevance:\n"
                "- Higher relevance_score = greater authority on the specific point\n"
                "- A domain expert's position on their domain outweighs a generalist's opinion\n"
                "- Equal relevance agents: consider the strength of their reasoning, not just "
                "the score\n"
                "- Cross-domain concerns (wildcard agents) are noted but don't override domain "
                "authority\n\n"
                f"Agent domain weights for this council:\n{weight_lines}"
            ),
            transparency_rules=(
                "Domain weighting must be transparent in the addendum:\n"
                "- When a position is adopted based on domain authority, state this explicitly "
                "(e.g., 'The Tax Advisor's position on 1099-K reporting is given priority as "
                "the most domain-relevant perspective')\n"
                "- When weighting resolves a tie, list the weights that informed the decision\n"
                "- Never silently dismiss a position — always explain the resolution"
            ),
            agent_weights=agent_weights,
        )

    def _build_tiered_consensus_guidance(self) -> TieredConsensusGuidance:
        """Build tiered consensus fallback rules."""
        return TieredConsensusGuidance(
            tier_definitions=(
                "When unanimity is not achievable, structure conclusions in tiers:\n\n"
                "Tier 1 — Universal Agreement: Positions ALL agents endorse.\n"
                "  Prefix: 'The council unanimously recommends...'\n\n"
                "Tier 2 — Strong Majority: Positions most agents endorse (>=2/3).\n"
                "  Prefix: 'The majority of the council recommends...'\n"
                "  Include: count of endorsements, note dissenters by name and domain\n\n"
                "Tier 3 — Divided: Positions where the council is split.\n"
                "  Prefix: 'The council is divided on...'\n"
                "  Include: both positions with supporting agents, domain-weighted assessment "
                "of which position has stronger domain authority"
            ),
            escalation_rules=(
                "Accept tiered consensus when:\n"
                "- 2+ attempts at unanimity have been made with specific compromise proposals\n"
                "- Dissenters have domain authority that makes their position non-dismissible\n"
                "- The disagreement is genuinely substantive (not a misunderstanding)\n\n"
                "Continue pushing for unanimity when:\n"
                "- The disagreement stems from different information, not different values\n"
                "- A compromise hasn't been explicitly proposed yet\n"
                "- Domain experts haven't been asked to evaluate the point of disagreement"
            ),
        )

    def _build_addendum_guidance(self) -> AddendumGuidance:
        """Build addendum format and content guidance."""
        return AddendumGuidance(
            structure=(
                "The addendum is a detail-preserving narrative. Recommended flow:\n\n"
                "1. TOPIC & CONTEXT: What was asked and why it matters\n"
                "2. COUNCIL COMPOSITION: Who participated, their domains, and model assignments\n"
                "3. KEY POSITIONS: The major positions that emerged during deliberation, "
                "with the reasoning behind each\n"
                "4. POINTS OF DEBATE: Where agents disagreed and how those debates unfolded\n"
                "5. CONSENSUS: The conclusion — unanimous or tiered — with clear recommendations\n"
                "6. DISSENTING VIEWS: Any positions that weren't adopted, preserved with "
                "reasoning\n"
                "7. KEY CAVEATS: Conditions, risks, or assumptions underlying the recommendation"
                "\n\n"
                "This is a narrative, not a template. Adapt the structure to fit the actual "
                "deliberation. A simple topic with quick consensus may skip section 4. "
                "A complex multi-domain topic may have extensive sections 3-6."
            ),
            detail_preservation_rules=(
                "The addendum must preserve reasoning, not just conclusions:\n"
                "- Include WHY each position was held, not just WHAT it was\n"
                "- Include the specific arguments that shifted positions during debate\n"
                "- Include quantitative details (costs, timelines, metrics) when agents cited "
                "them\n"
                "- When domain experts provided specialized insight, preserve the technical "
                "detail\n"
                "- Detail > brevity. A 2000-word addendum that captures the full deliberation "
                "is better than a 200-word summary that loses the reasoning."
            ),
            dissent_inclusion_rules=(
                "Dissenting views are first-class content in the addendum:\n"
                "- Every dissent appears in the addendum, attributed to the agent by name and "
                "role\n"
                "- The dissenter's strongest argument is stated in their own voice/style\n"
                "- Domain-weighted context is provided (how relevant is this agent to the "
                "point?)\n"
                "- The addendum explicitly states whether the dissent was overruled by "
                "domain authority, majority vote, or compromise\n"
                "- Future-proofing: note if a dissenting position could become relevant "
                "under different circumstances"
            ),
        )

    def _build_orchestration_notes(self, composition: CouncilComposition) -> str:
        """Build orchestration notes string from the composition."""
        assignments = composition.assignments
        type_counts = Counter(a.agent_type for a in assignments)
        unique_models = len(set(a.assigned_model for a in assignments))
        wildcard_count = sum(1 for a in assignments if a.is_wildcard)
        domains = ", ".join(composition.classification.domains) or "none identified"
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
