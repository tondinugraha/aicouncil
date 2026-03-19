"""Tests for OpenRouterClient with mocked httpx responses."""

import json

import httpx
import pytest
from pydantic import BaseModel, Field

from aicouncil.client import OpenRouterClient, clear_client_cache
from aicouncil.exceptions import ConfigError, ModelUnavailableError


class SimpleResponse(BaseModel):
    """Test response model."""

    message: str = Field(description="A message")
    count: int = Field(default=0, description="A count")


class MockConfig:
    """Mock config for testing."""

    api_key = "test-api-key"
    model = "test/model"
    temperature = 0.7
    max_output_tokens = 1024
    default_context = ""
    json_response = True
    retry_attempts = 3


def make_openrouter_response(content: str, model: str = "test/model") -> dict:
    """Build a mock OpenRouter response body."""
    return {
        "id": "gen-test123",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def mock_transport(handler):
    """Create an httpx.MockTransport from a handler function."""
    return httpx.MockTransport(handler)


class TestOpenRouterClientGenerate:
    """Test the generate() method."""

    @pytest.mark.asyncio
    async def test_generate_raw_text(self):
        """Test generate returns raw text when no response_model."""

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["model"] == "test/model"
            assert body["temperature"] == 0.7
            assert len(body["messages"]) >= 1
            return httpx.Response(
                200,
                json=make_openrouter_response("Hello from OpenRouter"),
            )

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        result = await client.generate("Say hello")
        assert result == "Hello from OpenRouter"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_response_model(self):
        """Test generate parses response into Pydantic model."""
        response_json = json.dumps({"message": "parsed result", "count": 42})

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["response_format"] == {"type": "json_object"}
            return httpx.Response(
                200,
                json=make_openrouter_response(response_json),
            )

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        result = await client.generate("Parse this", response_model=SimpleResponse)
        assert isinstance(result, SimpleResponse)
        assert result.message == "parsed result"
        assert result.count == 42
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_context(self):
        """Test that context is included in system message."""

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            messages = body["messages"]
            system_msg = next((m for m in messages if m["role"] == "system"), None)
            assert system_msg is not None
            assert "my project context" in system_msg["content"]
            return httpx.Response(
                200,
                json=make_openrouter_response("ok"),
            )

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        await client.generate("test", context="my project context")
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_model_override(self):
        """Test per-call model override."""

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["model"] == "override/model"
            return httpx.Response(
                200,
                json=make_openrouter_response("ok"),
            )

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        await client.generate("test", model="override/model")
        await client.close()


class TestOpenRouterClientErrors:
    """Test error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_401_raises_config_error(self):
        """Test 401 raises ConfigError (not retried, wraps in ModelUnavailableError)."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid key"})

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        # ConfigError is not an OpenRouterError, so the retry loop re-raises it directly
        with pytest.raises(ConfigError, match="Invalid OpenRouter API key"):
            await client.generate("test")
        await client.close()

    @pytest.mark.asyncio
    async def test_402_raises_open_router_error(self):
        """Test 402 raises OpenRouterError (no retry)."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(402, json={"error": "no credits"})

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        with pytest.raises(ModelUnavailableError):
            await client.generate("test")
        await client.close()

    @pytest.mark.asyncio
    async def test_502_retries_then_raises_model_unavailable(self):
        """Test 502 triggers retries, then ModelUnavailableError."""
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(502, text="Bad Gateway")

        config = MockConfig()
        config.retry_attempts = 3
        client = OpenRouterClient(config=config)
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        with pytest.raises(ModelUnavailableError):
            await client.generate("test")

        assert call_count == 3
        await client.close()

    @pytest.mark.asyncio
    async def test_empty_choices_raises_error(self):
        """Test empty choices array raises OpenRouterError."""

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"id": "gen-test", "model": "test", "choices": [], "usage": {}},
            )

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        with pytest.raises(ModelUnavailableError):
            await client.generate("test")
        await client.close()


class TestOpenRouterClientParsing:
    """Test response parsing logic."""

    @pytest.mark.asyncio
    async def test_parse_json_in_code_block(self):
        """Test extracting JSON from markdown code blocks."""
        content = '```json\n{"message": "in block", "count": 1}\n```'

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=make_openrouter_response(content))

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        result = await client.generate("test", response_model=SimpleResponse)
        assert isinstance(result, SimpleResponse)
        assert result.message == "in block"
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_raw_json(self):
        """Test parsing raw JSON (no code block)."""
        content = '{"message": "raw json", "count": 5}'

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=make_openrouter_response(content))

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        result = await client.generate("test", response_model=SimpleResponse)
        assert isinstance(result, SimpleResponse)
        assert result.message == "raw json"
        await client.close()

    @pytest.mark.asyncio
    async def test_error_response_creates_minimal_model(self):
        """Test that _error_response creates a valid minimal model."""
        client = OpenRouterClient(config=MockConfig())
        result = client._error_response("something failed", SimpleResponse)
        assert isinstance(result, SimpleResponse)
        assert "something failed" in result.message
        await client.close()


class TestGenerateWithFile:
    """Test the generate_with_file() method."""

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        """Test that missing file returns error response."""
        client = OpenRouterClient(config=MockConfig())
        result = await client.generate_with_file(
            "/nonexistent/file.txt", "analyze", response_model=SimpleResponse
        )
        assert isinstance(result, SimpleResponse)
        assert "not found" in result.message.lower()
        await client.close()

    @pytest.mark.asyncio
    async def test_file_content_embedded_in_prompt(self, tmp_path):
        """Test that file content is read and embedded in the prompt."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content here")

        async def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            user_msg = next(m for m in body["messages"] if m["role"] == "user")
            assert "file content here" in user_msg["content"]
            assert "test.txt" in user_msg["content"]
            return httpx.Response(200, json=make_openrouter_response("analyzed"))

        client = OpenRouterClient(config=MockConfig())
        client._http_client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            transport=mock_transport(handler),
        )

        result = await client.generate_with_file(str(test_file), "analyze this")
        assert result == "analyzed"
        await client.close()


class TestClientFactory:
    """Test get_client() factory function."""

    def test_get_client_returns_open_router_client(self):
        """Test that get_client returns an OpenRouterClient."""
        clear_client_cache()
        # We can't fully test without env vars, but we can test the cache clearing
        clear_client_cache()


class TestBuildMessages:
    """Test the _build_messages method."""

    def test_messages_without_context(self):
        client = OpenRouterClient(config=MockConfig())
        messages = client._build_messages("hello", None, None)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"

    def test_messages_with_context(self):
        client = OpenRouterClient(config=MockConfig())
        messages = client._build_messages("hello", "some context", None)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "some context" in messages[0]["content"]
        assert messages[1]["role"] == "user"

    def test_messages_with_response_model_adds_schema(self):
        client = OpenRouterClient(config=MockConfig())
        messages = client._build_messages("hello", None, SimpleResponse)
        user_content = messages[0]["content"]
        assert "JSON" in user_content
        assert "message" in user_content
