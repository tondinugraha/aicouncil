# Story 2.4: Council History & Output

Status: review

## Story

As a developer or team member,
I want council addendums delivered inline in my conversation AND saved as timestamped markdown files,
so that I can act on recommendations immediately and reference past decisions later.

## Acceptance Criteria

1. **Given** a council session reaches conclusion
   **When** the addendum is generated
   **Then** it is delivered as dual output — inline response in the MCP conversation AND saved as a markdown file

2. **Given** the addendum is saved to file
   **When** the file is written to `./aicouncil/history/`
   **Then** the filename follows the format `YYYY-MM-DD-topic-slug.md`
   **And** the file is written atomically to prevent partial output from interrupted sessions
   **And** `council/history.py` is the sole module that writes council history files

3. **Given** a team member opens the `./aicouncil/history/` directory
   **When** they read an addendum file
   **Then** the markdown narrative is readable by non-technical stakeholders without additional context
   **And** the file includes the topic, participating agents, model assignments, and full deliberation narrative

4. **Given** multiple council sessions have been completed
   **When** the history directory is inspected
   **Then** all past addendums persist as a project decision log accessible via the file system

## Tasks / Subtasks

- [x] Task 1: Define history & output Pydantic schemas (AC: #1, #2, #3)
  - [x] Add `AddendumMetadata` model to `council/schemas.py`
  - [x] Add `AddendumSaveResult` model to `council/schemas.py` (MCP tool return type)

- [x] Task 2: Create `council/history.py` boundary module (AC: #2, #3, #4)
  - [x] Create `src/aicouncil/council/history.py`
  - [x] Implement `_slugify_topic(topic: str) -> str` helper
  - [x] Implement `_generate_filename(topic: str, timestamp: datetime | None = None) -> str` (format: `YYYY-MM-DD-topic-slug.md`)
  - [x] Implement `_format_addendum_markdown(metadata: AddendumMetadata, addendum_content: str) -> str`
  - [x] Implement `write_council_addendum(metadata: AddendumMetadata, addendum_content: str, project_root: Path | None = None) -> Path` with atomic writes
  - [x] Update `council/__init__.py` to export `write_council_addendum`

- [x] Task 3: Add `save_council_addendum` MCP tool (AC: #1, #2)
  - [x] Add `save_council_addendum()` async function to `tools/council.py`
  - [x] Register tool in `server.py` via `mcp.tool()(save_council_addendum)`

- [x] Task 4: Write tests (AC: all)
  - [x] Test `_slugify_topic` with various inputs (spaces, special chars, unicode, long strings)
  - [x] Test `_generate_filename` produces `YYYY-MM-DD-topic-slug.md` format
  - [x] Test `_format_addendum_markdown` includes metadata header (topic, agents, models, session_id)
  - [x] Test `write_council_addendum` creates file in correct directory
  - [x] Test `write_council_addendum` writes atomically (temp file + rename pattern)
  - [x] Test `write_council_addendum` handles missing `history/` directory (creates it)
  - [x] Test `write_council_addendum` wraps `OSError` in `CouncilError`
  - [x] Test `AddendumSaveResult` schema validation
  - [x] Test `save_council_addendum` tool returns `AddendumSaveResult` with file path and inline content
  - [x] Test duplicate filenames (same topic, same day) get disambiguated
  - [x] Test edge cases: empty addendum content, very long topic strings, topics with only special chars

- [x] Task 5: Lint & Format (AC: all)
  - [x] `uv run ruff format .`
  - [x] `uv run ruff check --fix .`
  - [x] `uv run pytest` — all tests pass with zero regressions

## Dev Notes

### Critical Design Decision: New MCP Tool for Host AI Callback

The host AI is the orchestrator. The MCP server provided assembly data (Stories 2.1-2.3). Now the host AI has conducted deliberation, run the consensus round, and synthesized the addendum narrative. It needs a way to **send the finished addendum back** to the MCP server for file persistence.

This requires a **new MCP tool**: `save_council_addendum`. This tool:
1. Accepts the addendum narrative content from the host AI
2. Accepts council metadata (session_id, topic, agents, models) so the file is self-contained
3. Writes the file atomically via `council/history.py`
4. Returns the addendum content (for inline display) + the file path (for reference)

**The tool does NOT write the addendum content** — the host AI writes it. The tool persists it.

### Current Codebase State (Post Story 2.3 + CR 2-3)

| Component | Status | Location | Key API |
|-----------|--------|----------|---------|
| Council schemas | Complete | `council/schemas.py` | `CouncilAssemblyResult`, `OrchestrationData` (with consensus), `CouncilComposition`, `AgentAssignment` |
| Council assembler | Complete | `council/assembler.py` | `CouncilAssembler.assemble()`, `.build_orchestration_data()` |
| Council tool | Complete | `tools/council.py` | `ai_council()` — returns `CouncilAssemblyResult` |
| Council history | **DOES NOT EXIST** | `council/history.py` | **Create in this story** |
| Config system | Complete | `config.py` | `get_config()`, `Config` singleton, project root via `Path.cwd()` |
| Scaffold | Complete | `scaffold.py` | `ensure_scaffold()` — creates `./aicouncil/history/` directory |
| Exceptions | Complete | `exceptions.py` | `CouncilError` for history I/O failures |
| Server registry | Complete | `server.py` | `mcp.tool()(ai_council)` — add new tool registration here |
| Tests | 286 passing | `tests/test_council.py` | Council tests with `mock_config`, `sample_classification`, `sample_roster` fixtures |

### Architecture — Where Things Go

**Files to CREATE:**

| File | Purpose |
|------|---------|
| `src/aicouncil/council/history.py` | **Sole boundary module for council history file output** — atomic writes, filename generation, markdown formatting |

**Files to MODIFY:**

| File | Change |
|------|--------|
| `src/aicouncil/council/schemas.py` | Add `AddendumMetadata` and `AddendumSaveResult` schemas |
| `src/aicouncil/tools/council.py` | Add `save_council_addendum()` tool function |
| `src/aicouncil/server.py` | Register `save_council_addendum` tool |
| `src/aicouncil/council/__init__.py` | Export `write_council_addendum` |
| `tests/test_council.py` | Add history module tests |

**Files NOT to modify:**

| File | Why |
|------|-----|
| `src/aicouncil/council/assembler.py` | Assembly logic is complete — no changes needed |
| `src/aicouncil/client.py` | No HTTP calls — history is local file I/O |
| `src/aicouncil/config.py` | Project root resolution pattern already exists — reuse `Path.cwd()` |
| `src/aicouncil/scaffold.py` | Already creates `./aicouncil/history/` directory |
| `src/aicouncil/exceptions.py` | `CouncilError` already exists — use it for I/O failures |
| `src/aicouncil/agent_loader.py` | Agent data already loaded |

### Schema Design

**New schemas in `council/schemas.py`:**

```python
class AddendumMetadata(BaseModel):
    """Metadata for a council addendum file header."""
    session_id: str = Field(description="Council session UUID")
    topic: str = Field(description="Original topic provided by user")
    agents: list[str] = Field(description="Agent names that participated")
    model_assignments: dict[str, str] = Field(
        description="Mapping of agent name to assigned model"
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp of council completion"
    )

class AddendumSaveResult(BaseModel):
    """Result from saving a council addendum — returned by save_council_addendum tool."""
    file_path: str = Field(description="Path to the saved addendum file")
    addendum_content: str = Field(
        description="Full addendum narrative for inline display"
    )
    metadata: AddendumMetadata = Field(
        description="Council session metadata embedded in the file"
    )
```

### Atomic File Write Pattern

Use Python stdlib — no new dependencies:

```python
import tempfile
from pathlib import Path

def write_council_addendum(
    metadata: AddendumMetadata,
    addendum_content: str,
    project_root: Path | None = None,
) -> Path:
    root = project_root or Path.cwd()
    history_dir = root / "aicouncil" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    filename = _generate_filename(metadata.topic, ...)
    target_path = history_dir / filename

    content = _format_addendum_markdown(metadata, addendum_content)

    # Atomic write: temp file in same directory, then rename
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=history_dir,
        delete=False,
        encoding="utf-8",
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    tmp_path.replace(target_path)  # Atomic on POSIX
    return target_path
```

**Key design choices:**
- Temp file in same directory as target = same filesystem = atomic rename guaranteed on POSIX
- `history_dir.mkdir(parents=True, exist_ok=True)` — defensive, in case scaffold hasn't run
- Wrap all `OSError` in `CouncilError` for consistent error hierarchy
- No new dependencies — `tempfile` and `pathlib` are stdlib

### Filename Generation

```python
def _slugify_topic(topic: str) -> str:
    """Convert topic to URL-safe slug for filename."""
    # Lowercase, replace non-alphanumeric with hyphens, collapse multiple hyphens, trim
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    # Truncate to reasonable length (50 chars max for filename portion)
    return slug[:50].rstrip("-")

def _generate_filename(topic: str, timestamp: datetime | None = None) -> str:
    """Generate timestamped filename: YYYY-MM-DD-topic-slug.md"""
    ts = timestamp or datetime.now()
    date_str = ts.strftime("%Y-%m-%d")
    slug = _slugify_topic(topic)
    if not slug:
        slug = "council-session"
    return f"{date_str}-{slug}.md"
```

**Duplicate handling:** If file already exists (same topic, same day), append a numeric suffix: `YYYY-MM-DD-topic-slug-2.md`. Check existence before writing.

### Addendum Markdown Format

The file must be self-contained and readable by non-technical stakeholders:

```markdown
---
session_id: abc-123-def
topic: "Stripe Connect vs Direct Charges"
date: 2026-03-22
agents:
  - name: Payment Systems Architect
    model: openai/gpt-5.2
  - name: Backend Developer
    model: google/gemini-2.5-pro
---

# Council Addendum: Stripe Connect vs Direct Charges

**Date:** 2026-03-22
**Session:** abc-123-def
**Participating Agents:** Payment Systems Architect (GPT 5.2), Backend Developer (Gemini 2.5 Pro), ...

---

[Host AI's full addendum narrative goes here — the content passed to save_council_addendum]
```

YAML frontmatter = machine-parseable metadata. Markdown body = human-readable narrative.

### MCP Tool: `save_council_addendum`

```python
@mcp.tool()
async def save_council_addendum(
    session_id: str,
    topic: str,
    agents: list[str],
    model_assignments: dict[str, str],
    addendum_content: str,
) -> AddendumSaveResult:
    """Save a council addendum as a timestamped markdown file and return it for inline display.

    Call this tool after conducting the council deliberation and synthesizing
    the addendum narrative. The addendum content should be the full narrative
    following the guidance in orchestration.consensus.addendum.
    """
```

**Registration in `server.py`:**
```python
from aicouncil.tools.council import ai_council, save_council_addendum
mcp.tool()(save_council_addendum)
```

### Logging

Follow existing council tool patterns:
- **INFO:** `[council:{session_id}] Saving addendum to {file_path}`
- **INFO:** `[council:{session_id}] Addendum saved successfully ({size} bytes)`
- **DEBUG:** `[council:{session_id}] Addendum metadata: {metadata}`
- **ERROR:** `[council:{session_id}] Failed to write addendum: {error}`
- **WARNING:** `[council:{session_id}] History directory missing, creating: {path}`

### Testing Strategy

**Existing fixtures reuse:** Same `mock_config` from prior council tests. History tests need `tmp_path` (pytest built-in) for isolated filesystem testing.

**New test file consideration:** History tests could go in `tests/test_council.py` (alongside existing council tests) or a new `tests/test_history.py`. Since `council/history.py` is a distinct boundary module, a **separate `tests/test_history.py`** is cleaner and avoids bloating the 1558-line `test_council.py` further.

**Test patterns:**

```python
# tests/test_history.py

def test_slugify_basic():
    assert _slugify_topic("Stripe Connect vs Direct") == "stripe-connect-vs-direct"

def test_slugify_special_chars():
    assert _slugify_topic("What's the best API?!") == "what-s-the-best-api"

def test_slugify_long_topic():
    result = _slugify_topic("a" * 100)
    assert len(result) <= 50

def test_slugify_empty():
    assert _slugify_topic("") == ""

def test_generate_filename_format():
    result = _generate_filename("test topic", datetime(2026, 3, 22))
    assert result == "2026-03-22-test-topic.md"

def test_generate_filename_empty_topic():
    result = _generate_filename("!!!", datetime(2026, 3, 22))
    assert result == "2026-03-22-council-session.md"

def test_write_addendum_creates_file(tmp_path):
    metadata = AddendumMetadata(...)
    path = write_council_addendum(metadata, "test content", project_root=tmp_path)
    assert path.exists()
    assert path.name.endswith(".md")

def test_write_addendum_atomic(tmp_path):
    """No .tmp files left after successful write."""
    metadata = AddendumMetadata(...)
    write_council_addendum(metadata, "content", project_root=tmp_path)
    tmp_files = list((tmp_path / "aicouncil" / "history").glob("*.tmp"))
    assert len(tmp_files) == 0

def test_write_addendum_creates_history_dir(tmp_path):
    """Creates history/ if it doesn't exist."""
    metadata = AddendumMetadata(...)
    path = write_council_addendum(metadata, "content", project_root=tmp_path)
    assert (tmp_path / "aicouncil" / "history").is_dir()

def test_write_addendum_includes_metadata(tmp_path):
    """File content includes YAML frontmatter with session metadata."""
    metadata = AddendumMetadata(session_id="test-123", topic="Test", ...)
    path = write_council_addendum(metadata, "narrative", project_root=tmp_path)
    content = path.read_text()
    assert "session_id: test-123" in content
    assert "narrative" in content

def test_write_addendum_wraps_os_error(tmp_path):
    """OSError during write is wrapped in CouncilError."""
    # Make history dir read-only to trigger OSError
    ...

def test_duplicate_filename_disambiguated(tmp_path):
    """Second file with same topic/date gets numeric suffix."""
    metadata = AddendumMetadata(...)
    path1 = write_council_addendum(metadata, "first", project_root=tmp_path)
    path2 = write_council_addendum(metadata, "second", project_root=tmp_path)
    assert path1 != path2
    assert "-2" in path2.name
```

### Anti-Patterns to Avoid

- **DO NOT** write files from any module other than `council/history.py` — it is the sole file output boundary
- **DO NOT** use direct `Path.write_text()` — use atomic temp-file-then-rename pattern
- **DO NOT** return raw dicts or strings from the MCP tool — return `AddendumSaveResult` Pydantic model
- **DO NOT** catch broad `Exception` — catch `OSError` and wrap in `CouncilError`
- **DO NOT** implement addendum narrative writing — the host AI writes the narrative; this tool persists it
- **DO NOT** make HTTP calls — history is purely local file I/O
- **DO NOT** hardcode paths — use `project_root or Path.cwd()` pattern (matches `config.py` and `scaffold.py`)
- **DO NOT** import or call `history.py` from `assembler.py` — assembler is pure logic, no I/O
- **DO NOT** modify `assembler.py` or `config.py` — everything needed already exists
- **DO NOT** skip session_id in log entries — all council-related logs must include it
- **DO** handle the case where `./aicouncil/history/` doesn't exist (create it defensively)
- **DO** handle duplicate filenames with numeric suffix disambiguation
- **DO** clean up temp files on error (use try/finally around the rename)

### Previous Story Intelligence (Story 2.3 + CR 2-3)

**Key learnings from Story 2.3 implementation:**
- `build_orchestration_data()` is the main aggregation point — Story 2.4 does NOT touch it
- `CouncilAssemblyResult` already carries all composition + orchestration data — the save tool needs session_id + topic + agents from this
- `AgentAssignment` has `agent_name`, `agent_role`, `assigned_model`, `domains` — extract agent/model info from composition
- `AddendumGuidance` (in `orchestration.consensus.addendum`) already describes the narrative structure the host AI should follow — the save tool receives the result of following that guidance
- Story 2.3 added `domains` field to `AgentAssignment` and case-normalized domain matching in CR 2-3
- Story 2.3 test count: 286 total passing. This story should add ~15-20 tests in a new `tests/test_history.py`

**Git commit patterns:**
```
04ca22a CR 2-3
f179d61 DS 2-3
22e34f4 CS 1-2
5a12893 CR 2-2
```
Pattern: `DS X-Y` for implementation, `CR X-Y` for code review, `CS X-Y` for story creation.

### Call Chain

```
Host AI finishes deliberation and writes addendum narrative
  ↓
Host AI calls save_council_addendum(session_id, topic, agents, model_assignments, addendum_content)
  ↓
tools/council.py:save_council_addendum()
  1. Build AddendumMetadata from parameters
  2. Call council.history.write_council_addendum(metadata, addendum_content)
  3. Return AddendumSaveResult(file_path, addendum_content, metadata)
  ↓
council/history.py:write_council_addendum()
  1. Resolve project_root → history_dir
  2. Generate filename from topic + timestamp
  3. Format markdown (YAML frontmatter + narrative body)
  4. Atomic write: tempfile → rename
  5. Return file path
  ↓
Host AI receives AddendumSaveResult
  - file_path → reference for future lookup
  - addendum_content → display inline in conversation
```

### Scope Boundaries

**IN scope for Story 2.4:**
- `council/history.py` — the boundary module (file I/O)
- `AddendumMetadata` and `AddendumSaveResult` Pydantic schemas
- `save_council_addendum` MCP tool in `tools/council.py`
- Tool registration in `server.py`
- Atomic file writes with temp-file-then-rename
- Filename generation (`YYYY-MM-DD-topic-slug.md`)
- Markdown formatting with YAML frontmatter
- Tests for all above

**OUT of scope (later stories / host AI responsibility):**
- Writing the addendum narrative content (host AI does this)
- Council deliberation execution (host AI responsibility)
- End-to-end integration testing (Story 2.5)
- Council history indexing/search (post-MVP)
- Cross-council referencing (post-MVP)

### Project Structure After This Story

```
src/aicouncil/
├── council/
│   ├── __init__.py              # MODIFIED — export write_council_addendum
│   ├── schemas.py               # MODIFIED — add AddendumMetadata, AddendumSaveResult
│   ├── assembler.py             # UNCHANGED
│   └── history.py               # NEW — sole file output boundary module
├── tools/
│   ├── council.py               # MODIFIED — add save_council_addendum tool
│   └── ...                      # UNCHANGED
├── server.py                    # MODIFIED — register save_council_addendum
└── ...                          # UNCHANGED
tests/
├── test_council.py              # UNCHANGED (or minimal update if fixtures shared)
├── test_history.py              # NEW — history module tests
└── ...                          # UNCHANGED
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md — Story 2.4 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR16 (dual output), FR34 (timestamped filenames), FR35 (narrative markdown), FR36 (persistent decision log)]
- [Source: _bmad-output/planning-artifacts/architecture.md — File Output Boundary: council/history.py owns all council history file writing]
- [Source: _bmad-output/planning-artifacts/architecture.md — NFR8: Addendum files written atomically]
- [Source: _bmad-output/planning-artifacts/architecture.md — Council History: YYYY-MM-DD-topic-slug.md format]
- [Source: _bmad-output/planning-artifacts/architecture.md — Data flow: council session flow diagram — history.py at end of chain]
- [Source: _bmad-output/project-context.md — Boundary: council/history.py sole writer of council history files]
- [Source: _bmad-output/project-context.md — Atomic file writes: NFR8 requirement]
- [Source: src/aicouncil/council/schemas.py — AddendumGuidance (narrative format rules for host AI)]
- [Source: src/aicouncil/tools/council.py — ai_council tool, session_id generation, error handling patterns]
- [Source: src/aicouncil/scaffold.py — ensure_scaffold() creates ./aicouncil/history/ directory]
- [Source: src/aicouncil/exceptions.py — CouncilError for I/O failure wrapping]
- [Source: _bmad-output/implementation-artifacts/2-3-council-consensus-synthesis.md — Previous story learnings, CR 2-3 fixes]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation, no blockers encountered.

### Completion Notes List

- Task 1: Added `AddendumMetadata` and `AddendumSaveResult` Pydantic models to `council/schemas.py`
- Task 2: Created `council/history.py` boundary module with `_slugify_topic`, `_generate_filename`, `_format_addendum_markdown`, `write_council_addendum` (atomic temp-file-then-rename). Updated `council/__init__.py` exports.
- Task 3: Added `save_council_addendum` async tool to `tools/council.py`. Registered in `server.py`.
- Task 4: Created `tests/test_history.py` with 36 tests covering slugify, filename generation, markdown formatting, atomic writes, duplicate disambiguation, error wrapping, schema validation, and MCP tool return type.
- Task 5: Ruff format + check clean. 322 total tests pass (286 existing + 36 new). Zero regressions.

### Change Log

- 2026-03-22: Story 2.4 implemented — council history output boundary module, save_council_addendum MCP tool, 36 new tests

### File List

- `src/aicouncil/council/schemas.py` — MODIFIED (added AddendumMetadata, AddendumSaveResult)
- `src/aicouncil/council/history.py` — NEW (sole file output boundary for council history)
- `src/aicouncil/council/__init__.py` — MODIFIED (export write_council_addendum)
- `src/aicouncil/tools/council.py` — MODIFIED (added save_council_addendum tool)
- `src/aicouncil/server.py` — MODIFIED (registered save_council_addendum)
- `tests/test_history.py` — NEW (36 tests for history module)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED (status update)
- `_bmad-output/implementation-artifacts/2-4-council-history-output.md` — MODIFIED (story file updates)
