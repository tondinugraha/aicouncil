# Story 2.3: Council Consensus & Synthesis

Status: ready-for-dev

## Story

As a user who needs a clear outcome from a council session,
I want the orchestrator to drive toward consensus with a structured consensus round and synthesize a detail-preserving narrative addendum,
so that I get actionable recommendations with full reasoning, not just raw opinions.

## Acceptance Criteria

1. **Given** the orchestrator determines the council has sufficiently deliberated
   **When** the consensus round begins
   **Then** each agent provides a one-sentence endorsement or dissent with their key caveat

2. **Given** all agents have submitted consensus statements
   **When** the orchestrator evaluates agreement
   **Then** it drives toward unanimous consensus as the primary goal
   **And** falls back to tiered conclusions ("all agree on X, most agree on Y, divided on Z") when full agreement is not achievable

3. **Given** agents disagree on a domain-specific point
   **When** the orchestrator resolves the deadlock
   **Then** it weights opinions by domain relevance (e.g., Tax Advisor's tax position outweighs Entrepreneur's tax opinion)
   **And** the weighting is reflected transparently in the addendum

4. **Given** the council reaches conclusion
   **When** the orchestrator synthesizes the addendum
   **Then** it produces a detail-preserving narrative capturing full reasoning, recommendations, dissenting views, and key caveats
   **And** the format prioritizes detail preservation over rigid structure

## Tasks / Subtasks

