---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: ['brainstorming-session-2026-03-18-1625.md']
date: 2026-03-19
author: Odi
---

# Product Brief: aicouncil

## Executive Summary

AI Council is an MCP server that eliminates single-model AI bias by enabling multi-model, multi-agent deliberation directly within a developer's workflow. Instead of tab-hopping between ChatGPT, Claude, and Gemini to compare perspectives, developers and decision-makers can convene a council of domain-expert AI agents — each running on a different AI model — to discuss, debate, and reach consensus on any topic. Built on OpenRouter for unified multi-model access, AI Council brings the power of diverse AI reasoning into one tool that integrates directly with the user's codebase through the MCP protocol.

The product extends an existing Gemini MCP server into a model-agnostic platform with two modes of operation: individual tools powered by a configurable default model, and the flagship AI Council tool where an intelligent orchestrator assembles and mediates a panel of hand-crafted expert agents across multiple models to deliver well-reasoned, bias-reduced decisions.

---

## Core Vision

### Problem Statement

Developers and decision-makers relying on a single AI model inherit that model's biases, blind spots, and reasoning limitations — often without realizing it. Critical decisions about architecture, business strategy, tax obligations, pricing, and compliance are being made based on one model's perspective, leading to potentially flawed approaches baked in from the start.

Today, the workaround is painful: copy-paste the same prompt into multiple AI tools, manually compare outputs across browser tabs, and mentally synthesize the results. There is no mediation, no structured debate, no domain expertise layer, and no connection to the user's actual codebase. The process is slow, fragmented, and loses context between models.

### Problem Impact

For startup founders and developers, a biased early decision compounds. A flawed architecture choice, an overlooked tax obligation, or a misguided pricing strategy discovered months later costs orders of magnitude more to fix than getting it right from the start. The cost of single-model bias is not the wrong answer today — it's the cascade of wrong decisions built on top of it.

### Why Existing Solutions Fall Short

Several multi-model tools exist, but they share critical limitations:

- **Parallel runners, not deliberators** — they show you multiple outputs side by side but don't facilitate actual discussion, debate, or consensus between perspectives
- **No intelligent orchestration** — users must manually direct the conversation, decide who speaks next, and synthesize conclusions themselves
- **No domain expertise layer** — they return raw model outputs without persona-driven expert perspectives that frame responses in domain-specific context
- **No codebase integration** — web-based tools cannot reference the user's actual project files, making them useless for decisions that require code context
- **Single API complexity** — before OpenRouter, integrating multiple models required managing separate API keys, SDKs, and authentication flows

### Proposed Solution

AI Council is an MCP server that provides two modes of operation:

1. **Individual Tools** — Extended versions of existing utility tools (search, code review, etc.) that are now model-agnostic, powered by a configurable default model or per-tool model assignment via cascading configuration.

2. **AI Council Tool** — The flagship feature. When a user asks to discuss a topic, an intelligent orchestrator (the host AI, e.g., Claude in Claude Code) assembles a council of hand-crafted domain-expert agents, each assigned to a different AI model through capability-weighted random routing. The orchestrator acts as chairperson — directing turns, introducing debate when positions converge too easily, managing context length across models, and driving toward consensus. The result is a synthesized addendum delivered inline and saved as a persistent file.

The system ships with 35-42 hand-crafted agents across three categories (domain experts, technical builders, and end-user personas), with an open template for users to create custom agents. All model routing is powered by OpenRouter with a single API key.

### Key Differentiators

- **Orchestrator-mediated deliberation** — not just parallel outputs, but structured debate with an intelligent chairperson that shapes discourse quality
- **Codebase-aware through MCP** — council discussions can reference actual project files, making it uniquely valuable for development decisions
- **Model diversity as a feature** — the same agent persona on different models produces genuinely different reasoning, turning model selection into a deliberate debate strategy
- **Hand-crafted domain personas** — agents aren't generic prompt wrappers; they have distinct communication styles, principles, and expertise that make council discussions rich and authentic
- **Zero-config to full-control** — works autonomously by default, but users can override any aspect through natural language in their prompt
- **OpenRouter-enabled simplicity** — one API key unlocks the entire multi-model ecosystem, eliminating integration complexity

