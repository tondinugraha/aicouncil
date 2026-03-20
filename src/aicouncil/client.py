"""OpenRouter API client with async httpx, retry logic, and structured response parsing."""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from aicouncil.config import get_config
from aicouncil.exceptions import ConfigError, ModelUnavailableError, OpenRouterError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# HTTP status codes that should trigger retry
_RETRYABLE_STATUS_CODES = {429, 502, 503}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    """Async client for the OpenRouter chat completions API."""

    def __init__(self, model: str | None = None, config: Any | None = None) -> None:
        """Initialize the OpenRouter client.

        Args:
            model: Optional model name override.
            config: Optional config override (for testing).
        """
        self._config = config or get_config()
        self.model_name = model or self._config.model
        self._http_client: httpx.AsyncClient | None = None
        logger.debug(f"Initialized OpenRouterClient with model: {self.model_name}")

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the shared async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
            transport = httpx.AsyncHTTPTransport(retries=2)
            self._http_client = httpx.AsyncClient(
                base_url=OPENROUTER_BASE_URL,
                timeout=timeout,
                transport=transport,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "OpenRouterClient":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager, closing HTTP client."""
        await self.close()

    async def generate(
        self,
        prompt: str,
        response_model: type[T] | None = None,
        context: str | None = None,
        model: str | None = None,
    ) -> T | dict[str, Any] | str:
        """Generate a response from OpenRouter.

        Args:
            prompt: The prompt to send.
            response_model: Optional Pydantic model for structured responses.
            context: Optional additional context to prepend.
            model: Optional per-call model override.

        Returns:
            Parsed response as model instance, dict, or raw string.
        """
        messages = self._build_messages(prompt, context, response_model)
        request_model = model or self.model_name

        body: dict[str, Any] = {
            "model": request_model,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_output_tokens,
        }

        if response_model and self._config.json_response:
            body["response_format"] = {"type": "json_object"}

        max_attempts = self._config.retry_attempts
        last_error: Exception | None = None

        for attempt in range(max_attempts):
            try:
                text = await self._send_request(body)
                return self._parse_response(text, response_model)
            except OpenRouterError as e:
                logger.warning(f"OpenRouter API error (attempt {attempt + 1}): {e}")
                last_error = e
                if attempt < max_attempts - 1:
                    backoff = min(2**attempt, 30)
                    logger.debug(f"Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)

        if isinstance(last_error, OpenRouterError):
            raise ModelUnavailableError(
                f"Model {request_model} unavailable after {max_attempts} attempts: {last_error}"
            )
        return self._error_response("Unknown error", response_model)

    async def generate_with_file(
        self,
        file_path: str,
        prompt: str,
        response_model: type[T] | None = None,
        context: str | None = None,
    ) -> T | dict[str, Any] | str:
        """Generate a response with file content included in the prompt.

        OpenRouter does not support file upload. The file is read locally
        and its content is embedded in the prompt text.

        Args:
            file_path: Path to the file to read and include.
            prompt: The prompt to send.
            response_model: Optional Pydantic model for structured responses.
            context: Optional additional context to prepend.

        Returns:
            Parsed response as model instance, dict, or raw string.
        """
        path = Path(file_path)
        if not path.exists():
            return self._error_response(f"File not found: {file_path}", response_model)

        try:
            file_content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return self._error_response(f"Failed to read file: {e}", response_model)

        augmented_prompt = (
            f"## Document Content\n\n"
            f"File: {path.name}\n\n"
            f"```\n{file_content}\n```\n\n"
            f"## Analysis Request\n\n{prompt}"
        )
        return await self.generate(augmented_prompt, response_model, context)

    async def _send_request(self, body: dict[str, Any]) -> str:
        """Send request to OpenRouter and return the response text.

        Raises:
            ConfigError: For 401 (invalid API key).
            OpenRouterError: For retryable or non-retryable API errors.
        """
        client = await self._get_http_client()

        logger.debug(f"Sending request to OpenRouter: model={body.get('model')}")
        response = await client.post("/chat/completions", json=body)

        if response.status_code == 401:
            raise ConfigError("Invalid OpenRouter API key (401)")
        if response.status_code == 402:
            raise OpenRouterError("Insufficient OpenRouter credits (402)")
        if response.status_code in _RETRYABLE_STATUS_CODES:
            raise OpenRouterError(
                f"OpenRouter returned {response.status_code}: {response.text[:200]}"
            )
        if response.status_code >= 400:
            raise OpenRouterError(f"OpenRouter error {response.status_code}: {response.text[:200]}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise OpenRouterError("OpenRouter response contained no choices")

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise OpenRouterError("OpenRouter response contained empty content")

        usage = data.get("usage", {})
        logger.debug(
            f"OpenRouter response: model={data.get('model')}, "
            f"tokens={usage.get('total_tokens', 'unknown')}"
        )
        return content

    def _build_messages(
        self,
        prompt: str,
        context: str | None,
        response_model: type[T] | None,
    ) -> list[dict[str, str]]:
        """Build the messages array for the OpenRouter request."""
        messages: list[dict[str, str]] = []

        # System message with context
        system_parts: list[str] = []
        if self._config.default_context:
            system_parts.append(f"Project Context: {self._config.default_context}")
        if context:
            system_parts.append(f"Additional Context:\n{context}")

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        # User message with prompt and optional schema instruction
        user_content = prompt
        if response_model and self._config.json_response:
            schema = response_model.model_json_schema()
            user_content += (
                f"\n\nIMPORTANT: Respond ONLY with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```\n"
                f"Do not include any text before or after the JSON."
            )
        messages.append({"role": "user", "content": user_content})

        return messages

    def _parse_response(
        self,
        text: str,
        response_model: type[T] | None,
    ) -> T | dict[str, Any] | str:
        """Parse the response text into the expected format."""
        if not response_model:
            return text

        json_text = self._extract_json(text)

        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from response: {json_text[:200]}...")
            return self._error_response("Invalid JSON in model response", response_model)

        try:
            return response_model.model_validate(data)
        except ValidationError as e:
            logger.warning(f"Response validation failed: {e}")
            return self._error_response(f"Response validation failed: {e}", response_model)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text, handling markdown code blocks."""
        text = text.strip()

        code_block_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if code_block_match:
            return code_block_match.group(1).strip()

        json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if json_match:
            return json_match.group(1).strip()

        return text

    def _error_response(
        self,
        error_msg: str,
        response_model: type[T] | None,
    ) -> T | dict[str, Any]:
        """Create an error response in the expected format."""
        error_data: dict[str, Any] = {
            "error": True,
            "message": error_msg,
        }

        if response_model:
            try:
                schema = response_model.model_json_schema()
                minimal_data: dict[str, Any] = {}
                for field_name, field_info in schema.get("properties", {}).items():
                    if field_name in schema.get("required", []):
                        minimal_data[field_name] = self._default_for_field(
                            field_info, error_msg, schema.get("$defs", {})
                        )
                return response_model.model_validate(minimal_data)
            except (ValidationError, KeyError, TypeError) as e:
                logger.warning(f"Failed to construct error response model: {e}")
                return error_data

        return error_data

    def _default_for_field(
        self,
        field_info: dict[str, Any],
        error_msg: str,
        defs: dict[str, Any],
    ) -> Any:
        """Determine a safe default value for a schema field."""
        # Literal/enum fields — pick the first allowed value
        if "enum" in field_info:
            return field_info["enum"][0]

        # anyOf (Optional, Union) — pick first non-null variant
        if "anyOf" in field_info:
            for variant in field_info["anyOf"]:
                if variant.get("type") == "null":
                    continue
                return self._default_for_field(variant, error_msg, defs)
            return None

        # $ref — resolve from $defs
        if "$ref" in field_info:
            ref_name = field_info["$ref"].rsplit("/", 1)[-1]
            if ref_name in defs:
                return self._default_for_field(defs[ref_name], error_msg, defs)
            return None

        field_type = field_info.get("type", "string")
        if field_type == "string":
            return f"Error: {error_msg}"
        elif field_type == "array":
            return []
        elif field_type == "object":
            return {}
        elif field_type == "boolean":
            return False
        elif field_type == "number":
            return 0.0
        elif field_type == "integer":
            return 0
        return None
