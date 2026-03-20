"""Shared test fixtures for AI Council tests."""

import os

import pytest


@pytest.fixture
def api_key_env(monkeypatch):
    """Set OPENROUTER_API_KEY env var for tests."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key-12345")


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all OPENROUTER_* env vars."""
    for key in list(os.environ.keys()):
        if key.startswith("OPENROUTER_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def valid_config_yaml() -> str:
    """Return a valid config YAML string."""
    return """
default_model: "openai/gpt-4.1"
temperature: 0.5
max_output_tokens: 4096

tool_overrides:
  critique: "anthropic/claude-sonnet-4"
  brainstorm: "google/gemini-2.5-pro"

model_pool:
  - "openai/gpt-4.1"
  - "anthropic/claude-sonnet-4"
  - "google/gemini-2.5-pro"

capability_weights:
  "openai/gpt-4.1":
    context_window: 1048576
    coding: 0.90
    analysis: 0.90
  "anthropic/claude-sonnet-4":
    context_window: 200000
    coding: 0.95
    analysis: 0.90
"""


@pytest.fixture
def config_dir(tmp_path, valid_config_yaml):
    """Create a temp directory with aicouncil/config.yaml."""
    aicouncil_dir = tmp_path / "aicouncil"
    aicouncil_dir.mkdir()
    config_file = aicouncil_dir / "config.yaml"
    config_file.write_text(valid_config_yaml)
    return tmp_path


@pytest.fixture
def reset_singletons():
    """Reset config singletons before and after each test."""
    from aicouncil.config import reset_config

    reset_config()
    yield
    reset_config()
