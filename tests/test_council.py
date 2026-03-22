"""Tests for council assembly — assembler, schemas, and tool."""

import random
from unittest.mock import AsyncMock, patch

import pytest

from aicouncil.config import CapabilityWeight, Config
from aicouncil.council.assembler import (
    CouncilAssembler,
    build_classification_prompt,
    extract_available_domains,
)
from aicouncil.council.schemas import (
    AgentAssignment,
    ChairpersonInstructions,
    ContextWindowInfo,
    ConvergenceGuidance,
    CouncilAssemblyResult,
    CouncilComposition,
    OrchestrationData,
    ToneGuidance,
    TopicClassification,
)
from aicouncil.exceptions import CouncilError
from aicouncil.schemas.agents import Agent, AgentRoster

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config() -> Config:
    """Config with test model pool and capability weights."""
    return Config(
        api_key="test-key",
        model_pool=["model-a", "model-b", "model-c"],
        capability_weights={
            "model-a": CapabilityWeight(context_window=100000, coding=0.9, business=0.5),
            "model-b": CapabilityWeight(context_window=200000, coding=0.5, business=0.9),
            "model-c": CapabilityWeight(context_window=150000, coding=0.7, business=0.7),
        },
    )


@pytest.fixture
def sample_classification() -> TopicClassification:
    """A sample topic classification for testing."""
    return TopicClassification(
        topic="How should we implement Stripe Connect for our marketplace?",
        domains=["coding", "business"],
        domain_scores={"coding": 0.8, "business": 0.7},
        reasoning="Payment integration involves both coding and business strategy",
    )


