# Story 1.4: Agent System & Loader

Status: ready-for-dev

## Story

As a developer or power user,
I want to browse the agent roster, create custom agents, and have them automatically discovered and merged with built-in agents,
so that I can extend the council with domain-specific expertise for my project.

## Acceptance Criteria

1. **Given** built-in agents exist in `src/aicouncil/agents/` with `agent-manifest.csv` and individual `.md` persona files
   **When** the agent loader runs
   **Then** it parses the CSV manifest and loads all Markdown persona files with YAML frontmatter (name, role, type, tier, domains, include_flag)
   **And** `agent_loader.py` is the sole module that reads agent data

2. **Given** user-created agents exist in `./aicouncil/agents/`
   **When** the agent loader merges both directories
   **Then** user agents with the same name override built-in agents
   **And** all other agents from both directories are available

3. **Given** a user creates a new agent following the Markdown persona template
   **When** they add it to `./aicouncil/agents/` with a CSV manifest entry
   **Then** the agent is discoverable at runtime alongside built-in agents

4. **Given** an agent file is malformed (missing YAML frontmatter or required fields)
   **When** the agent loader attempts to parse it
   **Then** it raises `AgentLoadError` with a clear message identifying the file and the issue
   **And** other valid agents continue to load

5. **Given** agents are loaded
   **When** any module needs agent data
   **Then** the loader returns structured Pydantic models, never raw file contents
   **And** agents are organized by type (expert/builder/user) and tier (1/2/3) with inclusion flags accessible

## Tasks / Subtasks

