---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain-skipped', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['product-brief-aicouncil-2026-03-19.md', 'brainstorming-session-2026-03-18-1625.md']
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: 'developer_tool'
  domain: 'scientific'
  complexity: 'medium'
  projectContext: 'greenfield'
---

# Product Requirements Document - aicouncil

**Author:** Odi
**Date:** 2026-03-19

## Executive Summary

AI Council is an MCP server that eliminates single-model AI bias by enabling multi-model, multi-agent deliberation directly within a developer's workflow. Instead of manually comparing outputs across ChatGPT, Claude, and Gemini in separate browser tabs, developers and decision-makers convene a council of domain-expert AI agents — each running on a different AI model — to discuss, debate, and reach consensus on any topic. The system integrates through the MCP protocol, giving council discussions direct access to the user's codebase and project context.

The product operates in two modes: individual model-agnostic utility tools powered by a configurable default model, and the flagship AI Council tool where an intelligent orchestrator assembles and mediates a panel of hand-crafted expert agents across multiple models. The orchestrator acts as chairperson — directing turns, introducing debate when positions converge too easily, managing context across models with varying window sizes, and driving toward synthesized consensus. All model routing is powered by OpenRouter with a single API key.

Target users are solo technical founders making decisions outside their expertise, tech leads at early-stage startups who need multi-specialist validation for architectural choices, and non-technical founders using AI-assisted development tools who cannot independently evaluate whether a single model's advice is sound or dangerously wrong.

### What Makes This Special

The core differentiator is **orchestrator-mediated deliberation** — not parallel outputs displayed side-by-side, but structured debate with an intelligent chairperson that actively shapes discourse quality. Existing multi-model tools are parallel runners that leave synthesis to the user. AI Council's orchestrator introduces adversarial debate when positions align too easily, weights expert opinions by domain relevance during deadlocks, and produces a detail-preserving narrative addendum that captures the full reasoning.

Three design decisions compound this advantage: (1) the same agent persona instantiated on different models produces genuinely different reasoning, turning model diversity into a deliberate debate strategy; (2) hand-crafted domain personas with distinct communication styles, principles, and expertise make council discussions substantively rich rather than generic; (3) codebase awareness through MCP means council deliberations can reference actual project files — something no web-based multi-model tool can offer.

The product ships with 35-42 hand-crafted agents across three categories (domain experts, technical builders, and end-user personas), with user-type agents carrying inclusion flags for adaptive council composition. An open template allows users to create custom agents.

## Project Classification

- **Project Type:** Developer Tool (MCP server exposing capabilities via the MCP protocol to host AI environments)
- **Domain:** AI/Developer Tooling (multi-model AI orchestration)
- **Complexity:** Medium (architecturally non-trivial orchestration and multi-model routing, but no regulatory or compliance burden)
- **Project Context:** Brownfield evolution (forking and extending existing Python-based gemini-mcp server with 15 working tools)

## Success Criteria

### User Success

- **Decision Confidence** — Users make decisions they feel confident in after a council session, rather than second-guessing or seeking additional opinions elsewhere
- **Blind Spot Discovery** — The council surfaces risks, perspectives, or considerations the user hadn't thought of and their primary AI model didn't mention
- **Time Efficiency** — Users spend less time on multi-model comparison than the manual tab-hopping alternative, while getting deeper and more structured analysis
- **Repeat Usage** — Users return to the council for subsequent decisions, indicating the first experience delivered genuine value
- **Actionability** — Council addendums produce concrete, actionable recommendations users can immediately act on

### Business Success

**Core objective:** Be the default tool for important decisions in a developer's AI-assisted workflow.

- The tool reliably produces high-quality, multi-perspective deliberation
- Setup is frictionless enough that a new user runs their first council session within minutes
- The agent roster covers the domains users actually need
- The tool integrates seamlessly into existing MCP-enabled workflows without disruption

### Technical Success