@pytest.fixture
def sample_roster() -> AgentRoster:
    """An agent roster with diverse types, tiers, and domains."""
    return AgentRoster(
        agents=[
            # Experts
            Agent(
                name="Software Architect",
                role="System Design Expert",
                type="expert",
                tier=1,
                domains=["system_design", "coding"],
                include_flag=True,
                persona="I am a software architect.",
            ),
            Agent(
                name="Security Analyst",
                role="Security Expert",
                type="expert",
                tier=1,
                domains=["security", "coding"],
                include_flag=True,
                persona="I am a security analyst.",
            ),
            Agent(
                name="Data Scientist",
                role="Data Analysis Expert",
                type="expert",
                tier=2,
                domains=["data_analysis", "machine_learning"],
                include_flag=True,
                persona="I am a data scientist.",
            ),
            Agent(
                name="Business Strategist",
                role="Business Strategy Expert",
                type="expert",
                tier=1,
                domains=["business_strategy", "business"],
                include_flag=True,
                persona="I am a business strategist.",
            ),
            Agent(
                name="Tax Compliance Officer",
                role="Tax Expert",
                type="expert",
                tier=2,
                domains=["tax_compliance", "legal"],
                include_flag=True,
                persona="I am a tax compliance officer.",
            ),
            Agent(
                name="Financial Analyst",
                role="Finance Expert",
                type="expert",
                tier=2,
                domains=["finance", "business"],
                include_flag=True,
                persona="I am a financial analyst.",
            ),
            # Builders
            Agent(
                name="Full Stack Developer",
                role="Builder",
                type="builder",
                tier=1,
                domains=["web_development", "coding"],
                include_flag=True,
                persona="I am a full stack developer.",
            ),
            Agent(
                name="DevOps Engineer",
                role="Infrastructure Builder",
                type="builder",
                tier=2,
                domains=["infrastructure", "automation"],
                include_flag=True,
                persona="I am a devops engineer.",
            ),
            # Users
            Agent(
                name="End User Advocate",
                role="User Perspective",
                type="user",
                tier=1,
                domains=["user_experience"],
                include_flag=True,
                persona="I represent end users.",
            ),
            Agent(
                name="Internal Tester",
                role="QA Perspective",
                type="user",
                tier=2,
                domains=["testing"],
                include_flag=False,
                persona="I am an internal tester.",
            ),
            # Wildcard candidates (no overlap with coding/business)
            Agent(
                name="Psychologist",
                role="Psychology Expert",
                type="expert",
                tier=3,
                domains=["psychology", "cognitive_science"],
                include_flag=True,
                persona="I am a psychologist.",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestTopicClassification:
    def test_create(self):
        tc = TopicClassification(
            topic="test topic",
            domains=["coding"],
            domain_scores={"coding": 0.9},
            reasoning="technical topic",
        )
        assert tc.topic == "test topic"
        assert tc.domains == ["coding"]
        assert tc.domain_scores["coding"] == 0.9

    def test_multiple_domains(self):
        tc = TopicClassification(
            topic="complex topic",
            domains=["coding", "business", "legal"],
            domain_scores={"coding": 0.8, "business": 0.6, "legal": 0.4},
            reasoning="multi-domain",
        )
        assert len(tc.domains) == 3
        assert len(tc.domain_scores) == 3


class TestAgentAssignment:
    def test_create_default(self):
        aa = AgentAssignment(
            agent_name="Test",
            agent_role="Role",
            agent_type="expert",
            agent_tier=1,
            assigned_model="model-a",
            assignment_reasoning="test",
            persona="persona text",
        )
        assert aa.is_wildcard is False
        assert aa.is_pinned is False
        assert aa.context_window is None

    def test_create_with_flags(self):
        aa = AgentAssignment(
            agent_name="Test",
            agent_role="Role",
            agent_type="user",
            agent_tier=2,
            assigned_model="model-b",
            context_window=200000,
            assignment_reasoning="pinned",
            is_wildcard=False,
            is_pinned=True,
            persona="persona text",
        )
        assert aa.is_pinned is True
        assert aa.context_window == 200000


class TestCouncilComposition:
    def test_create(self, sample_classification):
        cc = CouncilComposition(
            session_id="test-uuid",
            topic="test",
            classification=sample_classification,
            assignments=[],
            council_size=0,
            diversity_metrics={},
        )
        assert cc.session_id == "test-uuid"
        assert cc.council_size == 0


class TestCouncilAssemblyResult:
    def test_create(self, sample_classification):
        comp = CouncilComposition(
            session_id="test-uuid",
            topic="test",
            classification=sample_classification,
            assignments=[],
            council_size=0,
            diversity_metrics={},
        )
        orchestration = OrchestrationData(
            chairperson=ChairpersonInstructions(
                speaking_order="order",
                debate_triggers="triggers",
                conclusion_driving="driving",
                topic_framing="framing",
            ),
            tone=ToneGuidance(
                default_tone="exploratory",
                adversarial_triggers="triggers",
                agreement_triggers="triggers",
                tone_shift_rules="rules",
            ),
            convergence=ConvergenceGuidance(
                evaluation_criteria="criteria",
                continue_signals="signals",
                consensus_signals="signals",
                no_fixed_rounds="dynamic",
            ),
            context_windows=[],
            agent_count=0,
            summary="Test notes",
        )
        result = CouncilAssemblyResult(
            composition=comp,
            orchestration=orchestration,
        )
        assert result.orchestration.summary == "Test notes"
        assert isinstance(result.orchestration, OrchestrationData)


# ---------------------------------------------------------------------------
# Classification Prompt Tests
# ---------------------------------------------------------------------------


class TestBuildClassificationPrompt:
    def test_includes_topic(self):
        prompt = build_classification_prompt("test topic", {"coding", "business"})
        assert "test topic" in prompt

    def test_includes_all_domains(self):
        domains = {"coding", "business", "legal"}
        prompt = build_classification_prompt("test", domains)
        for d in domains:
            assert d in prompt

    def test_empty_domains(self):
        prompt = build_classification_prompt("test", set())
        assert "test" in prompt


class TestExtractAvailableDomains:
    def test_extracts_domains(self, mock_config):
        domains = extract_available_domains(mock_config)
        assert "coding" in domains
        assert "business" in domains

    def test_empty_model_pool(self):
        config = Config(api_key="test-key", model_pool=[])
        domains = extract_available_domains(config)
        assert domains == set()

    def test_no_capability_weights(self):
        config = Config(api_key="test-key", model_pool=["model-x"])
        domains = extract_available_domains(config)
        assert domains == set()


# ---------------------------------------------------------------------------
# Agent Selection Tests
# ---------------------------------------------------------------------------


class TestAgentSelection:
    def test_selects_relevant_agents(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
            include_wildcard=False,
        )
        names = [a.agent_name for a in composition.assignments]
        # Should include coding/business-relevant agents
        assert "Software Architect" in names or "Business Strategist" in names
        assert composition.council_size <= 5

    def test_category_mix(self, mock_config, sample_classification, sample_roster):
        """Council should have expert + builder + user representation."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=7,
            include_wildcard=False,
        )
        types = {a.agent_type for a in composition.assignments}
        assert "expert" in types
        # Builder and user may be present depending on seat availability
        assert len(composition.assignments) <= 7

    def test_wildcard_inclusion(self, mock_config, sample_classification, sample_roster):
        """Wildcard agents from unrelated domains should be included at 5:1 ratio."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=7,
            include_wildcard=True,
        )
        wildcards = [a for a in composition.assignments if a.is_wildcard]
        assert len(wildcards) >= 1
        # Wildcard should be from unrelated domain (no overlap with coding/business)
        for wc in wildcards:
            assert wc.agent_name in [
                "Psychologist",
                "Data Scientist",
                "DevOps Engineer",
                "End User Advocate",
            ]

    def test_wildcard_disabled(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=7,
            include_wildcard=False,
        )
        wildcards = [a for a in composition.assignments if a.is_wildcard]
        assert len(wildcards) == 0

    def test_tier_preference(self, mock_config, sample_classification, sample_roster):
        """Tier 1 agents should be preferred over Tier 2/3."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=3,
            include_wildcard=False,
        )
        # With only 3 seats, should prefer tier 1 agents
        tiers = [a.agent_tier for a in composition.assignments]
        assert 1 in tiers

    def test_include_flag_respected(self, mock_config, sample_classification, sample_roster):
        """User agents with include_flag=False should not be auto-included."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=10,
            include_wildcard=False,
        )
        names = [a.agent_name for a in composition.assignments]
        assert "Internal Tester" not in names

    def test_exclude_user_agents(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=7,
            include_user_agents=False,
            include_wildcard=False,
        )
        user_agents = [a for a in composition.assignments if a.agent_type == "user"]
        assert len(user_agents) == 0

    def test_roster_smaller_than_council_size(self, mock_config, sample_classification):
        """When roster is smaller than council_size, use all available agents."""
        small_roster = AgentRoster(
            agents=[
                Agent(
                    name="Only Expert",
                    role="Expert",
                    type="expert",
                    tier=1,
                    domains=["coding"],
                    include_flag=True,
                    persona="solo",
                ),
            ]
        )
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=small_roster,
            session_id="test",
            council_size=10,
        )
        assert composition.council_size <= 1


