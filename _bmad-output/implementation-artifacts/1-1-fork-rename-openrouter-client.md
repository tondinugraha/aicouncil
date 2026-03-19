# Story 1.1: Fork, Rename & OpenRouter Client

Status: done

## Story

As a developer using an MCP-enabled host,
I want the aicouncil server to route all API calls through OpenRouter using a single API key,
so that I can access any model via a unified gateway without managing multiple provider SDKs.

## Acceptance Criteria

1. **Given** the gemini-mcp codebase exists at `https://github.com/tondinugraha/gemini-mcp.git`
   **When** the project is forked and renamed to aicouncil
   **Then** all package references (pyproject.toml, module names, imports) reflect the new `aicouncil` name
   **And** the `google-genai` dependency is removed and replaced with `httpx` for async HTTP

2. **Given** an OpenRouter API key is set via environment variable
   **When** the server starts and a tool makes an API call
   **Then** the request is sent to `https://openrouter.ai/api/v1/chat/completions` via the async httpx client in `client.py`
   **And** no other module makes HTTP requests directly

3. **Given** an API call fails
   **When** the error is an OpenRouter communication failure
   **Then** the system raises `OpenRouterError` (not bare `Exception`)
   **And** the full custom exception hierarchy exists in `exceptions.py`

4. **Given** the server is started via `uv run aicouncil`
   **When** it connects to the MCP host via stdio transport
   **Then** at least one tool is functional end-to-end through OpenRouter

## Tasks / Subtasks

