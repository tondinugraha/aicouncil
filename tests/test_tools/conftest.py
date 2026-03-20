"""Shared fixtures for tool tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aicouncil.config import Config


@pytest.fixture
def mock_config():
    """Create a mock Config with known tool_overrides."""
    return Config(
        api_key="test-api-key",
        default_model="test/default-model",
        temperature=0.7,
        max_output_tokens=1024,
        tool_overrides={
            "critique": "test/critique-model",
            "brainstorm": "test/brainstorm-model",
        },
        model_pool=["test/default-model", "test/critique-model"],
        capability_weights={},
    )


@pytest.fixture
def mock_client():
    """Create a mock OpenRouterClient with a controllable generate method."""
    client = MagicMock()
    client.generate = AsyncMock()
    client.generate_with_file = AsyncMock()
    client.close = AsyncMock()
    # Support async context manager (async with OpenRouterClient(...) as client)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client
