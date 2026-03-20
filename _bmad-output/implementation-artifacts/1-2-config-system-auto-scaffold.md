# Story 1.2: Config System & Auto-Scaffold

Status: done

## Story

As a developer installing aicouncil for the first time,
I want the server to auto-create its configuration directory and load model config from YAML with cascading defaults,
so that I can start using the tool immediately with zero manual setup and customize model selection later.

## Acceptance Criteria

1. **Given** no `./aicouncil/` directory exists in the project root
   **When** the server starts for the first time
   **Then** it creates `./aicouncil/` with default `config.yaml`, empty `history/`, and empty `agents/` directories
   **And** the default `config.yaml` contains a global default model, model pool array, and sensible capability weights with `context_window` metadata per model

2. **Given** a `./aicouncil/config.yaml` exists with cascading model defaults
   **When** a tool is invoked without a per-invocation model override
   **Then** the config resolves: per-invocation → per-tool override → global default (cascading)
   **And** the Config object is immutable after startup — no runtime mutation

3. **Given** the config system is loaded
   **When** any module needs config access
   **Then** it uses the hybrid singleton pattern (production: `get_config()`, tests: inject mock via constructor)
   **And** `config.py` is the sole reader of YAML config — no other module reads config files directly

4. **Given** the config file is malformed or the API key is missing
   **When** the server starts
   **Then** it raises `ConfigError` with a clear, actionable error message

## Tasks / Subtasks