- Orchestrator effectively manages multi-agent councils (6+ agents) without context degradation across models with varying context windows
- Capability-weighted random routing (60/40 bias) correctly distributes model assignments per the config capability matrix
- Adaptive context management triggers summarization at 50% context window threshold without losing key positions
- All existing gemini-mcp tools function correctly with configurable model selection via OpenRouter
- Council sessions complete end-to-end: topic classification → agent assembly → deliberation → consensus → addendum output

### Measurable Outcomes

**Quality KPIs:**
- Consensus rate — percentage of sessions reaching unanimous agreement vs. tiered conclusions
- Addendum completeness — sessions produce addendums with clear recommendations, supporting reasoning, and identified risks
- Multi-perspective coverage — discussions include perspectives from multiple agent categories (expert + builder + user)

**Engagement KPIs:**
- Sessions per user — repeat council usage indicates sustained value
- Council-to-individual tool ratio — frequency of council vs. single-model tool usage
- Agent roster utilization — distribution of which agents are summoned most frequently

**Utility KPIs:**
- Time to first council — under 10 minutes from installation to first completed session
- Session completion rate — percentage of councils that run to full addendum vs. abandoned
- Community agent contributions — users creating and sharing custom agents

## Product Scope

### MVP - Minimum Viable Product

1. **AI Council Tool** — Complete multi-agent deliberation: LLM-powered topic classification, orchestrator-driven assembly with balanced multi-factor selection, capability-weighted random model routing via OpenRouter, orchestrator as chairperson (directing turns, debate, context management, convergence), unanimous-first consensus with tiered fallback, detail-preserving narrative addendum, dual output (inline + file)
2. **Complete Agent Roster (35-42)** — Three-category architecture: Expert Tier 1 (universal), Tier 2 (high-demand), Tier 3 (niche); Builder agents; User agents with inclusion flags. Each hand-crafted in Markdown with full persona.
3. **Model-Agnostic Extended Tools** — All existing gemini-mcp tools converted to model-agnostic operation with cascading defaults (global → per-tool → per-invocation)
4. **Configuration System** — `.mcp.json` for model routing/tool config, `agents/agent-manifest.csv` + individual `.md` persona files, `config/model-capabilities.yaml` for capability weights
5. **Council History** — Dedicated directory for timestamped addendum files as persistent decision log
6. **Custom Agent Support** — Open template for user-created agents extending or overriding built-in roster

### Growth Features (Post-MVP)

- Community agent registry — shared marketplace for contributing and pulling agents
- Self-learning capability weights — auto-adjust model-capability affinities from session quality
- Dynamic model discovery — auto-populate model pool from OpenRouter's available models
- Council history indexing — searchable index across past councils with topic/agent metadata
- Cross-council referencing — loading past conclusions as context for new councils

### Vision (Future)

- Community agent ecosystem with curated, reviewed agent packs by industry (FinTech, HealthTech, LegalTech)
- Self-improving model routing that learns from council quality over time
- Cross-council institutional knowledge that compounds across sessions
- Team collaboration — shared sessions, follow-up assignments, decision tracking
- IDE-native plugins beyond MCP (VS Code, JetBrains)
- Specialized council modes — code review council, architecture review council, incident post-mortem council

## User Journeys

### Journey 1: Alex — Solo Founder's First Council (Primary User, Success Path)

Alex has been building a SaaS MVP for three months using Claude Code. Tonight, they need to decide whether to implement Stripe Connect for marketplace payments or build a simpler direct-charge flow. They've already asked Claude, which confidently recommended Stripe Connect. But this is a $20K+ architecture decision — one model's opinion isn't enough.

Alex types into Claude Code: *"I need to decide between Stripe Connect and direct Stripe charges for a two-sided marketplace. Let's get the council's take."*

The orchestrator classifies the topic, assembles a council: a Payment Systems Architect (on GPT 5.2), a Backend Developer (on Gemini 2.5 Pro), an Accountant/Tax Advisor (on Claude Opus), a Pricing Strategist (on DeepSeek R2), and an Entrepreneur persona (on Grok 3) as user-agent. The orchestrator references Alex's actual codebase through MCP — it sees the current database schema, the existing Stripe integration, and the user model.

