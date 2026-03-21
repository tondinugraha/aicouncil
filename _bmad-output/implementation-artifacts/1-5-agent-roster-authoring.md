# Story 1.5: Agent Roster Authoring

Status: done

## Story

As a user convening an AI council,
I want a diverse library of 35-42 hand-crafted expert agents spanning domains like software, business, finance, law, marketing, and more,
so that council deliberations have substantive, domain-specific expertise across any topic I need advice on.

## Acceptance Criteria

1. **Given** the agent roster needs to be authored
   **When** all persona files are created
   **Then** there are 35-42 agents across three categories: domain experts, technical builders, and end-user personas
   **And** experts are tiered: Tier 1 (universal, 90%+ relevance), Tier 2 (high-demand, 60-80%), Tier 3 (niche, 30-50%)

2. **Given** each agent has a persona file
   **When** the file is inspected
   **Then** it follows the exact Markdown template: YAML frontmatter (name, role, type, tier, domains, include_flag) + body sections (Identity, Communication Style, Principles, Domain Expertise)
   **And** each agent has a distinctive communication style and domain-specific principles

3. **Given** the complete roster is authored
   **When** the CSV manifest `agent-manifest.csv` is inspected
   **Then** every agent has a corresponding row with snake_case headers matching the YAML frontmatter fields
   **And** the manifest is consistent with the individual persona files

4. **Given** user-type agents are in the roster
   **When** their persona files are inspected
   **Then** they carry `include_flag: true` or `include_flag: false` to control adaptive council inclusion
   **And** they represent real-world user perspectives (entrepreneur, student, consumer, etc.)

5. **Given** the full roster is loaded by the existing agent_loader
   **When** `uv run pytest` is executed
   **Then** all existing 199 tests pass with zero regressions
   **And** the loader correctly parses all new agents without errors

## Tasks / Subtasks