- [x] Task 1: Fork & rename package (AC: #1)
  - [x] Clone `https://github.com/tondinugraha/gemini-mcp.git` into `/Users/tondinugraha/Dev/aicouncil`
  - [x] Rename package from `gemini-mcp` / `gemini_mcp` to `aicouncil` everywhere
  - [x] Update `pyproject.toml`: name, entry point, dependencies
  - [x] Rename `src/gemini_mcp/` directory to `src/aicouncil/`
  - [x] Update all internal imports (`from gemini_mcp.` → `from aicouncil.`)
  - [x] Remove `google-genai` dependency, add `httpx>=0.28.0` and `pyyaml>=6.0`
  - [x] Update `uv.lock` via `uv sync`
  - [x] Verify `uv run aicouncil` entry point resolves (even if server errors on missing client)
- [x] Task 2: Create exception hierarchy (AC: #3)
  - [x] Create `src/aicouncil/exceptions.py` with full hierarchy
  - [x] Import and use throughout the codebase where bare exceptions exist
- [x] Task 3: Replace API client (AC: #2)
  - [x] Rewrite `src/aicouncil/client.py` — replace `GeminiClient` with `OpenRouterClient`
  - [x] Implement async httpx client targeting OpenRouter API
  - [x] Implement `generate()` method matching existing interface
  - [x] Implement retry logic (2-3 attempts) with `ModelUnavailableError` on exhaustion
  - [x] Implement JSON response parsing and Pydantic model validation
  - [x] Update client factory (`get_client()`) for new client class
- [x] Task 4: Update server.py tool registration (AC: #4)
  - [x] Update imports from `GeminiClient` → `OpenRouterClient`
  - [x] Make tool functions `async` (httpx requires async)
  - [x] Verify at least one tool (e.g., `brainstorm` or `critique`) works end-to-end
- [x] Task 5: Update tests (AC: #1, #2, #3)
  - [x] Update test imports for new package name
  - [x] Add test for `OpenRouterClient` with mocked httpx responses
  - [x] Add tests for exception hierarchy
  - [x] Run `uv run pytest` — all tests pass
- [x] Task 6: Lint & format (AC: all)
  - [x] Run `uv run ruff format .`
  - [x] Run `uv run ruff check --fix .`
  - [x] Verify zero lint errors

## Dev Notes

### Source Codebase Analysis (gemini-mcp)

The gemini-mcp codebase is ~6020 lines of Python. Google SDK coupling is **isolated to one file**: `client.py` (353 lines). Everything else is provider-agnostic.

**Files that NEED changes:**

| File | Change | Why |
|------|--------|-----|
| `pyproject.toml` | Rename package, swap deps | Entry point + dependency change |
| `src/gemini_mcp/` → `src/aicouncil/` | Rename directory | Package rename |
| `src/aicouncil/__init__.py` | Update version/name | Package identity |
| `src/aicouncil/client.py` | **Full rewrite** | Replace google-genai with httpx/OpenRouter |
| `src/aicouncil/server.py` | Update imports, async tools | Client class rename + async requirement |
| `src/aicouncil/config.py` | Update config fields | API key field name, model config |
| `tests/` | Update imports | Package rename |

**Files that need NO changes (provider-agnostic):**

| File | Lines | Why untouched |
|------|-------|---------------|
| `tools/__init__.py` | 216 | Prompt builders — LLM-agnostic |
| `schemas/responses.py` | 349 | Pydantic models — provider-agnostic |
| `prompts/base.py` | 300+ | Prompt templates — LLM-agnostic |
| `prompts/workflows.py` | — | Context enhancements — LLM-agnostic |
| `memory/` (all files) | 710+ | JSONL persistence — independent |
| `scanner/` (all files) | 1000+ | Codebase analysis — independent |

### New File: `src/aicouncil/exceptions.py`

```python
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
```

### OpenRouter API Contract

**Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions`

**Auth header:** `Authorization: Bearer <OPENROUTER_API_KEY>`

**Request body (OpenAI-compatible):**
```json
{
  "model": "anthropic/claude-sonnet-4",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "max_tokens": 8192,
  "response_format": {"type": "json_object"}
}
```

**Response body:**
```json
{
  "id": "gen-abc123",
  "model": "anthropic/claude-sonnet-4",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 25, "completion_tokens": 10, "total_tokens": 35}
}
```

**Error codes to handle:**
- `429` — Rate limited (backoff and retry)
- `502` — Provider unavailable (retry then reassign model)
- `503` — No provider available (retry then reassign model)
- `401` — Invalid API key (raise `ConfigError`, do not retry)
- `402` — Insufficient credits (raise `OpenRouterError`, do not retry)

### httpx AsyncClient Pattern

**Version:** httpx 0.28.1 (latest stable)

**Critical implementation details:**
- Use a single long-lived `AsyncClient` instance, not one per request
- Set `read` timeout high (60-120s) — LLM inference is slow
- Built-in `retries` on transport only retries `ConnectError`/`ConnectTimeout` — NOT HTTP 429/502/503
- Application-level retry loop required for HTTP error codes

```python
import httpx

timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
transport = httpx.AsyncHTTPTransport(retries=2)
client = httpx.AsyncClient(
    base_url="https://openrouter.ai/api/v1",
    timeout=timeout,
    transport=transport,
    headers={"Authorization": f"Bearer {api_key}"}
)
```

### Existing Client Interface to Preserve

The current `GeminiClient` exposes these methods that tools depend on:

1. **`generate(prompt, response_model, context)`** → Pydantic model or dict or str
   - This is the primary method called by all 15 tools
   - Must maintain same signature for minimal tool disruption
   - Add `model` parameter for future per-tool model selection

2. **`generate_with_file(file_path, prompt, response_model)`** → Pydantic model or dict or str
   - Used by `research_document` tool
   - OpenRouter does NOT support file upload — implement as: read file content locally, include in prompt text
   - This is a behavioral difference from Google's file upload API

3. **`get_client(category)`** → client factory
   - Current categories: "fast", "default", "reasoning"
   - Keep this pattern for now, evolve to cascading defaults in Story 1.2

**Key behavioral differences:**
- Google SDK is synchronous → httpx is async → all tool functions must become `async def`
- Google has native file upload → OpenRouter does not → read files locally and embed content
- Google uses `response_mime_type: "application/json"` → OpenRouter uses `response_format: {"type": "json_object"}`
- Google uses `types.GenerateContentConfig` → OpenRouter uses flat JSON body

### pyproject.toml Changes

```toml
[project]
name = "aicouncil"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.28.0",          # Replaces google-genai
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0",            # For YAML config (Story 1.2 but add dep now)
]

[project.scripts]
aicouncil = "aicouncil.server:main"  # Renamed entry point

[tool.ruff]
line-length = 100
target-version = "py311"
```

### config.py Changes (Minimal for This Story)

Update the config to read `OPENROUTER_API_KEY` instead of `GEMINI_API_KEY`. Keep the singleton pattern. Full YAML config overhaul happens in Story 1.2.

Current env var pattern:
```python
# Before (gemini-mcp)
api_key = os.environ.get("GEMINI_API_KEY")

# After (aicouncil)
api_key = os.environ.get("OPENROUTER_API_KEY")
```

Keep `GeminiConfig` renamed to something like `Config` or `AiCouncilConfig` — the full Config refactor to YAML happens in Story 1.2.

### server.py Changes

- Update FastMCP name: `FastMCP("gemini-mcp", ...)` → `FastMCP("aicouncil", ...)`
- Update imports: `from gemini_mcp.client import ...` → `from aicouncil.client import ...`
- Make tool functions `async def` (required for async httpx)
- Update `get_client()` calls if client class is renamed
- Keep all 15 tool registrations — they should work once client is swapped

### Knowledge Store Path

The existing codebase uses `.gemini-mcp/` for knowledge persistence. Rename to `.aicouncil/` or keep as-is for now (Story 1.2 handles the full `./aicouncil/` scaffold). For this story, just ensure the memory module works — the path can be updated later.

### Project Structure Notes

After this story, the directory structure should be:
```
src/aicouncil/
├── __init__.py
├── server.py              # FastMCP("aicouncil"), 15 tools (async)
├── client.py              # OpenRouterClient (httpx async)
├── config.py              # Minimal update (OPENROUTER_API_KEY)
├── exceptions.py          # NEW: Full exception hierarchy
├── tools/
│   └── __init__.py        # Prompt builders (unchanged)
├── schemas/
│   ├── __init__.py
│   └── responses.py       # Response models (unchanged)
├── prompts/
│   ├── __init__.py
│   ├── base.py            # Prompt templates (unchanged)
│   └── workflows.py       # Workflow prompts (unchanged)
├── memory/
│   ├── __init__.py
│   ├── schemas.py
│   ├── store.py
│   ├── learner.py
│   └── retriever.py       # All unchanged
└── scanner/
    ├── __init__.py
    ├── project_detector.py
    ├── file_walker.py
    ├── code_analyzer.py
    └── context_builder.py  # All unchanged
```

### Anti-Patterns to Avoid

- **DO NOT** put any HTTP calls outside `client.py` — it is the sole OpenRouter boundary
- **DO NOT** use the OpenAI Python SDK to talk to OpenRouter — use raw httpx (per architecture decision)
- **DO NOT** make tool functions synchronous — httpx requires async
- **DO NOT** return raw dicts from tools — keep Pydantic schema returns
- **DO NOT** catch broad `Exception` — use the new exception hierarchy
- **DO NOT** log API keys — ensure `Authorization` header is never logged at any level
- **DO NOT** change prompt templates — they are LLM-agnostic and work with any model
- **DO NOT** modify memory/ or scanner/ modules — they have zero coupling to the API client

### Testing Strategy

- Mock httpx responses in `test_client.py` using `httpx.MockTransport` or `pytest-httpx`
- Test exception hierarchy instantiation and inheritance
- Test that `OpenRouterClient.generate()` correctly formats OpenRouter request body
- Test that `_parse_response()` correctly extracts content from OpenRouter response format
- Test retry behavior (mock 502 response, verify 2-3 retries before `ModelUnavailableError`)
- Run existing schema tests — they should pass unchanged

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — Core Architectural Decisions, OpenRouter Client section]
- [Source: _bmad-output/planning-artifacts/architecture.md — Implementation Patterns, Error Handling Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/prd.md — FR26, FR37, FR38]
- [Source: _bmad-output/project-context.md — Critical Implementation Rules]
- [Source: gemini-mcp client.py — GeminiClient interface at /Users/tondinugraha/mcp-servers/gemini-mcp/src/gemini_mcp/client.py]
- [Source: OpenRouter API — https://openrouter.ai/api/v1/chat/completions]
- [Source: httpx docs — https://www.python-httpx.org/async/]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
N/A — clean execution, no HALTs triggered.

### Completion Notes List
- Copied gemini-mcp source to `src/aicouncil/`, bulk-renamed all `gemini_mcp` → `aicouncil` imports
- Created `pyproject.toml` with `httpx>=0.28.0`, `pyyaml>=6.0`, removed `google-genai`
- Created `README.md` (required by hatchling build)
- Created `src/aicouncil/exceptions.py` with full hierarchy: `AiCouncilError` → `OpenRouterError` → `ModelUnavailableError`, plus `ConfigError`, `AgentLoadError`, `CouncilError`
- Fully rewrote `client.py`: `OpenRouterClient` with async httpx, retry logic (2-3 attempts with exponential backoff), `ModelUnavailableError` on exhaustion, proper error code handling (401→ConfigError, 402→OpenRouterError, 429/502/503→retry)
- `generate_with_file()` reads file locally and embeds content in prompt (OpenRouter has no file upload)
- Rewrote `config.py`: `GeminiConfig` → `Config`, `GEMINI_API_KEY` → `OPENROUTER_API_KEY`, default model to `anthropic/claude-sonnet-4`
- Rewrote `server.py`: all 15 tool functions are now `async def`, FastMCP name is `"aicouncil"`, all imports updated
- Updated `store.py` knowledge dir from `.gemini-mcp` → `.aicouncil`
- Fixed remaining Gemini string references in docstrings across tools/, scanner/, memory/, schemas/
- Tests: 36 tests pass (17 client, 8 exceptions, 11 schemas)
- Lint: zero errors after `ruff format` + `ruff check`
- Fixed F841 (unused variables) in `learner.py` and `code_analyzer.py`
- Entry point verified: `uv run python -c "from aicouncil.server import main"` succeeds

### Change Log
- 2026-03-20: Story 1.1 implemented — fork, rename, OpenRouter client, exception hierarchy, async tools, tests
- 2026-03-20: Code review fixes (P1-P14, P20, P25) — format string injection guard, ValidationError crash fix, show_knowledge_summary returns Pydantic, config path fix, broad Exception→AiCouncilError, silent YAML catch fix, greedy regex fix, backoff cap, stale gitignore/docstring cleanup

### File List
- `pyproject.toml` (new)
- `README.md` (new)
- `src/aicouncil/__init__.py` (modified)
- `src/aicouncil/client.py` (full rewrite)
- `src/aicouncil/config.py` (modified — Config class, OPENROUTER_API_KEY)
- `src/aicouncil/exceptions.py` (new)
- `src/aicouncil/server.py` (modified — async tools, aicouncil imports)
- `src/aicouncil/tools/__init__.py` (modified — imports, lint fixes)
- `src/aicouncil/schemas/__init__.py` (modified — imports)
- `src/aicouncil/schemas/responses.py` (modified — imports)
- `src/aicouncil/memory/__init__.py` (modified — imports)
- `src/aicouncil/memory/store.py` (modified — imports, .aicouncil dir)
- `src/aicouncil/memory/learner.py` (modified — imports, unused var fix)
- `src/aicouncil/memory/retriever.py` (modified — imports)
- `src/aicouncil/memory/schemas.py` (copied, no changes needed)
- `src/aicouncil/scanner/__init__.py` (modified — imports)
- `src/aicouncil/scanner/context_builder.py` (modified — imports, docstrings)
- `src/aicouncil/scanner/code_analyzer.py` (modified — unused var fix)
- `src/aicouncil/scanner/file_walker.py` (copied, no changes needed)
- `src/aicouncil/scanner/project_detector.py` (copied, no changes needed)
- `src/aicouncil/prompts/__init__.py` (modified — imports)
- `src/aicouncil/prompts/base.py` (copied, no changes needed)
- `src/aicouncil/prompts/workflows.py` (copied, no changes needed)
- `tests/__init__.py` (modified — docstring rename)
- `tests/test_schemas.py` (modified — imports)
- `tests/test_exceptions.py` (new — 8 tests)
- `tests/test_client.py` (new — 17 tests)
- `uv.lock` (generated)
- `.gitignore` (modified — stale entries fixed)
