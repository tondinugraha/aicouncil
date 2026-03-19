---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments: ['prd.md', 'product-brief-aicouncil-2026-03-19.md', 'brainstorming-session-2026-03-18-1625.md']
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-03-19'
project_name: 'aicouncil'
user_name: 'Odi'
date: '2026-03-19'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
39 requirements across 6 categories:
- **Council Deliberation (FR1-17):** The core loop — topic classification, council assembly, capability-weighted model routing, orchestrator-as-chairperson deliberation, adaptive context management, consensus mechanisms, and dual-output addendum generation. These define the interaction contract between MCP server and host AI.
- **Agent System (FR18-25):** 35-42 hand-crafted agents in Markdown + CSV manifest, three-category architecture (expert/builder/user) with tiered demand classification, user-extensible via template and local directory override.
- **Model Routing & Configuration (FR26-30):** OpenRouter as unified gateway, cascading model defaults (global → per-tool → per-invocation), capability-weight matrix in editable YAML, council-specific model pool.
- **Extended Tools (FR31-33):** Existing gemini-mcp utility tools converted to model-agnostic operation, respecting cascading defaults.
- **Council History & Output (FR34-36):** File-based timestamped markdown addendums in dedicated directory, narrative format readable by non-technical stakeholders.
- **Installation & Configuration (FR37-39):** Sub-10-minute onboarding, single API key requirement, project-local portable configuration.

**Non-Functional Requirements:**
- **Performance:** No server-added latency beyond request marshaling; single-call council assembly; adaptive context management at 50% window threshold.
- **Security:** API key stays local in `.mcp.json`; no telemetry, no analytics, no external data transmission beyond OpenRouter inference calls; fully local operation.
- **Reliability:** Graceful model unavailability handling with reassignment; atomic file writes for addendums; startup configuration validation with clear error messages.
- **Extensibility:** Documented agent template; data-driven capability weights (YAML); modular MCP tool registration.
- **Compatibility:** Any MCP-enabled host (Claude Code, Cursor, Windsurf); any OpenRouter model; cross-platform Python 3.11+ (macOS, Linux, Windows).

**Scale & Complexity:**

- Primary domain: MCP Server / Developer Tool (Python 3.11+)
- Complexity level: Medium
- Estimated architectural components: ~8 (MCP server core, tool registry, agent system, configuration loader, model router/OpenRouter client, file I/O manager, prompt builder, knowledge store)

### Technical Constraints & Dependencies

- **Runtime:** Python 3.11+ — consistent with existing gemini-mcp codebase and MCP Python SDK
- **Protocol:** MCP Python SDK (`mcp>=1.0.0`) with FastMCP decorator pattern for tool registration
- **External API:** OpenRouter only — single API key, unified model gateway (replacing google-genai)
- **Persistence:** File-system only — no database, no external storage
- **Distribution:** PyPI package via `uv` / `uvx`
- **Build System:** hatchling via pyproject.toml
- **Package Manager:** uv (with uv.lock)
- **Intelligence boundary:** Host AI provides orchestration intelligence; MCP server provides tools, data, and configuration. The server is stateless infrastructure.
- **Source codebase:** Fork and evolve existing `gemini-mcp` server (source: `/Users/tondinugraha/mcp-servers/gemini-mcp`) — 15 working tools, clean architecture, battle-tested

### Cross-Cutting Concerns Identified

- **Configuration cascading** — Global/per-tool/per-invocation model defaults must be resolved consistently across all tools including the council tool
- **OpenRouter integration** — Every tool that calls a model routes through OpenRouter; error handling, rate limiting, and model availability affect all tools
- **Agent data access** — Council tool and potentially future tools need to read agent manifests and persona files; consistent loading and validation pattern needed
- **File I/O patterns** — Agent reading, config loading, addendum writing, and history management all require file operations with proper error handling
- **Model metadata** — Context window sizes and capability weights must be accessible to the host AI for orchestration decisions (context management, routing)
- **Error communication** — Model unavailability, config errors, and file I/O failures must surface clearly through MCP to the host AI

## Starter Template Evaluation

### Primary Technology Domain

