"""Tests for config.py — YAML loading, cascading defaults, immutability, validation."""

import pytest
from pydantic import ValidationError

from aicouncil.config import (
    CapabilityWeight,
    get_config,
    load_config,
    reset_config,
)
from aicouncil.exceptions import ConfigError


class TestLoadConfigYaml:
    """Test YAML loading with valid config file."""

    def test_load_valid_config(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)

        assert config.api_key == "test-api-key-12345"
        assert config.default_model == "openai/gpt-4.1"
        assert config.temperature == 0.5
        assert config.max_output_tokens == 4096

    def test_load_with_tool_overrides(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)

        assert config.tool_overrides["critique"] == "anthropic/claude-sonnet-4"
        assert config.tool_overrides["brainstorm"] == "google/gemini-2.5-pro"

    def test_load_model_pool(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)

        assert len(config.model_pool) == 3
        assert "openai/gpt-4.1" in config.model_pool
        assert "anthropic/claude-sonnet-4" in config.model_pool
        assert "google/gemini-2.5-pro" in config.model_pool

    def test_load_capability_weights(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)

        assert "openai/gpt-4.1" in config.capability_weights
        assert "anthropic/claude-sonnet-4" in config.capability_weights

        gpt_weights = config.capability_weights["openai/gpt-4.1"]
        assert gpt_weights.context_window == 1048576
        assert gpt_weights.get_domain_score("coding") == 0.90
        assert gpt_weights.get_domain_score("analysis") == 0.90

    def test_load_defaults_without_yaml(self, api_key_env, tmp_path):
        """Config loads with defaults when no YAML file exists."""
        config = load_config(project_root=tmp_path)

        assert config.default_model == "anthropic/claude-sonnet-4"
        assert config.temperature == 0.7
        assert config.tool_overrides == {}
        assert config.model_pool == []
        assert config.capability_weights == {}

    def test_backward_compat_model_key(self, api_key_env, tmp_path):
        """Accepts 'model' key as alias for 'default_model'."""
        aicouncil_dir = tmp_path / "aicouncil"
        aicouncil_dir.mkdir()
        (aicouncil_dir / "config.yaml").write_text('model: "deepseek/deepseek-r1"')

        config = load_config(project_root=tmp_path)
        assert config.default_model == "deepseek/deepseek-r1"

    def test_model_property_alias(self, api_key_env, config_dir):
        """config.model returns config.default_model for backward compat."""
        config = load_config(project_root=config_dir)
        assert config.model == config.default_model


class TestCascadingResolution:
    """Test cascading resolution: global → per-tool → per-invocation."""

    def test_global_default_only(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.resolve_model() == "openai/gpt-4.1"

    def test_per_tool_override(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.resolve_model("critique") == "anthropic/claude-sonnet-4"

    def test_per_invocation_wins(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        result = config.resolve_model("critique", per_invocation="meta-llama/llama-4-maverick")
        assert result == "meta-llama/llama-4-maverick"

    def test_unknown_tool_falls_to_global(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.resolve_model("nonexistent_tool") == "openai/gpt-4.1"

    def test_none_tool_returns_global(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.resolve_model(None) == "openai/gpt-4.1"


class TestImmutability:
    """Test Config immutability (frozen=True)."""

    def test_cannot_mutate_default_model(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        with pytest.raises(ValidationError):
            config.default_model = "some/other-model"

    def test_cannot_mutate_api_key(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        with pytest.raises(ValidationError):
            config.api_key = "new-key"

    def test_cannot_mutate_temperature(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        with pytest.raises(ValidationError):
            config.temperature = 1.5


class TestConfigErrors:
    """Test ConfigError for malformed/missing config."""

    def test_missing_api_key(self, clean_env):
        with pytest.raises(ConfigError, match="OPENROUTER_API_KEY not set"):
            load_config()

    def test_malformed_yaml(self, api_key_env, tmp_path):
        aicouncil_dir = tmp_path / "aicouncil"
        aicouncil_dir.mkdir()
        (aicouncil_dir / "config.yaml").write_text("invalid: yaml: [broken: {")

        with pytest.raises(ConfigError, match="Failed to parse"):
            load_config(project_root=tmp_path)

    def test_invalid_temperature_type(self, api_key_env, tmp_path):
        aicouncil_dir = tmp_path / "aicouncil"
        aicouncil_dir.mkdir()
        (aicouncil_dir / "config.yaml").write_text("temperature: 5.0")

        with pytest.raises(ConfigError, match="Invalid configuration"):
            load_config(project_root=tmp_path)


class TestCapabilityWeights:
    """Test capability weights parsing and helpers."""

    def test_get_capability_weights(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        weights = config.get_capability_weights("openai/gpt-4.1")

        assert weights is not None
        assert weights.context_window == 1048576

    def test_get_capability_weights_unknown_model(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.get_capability_weights("unknown/model") is None

    def test_get_context_window(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.get_context_window("openai/gpt-4.1") == 1048576
        assert config.get_context_window("anthropic/claude-sonnet-4") == 200000

    def test_get_context_window_unknown_model(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        assert config.get_context_window("unknown/model") is None

    def test_get_model_pool(self, api_key_env, config_dir):
        config = load_config(project_root=config_dir)
        pool = config.get_model_pool()
        assert len(pool) == 3
        assert pool is not config.model_pool  # Returns a copy

    def test_domain_scores(self):
        weight = CapabilityWeight(context_window=100000, coding=0.95, analysis=0.8)
        scores = weight.domain_scores()
        assert scores == {"coding": 0.95, "analysis": 0.8}

    def test_unknown_domain_returns_none(self):
        weight = CapabilityWeight(context_window=100000, coding=0.95)
        assert weight.get_domain_score("nonexistent") is None


class TestSingleton:
    """Test singleton pattern and DI."""

    def test_get_config_returns_same_instance(self, api_key_env, tmp_path, reset_singletons):
        c1 = load_config(project_root=tmp_path)
        # Manually set singleton
        import aicouncil.config as config_module

        config_module._config = c1
        c2 = get_config()
        assert c1 is c2

    def test_constructor_injection_overrides(self, api_key_env, tmp_path):
        """OpenRouterClient accepts config via constructor (DI)."""
        config = load_config(project_root=tmp_path)
        from aicouncil.client import OpenRouterClient

        client = OpenRouterClient(config=config)
        assert client._config is config

    def test_reset_config_clears_singleton(self, api_key_env, tmp_path, reset_singletons):
        import aicouncil.config as config_module

        config_module._config = load_config(project_root=tmp_path)
        assert config_module._config is not None

        reset_config()
        assert config_module._config is None


class TestToolOverridesFiltering:
    """Test that commented-out / None tool overrides are filtered."""

    def test_none_values_filtered(self, api_key_env, tmp_path):
        aicouncil_dir = tmp_path / "aicouncil"
        aicouncil_dir.mkdir()
        (aicouncil_dir / "config.yaml").write_text(
            """
tool_overrides:
  critique: "openai/gpt-4.1"
  brainstorm:
"""
        )
        config = load_config(project_root=tmp_path)
        assert "critique" in config.tool_overrides
        assert "brainstorm" not in config.tool_overrides