## Target Users

### Primary Users

**Persona 1: The Solo Technical Founder**
*"Alex" — Solo founder building an MVP*

Alex is a full-stack developer who quit their job to build a SaaS product. They handle everything — architecture, frontend, backend, pricing, legal, taxes, marketing. They're technically strong but constantly making decisions outside their expertise. They currently use Claude Code as their primary development tool and have ChatGPT open in another tab for a second opinion on important decisions. When facing a critical choice — like whether to use a monolith or microservices, how to price their product, or how to handle cross-border tax obligations — they spend 30-60 minutes copy-pasting the same question across multiple AI tools, mentally comparing outputs, and still feeling uncertain about the decision.

- **Motivation:** Make confident, well-informed decisions without hiring a team of advisors
- **Frustration:** Single AI models give confident but potentially biased answers; comparing across tools manually is slow and loses context
- **Success moment:** Running an AI Council session and getting a synthesized recommendation that covers angles they didn't even think to ask about
- **Daily fit:** AI Council lives in their MCP setup alongside their coding tools — they invoke it naturally when facing any decision, whether technical or business

**Persona 2: The Tech Lead at an Early-Stage Startup**
*"Jordan" — Lead developer at a seed-stage startup with a small team*

Jordan leads a 3-5 person engineering team and is responsible for architectural decisions that will shape the product for years. They report to a non-technical founder and need to justify technical choices with clear reasoning. They use AI assistants daily for code review and technical research but lack access to diverse specialist opinions — the startup can't afford a dedicated security engineer, data architect, and DevOps specialist. When making critical infrastructure decisions, they want to pressure-test their thinking against multiple expert perspectives before committing.

- **Motivation:** De-risk technical decisions with multi-perspective validation before committing the team
- **Frustration:** Carrying the weight of architectural decisions alone, with only one AI model's perspective to lean on
- **Success moment:** Presenting a council addendum to the founder that clearly shows multiple expert perspectives considered, trade-offs weighed, and a recommended path forward
- **Daily fit:** Uses individual MCP tools for routine dev work, invokes the council for major architectural decisions and technical strategy

**Persona 3: The Non-Technical Founder**
*"Sam" — Business founder using AI-assisted development tools*

Sam is not a developer but uses AI coding assistants like Cursor or Claude Code with MCP integrations to build and iterate on their product. They rely heavily on AI for both coding and business decisions. Their biggest fear is making a technical or business decision that seems right in the moment but turns out to be fundamentally flawed — and they wouldn't know until it's too late because they lack the domain expertise to evaluate the AI's advice critically.

- **Motivation:** Get trustworthy multi-expert guidance on decisions they can't evaluate on their own
- **Frustration:** Having no way to know if a single AI model's advice is good or dangerously wrong
- **Success moment:** The council surfaces a critical risk or alternative approach that a single model never mentioned — preventing a costly mistake
- **Daily fit:** Invokes the council frequently for both technical and business decisions, treats the addendum as their "advisory board meeting notes"

### Secondary Users

**Team Members & Collaborators**

Team members who don't directly invoke the AI Council but benefit from its outputs. They read council addendums shared by the primary user to understand the reasoning behind decisions. In a small startup, this might be a co-founder reviewing a technical architecture decision, a freelance designer understanding why a certain UX approach was chosen, or a part-time advisor catching up on strategic decisions made during the week. The file-based council history becomes a shared decision log that gives the whole team transparency into how and why choices were made.

### User Journey

**Discovery → Value Realization**

1. **Discovery:** User finds AI Council through MCP server directories, developer communities, or word of mouth from other founders who share how it helped them make better decisions. The pitch "multi-model AI debate for your important decisions" immediately resonates with anyone who's experienced single-model bias.

2. **Onboarding:** User installs the MCP server, adds their OpenRouter API key to `.mcp.json`, and the built-in agent roster works out of the box. First council session can happen within minutes of installation — zero configuration required beyond the API key.

