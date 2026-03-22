"""End-to-end integration tests for the council pipeline.

Validates that council modules wire together correctly:
ai_council() -> data handoff -> save_council_addendum() -> file on disk.

All OpenRouter calls are mocked — no real API calls.
Agent loading is mocked — no reading built-in agent files.
File I/O uses tmp_path — no writing to real project directories.
"""

import ast
import logging
import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from aicouncil.config import CapabilityWeight, Config
from aicouncil.council.schemas import (
    AddendumMetadata,
    AddendumSaveResult,
    CouncilAssemblyResult,
    CouncilComposition,
    OrchestrationData,
    TopicClassification,
)
from aicouncil.exceptions import (
    CouncilError,
    ModelUnavailableError,
    OpenRouterError,
)
from aicouncil.schemas.agents import Agent, AgentRoster
from aicouncil.tools.council import (
    MAX_ADDENDUM_CONTENT_BYTES,
    ai_council,
    save_council_addendum,
)

# Project root for anchoring static analysis paths
_PROJECT_ROOT = Path(__file__).parent.parent

# UUID regex pattern for log assertions
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

# ---------------------------------------------------------------------------
# Shared Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_config() -> Config:
    """Config with realistic model pool and capability weights."""
    return Config(
        api_key="test-integration-key",
        default_model="model-alpha",
        model_pool=["model-alpha", "model-beta", "model-gamma"],
        capability_weights={
            "model-alpha": CapabilityWeight(
                context_window=128000, coding=0.9, architecture=0.85, business=0.5
            ),
            "model-beta": CapabilityWeight(
                context_window=200000, coding=0.6, architecture=0.5, business=0.9
            ),
            "model-gamma": CapabilityWeight(
                context_window=100000, coding=0.75, architecture=0.7, business=0.7
            ),
        },
    )


@pytest.fixture
def integration_roster() -> AgentRoster:
    """Realistic test roster with diverse agents."""
    return AgentRoster(
        agents=[
            Agent(
                name="Software Architect",
                role="System Design Expert",
                type="expert",
                tier=1,
                domains=["architecture", "coding"],
                include_flag=True,
                persona="I design systems.",
            ),
            Agent(
                name="Security Engineer",
                role="Security Expert",
                type="expert",
                tier=1,
                domains=["security", "coding"],
                include_flag=True,
                persona="I secure systems.",
            ),
            Agent(
                name="Business Analyst",
                role="Business Strategy",
                type="expert",
                tier=2,
                domains=["business", "analysis"],
                include_flag=True,
                persona="I analyze business.",
            ),
            Agent(
                name="Frontend Developer",
                role="UI Builder",
                type="builder",
                tier=1,
                domains=["coding", "user_experience"],
                include_flag=True,
                persona="I build UIs.",
            ),
            Agent(
                name="DevOps Engineer",
                role="Infrastructure Builder",
                type="builder",
                tier=2,
                domains=["infrastructure", "automation"],
                include_flag=True,
                persona="I manage infra.",
            ),
            Agent(
                name="End User Advocate",
                role="User Perspective",
                type="user",
                tier=1,
                domains=["user_experience"],
                include_flag=True,
                persona="I represent users.",
            ),
            Agent(
                name="QA Tester",
                role="Quality Perspective",
                type="user",
                tier=2,
                domains=["testing"],
                include_flag=True,
                persona="I test things.",
            ),
        ]
    )


@pytest.fixture
def mock_classification() -> TopicClassification:
    """Pre-built classification result for mocking the LLM call."""
    return TopicClassification(
        topic="Should we adopt microservices?",
        domains=["architecture", "coding"],
        domain_scores={"architecture": 0.9, "coding": 0.7},
        reasoning="Microservices is an architecture and coding question.",
    )


@pytest.fixture
def council_patches(integration_config, integration_roster, mock_classification):
    """Patch all external boundaries for council integration tests.

    Returns a context manager that patches:
    - get_config() -> integration_config
    - get_agents() -> integration_roster
    - OpenRouterClient.generate() -> mock_classification
    """
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(return_value=mock_classification)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    patches = {
        "config": patch("aicouncil.tools.council.get_config", return_value=integration_config),
        "agents": patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
        "client": patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
    }
    return patches, mock_client