- [ ] Task 1: Define consensus & synthesis Pydantic schemas (AC: #1, #2, #3, #4)
  - [ ] Add `ConsensusRoundGuidance` model to `council/schemas.py`
  - [ ] Add `AgentDomainWeight` model to `council/schemas.py`
  - [ ] Add `DeadlockResolutionGuidance` model to `council/schemas.py`
  - [ ] Add `TieredConsensusGuidance` model to `council/schemas.py`
  - [ ] Add `AddendumGuidance` model to `council/schemas.py`
  - [ ] Add `ConsensusAndSynthesisData` model to `council/schemas.py` (aggregates all above)
  - [ ] Update `OrchestrationData` to include `consensus: ConsensusAndSynthesisData` field

- [ ] Task 2: Build consensus data in assembler (AC: #1, #2, #3, #4)
  - [ ] Add `_build_consensus_round_guidance()` to `CouncilAssembler`
  - [ ] Add `_compute_agent_domain_weights()` to `CouncilAssembler`
  - [ ] Add `_build_deadlock_resolution_guidance()` to `CouncilAssembler`
  - [ ] Add `_build_tiered_consensus_guidance()` to `CouncilAssembler`
  - [ ] Add `_build_addendum_guidance()` to `CouncilAssembler`
  - [ ] Wire all into `build_orchestration_data()` as the new `consensus` field

- [ ] Task 3: Write tests (AC: all)
  - [ ] Test `ConsensusRoundGuidance` schema validation
  - [ ] Test `AgentDomainWeight` computation correctness
  - [ ] Test `DeadlockResolutionGuidance` references agent names and weights
  - [ ] Test `TieredConsensusGuidance` contains tiered structure rules
  - [ ] Test `AddendumGuidance` includes all required sections
  - [ ] Test `ConsensusAndSynthesisData` composition
  - [ ] Test `OrchestrationData.consensus` is populated after `build_orchestration_data()`
  - [ ] Test domain weights are normalized and sum meaningfully per agent
  - [ ] Test domain weights reflect classification domains (high score = high weight)
  - [ ] Test edge cases: single-agent council, all agents same domain, no matching domains, all-zero weights

- [ ] Task 4: Lint & Format (AC: all)
  - [ ] `uv run ruff format .`
  - [ ] `uv run ruff check --fix .`
  - [ ] `uv run pytest` — all tests pass with zero regressions

## Dev Notes

### Critical Design Decision: Data, Not Intelligence (Same as Story 2.2)

**The MCP server provides DATA; the host AI provides INTELLIGENCE.** This story creates Pydantic schemas containing consensus guidance, domain weights, and addendum format instructions. It does NOT implement actual consensus evaluation or addendum writing. The host AI reads this data and uses its reasoning to conduct the consensus round, resolve deadlocks, and write the addendum.

The consensus data is a "chairperson's consensus playbook" — rules for how to run the consensus round, how to weight opinions, and how to structure the final output.

### Current Codebase State (Post Story 2.2)

| Component | Status | Location | Key API |
|-----------|--------|----------|---------|
| Council schemas | Complete | `src/aicouncil/council/schemas.py` | `TopicClassification`, `AgentAssignment`, `CouncilComposition`, `CouncilAssemblyResult`, `OrchestrationData` (with chairperson, tone, convergence, context_windows) |
| Council assembler | Complete | `src/aicouncil/council/assembler.py` | `CouncilAssembler.assemble()`, `.build_orchestration_data()`, private helpers for chairperson/tone/convergence/context_windows |
| Council tool | Complete | `src/aicouncil/tools/council.py` | `ai_council()` — calls assembler, returns `CouncilAssemblyResult` |
| Config system | Complete | `src/aicouncil/config.py` | `Config.get_context_window(model)`, `.get_model_pool()`, `.get_capability_weights(model)` returns `CapabilityWeight` with `get_domain_score(domain)` and `domain_scores()` |
| Agent schemas | Complete | `src/aicouncil/schemas/agents.py` | `Agent(name, role, type, tier, domains, include_flag, persona)`, `AgentRoster` |
| OpenRouter client | Complete | `src/aicouncil/client.py` | `OpenRouterClient.generate(prompt, response_model, context, model)` |
| Tests | 261 passing | `tests/test_council.py` | ~90 council tests + ~170 prior tests |

### Architecture — Where Things Go

**Files to modify:**

| File | Change |
|------|--------|
| `src/aicouncil/council/schemas.py` | Add 6 consensus/synthesis schemas; update `OrchestrationData` with `consensus` field |
| `src/aicouncil/council/assembler.py` | Add 5 private builder methods; wire into `build_orchestration_data()` |
| `tests/test_council.py` | Add consensus data tests |

**Files NOT to modify:**

| File | Why |
|------|-----|
| `src/aicouncil/server.py` | No new tools — extending existing data |
| `src/aicouncil/tools/council.py` | `build_orchestration_data()` already called — it returns the updated `OrchestrationData` automatically |
| `src/aicouncil/client.py` | No HTTP calls — consensus data is computed locally |
| `src/aicouncil/config.py` | `get_capability_weights(model)` and `CapabilityWeight.get_domain_score(domain)` already exist |
| `src/aicouncil/agent_loader.py` | Agent data already loaded |
| `src/aicouncil/exceptions.py` | `CouncilError` already exists |
| `src/aicouncil/council/history.py` | Does not exist yet — that's Story 2.4 |

### Schema Design

All new models go in `src/aicouncil/council/schemas.py`:

```python
class ConsensusRoundGuidance(BaseModel):
    """Instructions for conducting the one-sentence consensus round."""
    format_instructions: str = Field(
        description="How each agent should state their consensus position"
    )
    unanimity_goal: str = Field(
        description="Instructions for driving toward unanimous agreement"
    )
    dissent_handling: str = Field(
        description="How to handle and document dissenting positions"
    )

class AgentDomainWeight(BaseModel):
    """Per-agent domain relevance weight for deadlock resolution."""
    agent_name: str = Field(description="Agent name")
    agent_role: str = Field(description="Agent role for context")
    relevance_score: float = Field(
        description="0.0-1.0 domain relevance to this topic",
        ge=0.0,
        le=1.0,
    )
    matched_domains: list[str] = Field(
        description="Agent domains that overlap with topic domains"
    )

class DeadlockResolutionGuidance(BaseModel):
    """Rules for resolving disagreements using domain-weighted opinions."""
    resolution_rules: str = Field(
        description="How to apply domain weights when agents disagree"
    )
    transparency_rules: str = Field(
        description="How to reflect weighting transparently in the addendum"
    )
    agent_weights: list[AgentDomainWeight] = Field(
        description="Per-agent domain relevance weights for this council"
    )

class TieredConsensusGuidance(BaseModel):
    """Rules for tiered consensus when unanimity is not achievable."""
    tier_definitions: str = Field(
        description="Definitions: 'all agree on X', 'most agree on Y', 'divided on Z'"
    )
    escalation_rules: str = Field(
        description="When to accept tiered consensus vs. continue pushing for unanimity"
    )

class AddendumGuidance(BaseModel):
    """Format and content guidance for the detail-preserving narrative addendum."""
    structure: str = Field(
        description="Recommended sections and narrative flow for the addendum"
    )
    detail_preservation_rules: str = Field(
        description="Rules for preserving reasoning detail over rigid structure"
    )
    dissent_inclusion_rules: str = Field(
        description="How to include dissenting views and minority positions"
    )

class ConsensusAndSynthesisData(BaseModel):
    """Complete consensus & synthesis guidance for the host AI."""
    consensus_round: ConsensusRoundGuidance = Field(
        description="How to run the one-sentence consensus round"
    )
    deadlock_resolution: DeadlockResolutionGuidance = Field(
        description="Domain-weighted deadlock resolution with per-agent weights"
    )
    tiered_consensus: TieredConsensusGuidance = Field(
        description="Rules for tiered fallback when unanimity fails"
    )
    addendum: AddendumGuidance = Field(
        description="Format guidance for the narrative addendum"
    )
```

**Updated `OrchestrationData`:**
```python
class OrchestrationData(BaseModel):
    """Complete orchestration data package for the host AI chairperson."""
    chairperson: ChairpersonInstructions
    tone: ToneGuidance
    convergence: ConvergenceGuidance
    consensus: ConsensusAndSynthesisData  # NEW — Story 2.3
    context_windows: list[ContextWindowInfo]
    agent_count: int
    summary: str
```

### Domain Weight Computation

The domain weights bridge the `TopicClassification.domain_scores` with each `AgentAssignment.agent.domains` to produce per-agent relevance:

```python
def _compute_agent_domain_weights(
    self,
    composition: CouncilComposition,
) -> list[AgentDomainWeight]:
    """Compute per-agent domain relevance from topic classification and agent domains."""
    topic_domains = composition.topic.domain_scores  # dict[str, float]
    weights: list[AgentDomainWeight] = []
    for assignment in composition.assignments:
        agent_domains = set(assignment.domains)
        topic_domain_keys = set(topic_domains.keys())
        matched = agent_domains & topic_domain_keys
        # Relevance = average of matched domain scores, or 0 if no match
        if matched and topic_domain_keys:
            relevance = sum(topic_domains[d] for d in matched) / len(topic_domain_keys)
        else:
            relevance = 0.0
        weights.append(AgentDomainWeight(
            agent_name=assignment.agent_name,
            agent_role=assignment.agent_role,
            relevance_score=round(min(relevance, 1.0), 2),
            matched_domains=sorted(matched),
        ))
    return weights
```

**Key design choices:**
- Relevance is based on how many topic domains the agent covers, weighted by those domains' classification scores
- Normalization: divide by total topic domain count (not matched count) so agents covering more topic domains score higher
- Wildcard agents (no matching domains) get `relevance_score: 0.0` — their value is acknowledged as cross-domain perspective, not domain authority
- Weights are for deadlock resolution only — not for filtering who speaks

### Consensus Round Guidance Content

**`format_instructions`:**
```
"Conduct a final consensus round. Ask each agent for exactly one sentence:
their position (endorse or dissent) and their single most important caveat.

Format per agent: '[Agent Name]: [Endorse/Dissent] — [One key caveat]'

Example:
'Tax Advisor: Endorse — but only if quarterly filings are automated'
'Security Engineer: Dissent — custom JWT creates unacceptable PCI exposure'

Collect ALL agent statements before evaluating consensus."
```

**`unanimity_goal`:**
```
"Primary goal is unanimous consensus. Before accepting dissent:
1. Ask dissenters if the majority position addresses their core concern
2. Propose a compromise that incorporates the dissenter's caveat
3. If the dissenter's concern is domain-specific and the domain experts agree
   it's addressed, note the original dissent but record practical consensus

Only fall back to tiered consensus after genuine attempts at unanimity."
```

**`dissent_handling`:**
```
"Dissent is valuable, not a failure. When recording dissent:
- State the dissenter's position clearly and charitably
- Note their domain authority on the point of disagreement
- Explain why the majority position was adopted despite the dissent
- Preserve the dissenting argument in the addendum for future reference"
```

### Deadlock Resolution Content

**`resolution_rules`:**
```
"When agents disagree on a domain-specific point, weight opinions by domain relevance:
- Higher relevance_score = greater authority on the specific point
- A domain expert's position on their domain outweighs a generalist's opinion
- Equal relevance agents: consider the strength of their reasoning, not just the score
- Cross-domain concerns (wildcard agents) are noted but don't override domain authority

Agent domain weights for this council:
[Dynamic: list agent_name (relevance_score) — matched_domains]"
```

**`transparency_rules`:**
```
"Domain weighting must be transparent in the addendum:
- When a position is adopted based on domain authority, state this explicitly
  (e.g., 'The Tax Advisor's position on 1099-K reporting is given priority as
  the most domain-relevant perspective')
- When weighting resolves a tie, list the weights that informed the decision
- Never silently dismiss a position — always explain the resolution"
```

### Tiered Consensus Content

**`tier_definitions`:**
```
"When unanimity is not achievable, structure conclusions in tiers:

Tier 1 — Universal Agreement: Positions ALL agents endorse.
  Prefix: 'The council unanimously recommends...'

Tier 2 — Strong Majority: Positions most agents endorse (>2/3).
  Prefix: 'The majority of the council recommends...'
  Include: count of endorsements, note dissenters by name and domain

Tier 3 — Divided: Positions where the council is split.
  Prefix: 'The council is divided on...'
  Include: both positions with supporting agents, domain-weighted assessment
  of which position has stronger domain authority"
```

**`escalation_rules`:**
```
"Accept tiered consensus when:
- 2+ attempts at unanimity have been made with specific compromise proposals
- Dissenters have domain authority that makes their position non-dismissible
- The disagreement is genuinely substantive (not a misunderstanding)

Continue pushing for unanimity when:
- The disagreement stems from different information, not different values
- A compromise hasn't been explicitly proposed yet
- Domain experts haven't been asked to evaluate the point of disagreement"
```

### Addendum Guidance Content

**`structure`:**
```
"The addendum is a detail-preserving narrative. Recommended flow:

1. TOPIC & CONTEXT: What was asked and why it matters
2. COUNCIL COMPOSITION: Who participated, their domains, and model assignments
3. KEY POSITIONS: The major positions that emerged during deliberation,
   with the reasoning behind each
4. POINTS OF DEBATE: Where agents disagreed and how those debates unfolded
5. CONSENSUS: The conclusion — unanimous or tiered — with clear recommendations
6. DISSENTING VIEWS: Any positions that weren't adopted, preserved with reasoning
7. KEY CAVEATS: Conditions, risks, or assumptions underlying the recommendation

This is a narrative, not a template. Adapt the structure to fit the actual
deliberation. A simple topic with quick consensus may skip section 4.
A complex multi-domain topic may have extensive sections 3-6."
```

**`detail_preservation_rules`:**
```
"The addendum must preserve reasoning, not just conclusions:
- Include WHY each position was held, not just WHAT it was
- Include the specific arguments that shifted positions during debate
- Include quantitative details (costs, timelines, metrics) when agents cited them
- When domain experts provided specialized insight, preserve the technical detail
- Detail > brevity. A 2000-word addendum that captures the full deliberation
  is better than a 200-word summary that loses the reasoning."
```

**`dissent_inclusion_rules`:**
```
"Dissenting views are first-class content in the addendum:
- Every dissent appears in the addendum, attributed to the agent by name and role
- The dissenter's strongest argument is stated in their own voice/style
- Domain-weighted context is provided (how relevant is this agent to the point?)
- The addendum explicitly states whether the dissent was overruled by
  domain authority, majority vote, or compromise
- Future-proofing: note if a dissenting position could become relevant
  under different circumstances"
```

### Integration into `build_orchestration_data()`

The change to `build_orchestration_data()` is additive:

```python
def build_orchestration_data(self, composition: CouncilComposition) -> OrchestrationData:
    """Build complete orchestration data from the assembled council."""
    summary = self._build_orchestration_notes(composition)
    chairperson = self._build_chairperson_instructions(composition)
    tone = self._build_tone_guidance(composition)
    convergence = self._build_convergence_guidance()
    context_windows = self._build_context_windows(composition)
    consensus = self._build_consensus_and_synthesis(composition)  # NEW

    return OrchestrationData(
        chairperson=chairperson,
        tone=tone,
        convergence=convergence,
        consensus=consensus,  # NEW
        context_windows=context_windows,
        agent_count=len(composition.assignments),
        summary=summary,
    )
```

The new `_build_consensus_and_synthesis()` method composes the sub-builders:

```python
def _build_consensus_and_synthesis(
    self, composition: CouncilComposition
) -> ConsensusAndSynthesisData:
    """Build consensus round guidance and addendum format instructions."""
    agent_weights = self._compute_agent_domain_weights(composition)
    return ConsensusAndSynthesisData(
        consensus_round=self._build_consensus_round_guidance(),
        deadlock_resolution=self._build_deadlock_resolution_guidance(agent_weights),
        tiered_consensus=self._build_tiered_consensus_guidance(),
        addendum=self._build_addendum_guidance(),
    )
```

### Testing Strategy

**Existing fixtures reuse:** Same `mock_config`, `sample_classification`, and `sample_roster` from Story 2.1/2.2 tests.

**New tests to add:**

```python
# Schema validation tests
def test_consensus_round_guidance_fields():
    """All ConsensusRoundGuidance fields are non-empty strings."""

def test_agent_domain_weight_validation():
    """AgentDomainWeight relevance_score is clamped 0.0-1.0."""

def test_agent_domain_weight_rejects_out_of_range():
    """AgentDomainWeight rejects relevance_score > 1.0 or < 0.0."""

def test_deadlock_resolution_guidance_has_weights():
    """DeadlockResolutionGuidance.agent_weights is a non-empty list."""

def test_tiered_consensus_guidance_fields():
    """All TieredConsensusGuidance fields are non-empty strings."""

def test_addendum_guidance_fields():
    """All AddendumGuidance fields are non-empty strings."""

# Domain weight computation tests
def test_domain_weights_reflect_classification(mock_config, sample_classification, sample_roster):
    """Agents with domains matching classification get higher relevance_score."""

def test_domain_weights_wildcard_agent_gets_zero(mock_config, sample_classification, sample_roster):
    """Wildcard agents (no matching domains) get relevance_score 0.0."""

def test_domain_weights_full_overlap_agent(mock_config, sample_classification, sample_roster):
    """Agent whose domains fully cover topic domains gets highest score."""

def test_domain_weights_no_matching_domains(mock_config, ...):
    """Agent with zero domain overlap gets relevance_score 0.0."""

def test_domain_weights_partial_overlap(mock_config, ...):
    """Agent matching some topic domains gets proportional score."""

def test_domain_weights_all_agents_present(mock_config, sample_classification, sample_roster):
    """agent_weights list has one entry per agent in composition."""

# Integration tests
def test_orchestration_data_has_consensus(mock_config, sample_classification, sample_roster):
    """OrchestrationData.consensus is ConsensusAndSynthesisData type."""

def test_consensus_deadlock_references_agent_names(mock_config, ...):
    """deadlock_resolution.agent_weights references actual agent names from council."""

def test_consensus_addendum_mentions_narrative(mock_config, ...):
    """addendum.structure mentions 'narrative' — not template-based."""

# Edge case tests
def test_consensus_single_agent_council(mock_config, ...):
    """Consensus guidance works for single-agent council (no deadlock possible)."""

def test_consensus_all_same_domain(mock_config, ...):
    """Domain weights are meaningful when all agents share the same domain."""

def test_consensus_no_domain_overlap(mock_config, ...):
    """All agents get 0.0 relevance when no domains match classification."""
```

**Mock pattern — same as Story 2.1/2.2:**
```python
assembler = CouncilAssembler(config=mock_config)
composition = assembler.assemble(
    classification=sample_classification,
    roster=sample_roster,
    session_id="test-session",
    council_size=5,
)
orchestration = assembler.build_orchestration_data(composition)
assert isinstance(orchestration.consensus, ConsensusAndSynthesisData)
assert len(orchestration.consensus.deadlock_resolution.agent_weights) == 5
```

### Anti-Patterns to Avoid

- **DO NOT** implement actual consensus evaluation — the host AI does that using the guidance data
- **DO NOT** implement addendum writing/file output — that's Story 2.4
- **DO NOT** make HTTP calls — all consensus data is computed locally from composition + classification
- **DO NOT** track deliberation state (rounds, positions) — the server is stateless
- **DO NOT** create `council/history.py` — that boundary module is Story 2.4
- **DO NOT** return raw dicts — all returns must be Pydantic model instances
- **DO NOT** break existing tests — the `OrchestrationData` schema change (adding `consensus` field) requires updating existing orchestration tests that construct `OrchestrationData` directly
- **DO NOT** make consensus guidance overly verbose — concise, actionable prompt content the host AI can reason about
- **DO NOT** hardcode agent names in guidance text — use composition data dynamically
- **DO NOT** modify `tools/council.py` — `build_orchestration_data()` is already called and returns the updated `OrchestrationData` automatically
- **DO** guard against empty `topic_domain_keys` in domain weight computation (ZeroDivisionError) — same defensive pattern as CR 2-2's empty-domains fallback

### Breaking Change: `OrchestrationData` Schema

`OrchestrationData` gains a new required field `consensus: ConsensusAndSynthesisData`. This requires updating:

1. **`schemas.py`** — Add `consensus` field to `OrchestrationData`
2. **`assembler.py`** — Wire `_build_consensus_and_synthesis()` into `build_orchestration_data()`
3. **`tests/test_council.py`** — Update any tests that construct `OrchestrationData` directly (they'll need the new `consensus` field)

Existing tests that receive `OrchestrationData` from `build_orchestration_data()` should pass without change since the method will now produce the field.

For tests that construct `OrchestrationData` directly, create a helper fixture:
```python
def _minimal_consensus_data() -> ConsensusAndSynthesisData:
    """Minimal ConsensusAndSynthesisData for tests that don't focus on consensus."""
    return ConsensusAndSynthesisData(
        consensus_round=ConsensusRoundGuidance(
            format_instructions="test", unanimity_goal="test", dissent_handling="test"
        ),
        deadlock_resolution=DeadlockResolutionGuidance(
            resolution_rules="test", transparency_rules="test", agent_weights=[]
        ),
        tiered_consensus=TieredConsensusGuidance(
            tier_definitions="test", escalation_rules="test"
        ),
        addendum=AddendumGuidance(
            structure="test", detail_preservation_rules="test", dissent_inclusion_rules="test"
        ),
    )
```

### Call Chain (Unchanged from Story 2.2)

```
tools/council.py:ai_council(topic, ...)
  1. Generate session UUID
  2. config = get_config()
  3. Classify topic via OpenRouterClient.generate()
  4. roster = get_agents()
  5. assembler = CouncilAssembler(config=config)
  6. composition = assembler.assemble(classification, roster, ...)
  7. orchestration = assembler.build_orchestration_data(composition)  # now includes consensus
  8. Return CouncilAssemblyResult(composition=composition, orchestration=orchestration)
```

**No changes to `tools/council.py` needed.** The assembler's `build_orchestration_data()` method returns the updated `OrchestrationData` which now includes the `consensus` field. The tool function is unchanged.

### Scope Boundaries

**IN scope for Story 2.3:**
- Consensus Pydantic schemas (`ConsensusRoundGuidance`, `AgentDomainWeight`, `DeadlockResolutionGuidance`, `TieredConsensusGuidance`, `AddendumGuidance`, `ConsensusAndSynthesisData`)
- Domain weight computation from classification + agent domains
- `_build_consensus_and_synthesis()` and sub-builders on `CouncilAssembler`
- Updated `OrchestrationData` with `consensus` field
- Tests for all above

**OUT of scope (later stories):**
- Actual deliberation execution (host AI responsibility)
- Addendum file writing to `./aicouncil/history/` (Story 2.4)
- Dual output delivery — inline + file (Story 2.4)
- End-to-end integration testing (Story 2.5)

### Previous Story Intelligence (Story 2.2)

**Key learnings from Story 2.2 implementation:**
- `build_orchestration_data()` is the single aggregation point — add new builders and wire them in. Same pattern for consensus.
- Existing private helpers follow the pattern: `_build_X(composition) -> XModel`. Follow exactly.
- `ContextWindowInfo.half_window` was converted to a `computed_field` in CR 2.2. Consider if any consensus fields need computed properties (likely not — domain weights are computed at build time, not at access time).
- Story 2.2 added 20 tests (261 total). Story 2.3 should add ~15-20 tests following the same patterns.
- CR 2-2 fixed: empty-domains fallback, zero-context-window guard, `_build_orchestration_notes` made private, unknown agent type warning. Apply similar defensive patterns to domain weight computation (handle empty domains, zero scores).
- `AgentAssignment` already carries `domains: list[str]` and `agent_name: str` and `agent_role: str` — all data needed for `AgentDomainWeight` is available on the composition.
- `TopicClassification.domain_scores: dict[str, float]` is already on `composition.topic` — no additional data loading needed.

**Git commit patterns:**
```
5a12893 CR 2-2
ad01a2f CS 2-2
0d3d759 CR 2-1
8d2aa96 DS 2-1
```
Pattern: `DS X-Y` for implementation, `CR X-Y` for code review, `CS X-Y` for story creation.

### Project Structure After This Story

```
src/aicouncil/
├── council/
│   ├── __init__.py              # UNCHANGED
│   ├── schemas.py               # MODIFIED — add 6 consensus/synthesis schemas, update OrchestrationData
│   └── assembler.py             # MODIFIED — add _build_consensus_and_synthesis() + 5 private helpers
├── tools/
│   ├── council.py               # UNCHANGED — build_orchestration_data() already called
│   └── ...                      # UNCHANGED
└── ...                          # UNCHANGED
tests/
├── test_council.py              # MODIFIED — add consensus data tests, update existing OrchestrationData assertions
└── ...                          # UNCHANGED
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 2.3 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR12 (consensus round), FR13 (tiered consensus), FR14 (domain-weighted deadlocks), FR15 (detail-preserving addendum)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Intelligence boundary: host AI orchestrates, server provides data]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data flow: council session flow diagram]
- [Source: _bmad-output/project-context.md — Rule: "Host AI is the orchestrator — MCP server provides tools, data, and config"]
- [Source: src/aicouncil/council/schemas.py — Current OrchestrationData with chairperson, tone, convergence, context_windows]
- [Source: src/aicouncil/council/assembler.py — CouncilAssembler.build_orchestration_data(), private builder pattern]
- [Source: src/aicouncil/council/schemas.py — TopicClassification.domain_scores, AgentAssignment.domains]
- [Source: src/aicouncil/config.py — CapabilityWeight.get_domain_score(domain)]
- [Source: _bmad-output/implementation-artifacts/2-2-council-orchestration-data.md — Previous story learnings, CR 2-2 patches, builder pattern]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### Change Log

### File List