Round 1 lays out positions. The Payment Architect favors Connect for future-proofing. The Backend Dev flags Connect's onboarding complexity for a solo dev. The Accountant raises 1099-K reporting obligations that Alex never considered. The Pricing Strategist argues direct charges preserve margin control at early stage. The Entrepreneur asks: "How many sellers do you actually have right now?"

The orchestrator notices too-quick alignment on "it depends on scale" and introduces debate: pushes the Payment Architect to defend Connect for a marketplace with only 3 sellers today.

Round 2 sharpens. The Accountant reveals that direct charges make Alex the merchant of record with different tax obligations. The Backend Dev estimates Connect adds 2-3 weeks to MVP. The Entrepreneur pins it: "Ship direct charges now, migrate to Connect at 20+ sellers."

Consensus round: 5 of 6 agree on phased approach. The Payment Architect dissents but acknowledges the pragmatic case. The orchestrator synthesizes a narrative addendum — inline in the conversation and saved to `./council-history/2026-03-19-stripe-architecture.md`.

Alex reads the addendum, sees the tax angle they completely missed, and commits to the phased approach with confidence. They reference the addendum file two weeks later when their co-founder asks why they chose direct charges.

**Capabilities revealed:** Topic classification, council assembly, codebase-aware context via MCP, orchestrator-driven debate, tiered consensus, dual output (inline + file), council history persistence.

### Journey 2: Jordan — Tech Lead Pressure-Tests an Architecture Decision (Primary User, Edge Case)

Jordan's team is debating whether to migrate from PostgreSQL to a distributed database for their growing analytics workload. Jordan has a strong opinion (stay with Postgres + read replicas) but needs to validate it before committing the team. They want to specifically challenge their own position.

Jordan prompts: *"We're considering migrating from PostgreSQL to CockroachDB or staying with Postgres read replicas for analytics scale. I'm biased toward Postgres — I want the council to stress-test that position. Include a Data Scientist and make sure the Security Engineer is on Gemini."*

The orchestrator respects Jordan's explicit requests — pins the Data Scientist and assigns Security Engineer to Gemini — then fills remaining seats automatically. The council includes agents Jordan didn't think to request: a DevOps Engineer who raises operational complexity, and an Economist wildcard who reframes the decision in terms of engineering opportunity cost.

During deliberation, the orchestrator detects Jordan's bias acknowledgment and deliberately assigns adversarial framing: pushes CockroachDB advocates to make their strongest case against Postgres. The Data Scientist on a different model than expected produces a perspective Jordan's primary AI never surfaced — the analytics workload pattern is actually better suited to a columnar store like ClickHouse, not either option Jordan was considering.

The council reaches tiered consensus: unanimous that CockroachDB is wrong for this workload, split between Postgres + read replicas and a ClickHouse sidecar. The addendum clearly presents both paths with trade-offs.

Jordan presents the addendum to their non-technical founder as evidence that the decision was rigorously evaluated by multiple expert perspectives.

**Capabilities revealed:** Natural language agent/model pinning, adversarial facilitation, wildcard agent value, tiered consensus with genuine disagreement, addendum as shareable artifact.

### Journey 3: Sam — Non-Technical Founder Gets Guardrails (Primary User, Alternative Profile)

Sam is using Cursor with MCP integrations to build their product. They've asked their AI assistant to implement user authentication, and it suggested rolling a custom JWT solution. Sam has no way to evaluate whether this is a good idea or a security disaster waiting to happen.

Sam prompts: *"My AI assistant wants to build custom JWT authentication. Is this the right approach for a B2C app that will handle payment info?"*

The council assembles with heavy security weighting: Security Engineer (on two different models), Backend Developer, Compliance Officer, and a Consumer end-user persona. The orchestrator recognizes this is a safety-critical topic and shifts tone toward cautious, risk-surfacing deliberation.

