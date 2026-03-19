"""Configuration management for AI Council server."""

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

# Model category type for type hints
ModelCategory = Literal["fast", "default", "reasoning"]


class ModelConfig(BaseModel):
    """Configuration for model selection by task category."""

    fast: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Fast model for quick iterations",
    )
    default: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Default fallback model",
    )
    reasoning: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Reasoning model for deep analysis",
    )

    def get_model(self, category: ModelCategory = "default") -> str:
        """Get the model for a specific category."""
        return getattr(self, category, self.default)


class Config(BaseModel):
    """Configuration for the AI Council server."""

    # API Configuration
    api_key: str = Field(description="OpenRouter API key")
    model: str = Field(
        default="anthropic/claude-sonnet-4",
        description="Default model to use via OpenRouter",
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


def load_config() -> Config:
    """Load configuration from environment variables and optional config file."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        from aicouncil.exceptions import ConfigError

        raise ConfigError(
            "OPENROUTER_API_KEY environment variable is required. "
            "Get your key at https://openrouter.ai/keys"
        )

    config_dict: dict[str, Any] = {
        "api_key": api_key,
        "model": os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4"),
        "temperature": float(os.environ.get("OPENROUTER_TEMPERATURE", "0.7")),
        "max_output_tokens": int(os.environ.get("OPENROUTER_MAX_TOKENS", "8192")),
        "timeout_seconds": int(os.environ.get("OPENROUTER_TIMEOUT", "120")),
        "default_context": os.environ.get("OPENROUTER_DEFAULT_CONTEXT", ""),
    }

    # Try to load project-specific config if it exists
    project_config_path = Path.cwd() / "aicouncil" / "config.yaml"
    if project_config_path.exists():
        try:
            import yaml

            with open(project_config_path) as f:
                project_config = yaml.safe_load(f)
                if project_config:
                    if "default_context" in project_config:
                        config_dict["default_context"] = project_config["default_context"]
                    if "preferred_personas" in project_config:
                        config_dict["preferred_personas"] = project_config["preferred_personas"]
                    if "model" in project_config:
                        config_dict["model"] = project_config["model"]
                    if "temperature" in project_config:
                        config_dict["temperature"] = project_config["temperature"]
        except ImportError:
            pass
        except yaml.YAMLError as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to parse {project_config_path}: {e}")
        except OSError as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to read {project_config_path}: {e}")

    return Config(**config_dict)


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


# Singleton model config instance
_model_config: ModelConfig | None = None


def get_model_config() -> ModelConfig:
    """Get the model configuration for task-based model selection.

    Supports OPENROUTER_MODELS env var as JSON:
    {"fast": "anthropic/claude-haiku-4-5", "default": "anthropic/claude-sonnet-4", ...}

    Falls back to OPENROUTER_MODEL for all categories.
    """
    global _model_config
    if _model_config is not None:
        return _model_config

    models_json = os.environ.get("OPENROUTER_MODELS")

    if models_json:
        try:
            models_dict = json.loads(models_json)
            _model_config = ModelConfig(**models_dict)
            return _model_config
        except (json.JSONDecodeError, ValueError):
            pass

    single_model = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")
    _model_config = ModelConfig(
        fast=single_model,
        default=single_model,
        reasoning=single_model,
    )
    return _model_config


def reload_model_config() -> ModelConfig:
    """Force reload the model configuration."""
    global _model_config
    _model_config = None
    return get_model_config()