3. **First Council Session:** User asks a question they've been wrestling with. The orchestrator assembles a council, runs the deliberation, and delivers a synthesized addendum. The user reads perspectives they never considered and realizes the depth gap between a single-model answer and a council discussion.

4. **Aha Moment:** The council surfaces a critical blind spot — a tax obligation, a security vulnerability, a pricing mistake, an architectural limitation — that the user's primary AI model never mentioned. This is the moment AI Council proves its value and becomes indispensable.

5. **Integration into Routine:** Council becomes the default for any decision with significant consequences. Individual tools handle daily dev tasks. The user develops an instinct for which decisions warrant a council and which don't. Council history files become a project decision log they reference regularly.

## Success Metrics

### User Success Metrics

The primary measure of AI Council's success is whether it helps users make better, more confident decisions. These metrics focus on outcomes and behaviors that indicate real value creation:

- **Decision Confidence** — Users make decisions they feel confident in after a council session, rather than second-guessing or seeking additional opinions elsewhere
- **Blind Spot Discovery** — The council surfaces risks, perspectives, or considerations that the user hadn't thought of and their primary AI model didn't mention
- **Time Efficiency** — Users spend less time on multi-model comparison than the manual tab-hopping alternative, while getting deeper and more structured analysis
- **Repeat Usage** — Users return to the council for subsequent decisions, indicating the first experience delivered genuine value
- **Actionability** — Council addendums produce concrete, actionable recommendations that users can immediately act on, not abstract discussion

### Business Objectives

AI Council is a utility tool — its success is measured by how well it serves its purpose, not by vanity metrics. The core business objective is:

**Be the default tool for important decisions in a developer's AI-assisted workflow.**

This means:
- The tool reliably produces high-quality, multi-perspective deliberation
- Setup is frictionless enough that a new user can run their first council session within minutes
- The agent roster covers the domains users actually need
- The tool integrates seamlessly into existing MCP-enabled workflows without disrupting them

### Key Performance Indicators

**Quality KPIs:**
- **Consensus rate** — Percentage of council sessions that reach unanimous agreement vs. tiered conclusions (both are valid outcomes, but tracking the ratio indicates discussion quality)
- **Addendum completeness** — Council sessions produce addendums with clear recommendations, supporting reasoning, and identified risks
- **Multi-perspective coverage** — Council discussions include perspectives from multiple agent categories (expert + builder + user) rather than single-category echo chambers

**Engagement KPIs:**
- **Sessions per user** — Repeat council usage indicates sustained value delivery
- **Council-to-individual tool ratio** — How often users choose the council over single-model tools for decision-making, indicating trust in the deliberation process
- **Agent roster utilization** — Distribution of which agents are summoned most frequently, informing future roster development priorities

**Utility KPIs:**
- **Time to first council** — How quickly a new user goes from installation to their first completed council session (target: under 10 minutes)
- **Session completion rate** — Percentage of council sessions that run to full addendum vs. abandoned mid-discussion
- **Community agent contributions** — Users creating and sharing custom agents indicates the extensibility model is working

## MVP Scope

### Core Features

**1. AI Council Tool — The Flagship Feature**
The complete multi-agent deliberation system as designed:
- LLM-powered topic classification to determine capability domains
- Orchestrator-driven council assembly with balanced multi-factor agent selection (topic relevance, category mix, domain coverage)
- Capability-weighted random model routing (60/40 moderate bias) via OpenRouter
- Duplicate agent roles on different models for perspective diversity
- 5:1 wildcard ratio for unexpected cross-domain insights
- Full auto assembly by default with natural language prompt override for pinning specific agents/models
- Orchestrator as chairperson — directing turns, introducing debate, managing context, driving toward consensus
- Adaptive context management with 50% context window threshold rule (full transcript vs. summarized)
- Free-form persona voice for all agent responses
- Orchestrator-driven dynamic tone shifting (debate vs. agreement-seeking)
- Orchestrator-judged convergence — no fixed round count
- One-sentence consensus round for efficient conclusion
- Unanimous-first consensus with tiered fallback
- Expertise-weighted opinion for deadlock resolution
- Detail-preserving free narrative addendum synthesized by orchestrator
- Dual output — inline response + saved markdown file