- [x] Task 1: Create default config template (AC: #1)
  - [x] Create `config/default-config.yaml` with global default model, per-tool overrides section, council model pool array, capability weights (model-centric), and `context_window` per model
  - [x] Include comments explaining each section for first-time users
  - [x] Ship sensible defaults (FR30): 4-6 models with realistic capability scores across domains

- [x] Task 2: Refactor `config.py` — Config and ModelConfig classes (AC: #2, #3, #4)
  - [x] Extend `Config` Pydantic model with new fields: `model_pool`, `capability_weights`, `tool_overrides`
  - [x] Add `context_window` metadata per model in capability weights structure
  - [x] Implement cascading resolution: `resolve_model(tool_name, per_invocation_model)` → per-invocation → per-tool → global default
  - [x] Make Config immutable after load (Pydantic `model_config = ConfigDict(frozen=True)`)
  - [x] Refactor YAML loading to parse ALL config sections (not just basic fields)
  - [x] Raise `ConfigError` for malformed YAML with specific field-level error messages
  - [x] Raise `ConfigError` for missing `OPENROUTER_API_KEY` with clear fix instructions
  - [x] Maintain backward compatibility: `get_config()` singleton + constructor injection for tests
  - [x] Refactor `ModelConfig` / `get_model_config()` to read from YAML instead of env vars
  - [x] Add helper methods: `get_model_pool()`, `get_capability_weights(model)`, `get_context_window(model)`

- [x] Task 3: Create `src/aicouncil/scaffold.py` (AC: #1)
  - [x] Implement `ensure_scaffold(project_root: Path)` function
  - [x] Create `./aicouncil/` directory if missing
  - [x] Create `./aicouncil/history/` subdirectory
  - [x] Create `./aicouncil/agents/` subdirectory
  - [x] Copy `config/default-config.yaml` → `./aicouncil/config.yaml` (only if config.yaml doesn't exist)
  - [x] Log at INFO level: "Auto-scaffolded ./aicouncil/ directory with default config"
  - [x] Log at DEBUG level: specific files/dirs created
  - [x] If directory already exists, do nothing (idempotent)

- [x] Task 4: Integrate scaffold into server startup (AC: #1)
  - [x] Call `ensure_scaffold()` in server startup path (in `server.py` or `config.py` load path)
  - [x] Scaffold must run BEFORE config loading (so config.yaml exists to read)
  - [x] Ensure scaffold uses `importlib.resources` to locate `config/default-config.yaml` from the installed package

- [x] Task 5: Write tests (AC: #1, #2, #3, #4)
  - [x] Create `tests/conftest.py` with shared fixtures (mock config factory, tmp directories)
  - [x] Create `tests/test_config.py`:
    - Test YAML loading with valid config file
    - Test cascading resolution: global → per-tool → per-invocation
    - Test immutability (attempting to mutate raises error)
    - Test missing YAML file raises `ConfigError`
    - Test malformed YAML raises `ConfigError` with field-level message
    - Test missing API key raises `ConfigError`
    - Test capability weights parsing and helper methods
    - Test model pool parsing
    - Test context_window metadata access
    - Test singleton pattern: `get_config()` returns same instance
    - Test DI pattern: constructor injection overrides singleton
  - [x] Create `tests/test_scaffold.py`:
    - Test scaffold creates directory structure on first run
    - Test scaffold copies default config.yaml
    - Test scaffold is idempotent (second run changes nothing)
    - Test scaffold does not overwrite existing config.yaml
    - Test scaffold creates empty history/ and agents/ dirs
  - [x] Run `uv run pytest` — all tests pass (including existing 36 from Story 1.1)

- [x] Task 6: Lint & format (AC: all)
  - [x] Run `uv run ruff format .`
  - [x] Run `uv run ruff check --fix .`
  - [x] Verify zero lint errors

## Dev Notes

### Current State from Story 1.1

The `config.py` module already exists with partial functionality:

- **`Config` class** (Pydantic BaseModel) — has basic fields: `api_key`, `model`, `temperature`, `max_output_tokens`, `default_context`, `preferred_personas`, `timeout_seconds`, `retry_attempts`, `json_response`, `include_reasoning`
- **`ModelConfig` class** — supports category-based routing ("fast", "default", "reasoning") via `get_model()` method
- **YAML loading** — attempts to load from `./aicouncil/config.yaml` but only parses 4 fields: `default_context`, `preferred_personas`, `model`, `temperature`
- **Singleton** — `get_config()` / `reload_config()` implemented with `_config` module-level variable
- **`get_model_config()`** — reads from `OPENROUTER_MODELS` env var (JSON) or falls back to `OPENROUTER_MODEL` env var. Does NOT read from YAML yet.

**What's missing for this story:**
- No capability weights matrix, model pool array, or context_window in Config
- No cascading defaults resolution (global → per-tool → per-invocation)
- Config is NOT immutable (`frozen=True` not set)
- YAML loading doesn't validate structure or parse most fields
- ModelConfig reads env vars, not YAML
- `scaffold.py` does not exist
- `config/default-config.yaml` does not exist

### Files to Create

| File | Purpose |
|------|---------|
| `config/default-config.yaml` | Default config template shipped with package |
| `src/aicouncil/scaffold.py` | Auto-scaffold `./aicouncil/` on first run |
| `tests/conftest.py` | Shared test fixtures |
| `tests/test_config.py` | Config system tests |
| `tests/test_scaffold.py` | Auto-scaffold tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/aicouncil/config.py` | Major refactor — extend Config model, cascading defaults, full YAML parsing, immutability, ConfigError validation |
| `src/aicouncil/server.py` | Call `ensure_scaffold()` before config load in startup path |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/aicouncil/client.py` | Already uses Config via DI correctly; no changes needed |
| `src/aicouncil/exceptions.py` | `ConfigError` already exists; no new exceptions needed |
| `src/aicouncil/tools/__init__.py` | Prompt builders are config-agnostic |
| `src/aicouncil/schemas/` | Response models are config-agnostic |
| `src/aicouncil/memory/` | Knowledge persistence is independent |
| `src/aicouncil/scanner/` | Codebase analysis is independent |

### Default Config YAML Structure

The `config/default-config.yaml` must follow this exact structure (architecture spec):

```yaml
# aicouncil default configuration
# Auto-created on first run. Customize as needed.
# API keys belong in .mcp.json env vars — NOT here.

# Global default model — used when no per-tool or per-invocation override is set
default_model: "anthropic/claude-sonnet-4"

# Per-tool model overrides — override global default for specific tools
# Uncomment and set to override:
tool_overrides:
  # critique: "openai/gpt-4.1"
  # brainstorm: "anthropic/claude-sonnet-4"
  # research_assist: "google/gemini-2.5-pro"

# Council model pool — models available for council agent assignment
# The council assembler picks from this pool using capability-weighted routing
model_pool:
  - "anthropic/claude-sonnet-4"
  - "openai/gpt-4.1"
  - "google/gemini-2.5-pro"
  - "deepseek/deepseek-r1"
  - "meta-llama/llama-4-maverick"

# Capability weights — model-centric format
# Top-level keys = model names, values = domain scores (0.0-1.0) + context_window
# Used by council assembler for capability-weighted random routing (60/40 bias)
capability_weights:
  "anthropic/claude-sonnet-4":
    context_window: 200000
    coding: 0.95
    analysis: 0.90
    creative: 0.85
    business: 0.80
    legal: 0.70
    finance: 0.75
  "openai/gpt-4.1":
    context_window: 1047576
    coding: 0.90
    analysis: 0.90
    creative: 0.85
    business: 0.85
    legal: 0.75
    finance: 0.80
  "google/gemini-2.5-pro":
    context_window: 1048576
    coding: 0.90
    analysis: 0.85
    creative: 0.80
    business: 0.80
    legal: 0.70
    finance: 0.75
  "deepseek/deepseek-r1":
    context_window: 163840
    coding: 0.90
    analysis: 0.90
    creative: 0.70
    business: 0.65
    legal: 0.60
    finance: 0.70
  "meta-llama/llama-4-maverick":
    context_window: 1048576
    coding: 0.80
    analysis: 0.75
    creative: 0.80
    business: 0.70
    legal: 0.60
    finance: 0.65
```

**Key design decisions:**
- `capability_weights` uses model names as top-level keys (model-centric, per architecture). This optimizes for model churn — adding/removing a model is a single-location edit.
- `context_window` is nested inside each model's capability entry (per architecture gap resolution).
- Domain scores are 0.0-1.0 floats used by council assembler for weighted routing.
- The default models and scores above are reasonable starting points; users tune as needed.

### Cascading Default Resolution Logic

```python
def resolve_model(self, tool_name: str | None = None, per_invocation: str | None = None) -> str:
    """Resolve model using cascade: per-invocation → per-tool → global default."""
    if per_invocation:
        return per_invocation
    if tool_name and tool_name in self.tool_overrides:
        return self.tool_overrides[tool_name]
    return self.default_model
```

This is the core of FR27. Every tool call resolves its model through this method.

### Config Immutability Pattern

Use Pydantic v2's frozen config to prevent runtime mutation:

```python
from pydantic import BaseModel, ConfigDict

class Config(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str
    default_model: str
    # ... other fields
```

After `get_config()` returns, attempting `config.default_model = "x"` raises `ValidationError`. This satisfies AC #2's immutability requirement.

### Auto-Scaffold Implementation

`scaffold.py` must:
1. Check if `./aicouncil/` exists
2. If not, create it with subdirectories
3. Copy `config/default-config.yaml` into `./aicouncil/config.yaml`
4. The default config template lives inside the installed package — use `importlib.resources` to locate it

```python
from importlib import resources
from pathlib import Path

def ensure_scaffold(project_root: Path | None = None) -> Path:
    """Create ./aicouncil/ with defaults on first run. Idempotent."""
    root = project_root or Path.cwd()
    aicouncil_dir = root / "aicouncil"

    if aicouncil_dir.exists():
        return aicouncil_dir

    aicouncil_dir.mkdir()
    (aicouncil_dir / "history").mkdir()
    (aicouncil_dir / "agents").mkdir()

    # Copy default config from package resources
    config_dest = aicouncil_dir / "config.yaml"
    default_config = resources.files("aicouncil") / ".." / ".." / "config" / "default-config.yaml"
    # OR bundle default-config.yaml inside src/aicouncil/config/ and use:
    # default_config = resources.files("aicouncil.config") / "default-config.yaml"
    config_dest.write_text(default_config.read_text())

    return aicouncil_dir
```

**Important:** The package data inclusion strategy needs to be decided. Two options:
1. **Package data** — put `default-config.yaml` inside `src/aicouncil/` and declare in pyproject.toml
2. **Top-level `config/`** — keep it at repo root, include via hatchling config

Option 1 is cleaner for distribution: place the default at `src/aicouncil/defaults/default-config.yaml` and use `importlib.resources.files("aicouncil.defaults")`. Add an `__init__.py` to make it a package.

### Startup Integration

The scaffold must run before config loading. In `server.py` or the server's `main()`:

```python
from aicouncil.scaffold import ensure_scaffold

def main():
    ensure_scaffold()  # Creates ./aicouncil/ if missing
    # ... existing server startup
```

### ModelConfig Refactor Strategy

Currently `get_model_config()` reads `OPENROUTER_MODELS` env var (JSON). For Story 1.2, it should:
1. Read `tool_overrides` from YAML config (via `Config` object)
2. Still support the env var as an escape hatch (env var overrides YAML if set)
3. The `get_client(category)` pattern in `server.py` should evolve to use `config.resolve_model(tool_name)` instead of category-based routing

**Migration path:** The existing category system ("fast", "default", "reasoning") maps to tool names. The `get_client()` function should accept a `tool_name` parameter and use `config.resolve_model(tool_name)` to pick the model. For backward compatibility, keep accepting category strings and map them to tool names internally.

### ConfigError Validation Requirements

Raise `ConfigError` with clear messages for:
- Missing `OPENROUTER_API_KEY` env var: `"OPENROUTER_API_KEY not set. Add it to your .mcp.json environment variables."`
- Invalid YAML syntax: `"Failed to parse ./aicouncil/config.yaml: {yaml_error}"`
- Invalid field types: `"config.yaml: 'default_model' must be a string, got {type}"`
- Unknown model in tool_overrides: Log WARNING (not error) — model might be valid on OpenRouter
- Missing capability_weights for a model_pool entry: Log WARNING — non-fatal, just means no weighted routing for that model

### Previous Story Intelligence (Story 1.1)

**Key learnings from 1.1 dev record:**
- Bulk-rename `gemini_mcp` → `aicouncil` across all imports worked cleanly
- `client.py` was a full rewrite; `config.py` was modified minimally (renamed class + env var)
- Code review found 14 issues (P1-P14) including: format string injection guard, ValidationError crash fix, broad Exception catches, silent YAML catch fix
- 36 tests pass: 17 client, 8 exceptions, 11 schemas
- `ruff format` + `ruff check` produce zero errors
- Entry point works: `uv run python -c "from aicouncil.server import main"` succeeds

**Patterns to follow from 1.1:**
- The `MockConfig` class pattern in `tests/test_client.py` (line ~20) — reuse this for config tests
- httpx `MockTransport` pattern for API mocking
- Test naming: `test_{method}_{scenario}` convention

**Files created/modified in 1.1 that this story touches:**
- `src/aicouncil/config.py` — modified (will be significantly refactored)
- `src/aicouncil/server.py` — modified (will add scaffold call)

### Git Intelligence

Recent commits:
- `b7f1489` — story1 (Story 1.1 implementation)
- `bf9fc7e` — feat: fork gemini-mcp, rename to aicouncil, add OpenRouter client

Code patterns from Story 1.1:
- Pydantic v2 BaseModel for all data structures
- `async def` for all tool functions
- Module-level `logger = logging.getLogger(__name__)`
- Type hints using Python 3.11+ union syntax (`X | None`)

### Project Structure Notes

After this story, the relevant directory additions:

```
aicouncil/
├── src/aicouncil/
│   ├── config.py              # REFACTORED: Full YAML parsing, cascading defaults, immutable
│   ├── scaffold.py            # NEW: Auto-scaffold ./aicouncil/ on first run
│   ├── defaults/              # NEW: Package-bundled default files
│   │   ├── __init__.py
│   │   └── default-config.yaml
│   └── server.py              # MODIFIED: Call ensure_scaffold() at startup
├── config/                    # Can be removed if using src/aicouncil/defaults/ instead
│   └── default-config.yaml    # OR keep here if using hatchling include
└── tests/
    ├── conftest.py            # NEW: Shared fixtures
    ├── test_config.py         # NEW: Config system tests
    └── test_scaffold.py       # NEW: Auto-scaffold tests
```

**Decision needed:** Whether to place `default-config.yaml` at `config/` (repo root) or `src/aicouncil/defaults/` (inside package). Recommendation: `src/aicouncil/defaults/` for cleaner `importlib.resources` access.

### Anti-Patterns to Avoid

- **DO NOT** read YAML config outside `config.py` — it is the sole config boundary
- **DO NOT** put API keys in `config.yaml` — they belong in `.mcp.json` env vars only
- **DO NOT** mutate Config after startup — use `frozen=True`
- **DO NOT** write scaffold logic in `server.py` — it belongs in `scaffold.py`
- **DO NOT** silently swallow YAML parse errors — raise `ConfigError`
- **DO NOT** make `config/default-config.yaml` a copy of production config — it should have commented-out overrides and sensible defaults only
- **DO NOT** hardcode model names in Python code — all model references come from config
- **DO NOT** use `os.environ` directly in config — use `Config` object
- **DO NOT** break the existing `get_client(category)` pattern abruptly — provide backward compatibility or migrate all call sites in server.py

### Testing Strategy

- Use `tmp_path` pytest fixture for scaffold tests (creates temp dirs)
- Use `monkeypatch.setenv` for `OPENROUTER_API_KEY` in config tests
- Create `tests/fixtures/config/` with valid and malformed YAML samples
- Test Config immutability by asserting `ValidationError` on attribute assignment
- Test cascading with combinations: global only, global+tool, global+tool+invocation
- Mock `importlib.resources` for scaffold tests to avoid filesystem coupling

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — Data Architecture, Configuration System]
- [Source: _bmad-output/planning-artifacts/architecture.md — Config Access Patterns, Hybrid Singleton + DI]
- [Source: _bmad-output/planning-artifacts/architecture.md — First-Run Auto-Scaffold]
- [Source: _bmad-output/planning-artifacts/architecture.md — Capability Weight Matrix]
- [Source: _bmad-output/planning-artifacts/epics.md — Story 1.2 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR27 (cascading defaults), FR28 (model pool), FR29 (capability weights), FR30 (default weights), FR37 (10-min setup), FR38 (zero config), FR39 (project-local config)]
- [Source: _bmad-output/project-context.md — Config Violations, Development Workflow Rules]
- [Source: _bmad-output/implementation-artifacts/1-1-fork-rename-openrouter-client.md — Previous Story Dev Notes, Completion Notes]
- [Source: src/aicouncil/config.py — Current Config class, ModelConfig, singleton pattern]
- [Source: src/aicouncil/exceptions.py — ConfigError definition]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no debug issues encountered.

### Completion Notes List

- **Task 1:** Created `src/aicouncil/defaults/default-config.yaml` with 5 models, capability weights (model-centric format with context_window), tool_overrides section, model_pool. Comments explain each section.
- **Task 2:** Full refactor of `config.py`. Added `CapabilityWeight` model with `extra="allow"` for domain scores. `Config` now has `frozen=True`, `tool_overrides`, `model_pool`, `capability_weights` fields. `resolve_model()` implements 3-tier cascading. YAML loading validates all sections. `ConfigError` raised for malformed YAML, missing API key, invalid values. `ModelConfig`/`get_model_config()` preserved for backward compat, now derives from YAML config. Added `reset_config()` for test cleanup. `config.model` property alias maintained.
- **Task 3:** Created `scaffold.py` with `ensure_scaffold()`. Uses `importlib.resources` to locate default config from `aicouncil.defaults` package. Idempotent — skips if directory exists. Logs at INFO (scaffolding) and DEBUG (individual files/dirs).
- **Task 4:** Added `ensure_scaffold()` call in `server.py:main()` before `mcp.run()`. Scaffold runs before any config loading.
- **Task 5:** Created `tests/conftest.py` (5 shared fixtures), `tests/test_config.py` (29 tests across 6 test classes), `tests/test_scaffold.py` (9 tests). All 107 tests pass (38 new + 69 existing). Zero regressions.
- **Task 6:** `ruff format` + `ruff check --fix` — zero lint errors. 3 auto-fixed unused imports.
- **Code Review Fixes (post-review):**
  - **P4:** `scaffold.py` — Made scaffold resilient to partial creation. Each component (dir, subdirs, config.yaml) is now checked independently. If config copy failed on a prior run, subsequent runs retry it instead of skipping.
  - **P5:** `config.py` — Added domain score validation in `_parse_capability_weights()`: rejects non-numeric values (skips the model with warning) and warns on scores outside 0.0-1.0 range. `get_domain_score()` also warns on out-of-range values at access time.
  - **P6:** `default-config.yaml`, `conftest.py`, `test_config.py` — Fixed GPT-4.1 `context_window` typo from 1047576 to 1048576 (2^20).

### Change Log

- 2026-03-20: Implemented Story 1.2 — Config System & Auto-Scaffold. All 6 tasks complete. 107 tests pass, zero lint errors.
- 2026-03-20: Code review (3-layer: Blind Hunter, Edge Case Hunter, Acceptance Auditor). 3 actionable findings fixed (P4 scaffold resilience, P5 domain score validation, P6 context_window typo). 74 tests pass, zero lint errors. Status → done.

### File List

**New files:**
- `src/aicouncil/defaults/__init__.py`
- `src/aicouncil/defaults/default-config.yaml`
- `src/aicouncil/scaffold.py`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_scaffold.py`

**Modified files:**
- `src/aicouncil/config.py`
- `src/aicouncil/server.py`