# ---------------------------------------------------------------------------
# Agent/Model Pinning Tests
# ---------------------------------------------------------------------------


class TestAgentPinning:
    def test_pinned_agents_included(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
            pinned_agents=["Psychologist"],
        )
        names = [a.agent_name for a in composition.assignments]
        assert "Psychologist" in names
        psychologist = next(a for a in composition.assignments if a.agent_name == "Psychologist")
        assert psychologist.is_pinned is True

    def test_pinned_case_insensitive(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
            pinned_agents=["psychologist"],
        )
        names = [a.agent_name for a in composition.assignments]
        assert "Psychologist" in names

    def test_pinned_unknown_agent_warns(self, mock_config, sample_classification, sample_roster):
        """Unknown pinned agents should be silently skipped (logged as warning)."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
            pinned_agents=["NonexistentAgent"],
        )
        names = [a.agent_name for a in composition.assignments]
        assert "NonexistentAgent" not in names

    def test_pinned_fills_remaining_automatically(
        self, mock_config, sample_classification, sample_roster
    ):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=5,
            pinned_agents=["Psychologist"],
            include_wildcard=False,
        )
        assert composition.council_size <= 5
        assert any(a.is_pinned for a in composition.assignments)
        assert any(not a.is_pinned for a in composition.assignments)

    def test_pinned_include_flagged_false_user(
        self, mock_config, sample_classification, sample_roster
    ):
        """Explicitly pinned user agents should be included even with include_flag=False."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
            pinned_agents=["Internal Tester"],
        )
        names = [a.agent_name for a in composition.assignments]
        assert "Internal Tester" in names


# ---------------------------------------------------------------------------
# Capability-Weighted Model Routing Tests
# ---------------------------------------------------------------------------


