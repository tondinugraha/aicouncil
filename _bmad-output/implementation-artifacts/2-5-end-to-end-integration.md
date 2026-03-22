# Story 2.5: End-to-End Integration

Status: ready-for-dev

## Story

As a developer running my first council session,
I want the entire council flow to work seamlessly from invocation to addendum output with graceful error handling,
so that I can trust the tool to deliver reliable, high-quality multi-perspective deliberation.

## Acceptance Criteria

1. **Given** the aicouncil server is running with a valid OpenRouter API key and agent roster loaded
   **When** a user invokes `ai_council` with a topic
   **Then** the full session completes end-to-end: topic classification -> agent assembly -> model assignment -> deliberation data -> consensus -> addendum (inline + file)

2. **Given** a model assigned to an agent is unavailable during the session
   **When** the OpenRouter client receives an error
   **Then** it retries 2-3 times, then reassigns the agent to a different available model from the pool
   **And** the council continues with the substitution noted in the output

3. **Given** the council tool returns a response
   **When** the response is inspected
   **Then** it is a Pydantic `BaseModel` instance (never a raw dict or string)
   **And** error states are returned as structured error responses, not raw tracebacks

4. **Given** any exception occurs during a council session
   **When** the error is handled
   **Then** only specific `AiCouncilError` subclasses are used (never broad `Exception`)
   **And** the session UUID is included in all error log entries

5. **Given** the complete system is running
   **When** all NFRs are evaluated
   **Then** the server adds no meaningful latency beyond request marshaling (NFR1)
   **And** assembly completes in a single LLM call (NFR2)
   **And** no data is transmitted beyond OpenRouter inference calls (NFR5)
   **And** the system is compatible with any MCP-enabled host (NFR13)

## Tasks / Subtasks

