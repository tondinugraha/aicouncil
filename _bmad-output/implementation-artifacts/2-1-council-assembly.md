# Story 2.1: Council Assembly

Status: done

## Story

As a developer seeking multi-perspective advice,
I want to invoke an `ai_council` tool that classifies my topic, selects relevant agents, and assigns models using capability-weighted routing,
so that the council is intelligently composed for my specific question without any manual configuration.

## Acceptance Criteria

1. **Given** a user invokes the `ai_council` MCP tool with a topic
   **When** the tool processes the request
   **Then** it generates a session UUID and includes it in all related log entries
   **And** the tool is registered in `server.py` with logic in `tools/council.py`

2. **Given** a topic is provided
   **When** topic classification runs
   **Then** the system uses a single LLM call to classify the topic into capability domains
   **And** the classification result informs agent selection

3. **Given** the topic is classified
   **When** the council assembler selects agents
   **Then** it balances three factors: topic relevance, category mix (expert/builder/user), and domain coverage breadth
   **And** it includes wildcard agents from unrelated domains at a 5:1 ratio when the topic warrants cross-domain insight

4. **Given** agents are selected
   **When** models are assigned
   **Then** the system uses capability-weighted random routing (60/40 bias toward capability-matched models)
   **And** the same agent persona can be instantiated on multiple different models within a single council

5. **Given** the user includes natural language agent/model preferences in their prompt (e.g., "include a Statistician on GPT 5.2")
   **When** the council assembles
   **Then** the orchestrator respects explicit pinning requests and fills remaining seats automatically

## Tasks / Subtasks