class TestModelRouting:
    def test_model_assigned_from_pool(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=3,
            include_wildcard=False,
        )
        valid_models = set(mock_config.model_pool)
        for assignment in composition.assignments:
            assert assignment.assigned_model in valid_models

    def test_context_window_included(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=3,
            include_wildcard=False,
        )
        for assignment in composition.assignments:
            assert assignment.context_window is not None
            assert assignment.context_window > 0

    def test_60_40_distribution(self, mock_config):
        """Over many iterations, verify ~60% top model and ~40% other distribution."""
        classification = TopicClassification(
            topic="pure coding question",
            domains=["coding"],
            domain_scores={"coding": 1.0},
            reasoning="coding topic",
        )
        agent = Agent(
            name="Coder",
            role="Developer",
            type="expert",
            tier=1,
            domains=["coding"],
            include_flag=True,
            persona="coder",
        )
        roster = AgentRoster(agents=[agent])
        assembler = CouncilAssembler(config=mock_config)

        # model-a has coding=0.9 (highest), so should be picked ~60% of the time
        top_count = 0
        n = 1000
        random.seed(42)
        for _ in range(n):
            composition = assembler.assemble(
                classification=classification,
                roster=roster,
                session_id="test",
                council_size=1,
                include_wildcard=False,
            )
            if composition.assignments[0].assigned_model == "model-a":
                top_count += 1

        ratio = top_count / n
        # Should be roughly 60% but with some variance — allow 45%-80%
        assert 0.45 <= ratio <= 0.80, f"Top model ratio was {ratio:.2f}, expected ~0.60"

    def test_all_models_used(self, mock_config, sample_classification, sample_roster):
        """Over many iterations, all models from pool should be used at least once."""
        assembler = CouncilAssembler(config=mock_config)
        used_models: set[str] = set()
        random.seed(42)
        for _ in range(100):
            composition = assembler.assemble(
                classification=sample_classification,
                roster=sample_roster,
                session_id="test",
                council_size=7,
            )
            for a in composition.assignments:
                used_models.add(a.assigned_model)
        assert used_models == set(mock_config.model_pool)


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_empty_model_pool(self, sample_classification, sample_roster):
        config = Config(api_key="test-key", model_pool=[])
        assembler = CouncilAssembler(config=config)
        with pytest.raises(CouncilError, match="No models in model pool"):
            assembler.assemble(
                classification=sample_classification,
                roster=sample_roster,
                session_id="test",
            )

    def test_empty_roster(self, mock_config, sample_classification):
        assembler = CouncilAssembler(config=mock_config)
        with pytest.raises(CouncilError, match="Agent roster is empty"):
            assembler.assemble(
                classification=sample_classification,
                roster=AgentRoster(agents=[]),
                session_id="test",
            )


# ---------------------------------------------------------------------------
# Orchestration Notes Tests
# ---------------------------------------------------------------------------


class TestOrchestrationNotes:
    def test_builds_notes(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
        )
        notes = assembler._build_orchestration_notes(composition)
        assert "Council of" in notes
        assert "agents assembled" in notes
        assert "Domains:" in notes
        assert "Models:" in notes


# ---------------------------------------------------------------------------
# Diversity Metrics Tests
# ---------------------------------------------------------------------------


class TestDiversityMetrics:
    def test_metrics_computed(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=7,
        )
        metrics = composition.diversity_metrics
        assert "type_distribution" in metrics
        assert "tier_distribution" in metrics
        assert "model_distribution" in metrics
        assert "unique_models" in metrics
        assert "wildcard_count" in metrics
        assert "pinned_count" in metrics
        assert metrics["unique_models"] >= 1


# ---------------------------------------------------------------------------
# Tool Function Tests (ai_council)
# ---------------------------------------------------------------------------


