# Story 1.3: Extended Tools Migration

Status: review

## Story

As a developer using aicouncil utility tools,
I want all existing gemini-mcp tools (critique, brainstorm, validate, research, codebase scan, memory) to work with any model via OpenRouter and live in their proper tool modules,
so that I can use different models for different tasks, and the codebase follows the architecture's boundary rules.

## Acceptance Criteria

1. **Given** the existing tool logic lives inline in `server.py` (~1028 lines with 15 tools)
   **When** the migration is complete
   **Then** all tool business logic has moved to proper modules in `src/aicouncil/tools/` (analysis.py, research.py, codebase.py, memory.py)
   **And** `server.py` is a thin registry that imports tool functions and registers them via `@mcp.tool()`

2. **Given** tools currently use `get_client(category)` with categories "fast", "default", "reasoning"
   **When** any tool is invoked via MCP
   **Then** it resolves its model via `config.resolve_model(tool_name, per_invocation_override)` cascading: per-invocation → per-tool → global default
   **And** routes the API call through the OpenRouter client in `client.py`
   **And** tool behavior is identical to the original except the model is configurable per-tool

3. **Given** a tool has a per-tool model override in `config.yaml` (e.g., `tool_overrides.critique: "openai/gpt-4.1"`)
   **When** the tool is invoked without a per-invocation override
   **Then** it uses the per-tool model, not the global default
   **And** per-invocation overrides still take precedence over per-tool config

4. **Given** the council model pool is defined in `config.yaml`
   **When** the config is loaded
   **Then** the model pool array, capability weight matrix (model-centric format), and `context_window` per model are all accessible via the Config object
   **And** the capability weights ship with sensible defaults
   *(Note: This AC was already satisfied by Story 1.2 — verify it still works after refactoring)*

5. **Given** a model is unavailable during a tool call
   **When** the `client.py` receives an error from OpenRouter
   **Then** it retries 2-3 times before raising `ModelUnavailableError`
   *(Note: Retry logic already exists in client.py — verify it handles ModelUnavailableError correctly after migration)*

6. **Given** every MCP tool returns a response
   **When** the response is inspected
   **Then** it is a Pydantic `BaseModel` instance (never a raw dict or string)
   **And** error states are returned as structured error responses, not raw tracebacks

## Tasks / Subtasks

