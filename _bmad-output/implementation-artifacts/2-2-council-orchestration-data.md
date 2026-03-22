# Story 2.2: Council Orchestration Data

Status: done

## Story

As a host AI orchestrating a council session,
I want to receive structured orchestration prompts, tone guidance, and context management metadata,
so that I can effectively direct the deliberation as chairperson — controlling turns, introducing debate, and managing context across models with varying window sizes.

## Acceptance Criteria

1. **Given** a council is assembled
   **When** the orchestration data is returned to the host AI
   **Then** it includes chairperson instructions for directing speaking order, introducing debate when positions converge prematurely, and driving toward conclusion

2. **Given** the orchestration data includes tone guidance
   **When** the host AI evaluates the discussion state
   **Then** the guidance enables dynamic shifting between adversarial debate and agreement-seeking based on convergence patterns

3. **Given** the orchestration data includes convergence evaluation guidance
   **When** the host AI reviews agent responses after each round
   **Then** the guidance supports deciding whether to continue deliberation or drive toward consensus (no fixed round count)

4. **Given** agent personas are loaded for the council
   **When** the persona data is provided to the host AI
   **Then** each agent's communication style, principles, and domain expertise are available so agents respond in free-form persona voice

5. **Given** each model in the council has a `context_window` value in config
   **When** the orchestration metadata is returned
   **Then** it includes per-model context window sizes so the host AI can implement adaptive context management (full transcript under 50% threshold, summarized above)

## Tasks / Subtasks