Python MCP Server — forking and evolving the existing `gemini-mcp` codebase rather than starting from scratch.

### Starter Options Considered

**Option 1: Fork gemini-mcp (SELECTED)**
The existing battle-tested Python MCP server with 15 working tools, clean architecture, and established patterns. Already solves MCP protocol compliance, multi-model routing, structured responses, and project-local configuration.

**Option 2: MCP Python SDK create-server template**
The official MCP SDK provides a minimal server scaffold. Would require rebuilding all the infrastructure gemini-mcp already provides (client abstraction, config management, prompt building, knowledge store, codebase scanning).

**Option 3: TypeScript/Node.js MCP server (PRD assumption — CORRECTED)**
The PRD assumed TypeScript, but the existing codebase is Python. Switching languages would discard a working, tested foundation for no architectural benefit. The Python MCP SDK is mature and well-supported.

### Selected Starter: Fork of gemini-mcp

**Rationale for Selection:**
- Battle-tested with 15 working tools and clean architecture
- FastMCP decorator pattern makes adding new tools trivial
- Multi-model routing already exists (fast/default/reasoning categories) — needs extension to OpenRouter model pools, not a rewrite
- Pydantic schemas provide type safety for all tool responses
- Knowledge persistence system (JSONL) is reusable
- Codebase scanner module provides MCP-native project context awareness
- Prompt builder pattern (base templates + workflow-specific guidance) maps directly to agent persona loading
- `uv` package manager is modern and fast
- `ruff` handles both linting and formatting
- `pytest` + `pytest-asyncio` for async MCP tool testing

**Initialization:**

