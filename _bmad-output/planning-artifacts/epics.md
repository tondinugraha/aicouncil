---
stepsCompleted: ['step-01-requirements-extraction', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments: ['prd.md', 'architecture.md', 'brainstorming-session-2026-03-18-1625.md']
---

# aicouncil - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for aicouncil, decomposing the requirements from the PRD, Architecture, and Brainstorming session into implementable stories.

## Requirements Inventory

### Functional Requirements

- FR1: User can invoke a council session by providing a topic through the MCP `ai_council` tool
- FR2: System classifies the topic into capability domains using LLM-powered analysis to inform agent selection
- FR3: Orchestrator assembles a council by selecting agents based on topic relevance, category mix (expert/builder/user), and domain coverage breadth
- FR4: Orchestrator assigns models to selected agents using capability-weighted random routing (60/40 bias toward capability-matched models)
- FR5: Orchestrator can instantiate the same agent persona on multiple different models within a single council for perspective diversity
- FR6: Orchestrator includes wildcard agents from unrelated domains at a 5:1 ratio when topic warrants cross-domain insight
- FR7: Orchestrator directs the deliberation as chairperson — controlling speaking order, introducing debate when positions converge prematurely, and driving toward conclusion
- FR8: Orchestrator dynamically shifts council tone between adversarial debate and agreement-seeking based on discussion state
- FR9: Orchestrator evaluates convergence after each round and decides whether to continue deliberation or drive toward consensus (no fixed round count)
- FR10: Agents respond in free-form persona voice consistent with their authored communication style and domain expertise
- FR11: Orchestrator manages context adaptively — full transcript when under 50% of model's context window, summarized context when exceeding threshold
- FR12: Orchestrator conducts a one-sentence consensus round where each agent states endorsement or dissent with key caveat
- FR13: Orchestrator drives toward unanimous consensus as primary goal, falling back to tiered conclusions ("all agree on X, most agree on Y, divided on Z") when full agreement is not achievable
- FR14: Orchestrator weights agent opinions by domain relevance when resolving deadlocks
- FR15: Orchestrator synthesizes a detail-preserving narrative addendum capturing full reasoning, recommendations, and dissenting views
- FR16: System delivers council output as dual output — inline response in conversation AND saved markdown file
- FR17: User can override automatic council assembly by pinning specific agents and/or models via natural language in their prompt
- FR18: System ships with 35-42 hand-crafted agents across three categories: domain experts, technical builders, and end-user personas
- FR19: Each agent is defined in an individual Markdown file with name, role, identity, communication style, principles, domain expertise, and agent type flag
- FR20: Agent roster is indexed via CSV manifest (`agents/agent-manifest.csv`) for quick lookup and routing
- FR21: Expert agents are organized in demand tiers: Tier 1 (universal — 90%+ niche relevance), Tier 2 (high-demand — 60-80%), Tier 3 (niche specialists — 30-50%)
- FR22: User-type agents carry an inclusion flag allowing council selection logic to include/exclude them based on topic nature
- FR23: User can create custom agents following the same Markdown persona format and CSV manifest pattern
- FR24: Custom agents in a user directory extend or override built-in core agents
- FR25: Orchestrator discovers and includes custom agents alongside built-in roster during council assembly
- FR26: All tools route API calls through OpenRouter using a single API key
- FR27: System supports cascading model defaults: global default → per-tool override → per-invocation override
- FR28: Council tool maintains its own model pool array in configuration, separate from individual tool defaults
- FR29: Model-capability affinities are stored in an editable YAML config file
- FR30: System ships with sensible default capability weights that users can tune as models evolve
- FR31: All existing gemini-mcp utility tools function with configurable model selection via OpenRouter
- FR32: Each extended tool operates identically to its current implementation with the model being the only configurable difference
- FR33: Extended tools respect the cascading model default hierarchy
- FR34: System saves council addendums to a dedicated `council-history/` directory with timestamped filenames
- FR35: Addendum files are markdown-formatted narratives readable by non-technical stakeholders
- FR36: Council history persists as a project decision log accessible to all team members via the file system
- FR37: User can install the MCP server and run their first council session in under 10 minutes
- FR38: System requires only an OpenRouter API key to function — zero additional configuration needed for default operation
- FR39: All configuration lives in the project directory — portable, self-contained, and version-controllable

### NonFunctional Requirements

- NFR1: API calls to OpenRouter complete within the model provider's standard response time; the MCP server adds no meaningful latency overhead beyond request marshaling
- NFR2: Council assembly (topic classification + agent selection + model routing) completes in a single LLM call before deliberation begins
- NFR3: Adaptive context management maintains deliberation quality across long sessions by summarizing at the 50% context window threshold
- NFR4: OpenRouter API key is stored in `.mcp.json` (project-local, user-managed) — the system never transmits, logs, or exposes the key beyond OpenRouter API calls
- NFR5: No user data, conversation content, or council history is transmitted to any service other than OpenRouter for model inference
- NFR6: The system operates entirely locally — no backend service, no analytics, no telemetry
- NFR7: Council sessions gracefully handle model unavailability — if a specific model is unreachable via OpenRouter, the orchestrator can reassign the agent to an available model from the pool
- NFR8: Addendum files are written atomically to prevent partial output from interrupted sessions
- NFR9: Configuration validation at startup surfaces invalid config, missing API key, or malformed agent manifests with clear error messages
- NFR10: Agent persona format is documented and templated, enabling users to author new agents without modifying system code
- NFR11: Capability weight matrix is data-driven (YAML config), allowing model routing adjustments without code changes
- NFR12: MCP tool registration is modular — new tools can be added by following existing tool patterns
- NFR13: Compatible with any MCP-enabled host environment (Claude Code, Cursor, Windsurf, and future MCP clients)
- NFR14: Compatible with any model available through OpenRouter's API
- NFR15: Runs on any platform supporting Python 3.11+ (macOS, Linux, Windows)

### Additional Requirements

- Architecture specifies fork of gemini-mcp as starter — not greenfield. Epic 1 Story 1 must handle the fork, rename, and client swap.
- Auto-scaffold `./aicouncil/` directory with default `config.yaml`, empty `history/` and `agents/` on first run when directory is missing
- Custom exception hierarchy must be implemented early — `AiCouncilError`, `OpenRouterError`, `ModelUnavailableError`, `ConfigError`, `AgentLoadError`, `CouncilError`
- Hybrid singleton + dependency injection for config access (production uses singleton, tests inject mock)
- All boundary modules have strict ownership: `server.py` (MCP protocol), `client.py` (OpenRouter API), `config.py` (configuration), `agent_loader.py` (agent data), `council/history.py` (file output)
- `ModelUnavailableError` triggers retry-then-reassign pattern (retry 2-3x, then swap model)
- Config is immutable after startup — no runtime mutation
- Council sessions generate UUID at start, included in all related log entries
- Model context window metadata (`context_window` per model) must be included in config for orchestrator adaptive context management
- Git-based install (`uvx --from git+...`) for now — PyPI deferred

### UX Design Requirements

N/A — MCP server with no UI. No UX document exists.

### FR Coverage Map

- FR1: Epic 2 — Invoke council session via MCP tool
- FR2: Epic 2 — LLM-powered topic classification
- FR3: Epic 2 — Orchestrator assembles council (relevance, category mix, coverage)
- FR4: Epic 2 — Capability-weighted random model routing (60/40)
- FR5: Epic 2 — Same agent on multiple models for diversity
- FR6: Epic 2 — Wildcard agents at 5:1 ratio
- FR7: Epic 2 — Orchestrator as chairperson directing deliberation
- FR8: Epic 2 — Dynamic tone shifting (debate vs agreement)
- FR9: Epic 2 — Orchestrator-judged convergence (no fixed rounds)
- FR10: Epic 2 — Free-form persona voice responses
- FR11: Epic 2 — Adaptive context management (50% threshold)
- FR12: Epic 2 — One-sentence consensus round
- FR13: Epic 2 — Unanimous-first consensus, tiered fallback
- FR14: Epic 2 — Domain-weighted opinion for deadlocks
- FR15: Epic 2 — Detail-preserving narrative addendum
- FR16: Epic 2 — Dual output (inline + file)
- FR17: Epic 2 — User override — pin agents/models via prompt
- FR18: Epic 1 — 35-42 hand-crafted agents across 3 categories
- FR19: Epic 1 — Markdown persona files with full agent template
- FR20: Epic 1 — CSV manifest for quick lookup and routing
- FR21: Epic 1 — Demand-tiered expert agents (Tier 1/2/3)
- FR22: Epic 1 — User-agent inclusion flag
- FR23: Epic 1 — Custom agent creation via open template
- FR24: Epic 1 — Custom agents extend/override built-ins
- FR25: Epic 1 — Orchestrator discovers custom agents at runtime
- FR26: Epic 1 — All tools route through OpenRouter (single API key)
- FR27: Epic 1 — Cascading model defaults (global → per-tool → per-invocation)
- FR28: Epic 1 — Council model pool array in config
- FR29: Epic 1 — Capability weight matrix in editable YAML
- FR30: Epic 1 — Sensible default capability weights shipped
- FR31: Epic 1 — All gemini-mcp tools work via OpenRouter
- FR32: Epic 1 — Extended tools identical except model is configurable
- FR33: Epic 1 — Extended tools respect cascading defaults
- FR34: Epic 2 — Council addendums saved with timestamped filenames
- FR35: Epic 2 — Addendums in narrative markdown format
- FR36: Epic 2 — Council history as persistent decision log
- FR37: Epic 1 — Install and first session in under 10 minutes
- FR38: Epic 1 — Only OpenRouter API key needed for default operation
- FR39: Epic 1 — All config project-local, portable, version-controllable

## Epic List

### Epic 1: OpenRouter Migration & Agent Infrastructure
All existing tools work via OpenRouter with configurable model selection, and the full agent roster is loaded, browsable, and extensible.
**FRs covered:** FR18-33, FR26-27, FR37-39

### Epic 2: AI Council Deliberation
User can convene a multi-agent, multi-model council — orchestrator-driven assembly, structured debate with a chairperson, consensus with tiered fallback, and a detail-preserving narrative addendum delivered inline and saved to file.
**FRs covered:** FR1-17, FR34-36

## Epic 1: OpenRouter Migration & Agent Infrastructure

All existing tools work via OpenRouter with configurable model selection, and the full agent roster is loaded, browsable, and extensible.

### Story 1.1: Fork, Rename & OpenRouter Client

As a developer using an MCP-enabled host,
I want the aicouncil server to route all API calls through OpenRouter using a single API key,
So that I can access any model via a unified gateway without managing multiple provider SDKs.

**Acceptance Criteria:**

**Given** the gemini-mcp codebase exists at https://github.com/tondinugraha/gemini-mcp.git
**When** the project is forked and renamed to aicouncil
**Then** all package references (pyproject.toml, module names, imports) reflect the new `aicouncil` name
**And** the `google-genai` dependency is removed and replaced with `httpx` for async HTTP

**Given** an OpenRouter API key is set in `.mcp.json` environment variables
**When** the server starts and a tool makes an API call
**Then** the request is sent to `https://openrouter.ai/api/v1/chat/completions` via the async httpx client in `client.py`
**And** no other module makes HTTP requests directly

**Given** an API call fails
**When** the error is an OpenRouter communication failure
**Then** the system raises `OpenRouterError` (not bare `Exception`)
**And** the full custom exception hierarchy exists: `AiCouncilError`, `OpenRouterError`, `ModelUnavailableError`, `ConfigError`, `AgentLoadError`, `CouncilError`

**Given** the server is started via `uv run aicouncil`
**When** it connects to the MCP host via stdio transport
**Then** at least one tool is functional end-to-end through OpenRouter

### Story 1.2: Config System & Auto-Scaffold

As a developer installing aicouncil for the first time,
I want the server to auto-create its configuration directory and load model config from YAML with cascading defaults,
So that I can start using the tool immediately with zero manual setup and customize model selection later.

**Acceptance Criteria:**

**Given** no `./aicouncil/` directory exists in the project root
**When** the server starts for the first time
**Then** it creates `./aicouncil/` with default `config.yaml`, empty `history/`, and empty `agents/` directories
**And** the default `config.yaml` contains a global default model, model pool array, and sensible capability weights with `context_window` metadata per model

**Given** a `./aicouncil/config.yaml` exists with cascading model defaults
**When** a tool is invoked without a per-invocation model override
**Then** the config resolves: per-invocation → per-tool override → global default (cascading)
**And** the Config object is immutable after startup — no runtime mutation

**Given** the config system is loaded
**When** any module needs config access
**Then** it uses the hybrid singleton pattern (production: `get_config()`, tests: inject mock via constructor)
**And** `config.py` is the sole reader of YAML config — no other module reads config files directly

**Given** the config file is malformed or the API key is missing
**When** the server starts
**Then** it raises `ConfigError` with a clear, actionable error message

### Story 1.3: Extended Tools Migration

As a developer using aicouncil utility tools,
I want all existing gemini-mcp tools (critique, brainstorm, validate, research, codebase scan, memory) to work with any model via OpenRouter,
So that I can use different models for different tasks without changing tools.

**Acceptance Criteria:**

**Given** the existing gemini-mcp tools are present in `src/aicouncil/tools/`
**When** any tool is invoked via MCP
**Then** it routes its API call through the OpenRouter client in `client.py`
**And** the tool behavior is identical to the original except the model is configurable

**Given** a tool has a per-tool model override in `config.yaml`
**When** the tool is invoked without a per-invocation override
**Then** it uses the per-tool model, not the global default
**And** per-invocation overrides still take precedence over per-tool config

**Given** the council model pool is defined in `config.yaml`
**When** the config is loaded
**Then** the model pool array, capability weight matrix (model-centric format), and `context_window` per model are all accessible via the Config object
**And** the capability weights ship with sensible defaults

**Given** a model is unavailable during a tool call
**When** the `client.py` receives an error from OpenRouter
**Then** it retries 2-3 times before raising `ModelUnavailableError`

### Story 1.4: Agent System & Loader

As a developer or power user,
I want to browse the agent roster, create custom agents, and have them automatically discovered and merged with built-in agents,
So that I can extend the council with domain-specific expertise for my project.

**Acceptance Criteria:**

**Given** built-in agents exist in `src/aicouncil/agents/` with `agent-manifest.csv` and individual `.md` persona files
**When** the agent loader runs
**Then** it parses the CSV manifest and loads all Markdown persona files with YAML frontmatter (name, role, type, tier, domains, include_flag)
**And** `agent_loader.py` is the sole module that reads agent data

**Given** user-created agents exist in `./aicouncil/agents/`
**When** the agent loader merges both directories
**Then** user agents with the same name override built-in agents
**And** all other agents from both directories are available

**Given** a user creates a new agent following the Markdown persona template
**When** they add it to `./aicouncil/agents/` with a CSV manifest entry
**Then** the agent is discoverable at runtime alongside built-in agents

**Given** an agent file is malformed (missing YAML frontmatter or required fields)
**When** the agent loader attempts to parse it
**Then** it raises `AgentLoadError` with a clear message identifying the file and the issue
**And** other valid agents continue to load

**Given** agents are loaded
**When** any module needs agent data
**Then** the loader returns structured Pydantic models, never raw file contents
**And** agents are organized by type (expert/builder/user) and tier (1/2/3) with inclusion flags accessible

### Story 1.5: Agent Roster Authoring

As a user convening an AI council,
I want a diverse library of 35-42 hand-crafted expert agents spanning domains like software, business, finance, law, marketing, and more,
So that council deliberations have substantive, domain-specific expertise across any topic I need advice on.

**Acceptance Criteria:**

**Given** the agent roster needs to be authored
**When** all persona files are created
**Then** there are 35-42 agents across three categories: domain experts, technical builders, and end-user personas
**And** experts are tiered: Tier 1 (universal, 90%+ relevance), Tier 2 (high-demand, 60-80%), Tier 3 (niche, 30-50%)

**Given** each agent has a persona file
**When** the file is inspected
**Then** it follows the exact Markdown template: YAML frontmatter (name, role, type, tier, domains, include_flag) + body sections (Identity, Communication Style, Principles, Domain Expertise)
**And** each agent has a distinctive communication style and domain-specific principles

**Given** the complete roster is authored
**When** the CSV manifest `agent-manifest.csv` is inspected
**Then** every agent has a corresponding row with snake_case headers matching the YAML frontmatter fields
**And** the manifest is consistent with the individual persona files

**Given** user-type agents are in the roster
**When** their persona files are inspected
**Then** they carry `include_flag: true` or `include_flag: false` to control adaptive council inclusion
**And** they represent real-world user perspectives (entrepreneur, student, consumer, etc.)

## Epic 2: AI Council Deliberation

User can convene a multi-agent, multi-model council — orchestrator-driven assembly, structured debate with a chairperson, consensus with tiered fallback, and a detail-preserving narrative addendum delivered inline and saved to file.

### Story 2.1: Council Assembly

As a developer seeking multi-perspective advice,
I want to invoke an `ai_council` tool that classifies my topic, selects relevant agents, and assigns models using capability-weighted routing,
So that the council is intelligently composed for my specific question without any manual configuration.

**Acceptance Criteria:**

**Given** a user invokes the `ai_council` MCP tool with a topic
**When** the tool processes the request
**Then** it generates a session UUID and includes it in all related log entries
**And** the tool is registered in `server.py` with logic in `tools/council.py`

**Given** a topic is provided
**When** topic classification runs
**Then** the system uses a single LLM call to classify the topic into capability domains
**And** the classification result informs agent selection

**Given** the topic is classified
**When** the council assembler selects agents
**Then** it balances three factors: topic relevance, category mix (expert/builder/user), and domain coverage breadth
**And** it includes wildcard agents from unrelated domains at a 5:1 ratio when the topic warrants cross-domain insight

**Given** agents are selected
**When** models are assigned
**Then** the system uses capability-weighted random routing (60/40 bias toward capability-matched models)
**And** the same agent persona can be instantiated on multiple different models within a single council

**Given** the user includes natural language agent/model preferences in their prompt (e.g., "include a Statistician on GPT 5.2")
**When** the council assembles
**Then** the orchestrator respects explicit pinning requests and fills remaining seats automatically

### Story 2.2: Council Orchestration Data

As a host AI orchestrating a council session,
I want to receive structured orchestration prompts, tone guidance, and context management metadata,
So that I can effectively direct the deliberation as chairperson — controlling turns, introducing debate, and managing context across models with varying window sizes.

**Acceptance Criteria:**

**Given** a council is assembled
**When** the orchestration data is returned to the host AI
**Then** it includes chairperson instructions for directing speaking order, introducing debate when positions converge prematurely, and driving toward conclusion

**Given** the orchestration data includes tone guidance
**When** the host AI evaluates the discussion state
**Then** the guidance enables dynamic shifting between adversarial debate and agreement-seeking based on convergence patterns

**Given** the orchestration data includes convergence evaluation guidance
**When** the host AI reviews agent responses after each round
**Then** the guidance supports deciding whether to continue deliberation or drive toward consensus (no fixed round count)

**Given** agent personas are loaded for the council
**When** the persona data is provided to the host AI
**Then** each agent's communication style, principles, and domain expertise are available so agents respond in free-form persona voice

**Given** each model in the council has a `context_window` value in config
**When** the orchestration metadata is returned
**Then** it includes per-model context window sizes so the host AI can implement adaptive context management (full transcript under 50% threshold, summarized above)

### Story 2.3: Council Consensus & Synthesis

As a user who needs a clear outcome from a council session,
I want the orchestrator to drive toward consensus with a structured consensus round and synthesize a detail-preserving narrative addendum,
So that I get actionable recommendations with full reasoning, not just raw opinions.

**Acceptance Criteria:**

**Given** the orchestrator determines the council has sufficiently deliberated
**When** the consensus round begins
**Then** each agent provides a one-sentence endorsement or dissent with their key caveat

**Given** all agents have submitted consensus statements
**When** the orchestrator evaluates agreement
**Then** it drives toward unanimous consensus as the primary goal
**And** falls back to tiered conclusions ("all agree on X, most agree on Y, divided on Z") when full agreement is not achievable

**Given** agents disagree on a domain-specific point
**When** the orchestrator resolves the deadlock
**Then** it weights opinions by domain relevance (e.g., Tax Advisor's tax position outweighs Entrepreneur's tax opinion)
**And** the weighting is reflected transparently in the addendum

**Given** the council reaches conclusion
**When** the orchestrator synthesizes the addendum
**Then** it produces a detail-preserving narrative capturing full reasoning, recommendations, dissenting views, and key caveats
**And** the format prioritizes detail preservation over rigid structure

### Story 2.4: Council History & Output

As a developer or team member,
I want council addendums delivered inline in my conversation AND saved as timestamped markdown files,
So that I can act on recommendations immediately and reference past decisions later.

**Acceptance Criteria:**

**Given** a council session reaches conclusion
**When** the addendum is generated
**Then** it is delivered as dual output — inline response in the MCP conversation AND saved as a markdown file

**Given** the addendum is saved to file
**When** the file is written to `./aicouncil/history/`
**Then** the filename follows the format `YYYY-MM-DD-topic-slug.md`
**And** the file is written atomically to prevent partial output from interrupted sessions
**And** `council/history.py` is the sole module that writes council history files

**Given** a team member opens the `./aicouncil/history/` directory
**When** they read an addendum file
**Then** the markdown narrative is readable by non-technical stakeholders without additional context
**And** the file includes the topic, participating agents, model assignments, and full deliberation narrative

**Given** multiple council sessions have been completed
**When** the history directory is inspected
**Then** all past addendums persist as a project decision log accessible via the file system

### Story 2.5: End-to-End Integration

As a developer running my first council session,
I want the entire council flow to work seamlessly from invocation to addendum output with graceful error handling,
So that I can trust the tool to deliver reliable, high-quality multi-perspective deliberation.

**Acceptance Criteria:**

**Given** the aicouncil server is running with a valid OpenRouter API key and agent roster loaded
**When** a user invokes `ai_council` with a topic
**Then** the full session completes end-to-end: topic classification → agent assembly → model assignment → deliberation data → consensus → addendum (inline + file)

**Given** a model assigned to an agent is unavailable during the session
**When** the OpenRouter client receives an error
**Then** it retries 2-3 times, then reassigns the agent to a different available model from the pool
**And** the council continues with the substitution noted in the output

**Given** the council tool returns a response
**When** the response is inspected
**Then** it is a Pydantic `BaseModel` instance (never a raw dict or string)
**And** error states are returned as structured error responses, not raw tracebacks

**Given** any exception occurs during a council session
**When** the error is handled
**Then** only specific `AiCouncilError` subclasses are used (never broad `Exception`)
**And** the session UUID is included in all error log entries

**Given** the complete system is running
**When** all NFRs are evaluated
**Then** the server adds no meaningful latency beyond request marshaling (NFR1)
**And** assembly completes in a single LLM call (NFR2)
**And** no data is transmitted beyond OpenRouter inference calls (NFR5)
**And** the system is compatible with any MCP-enabled host (NFR13)