The two Security Engineers on different models disagree — one says custom JWT is fine with proper implementation, the other flags it as unnecessary risk when Auth0/Clerk exist. The Compliance Officer adds PCI DSS implications Sam didn't know about. The Consumer persona asks: "What happens to my credit card if this gets hacked?"

Consensus: unanimous against custom JWT for a payment-handling B2C app. The addendum includes a concrete recommendation (use Auth0 or Clerk), explains why in terms Sam can understand, and flags the specific risks of the custom approach.

Sam avoids a potentially catastrophic security decision they had no ability to evaluate independently. They save the addendum and share it with their freelance developer as implementation guidance.

**Capabilities revealed:** Security-sensitive topic handling, duplicate agents on different models producing genuine disagreement, user-agent grounding, accessible language for non-technical users, addendum as implementation guidance.

### Journey 4: Team Member — Reading the Decision Log (Secondary User)

Jordan's co-founder, a non-technical CEO, missed the database architecture discussion. Three days later, they open the `council-history/` directory and find timestamped addendum files. They read `2026-03-22-database-migration.md` — a clear narrative explaining the options considered, expert perspectives from multiple models, the dissenting views, and the recommended path with reasoning.

The CEO understands the decision without needing Jordan to explain it. They reference the addendum in their board update, noting that the architectural decision was validated by multi-model expert deliberation.

**Capabilities revealed:** File-based council history as team knowledge base, narrative addendum format readable by non-technical stakeholders, persistent decision log.

### Journey 5: Power User — Custom Agent Creation (Extension Path)

Alex has been using AI Council for a month. Their SaaS targets the restaurant industry, and council discussions keep lacking industry-specific context. Alex opens the agent template, creates `agents/restaurant-industry-expert.md` with a persona that understands food cost margins, health code compliance, POS integration, and seasonal staffing patterns. They add the agent to `agents/agent-manifest.csv`.

Next council session on pricing strategy, the orchestrator discovers the custom agent and includes it. The restaurant expert brings domain context that generic Business Strategist and Pricing Strategist agents couldn't — specific benchmark margins, industry-standard pricing models, and seasonal revenue patterns.

**Capabilities revealed:** Custom agent creation via open template, CSV manifest extensibility, orchestrator discovers and includes custom agents, domain-specific value from user-authored agents.

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---------|--------------------------|
| **Alex (Success Path)** | Topic classification, council assembly, MCP codebase awareness, orchestrator debate, consensus, dual output, council history |
| **Jordan (Edge Case)** | Agent/model pinning via prompt, adversarial facilitation, wildcard value, tiered consensus, addendum as shareable artifact |
| **Sam (Alt Profile)** | Security-weighted assembly, duplicate agents disagreeing, user-agent grounding, accessible language, addendum as guidance |
| **Team Member (Secondary)** | File-based history, narrative format readability, persistent decision log |
| **Power User (Extension)** | Custom agent template, CSV manifest, orchestrator auto-discovery, domain-specific agents |

**Full capability coverage:** All 6 MVP features (Council Tool, Agent Roster, Model-Agnostic Tools, Configuration, Council History, Custom Agents) are exercised across journeys.

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Orchestrator-Mediated Multi-Model Deliberation (New Paradigm)**
No existing tool facilitates actual structured debate between AI models with an intelligent chairperson. Current multi-model tools (parallel runners) display outputs side-by-side and leave synthesis entirely to the user. AI Council introduces a fundamentally different interaction pattern: an orchestrator that reads the room, introduces adversarial debate, manages context, and drives toward consensus. This is not an incremental improvement — it's a new category of AI interaction.

**2. Model Diversity as Debate Strategy**
The insight that the same agent persona on different models produces genuinely different reasoning is novel. Existing tools treat model selection as an infrastructure decision. AI Council treats it as a deliberate diversity mechanism — "same expert, different brain" — validated in brainstorming simulation where duplicate Tax Advisors on different models gave substantively different perspectives.