```bash
# Fork the existing repo
cp -r /Users/tondinugraha/mcp-servers/gemini-mcp /Users/tondinugraha/Dev/aicouncil
# Rename package, update pyproject.toml, swap client layer
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python 3.11+ with full type hints and Pydantic data validation

**Build System:**
hatchling via pyproject.toml, uv for dependency management and lockfile

**Testing Framework:**
pytest >= 8.0.0 with pytest-asyncio for async tool tests

**Linting & Formatting:**
ruff (line-length: 100, target: py311, checks: E/F/I/N/W/UP)

**Code Organization (inherited + new):**
```
src/aicouncil/
├── server.py          # MCP tool registration (FastMCP)
├── client.py          # API client (Gemini → OpenRouter)
├── config.py          # Configuration management
├── tools/             # Tool prompt builders
├── prompts/           # Prompt template library
├── schemas/           # Pydantic response models
├── memory/            # Knowledge persistence (JSONL)
├── scanner/           # Codebase analysis
├── agents/            # NEW: Agent system (manifest + personas)
└── council/           # NEW: Council orchestration data/tools
```

**Development Experience:**
- `uv sync` for dependency installation
- `uv run aicouncil` for local server startup
- `uv run pytest` for testing
- `uv run ruff format .` and `uv run ruff check .` for code quality
- stdio transport for MCP host communication

**Key Evolution Points (gemini-mcp → aicouncil):**
1. Replace `google-genai` client with OpenRouter API client
2. Extend config system for cascading model defaults and council model pool
3. Add agent system (CSV manifest + Markdown persona loader)
4. Add `ai_council` tool with council assembly and orchestration data
5. Add capability-weight matrix (YAML) for model routing
6. Add council history file output
7. Rename package from `gemini-mcp` to `aicouncil`

**Note:** The PRD's TypeScript/Node.js assumption has been corrected — the project is Python-based, inheriting from the existing gemini-mcp foundation.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- OpenRouter client via httpx async — foundation for all model communication
- Config file structure (aicouncil/config.yaml) — everything depends on config loading
- Agent dual-directory overlay system — council assembly depends on agent loading

**Important Decisions (Shape Architecture):**
- Capability weight matrix format (model-centric, inside config.yaml)
- Error handling strategy (retry then reassign)
- Auto-scaffold on first run

**Deferred Decisions (Post-MVP):**
- PyPI publishing workflow (git-based install for now)
- Council history indexing/search
- Dynamic model discovery from OpenRouter

### Data Architecture

**Project Footprint — `./aicouncil/` Directory:**
- Decision: Single dedicated directory in user's project root
- Structure:
  ```
  ./aicouncil/
  ├── config.yaml    # Model config, cascading defaults, model pool, capability weights
  ├── history/       # Timestamped council addendum .md files
  └── agents/        # User-created/override agent personas + manifest
  ```
- Rationale: Clean single footprint, all aicouncil-specific files in one place, version-controllable
- Affects: All components that read/write project-local files

**Configuration System:**
- Decision: Dedicated YAML config file (`./aicouncil/config.yaml`) for model configuration; API keys in `.mcp.json` env vars
- Config contains: global default model, per-tool model overrides, council model pool array, capability-weight matrix (model-centric format)
- Rationale: YAML is expressive enough for nested model config (pools, weights, cascading defaults). API keys stay in MCP host config where they belong — never in version-controlled files.
- Affects: Config loader, all tools, council assembly, model routing

**Capability Weight Matrix:**
- Decision: Model-centric format embedded in config.yaml (not a separate file)
- Format: Top-level keys are model names, values are capability scores per domain
- Rationale: Model churn (adding/removing models as OpenRouter landscape shifts) is the dominant maintenance operation — model-centric structure makes this a single-location edit
- Affects: Council model routing, capability-weighted random selection

**Agent System — Dual Directory with Overlay:**
- Decision: Built-in agents ship inside the package (read-only); user agents live in `./aicouncil/agents/`. User agents with the same name override built-ins. Orchestrator merges both at runtime.
- Built-in: `src/aicouncil/agents/` (packaged, updated with releases)
- User-local: `./aicouncil/agents/` (project-specific, user-editable)
- Format: CSV manifest (`agent-manifest.csv`) + individual Markdown persona files
- Rationale: Clean extension/override without blocking package updates. Users never need to touch built-in files.
- Affects: Agent loader, council assembly, custom agent support

**Council History:**
- Decision: Timestamped markdown files in `./aicouncil/history/`
- Format: `YYYY-MM-DD-topic-slug.md` narrative addendums
- Rationale: File-based, human-readable, version-controllable, referenceable by team members
- Affects: Council tool output, file I/O manager

### Authentication & Security

- Decision: No auth system — fully local tool
- API key stored in `.mcp.json` as environment variable, never logged or transmitted beyond OpenRouter API calls
- No telemetry, no analytics, no backend service
- Rationale: MCP server is local infrastructure, not a service

### API & Communication Patterns

**OpenRouter Client:**
- Decision: `httpx` async client (not OpenAI SDK, not raw `requests`)
- Rationale: Async-native for concurrent council API calls (6+ models per session); lightweight single dependency; clean error hierarchy and custom retry transport; no misleading transitive dependencies (unlike OpenAI SDK approach)
- Affects: All model API calls, council deliberation concurrency

**Error Handling — Model Unavailability:**
- Decision: Retry then reassign
- Pattern: Retry failed model 2-3 times → on failure, reassign agent to different available model from pool → council continues with substitution noted in output
- Rationale: Preserves council composition and quality; matches PRD requirement for graceful model unavailability handling
- Affects: OpenRouter client, council orchestration, addendum output

**MCP Tool Interface:**
- Decision: FastMCP decorator pattern (inherited from gemini-mcp)
- All tools registered via `@mcp.tool()` with Pydantic input/output schemas
- stdio transport for host AI communication
- Rationale: Proven pattern, trivial to add new tools

### Frontend Architecture

Not applicable — MCP server with no UI.

### Infrastructure & Deployment

**Package Distribution:**
- Decision: Git-based install for now (`uvx --from git+...`)
- Deferred: PyPI publishing for later (improves discoverability but not critical for initial launch)
- Rationale: Ship first, polish distribution later

**First-Run Auto-Scaffold:**
- Decision: Auto-create `./aicouncil/` directory with default `config.yaml` and empty `history/` and `agents/` subdirectories on first run when directory is missing
- Rationale: Zero-config first experience aligns with PRD's "under 10 minutes to first council" and "zero additional configuration needed"
- Affects: Server startup, config loader

**Environment Configuration:**
- Decision: API key via `.mcp.json` env vars; model config via `./aicouncil/config.yaml`; package ships with sensible defaults for all config values
- Rationale: Separation of secrets (env vars) from tunable config (YAML)

### Decision Impact Analysis

**Implementation Sequence:**
1. Fork gemini-mcp, rename package to aicouncil
2. Swap google-genai client for httpx async OpenRouter client
3. Implement config loader (YAML parsing, cascading defaults)
4. Implement auto-scaffold for `./aicouncil/` directory
5. Implement agent loader (dual directory overlay, CSV + Markdown parsing)
6. Add `ai_council` tool with council assembly data
7. Add council history file output
8. Author agent roster (35-42 Markdown personas + manifest)

**Cross-Component Dependencies:**
- OpenRouter client ← config loader (needs model defaults and API routing info)
- Council tool ← agent loader + config loader + OpenRouter client (needs all three)
- All tools ← config loader (cascading model defaults)
- Auto-scaffold ← config loader (must run before config is read)

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
8 areas where AI agents could make different choices, all resolved below.

### Naming Patterns

**Code Naming Conventions (locked — inherited from gemini-mcp):**
- Functions/variables/modules: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Enforced by ruff (checks: E/F/I/N/W/UP)
- Example: `def load_agent_manifest()`, `class OpenRouterClient`, `DEFAULT_MODEL_POOL`

**Config/YAML Naming:**
- YAML keys: `snake_case` (e.g., `default_model`, `model_pool`, `capability_weights`)
- Agent manifest CSV headers: `snake_case`
- Consistent with Python naming — no camelCase in data files

### Structure Patterns

**Test Organization (locked — inherited from gemini-mcp):**
- Separate `tests/` directory at project root
- Files named `test_*.py` following pytest conventions
- Example: `tests/test_client.py`, `tests/test_council.py`, `tests/test_agent_loader.py`
- Async tests use `pytest-asyncio`

**Tool Module Organization:**
- Each tool or tool group in its own module under `src/aicouncil/tools/`
- `server.py` acts as registry — imports and registers tools, no business logic
- Example:
  ```
  src/aicouncil/tools/
  ├── __init__.py
  ├── council.py        # ai_council tool
  ├── analysis.py       # critique, brainstorm, validate, etc.
  ├── codebase.py       # scan, critique_file, dependencies
  └── memory.py         # remember, recall, forget
  ```
- Each module exports tool functions decorated with `@mcp.tool()`

### MCP Tool Patterns

**Tool Registration:**
- All tools use `@mcp.tool()` decorator from FastMCP
- Input parameters use Python type hints
- Output uses Pydantic `BaseModel` subclasses
- Tool docstrings serve as MCP tool descriptions

**Tool Return Pattern:**
- All tools return Pydantic schema instances (never raw dicts or strings)
- Council tool returns both inline content and writes file, returns schema with file path + summary
- Error states returned as structured error responses, not exceptions thrown to MCP

### Error Handling Patterns

**Custom Exception Hierarchy:**
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

- Tools catch exceptions and translate to MCP-friendly Pydantic error responses
- `ModelUnavailableError` triggers retry-then-reassign logic in council sessions
- `ConfigError` surfaces at startup with clear fix instructions
- Never expose raw tracebacks to host AI — always structured error messages

### Config Access Patterns

**Hybrid Singleton + Dependency Injection:**
- One `Config` singleton loaded at startup, importable by any module
- Classes accept config as optional constructor parameter, defaulting to singleton
- Example:
  ```python
  class OpenRouterClient:
      def __init__(self, config: Config | None = None):
          self._config = config or get_config()
  ```
- Tests inject mock config; production code uses default singleton
- Config is immutable after startup — no runtime mutation

### Agent Persona File Format

**Standard Markdown Template:**
```markdown
---
name: "Agent Name"
role: "Agent Role Title"
type: "expert|builder|user"
tier: 1|2|3
domains: ["domain1", "domain2"]
include_flag: true|false
---