class TestAiCouncilTool:
    @pytest.mark.asyncio
    async def test_empty_topic_raises(self):
        with pytest.raises(CouncilError, match="Topic is required"):
            await ai_council(topic="")

    @pytest.mark.asyncio
    async def test_assembly_success(self, mock_config, sample_classification, sample_roster):
        """Full tool function with mocked LLM and config."""
        with (
            patch("aicouncil.tools.council.get_config", return_value=mock_config),
            patch("aicouncil.tools.council.get_agents", return_value=sample_roster),
            patch("aicouncil.tools.council.OpenRouterClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value=sample_classification)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await ai_council(
                topic="How should we implement Stripe Connect?",
                council_size=5,
            )

            assert isinstance(result, CouncilAssemblyResult)
            assert result.composition.council_size > 0
            assert isinstance(result.orchestration, OrchestrationData)
            assert result.orchestration.summary
            assert result.composition.session_id

    @pytest.mark.asyncio
    async def test_classification_failure(self, mock_config):
        """When LLM returns non-TopicClassification, should raise CouncilError."""
        with (
            patch("aicouncil.tools.council.get_config", return_value=mock_config),
            patch("aicouncil.tools.council.OpenRouterClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.generate = AsyncMock(return_value={"error": True})
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(CouncilError, match="classification failed"):
                await ai_council(topic="test topic")


# ---------------------------------------------------------------------------
# Orchestration Data Tests (Story 2.2)
# ---------------------------------------------------------------------------


class TestChairpersonInstructions:
    def test_fields_non_empty(self):
        ci = ChairpersonInstructions(
            speaking_order="order",
            debate_triggers="triggers",
            conclusion_driving="driving",
            topic_framing="framing",
        )
        assert ci.speaking_order
        assert ci.debate_triggers
        assert ci.conclusion_driving
        assert ci.topic_framing


class TestToneGuidance:
    def test_fields_non_empty(self):
        tg = ToneGuidance(
            default_tone="exploratory",
            adversarial_triggers="triggers",
            agreement_triggers="triggers",
            tone_shift_rules="rules",
        )
        assert tg.default_tone
        assert tg.adversarial_triggers
        assert tg.agreement_triggers
        assert tg.tone_shift_rules


class TestConvergenceGuidance:
    def test_fields_non_empty(self):
        cg = ConvergenceGuidance(
            evaluation_criteria="criteria",
            continue_signals="signals",
            consensus_signals="signals",
            no_fixed_rounds="dynamic",
        )
        assert cg.evaluation_criteria
        assert cg.continue_signals
        assert cg.consensus_signals
        assert cg.no_fixed_rounds


class TestContextWindowInfo:
    def test_half_calculation(self):
        cwi = ContextWindowInfo(model="model-a", context_window=200000)
        assert cwi.half_window == 100000

    def test_odd_context_window(self):
        cwi = ContextWindowInfo(model="model-x", context_window=131073)
        assert cwi.half_window == 65536


class TestBuildOrchestrationData:
    def test_returns_orchestration_data(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert isinstance(orchestration, OrchestrationData)

    def test_includes_summary(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert "Council of" in orchestration.summary
        assert "agents assembled" in orchestration.summary

    def test_context_windows_unique_models(self, mock_config, sample_classification, sample_roster):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=7,
        )
        orchestration = assembler.build_orchestration_data(composition)
        models_in_windows = [cw.model for cw in orchestration.context_windows]
        assert len(models_in_windows) == len(set(models_in_windows))

    def test_context_windows_50_percent_threshold(
        self, mock_config, sample_classification, sample_roster
    ):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        for cw in orchestration.context_windows:
            assert cw.half_window == cw.context_window // 2

    def test_agent_count_matches_composition(
        self, mock_config, sample_classification, sample_roster
    ):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert orchestration.agent_count == composition.council_size

    def test_chairperson_mentions_agent_names(
        self, mock_config, sample_classification, sample_roster
    ):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
            include_wildcard=False,
        )
        orchestration = assembler.build_orchestration_data(composition)
        for a in composition.assignments:
            assert a.agent_name in orchestration.chairperson.speaking_order

    def test_topic_framing_includes_domains(
        self, mock_config, sample_classification, sample_roster
    ):
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test-session",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        for domain in sample_classification.domains:
            assert domain in orchestration.chairperson.topic_framing

    def test_tone_default_exploratory_single_high_domain(self, mock_config, sample_roster):
        """Single domain with high score → exploratory tone."""
        classification = TopicClassification(
            topic="Pure coding question",
            domains=["coding"],
            domain_scores={"coding": 0.95},
            reasoning="single domain",
        )
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=classification,
            roster=sample_roster,
            session_id="test",
            council_size=3,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert "Exploratory" in orchestration.tone.default_tone

    def test_tone_default_structured_multi_domain(self, mock_config, sample_roster):
        """Multi-domain with moderate scores → structured debate."""
        classification = TopicClassification(
            topic="Mixed question",
            domains=["coding", "business"],
            domain_scores={"coding": 0.7, "business": 0.6},
            reasoning="multi-domain",
        )
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=classification,
            roster=sample_roster,
            session_id="test",
            council_size=3,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert "Structured debate" in orchestration.tone.default_tone

    def test_tone_default_risk_aware_safety_domain(self, mock_config, sample_roster):
        """Safety/security domains → risk-aware tone."""
        classification = TopicClassification(
            topic="Security audit question",
            domains=["security", "coding"],
            domain_scores={"security": 0.9, "coding": 0.5},
            reasoning="security topic",
        )
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=classification,
            roster=sample_roster,
            session_id="test",
            council_size=3,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert "Risk-aware" in orchestration.tone.default_tone


class TestOrchestrationEdgeCases:
    def test_single_agent_council(self, mock_config, sample_classification):
        """Orchestration works for single-agent council."""
        roster = AgentRoster(
            agents=[
                Agent(
                    name="Solo Expert",
                    role="Expert",
                    type="expert",
                    tier=1,
                    domains=["coding"],
                    include_flag=True,
                    persona="solo expert persona",
                ),
            ]
        )
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=roster,
            session_id="test",
            council_size=1,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert orchestration.agent_count == 1
        assert isinstance(orchestration.chairperson, ChairpersonInstructions)
        assert isinstance(orchestration.tone, ToneGuidance)
        assert isinstance(orchestration.convergence, ConvergenceGuidance)

    def test_all_same_model(self, sample_classification):
        """context_windows has one entry when all agents use same model."""
        config = Config(
            api_key="test-key",
            model_pool=["model-only"],
            capability_weights={
                "model-only": CapabilityWeight(context_window=128000, coding=0.8, business=0.8),
            },
        )
        roster = AgentRoster(
            agents=[
                Agent(
                    name="Agent A",
                    role="Expert",
                    type="expert",
                    tier=1,
                    domains=["coding"],
                    include_flag=True,
                    persona="a",
                ),
                Agent(
                    name="Agent B",
                    role="Builder",
                    type="builder",
                    tier=1,
                    domains=["coding"],
                    include_flag=True,
                    persona="b",
                ),
            ]
        )
        assembler = CouncilAssembler(config=config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=roster,
            session_id="test",
            council_size=2,
            include_wildcard=False,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert len(orchestration.context_windows) == 1
        assert orchestration.context_windows[0].model == "model-only"

    def test_missing_context_window(self, sample_classification):
        """Models with None context_window are excluded from context_windows list."""
        config = Config(
            api_key="test-key",
            model_pool=["model-no-cw"],
            capability_weights={},
        )
        roster = AgentRoster(
            agents=[
                Agent(
                    name="Test Agent",
                    role="Expert",
                    type="expert",
                    tier=1,
                    domains=["coding"],
                    include_flag=True,
                    persona="persona",
                ),
            ]
        )
        assembler = CouncilAssembler(config=config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=roster,
            session_id="test",
            council_size=1,
            include_wildcard=False,
        )
        orchestration = assembler.build_orchestration_data(composition)
        assert len(orchestration.context_windows) == 0

    def test_backward_compat_summary_present(
        self, mock_config, sample_classification, sample_roster
    ):
        """OrchestrationData.summary contains the old orchestration_notes content."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        notes = assembler._build_orchestration_notes(composition)
        assert orchestration.summary == notes

    def test_council_assembly_result_has_orchestration(
        self, mock_config, sample_classification, sample_roster
    ):
        """CouncilAssemblyResult.orchestration is OrchestrationData type."""
        assembler = CouncilAssembler(config=mock_config)
        composition = assembler.assemble(
            classification=sample_classification,
            roster=sample_roster,
            session_id="test",
            council_size=5,
        )
        orchestration = assembler.build_orchestration_data(composition)
        result = CouncilAssemblyResult(
            composition=composition,
            orchestration=orchestration,
        )
        assert isinstance(result.orchestration, OrchestrationData)
        assert result.orchestration.agent_count == composition.council_size


# Import at module level after fixtures are defined
from aicouncil.tools.council import ai_council  # noqa: E402