- [ ] Task 1: Create integration test module (AC: #1, #3)
  - [ ] Create `tests/test_integration.py`
  - [ ] Test full lifecycle: `ai_council()` -> verify `CouncilAssemblyResult` -> extract metadata -> `save_council_addendum()` -> verify `AddendumSaveResult` -> verify file on disk
  - [ ] Test assembly-to-save data handoff: session_id, topic, agents, model_assignments flow correctly between the two tools
  - [ ] Test file content is self-contained, readable markdown with YAML frontmatter + narrative
  - [ ] Test multiple sequential councils produce distinct history files

- [ ] Task 2: Model unavailability & retry-then-reassign (AC: #2)
  - [ ] Test OpenRouterClient retries 2-3x on transient errors before raising `ModelUnavailableError`
  - [ ] Test that `ai_council` wraps `ModelUnavailableError` in `CouncilError` with session UUID in logs
  - [ ] Test that classification failure after retries produces structured error (not traceback)
  - [ ] Document reassignment pattern: host AI catches model failure during deliberation, invokes `ai_council` again with remaining agents pinned to new models

- [ ] Task 3: Pydantic response validation (AC: #3)
  - [ ] Test `ai_council` returns `CouncilAssemblyResult` (Pydantic BaseModel) — never dict/string
  - [ ] Test `save_council_addendum` returns `AddendumSaveResult` (Pydantic BaseModel) — never dict/string
  - [ ] Test all nested models are proper Pydantic instances: `CouncilComposition`, `OrchestrationData`, `AgentAssignment`, `AddendumMetadata`
  - [ ] Test error states are `CouncilError` exceptions (not raw tracebacks to MCP)

- [ ] Task 4: Error handling coverage across pipeline (AC: #4)
  - [ ] Test empty topic -> `CouncilError("Topic is required")`
  - [ ] Test no capability domains in config -> `CouncilError("No capability domains found")`
  - [ ] Test classification LLM returns invalid response -> `CouncilError("classification failed")`
  - [ ] Test empty agent roster -> `CouncilError` from assembler
  - [ ] Test addendum content > 1MB -> `CouncilError("exceeds maximum size")`
  - [ ] Test file I/O failure -> `CouncilError` (wrapped `OSError`)
  - [ ] Verify ALL errors include session UUID in log entries
  - [ ] Verify no broad `Exception` catch — only specific `AiCouncilError` subclasses

- [ ] Task 5: NFR validation (AC: #5)
  - [ ] Test assembly uses exactly one LLM call (NFR2): mock client, assert `.generate()` called once
  - [ ] Test no HTTP calls outside `client.py` (NFR5): verify httpx is only imported in client module
  - [ ] Test all tool returns are Pydantic models (NFR — structured responses)
  - [ ] Test session UUID correlation: verify session_id from `ai_council` matches what goes into `save_council_addendum`

- [ ] Task 6: Lint, format, run all tests (AC: all)
  - [ ] `uv run ruff format .`
  - [ ] `uv run ruff check --fix .`
  - [ ] `uv run pytest` — all tests pass with zero regressions

## Dev Notes

### Critical Design Decision: Integration Testing Scope

This story validates that the **existing modules wire together correctly** end-to-end. It does NOT build new business logic — all council components (assembly, orchestration, consensus schemas, history) are complete from Stories 2.1-2.4. The story's value is proving the contract between components is solid and errors propagate correctly.

**What "end-to-end" means here:**
The MCP server provides tools and data; the host AI orchestrates deliberation. The server's end-to-end flow is:
1. `ai_council(topic)` -> `CouncilAssemblyResult` (classification + assembly + orchestration data)
2. Host AI conducts deliberation (outside MCP server scope)
3. `save_council_addendum(session_id, topic, agents, models, content)` -> `AddendumSaveResult` (file + inline)

Integration tests validate steps 1 and 3 and the data handoff between them.

**What "retry-then-reassign" means for AC #2:**
The retry logic (2-3x) already exists in `client.py`. The "reassign" part is the HOST AI's responsibility — when a model fails during deliberation, the host AI picks a different model from the pool (available in `config.get_model_pool()`). The MCP server cannot reassign mid-session because it doesn't control deliberation. This story documents this pattern clearly and tests the retry portion.

### Current Codebase State (Post Story 2.4 + CR 2-4)

| Component | Status | Location | Key API |
|-----------|--------|----------|---------|
| Council tool | Complete | `tools/council.py` | `ai_council()` -> `CouncilAssemblyResult` |
| Save tool | Complete | `tools/council.py` | `save_council_addendum()` -> `AddendumSaveResult` |
| Council schemas | Complete | `council/schemas.py` | 20+ Pydantic models (composition, orchestration, consensus, addendum) |
| Council assembler | Complete | `council/assembler.py` | `CouncilAssembler.assemble()`, `.build_orchestration_data()` |
| Council history | Complete | `council/history.py` | `write_council_addendum()` — atomic temp-file + `os.link()` |
| OpenRouter client | Complete | `client.py` | `OpenRouterClient.generate()` — retry 2-3x, structured responses |
| Config system | Complete | `config.py` | `get_config()`, cascading defaults, model pool, capability weights |
| Agent loader | Complete | `agent_loader.py` | `get_agents()` -> `AgentRoster` (dual-directory overlay) |
| Exception hierarchy | Complete | `exceptions.py` | `AiCouncilError` -> `OpenRouterError`/`ModelUnavailableError`/`ConfigError`/`AgentLoadError`/`CouncilError` |
| Scaffold | Complete | `scaffold.py` | `ensure_scaffold()` — creates `./aicouncil/{config.yaml,history/,agents/}` |
| Server registry | Complete | `server.py` | `mcp.tool()(ai_council)`, `mcp.tool()(save_council_addendum)` + 15 other tools |
| Tests | 347 passing | `tests/` | 12 test modules, zero regressions |

### Architecture — Where Things Go

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `tests/test_integration.py` | **End-to-end integration tests** — full council lifecycle, data handoff, error propagation, NFR validation |

**Files NOT to modify:**

Every source module is complete. This story adds tests only — no production code changes.

| File | Why |
|------|-----|
| `src/aicouncil/tools/council.py` | Both tools fully implemented and tested |
| `src/aicouncil/council/assembler.py` | Assembly logic complete |
| `src/aicouncil/council/history.py` | File I/O boundary complete with atomic writes |
| `src/aicouncil/council/schemas.py` | All 20+ Pydantic models complete |
| `src/aicouncil/client.py` | Retry logic (2-3x) already implemented |
| `src/aicouncil/config.py` | Config system complete |
| `src/aicouncil/agent_loader.py` | Agent loading complete |
| `src/aicouncil/server.py` | Tool registration complete |
| `src/aicouncil/exceptions.py` | Exception hierarchy complete |

### Integration Test Strategy

**Test file:** `tests/test_integration.py` — isolated from unit tests.

**Fixture approach:** Reuse existing `conftest.py` fixtures (`mock_config`, `api_key_env`, `reset_singletons`) + add integration-specific fixtures for realistic mock LLM responses and agent rosters.

**Mock boundaries:**
- Mock `OpenRouterClient.generate()` to return pre-built `TopicClassification` (avoids real API calls)
- Mock `get_agents()` to return test fixture agents (avoids reading built-in agent files)
- Use `tmp_path` for file system tests (avoids writing to real project directory)
- Patch `Path.cwd()` -> `tmp_path` for `save_council_addendum` file output

**Key test patterns:**

```python
# tests/test_integration.py

class TestFullCouncilLifecycle:
    """End-to-end: ai_council() -> data handoff -> save_council_addendum() -> file on disk."""

    async def test_assembly_to_save_lifecycle(self, tmp_path, mock_config, ...):
        """Full lifecycle produces valid assembly result and persisted addendum file."""
        # Step 1: Invoke ai_council
        result = await ai_council(topic="Should we adopt microservices?")
        assert isinstance(result, CouncilAssemblyResult)

        # Step 2: Extract data for host AI deliberation (simulated)
        session_id = result.composition.session_id
        topic = result.composition.topic
        agents = [a.agent_name for a in result.composition.assignments]
        model_assignments = {a.agent_name: a.assigned_model for a in result.composition.assignments}

        # Step 3: Save addendum (simulating host AI completion)
        save_result = await save_council_addendum(
            session_id=session_id,
            topic=topic,
            agents=agents,
            model_assignments=model_assignments,
            addendum_content="## Consensus\nThe council recommends...",
        )
        assert isinstance(save_result, AddendumSaveResult)
        assert save_result.metadata.session_id == session_id

        # Step 4: Verify file on disk
        file_path = tmp_path / save_result.file_path
        assert file_path.exists()
        content = file_path.read_text()
        assert "session_id:" in content  # YAML frontmatter
        assert "The council recommends" in content  # Narrative body

    async def test_data_handoff_consistency(self, ...):
        """session_id, topic, agents, models flow correctly between tools."""
        ...

    async def test_multiple_sequential_councils(self, tmp_path, ...):
        """Two councils produce two distinct history files."""
        ...


class TestModelUnavailability:
    """AC #2: Retry then reassign pattern."""

    async def test_client_retries_before_failure(self, ...):
        """OpenRouterClient retries 2-3x on transient errors."""
        ...

    async def test_model_failure_produces_council_error(self, ...):
        """ModelUnavailableError wraps into CouncilError with session UUID."""
        ...

    async def test_classification_failure_structured_error(self, ...):
        """Classification LLM failure returns structured error, not traceback."""
        ...


class TestPydanticResponseValidation:
    """AC #3: All tool returns are Pydantic BaseModel instances."""

    async def test_ai_council_returns_pydantic(self, ...):
        """ai_council returns CouncilAssemblyResult (BaseModel)."""
        ...

    async def test_save_addendum_returns_pydantic(self, ...):
        """save_council_addendum returns AddendumSaveResult (BaseModel)."""
        ...

    async def test_nested_models_are_pydantic(self, ...):
        """All nested objects in assembly result are Pydantic instances."""
        ...


class TestErrorHandlingPipeline:
    """AC #4: Exception hierarchy and session UUID in logs."""

    async def test_empty_topic_raises_council_error(self, ...):
        ...

    async def test_no_domains_raises_council_error(self, ...):
        ...

    async def test_invalid_classification_raises_council_error(self, ...):
        ...

    async def test_oversized_addendum_raises_council_error(self, ...):
        ...

    async def test_file_io_failure_raises_council_error(self, ...):
        ...

    async def test_session_uuid_in_error_logs(self, caplog, ...):
        ...

    async def test_no_broad_exception_catch(self):
        """Verify source code doesn't catch bare Exception."""
        ...


class TestNFRValidation:
    """AC #5: Non-functional requirements."""

    async def test_single_llm_call_for_assembly(self, ...):
        """Assembly uses exactly one LLM call (NFR2)."""
        ...

    async def test_no_http_outside_client(self):
        """No module other than client.py imports httpx (NFR5)."""
        ...

    async def test_session_uuid_correlation(self, ...):
        """session_id from ai_council flows through to save_council_addendum."""
        ...
```

### Previous Story Intelligence (Story 2.4 + CR 2-4)

**Key learnings from Story 2.4 implementation:**
- `save_council_addendum` converts file path to relative via `file_path.relative_to(project_root)` before returning — tests must account for this
- YAML frontmatter values are escaped via `_yaml_escape()` — double quotes, backslashes, newlines
- `AddendumMetadata` has `min_length=1` on `agents` field and ISO 8601 timestamp validation
- `MAX_ADDENDUM_CONTENT_BYTES = 1_048_576` (1 MB) enforced in tool before writing
- Atomic file writes use `os.link()` for TOCTOU safety, capped at 100 disambiguation attempts
- Test count after CR 2-4: 347 total (286 pre-2.4 + 61 history tests)

**Git commit patterns:**
```
785ec1c CR 2-4
ce63e5f DS 2-4
2e039bd CS 2-4
04ca22a CR 2-3
f179d61 DS 2-3
```
Pattern: `CS X-Y` for story creation, `DS X-Y` for implementation, `CR X-Y` for code review.

**CR 2-4 fixes that affect integration tests:**
- P-3: `AddendumMetadata.timestamp` has a `field_validator` rejecting non-ISO strings — tests must pass valid ISO timestamps
- D-2: `save_council_addendum` returns relative path (`aicouncil/history/...`), not absolute — file assertions must use `tmp_path / relative_path`
- D-3: Content > 1MB is rejected — tests should verify this boundary

### Call Chain (Full End-to-End)

```
Host AI calls: ai_council(topic="Should we adopt microservices?")
  |
  v
tools/council.py:ai_council()
  1. Generate session_id (UUID)
  2. get_config() -> Config (model pool, capability weights)
  3. extract_available_domains(config) -> set[str]
  4. build_classification_prompt(topic, domains) -> str
  5. config.resolve_model("ai_council", model) -> str
  6. OpenRouterClient.generate(prompt, TopicClassification) -> TopicClassification
  7. get_agents() -> AgentRoster (dual-directory overlay)
  8. CouncilAssembler(config).assemble(classification, roster, session_id, ...) -> CouncilComposition
  9. assembler.build_orchestration_data(composition) -> OrchestrationData
  10. Return CouncilAssemblyResult(composition, orchestration)
  |
  v
Host AI receives CouncilAssemblyResult via MCP
  - Reads composition.assignments (agent personas, assigned models)
  - Reads orchestration (chairperson, tone, convergence, consensus guidance)
  - Conducts deliberation rounds (outside MCP server)
  - Writes addendum narrative following orchestration.consensus.addendum guidance
  |
  v
Host AI calls: save_council_addendum(session_id, topic, agents, model_assignments, addendum_content)
  |
  v
tools/council.py:save_council_addendum()
  1. Validate content size (<= 1MB)
  2. Generate ISO 8601 timestamp (UTC)
  3. Build AddendumMetadata(session_id, topic, agents, model_assignments, timestamp)
  4. council.history.write_council_addendum(metadata, content, project_root)
     a. Slugify topic -> filename
     b. Format YAML frontmatter + markdown body
     c. Atomic write: tempfile -> os.link() -> cleanup
     d. Return Path
  5. Convert to relative path
  6. Return AddendumSaveResult(file_path, addendum_content, metadata)
  |
  v
Host AI receives AddendumSaveResult via MCP
  - file_path -> reference for future lookup
  - addendum_content -> display inline in conversation
  - File persists at ./aicouncil/history/YYYY-MM-DD-topic-slug.md
```

### Boundary Modules — DO NOT Bypass

| Boundary | Owner | What Integration Tests Should Mock |
|----------|-------|-----------------------------------|
| MCP protocol | `server.py` | Not tested here — we call tool functions directly |
| OpenRouter API | `client.py` | Mock `OpenRouterClient.generate()` — no real API calls |
| Configuration | `config.py` | Inject mock config via dependency injection |
| Agent data | `agent_loader.py` | Mock `get_agents()` to return test fixture roster |
| File output | `council/history.py` | Use `tmp_path` — test real file I/O, mock the directory |

### Anti-Patterns to Avoid

- **DO NOT** make real OpenRouter API calls in tests — mock `client.generate()`
- **DO NOT** read real built-in agent files — mock `get_agents()` with fixture agents
- **DO NOT** write to real project directory — use `tmp_path` (pytest built-in)
- **DO NOT** add production code changes — this story is tests-only
- **DO NOT** catch broad `Exception` in tests — assert specific `CouncilError` or `AiCouncilError` subclasses
- **DO NOT** test MCP transport layer — test tool functions directly
- **DO NOT** test individual module internals — that's done in unit tests (test_council.py, test_history.py, etc.)
- **DO NOT** skip session UUID verification — every error log must include it
- **DO NOT** monkeypatch the config singleton — use constructor injection
- **DO NOT** duplicate existing unit tests — integration tests focus on cross-module contracts

### Scope Boundaries

**IN scope for Story 2.5:**
- Integration tests validating full council lifecycle (assembly -> save -> file)
- Data handoff verification (session_id, topic, agents, models consistent across tools)
- Model unavailability retry behavior validation
- Pydantic response type assertions for all tool returns
- Error propagation across pipeline stages
- NFR validation (single LLM call, no external HTTP beyond client.py, session UUID correlation)

**OUT of scope:**
- New production code (everything is built in Stories 2.1-2.4)
- MCP transport layer testing (FastMCP handles that)
- Host AI deliberation logic (not in MCP server)
- Real OpenRouter API calls (mocked)
- Performance benchmarking (NFR1 validated by architecture, not by load testing)
- Council history indexing/search (post-MVP)

### Project Structure After This Story

```
tests/
├── conftest.py              # UNCHANGED — shared fixtures
├── test_council.py          # UNCHANGED — 81 unit tests
├── test_history.py          # UNCHANGED — 61 unit tests
├── test_config.py           # UNCHANGED — 29 unit tests
├── test_client.py           # UNCHANGED — 16 unit tests
├── test_schemas.py          # UNCHANGED — 21 unit tests
├── test_agent_loader.py     # UNCHANGED — 45+ unit tests
├── test_exceptions.py       # UNCHANGED — 5 unit tests
├── test_scaffold.py         # UNCHANGED — 10+ unit tests
├── test_integration.py      # NEW — end-to-end integration tests (~20-30 tests)
├── test_tools/              # UNCHANGED
│   ├── test_analysis.py
│   ├── test_research.py
│   ├── test_codebase.py
│   └── test_memory.py
└── fixtures/                # UNCHANGED (may add integration-specific fixtures)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 2.5 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR1 (council invocation), FR16 (dual output), NFR1 (no latency overhead), NFR2 (single-call assembly), NFR5 (no external data transmission), NFR7 (model unavailability), NFR13 (MCP host compatibility)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Error Handling: retry-then-reassign pattern, Custom Exception Hierarchy, Boundary Modules ownership table]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data Flow: council session flow diagram (user prompt -> server -> tools -> assembler -> client -> history)]
- [Source: _bmad-output/project-context.md — Exception hierarchy: AiCouncilError subclasses, Pydantic v2 for all tool returns, No raw dicts/strings from MCP tools]
- [Source: src/aicouncil/tools/council.py — ai_council() lines 32-128, save_council_addendum() lines 131-187]
- [Source: src/aicouncil/client.py — OpenRouterClient.generate() with retry logic]
- [Source: src/aicouncil/council/schemas.py — CouncilAssemblyResult, AddendumSaveResult, all 20+ models]
- [Source: src/aicouncil/council/assembler.py — CouncilAssembler.assemble(), .build_orchestration_data()]
- [Source: src/aicouncil/council/history.py — write_council_addendum() with atomic os.link()]
- [Source: src/aicouncil/server.py — tool registration: mcp.tool()(ai_council), mcp.tool()(save_council_addendum)]
- [Source: _bmad-output/implementation-artifacts/2-4-council-history-output.md — Previous story: CR 2-4 fixes (relative paths, content size limit, timestamp validation)]
- [Source: tests/conftest.py — Shared fixtures: mock_config, api_key_env, reset_singletons, valid_config_yaml]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
