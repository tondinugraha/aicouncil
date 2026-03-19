---
project_name: 'aicouncil'
user_name: 'Odi'
date: '2026-03-19'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 48
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Runtime:** Python 3.11+ with full type hints
- **Package Manager:** uv (lockfile: uv.lock)
- **Build System:** hatchling via pyproject.toml
- **MCP SDK:** mcp>=1.0.0 — FastMCP decorator pattern, stdio transport
- **HTTP Client:** httpx (async) — sole library for OpenRouter API calls
- **Data Validation:** Pydantic v2 — all tool inputs/outputs are BaseModel subclasses
- **Linting/Formatting:** ruff (line-length: 100, target: py311, checks: E/F/I/N/W/UP)
- **Testing:** pytest>=8.0.0 + pytest-asyncio
- **External API:** OpenRouter only (https://openrouter.ai/api/v1/chat/completions)
- **Distribution:** git-based install via uvx (PyPI deferred)

## Critical Implementation Rules

### Language-Specific Rules (Python)

- **Type hints required everywhere** — Python 3.11+ union syntax (`X | None`) not `Optional[X]`
- **Async-first** — all OpenRouter calls use `async/await` via httpx; council sessions make concurrent calls (6+ models)
- **Pydantic v2 for all data models** — use `BaseModel` subclasses, not dataclasses or TypedDicts, for anything crossing a boundary
- **No raw dicts or strings from MCP tools** — every tool return must be a Pydantic model instance
- **Import style** — ruff enforces isort-compatible import ordering (I checks enabled)
- **String formatting** — use f-strings (UP rules enforce modern Python idioms)
- **Exception hierarchy is mandatory** — never raise bare `Exception` or `RuntimeError`; always use `AiCouncilError` subclasses:
  - `OpenRouterError` → API failures
  - `ModelUnavailableError` → model unreachable after retries (triggers reassign)
  - `ConfigError` → config loading/validation
  - `AgentLoadError` → agent manifest/persona parse failures
  - `CouncilError` → council assembly/deliberation failures
- **Config access** — never read env vars directly with `os.environ`; always go through `Config` object
- **Logging** — module-level `logger = logging.getLogger(__name__)`, correct log levels (DEBUG for payloads, INFO for tool invocations, WARNING for retries, ERROR for post-retry failures)

### Framework-Specific Rules (MCP + FastMCP)

- **Tool registration lives ONLY in `server.py`** — it is a registry, not a container for logic
- **Tool logic lives in `src/aicouncil/tools/`** — one module per tool group (council.py, analysis.py, research.py, codebase.py, memory.py)
- **Every tool uses `@mcp.tool()` decorator** — tool docstrings serve as MCP tool descriptions
- **Tools catch exceptions internally** — return structured Pydantic error responses to MCP; never expose raw tracebacks to the host AI
- **Host AI is the orchestrator** — the MCP server provides tools, data, and config; it does NOT orchestrate council sessions itself
- **stdio transport only** — no HTTP/SSE server; MCP host communicates via stdin/stdout
- **Cascading model defaults** — global → per-tool → per-invocation; resolved by `config.py`, consumed by all tools
- **Council session pattern** — generate UUID at session start, include in all related log entries for traceability
- **Model unavailability** — retry 2-3x, then reassign agent to different model from pool; council continues with substitution noted in output

### Testing Rules

- **Test location:** separate `tests/` directory at project root — never co-locate tests with source
- **File naming:** `test_*.py` following pytest conventions (e.g., `test_client.py`, `test_council.py`)
- **Async tests:** use `pytest-asyncio` for all async tool/client tests
- **Config mocking:** inject mock `Config` via constructor parameter — NEVER monkeypatch the singleton
  ```python
  # CORRECT
  client = OpenRouterClient(config=mock_config)
  # WRONG
  monkeypatch.setattr("aicouncil.config._instance", mock_config)
  ```
- **Test fixtures:** stored in `tests/fixtures/` organized by type (agents/, config/, responses/)
- **API mocking:** mock httpx responses in `test_client.py` — never make real OpenRouter calls in tests
- **Agent test data:** use fixture agent files in `tests/fixtures/agents/`, not the real built-in agents
- **No broad assertions** — assert on specific Pydantic model fields, not just "response is not None"

### Code Quality & Style Rules

- **Naming is locked — no exceptions:**
  - Functions/variables/modules: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - YAML keys: `snake_case`
  - CSV headers: `snake_case`
  - No camelCase anywhere in code or data files
- **Line length:** 100 characters max (ruff enforced)
- **Format before commit:** `uv run ruff format .` then `uv run ruff check .`
- **All naming conventions enforced by ruff** — N checks are enabled, violations will fail lint
- **File organization by boundary:**
  - Tool logic → `src/aicouncil/tools/`
  - Council logic → `src/aicouncil/council/`
  - Schemas → `src/aicouncil/schemas/` and `src/aicouncil/council/schemas.py`
  - Prompts → `src/aicouncil/prompts/`
- **Agent persona files must follow exact template** — YAML frontmatter (name, role, type, tier, domains, include_flag) + Markdown body (Identity, Communication Style, Principles, Domain Expertise)

### Development Workflow Rules

- **Commands:**
  - `uv sync` — install dependencies
  - `uv run aicouncil` — start MCP server locally
  - `uv run pytest` — run all tests
  - `uv run ruff format .` — format code
  - `uv run ruff check --fix .` — lint + auto-fix
- **Auto-scaffold on first run** — server creates `./aicouncil/` with default `config.yaml`, empty `history/` and `agents/` dirs when missing
- **API key management** — stored in `.mcp.json` as env var; NEVER in config.yaml or version-controlled files
- **Config file** — `./aicouncil/config.yaml` for model config, cascading defaults, model pool, capability weights; API keys stay out
- **Agent extension** — create user agents in `./aicouncil/agents/`; same-name files override built-ins at runtime; never modify built-in agents in `src/aicouncil/agents/`
- **Council history output** — timestamped markdown addendums in `./aicouncil/history/` (format: `YYYY-MM-DD-topic-slug.md`)
- **Distribution** — git-based install (`uvx --from git+...`) for now; PyPI deferred

### Critical Don't-Miss Rules

**Boundary Violations (most common AI agent mistake):**
- Do NOT put tool logic in `server.py` — it is a registry only
- Do NOT make HTTP calls outside `client.py` — it is the sole OpenRouter boundary
- Do NOT read config files outside `config.py` — it is the sole config boundary
- Do NOT read agent files outside `agent_loader.py` — it is the sole agent data boundary
- Do NOT write files outside `council/history.py` (for history) or `memory/store.py` (for knowledge)

**Data Format Violations:**
- Do NOT return raw dicts or strings from MCP tools — always Pydantic BaseModel
- Do NOT create agent files without YAML frontmatter — loader will reject them
- Do NOT use camelCase in YAML or CSV — everything is snake_case

**Error Handling Violations:**
- Do NOT catch broad `Exception` — use specific `AiCouncilError` subclasses
- Do NOT expose raw tracebacks to host AI — translate to structured error responses
- Do NOT skip retry logic for model failures — always retry 2-3x before reassigning

**Config Violations:**
- Do NOT read env vars with `os.environ` — use Config object
- Do NOT mutate config after startup — Config is immutable once loaded
- Do NOT put API keys in config.yaml — they belong in `.mcp.json` env vars only

**Architecture Violations:**
- Do NOT let the MCP server orchestrate councils — host AI is the chairperson
- Do NOT log DEBUG content at INFO level — follow the log level conventions strictly
- Do NOT skip session UUID — all council-related log entries must include it

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**

- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-03-19