**3. Hand-Crafted Persona Layer Over Multi-Model Routing**
Combining rich, individually authored agent personas (communication style, principles, domain expertise) with capability-weighted model routing creates a compound effect no existing tool achieves. The persona shapes what the model says; the model shapes how it reasons. Neither layer alone produces the same result.

**4. Codebase-Aware AI Deliberation via MCP**
Web-based multi-model tools cannot reference the user's actual project files. By building on MCP, council discussions can read the codebase, inspect schemas, and reference implementation details — making deliberation contextually grounded in a way that's structurally impossible for browser-based competitors.

### Market Context & Competitive Landscape

The multi-model AI space is dominated by parallel runners and routers — tools that select the best model for a task or show multiple outputs side-by-side. None implement mediated deliberation. The MCP ecosystem is early-stage, creating a window for a well-designed multi-model deliberation tool to establish the category before incumbents recognize the opportunity. OpenRouter's unified API has only recently made multi-model integration practical with a single key, removing the infrastructure barrier that previously made this architecture impractical.

### Validation Approach

- **Brainstorming simulation validated core mechanics** — the role-play simulation of a cross-border tax council confirmed that orchestrator-directed debate, duplicate agents on different models, user-agent inclusion, and wildcard agents all produce measurably richer output than single-model responses
- **MVP validates through usage** — time to first council (<10 min), session completion rate, and repeat usage directly measure whether the deliberation paradigm delivers value users return to
- **Addendum quality is the proxy metric** — if users reference, share, and act on addendums, the innovation is working

### Risk Mitigation

- **Orchestrator quality risk** — deliberation quality depends heavily on the host AI's ability to act as an effective chairperson. Mitigation: design clear orchestration prompts and guidelines; the orchestrator IS the host AI (Claude, GPT, etc.), leveraging the model's existing reasoning capabilities rather than building custom orchestration logic
- **Model API cost risk** — multi-model councils consume multiple API calls per session. Mitigation: adaptive context management (50% threshold rule) controls cost; users have full visibility into which models are called
- **Model availability risk** — OpenRouter models may be unavailable or deprecated. Mitigation: capability-weighted random routing naturally falls back to available models; config-file capability matrix is user-editable to adapt to model landscape changes

## Developer Tool Specific Requirements

### Project-Type Overview

AI Council is an MCP server — a developer tool that exposes capabilities via the Model Context Protocol to host AI environments (Claude Code, Cursor, Windsurf, etc.). It is not a standalone application; it operates as infrastructure within the user's existing AI-assisted development workflow.

### Technical Architecture Considerations

**Language Support & Runtime:**
- Python 3.11+ runtime (consistent with existing gemini-mcp codebase and MCP Python SDK ecosystem)
- MCP Python SDK (`mcp>=1.0.0`) with FastMCP for protocol compliance and tool registration
- OpenRouter API client for unified multi-model access
- Pydantic for data validation and structured response schemas

**MCP Tool Interface:**
- `ai_council` tool — accepts topic (required), agents, models, council_size, include_user_agents, include_wildcard, output_file (all optional). Orchestrator fills defaults autonomously.
- Extended model-agnostic tools — each existing gemini-mcp tool re-exposed with configurable model selection
- All tools registered via MCP protocol with proper input schemas and descriptions

**Package Distribution:**
- PyPI package installable via `uv` / `uvx` for standard MCP server installation
- Configuration via environment variables in MCP host config (standard MCP pattern)
- Core dependencies: Python 3.11+, MCP SDK, Pydantic, OpenRouter client, python-dotenv

**API Surface:**
- Single external dependency: OpenRouter API (unified gateway to all models)
- No proprietary API, no backend service, no user accounts — fully local tool
- Agent roster and config are file-based, version-controllable with the project