## Identity
[Agent background and expertise description]

## Communication Style
[How this agent speaks and interacts]

## Principles
- [Guiding principle 1]
- [Guiding principle 2]

## Domain Expertise
- [Specific expertise area 1]
- [Specific expertise area 2]
```

- YAML frontmatter: machine-parseable fields for council assembly (loader + CSV manifest)
- Markdown body: persona prompt context passed to the model
- All 35-42 agents follow this exact structure — no deviations
- User-created agents in `./aicouncil/agents/` must follow the same format

### Logging Conventions

**Log Levels:**
- **DEBUG:** Full API request/response payloads, agent selection details, config resolution steps
- **INFO:** Tool invocations, council session start/end, model assignments, agent count
- **WARNING:** Model retry attempts, config fallbacks to defaults, missing optional files
- **ERROR:** Model failures (after retries exhausted), config validation failures, agent file parse errors

**Council Session Correlation:**
- Each council session generates a UUID at start
- All log entries for that session include the session ID
- Enables tracing all API calls, agent interactions, and errors for a single council run

**Logger Pattern:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s` (inherited from gemini-mcp)

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow `snake_case` for all Python code and YAML/CSV data files
- Place new tools in `src/aicouncil/tools/` as separate modules, registered via `server.py`
- Return Pydantic schemas from all MCP tools — never raw dicts or strings
- Use the custom exception hierarchy — never raise bare `Exception` or `RuntimeError`
- Accept optional `Config` parameter for testability, default to singleton
- Follow the agent persona Markdown template exactly for new agents
- Include session ID in all council-related log entries

