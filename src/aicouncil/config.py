"""Configuration management for AI Council server."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aicouncil.exceptions import ConfigError
from aicouncil.roots import get_project_root

logger = logging.getLogger(__name__)


class CapabilityWeight(BaseModel):
    """Capability weights for a single model."""

    model_config = ConfigDict(frozen=True, extra="allow")

    context_window: int = Field(description="Model context window size in tokens")

    def get_domain_score(self, domain: str) -> float | None:
        """Get the capability score for a specific domain."""
        extra = self.model_extra or {}
        value = extra.get(domain)
        if value is not None:
            score = float(value)
            if not 0.0 <= score <= 1.0:
                logger.warning(
                    "capability_weights: domain '%s' score %.2f is outside 0.0-1.0 range",
                    domain,
                    score,
                )
            return score
        return None

    def domain_scores(self) -> dict[str, float]:
        """Return all domain scores (excludes context_window)."""
        extra = self.model_extra or {}
        return {k: float(v) for k, v in extra.items()}


class Config(BaseModel):
    """Configuration for the AI Council server."""

    model_config = ConfigDict(frozen=True)

    # API Configuration
    api_key: str = Field(description="OpenRouter API key")
    default_model: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Global default model for all tools",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_output_tokens: int = Field(default=8192, description="Maximum output tokens")

    # Behavior Configuration
    default_context: str = Field(
        default="", description="Default project context to include in prompts"
    )
    preferred_personas: list[str] = Field(
        default_factory=list, description="Preferred critic personas"
    )
    timeout_seconds: int = Field(default=120, description="API timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts on failure")

    # Response Configuration
    json_response: bool = Field(default=True, description="Enforce JSON responses")
    include_reasoning: bool = Field(default=True, description="Include reasoning in responses")

    # Per-tool model overrides
    tool_overrides: dict[str, str] = Field(
        default_factory=dict, description="Per-tool model overrides"
    )

    # Council model pool
    model_pool: list[str] = Field(
        default_factory=list, description="Models available for council assignment"
    )

    # Capability weights — model-centric
    capability_weights: dict[str, CapabilityWeight] = Field(
        default_factory=dict, description="Model capability weights for routing"
    )

    # Backward compatibility alias
    @property
    def model(self) -> str:
        """Backward-compatible alias for default_model."""
        return self.default_model

    def resolve_model(self, tool_name: str | None = None, per_invocation: str | None = None) -> str:
        """Resolve model using cascade: per-invocation → per-tool → global default."""
        if per_invocation:
            return per_invocation
        if tool_name and tool_name in self.tool_overrides:
            return self.tool_overrides[tool_name]
        return self.default_model

    def get_model_pool(self) -> list[str]:
        """Get the list of models available for council assignment."""
        return list(self.model_pool)

    def get_capability_weights(self, model: str) -> CapabilityWeight | None:
        """Get capability weights for a specific model."""
        return self.capability_weights.get(model)

    def get_context_window(self, model: str) -> int | None:
        """Get the context window size for a model."""
        weights = self.capability_weights.get(model)
        if weights:
            return weights.context_window
        return None


def _parse_capability_weights(raw: dict[str, Any]) -> dict[str, CapabilityWeight]:
    """Parse raw capability weights dict into CapabilityWeight models."""
    result: dict[str, CapabilityWeight] = {}
    for model_name, weight_data in raw.items():
        if not isinstance(weight_data, dict):
            logger.warning(
                f"config.yaml: capability_weights['{model_name}'] must be a dict, "
                f"got {type(weight_data).__name__}"
            )
            continue
        if "context_window" not in weight_data:
            logger.warning(
                f"config.yaml: capability_weights['{model_name}'] missing 'context_window'"
            )
            continue
        # Validate domain scores are numeric and in range
        for key, val in weight_data.items():
            if key == "context_window":
                continue
            try:
                score = float(val)
            except (TypeError, ValueError):
                logger.warning(
                    "capability_weights[%s].%s: expected numeric, got %r — skipping model",
                    model_name,
                    key,
                    val,
                )
                break
            if not 0.0 <= score <= 1.0:
                logger.warning(
                    "capability_weights[%s].%s: score %.2f outside 0.0-1.0 range",
                    model_name,
                    key,
                    score,
                )
        else:
            result[model_name] = CapabilityWeight(**weight_data)
            continue
        # break landed here — skip this model
    return result


def load_config(project_root: Path | None = None) -> Config:
    """Load configuration from YAML config file and environment variables.

    Args:
        project_root: Optional project root path. Defaults to cwd.

    Returns:
        Immutable Config instance.

    Raises:
        ConfigError: On missing API key, malformed YAML, or invalid config values.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ConfigError(
            "OPENROUTER_API_KEY not set. Add it to your .mcp.json environment variables."
        )

    root = project_root or get_project_root()
    config_path = root / ".aicouncil" / "config.yaml"

    config_dict: dict[str, Any] = {"api_key": api_key}

    if config_path.exists():
        try:
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse {config_path}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read {config_path}: {e}") from e

        if yaml_data and isinstance(yaml_data, dict):
            # Map YAML fields to Config fields
            if "default_model" in yaml_data:
                config_dict["default_model"] = yaml_data["default_model"]
            elif "model" in yaml_data:
                # Backward compat: accept 'model' key
                config_dict["default_model"] = yaml_data["model"]

            for field in (
                "temperature",
                "max_output_tokens",
                "default_context",
                "preferred_personas",
                "timeout_seconds",
                "retry_attempts",
                "json_response",
                "include_reasoning",
                "model_pool",
            ):
                if field in yaml_data:
                    config_dict[field] = yaml_data[field]

            # Parse tool overrides — filter out None/commented values
            raw_overrides = yaml_data.get("tool_overrides")
            if isinstance(raw_overrides, dict):
                config_dict["tool_overrides"] = {
                    k: v for k, v in raw_overrides.items() if v is not None
                }

            # Parse capability weights
            raw_weights = yaml_data.get("capability_weights")
            if isinstance(raw_weights, dict):
                config_dict["capability_weights"] = _parse_capability_weights(raw_weights)

    # Apply env var overrides (backward compat)
    env_model = os.environ.get("OPENROUTER_MODEL")
    if env_model and "default_model" not in config_dict:
        config_dict["default_model"] = env_model

    env_temp = os.environ.get("OPENROUTER_TEMPERATURE")
    if env_temp:
        config_dict["temperature"] = float(env_temp)

    env_max_tokens = os.environ.get("OPENROUTER_MAX_TOKENS")
    if env_max_tokens:
        config_dict["max_output_tokens"] = int(env_max_tokens)

    env_timeout = os.environ.get("OPENROUTER_TIMEOUT")
    if env_timeout:
        config_dict["timeout_seconds"] = int(env_timeout)

    env_context = os.environ.get("OPENROUTER_DEFAULT_CONTEXT")
    if env_context:
        config_dict["default_context"] = env_context

    try:
        return Config(**config_dict)
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {e}") from e


# Singleton config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the current configuration (lazy loaded singleton)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Force reload the configuration."""
    global _config
    _config = load_config()
    return _config


def reset_config() -> None:
    """Reset the singleton (for testing)."""
    global _config
    _config = None