**2. Complete Agent Roster (35-42 Hand-Crafted Agents)**
Three-category agent architecture shipped from day one:

*Expert Agents (Tier 1 — Universal):* Software Architect, Backend Developer, DevOps/Infra Engineer, Product Manager, Business Strategist, Lawyer, Investor/VC Analyst, Sales Strategist, QA Engineer, HR Specialist

*Expert Agents (Tier 2 — High Demand):* Frontend Developer, Security Engineer, Data Scientist, UX Designer, Financial Advisor, Marketing Strategist, Accountant/Tax Advisor, Growth Hacker, Pricing Strategist, Customer Success Manager, Technical Writer, Compliance Officer

*Expert Agents (Tier 3 — Niche Specialists):* Statistician, Economist, Psychologist, and additional domain specialists as identified

*Builder Agents:* Technical implementation perspectives covering architecture, code, infrastructure, and testing

*User Agents (with inclusion flag):* Employee (Non-Technical), Entrepreneur/Small Business Owner, Student, Consumer/End Customer, Non-Technical Executive, Junior Developer, Freelancer/Solopreneur, and additional personas as identified

Each agent authored in Markdown with full persona: name, role, identity, communication style, principles, domain expertise, and agent type flag.

**3. Model-Agnostic Extended Tools**
All existing gemini-mcp tools converted to model-agnostic operation:
- Each tool functions identically to current implementation but model is configurable
- Cascading model defaults: global default → per-tool override → per-invocation override
- OpenRouter as the unified model gateway with single API key

**4. Configuration System**
- `.mcp.json` for model routing, tool config, and council model pool
- `agents/agent-manifest.csv` index + individual `agents/{name}.md` persona files
- `config/model-capabilities.yaml` for capability-weight matrix (shipped with sensible defaults)
- Project-only configuration — portable and version-controllable

**5. Council History**
- Dedicated directory for council addendum files (e.g., `./council-history/`)
- Timestamped filenames for chronological organization
- Persistent decision log that team members can reference

**6. User-Created Custom Agents**
- Open template for users to create custom agents following the same CSV + Markdown pattern
- User agents directory that extends or overrides built-in core agents
- Template and documentation for agent authoring

### Out of Scope for MVP

- **Community agent registry** — shared agent marketplace where users contribute and pull agents from a central repository
- **Self-learning capability weights** — tracking council quality to auto-adjust model-capability affinities over time
- **Dynamic model discovery** — auto-populating model pool from OpenRouter's available models
- **Council history indexing** — searchable index across past councils with topic/agent metadata (file-based history is MVP, structured indexing is v2)
- **Cross-council referencing** — loading past council conclusions as context for new councils

### MVP Success Criteria

The MVP is successful when:
- A user can install the MCP server, configure their OpenRouter API key, and run their first AI Council session in under 10 minutes
- The council produces a multi-perspective deliberation with distinct agent voices across different models that is noticeably richer than any single-model response
- The orchestrator effectively manages the discussion flow — directing turns, introducing debate when needed, and driving toward a clear conclusion
- The addendum is actionable and captures the full depth of the discussion
- All existing gemini-mcp tools function correctly with configurable model selection
- Users can create and use custom agents alongside the built-in roster

### Future Vision

If AI Council succeeds, it evolves into the **standard for multi-model AI deliberation in developer workflows**:

- **Community agent ecosystem** — a shared registry where domain experts contribute hand-crafted agents, reviewed and curated for quality. Specialized agent packs for industries (FinTech pack, HealthTech pack, LegalTech pack)
- **Self-improving model routing** — the system learns from council session quality to continuously refine its capability-weight matrix, getting smarter about which models serve which domains best
- **Cross-council intelligence** — past council decisions become referenceable context for new councils, building institutional knowledge that compounds over time
- **Team collaboration features** — shared council sessions where multiple team members participate, assign follow-ups, and track decision implementation
- **IDE-native integration** — beyond MCP, direct plugins for VS Code, JetBrains, and other IDEs that surface council recommendations contextually
- **Specialized council modes** — code review council, architecture review council, incident post-mortem council — pre-configured council templates optimized for common decision types