**Anti-Patterns:**
- Putting tool logic directly in `server.py` (belongs in `tools/` modules)
- Returning raw dicts from MCP tools (use Pydantic schemas)
- Reading config via direct env var access (use Config object)
- Catching broad `Exception` where specific `AiCouncilError` subclasses apply
- Creating agent files without YAML frontmatter
- Logging without appropriate level (e.g., DEBUG content at INFO level)

## Project Structure & Boundaries

### Complete Project Directory Structure

```
aicouncil/
├── README.md
├── LICENSE
├── pyproject.toml                    # Package metadata, deps, ruff config, entry point
├── uv.lock                           # Dependency lockfile
├── .env.example                      # Template showing required env vars
├── .gitignore
│
├── src/aicouncil/
│   ├── __init__.py
│   ├── server.py                     # FastMCP server setup, tool registry (imports from tools/)
│   ├── client.py                     # OpenRouter httpx async client (retry, model routing)
│   ├── config.py                     # Config singleton, YAML loader, cascading defaults
│   ├── exceptions.py                 # Custom exception hierarchy
│   ├── scaffold.py                   # Auto-scaffold ./aicouncil/ on first run
│   │
│   ├── tools/                        # MCP tool modules
│   │   ├── __init__.py
│   │   ├── council.py                # ai_council tool (assembly data, session management)
│   │   ├── analysis.py               # critique, brainstorm, validate, challenge, gaps, alternatives
│   │   ├── research.py               # research_assist, research_document
│   │   ├── codebase.py               # scan_codebase, critique_file, analyze_dependencies
│   │   └── memory.py                 # remember, recall, forget, show_knowledge_summary
│   │
│   ├── council/                      # Council-specific logic
│   │   ├── __init__.py
│   │   ├── assembler.py              # Agent selection, model assignment, council composition
│   │   ├── history.py                # Addendum file writing, timestamped output
│   │   └── schemas.py                # Council-specific Pydantic models
│   │
│   ├── agents/                       # Built-in agent roster (read-only, ships with package)
│   │   ├── agent-manifest.csv        # CSV index of all built-in agents
│   │   ├── software-architect.md     # Individual persona files...
│   │   ├── backend-developer.md
│   │   ├── tax-advisor.md
│   │   └── ...                       # 35-42 total agent personas
│   │
│   ├── agent_loader.py               # Dual-directory overlay, CSV + Markdown parsing
│   │
│   ├── prompts/                      # Prompt template library (inherited from gemini-mcp)
│   │   ├── __init__.py
│   │   ├── base.py                   # Base prompt templates, system persona
│   │   └── workflows.py              # Context-specific prompt guidance
│   │
│   ├── schemas/                      # Pydantic response models
│   │   ├── __init__.py
│   │   └── responses.py              # All MCP tool response schemas
│   │
│   ├── memory/                       # Knowledge persistence (inherited from gemini-mcp)
│   │   ├── __init__.py
│   │   ├── store.py                  # JSONL-based knowledge storage
│   │   ├── learner.py                # Knowledge capture from tool outputs
│   │   ├── retriever.py              # Knowledge search & prompt formatting
│   │   └── schemas.py                # KnowledgeEntry models
│   │
│   └── scanner/                      # Codebase analysis (inherited from gemini-mcp)
│       ├── __init__.py
│       ├── project_detector.py       # Project type & root detection
│       ├── file_walker.py            # File traversal & cataloging
│       ├── code_analyzer.py          # Import/structure parsing
│       └── context_builder.py        # Project context assembly
│
├── config/                           # Default config templates (shipped with package)
│   └── default-config.yaml           # Default config.yaml copied during auto-scaffold
│
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Shared fixtures, mock config factory
    ├── test_client.py                # OpenRouter client tests (httpx mocking)
    ├── test_config.py                # Config loading, cascading, validation
    ├── test_agent_loader.py          # Dual-directory overlay, parsing
    ├── test_council.py               # Council assembly, model assignment
    ├── test_scaffold.py              # Auto-scaffold behavior
    ├── test_tools/                   # Tool-specific tests
    │   ├── test_council_tool.py
    │   ├── test_analysis.py
    │   └── test_memory.py
    └── fixtures/                     # Test data
        ├── agents/                   # Mock agent files for testing
        ├── config/                   # Mock config files for testing
        └── responses/                # Mock API responses
```