- [x] Task 1: Create council directory structure (AC: #1)
  - [x] Create `src/aicouncil/council/__init__.py`
  - [x] Create `src/aicouncil/council/schemas.py` — council-specific Pydantic models
  - [x] Create `src/aicouncil/council/assembler.py` — agent selection + model assignment logic

- [x] Task 2: Define council Pydantic schemas (AC: #1, #2, #3, #4)
  - [x] `TopicClassification` — domains identified, confidence scores
  - [x] `AgentAssignment` — agent + assigned model + assignment reasoning
  - [x] `CouncilComposition` — full council: assignments, session_id, diversity metrics
  - [x] `CouncilAssemblyResult` — MCP tool return: composition + orchestration prompts + metadata

- [x] Task 3: Implement topic classification (AC: #2)
  - [x] Create classification prompt that maps a topic to capability domains from the config's capability weight domains
  - [x] Single LLM call via `OpenRouterClient.generate()` with structured `TopicClassification` response
  - [x] Return list of relevant domains with confidence scores

- [x] Task 4: Implement agent selection algorithm (AC: #3)
  - [x] Load full agent roster via `get_agents()` from `agent_loader.py`
  - [x] Score agents by domain overlap with classified topic domains
  - [x] Balance category mix: ensure expert + builder + user representation
  - [x] Implement wildcard selection: 5:1 ratio (e.g., for 5 relevant agents include 1 wildcard from unrelated domain)
  - [x] Respect `include_flag` for user-type agents
  - [x] Tier-aware: prefer Tier 1 agents, include Tier 2/3 for domain specificity

- [x] Task 5: Implement capability-weighted model routing (AC: #4)
  - [x] Load model pool from `config.get_model_pool()`
  - [x] Load capability weights from `config.get_capability_weights(model)`
  - [x] For each agent's primary domain, compute model affinity scores
  - [x] 60/40 weighted random: 60% chance of highest-scoring model, 40% distributed across others
  - [x] Support same agent on multiple models (duplicate persona, different model assignment)
  - [x] Include `context_window` metadata per model in assignment output for host AI context management

- [x] Task 6: Implement agent/model pinning from natural language (AC: #5)
  - [x] Parse optional `agents` and `models` parameters from the tool input
  - [x] Match pinned agent names against roster (case-insensitive via `AgentRoster.get_by_name()`)
  - [x] Pin specific models to specific agents when both are specified
  - [x] Fill remaining council seats automatically after pinning

- [x] Task 7: Create `tools/council.py` MCP tool (AC: #1)
  - [x] Define `ai_council` async function with parameters: topic (required), agents (optional list), council_size (optional int), include_user_agents (optional bool), include_wildcard (optional bool), model (optional str)
  - [x] Generate session UUID at start, log with session ID
  - [x] Orchestrate: classify topic → select agents → assign models → compose result
  - [x] Return `CouncilAssemblyResult` Pydantic model
  - [x] Handle errors with `CouncilError`, never expose tracebacks

- [x] Task 8: Register tool in `server.py` (AC: #1)
  - [x] Import `ai_council` from `aicouncil.tools.council`
  - [x] Register with `mcp.tool()(ai_council)` following existing pattern

- [x] Task 9: Write tests (AC: all)
  - [x] `tests/test_council.py` — assembler unit tests
  - [x] Test topic classification with mock LLM responses
  - [x] Test agent selection balancing (category mix, wildcard ratio, tier preference)
  - [x] Test capability-weighted routing distribution
  - [x] Test agent/model pinning
  - [x] Test error handling (empty roster, unavailable model, classification failure)
  - [x] Inject mock Config with test model pool and capability weights

- [x] Task 10: Lint & Format (AC: all)
  - [x] `uv run ruff format .`
  - [x] `uv run ruff check --fix .`
  - [x] `uv run pytest` — all tests pass with zero regressions

## Dev Notes

### Current Codebase State (Post Epic 1)

| Component | Status | Location | Key API |
|-----------|--------|----------|---------|
| Config system | Complete | `src/aicouncil/config.py` | `get_config()`, `Config.get_model_pool()`, `Config.get_capability_weights(model)`, `Config.get_context_window(model)`, `Config.resolve_model()` |
| Agent loader | Complete | `src/aicouncil/agent_loader.py` | `get_agents() → AgentRoster`, `load_all_agents()` |
| Agent schemas | Complete | `src/aicouncil/schemas/agents.py` | `Agent(name, role, type, tier, domains, include_flag, persona)`, `AgentRoster.by_type()`, `.by_tier()`, `.by_domain()`, `.get_by_name()`, `.users(include_flagged_only)` |
| OpenRouter client | Complete | `src/aicouncil/client.py` | `OpenRouterClient.generate(prompt, response_model, context, model)` |
| Exception hierarchy | Complete | `src/aicouncil/exceptions.py` | `CouncilError`, `OpenRouterError`, `ModelUnavailableError` |
| Response schemas | Complete | `src/aicouncil/schemas/responses.py` | Existing tool schemas (no council schemas yet) |
| Server registry | Complete | `src/aicouncil/server.py` | `mcp.tool()()` registration pattern |
| Council directory | **MISSING** | `src/aicouncil/council/` | Must create |
| Council tool | **MISSING** | `src/aicouncil/tools/council.py` | Must create |
| 40 agents loaded | Complete | `src/aicouncil/agents/` | 9 Tier1 + 12 Tier2 + 7 Tier3 experts + 4 builders + 8 users |
| 205 tests passing | Complete | `tests/` | Zero regressions required |

### Architecture — Where Things Go

**Strict boundary rules — DO NOT violate:**

| New File | Responsibility | Depends On |
|----------|---------------|------------|
| `src/aicouncil/council/__init__.py` | Package init | — |
| `src/aicouncil/council/schemas.py` | Council Pydantic models only | `pydantic` |
| `src/aicouncil/council/assembler.py` | Agent selection + model routing logic (NO HTTP calls) | `config.py`, `agent_loader.py`, `council/schemas.py` |
| `src/aicouncil/tools/council.py` | MCP tool function — owns the LLM call for classification, delegates assembly to `assembler.py` | `client.py`, `council/assembler.py`, `council/schemas.py` |
| `server.py` | Add import + registration only | `tools/council.py` |

**DO NOT:**
- Put business logic in `server.py` — it's a registry
- Put business logic in `tools/council.py` — keep it thin, delegate to `council/assembler.py`
- Make HTTP calls outside `client.py`
- Read agent files outside `agent_loader.py`
- Read config outside `config.py`

### Council Schemas Design

```python
# src/aicouncil/council/schemas.py

class TopicClassification(BaseModel):
    """Result of LLM-powered topic classification."""
    topic: str                           # Original topic
    domains: list[str]                   # Identified capability domains
    domain_scores: dict[str, float]      # Domain → confidence (0.0-1.0)
    reasoning: str                       # Why these domains

class AgentAssignment(BaseModel):
    """Single agent with assigned model."""
    agent_name: str                      # Display name
    agent_role: str                      # Role title
    agent_type: str                      # expert/builder/user
    agent_tier: int                      # 1/2/3
    assigned_model: str                  # OpenRouter model ID
    context_window: int | None           # Model context window tokens
    assignment_reasoning: str            # Why this agent + model combo
    is_wildcard: bool = False            # True if wildcard pick
    is_pinned: bool = False              # True if user-requested
    persona: str                         # Full persona Markdown for host AI

class CouncilComposition(BaseModel):
    """Assembled council ready for deliberation."""
    session_id: str                      # UUID for log correlation
    topic: str                           # Original topic
    classification: TopicClassification  # Topic analysis
    assignments: list[AgentAssignment]   # All agent-model pairs
    council_size: int                    # Number of seats
    diversity_metrics: dict[str, Any]    # Category mix, tier spread, model spread

class CouncilAssemblyResult(BaseModel):
    """MCP tool return — everything the host AI needs to orchestrate."""
    composition: CouncilComposition      # Who's on the council
    orchestration_notes: str             # Brief guidance for the host AI
```

### Topic Classification Strategy

The classification prompt must map the user's topic to the domains used in the capability weight matrix. The default config uses these domains: `coding`, `analysis`, `creative`, `business`, `legal`, `finance`.

**Classification prompt structure:**
1. Present the user's topic
2. List available domains from the capability weight config
3. Ask the LLM to score relevance (0.0-1.0) for each domain
4. Return as structured `TopicClassification`

**Important:** Extract domain names dynamically from the config's capability weights. Do NOT hardcode domains — users can customize their config with different domain names.

To extract domains dynamically:
```python
config = get_config()
model_pool = config.get_model_pool()
all_domains: set[str] = set()
for model in model_pool:
    weights = config.get_capability_weights(model)
    if weights:
        all_domains.update(weights.domain_scores().keys())
# all_domains is now {"coding", "analysis", "creative", "business", "legal", "finance"}
```

### Agent Selection Algorithm

**Step 1: Score agents by domain overlap**
- For each agent, compute overlap between agent's `domains` list and classified topic's `domains`
- Score = sum of topic's domain confidence scores for matching domains
- This is a fuzzy match — agent domains (e.g., `system_design`) won't exactly match config domains (e.g., `coding`). Use the classification's domain scores to weight relevance.

**Step 2: Balance category mix**
- Default council size: ~6-8 agents
- Target mix: ~60% experts, ~25% builders, ~15% users (at least 1 of each category if available)
- Tier preference: Tier 1 > Tier 2 > Tier 3 (but Tier 2/3 included if they have higher domain relevance)

**Step 3: Wildcard selection**
- 5:1 ratio: for every 5 relevant picks, include 1 wildcard from unrelated domains
- Wildcard = agent whose domains have ZERO overlap with topic domains
- Provides cross-domain insight per FR6

**Step 4: User agent filtering**
- Respect `include_flag`: only auto-include user agents with `include_flag: true`
- User agents with `include_flag: false` only included if explicitly pinned

### Capability-Weighted Random Routing (60/40)

For each agent assignment:
1. Get the agent's primary domain (first in their domains list, or highest-scored from classification)
2. For each model in `model_pool`, get the domain score from `capability_weights`
3. Sort models by domain score descending
4. 60% probability: assign the top-scoring model
5. 40% probability: assign from remaining models (weighted by their scores)

This ensures capability-matched routing while maintaining model diversity across the council.

```python
import random

def assign_model(agent_domain: str, model_pool: list[str], config: Config) -> str:
    """Capability-weighted random routing with 60/40 bias."""
    scored = []
    for model in model_pool:
        weights = config.get_capability_weights(model)
        score = weights.get_domain_score(agent_domain) if weights else 0.5
        scored.append((model, score or 0.5))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_model = scored[0][0]

    if random.random() < 0.6:
        return top_model

    # 40% — weighted random from all models
    models, weights = zip(*scored)
    return random.choices(models, weights=weights, k=1)[0]
```

### Agent/Model Pinning

The `ai_council` tool accepts optional `agents` parameter (list of agent names). When provided:
1. Look up each name via `AgentRoster.get_by_name(name)` — case-insensitive
2. If found, add to council as pinned (`is_pinned=True`)
3. Log a warning for any names that don't match the roster
4. Fill remaining seats with automatic selection

Model pinning within agent strings (e.g., "Statistician on GPT 5.2") is a stretch goal for this story. The basic implementation accepts agent names; model assignment is automatic. A future enhancement can parse "on <model>" syntax.

### Tool Function Signature

```python
# src/aicouncil/tools/council.py

async def ai_council(
    topic: str,
    agents: list[str] | None = None,
    council_size: int = 7,
    include_user_agents: bool = True,
    include_wildcard: bool = True,
    model: str | None = None,
) -> CouncilAssemblyResult:
    """
    Assemble a multi-agent, multi-model council for deliberation on a topic.

    Classifies the topic, selects relevant agents from the roster,
    assigns models using capability-weighted routing, and returns
    everything the host AI needs to orchestrate the deliberation.

    Args:
        topic: The question or topic for the council to deliberate.
        agents: Optional list of agent names to pin in the council.
        council_size: Target number of agents (default: 7).
        include_user_agents: Include user-perspective agents (default: True).
        include_wildcard: Include wildcard cross-domain agents (default: True).
        model: Override model for the classification LLM call.
    """
```

### OpenRouter Client Usage Pattern

Follow the pattern from existing tools (e.g., `tools/analysis.py`):

```python
config = get_config()
resolved_model = config.resolve_model(tool_name="ai_council", per_invocation=model)
async with OpenRouterClient(model=resolved_model, config=config) as client:
    classification = await client.generate(
        prompt=classification_prompt,
        response_model=TopicClassification,
    )
```

### Logging Pattern

```python
import uuid
import logging

logger = logging.getLogger(__name__)

session_id = str(uuid.uuid4())
logger.info(f"[council:{session_id}] Council session started for topic: {topic[:100]}")
logger.info(f"[council:{session_id}] Topic classified: domains={classification.domains}")
logger.debug(f"[council:{session_id}] Classification scores: {classification.domain_scores}")
logger.info(f"[council:{session_id}] Council assembled: {len(assignments)} agents")
```

### Testing Strategy

**Mock Config for tests:**
```python
# Inject mock config with test model pool and capability weights
mock_config = Config(
    api_key="test-key",
    model_pool=["model-a", "model-b", "model-c"],
    capability_weights={
        "model-a": CapabilityWeight(context_window=100000, coding=0.9, business=0.5),
        "model-b": CapabilityWeight(context_window=200000, coding=0.5, business=0.9),
        "model-c": CapabilityWeight(context_window=150000, coding=0.7, business=0.7),
    },
)
```

**Mock LLM responses for classification:**
- Mock `OpenRouterClient.generate()` to return a pre-built `TopicClassification`
- Test various topic types: technical, business, legal, mixed

**Agent selection tests:**
- Verify category mix (expert + builder + user)
- Verify wildcard inclusion at 5:1 ratio
- Verify tier preference (Tier 1 weighted higher)
- Verify `include_flag` respected
- Verify pinned agents always included

**Model routing tests:**
- Verify 60/40 distribution (run N iterations, check statistical distribution)
- Verify all models from pool are used
- Verify context_window metadata included

### Files to Create

| File | Purpose |
|------|---------|
| `src/aicouncil/council/__init__.py` | Package init (empty or minimal exports) |
| `src/aicouncil/council/schemas.py` | `TopicClassification`, `AgentAssignment`, `CouncilComposition`, `CouncilAssemblyResult` |
| `src/aicouncil/council/assembler.py` | `CouncilAssembler` class — classify, select, route, compose |
| `src/aicouncil/tools/council.py` | `ai_council` MCP tool function |
| `tests/test_council.py` | Assembler + tool tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/aicouncil/server.py` | Import `ai_council` from `tools.council`, register with `mcp.tool()(ai_council)` |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/aicouncil/config.py` | Config is complete — model_pool, capability_weights, cascading defaults all exist |
| `src/aicouncil/agent_loader.py` | Agent system is complete — just consume via `get_agents()` |
| `src/aicouncil/client.py` | OpenRouter client is complete — just use `generate()` |
| `src/aicouncil/exceptions.py` | `CouncilError` already exists |
| `src/aicouncil/schemas/agents.py` | Agent models are complete |
| `src/aicouncil/agents/*.md` | Agent roster is complete (40 agents) |

### Anti-Patterns to Avoid

- **DO NOT** hardcode domain names — extract dynamically from config capability weights
- **DO NOT** put selection/routing logic in `tools/council.py` — delegate to `council/assembler.py`
- **DO NOT** make HTTP calls in `council/assembler.py` — the LLM classification call lives in `tools/council.py`, which passes the `TopicClassification` result into the assembler
- **DO NOT** return raw dicts — all returns must be Pydantic `BaseModel` instances
- **DO NOT** catch broad `Exception` — use `CouncilError` for assembly failures
- **DO NOT** skip session UUID in log entries
- **DO NOT** forget to include agent persona text in assignments — the host AI needs it for deliberation
- **DO NOT** create council history output in this story — that's Story 2.4
- **DO NOT** implement deliberation rounds — that's orchestrated by the host AI using Story 2.2 data
- **DO NOT** implement consensus — that's Story 2.3

### Call Chain (Critical — Resolves Boundary Ownership)

```
tools/council.py:ai_council(topic, ...)
  1. Generate session UUID
  2. config = get_config()
  3. resolved_model = config.resolve_model("ai_council", model)
  4. async with OpenRouterClient(model=resolved_model, config=config) as client:
       classification = await client.generate(prompt, response_model=TopicClassification)
  5. roster = get_agents()
  6. assembler = CouncilAssembler(config=config)
  7. composition = assembler.assemble(classification, roster, council_size, ...)
  8. Return CouncilAssemblyResult(composition=composition, ...)
```

**The tool owns the LLM call. The assembler is pure logic — no I/O.**

### Domain Vocabulary Bridging

Agent domains (e.g., `system_design`, `tax_compliance`) use a different vocabulary than config capability domains (e.g., `coding`, `legal`). The classification prompt must bridge this gap:

1. The classification prompt receives both: (a) config capability domains and (b) the full list of agent domain slugs from the roster
2. The LLM returns scores for config capability domains AND a mapping of which agent domain slugs are relevant to the topic
3. Agent scoring uses the agent-domain-to-topic relevance from the classification, NOT direct string matching

**Alternative simpler approach:** The classification prompt only classifies into config domains. Agent scoring then uses a heuristic mapping:
- Agent domain `system_design` → config domain `coding`
- Agent domain `tax_compliance` → config domain `legal` + `finance`
- If no mapping exists, agent gets a default score of 0.3

Either approach works. The simpler heuristic is recommended for this story — the LLM-based mapping can be enhanced later.

### Edge Cases

- **Empty model pool:** Raise `CouncilError("No models in model pool — check config.yaml")`
- **Roster smaller than council_size:** Use all available matching agents without error. Council can be smaller than requested.
- **No matching agents for topic:** Fall back to Tier 1 agents (universal relevance). If roster is empty, raise `CouncilError`.
- **Wildcard with council_size:** `council_size` is INCLUSIVE of wildcards. For `council_size=7`: ~6 relevant + ~1 wildcard. Apply 5:1 ratio to the relevant count.
- **Zero capability weights for a domain:** Use 0.5 as default score for models missing a domain weight.
- **AC #5 partial scope:** Agent name pinning via `agents` parameter is fully implemented. Natural language "on <model>" syntax parsing is deferred to a future enhancement.

### `orchestration_notes` Content

For this story, `orchestration_notes` is a brief string assembled from the council composition. Example:

```
"Council of 7 agents assembled for topic 'Stripe Connect vs direct charges'.
Domains: business, finance, coding. 4 experts, 2 builders, 1 user perspective.
1 wildcard (Psychologist) for cross-domain insight. Models: 3 unique models assigned.
Host AI should direct deliberation as chairperson — see Story 2.2 for full orchestration prompts."
```

Keep it simple — detailed orchestration guidance is Story 2.2.

### Scope Boundaries

**IN scope for Story 2.1:**
- Topic classification via single LLM call
- Agent selection algorithm (relevance scoring, category mix, wildcard, tier preference)
- Model assignment via capability-weighted random routing (60/40)
- Agent/model pinning from explicit parameters
- Session UUID generation and logging
- MCP tool registration
- Pydantic schemas for all council data
- Tests for all above

**OUT of scope (later stories):**
- Deliberation orchestration prompts (Story 2.2)
- Consensus mechanism (Story 2.3)
- History file output (Story 2.4)
- End-to-end integration (Story 2.5)

### Previous Story Intelligence (Epic 1)

**Key learnings from Epic 1 implementation:**
- Agent loader uses `importlib.resources` for built-in agents — treat it as a read-only API via `get_agents()`
- Config singleton pattern works well — use `get_config()` in production, inject mock in tests
- `OpenRouterClient` supports structured responses via `response_model=SomePydanticModel` — use this for topic classification
- All 205 existing tests must continue to pass — zero regressions
- Domain slug deduplication was done in Story 1.5 — each agent has unique domain coverage
- Tool pattern in `tools/analysis.py` is the reference implementation — follow it exactly for `tools/council.py`

**Git commit patterns:**
```
3d82b9e CR 1-5     (code review fixes)
166b6f2 DS 1-5     (dev story implementation)
cd2cbde CR 1-4     (code review fixes)
```
Pattern: `DS X-Y` for implementation, `CR X-Y` for code review fixes.

### Project Structure After This Story

```
src/aicouncil/
├── council/                     # NEW DIRECTORY
│   ├── __init__.py              # NEW
│   ├── schemas.py               # NEW — Council Pydantic models
│   └── assembler.py             # NEW — Agent selection + model routing
├── tools/
│   ├── council.py               # NEW — ai_council MCP tool
│   ├── analysis.py              # UNCHANGED
│   ├── research.py              # UNCHANGED
│   ├── codebase.py              # UNCHANGED
│   └── memory.py                # UNCHANGED
├── server.py                    # MODIFIED — add council tool registration
└── ...                          # Everything else UNCHANGED
tests/
├── test_council.py              # NEW — assembler + tool tests
└── ...                          # Everything else UNCHANGED
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 2.1 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR1-6, FR17 (Council Assembly requirements)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Council data flow, boundary modules, capability weight matrix]
- [Source: _bmad-output/project-context.md — Tool registration pattern, exception hierarchy, naming conventions]
- [Source: _bmad-output/implementation-artifacts/1-5-agent-roster-authoring.md — Agent roster details, 40 agents, domain deduplication]
- [Source: src/aicouncil/config.py — Config.get_model_pool(), Config.get_capability_weights(), CapabilityWeight.domain_scores()]
- [Source: src/aicouncil/schemas/agents.py — Agent model, AgentRoster query methods]
- [Source: src/aicouncil/client.py — OpenRouterClient.generate(prompt, response_model)]
- [Source: src/aicouncil/tools/analysis.py — Reference tool implementation pattern]
- [Source: src/aicouncil/defaults/default-config.yaml — Default model pool (5 models), capability weight domains]
- [Source: src/aicouncil/server.py — Tool registration pattern: mcp.tool()(function)]
- [Source: src/aicouncil/exceptions.py — CouncilError exists, ready for use]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Implemented all 10 tasks for Story 2.1: Council Assembly
- Created council package: `__init__.py`, `schemas.py`, `assembler.py`
- 4 Pydantic schemas: TopicClassification, AgentAssignment, CouncilComposition, CouncilAssemblyResult
- Classification prompt dynamically extracts domains from config capability weights (not hardcoded)
- Agent selection balances category mix (~60% expert, ~25% builder, ~15% user), respects tier preference and include_flag
- Wildcard selection at 5:1 ratio from unrelated domains
- 60/40 capability-weighted random model routing verified statistically over 1000 iterations
- Agent/model pinning via `agents` parameter with case-insensitive lookup
- Tool registered in server.py following existing pattern
- 36 new tests in test_council.py, 241 total tests passing (0 regressions)
- Ruff format + lint clean

#### CR 2-1: Adversarial Code Review Fixes (14 patches)

3-layer review (Blind Hunter, Edge Case Hunter, Acceptance Auditor) — 22 raw findings triaged to 14 patches, 8 rejected as false positives/handled elsewhere.

- P1: Fixed wildcard ratio from 6:1 to spec-correct 5:1 (`count // 6` → `count // 5`)
- P2: Floored capability weights at 0.01 to prevent `random.choices` crash on all-zero weights
- P3: Guarded `relevant_seats <= 0` — skip category balancing to prevent negative `target_experts`
- P4: Moved empty-topic validation inside `try` block for consistent error handling
- P5: Added `logger.error` with session UUID before `except CouncilError: raise`
- P6: Removed hardcoded "Story 2.2" internal reference from user-visible orchestration notes
- P7: Guarded empty `type_parts` to prevent bare `"."` in orchestration notes
- P8: Standardized topic truncation to `[:100]` (was inconsistent `[:80]` vs `[:100]`)
- P9: Sanitized newlines from topic string in orchestration notes
- P10: Aligned `_compute_diversity_metrics` return type to `dict[str, Any]` (was `dict[str, object]`)
- P11: Normalized unmatched domain bonus to `0.3 / len(domains)` to prevent many-domain agents from outscoring relevant ones
- P12: Added warning log when agent has empty `domains` list (falls back to "general")
- P13: Added `council_size >= 1` validation at assembler entry
- P14: Added debug log when `get_domain_score` returns `None` for a domain/model pair

### Change Log

- 2026-03-21: Implemented Story 2.1 — Council Assembly (all tasks)
- 2026-03-21: CR 2-1 — 14 patches from adversarial code review, 241 tests passing, ruff clean

### File List

New files:
- src/aicouncil/council/__init__.py
- src/aicouncil/council/schemas.py
- src/aicouncil/council/assembler.py
- src/aicouncil/tools/council.py
- tests/test_council.py

Modified files:
- src/aicouncil/server.py (added council tool import + registration)