**Documentation:**
- README with quickstart (API key → first council in <5 minutes)
- Agent authoring guide with template and examples
- Configuration reference for `.mcp.json`, capability matrix, and agent manifest

### Implementation Considerations

**Cascading Configuration:**
- Global default model → per-tool model override → per-invocation model override
- Council tool has its own `model_pool` array in config, separate from individual tool defaults
- Capability weight matrix (`config/model-capabilities.yaml`) shipped with sensible defaults, user-editable

**Agent System:**
- `agents/agent-manifest.csv` — registry for quick lookup (name, role, type, tier, domain tags, inclusion flag)
- `agents/{name}.md` — full persona files (name, role, identity, communication style, principles, domain expertise, agent type)
- Built-in core agents shipped with package + user-extensible local directory that overrides built-ins

**Council History:**
- `council-history/` directory in project root
- Timestamped markdown files (e.g., `2026-03-19-stripe-architecture.md`)
- Narrative addendum format — readable by humans, referenceable by team members

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — deliver the complete AI Council deliberation experience end-to-end. The value proposition requires the full orchestration loop (classify → assemble → deliberate → consensus → addendum) to be meaningful. A partial implementation (e.g., parallel queries without orchestration) would be indistinguishable from existing tools and fail to validate the core hypothesis.

**Resource Requirements:** Solo developer (Odi). The architecture is designed for single-developer execution: fork of existing battle-tested gemini-mcp Python codebase, file-based config (no database), MCP protocol handles transport (no custom networking), OpenRouter handles model access (no multi-provider integration), and the orchestrator is the host AI itself (no custom orchestration engine to build).

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Alex (solo founder first council) — full success path
- Jordan (tech lead pressure-test) — agent/model pinning + adversarial debate
- Sam (non-technical founder guardrails) — security-weighted assembly
- Team member (decision log reader) — council history access
- Power user (custom agent creation) — extensibility path

**Must-Have Capabilities:**
1. AI Council tool with complete deliberation loop
2. Full agent roster (35-42 hand-crafted agents across 3 categories)
3. Model-agnostic extended tools with cascading config
4. Configuration system (`.mcp.json` + agent manifest + capability matrix)
5. Council history with timestamped addendum files
6. Custom agent template and user-extensible agent directory

### Post-MVP Features

**Phase 2 (Growth):**
- Community agent registry for sharing and discovering agents
- Self-learning capability weights from session quality tracking
- Dynamic model discovery from OpenRouter's available model list
- Council history indexing with searchable topic/agent metadata
- Cross-council referencing — past conclusions as context for new councils

**Phase 3 (Expansion):**
- Industry-specific agent packs (FinTech, HealthTech, LegalTech)
- Self-improving model routing from accumulated quality data
- Team collaboration features — shared sessions, follow-ups, decision tracking
- IDE-native plugins beyond MCP (VS Code, JetBrains)
- Specialized pre-configured council modes (code review, architecture review, post-mortem)

### Risk Mitigation Strategy

**Technical Risks:** Orchestrator quality depends on host AI reasoning capability. Mitigated by designing clear orchestration prompts that work with current-generation models (Claude, GPT, Gemini). The MCP server provides tools and agent data; the host AI provides intelligence. No custom ML or orchestration engine required.

**Market Risks:** Multi-model deliberation is a new category — users may not understand the value until they experience it. Mitigated by zero-config first experience (install, add API key, run council) and the "aha moment" design: the first council surfaces a blind spot the user's primary model missed.

**Resource Risks:** Solo developer building a multi-component system. Mitigated by architecture choices that minimize custom code: MCP SDK handles protocol, OpenRouter handles models, file system handles persistence, host AI handles orchestration. The developer builds the agent roster, configuration system, and council tool interface — not an orchestration engine.

## Functional Requirements