**User's project-local directory (auto-scaffolded):**
```
./aicouncil/                          # Created on first run in user's project
├── config.yaml                       # Model config, defaults, pool, capability weights
├── history/                          # Council addendum files
│   └── 2026-03-19-stripe-architecture.md  # (example)
└── agents/                           # User-created/override agents
    ├── agent-manifest.csv            # (optional — user's custom manifest)
    └── restaurant-expert.md          # (example custom agent)
```

### Architectural Boundaries

**MCP Protocol Boundary:**
- `server.py` is the sole MCP interface — all tool registration happens here
- Tools in `tools/` modules are imported and registered by `server.py`
- No tool module directly touches MCP transport — `server.py` owns that relationship
- Host AI communicates exclusively through MCP tool calls and responses

**OpenRouter API Boundary:**
- `client.py` is the sole external API interface — all OpenRouter calls go through it
- No other module makes HTTP requests directly
- Retry logic, error translation, and response parsing are encapsulated here
- Returns Pydantic models, never raw HTTP responses

**Config Boundary:**
- `config.py` is the sole config interface — reads YAML, resolves cascading defaults
- Other modules access config via singleton or injected `Config` instance
- `scaffold.py` creates default config on first run — only module that writes config

**Agent Data Boundary:**
- `agent_loader.py` is the sole agent data interface — reads CSV + Markdown, merges directories
- Returns structured agent data (Pydantic models), never raw file contents
- Council assembler consumes agent data through this interface only

**File Output Boundary:**
- `council/history.py` owns all council history file writing
- `memory/store.py` owns all knowledge persistence file I/O
- No other module writes to user's project directory

### Requirements to Structure Mapping

**FR Category → Location:**

| FR Category | Primary Location | Supporting Modules |
|-------------|-----------------|-------------------|
| **Council Deliberation (FR1-17)** | `tools/council.py` + `council/` | `client.py`, `agent_loader.py`, `config.py` |
| **Agent System (FR18-25)** | `agents/` + `agent_loader.py` | `council/assembler.py` |
| **Model Routing & Config (FR26-30)** | `config.py` + `client.py` | `council/assembler.py` |
| **Extended Tools (FR31-33)** | `tools/analysis.py`, `tools/research.py`, `tools/codebase.py` | `client.py`, `config.py` |
| **Council History (FR34-36)** | `council/history.py` | `tools/council.py` |
| **Installation & Config (FR37-39)** | `scaffold.py` + `config/default-config.yaml` | `config.py` |

**Cross-Cutting Concerns → Location:**