- [x] Task 1: Create `src/aicouncil/tools/analysis.py` (AC: #1, #2, #3, #6)
  - [x] Move 6 analysis tools from `server.py`: `critique`, `brainstorm`, `validate`, `challenge_assumptions`, `find_gaps`, `propose_alternatives`
  - [x] Each function accepts the same MCP parameters as currently defined in server.py
  - [x] Replace `get_client(category)` calls with direct `OpenRouterClient` instantiation using `config.resolve_model(tool_name)`
  - [x] Preserve knowledge context integration (architecture/code context injection via memory retriever)
  - [x] Preserve all prompt building via `tools/__init__.py` builder functions
  - [x] Return same Pydantic schema types (CritiqueResult, BrainstormResult, etc.)
  - [x] Error handling: catch exceptions, return structured error responses

- [x] Task 2: Create `src/aicouncil/tools/research.py` (AC: #1, #2, #3, #6)
  - [x] Move 2 research tools from `server.py`: `research_assist`, `research_document`
  - [x] Replace `get_client("reasoning")` with resolve_model pattern
  - [x] Preserve `generate_with_file()` usage in `research_document`
  - [x] Preserve auto-learning via KnowledgeLearner for document research insights

- [x] Task 3: Create `src/aicouncil/tools/codebase.py` (AC: #1, #2, #6)
  - [x] Move 3 codebase tools from `server.py`: `scan_codebase`, `critique_file`, `analyze_dependencies`
  - [x] Replace get_client calls with resolve_model pattern
  - [x] Preserve scanner module integration (ContextBuilder, ProjectDetector, CodeAnalyzer)
  - [x] Preserve auto-learning via KnowledgeLearner for scan and file analysis results
  - [x] `analyze_dependencies` is purely local (no LLM call) — ensure no model routing needed

- [x] Task 4: Create `src/aicouncil/tools/memory.py` (AC: #1, #6)
  - [x] Move 4 memory tools from `server.py`: `remember`, `recall`, `forget`, `show_knowledge_summary`
  - [x] These are local-only tools (no LLM calls) — just KnowledgeStore operations
  - [x] Preserve exact return types (MemoryResult, RecallResult)

- [x] Task 5: Refactor `server.py` to thin registry (AC: #1)
  - [x] Remove all tool business logic from server.py
  - [x] Import tool functions from `tools/analysis.py`, `tools/research.py`, `tools/codebase.py`, `tools/memory.py`
  - [x] Register each tool via `@mcp.tool()` decorator
  - [x] Keep `get_project_root()` helper (used by scanner tools)
  - [x] Keep `get_knowledge_context()` helper OR move it to a shared utility
  - [x] Preserve the `mcp = FastMCP("aicouncil", ...)` initialization
  - [x] Preserve `main()` function with scaffold + mcp.run()
  - [x] Final server.py should be <150 lines (registry + startup only)

- [x] Task 6: Refactor model resolution in client.py (AC: #2, #3)
  - [x] Deprecate/remove the category-based `get_client(category)` function
  - [x] Remove `ModelConfig` class and `get_model_config()` (no longer needed)
  - [x] Tool modules instantiate `OpenRouterClient(model=resolved_model)` directly
  - [x] OR create a new helper: `get_client_for_tool(tool_name, per_invocation=None)` that wraps `config.resolve_model()` + `OpenRouterClient()`
  - [x] Preserve `clear_client_cache()` for test cleanup if caching is kept

- [x] Task 7: Update `tools/__init__.py` (AC: #1)
  - [x] Keep prompt builder functions (they are still needed by tool modules)
  - [x] Add any necessary shared imports or re-exports
  - [x] Ensure tool modules can import builders: `from aicouncil.tools import build_critique_prompt`

- [x] Task 8: Write tests (AC: #1-#6)
  - [x] Create `tests/test_tools/test_analysis.py` — test all 6 analysis tools with mocked client
  - [x] Create `tests/test_tools/test_research.py` — test both research tools with mocked client
  - [x] Create `tests/test_tools/test_codebase.py` — test all 3 codebase tools with mocked scanner/client
  - [x] Create `tests/test_tools/test_memory.py` — test all 4 memory tools with mocked KnowledgeStore
  - [x] Test model resolution: verify tools use resolve_model correctly (per-tool override, global default, per-invocation)
  - [x] Test error handling: model unavailable → structured error response (not raw exception)
  - [x] Run `uv run pytest` — all tests pass (including existing 74 from Stories 1.1-1.2)
  - [x] No regressions in existing test suites

- [x] Task 9: Lint & format (AC: all)
  - [x] Run `uv run ruff format .`
  - [x] Run `uv run ruff check --fix .`
  - [x] Verify zero lint errors

## Dev Notes

### Current State (Post Story 1.2)

**The core problem:** All 15 MCP tool functions live inline in `server.py` (1028 lines). The architecture requires tool logic in `src/aicouncil/tools/` modules, with `server.py` as a thin registry. This story performs that migration AND switches from category-based model routing to per-tool configurable model resolution.

**What exists today:**

| Component | State | Location |
|-----------|-------|----------|
| 15 tool functions with full business logic | Inline in server.py | `src/aicouncil/server.py` (1028 lines) |
| Prompt builders (8 functions) | Already in tools/ | `src/aicouncil/tools/__init__.py` (231 lines) |
| Pydantic response schemas (all tools) | Complete | `src/aicouncil/schemas/responses.py` (332 lines) |
| Prompt templates (base + workflows) | Complete | `src/aicouncil/prompts/` |
| Memory subsystem (store/retriever/learner) | Complete | `src/aicouncil/memory/` |
| Scanner subsystem (4 modules) | Complete | `src/aicouncil/scanner/` |
| OpenRouter client with retry | Complete | `src/aicouncil/client.py` (326 lines) |
| Config with resolve_model() + cascading | Complete | `src/aicouncil/config.py` (361 lines) |
| Exception hierarchy | Complete | `src/aicouncil/exceptions.py` |
| Tests (74 passing) | client, config, exceptions, schemas, scaffold | `tests/` |

### Tool Inventory — What Moves Where

**`tools/analysis.py` (6 tools):**
| Tool | Current Model Category | New tool_name for resolve_model |
|------|----------------------|-------------------------------|
| `critique` | reasoning | "critique" |
| `brainstorm` | fast | "brainstorm" |
| `validate` | fast | "validate" |
| `challenge_assumptions` | reasoning | "challenge_assumptions" |
| `find_gaps` | reasoning | "find_gaps" |
| `propose_alternatives` | reasoning | "propose_alternatives" |

**`tools/research.py` (2 tools):**
| Tool | Current Model Category | New tool_name for resolve_model |
|------|----------------------|-------------------------------|
| `research_assist` | reasoning | "research_assist" |
| `research_document` | reasoning | "research_document" |

**`tools/codebase.py` (3 tools):**
| Tool | Current Model Category | New tool_name for resolve_model |
|------|----------------------|-------------------------------|
| `scan_codebase` | default | "scan_codebase" |
| `critique_file` | reasoning | "critique_file" |
| `analyze_dependencies` | N/A (no LLM call) | N/A |

**`tools/memory.py` (4 tools):**
| Tool | Current Model Category | New tool_name for resolve_model |
|------|----------------------|-------------------------------|
| `remember` | N/A (local only) | N/A |
| `recall` | N/A (local only) | N/A |
| `forget` | N/A (local only) | N/A |
| `show_knowledge_summary` | N/A (local only) | N/A |

### Model Resolution Migration Pattern

**Current pattern (category-based — to be removed):**
```python
# In server.py
client = get_client("reasoning")  # or "fast", "default"
result = await client.generate(prompt, response_model=CritiqueResult)
```

**New pattern (tool-name-based — cascading defaults):**
```python
# In tools/analysis.py
from aicouncil.config import get_config
from aicouncil.client import OpenRouterClient

async def critique(content: str, ..., model: str | None = None) -> CritiqueResult:
    config = get_config()
    resolved_model = config.resolve_model("critique", per_invocation=model)
    client = OpenRouterClient(model=resolved_model, config=config)
    result = await client.generate(prompt, response_model=CritiqueResult)
    ...
```

**Why this works:** `config.resolve_model("critique", model)` already implements the cascade:
1. If `model` is passed → use it (per-invocation)
2. Else if `tool_overrides.critique` is set in config.yaml → use it (per-tool)
3. Else → use `default_model` from config (global default)

### Adding `model` Parameter to All LLM-Calling Tools

Every tool that makes an LLM call should accept an optional `model: str | None = None` parameter. This enables per-invocation model override via MCP. The MCP host can pass `model="openai/gpt-4.1"` to any tool call to override the config.

Memory tools and `analyze_dependencies` do NOT need this parameter (no LLM calls).

### Knowledge Context Helper

`server.py` currently has `get_knowledge_context()` which retrieves relevant knowledge by context type. This is used by critique, brainstorm, find_gaps, propose_alternatives, scan_codebase, critique_file.

**Migration strategy:** Move `get_knowledge_context()` into a shared location. Options:
1. Put in `tools/__init__.py` alongside prompt builders (recommended — keeps tools/ self-contained)
2. Put in `memory/retriever.py` (alternative — closer to data source)

Recommendation: Option 1. The function is a tool-level concern (formatting knowledge for tool prompts), not a retriever concern.

### Server.py Registry Pattern (Target State)

After migration, `server.py` should look like:
```python
from mcp.server.fastmcp import FastMCP
from aicouncil.scaffold import ensure_scaffold
from aicouncil.tools.analysis import critique, brainstorm, validate, challenge_assumptions, find_gaps, propose_alternatives
from aicouncil.tools.research import research_assist, research_document
from aicouncil.tools.codebase import scan_codebase, critique_file, analyze_dependencies
from aicouncil.tools.memory import remember, recall, forget, show_knowledge_summary

mcp = FastMCP("aicouncil", instructions="...")

# Register all tools
mcp.tool()(critique)
mcp.tool()(brainstorm)
# ... etc

def main():
    ensure_scaffold()
    mcp.run(transport="stdio")
```

**Important:** The `@mcp.tool()` decorator in FastMCP can be applied at import time (decorating the function in the tool module) OR at registration time. Check how FastMCP handles this — if `@mcp.tool()` requires the `mcp` instance, then either:
- Pass `mcp` to tool modules (creates coupling)
- Use `mcp.tool()(imported_function)` in server.py (preferred — keeps tool modules MCP-agnostic)
- Use a deferred registration pattern

**Recommended approach:** Define tool functions as plain `async def` in tool modules (NO decorator). In `server.py`, register them: `mcp.tool()(critique)`. This keeps tool modules MCP-agnostic and testable without MCP.

### client.py Changes — Deprecate Category System

**Remove:**
- `ModelCategory` type alias (if exists)
- `ModelConfig` class — no longer needed (was backward compat for env-var model routing)
- `get_model_config()` function — replaced by `config.resolve_model()`
- `get_client(category)` function — replaced by direct `OpenRouterClient(model=resolved_model)` instantiation
- `_clients` cache dict — no longer needed if not caching

**Keep:**
- `OpenRouterClient` class — core client, unchanged
- `clear_client_cache()` — only if caching is retained
- All retry logic, error handling, response parsing

**Migration risk:** Any code calling `get_client()` will break. Search for all call sites before removing. Currently only `server.py` tool functions call it (which are being moved), so this is safe.

### Prompt Builder Functions — No Changes Needed

The 8 prompt builder functions in `tools/__init__.py` are pure functions that compose prompt strings. They don't touch the client or config. Tool modules will import and use them as-is:

```python
from aicouncil.tools import build_critique_prompt
```

### Error Handling Pattern for Tool Modules

Every tool function must catch exceptions and return structured Pydantic error responses:

```python
async def critique(content: str, ...) -> CritiqueResult:
    try:
        # ... business logic ...
        result = await client.generate(prompt, response_model=CritiqueResult)
        return result
    except AiCouncilError as e:
        logger.error(f"critique failed: {e}")
        return CritiqueResult(
            verdict="error",
            summary=f"Analysis failed: {e}",
            issues=[],
            strengths=[],
            confidence=0.0,
        )
    except Exception as e:
        logger.error(f"critique unexpected error: {e}")
        return CritiqueResult(
            verdict="error",
            summary=f"Unexpected error: {e}",
            issues=[],
            strengths=[],
            confidence=0.0,
        )
```

**Note:** The architecture says "never catch broad Exception", but tool boundary functions are the ONE place where a catch-all is acceptable — to prevent raw tracebacks from reaching the MCP host. Use specific `AiCouncilError` catches first, with a final `Exception` catch as safety net.

### Project Structure After This Story

```
src/aicouncil/
├── server.py              # REFACTORED: ~100-150 lines, registry only
├── client.py              # MODIFIED: Remove ModelConfig, get_client(), get_model_config()
├── config.py              # UNCHANGED
├── exceptions.py          # UNCHANGED
├── scaffold.py            # UNCHANGED
├── tools/
│   ├── __init__.py        # UNCHANGED: Prompt builders + get_knowledge_context() (moved here)
│   ├── analysis.py        # NEW: critique, brainstorm, validate, challenge, gaps, alternatives
│   ├── research.py        # NEW: research_assist, research_document
│   ├── codebase.py        # NEW: scan_codebase, critique_file, analyze_dependencies
│   └── memory.py          # NEW: remember, recall, forget, show_knowledge_summary
├── schemas/               # UNCHANGED
├── prompts/               # UNCHANGED
├── memory/                # UNCHANGED
├── scanner/               # UNCHANGED
└── defaults/              # UNCHANGED

tests/
├── test_tools/            # NEW
│   ├── __init__.py
│   ├── test_analysis.py   # NEW: Analysis tool tests
│   ├── test_research.py   # NEW: Research tool tests
│   ├── test_codebase.py   # NEW: Codebase tool tests
│   └── test_memory.py     # NEW: Memory tool tests
├── conftest.py            # MAY NEED UPDATES for new fixtures
├── test_client.py         # UPDATE: Remove tests for deprecated get_client/ModelConfig
├── test_config.py         # UNCHANGED
├── test_exceptions.py     # UNCHANGED
├── test_schemas.py        # UNCHANGED
└── test_scaffold.py       # UNCHANGED
```

### Files to Create

| File | Purpose |
|------|---------|
| `src/aicouncil/tools/analysis.py` | 6 analysis tool functions |
| `src/aicouncil/tools/research.py` | 2 research tool functions |
| `src/aicouncil/tools/codebase.py` | 3 codebase tool functions |
| `src/aicouncil/tools/memory.py` | 4 memory tool functions |
| `tests/test_tools/__init__.py` | Test package init |
| `tests/test_tools/test_analysis.py` | Analysis tool tests |
| `tests/test_tools/test_research.py` | Research tool tests |
| `tests/test_tools/test_codebase.py` | Codebase tool tests |
| `tests/test_tools/test_memory.py` | Memory tool tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/aicouncil/server.py` | Strip to thin registry (~100-150 lines) |
| `src/aicouncil/client.py` | Remove ModelConfig, get_client(), get_model_config() |
| `src/aicouncil/tools/__init__.py` | Add get_knowledge_context() helper |
| `tests/test_client.py` | Remove tests for deprecated functions |
| `tests/conftest.py` | Add fixtures for tool testing (mock client, mock knowledge store) |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/aicouncil/config.py` | resolve_model() already works; no changes needed |
| `src/aicouncil/exceptions.py` | Exception hierarchy is complete |
| `src/aicouncil/scaffold.py` | Independent of tool migration |
| `src/aicouncil/schemas/responses.py` | Response models are unchanged |
| `src/aicouncil/prompts/` | Prompt templates are unchanged |
| `src/aicouncil/memory/` | Knowledge subsystem is unchanged (tools import from it) |
| `src/aicouncil/scanner/` | Scanner subsystem is unchanged (tools import from it) |
| `src/aicouncil/defaults/` | Default config is unchanged |

### Previous Story Intelligence (Story 1.2)

**Key learnings from 1.2:**
- Config refactor went smoothly — `resolve_model()` cascade works correctly
- `CapabilityWeight` model uses `extra="allow"` for flexible domain scores
- Config is frozen (immutable) — any attempt to mutate raises ValidationError
- Code review found 3 actionable issues (scaffold resilience, domain score validation, context_window typo)
- Test pattern: Use `conftest.py` fixtures for mock config, `tmp_path` for temp directories
- 74 tests pass (38 new in 1.2 + 36 from 1.1)
- The `MockConfig` pattern in test_client.py is reusable for tool tests

**Patterns established in 1.2:**
- `importlib.resources` for loading package defaults
- `reset_config()` for test cleanup (use in conftest.py `reset_singletons` fixture)
- Pydantic v2 `ConfigDict(frozen=True)` for immutability

### Git Intelligence

Recent commits:
- `f4e8b72` — story 1-2 (Config System & Auto-Scaffold)
- `b7f1489` — story1 (Fork, Rename & OpenRouter Client)
- `bf9fc7e` — feat: fork gemini-mcp, rename to aicouncil, add OpenRouter client

Working tree: clean, branch: develop

### Anti-Patterns to Avoid

- **DO NOT** keep tool logic in `server.py` — move it ALL to tools/ modules
- **DO NOT** use `get_client(category)` — use `config.resolve_model(tool_name)` + `OpenRouterClient(model=...)`
- **DO NOT** hardcode model names in tool functions — always resolve via config
- **DO NOT** pass the `mcp` instance to tool modules — keep them MCP-agnostic
- **DO NOT** modify Pydantic schemas — they are the stable API contract
- **DO NOT** modify prompt builders — they compose correctly as-is
- **DO NOT** modify memory or scanner subsystems — tools import from them
- **DO NOT** return raw dicts or strings from tools — always Pydantic models
- **DO NOT** let exceptions propagate to MCP — catch and return error responses
- **DO NOT** remove the `get_project_root()` helper — codebase tools still need it (move to tools/__init__.py or keep in server.py)

### Testing Strategy

- Mock `OpenRouterClient.generate()` for all LLM-calling tool tests
- Mock `KnowledgeStore`, `KnowledgeLearner`, `KnowledgeRetriever` for memory/learning tests
- Mock scanner modules (`ContextBuilder`, `ProjectDetector`) for codebase tool tests
- Use `conftest.py` fixtures for mock config with known tool_overrides
- Test model resolution: verify the correct model is passed to OpenRouterClient based on config
- Test error paths: simulate OpenRouterError, ModelUnavailableError — verify structured error response
- Verify no regressions: all 74 existing tests must still pass

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — Tool Module Organization, MCP Tool Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md — Architectural Boundaries, server.py as registry]
- [Source: _bmad-output/planning-artifacts/architecture.md — Config Access Patterns, resolve_model cascade]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error Handling Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md — Story 1.3 Acceptance Criteria (FR31-33)]
- [Source: _bmad-output/planning-artifacts/prd.md — FR31 (tools work via OpenRouter), FR32 (identical except model configurable), FR33 (cascading defaults)]
- [Source: _bmad-output/project-context.md — Boundary Violations, Framework-Specific Rules]
- [Source: _bmad-output/implementation-artifacts/1-2-config-system-auto-scaffold.md — resolve_model(), MockConfig pattern, test conventions]
- [Source: src/aicouncil/server.py — Current inline tool implementations (1028 lines)]
- [Source: src/aicouncil/client.py — OpenRouterClient, get_client(), ModelConfig]
- [Source: src/aicouncil/config.py — Config.resolve_model(), get_config() singleton]
- [Source: src/aicouncil/tools/__init__.py — Prompt builder functions]
- [Source: src/aicouncil/schemas/responses.py — All Pydantic response models]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Tests initially failed due to incorrect mock patching locations — tool modules use top-level `from X import Y` (analysis, research, codebase) and deferred imports (memory, scanner in codebase). Fixed by patching at the correct namespace for each pattern.

### Completion Notes List

- **Task 1-4:** Created 4 tool modules (analysis.py, research.py, codebase.py, memory.py) with all 15 tool functions migrated from server.py. Each LLM-calling tool now accepts optional `model` parameter for per-invocation override and uses `config.resolve_model(tool_name)` cascade.
- **Task 5:** Refactored server.py from 1028 lines to 73 lines — pure registry using `mcp.tool()(func)` pattern. Tool modules are MCP-agnostic.
- **Task 6:** Removed `get_client()`, `ModelConfig`, `get_model_config()`, `ModelCategory`, `_clients` cache from client.py and config.py. Tools now directly instantiate `OpenRouterClient(model=resolved_model, config=config)`.
- **Task 7:** Added `get_knowledge_context()` and `get_project_root()` helpers to `tools/__init__.py` (moved from server.py).
- **Task 8:** Created 47 new tests across 4 test files. All 153 tests pass (106 existing + 47 new). Zero regressions.
- **Task 9:** Ruff format + check pass with zero errors.

### Change Log

- 2026-03-20: Story 1.3 implementation complete — all tools migrated to modules, server.py is thin registry, category-based model routing removed.

### File List

**New files:**
- `src/aicouncil/tools/analysis.py` — 6 analysis tool functions
- `src/aicouncil/tools/research.py` — 2 research tool functions + `_format_document_research` helper
- `src/aicouncil/tools/codebase.py` — 3 codebase tool functions
- `src/aicouncil/tools/memory.py` — 4 memory tool functions
- `tests/test_tools/__init__.py` — test package init
- `tests/test_tools/conftest.py` — shared fixtures (mock_config, mock_client)
- `tests/test_tools/test_analysis.py` — 20 tests for analysis tools
- `tests/test_tools/test_research.py` — 8 tests for research tools
- `tests/test_tools/test_codebase.py` — 8 tests for codebase tools
- `tests/test_tools/test_memory.py` — 11 tests for memory tools

**Modified files:**
- `src/aicouncil/server.py` — stripped to 73-line thin registry
- `src/aicouncil/client.py` — removed `get_client()`, `_clients` cache, `ModelCategory` import
- `src/aicouncil/config.py` — removed `ModelConfig`, `get_model_config()`, `reload_model_config()`, `ModelCategory`
- `src/aicouncil/tools/__init__.py` — added `get_knowledge_context()`, `get_project_root()` helpers
- `tests/test_client.py` — removed `TestClientFactory` (tested deprecated `get_client`), removed `clear_client_cache` import