### Council Deliberation

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
- FR14: Orchestrator weights agent opinions by domain relevance when resolving deadlocks (e.g., Tax Advisor's tax position outweighs Entrepreneur's tax opinion)
- FR15: Orchestrator synthesizes a detail-preserving narrative addendum capturing full reasoning, recommendations, and dissenting views
- FR16: System delivers council output as dual output — inline response in conversation AND saved markdown file
- FR17: User can override automatic council assembly by pinning specific agents and/or models via natural language in their prompt

### Agent System

- FR18: System ships with 35-42 hand-crafted agents across three categories: domain experts, technical builders, and end-user personas
- FR19: Each agent is defined in an individual Markdown file with name, role, identity, communication style, principles, domain expertise, and agent type flag
- FR20: Agent roster is indexed via CSV manifest (`agents/agent-manifest.csv`) for quick lookup and routing
- FR21: Expert agents are organized in demand tiers: Tier 1 (universal — 90%+ niche relevance), Tier 2 (high-demand — 60-80%), Tier 3 (niche specialists — 30-50%)
- FR22: User-type agents carry an inclusion flag allowing council selection logic to include/exclude them based on topic nature
- FR23: User can create custom agents following the same Markdown persona format and CSV manifest pattern
- FR24: Custom agents in a user directory extend or override built-in core agents
- FR25: Orchestrator discovers and includes custom agents alongside built-in roster during council assembly

### Model Routing & Configuration

- FR26: All tools route API calls through OpenRouter using a single API key
- FR27: System supports cascading model defaults: global default → per-tool override → per-invocation override
- FR28: Council tool maintains its own model pool array in configuration, separate from individual tool defaults
- FR29: Model-capability affinities are stored in an editable YAML config file (`config/model-capabilities.yaml`)
- FR30: System ships with sensible default capability weights that users can tune as models evolve

### Extended Tools

- FR31: All existing gemini-mcp utility tools function with configurable model selection via OpenRouter
- FR32: Each extended tool operates identically to its current implementation with the model being the only configurable difference
- FR33: Extended tools respect the cascading model default hierarchy

### Council History & Output

- FR34: System saves council addendums to a dedicated `council-history/` directory with timestamped filenames
- FR35: Addendum files are markdown-formatted narratives readable by non-technical stakeholders
- FR36: Council history persists as a project decision log accessible to all team members via the file system

### Installation & Configuration

- FR37: User can install the MCP server and run their first council session in under 10 minutes
- FR38: System requires only an OpenRouter API key in `.mcp.json` to function — zero additional configuration needed for default operation
- FR39: All configuration lives in the project directory — portable, self-contained, and version-controllable

## Non-Functional Requirements

### Performance

- API calls to OpenRouter complete within the model provider's standard response time; the MCP server adds no meaningful latency overhead beyond request marshaling
- Council assembly (topic classification + agent selection + model routing) completes in a single LLM call before deliberation begins
- Adaptive context management maintains deliberation quality across long sessions by summarizing at the 50% context window threshold

### Security

- OpenRouter API key is stored in `.mcp.json` (project-local, user-managed) — the system never transmits, logs, or exposes the key beyond OpenRouter API calls
- No user data, conversation content, or council history is transmitted to any service other than OpenRouter for model inference
- The system operates entirely locally — no backend service, no analytics, no telemetry

### Reliability

- Council sessions gracefully handle model unavailability — if a specific model is unreachable via OpenRouter, the orchestrator can reassign the agent to an available model from the pool
- Addendum files are written atomically to prevent partial output from interrupted sessions
- Configuration validation at startup surfaces invalid `.mcp.json`, missing API key, or malformed agent manifests with clear error messages

### Extensibility

- Agent persona format is documented and templated, enabling users to author new agents without modifying system code
- Capability weight matrix is data-driven (YAML config), allowing model routing adjustments without code changes
- MCP tool registration is modular — new tools can be added by following existing tool patterns

### Compatibility

- Compatible with any MCP-enabled host environment (Claude Code, Cursor, Windsurf, and future MCP clients)
- Compatible with any model available through OpenRouter's API
- Runs on any platform supporting Python 3.11+ (macOS, Linux, Windows)