| Concern | Location |
|---------|----------|
| Configuration cascading | `config.py` |
| OpenRouter communication | `client.py` |
| Error handling | `exceptions.py` (definitions), each module (handling) |
| Logging with session ID | `council/` modules (generation), all modules (usage) |
| Pydantic schemas | `schemas/responses.py` + `council/schemas.py` |

### Integration Points

**Internal Communication:**
- `server.py` → `tools/*` — Tool registration and invocation
- `tools/council.py` → `council/assembler.py` — Council composition
- `council/assembler.py` → `agent_loader.py` — Agent data retrieval
- `council/assembler.py` → `config.py` — Model pool and capability weights
- `tools/*` → `client.py` — All model API calls
- `tools/*` → `config.py` — Model selection via cascading defaults
- `council/` → `council/history.py` — Addendum file output

**External Integrations:**
- `client.py` → OpenRouter API (`https://openrouter.ai/api/v1/chat/completions`)
- `scaffold.py` → User's file system (`./aicouncil/` directory)
- `council/history.py` → User's file system (`./aicouncil/history/`)
- `memory/store.py` → User's file system (knowledge store)

**Data Flow (Council Session):**
```
User prompt (via MCP host)
  → server.py (tool dispatch)
    → tools/council.py (session init, UUID generation)
      → config.py (load model pool, capability weights)
      → agent_loader.py (load + merge agent rosters)
      → council/assembler.py (select agents, assign models)
      → client.py (concurrent httpx calls to OpenRouter per agent)
      → council/history.py (write addendum to ./aicouncil/history/)
    ← Pydantic response (inline summary + file path)
  ← MCP response to host AI
```

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are compatible and conflict-free:
- Python 3.11+ / uv / hatchling / ruff / pytest — proven stack inherited from gemini-mcp
- httpx async + FastMCP + Pydantic — async-compatible Python libraries with no version conflicts
- YAML config + env var API keys — clean separation with no overlap
- Dual-directory agent overlay — compatible with package distribution via git install

**Pattern Consistency:**
- snake_case naming applied uniformly across code, YAML, and CSV
- All MCP tools return Pydantic schemas — consistent boundary contract
- Custom exception hierarchy aligns with retry-then-reassign error handling flow
- Hybrid config access (singleton + injection) applied consistently across all modules
- Tool module organization (`tools/`) aligns with `server.py` registry pattern

**Structure Alignment:**
- Every architectural boundary has a single owning module — no overlapping responsibilities
- Data flow is unidirectional: config → loader → assembler → client → history
- All external I/O (OpenRouter API, file system) is encapsulated behind clear boundary modules

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**

| FR Range | Status | Architecture Support |
|----------|--------|---------------------|
| FR1-17 (Council Deliberation) | ✅ Covered | `tools/council.py` + `council/assembler.py` + `client.py` + `council/history.py`. Orchestration intelligence in host AI; server provides assembly data, concurrent model calls, and history output |
| FR18-25 (Agent System) | ✅ Covered | `agents/` (built-in) + `./aicouncil/agents/` (user) + `agent_loader.py` (dual-directory overlay) + standardized Markdown persona template |
| FR26-30 (Model Routing & Config) | ✅ Covered | `config.py` (YAML loader, cascading defaults, capability weights) + `client.py` (OpenRouter routing) |
| FR31-33 (Extended Tools) | ✅ Covered | `tools/analysis.py`, `tools/research.py`, `tools/codebase.py` — all inherit cascading model defaults from config |
| FR34-36 (Council History) | ✅ Covered | `council/history.py` → `./aicouncil/history/YYYY-MM-DD-topic-slug.md` |
| FR37-39 (Installation & Config) | ✅ Covered | `scaffold.py` auto-creates `./aicouncil/` on first run; git-based install; single API key in `.mcp.json` |

**Non-Functional Requirements Coverage:**