def _assert_session_uuid_in_logs(caplog_records: list[logging.LogRecord]) -> None:
    """Assert at least one log record contains a valid session UUID in [council:<uuid>] format."""
    for record in caplog_records:
        msg = record.getMessage()
        if "council:" in msg and _UUID_RE.search(msg):
            return
    pytest.fail("No log record contains a session UUID in [council:<uuid>] format")


# ---------------------------------------------------------------------------
# Task 1: Full Council Lifecycle (AC: #1, #3)
# ---------------------------------------------------------------------------


class TestFullCouncilLifecycle:
    """End-to-end: ai_council() -> data handoff -> save_council_addendum() -> file on disk."""

    @pytest.mark.asyncio
    async def test_assembly_to_save_lifecycle(self, council_patches, tmp_path):
        """Full lifecycle produces valid assembly result and persisted addendum file."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        assert isinstance(result, CouncilAssemblyResult)
        assert isinstance(result.composition, CouncilComposition)
        assert isinstance(result.orchestration, OrchestrationData)

        # Extract data for save (simulating host AI handoff)
        session_id = result.composition.session_id
        topic = result.composition.topic
        agents = [a.agent_name for a in result.composition.assignments]
        model_assignments = {a.agent_name: a.assigned_model for a in result.composition.assignments}

        # Save addendum
        addendum_content = "## Consensus\nThe council recommends microservices."
        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=session_id,
                topic=topic,
                agents=agents,
                model_assignments=model_assignments,
                addendum_content=addendum_content,
            )

        assert isinstance(save_result, AddendumSaveResult)
        assert save_result.metadata.session_id == session_id
        assert not Path(save_result.file_path).is_absolute(), "file_path must be relative"

        # Verify file on disk
        file_path = tmp_path / save_result.file_path
        assert file_path.exists()
        content = file_path.read_text()
        assert "session_id:" in content  # YAML frontmatter
        assert "The council recommends microservices" in content

    @pytest.mark.asyncio
    async def test_data_handoff_consistency(self, council_patches, tmp_path):
        """session_id, topic, agents, models flow correctly between tools."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        session_id = result.composition.session_id
        topic = result.composition.topic
        agents = [a.agent_name for a in result.composition.assignments]
        model_assignments = {a.agent_name: a.assigned_model for a in result.composition.assignments}

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=session_id,
                topic=topic,
                agents=agents,
                model_assignments=model_assignments,
                addendum_content="Deliberation content.",
            )

        # Verify metadata consistency
        assert save_result.metadata.session_id == session_id
        assert save_result.metadata.topic == topic
        assert save_result.metadata.agents == agents
        assert save_result.metadata.model_assignments == model_assignments
        assert not Path(save_result.file_path).is_absolute(), "file_path must be relative"

    @pytest.mark.asyncio
    async def test_file_content_self_contained_markdown(self, council_patches, tmp_path):
        """File content is self-contained, readable markdown with YAML frontmatter + narrative."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        session_id = result.composition.session_id
        agents = [a.agent_name for a in result.composition.assignments]
        model_assignments = {a.agent_name: a.assigned_model for a in result.composition.assignments}

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=session_id,
                topic="Should we adopt microservices?",
                agents=agents,
                model_assignments=model_assignments,
                addendum_content="## Analysis\nDetailed analysis here.",
            )

        file_path = tmp_path / save_result.file_path
        content = file_path.read_text()

        # YAML frontmatter: must start with --- and have a closing ---
        assert content.startswith("---\n")
        # Find the closing --- fence (second occurrence, within the header block)
        first_fence_end = content.index("\n", 3) + 1  # past first "---\n"
        closing_fence_pos = content.index("---", first_fence_end)
        frontmatter = content[4:closing_fence_pos]
        assert f'session_id: "{session_id}"' in frontmatter
        assert 'topic: "Should we adopt microservices?"' in frontmatter

        # Readable narrative (after frontmatter)
        body = content[closing_fence_pos + 3 :]
        assert "# Council Addendum" in body
        assert "## Council Deliberation" in body
        assert "Detailed analysis here" in body

        # Agent model table
        assert "| Agent | Model |" in content

    @pytest.mark.asyncio
    async def test_multiple_sequential_councils(self, council_patches, tmp_path):
        """Two councils produce two distinct history files."""
        patches, mock_client = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result1 = await ai_council(topic="Should we adopt microservices?")
            result2 = await ai_council(topic="Should we adopt microservices?")

        assert result1.composition.session_id != result2.composition.session_id

        for i, result in enumerate([result1, result2]):
            session_id = result.composition.session_id
            agents = [a.agent_name for a in result.composition.assignments]
            model_assignments = {
                a.agent_name: a.assigned_model for a in result.composition.assignments
            }

            with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
                await save_council_addendum(
                    session_id=session_id,
                    topic="Should we adopt microservices?",
                    agents=agents,
                    model_assignments=model_assignments,
                    addendum_content=f"Deliberation {i + 1}.",
                )

        # Two distinct files in history dir
        history_dir = tmp_path / "aicouncil" / "history"
        md_files = list(history_dir.glob("*.md"))
        assert len(md_files) == 2


# ---------------------------------------------------------------------------
# Task 2: Model Unavailability & Retry-then-Reassign (AC: #2)
# ---------------------------------------------------------------------------


class TestModelUnavailability:
    """AC #2: Retry then reassign pattern."""

    @pytest.mark.asyncio
    async def test_client_retries_before_model_unavailable(self, integration_config):
        """OpenRouterClient retries 2-3x on transient errors before ModelUnavailableError."""
        from aicouncil.client import OpenRouterClient

        # Verify retry_attempts is in spec range 2-3
        assert 2 <= integration_config.retry_attempts <= 3, (
            f"retry_attempts must be 2-3, got {integration_config.retry_attempts}"
        )

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        async with OpenRouterClient(model="test-model", config=integration_config) as client:
            with patch.object(client, "_get_http_client") as mock_get:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(return_value=mock_response)
                mock_get.return_value = mock_http

                with pytest.raises(ModelUnavailableError, match="unavailable after"):
                    await client.generate("test prompt")

                # Verify retry count matches configured value (within 2-3 range)
                assert mock_http.post.call_count == integration_config.retry_attempts

    @pytest.mark.asyncio
    async def test_model_failure_wraps_in_council_error_with_uuid_log(
        self, integration_config, integration_roster, caplog
    ):
        """ModelUnavailableError wraps into CouncilError with session UUID in logs."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(
            side_effect=ModelUnavailableError("model-alpha unavailable after 3 attempts")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(CouncilError, match="Council assembly failed"):
                    await ai_council(topic="Test topic")

        # Verify session UUID appears in log entries
        _assert_session_uuid_in_logs(caplog.records)

    @pytest.mark.asyncio
    async def test_classification_failure_structured_error(
        self, integration_config, integration_roster
    ):
        """Classification LLM failure returns structured CouncilError, not raw traceback."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=OpenRouterError("API timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with pytest.raises(CouncilError) as exc_info:
                await ai_council(topic="Test topic")

            # Must be CouncilError (structured), not bare OpenRouterError
            assert isinstance(exc_info.value, CouncilError)
            assert type(exc_info.value) is not OpenRouterError

    @pytest.mark.asyncio
    async def test_model_failure_logs_session_uuid(
        self, integration_config, integration_roster, caplog
    ):
        """Session UUID appears in error log when model fails."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=ModelUnavailableError("model gone"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(CouncilError):
                    await ai_council(topic="Test topic")

        _assert_session_uuid_in_logs(caplog.records)


# ---------------------------------------------------------------------------
# Task 3: Pydantic Response Validation (AC: #3)
# ---------------------------------------------------------------------------


class TestPydanticResponseValidation:
    """AC #3: All tool returns are Pydantic BaseModel instances."""

    @pytest.mark.asyncio
    async def test_ai_council_returns_pydantic(self, council_patches):
        """ai_council returns CouncilAssemblyResult (BaseModel), never dict/string."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        assert isinstance(result, BaseModel)
        assert isinstance(result, CouncilAssemblyResult)

    @pytest.mark.asyncio
    async def test_save_addendum_returns_pydantic(self, council_patches, tmp_path):
        """save_council_addendum returns AddendumSaveResult (BaseModel), never dict/string."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=result.composition.session_id,
                topic=result.composition.topic,
                agents=[a.agent_name for a in result.composition.assignments],
                model_assignments={
                    a.agent_name: a.assigned_model for a in result.composition.assignments
                },
                addendum_content="Test content.",
            )

        assert isinstance(save_result, BaseModel)
        assert isinstance(save_result, AddendumSaveResult)

    @pytest.mark.asyncio
    async def test_nested_models_are_pydantic(self, council_patches, tmp_path):
        """All nested objects in assembly result are proper Pydantic instances."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        # CouncilComposition
        assert isinstance(result.composition, BaseModel)
        assert isinstance(result.composition, CouncilComposition)

        # OrchestrationData
        assert isinstance(result.orchestration, BaseModel)
        assert isinstance(result.orchestration, OrchestrationData)

        # TopicClassification
        assert isinstance(result.composition.classification, BaseModel)
        assert isinstance(result.composition.classification, TopicClassification)

        # AgentAssignments
        for assignment in result.composition.assignments:
            assert isinstance(assignment, BaseModel)

        # AddendumMetadata — must invoke save to get an actual metadata instance
        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=result.composition.session_id,
                topic=result.composition.topic,
                agents=[a.agent_name for a in result.composition.assignments],
                model_assignments={
                    a.agent_name: a.assigned_model for a in result.composition.assignments
                },
                addendum_content="Test content for metadata validation.",
            )

        assert isinstance(save_result.metadata, BaseModel)
        assert isinstance(save_result.metadata, AddendumMetadata)

    @pytest.mark.asyncio
    async def test_error_states_are_council_error(self, integration_config, integration_roster):
        """Error states are CouncilError exceptions, not raw tracebacks to MCP."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=OpenRouterError("API error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with pytest.raises(CouncilError):
                await ai_council(topic="Test")