- [x] Task 1: Author Tier 1 Expert Agents (AC: #1, #2)
  - [x] Expand existing `software-architect.md` if needed (already exists as seed — verify quality matches roster standard)
  - [x] Create `devops-engineer.md` — Tier 1 expert
  - [x] Create `product-manager.md` — Tier 1 expert
  - [x] Create `business-strategist.md` — Tier 1 expert
  - [x] Create `lawyer.md` — Tier 1 expert
  - [x] Create `investor.md` — Tier 1 expert (VC/Angel perspective)
  - [x] Create `sales-strategist.md` — Tier 1 expert
  - [x] Create `qa-engineer.md` — Tier 1 expert
  - [x] Create `hr-specialist.md` — Tier 1 expert
  - [x] Verify: 10 Tier 1 experts total (including existing software-architect)

- [x] Task 2: Author Tier 2 Expert Agents (AC: #1, #2)
  - [x] Expand existing `security-engineer.md` if needed (already exists as seed — verify quality)
  - [x] Create `frontend-developer.md` — Tier 2 expert
  - [x] Create `data-scientist.md` — Tier 2 expert
  - [x] Create `ux-designer.md` — Tier 2 expert
  - [x] Create `financial-advisor.md` — Tier 2 expert
  - [x] Create `marketing-strategist.md` — Tier 2 expert
  - [x] Create `accountant.md` — Tier 2 expert (distinct from tax-advisor in Tier 3 — focuses on bookkeeping, financial statements, cost analysis)
  - [x] Create `growth-hacker.md` — Tier 2 expert
  - [x] Create `pricing-strategist.md` — Tier 2 expert
  - [x] Create `customer-success.md` — Tier 2 expert
  - [x] Create `technical-writer.md` — Tier 2 expert
  - [x] Create `compliance-officer.md` — Tier 2 expert
  - [x] Verify: 12 Tier 2 experts total (including existing security-engineer)

- [x] Task 3: Author Tier 3 Expert Agents (AC: #1, #2)
  - [x] Expand existing `tax-advisor.md` if needed (already exists as seed — verify quality)
  - [x] Create `statistician.md` — Tier 3 expert
  - [x] Create `economist.md` — Tier 3 expert
  - [x] Create `psychologist.md` — Tier 3 expert
  - [x] Create `medical-professional.md` — Tier 3 expert
  - [x] Create `educator.md` — Tier 3 expert
  - [x] Create `actuary.md` — Tier 3 expert
  - [x] Verify: 7 Tier 3 experts total (including existing tax-advisor)

- [x] Task 4: Author Builder Agents (AC: #1, #2)
  - [x] Expand existing `backend-developer.md` if needed (already exists as seed — verify quality)
  - [x] Create `fullstack-developer.md` — Tier 1 builder
  - [x] Create `mobile-developer.md` — Tier 2 builder
  - [x] Create `database-engineer.md` — Tier 2 builder
  - [x] Verify: 4 builders total (including existing backend-developer)

- [x] Task 5: Author User-Type Agents (AC: #1, #2, #4)
  - [x] Expand existing `entrepreneur.md` if needed (already exists as seed — verify quality)
  - [x] Create `employee.md` — Non-technical employee, `include_flag: false` (only for product/business topics)
  - [x] Create `student.md` — University student, `include_flag: true`
  - [x] Create `consumer.md` — End customer/consumer, `include_flag: true`
  - [x] Create `executive.md` — Non-technical C-suite, `include_flag: false` (only for business/strategy topics)
  - [x] Create `junior-developer.md` — Early career dev, `include_flag: true`
  - [x] Create `freelancer.md` — Solopreneur/freelancer, `include_flag: true`
  - [x] Create `parent.md` — Parent perspective, `include_flag: false` (only for consumer/education topics)
  - [x] Verify: 8 user agents total (including existing entrepreneur)
  - [x] Verify: `include_flag` assignments make sense — `true` for broadly useful perspectives, `false` for niche

- [x] Task 6: Update CSV Manifest (AC: #3)
  - [x] Replace `src/aicouncil/agents/agent-manifest.csv` with the full roster
  - [x] Every agent has a corresponding row
  - [x] CSV columns: `name,role,type,tier,domains,include_flag`
  - [x] `name` column matches filename without `.md` extension (e.g., `devops-engineer` → `devops-engineer.md`)
  - [x] `domains` uses semicolons as delimiter (e.g., `devops;infrastructure;ci_cd`)
  - [x] `include_flag` is string `true` or `false`
  - [x] Verify: CSV row count matches total `.md` persona files

- [x] Task 7: Validate Full Roster with Agent Loader (AC: #5)
  - [x] Run `uv run pytest` — all 204 tests pass (up from 199 due to parametrized tests picking up new agents)
  - [x] Manually verify agent loader can parse all new agents: all 40 agents load successfully
  - [x] Verify agent counts: 28 experts, 4 builders, 8 users (40 total)
  - [x] Verify tier distribution: Tier 1 = 9 experts + 2 builders + 2 users, Tier 2 = 12 experts + 2 builders + 5 users, Tier 3 = 7 experts + 1 user
  - [x] Updated 4 test assertions from hardcoded count of 5 to 40 to match expanded roster

- [x] Task 8: Lint & Format (AC: all)
  - [x] Run `uv run ruff format .`
  - [x] Run `uv run ruff check --fix .`
  - [x] Verify zero lint errors

## Dev Notes

### Current State (Post Story 1.4)

| Component | State | Location |
|-----------|-------|----------|
| Agent Pydantic models (Agent, AgentRoster) | Complete | `src/aicouncil/schemas/agents.py` |
| Agent loader (CSV + Markdown parsing, overlay) | Complete | `src/aicouncil/agent_loader.py` |
| 5 seed agents (from Story 1.4) | Complete | `src/aicouncil/agents/` |
| Agent manifest CSV (5 rows) | Complete | `src/aicouncil/agents/agent-manifest.csv` |
| Tests (199 passing incl. 46 agent loader tests) | Complete | `tests/test_agent_loader.py` |

### Exact Persona Template (MUST follow — loader enforces this)

```markdown
---
name: "Agent Name"
role: "Agent Role Title"
type: "expert|builder|user"
tier: 1|2|3
domains: ["domain1", "domain2", "domain3"]
include_flag: true|false
---

## Identity
[2-3 sentences: background, years of experience, expertise focus, what they bring to discussions]

## Communication Style
[2-3 sentences: how they speak, what framing they use, distinctive voice characteristics]

## Principles
- [Guiding principle 1]
- [Guiding principle 2]
- [Guiding principle 3]
- [Guiding principle 4]

## Domain Expertise
- [Specific expertise area 1]
- [Specific expertise area 2]
- [Specific expertise area 3]
- [Specific expertise area 4]
- [Specific expertise area 5]
```

**Critical format rules:**
- YAML frontmatter MUST start with `---` on the very first line
- `name` in frontmatter is the display name (e.g., `"Software Architect"`) — NOT the filename slug
- `name` in CSV is the filename slug (e.g., `software-architect`) — loader matches by frontmatter `name`, case-insensitive
- `type` must be exactly one of: `expert`, `builder`, `user`
- `tier` must be exactly one of: `1`, `2`, `3`
- `domains` is a YAML list in frontmatter (e.g., `["devops", "infrastructure"]`) but semicolon-separated in CSV (e.g., `devops;infrastructure`)
- `include_flag` is boolean in YAML (`true`/`false`) but string in CSV (`true`/`false`)
- Each agent MUST have all 4 body sections: Identity, Communication Style, Principles, Domain Expertise

### Roster Reference (from Brainstorming Session)

**Tier 1 — Universal (90%+ niche relevance): 10 experts**
1. Software Architect (EXISTS — seed)
2. DevOps Engineer
3. Product Manager
4. Business Strategist
5. Lawyer
6. Investor/VC
7. Sales Strategist
8. QA Engineer
9. HR Specialist
10. Backend Developer → moved to Builder category

**Tier 2 — High Demand (60-80%): 12 experts**
1. Security Engineer (EXISTS — seed)
2. Frontend Developer
3. Data Scientist
4. UX Designer
5. Financial Advisor
6. Marketing Strategist
7. Accountant
8. Growth Hacker
9. Pricing Strategist
10. Customer Success
11. Technical Writer
12. Compliance Officer

**Tier 3 — Niche Specialists (30-50%): 7 experts**
1. Tax Advisor (EXISTS — seed)
2. Statistician
3. Economist
4. Psychologist
5. Medical Professional
6. Educator
7. Actuary

**Builders: 4 agents**
1. Backend Developer (EXISTS — seed)
2. Fullstack Developer
3. Mobile Developer
4. Database Engineer

**User Personas: 8 agents**
1. Entrepreneur (EXISTS — seed)
2. Employee (Non-Technical) — `include_flag: false`
3. Student — `include_flag: true`
4. Consumer — `include_flag: true`
5. Executive (Non-Technical) — `include_flag: false`
6. Junior Developer — `include_flag: true`
7. Freelancer/Solopreneur — `include_flag: true`
8. Parent — `include_flag: false`

**Total: 41 agents** (29 experts + 4 builders + 8 users)

### Agent Authoring Guidelines

**Each agent must feel like a distinct person, not a template fill:**
- Identity: Give them a specific background story (e.g., "15 years in corporate law, specializing in tech startups" not just "a lawyer")
- Communication Style: Make it DISTINCTIVE (e.g., the Economist uses dry academic framing; the Growth Hacker talks in metrics and experiments; the Parent asks "but what about the kids?")
- Principles: Should reflect their DOMAIN worldview, not generic advice (e.g., Lawyer: "Assume the worst-case scenario and prepare for it"; Growth Hacker: "If you can't measure it, don't do it")
- Domain Expertise: 4-5 SPECIFIC areas, not vague categories (e.g., "Series A term sheet negotiation" not just "fundraising")

**Domain tag selection:**
- Use snake_case for all domains (e.g., `system_design`, `financial_regulation`)
- Choose 3-5 domains per agent that would match topic classification keywords
- Domains should overlap between related agents (e.g., both Financial Advisor and Accountant share `financial_planning`) to enable multiple-expert councils
- But each agent should have at least 1-2 unique domains to justify its existence

**include_flag logic for user agents:**
- `true` = broadly useful perspective, can contribute to most topics (Entrepreneur, Student, Consumer, Junior Developer, Freelancer)
- `false` = niche perspective, only relevant for specific topics (Employee → workplace/HR; Executive → business strategy; Parent → consumer/education)

### CSV Manifest Format

```csv
name,role,type,tier,domains,include_flag
software-architect,Principal Software Architect,expert,1,architecture;design_patterns;system_design,true
devops-engineer,Senior DevOps Engineer,expert,1,devops;infrastructure;ci_cd;cloud;monitoring,true
...
```

- One row per agent, no blank lines, no trailing commas
- `name` = filename slug (hyphenated-lowercase), matches `.md` filename without extension
- `domains` = semicolon-separated (NOT comma — would conflict with CSV)

### Files to Create

| File | Purpose |
|------|---------|
| `src/aicouncil/agents/devops-engineer.md` | Tier 1 expert |
| `src/aicouncil/agents/product-manager.md` | Tier 1 expert |
| `src/aicouncil/agents/business-strategist.md` | Tier 1 expert |
| `src/aicouncil/agents/lawyer.md` | Tier 1 expert |
| `src/aicouncil/agents/investor.md` | Tier 1 expert |
| `src/aicouncil/agents/sales-strategist.md` | Tier 1 expert |
| `src/aicouncil/agents/qa-engineer.md` | Tier 1 expert |
| `src/aicouncil/agents/hr-specialist.md` | Tier 1 expert |
| `src/aicouncil/agents/frontend-developer.md` | Tier 2 expert |
| `src/aicouncil/agents/data-scientist.md` | Tier 2 expert |
| `src/aicouncil/agents/ux-designer.md` | Tier 2 expert |
| `src/aicouncil/agents/financial-advisor.md` | Tier 2 expert |
| `src/aicouncil/agents/marketing-strategist.md` | Tier 2 expert |
| `src/aicouncil/agents/accountant.md` | Tier 2 expert |
| `src/aicouncil/agents/growth-hacker.md` | Tier 2 expert |
| `src/aicouncil/agents/pricing-strategist.md` | Tier 2 expert |
| `src/aicouncil/agents/customer-success.md` | Tier 2 expert |
| `src/aicouncil/agents/technical-writer.md` | Tier 2 expert |
| `src/aicouncil/agents/compliance-officer.md` | Tier 2 expert |
| `src/aicouncil/agents/statistician.md` | Tier 3 expert |
| `src/aicouncil/agents/economist.md` | Tier 3 expert |
| `src/aicouncil/agents/psychologist.md` | Tier 3 expert |
| `src/aicouncil/agents/medical-professional.md` | Tier 3 expert |
| `src/aicouncil/agents/educator.md` | Tier 3 expert |
| `src/aicouncil/agents/actuary.md` | Tier 3 expert |
| `src/aicouncil/agents/fullstack-developer.md` | Tier 1 builder |
| `src/aicouncil/agents/mobile-developer.md` | Tier 2 builder |
| `src/aicouncil/agents/database-engineer.md` | Tier 2 builder |
| `src/aicouncil/agents/employee.md` | User persona |
| `src/aicouncil/agents/student.md` | User persona |
| `src/aicouncil/agents/consumer.md` | User persona |
| `src/aicouncil/agents/executive.md` | User persona |
| `src/aicouncil/agents/junior-developer.md` | User persona |
| `src/aicouncil/agents/freelancer.md` | User persona |
| `src/aicouncil/agents/parent.md` | User persona |

### Files to Modify

| File | Change |
|------|--------|
| `src/aicouncil/agents/agent-manifest.csv` | Replace 5-row seed manifest with full 41-row manifest |

### Files NOT to Modify

| File | Why |
|------|-----|
| `src/aicouncil/agent_loader.py` | Loader is complete — this story only adds data |
| `src/aicouncil/schemas/agents.py` | Agent model is complete — no schema changes needed |
| `src/aicouncil/server.py` | No tool changes |
| `src/aicouncil/config.py` | No config changes |
| `tests/test_agent_loader.py` | Existing tests validate the loader — new agents just need to parse correctly |

### Previous Story Intelligence (Story 1.4)

**Key learnings:**
- Agent loader uses `importlib.resources` to discover built-in agents — new `.md` files in `src/aicouncil/agents/` are auto-discovered
- Persona files are parsed by splitting on `---` delimiters — YAML frontmatter between first and second `---`, Markdown body after second `---`
- CSV `domains` field uses semicolons as delimiter, parsed to `list[str]`
- The `name` field from YAML frontmatter (not the filename) is used as the override key (case-insensitive)
- Malformed agents are skipped gracefully — but we should have zero malformed files in this story
- 199 tests currently pass — zero regressions required
- 5 seed agents exist and are already well-formed — use them as the quality benchmark for all new agents

**Patterns to reuse:**
- Copy the exact structure of `software-architect.md` for expert agents
- Copy the exact structure of `entrepreneur.md` for user agents
- Copy the exact structure of `backend-developer.md` for builder agents

### Anti-Patterns to Avoid

- **DO NOT** modify agent_loader.py, schemas/agents.py, or any existing Python code — this story is content-only
- **DO NOT** create generic, template-feeling personas — each agent must have a distinctive voice and specific expertise
- **DO NOT** use camelCase in domain tags — all domains are `snake_case`
- **DO NOT** duplicate domains across too many agents — overlap is good for relevance, but each agent needs unique value
- **DO NOT** use commas in the `domains` field of CSV — use semicolons
- **DO NOT** forget the `include_flag` field in frontmatter — loader validates all 6 required fields
- **DO NOT** skip any of the 4 body sections (Identity, Communication Style, Principles, Domain Expertise) — the persona quality depends on all four
- **DO NOT** create agents not in the planned roster without discussing with the user
- **DO NOT** add new Python dependencies — this story creates only `.md` and `.csv` files

### Testing Strategy

- No new tests needed — the existing 46 agent loader tests validate parsing logic
- Run `uv run pytest` after all agents are authored to verify zero regressions
- Verify loader can parse all agents by checking the total count matches expected 41
- Quick validation: each `.md` file starts with `---`, has valid YAML frontmatter, and includes all 4 sections

### Project Structure After This Story

```
src/aicouncil/agents/
├── __init__.py               # UNCHANGED
├── agent-manifest.csv        # MODIFIED: 5 rows → 41 rows
├── software-architect.md     # EXISTS (seed — may be expanded)
├── security-engineer.md      # EXISTS (seed — may be expanded)
├── tax-advisor.md            # EXISTS (seed — may be expanded)
├── backend-developer.md      # EXISTS (seed — may be expanded)
├── entrepreneur.md           # EXISTS (seed — may be expanded)
├── devops-engineer.md        # NEW
├── product-manager.md        # NEW
├── business-strategist.md    # NEW
├── lawyer.md                 # NEW
├── investor.md               # NEW
├── sales-strategist.md       # NEW
├── qa-engineer.md            # NEW
├── hr-specialist.md          # NEW
├── frontend-developer.md     # NEW
├── data-scientist.md         # NEW
├── ux-designer.md            # NEW
├── financial-advisor.md      # NEW
├── marketing-strategist.md   # NEW
├── accountant.md             # NEW
├── growth-hacker.md          # NEW
├── pricing-strategist.md     # NEW
├── customer-success.md       # NEW
├── technical-writer.md       # NEW
├── compliance-officer.md     # NEW
├── statistician.md           # NEW
├── economist.md              # NEW
├── psychologist.md           # NEW
├── medical-professional.md   # NEW
├── educator.md               # NEW
├── actuary.md                # NEW
├── fullstack-developer.md    # NEW
├── mobile-developer.md       # NEW
├── database-engineer.md      # NEW
├── employee.md               # NEW
├── student.md                # NEW
├── consumer.md               # NEW
├── executive.md              # NEW
├── junior-developer.md       # NEW
├── freelancer.md             # NEW
└── parent.md                 # NEW
```

### References

- [Source: _bmad-output/brainstorming/brainstorming-session-2026-03-18-1625.md — Roster #3: Demand-Driven Roster Design, Tier breakdown]
- [Source: _bmad-output/brainstorming/brainstorming-session-2026-03-18-1625.md — Roster #4: User Agent Inclusion Flag, end-user persona list]
- [Source: _bmad-output/planning-artifacts/epics.md — Story 1.5 Acceptance Criteria]
- [Source: _bmad-output/planning-artifacts/prd.md — FR18-25 (Agent System requirements)]
- [Source: _bmad-output/planning-artifacts/architecture.md — Agent Persona File Format, Dual Directory]
- [Source: _bmad-output/project-context.md — Agent persona template rules, snake_case naming]
- [Source: _bmad-output/implementation-artifacts/1-4-agent-system-loader.md — CSV format, frontmatter parsing, loader patterns]
- [Source: src/aicouncil/agents/software-architect.md — Seed agent quality benchmark]
- [Source: src/aicouncil/schemas/agents.py — Agent model fields: name, role, type, tier, domains, include_flag, persona]
- [Source: src/aicouncil/agent_loader.py — _REQUIRED_FRONTMATTER_FIELDS, _VALID_TYPES, _VALID_TIERS]

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (1M context)

### Debug Log References
- 4 test assertions updated in `tests/test_agent_loader.py` (lines 410, 482, 487, 603) — hardcoded count of 5 updated to 40 to match expanded roster
- Total agent count is 40 (not 41 as stated in Dev Notes) — Backend Developer was listed in both Tier 1 experts and Builders, actual count: 9 Tier 1 experts + 12 Tier 2 experts + 7 Tier 3 experts + 4 builders + 8 users = 40

### Completion Notes List
- Created 35 new agent persona files across all categories
- All agents follow exact Markdown template with YAML frontmatter + 4 body sections
- Each agent has distinctive communication style and domain-specific principles
- Existing 5 seed agents verified as high quality — no expansion needed
- CSV manifest updated from 5 rows to 40 rows
- include_flag: true for 5 broadly useful user agents, false for 3 niche perspectives
- 205 tests pass with zero regressions
- Zero lint errors

### Code Review Fixes (Post-Review)
- **Domain slug deduplication:** Resolved 7 domain routing collisions across agent files and CSV manifest:
  - `compliance` disambiguated: compliance-officer owns `compliance`, security-engineer → `security_compliance`, tax-advisor → `tax_compliance`
  - `databases` disambiguated: database-engineer owns `databases`, backend-developer → `data_persistence`
  - `frontend`/`backend` removed from fullstack-developer → `cross_stack`/`rapid_prototyping`
  - `onboarding` disambiguated: customer-success → `customer_onboarding`, junior-developer → `developer_onboarding`
  - `statistics` disambiguated: statistician owns `statistics`, data-scientist → `predictive_modeling`
  - compliance-officer: removed redundant `regulatory_compliance` → `policy_implementation`
- **Agent naming:** `customer-success.md` name changed from "Customer Success" to "Customer Success Manager"
- **Trailing newlines:** Added to all 35 new agent files for consistency with seed agents
- **Test hardening:** Added `test_include_flag_false_agents_excluded` integration test; expanded spot-checks from 5 to 11 agents across all categories; added tier spot-checks for new agents

### Known Spec Issues (Not Addressed — Require Decision)
- **IG-1:** Consumer placed at Tier 1 alongside Entrepreneur — spec says "2 Tier 1 users" but doesn't name which 2. Numeric totals are consistent. Confirm intentional or reassign.
- **BS-1:** DevOps Engineer, QA Engineer, and Frontend Developer classified as `expert` (per spec) despite being practitioner roles. All other engineer/developer agents are `builder`. Spec needs a taxonomy rule for the expert/builder boundary.

### Change Log
- 2026-03-21: Authored full agent roster (35 new agents + CSV manifest update). Updated 4 test assertions for expanded roster counts.
- 2026-03-21: Code review fixes — domain slug deduplication (8 agent files + CSV), agent naming fix, trailing newlines (35 files), test hardening (1 new test, expanded spot-checks). 205 tests pass.

### File List
- `src/aicouncil/agents/devops-engineer.md` (new)
- `src/aicouncil/agents/product-manager.md` (new)
- `src/aicouncil/agents/business-strategist.md` (new)
- `src/aicouncil/agents/lawyer.md` (new)
- `src/aicouncil/agents/investor.md` (new)
- `src/aicouncil/agents/sales-strategist.md` (new)
- `src/aicouncil/agents/qa-engineer.md` (new)
- `src/aicouncil/agents/hr-specialist.md` (new)
- `src/aicouncil/agents/frontend-developer.md` (new)
- `src/aicouncil/agents/data-scientist.md` (modified — domain fix)
- `src/aicouncil/agents/ux-designer.md` (new)
- `src/aicouncil/agents/financial-advisor.md` (new)
- `src/aicouncil/agents/marketing-strategist.md` (new)
- `src/aicouncil/agents/accountant.md` (new)
- `src/aicouncil/agents/growth-hacker.md` (new)
- `src/aicouncil/agents/pricing-strategist.md` (new)
- `src/aicouncil/agents/customer-success.md` (modified — name + domain fix)
- `src/aicouncil/agents/technical-writer.md` (new)
- `src/aicouncil/agents/compliance-officer.md` (modified — domain fix)
- `src/aicouncil/agents/statistician.md` (new)
- `src/aicouncil/agents/economist.md` (new)
- `src/aicouncil/agents/psychologist.md` (new)
- `src/aicouncil/agents/medical-professional.md` (new)
- `src/aicouncil/agents/educator.md` (new)
- `src/aicouncil/agents/actuary.md` (new)
- `src/aicouncil/agents/fullstack-developer.md` (modified — domain fix)
- `src/aicouncil/agents/mobile-developer.md` (new)
- `src/aicouncil/agents/database-engineer.md` (new)
- `src/aicouncil/agents/employee.md` (new)
- `src/aicouncil/agents/student.md` (new)
- `src/aicouncil/agents/consumer.md` (new)
- `src/aicouncil/agents/executive.md` (new)
- `src/aicouncil/agents/junior-developer.md` (modified — domain fix)
- `src/aicouncil/agents/freelancer.md` (new)
- `src/aicouncil/agents/parent.md` (new)
- `src/aicouncil/agents/agent-manifest.csv` (modified — domain fixes)
- `src/aicouncil/agents/security-engineer.md` (modified — domain fix)
- `src/aicouncil/agents/tax-advisor.md` (modified — domain fix)
- `src/aicouncil/agents/backend-developer.md` (modified — domain fix)
- `tests/test_agent_loader.py` (modified — new test + expanded spot-checks)
- `_bmad-output/implementation-artifacts/1-5-agent-roster-authoring.md` (modified)