| NFR | Status | Architecture Support |
|-----|--------|---------------------|
| Performance | ✅ Covered | httpx async for concurrent council API calls; no server-added latency beyond request marshaling |
| Security | ✅ Covered | API key in `.mcp.json` env vars only; no telemetry/analytics; fully local operation |
| Reliability | ✅ Covered | Retry-then-reassign for model unavailability; custom exception hierarchy; config validation at startup with clear errors |
| Extensibility | ✅ Covered | Agent Markdown template; dual-directory overlay; YAML capability weights; modular `@mcp.tool()` registration |
| Compatibility | ✅ Covered | MCP protocol via FastMCP (any MCP host); OpenRouter API (any model); Python 3.11+ (macOS/Linux/Windows) |

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with specific technology choices
- Implementation patterns comprehensive with concrete examples and anti-patterns
- Consistency rules clear and enforceable via ruff + code review
- Exception hierarchy, config access, and tool registration patterns all specified with code examples

**Structure Completeness:**
- Complete directory tree defined down to individual files
- All modules have clear purposes documented
- Test structure mirrors source structure with fixtures directory
- User-facing `./aicouncil/` directory fully specified

**Pattern Completeness:**
- All 8 conflict points identified and resolved
- Naming, structure, tool, error, config, agent, and logging patterns all documented
- Enforcement guidelines with explicit MUST rules and anti-patterns

### Gap Analysis Results

**Gaps Found and Resolved:**

1. **Model context window metadata (FR11)** — RESOLVED
   - Gap: Adaptive context management at 50% window threshold requires the host AI to know each model's context window size
   - Resolution: Added `context_window` as a per-model metadata field in `config.yaml` alongside capability weights. Orchestrator receives this in council assembly response.

**No remaining critical or important gaps.**

**Nice-to-Have (deferred):**
- CI/CD pipeline configuration (not needed for solo dev MVP)
- PyPI publishing workflow (deferred — git-based install for now)
- Pre-commit hooks for ruff enforcement (can add later)

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (39 FRs across 6 categories)
- [x] Scale and complexity assessed (medium complexity, Python MCP server)
- [x] Technical constraints identified (Python 3.11+, MCP SDK, OpenRouter, file-only persistence)
- [x] Cross-cutting concerns mapped (config cascading, OpenRouter integration, error handling, logging)

**✅ Architectural Decisions**
- [x] Critical decisions documented (OpenRouter client, config structure, agent system)
- [x] Technology stack fully specified (Python/uv/hatchling/httpx/Pydantic/FastMCP/ruff/pytest)
- [x] Integration patterns defined (boundary modules, data flow, concurrent API calls)
- [x] Performance considerations addressed (async concurrency, no server-side bottlenecks)

**✅ Implementation Patterns**
- [x] Naming conventions established (snake_case everywhere, enforced by ruff)
- [x] Structure patterns defined (tool modules, test organization)
- [x] Error handling patterns specified (custom hierarchy, retry-then-reassign)
- [x] Process patterns documented (config access, logging, tool registration)

**✅ Project Structure**
- [x] Complete directory structure defined (source, tests, fixtures, user-facing directory)
- [x] Component boundaries established (5 clear boundaries with single owners)
- [x] Integration points mapped (internal and external)
- [x] Requirements to structure mapping complete (FR categories → modules table)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — architecture inherits a battle-tested foundation (gemini-mcp) and all decisions are grounded in the existing codebase patterns.

**Key Strengths:**
- Inherits proven architecture from gemini-mcp — not designing from scratch
- Clear separation of concerns with single-owner boundary modules
- Evolution path is well-defined (7 specific steps from gemini-mcp to aicouncil)
- Every FR has a concrete module mapping
- Patterns are specific to this project, not generic boilerplate

**Areas for Future Enhancement:**
- PyPI distribution for better discoverability
- CI/CD pipeline for automated testing
- Pre-commit hooks for pattern enforcement
- Council history indexing/search (post-MVP)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries — every module has a single owner
- Use custom exception hierarchy, never bare exceptions
- All MCP tools return Pydantic schemas
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. Fork gemini-mcp → rename to aicouncil
2. Swap google-genai client for httpx async OpenRouter client
3. Implement YAML config loader with cascading defaults
4. Implement auto-scaffold for `./aicouncil/` directory

**PRD Correction Applied:**
The PRD's TypeScript/Node.js assumption has been corrected to Python 3.11+ throughout. The project classification has been updated from "Greenfield" to "Brownfield evolution" reflecting the gemini-mcp fork.
