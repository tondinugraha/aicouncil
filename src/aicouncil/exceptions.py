"""Custom exception hierarchy for AI Council."""


class AiCouncilError(Exception):
    """Base exception for all aicouncil errors."""


class OpenRouterError(AiCouncilError):
    """API communication failures with OpenRouter."""


class ModelUnavailableError(OpenRouterError):
    """Specific model is unreachable after retries."""


class ConfigError(AiCouncilError):
    """Configuration loading or validation failures."""


class AgentLoadError(AiCouncilError):
    """Agent manifest or persona file parsing failures."""


class CouncilError(AiCouncilError):
    """Council assembly or deliberation failures."""