- [x] Task 1: Define orchestration Pydantic schemas (AC: #1, #2, #3, #5)
  - [x] Add `ChairpersonInstructions` model to `council/schemas.py`
  - [x] Add `ToneGuidance` model to `council/schemas.py`
  - [x] Add `ConvergenceGuidance` model to `council/schemas.py`
  - [x] Add `ContextWindowInfo` model to `council/schemas.py`
  - [x] Add `OrchestrationData` model to `council/schemas.py` (aggregates all above)
  - [x] Update `CouncilAssemblyResult` to replace `orchestration_notes: str` with `orchestration: OrchestrationData`

- [x] Task 2: Build orchestration data in assembler (AC: #1, #2, #3, #4, #5)
  - [x] Add `build_orchestration_data()` method to `CouncilAssembler`
  - [x] Generate chairperson instructions from council composition (topic, agent roster, domain weights)
  - [x] Generate tone guidance with convergence-aware rules
  - [x] Generate convergence evaluation criteria
  - [x] Compute per-model context window metadata with 50% threshold values
  - [x] Retain backward-compatible `orchestration_notes` as a summary string inside `OrchestrationData`

- [x] Task 3: Update tool to pass orchestration data (AC: all)
  - [x] Update `tools/council.py` to call `build_orchestration_data()` instead of `build_orchestration_notes()`
  - [x] Return `OrchestrationData` in `CouncilAssemblyResult`

- [x] Task 4: Write tests (AC: all)
  - [x] Test `ChairpersonInstructions` schema validation
  - [x] Test `ToneGuidance` schema content
  - [x] Test `ConvergenceGuidance` schema content
  - [x] Test `ContextWindowInfo` per-model calculation (50% threshold)
  - [x] Test `OrchestrationData` composition from council
  - [x] Test `build_orchestration_data()` produces correct structure from various council compositions
  - [x] Test backward-compat: `orchestration_notes` summary string still present
  - [x] Test edge cases: single-agent council, all same model, missing context_window

- [x] Task 5: Lint & Format (AC: all)
  - [x] `uv run ruff format .`
  - [x] `uv run ruff check --fix .`
  - [x] `uv run pytest` — all tests pass with zero regressions

## Dev Notes

### Critical Design Decision: Data, Not Intelligence

**The MCP server provides DATA; the host AI provides INTELLIGENCE.** This story creates structured Pydantic schemas containing orchestration guidance and metadata. It does NOT implement orchestration logic. The host AI (Claude, GPT, etc.) reads this data and uses its own reasoning to conduct the deliberation.

The orchestration data is essentially a well-crafted "chairperson briefing document" — instructions, tone rules, convergence criteria, and context constraints that the host AI interprets and applies dynamically.

### Current Codebase State (Post Story 2.1)

| Component | Status | Location | Key API |
|-----------|--------|----------|---------|
| Council schemas | Complete | `src/aicouncil/council/schemas.py` | `TopicClassification`, `AgentAssignment`, `CouncilComposition`, `CouncilAssemblyResult` |
| Council assembler | Complete | `src/aicouncil/council/assembler.py` | `CouncilAssembler.assemble()`, `.build_orchestration_notes()` |
| Council tool | Complete | `src/aicouncil/tools/council.py` | `ai_council()` — calls assembler, returns `CouncilAssemblyResult` |
| Config system | Complete | `src/aicouncil/config.py` | `Config.get_context_window(model)`, `.get_model_pool()`, `.get_capability_weights(model)` |
| Agent schemas | Complete | `src/aicouncil/schemas/agents.py` | `Agent(name, role, type, tier, domains, include_flag, persona)`, `AgentRoster` |
| Tests | 241 passing | `tests/test_council.py` | 36 council tests + 205 prior tests |

### Architecture — Where Things Go

**Files to modify:**

| File | Change |
|------|--------|
| `src/aicouncil/council/schemas.py` | Add `ChairpersonInstructions`, `ToneGuidance`, `ConvergenceGuidance`, `ContextWindowInfo`, `OrchestrationData` models; update `CouncilAssemblyResult` |
| `src/aicouncil/council/assembler.py` | Add `build_orchestration_data()` method; keep `build_orchestration_notes()` as internal helper for the summary string |
| `src/aicouncil/tools/council.py` | Call `build_orchestration_data()` instead of `build_orchestration_notes()` |
| `tests/test_council.py` | Add orchestration data tests |

**Files NOT to modify:**

| File | Why |
|------|-----|
| `src/aicouncil/server.py` | Tool already registered — no new tools in this story |
| `src/aicouncil/config.py` | `get_context_window(model)` already exists and returns `int \| None` |
| `src/aicouncil/client.py` | No HTTP calls needed — orchestration data is computed locally |
| `src/aicouncil/agent_loader.py` | Agent data already loaded via `get_agents()` |
| `src/aicouncil/exceptions.py` | `CouncilError` already exists |
| `src/aicouncil/schemas/agents.py` | Agent model already has `persona` field with full markdown |

### Schema Design

```python
# All new models go in src/aicouncil/council/schemas.py

class ChairpersonInstructions(BaseModel):
    """Structured instructions for the host AI acting as chairperson."""
    speaking_order: str = Field(
        description="Instructions for managing agent speaking turns"
    )
    debate_triggers: str = Field(
        description="When and how to introduce adversarial debate"
    )
    conclusion_driving: str = Field(
        description="How to drive the council toward conclusion"
    )
    topic_framing: str = Field(
        description="How to frame the topic for the council"
    )

class ToneGuidance(BaseModel):
    """Rules for dynamic tone shifting during deliberation."""
    default_tone: str = Field(
        description="Starting tone for the deliberation"
    )
    adversarial_triggers: str = Field(
        description="Conditions that should trigger adversarial/devil's advocate mode"
    )
    agreement_triggers: str = Field(
        description="Conditions that should trigger agreement-seeking mode"
    )
    tone_shift_rules: str = Field(
        description="Rules for when and how to shift between tones"
    )

class ConvergenceGuidance(BaseModel):
    """Criteria for evaluating when to continue vs. drive toward consensus."""
    evaluation_criteria: str = Field(
        description="How to evaluate whether positions are converging"
    )
    continue_signals: str = Field(
        description="Signals that deliberation should continue"
    )
    consensus_signals: str = Field(
        description="Signals that it's time to drive toward consensus"
    )
    no_fixed_rounds: str = Field(
        description="Reminder: no fixed round count — evaluate dynamically"
    )

class ContextWindowInfo(BaseModel):
    """Per-model context window metadata for adaptive context management."""
    model: str = Field(description="Model identifier")
    context_window: int = Field(description="Total context window in tokens")
    half_window: int = Field(description="50% threshold for context summarization")

class OrchestrationData(BaseModel):
    """Complete orchestration data package for the host AI chairperson."""
    chairperson: ChairpersonInstructions = Field(
        description="Instructions for directing the deliberation"
    )
    tone: ToneGuidance = Field(
        description="Dynamic tone shifting guidance"
    )
    convergence: ConvergenceGuidance = Field(
        description="When to continue vs. drive to consensus"
    )
    context_windows: list[ContextWindowInfo] = Field(
        description="Per-model context window metadata"
    )
    agent_count: int = Field(
        description="Number of agents in the council"
    )
    summary: str = Field(
        description="Brief human-readable orchestration summary"
    )
```

**Updated `CouncilAssemblyResult`:**
```python
class CouncilAssemblyResult(BaseModel):
    """MCP tool return — everything the host AI needs to orchestrate."""
    composition: CouncilComposition
    orchestration: OrchestrationData  # CHANGED from orchestration_notes: str
```

### Chairperson Instructions Content

The chairperson instructions are generated dynamically based on council composition. They should be concise, actionable prompt content — NOT verbose documentation.

**`speaking_order`** — Generated from council composition:
```
"Address agents in rounds. Each round, have every agent respond to the topic or
to the previous round's positions. Vary speaking order between rounds to prevent
anchoring bias. Start with domain experts most relevant to the topic, then builders,
then user perspectives. In subsequent rounds, let dissenters speak first to ensure
minority positions get airtime.

Council: [list agent names with roles, grouped by type]"
```

**`debate_triggers`** — Static guidance with council-specific detail:
```
"Introduce adversarial debate when:
- All agents agree on a position within the first 1-2 rounds (premature convergence)
- A critical domain perspective is not being challenged (e.g., security implications
  not questioned on a technical topic)
- [Domain-specific trigger based on classified topic domains]

Devil's advocate technique: Ask a specific agent to argue the opposite position.
Choose agents whose domain gives them standing to challenge (e.g., ask Security Analyst
to challenge a convenience-first architecture proposal)."
```

**`conclusion_driving`** — Static guidance:
```
"Drive toward conclusion when:
- Key positions are well-established and repeated across agents
- New rounds are producing diminishing novel insights
- Major disagreements have been explored from multiple angles

Conclusion technique: Summarize areas of agreement, then explicitly ask each agent
for a one-sentence final position on remaining disagreements."
```

**`topic_framing`** — Dynamic based on classification:
```
"Topic: '{topic}'
Primary domains: {domains with scores}
Frame this as a {domain1}/{domain2} question. Ensure agents address both the
{domain1} implementation aspects and the {domain2} strategic implications."
```

### Tone Guidance Content

**`default_tone`** — Varies by topic nature:
- If single domain with high score (>0.8): start with "exploratory" — gather diverse perspectives before narrowing
- If multi-domain: start with "structured debate" — each domain expert presents their perspective first
- If safety/security domains present: start with "risk-aware" — prioritize surfacing risks before solutions

**`adversarial_triggers`:**
```
"Shift to adversarial/devil's advocate when:
- More than 2/3 of agents agree on a position before round 3
- A domain expert's core concern is being dismissed by majority
- The topic involves risk/cost tradeoffs where the 'easy' option is being favored
- Wildcard agent raises a cross-domain concern that gets ignored"
```

**`agreement_triggers`:**
```
"Shift to agreement-seeking when:
- Key disagreements have been explored for 2+ rounds
- Agents are repeating positions without new arguments
- A compromise position has been proposed and partially endorsed
- Domain experts in the most relevant domains are aligned"
```

**`tone_shift_rules`:**
```
"- Never stay in adversarial mode for more than 2 consecutive rounds
- Return to exploratory/structured mode after adversarial challenge
- If adversarial mode produces new insights, continue exploring those
- Agreement-seeking is the final phase — once entered, don't revert to adversarial
  unless a genuinely new concern surfaces"
```

### Convergence Guidance Content

**`evaluation_criteria`:**
```
"After each round, evaluate:
1. Position clustering — Are agents grouping into distinct camps, or is there a
   dominant position?
2. Novelty — Did this round surface new arguments, or are agents repeating?
3. Domain alignment — Are the most domain-relevant experts converging?
4. Wildcard insight — Has the wildcard agent contributed a unique perspective?"
```

**`continue_signals`:**
```
"Continue deliberation when:
- New arguments or perspectives emerged in the last round
- A domain expert strongly dissents and hasn't been adequately addressed
- The wildcard agent raised a cross-domain concern that hasn't been explored
- Less than half the council has stated a clear position"
```

**`consensus_signals`:**
```
"Drive toward consensus when:
- Agents are restating previous positions with minor variations
- Domain experts in the primary domains are aligned
- Remaining disagreements are about implementation details, not direction
- 3+ rounds have passed with diminishing novelty per round"
```

**`no_fixed_rounds`:**
```
"There is no fixed round limit. Evaluate dynamically after each round. A simple
topic with early convergence may conclude in 2 rounds. A complex multi-domain
topic with genuine disagreement may run 5+ rounds. Quality of conclusion matters
more than speed."
```

### Context Window Metadata

Computed from `config.get_context_window(model)` for each unique model in the council:

```python
def _build_context_windows(self, composition: CouncilComposition) -> list[ContextWindowInfo]:
    """Build context window metadata for adaptive context management."""
    seen_models: set[str] = set()
    windows: list[ContextWindowInfo] = []
    for assignment in composition.assignments:
        model = assignment.assigned_model
        if model in seen_models:
            continue
        seen_models.add(model)
        cw = assignment.context_window
        if cw is not None:
            windows.append(ContextWindowInfo(
                model=model,
                context_window=cw,
                half_window=cw // 2,
            ))
    return windows
```

The host AI uses `half_window` to decide when to summarize prior context:
- Below 50% utilization → send full transcript to the model
- Above 50% utilization → send summarized context

This is per-model — a model with 200K context can receive full transcripts longer than a model with 100K context.

### `build_orchestration_data()` Method

```python
def build_orchestration_data(self, composition: CouncilComposition) -> OrchestrationData:
    """Build complete orchestration data from the assembled council."""
    # Reuse existing summary builder
    summary = self.build_orchestration_notes(composition)

    chairperson = self._build_chairperson_instructions(composition)
    tone = self._build_tone_guidance(composition)
    convergence = self._build_convergence_guidance()
    context_windows = self._build_context_windows(composition)

    return OrchestrationData(
        chairperson=chairperson,
        tone=tone,
        convergence=convergence,
        context_windows=context_windows,
        agent_count=len(composition.assignments),
        summary=summary,
    )
```

### Tool Update

The change in `tools/council.py` is minimal:

```python
# BEFORE (Story 2.1):
orchestration_notes = assembler.build_orchestration_notes(composition)
return CouncilAssemblyResult(
    composition=composition,
    orchestration_notes=orchestration_notes,
)

# AFTER (Story 2.2):
orchestration = assembler.build_orchestration_data(composition)
return CouncilAssemblyResult(
    composition=composition,
    orchestration=orchestration,
)
```

### Call Chain (Updated)

```
tools/council.py:ai_council(topic, ...)
  1. Generate session UUID
  2. config = get_config()
  3. Classify topic via OpenRouterClient.generate()
  4. roster = get_agents()
  5. assembler = CouncilAssembler(config=config)
  6. composition = assembler.assemble(classification, roster, ...)
  7. orchestration = assembler.build_orchestration_data(composition)  # CHANGED
  8. Return CouncilAssemblyResult(composition=composition, orchestration=orchestration)
```

**The assembler remains pure logic — no I/O.** All orchestration data is computed from the composition and config, not from external calls.

### Testing Strategy

**Existing test fixtures reuse:** Use the same `mock_config`, `sample_classification`, and `sample_roster` fixtures from Story 2.1 tests.

**New tests to add:**

```python
# Schema validation tests
def test_chairperson_instructions_fields():
    """All ChairpersonInstructions fields are non-empty strings."""

def test_tone_guidance_fields():
    """All ToneGuidance fields are non-empty strings."""

def test_convergence_guidance_fields():
    """All ConvergenceGuidance fields are non-empty strings."""

def test_context_window_info_half_calculation():
    """ContextWindowInfo.half_window is exactly context_window // 2."""

# Builder tests
def test_build_orchestration_data_returns_orchestration_data(mock_config, ...):
    """build_orchestration_data() returns OrchestrationData type."""

def test_orchestration_data_includes_summary(mock_config, ...):
    """OrchestrationData.summary contains council composition summary."""

def test_orchestration_context_windows_unique_models(mock_config, ...):
    """context_windows has one entry per unique model (no duplicates)."""

def test_orchestration_context_windows_50_percent_threshold(mock_config, ...):
    """Each ContextWindowInfo.half_window == context_window // 2."""

def test_orchestration_agent_count_matches_composition(mock_config, ...):
    """OrchestrationData.agent_count matches composition.council_size."""

def test_chairperson_mentions_agent_names(mock_config, ...):
    """Chairperson instructions reference actual agent names from council."""

def test_topic_framing_includes_domains(mock_config, ...):
    """topic_framing references the classified domains."""

def test_tone_default_varies_by_topic(mock_config, ...):
    """Default tone adapts based on classification domain scores."""

# Edge case tests
def test_orchestration_single_agent_council(mock_config, ...):
    """Orchestration works for single-agent council (council_size=1)."""

def test_orchestration_all_same_model(mock_config, ...):
    """context_windows has one entry when all agents use same model."""

def test_orchestration_missing_context_window(mock_config, ...):
    """Models with None context_window are excluded from context_windows list."""

# Backward compatibility
def test_council_assembly_result_has_orchestration(mock_config, ...):
    """CouncilAssemblyResult.orchestration is OrchestrationData type."""
```

**Mock pattern — same as Story 2.1:**
```python
assembler = CouncilAssembler(config=mock_config)
composition = assembler.assemble(
    classification=sample_classification,
    roster=sample_roster,
    session_id="test-session",
    council_size=5,
)
orchestration = assembler.build_orchestration_data(composition)
assert isinstance(orchestration, OrchestrationData)
```

### Anti-Patterns to Avoid

- **DO NOT** implement deliberation rounds — the host AI does that using the orchestration data
- **DO NOT** implement consensus logic — that's Story 2.3
- **DO NOT** make HTTP calls in orchestration data building — this is pure local computation
- **DO NOT** hardcode model names in context window logic — use `config.get_context_window()`
- **DO NOT** return raw dicts — all returns must be Pydantic model instances
- **DO NOT** make orchestration text overly verbose — the host AI needs concise, actionable guidance, not documentation
- **DO NOT** create separate files for prompt templates — the orchestration content is built in `assembler.py` methods
- **DO NOT** break existing tests — the `build_orchestration_notes()` method stays as internal helper; `CouncilAssemblyResult` schema change requires updating existing tests that assert on `orchestration_notes`
- **DO NOT** implement council history output — that's Story 2.4

### Breaking Change: `CouncilAssemblyResult` Schema

`CouncilAssemblyResult.orchestration_notes: str` is replaced by `orchestration: OrchestrationData`. This requires updating:

1. **`assembler.py`** — `build_orchestration_data()` replaces `build_orchestration_notes()` as the public API (keep `build_orchestration_notes()` as a private helper called internally)
2. **`tools/council.py`** — Pass `orchestration=` instead of `orchestration_notes=`
3. **`tests/test_council.py`** — Update any assertions that reference `result.orchestration_notes` to `result.orchestration.summary`

The summary string content is preserved inside `OrchestrationData.summary` for backward compatibility with any host AI that was consuming the notes.

### Scope Boundaries

**IN scope for Story 2.2:**
- Orchestration Pydantic schemas (`ChairpersonInstructions`, `ToneGuidance`, `ConvergenceGuidance`, `ContextWindowInfo`, `OrchestrationData`)
- `build_orchestration_data()` method on `CouncilAssembler`
- Chairperson instructions content generated from composition
- Tone guidance content with dynamic default tone
- Convergence evaluation criteria content
- Per-model context window metadata with 50% threshold
- Updated `CouncilAssemblyResult` schema
- Tests for all above

**OUT of scope (later stories):**
- Actual deliberation execution (host AI responsibility)
- Consensus mechanism and consensus round (Story 2.3)
- Addendum synthesis (Story 2.3)
- History file output (Story 2.4)
- End-to-end integration (Story 2.5)

### Previous Story Intelligence (Story 2.1)

**Key learnings from Story 2.1 implementation:**
- `CouncilAssembler` is pure logic — no I/O, no HTTP calls. Story 2.2 follows the same pattern.
- `build_orchestration_notes()` already exists and produces a summary string — reuse it inside `build_orchestration_data()` for the `summary` field.
- Existing tests use `mock_config` with 3 test models (model-a/b/c) and capability weights — reuse these fixtures.
- CR 2-1 fixed 14 issues including topic sanitization (P8), empty type_parts guard (P7), and `orchestration_notes` content cleanup (P6) — the `build_orchestration_notes()` method is already clean.
- 241 tests currently passing — zero regressions required.
- `AgentAssignment` already carries `persona: str` (full persona markdown) and `context_window: int | None` — AC #4 (persona data) is already satisfied by the existing composition data. The orchestration data provides instructions for *how* to use the personas, not the personas themselves.

**Git commit patterns:**
```
0d3d759 CR 2-1     (code review fixes)
8d2aa96 DS 2-1     (dev story implementation)
```
Pattern: `DS X-Y` for implementation, `CR X-Y` for code review fixes.

### Project Structure After This Story

```
src/aicouncil/
├── council/
│   ├── __init__.py              # UNCHANGED
│   ├── schemas.py               # MODIFIED — add 5 orchestration schemas, update CouncilAssemblyResult
│   └── assembler.py             # MODIFIED — add build_orchestration_data() + helper methods
├── tools/
│   ├── council.py               # MODIFIED — call build_orchestration_data()
│   └── ...                      # UNCHANGED
└── ...                          # UNCHANGED
tests/
├── test_council.py              # MODIFIED — add orchestration data tests, update existing assertions
└── ...                          # UNCHANGED
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 2.2 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR7 (chairperson), FR8 (tone), FR9 (convergence), FR10 (persona voice), FR11 (adaptive context)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Intelligence boundary: host AI orchestrates, server provides data]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data flow: council session flow diagram]
- [Source: _bmad-output/project-context.md — Rule: "Host AI is the orchestrator — MCP server provides tools, data, and config"]
- [Source: src/aicouncil/council/schemas.py — Current CouncilAssemblyResult with orchestration_notes: str]
- [Source: src/aicouncil/council/assembler.py — CouncilAssembler.build_orchestration_notes(), CouncilAssembler.assemble()]
- [Source: src/aicouncil/tools/council.py — ai_council() tool function, current call chain]
- [Source: src/aicouncil/config.py — Config.get_context_window(model) returns int | None]
- [Source: _bmad-output/implementation-artifacts/2-1-council-assembly.md — Previous story learnings, CR 2-1 patches]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- ✅ Task 1: Added 5 Pydantic schemas (`ChairpersonInstructions`, `ToneGuidance`, `ConvergenceGuidance`, `ContextWindowInfo`, `OrchestrationData`) to `council/schemas.py`. Updated `CouncilAssemblyResult` to use `orchestration: OrchestrationData` replacing `orchestration_notes: str`.
- ✅ Task 2: Added `build_orchestration_data()` + 4 private helpers (`_build_chairperson_instructions`, `_build_tone_guidance`, `_build_convergence_guidance`, `_build_context_windows`) to `CouncilAssembler`. Chairperson instructions dynamically reference agent roster. Tone defaults vary by topic (exploratory/structured debate/risk-aware). Context windows deduplicate models and compute 50% threshold. Summary field reuses existing `_build_orchestration_notes()`.
- ✅ Task 3: Updated `tools/council.py` to call `build_orchestration_data()` and pass `orchestration=` to `CouncilAssemblyResult`.
- ✅ Task 4: Added 20 new tests (56 total council tests): schema validation, builder integration, tone variation by topic type, edge cases (single-agent, all-same-model, missing context window), backward compatibility. Updated 2 existing tests for new schema.
- ✅ Task 5: Ruff format + lint clean. 261/261 tests pass, zero regressions.

### Change Log

- 2026-03-22: Story 2.2 implementation complete — orchestration data schemas, assembler methods, tool update, and comprehensive tests.
- 2026-03-22: CR 2-2 fixes applied — 5 patches from code review: (1) `ContextWindowInfo.half_window` converted to `computed_field` enforced by schema; (2) empty-domains fallback in `topic_framing`/`debate_triggers`; (3) `context_window=0` excluded from context_windows list; (4) `build_orchestration_notes` renamed to `_build_orchestration_notes` (private per spec intent); (5) `logger.warning` for unknown agent types in speaking order. 261/261 tests pass.

### File List

- `src/aicouncil/council/schemas.py` — Added 5 orchestration Pydantic models, updated `CouncilAssemblyResult`; `ContextWindowInfo.half_window` is a `computed_field`
- `src/aicouncil/council/assembler.py` — Added `build_orchestration_data()` + 4 private builder methods; `build_orchestration_notes` renamed to `_build_orchestration_notes`; empty-domains and zero-context-window guards added; unknown agent type warning
- `src/aicouncil/tools/council.py` — Updated to call `build_orchestration_data()`
- `tests/test_council.py` — Added 20 new orchestration data tests, updated 4 existing tests (schema change + private method rename)