# ---------------------------------------------------------------------------
# Task 4: Error Handling Coverage (AC: #4)
# ---------------------------------------------------------------------------


class TestErrorHandlingPipeline:
    """AC #4: Exception hierarchy and session UUID in logs."""

    @pytest.mark.asyncio
    async def test_empty_topic_raises_council_error(self, council_patches):
        """Empty topic -> CouncilError('Topic is required')."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            with pytest.raises(CouncilError, match="Topic is required"):
                await ai_council(topic="")

    @pytest.mark.asyncio
    async def test_whitespace_topic_raises_council_error(self, council_patches):
        """Whitespace-only topic -> CouncilError('Topic is required')."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            with pytest.raises(CouncilError, match="Topic is required"):
                await ai_council(topic="   ")

    @pytest.mark.asyncio
    async def test_no_capability_domains_raises_council_error(
        self, integration_roster, mock_classification
    ):
        """No capability domains in config -> CouncilError."""
        config_no_domains = Config(
            api_key="test-key",
            model_pool=["model-a"],
            capability_weights={},
        )

        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=mock_classification)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=config_no_domains),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
            pytest.raises(CouncilError, match="No capability domains found"),
        ):
            await ai_council(topic="Test topic")

    @pytest.mark.asyncio
    async def test_invalid_classification_raises_council_error(
        self, integration_config, integration_roster
    ):
        """Classification LLM returns invalid response -> CouncilError."""
        # Return a non-TopicClassification value (simulating bad LLM parse)
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value={"error": True, "message": "bad"})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
            pytest.raises(CouncilError, match="classification failed"),
        ):
            await ai_council(topic="Test topic")

    @pytest.mark.asyncio
    async def test_empty_agent_roster_raises_council_error(
        self, integration_config, mock_classification
    ):
        """Empty agent roster -> CouncilError from assembler."""
        empty_roster = AgentRoster(agents=[])

        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=mock_classification)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=empty_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
            pytest.raises(CouncilError, match="roster is empty"),
        ):
            await ai_council(topic="Test topic")

    @pytest.mark.asyncio
    async def test_oversized_addendum_raises_council_error(self, tmp_path):
        """Addendum content > 1MB -> CouncilError('exceeds maximum size')."""
        oversized = "x" * (MAX_ADDENDUM_CONTENT_BYTES + 1)

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            with pytest.raises(CouncilError, match="exceeds maximum size"):
                await save_council_addendum(
                    session_id=str(uuid.uuid4()),
                    topic="Test",
                    agents=["Agent1"],
                    model_assignments={"Agent1": "model-a"},
                    addendum_content=oversized,
                )

    @pytest.mark.asyncio
    async def test_oversized_addendum_multibyte(self, tmp_path):
        """Addendum with multibyte chars exceeding 1MB byte limit is rejected."""
        # Each \u00e9 is 2 bytes in UTF-8; half the byte limit + 1 chars exceeds it
        oversized = "\u00e9" * (MAX_ADDENDUM_CONTENT_BYTES // 2 + 1)

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            with pytest.raises(CouncilError, match="exceeds maximum size"):
                await save_council_addendum(
                    session_id=str(uuid.uuid4()),
                    topic="Test",
                    agents=["Agent1"],
                    model_assignments={"Agent1": "model-a"},
                    addendum_content=oversized,
                )

    @pytest.mark.asyncio
    async def test_file_io_failure_raises_council_error(self):
        """File I/O failure -> CouncilError (wrapped OSError)."""
        with patch("aicouncil.tools.council.Path.cwd", return_value=Path("/nonexistent/path")):
            with pytest.raises(CouncilError):
                await save_council_addendum(
                    session_id=str(uuid.uuid4()),
                    topic="Test",
                    agents=["Agent1"],
                    model_assignments={"Agent1": "model-a"},
                    addendum_content="Content.",
                )

    @pytest.mark.asyncio
    async def test_session_uuid_in_error_logs_empty_topic(self, council_patches, caplog):
        """Session UUID in logs for empty topic error path."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(CouncilError):
                    await ai_council(topic="")

        _assert_session_uuid_in_logs(caplog.records)

    @pytest.mark.asyncio
    async def test_session_uuid_in_error_logs_model_failure(
        self, integration_config, integration_roster, caplog
    ):
        """Session UUID in logs for model failure error path."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(side_effect=OpenRouterError("API error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=integration_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(CouncilError):
                    await ai_council(topic="Test topic")

        _assert_session_uuid_in_logs(caplog.records)

    @pytest.mark.asyncio
    async def test_session_uuid_in_error_logs_empty_roster(
        self, integration_config, mock_classification, caplog
    ):
        """Session UUID in logs for empty roster error path."""
        empty_roster = AgentRoster(agents=[])
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value=mock_classification)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("aicouncil.tools.council.get_config", return_value=integration_config),
            patch("aicouncil.tools.council.get_agents", return_value=empty_roster),
            patch("aicouncil.tools.council.OpenRouterClient", return_value=mock_client),
        ):
            with caplog.at_level(logging.DEBUG):
                with pytest.raises(CouncilError):
                    await ai_council(topic="Test topic")

        _assert_session_uuid_in_logs(caplog.records)

    def test_no_broad_exception_catch_in_pipeline(self):
        """Verify council pipeline source code doesn't catch bare Exception."""
        pipeline_modules = [
            "src/aicouncil/tools/council.py",
            "src/aicouncil/council/assembler.py",
            "src/aicouncil/council/history.py",
            "src/aicouncil/council/schemas.py",
            "src/aicouncil/client.py",
            "src/aicouncil/config.py",
            "src/aicouncil/exceptions.py",
            "src/aicouncil/agent_loader.py",
        ]

        for module_rel in pipeline_modules:
            path = _PROJECT_ROOT / module_rel
            assert path.exists(), f"Expected pipeline module not found: {module_rel}"

            source = path.read_text()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        pytest.fail(
                            f"{module_rel}:{node.lineno} has bare 'except:' — "
                            "must use specific AiCouncilError subclasses"
                        )
                    # Check single-name handler: except Exception:
                    if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                        pytest.fail(
                            f"{module_rel}:{node.lineno} catches broad 'Exception' — "
                            "must use specific AiCouncilError subclasses"
                        )
                    # Check tuple handler: except (Foo, Exception):
                    if isinstance(node.type, ast.Tuple):
                        for elt in node.type.elts:
                            if isinstance(elt, ast.Name) and elt.id == "Exception":
                                pytest.fail(
                                    f"{module_rel}:{node.lineno} catches broad 'Exception' "
                                    "in tuple handler — "
                                    "must use specific AiCouncilError subclasses"
                                )