- [ ] Task 1: Create agent Pydantic models (AC: #5)
  - [ ] Create `Agent` model with all frontmatter fields (name, role, type, tier, domains, include_flag) + persona body
  - [ ] Create `AgentRoster` model holding the merged collection with query methods (by_type, by_tier, by_domain)
  - [ ] Type field: `Literal["expert", "builder", "user"]`; Tier field: `Literal[1, 2, 3]`; domains: `list[str]`; include_flag: `bool`
  - [ ] Place models in `src/aicouncil/schemas/agents.py` (separate from responses.py — agents are a distinct domain)

- [ ] Task 2: Create seed built-in agents for testing (AC: #1)
  - [ ] Create `src/aicouncil/agents/` directory with `__init__.py` (empty, makes it a package for `importlib.resources`)
  - [ ] Create `agent-manifest.csv` with 5 seed agents (minimum viable roster for loader development + tests):
    - 1 Tier-1 expert (e.g., software-architect)
    - 1 Tier-2 expert (e.g., security-engineer)
    - 1 Tier-3 expert (e.g., tax-advisor)
    - 1 builder (e.g., backend-developer)
    - 1 user (e.g., entrepreneur)
  - [ ] Create 5 corresponding `.md` persona files following the exact template format (YAML frontmatter + 4 body sections)
  - [ ] CSV headers: `name,role,type,tier,domains,include_flag`
  - [ ] Note: Full 35-42 roster is Story 1.5 scope — only seed agents here

- [ ] Task 3: Create `src/aicouncil/agent_loader.py` — CSV parsing (AC: #1, #4)
  - [ ] `parse_manifest(csv_path: Path) -> list[dict]` — parse CSV manifest into list of row dicts
  - [ ] Validate required CSV headers: name, role, type, tier, domains, include_flag
  - [ ] Parse domains field: CSV stores as semicolon-separated string (e.g., `"architecture;design;patterns"`) → convert to `list[str]`
  - [ ] Raise `AgentLoadError` if CSV is missing, empty, or has missing required headers

- [ ] Task 4: Create `agent_loader.py` — Markdown persona parsing (AC: #1, #4, #5)
  - [ ] `parse_persona(md_path: Path) -> Agent` — parse single Markdown persona file
  - [ ] Extract YAML frontmatter (between `---` delimiters) using `yaml.safe_load()`
  - [ ] Extract Markdown body (everything after second `---`)
  - [ ] Validate required frontmatter fields: name, role, type, tier, domains, include_flag
  - [ ] Validate type is one of: expert, builder, user
  - [ ] Validate tier is one of: 1, 2, 3
  - [ ] Raise `AgentLoadError` with filename + specific issue on malformed files
  - [ ] Return `Agent` Pydantic model instance

- [ ] Task 5: Create `agent_loader.py` — Directory loading (AC: #1, #2, #3)
  - [ ] `load_agents_from_directory(directory: Path) -> list[Agent]` — load all agents from a single directory
  - [ ] Read manifest CSV to discover agents, then load each persona `.md` file
  - [ ] If no manifest CSV exists but `.md` files exist, load `.md` files directly (user dir may not have manifest)
  - [ ] If manifest references a file that doesn't exist, log WARNING and skip (don't fail entire load)
  - [ ] If `.md` file exists but isn't in manifest, still load it (manifest is index, not gatekeeper)

- [ ] Task 6: Create `agent_loader.py` — Dual-directory overlay merge (AC: #2, #3)
  - [ ] `load_builtin_agents() -> list[Agent]` — load from `src/aicouncil/agents/` using `importlib.resources`
  - [ ] `load_user_agents(project_root: Path | None = None) -> list[Agent]` — load from `./aicouncil/agents/`
  - [ ] `load_all_agents(project_root: Path | None = None) -> AgentRoster` — merge both, user overrides built-in by name
  - [ ] Override key: agent `name` field (case-insensitive comparison)
  - [ ] Return `AgentRoster` with all merged agents

- [ ] Task 7: Create `agent_loader.py` — Singleton/caching pattern (AC: #5)
  - [ ] `get_agents() -> AgentRoster` — lazy-loaded singleton (mirrors `get_config()` pattern)
  - [ ] `reset_agents() -> None` — reset singleton for testing
  - [ ] Accept optional `project_root` parameter for testability
  - [ ] Log INFO on initial load with agent count summary (e.g., "Loaded 42 agents: 30 expert, 7 builder, 5 user")

- [ ] Task 8: Write tests — `tests/test_agent_loader.py` (AC: #1-#5)
  - [ ] Test CSV manifest parsing: valid manifest, missing headers, empty file, malformed rows
  - [ ] Test Markdown persona parsing: valid file, missing frontmatter, missing required fields, invalid type/tier values
  - [ ] Test directory loading: directory with manifest + personas, directory with only personas (no manifest), empty directory
  - [ ] Test dual-directory overlay: user agent overrides built-in by name, both directories contribute unique agents
  - [ ] Test AgentRoster query methods: by_type, by_tier, by_domain, include_flag filtering
  - [ ] Test error handling: AgentLoadError raised with clear messages, valid agents load despite individual file failures
  - [ ] Test singleton: get_agents(), reset_agents()
  - [ ] Use `tmp_path` fixtures for temp directories with mock agent files
  - [ ] Run `uv run pytest` — all tests pass including existing 153

- [ ] Task 9: Lint & format (AC: all)
  - [ ] Run `uv run ruff format .`
  - [ ] Run `uv run ruff check --fix .`
  - [ ] Verify zero lint errors

## Dev Notes

### Current State (Post Story 1.3)

| Component | State | Location |
|-----------|-------|----------|
| Exception hierarchy incl. `AgentLoadError` | Complete | `src/aicouncil/exceptions.py` |
| Config system (singleton, resolve_model, frozen) | Complete | `src/aicouncil/config.py` (276 lines) |
| Auto-scaffold (creates `./aicouncil/agents/` dir) | Complete | `src/aicouncil/scaffold.py` (57 lines) |
| Server.py thin registry (15 tools registered) | Complete | `src/aicouncil/server.py` (81 lines) |
| Pydantic response schemas (all tool responses) | Complete | `src/aicouncil/schemas/responses.py` (332 lines) |
| OpenRouter client with retry | Complete | `src/aicouncil/client.py` |
| Tool modules (analysis, research, codebase, memory) | Complete | `src/aicouncil/tools/` |
| Tests (153 passing) | Complete | `tests/` |
| `src/aicouncil/agents/` directory | Does NOT exist | Create in this story |
| `src/aicouncil/agent_loader.py` | Does NOT exist | Create in this story |
| `src/aicouncil/schemas/agents.py` | Does NOT exist | Create in this story |

### Agent Persona Markdown Template (Exact Format)

```markdown
---
name: "Software Architect"
role: "Principal Software Architect"
type: "expert"
tier: 1
domains: ["architecture", "design_patterns", "system_design"]
include_flag: true
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

YAML frontmatter = machine-parseable for assembly. Markdown body = persona prompt sent to model.

### CSV Manifest Format

```csv
name,role,type,tier,domains,include_flag
software-architect,Principal Software Architect,expert,1,architecture;design_patterns;system_design,true
security-engineer,Application Security Engineer,expert,2,security;authentication;compliance,true
tax-advisor,Tax & Compliance Advisor,expert,3,taxation;compliance;financial_regulation,true
backend-developer,Senior Backend Developer,builder,1,backend;api_design;databases,true
entrepreneur,Startup Entrepreneur,user,1,business;product;market_fit,true
```

- `name` column matches the `.md` filename (without extension): e.g., `software-architect` → `software-architect.md`
- `domains` uses semicolons as delimiter (commas would conflict with CSV)
- `include_flag` is string `"true"`/`"false"` in CSV, parsed to Python `bool`

### YAML Frontmatter Parsing Pattern

Do NOT add `python-frontmatter` as a dependency. Use raw YAML parsing — the project already depends on PyYAML:

```python
import yaml

def parse_persona(md_path: Path) -> Agent:
    content = md_path.read_text()
    if not content.startswith("---"):
        raise AgentLoadError(f"{md_path.name}: missing YAML frontmatter (must start with ---)")

    parts = content.split("---", 2)  # ['', yaml_str, markdown_body]
    if len(parts) < 3:
        raise AgentLoadError(f"{md_path.name}: malformed frontmatter (missing closing ---)")

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()
    # Validate and construct Agent model...
```

### Dual-Directory Overlay — Loading Built-In Agents

Built-in agents ship inside the package at `src/aicouncil/agents/`. Use `importlib.resources` (same pattern as `scaffold.py` uses for default config):

```python
from importlib import resources

def load_builtin_agents() -> list[Agent]:
    agents_ref = resources.files("aicouncil.agents")
    # List all .md and .csv files in the package directory
    # Use resources.as_file() for each file to get a real Path
```

The `src/aicouncil/agents/` directory needs an `__init__.py` to be importable as a package resource.

### Dual-Directory Overlay — Merge Logic

```
Built-in (src/aicouncil/agents/):
  software-architect.md  → Agent(name="software-architect", ...)
  security-engineer.md   → Agent(name="security-engineer", ...)

User-local (./aicouncil/agents/):
  software-architect.md  → Agent(name="software-architect", ...) [OVERRIDE]
  restaurant-expert.md   → Agent(name="restaurant-expert", ...)  [NEW]

Merged result:
  software-architect     → FROM USER (override)
  security-engineer      → FROM BUILT-IN
  restaurant-expert      → FROM USER (new)
```

Override key: `name` field from YAML frontmatter (case-insensitive). NOT filename.

### AgentRoster Query API

The `AgentRoster` model should provide query methods for council assembly (Story 2.1):

```python
class AgentRoster(BaseModel):
    agents: list[Agent]

    def by_type(self, agent_type: str) -> list[Agent]: ...
    def by_tier(self, tier: int) -> list[Agent]: ...
    def by_domain(self, domain: str) -> list[Agent]: ...
    def experts(self) -> list[Agent]: ...
    def builders(self) -> list[Agent]: ...
    def users(self, include_flagged_only: bool = True) -> list[Agent]: ...
    def get_by_name(self, name: str) -> Agent | None: ...
```

These methods will be consumed by `council/assembler.py` in Story 2.1.

### Error Handling — Graceful Degradation

Per AC #4: malformed agents must NOT crash the entire load. Pattern:

```python
for md_file in md_files:
    try:
        agent = parse_persona(md_file)
        agents.append(agent)
    except AgentLoadError as e:
        logger.error(f"Skipping malformed agent: {e}")
        # Continue loading other agents
```

Only raise `AgentLoadError` to the caller when NO agents can be loaded at all (empty roster after attempted load).

### Logging Conventions

- **DEBUG:** Individual file parsing details, frontmatter field values, merge decisions
- **INFO:** Agent load summary ("Loaded 42 agents: 30 expert, 7 builder, 5 user"), user override notifications
- **WARNING:** Missing manifest file (falling back to .md discovery), manifest references non-existent file, skipping malformed agent
- **ERROR:** Failed to parse agent file (with filename and error), no agents loaded at all

### Files to Create

| File | Purpose |
|------|---------|
| `src/aicouncil/schemas/agents.py` | Agent + AgentRoster Pydantic models |
| `src/aicouncil/agent_loader.py` | Dual-directory overlay, CSV + Markdown parsing, singleton |
| `src/aicouncil/agents/__init__.py` | Empty (makes agents/ an importable package for importlib.resources) |
| `src/aicouncil/agents/agent-manifest.csv` | CSV index of 5 seed agents |
| `src/aicouncil/agents/software-architect.md` | Seed persona: Tier-1 expert |
| `src/aicouncil/agents/security-engineer.md` | Seed persona: Tier-2 expert |
| `src/aicouncil/agents/tax-advisor.md` | Seed persona: Tier-3 expert |
| `src/aicouncil/agents/backend-developer.md` | Seed persona: builder |
| `src/aicouncil/agents/entrepreneur.md` | Seed persona: user |
| `tests/test_agent_loader.py` | Comprehensive agent loader tests |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/aicouncil/server.py` | Agent loader doesn't register MCP tools (no tool surface in this story) |
| `src/aicouncil/config.py` | Config has no agent-related fields — agent_loader is independent |
| `src/aicouncil/client.py` | Agent loading is local I/O — no API calls |
| `src/aicouncil/exceptions.py` | `AgentLoadError` already exists |
| `src/aicouncil/schemas/responses.py` | Agent models go in new `schemas/agents.py` |
| `src/aicouncil/scaffold.py` | Already creates `./aicouncil/agents/` dir — no changes needed |
| `src/aicouncil/tools/` | No tool changes — agent browsing tools are future scope |

### Previous Story Intelligence (Story 1.3)

**Key learnings:**
- `importlib.resources` pattern is established for loading package data (used in `scaffold.py` for `default-config.yaml`)
- Singleton pattern is established: `get_config()` / `reset_config()` / `reload_config()` — mirror for agents
- Test pattern: `tmp_path` for temp directories, mock data files, `conftest.py` fixtures
- 153 tests currently pass — zero regressions required
- `tools/__init__.py` contains shared helpers — agent-related shared utilities go in `agent_loader.py` (not tools/)
- Pydantic v2 with `ConfigDict(frozen=True)` for immutable models

**Patterns to reuse:**
- `Config` singleton → same pattern for `get_agents()` singleton
- `importlib.resources.files("aicouncil.defaults")` → `importlib.resources.files("aicouncil.agents")`
- `yaml.safe_load()` for YAML parsing (already a dependency)
- `csv` module from stdlib for CSV parsing (no new deps needed)

### Anti-Patterns to Avoid

- **DO NOT** add `python-frontmatter` dependency — parse YAML frontmatter manually with PyYAML
- **DO NOT** read agent files from any module other than `agent_loader.py`
- **DO NOT** return raw dicts or file contents — always Pydantic `Agent` models
- **DO NOT** fail the entire load for one malformed agent — skip and continue
- **DO NOT** put agent models in `schemas/responses.py` — use separate `schemas/agents.py`
- **DO NOT** modify built-in agent files at runtime — they are read-only package data
- **DO NOT** require the user directory to have a manifest CSV — `.md` files alone should work
- **DO NOT** use `os.listdir()` or `glob` for package resources — use `importlib.resources` for built-in agents
- **DO NOT** use filename as override key — use the `name` field from YAML frontmatter
- **DO NOT** create MCP tools in this story — agent browsing tools are future scope (Story 2.x)

### Testing Strategy

- Create fixture agent files (valid + invalid) in `tmp_path` directories
- Test CSV parsing independently from Markdown parsing
- Test directory loading with various combinations (manifest only, .md only, both, neither)
- Test overlay merge with name collision (user wins)
- Test AgentRoster query methods with known fixture data
- Test error cases: malformed YAML, missing fields, invalid type/tier, file not found
- Verify singleton caching and reset behavior
- All 153 existing tests must still pass

### Project Structure After This Story

```
src/aicouncil/
├── server.py              # UNCHANGED
├── client.py              # UNCHANGED
├── config.py              # UNCHANGED
├── exceptions.py          # UNCHANGED (AgentLoadError already there)
├── scaffold.py            # UNCHANGED
├── agent_loader.py        # NEW: Dual-directory overlay, CSV + Markdown parsing
├── tools/                 # UNCHANGED
├── schemas/
│   ├── __init__.py        # UNCHANGED
│   ├── responses.py       # UNCHANGED
│   └── agents.py          # NEW: Agent + AgentRoster Pydantic models
├── agents/                # NEW: Built-in agent roster (read-only package data)
│   ├── __init__.py        # NEW: Empty (importlib.resources package marker)
│   ├── agent-manifest.csv # NEW: CSV index of 5 seed agents
│   ├── software-architect.md
│   ├── security-engineer.md
│   ├── tax-advisor.md
│   ├── backend-developer.md
│   └── entrepreneur.md
├── prompts/               # UNCHANGED
├── memory/                # UNCHANGED
├── scanner/               # UNCHANGED
└── defaults/              # UNCHANGED

tests/
├── test_agent_loader.py   # NEW: Agent loader tests
├── test_client.py         # UNCHANGED
├── test_config.py         # UNCHANGED
├── test_exceptions.py     # UNCHANGED
├── test_schemas.py        # UNCHANGED
├── test_scaffold.py       # UNCHANGED
├── test_tools/            # UNCHANGED
└── conftest.py            # UNCHANGED (or minor fixture additions)
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md — Agent System — Dual Directory with Overlay]
- [Source: _bmad-output/planning-artifacts/architecture.md — Agent Persona File Format]
- [Source: _bmad-output/planning-artifacts/architecture.md — Agent Data Boundary, agent_loader.py ownership]
- [Source: _bmad-output/planning-artifacts/architecture.md — Implementation Patterns — Naming, Error Handling]
- [Source: _bmad-output/planning-artifacts/epics.md — Story 1.4 Acceptance Criteria (FR18-25)]
- [Source: _bmad-output/planning-artifacts/prd.md — FR18 (35-42 agents), FR19 (Markdown persona), FR20 (CSV manifest), FR21 (tier system), FR22 (inclusion flag), FR23-25 (custom agents)]
- [Source: _bmad-output/project-context.md — Boundary Violations, Agent Data Boundary]
- [Source: _bmad-output/implementation-artifacts/1-3-extended-tools-migration.md — importlib.resources pattern, singleton pattern, test conventions]
- [Source: src/aicouncil/scaffold.py — importlib.resources usage, ./aicouncil/agents/ creation]
- [Source: src/aicouncil/config.py — Singleton pattern (get_config/reset_config), Pydantic frozen models]
- [Source: src/aicouncil/exceptions.py — AgentLoadError already defined]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log

### File List