# ---------------------------------------------------------------------------
# Task 5: NFR Validation (AC: #5)
# ---------------------------------------------------------------------------


class TestNFRValidation:
    """AC #5: Non-functional requirements."""

    @pytest.mark.asyncio
    async def test_single_llm_call_for_assembly(self, council_patches):
        """Assembly uses exactly one LLM call (NFR2)."""
        patches, mock_client = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            await ai_council(topic="Should we adopt microservices?")

        # client.generate() called exactly once — for topic classification
        assert mock_client.generate.call_count == 1

    def test_no_http_outside_client(self):
        """No module other than client.py imports httpx (NFR5)."""
        src_dir = _PROJECT_ROOT / "src" / "aicouncil"
        assert src_dir.exists(), f"Source directory not found: {src_dir}"

        for py_file in src_dir.rglob("*.py"):
            if py_file.name == "client.py":
                continue

            source = py_file.read_text()
            tree = ast.parse(source)

            rel_path = py_file.relative_to(_PROJECT_ROOT / "src")
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "httpx" or alias.name.startswith("httpx."):
                            pytest.fail(
                                f"{rel_path} imports httpx "
                                "— only client.py should import httpx (NFR5)"
                            )
                if isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "httpx" or node.module.startswith("httpx.")):
                        pytest.fail(
                            f"{rel_path} imports from httpx "
                            "— only client.py should import httpx (NFR5)"
                        )

    @pytest.mark.asyncio
    async def test_all_tool_returns_are_pydantic(self, council_patches, tmp_path):
        """All tool return values are Pydantic BaseModel instances."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            assembly_result = await ai_council(topic="Should we adopt microservices?")

        assert isinstance(assembly_result, BaseModel)

        session_id = assembly_result.composition.session_id
        agents = [a.agent_name for a in assembly_result.composition.assignments]
        model_assignments = {
            a.agent_name: a.assigned_model for a in assembly_result.composition.assignments
        }

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=session_id,
                topic="Should we adopt microservices?",
                agents=agents,
                model_assignments=model_assignments,
                addendum_content="Test.",
            )

        assert isinstance(save_result, BaseModel)

    @pytest.mark.asyncio
    async def test_session_uuid_correlation(self, council_patches, tmp_path):
        """session_id from ai_council flows through to save_council_addendum."""
        patches, _ = council_patches

        with patches["config"], patches["agents"], patches["client"]:
            result = await ai_council(topic="Should we adopt microservices?")

        session_id = result.composition.session_id
        # Verify it's a valid UUID
        uuid.UUID(session_id)

        agents = [a.agent_name for a in result.composition.assignments]
        model_assignments = {a.agent_name: a.assigned_model for a in result.composition.assignments}

        with patch("aicouncil.tools.council.Path.cwd", return_value=tmp_path):
            save_result = await save_council_addendum(
                session_id=session_id,
                topic="Should we adopt microservices?",
                agents=agents,
                model_assignments=model_assignments,
                addendum_content="Test.",
            )

        # Same session_id flows through
        assert save_result.metadata.session_id == session_id

        # Verify in file on disk too
        file_path = tmp_path / save_result.file_path
        content = file_path.read_text()
        assert session_id in content
