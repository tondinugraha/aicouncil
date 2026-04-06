# AI Council

**Multi-model deliberation MCP server that assembles councils of diverse AI agents to debate, analyze, and decide — powered by OpenRouter.**

AI Council routes requests across multiple LLM providers (Claude, GPT-4, Gemini, DeepSeek, Llama) and combines them with 40 specialized agent personas to conduct structured multi-round deliberations. Think of it as a boardroom of AI experts that debate your questions from different angles before reaching a verdict.

---

## Key Features

- **Multi-Model Routing** — Capability-weighted model assignment across 5+ LLMs via OpenRouter
- **40 Built-in Agents** — Domain experts, builders, and end-user perspectives across coding, business, legal, finance, security, and more
- **Structured Deliberation** — Multi-round debates with dynamic tone shifting, convergence detection, and consensus tracking
- **14 MCP Tools** — Council assembly, critique, brainstorming, validation, research, codebase analysis, and persistent memory
- **Persistent Knowledge** — JSONL-based memory system that learns from analyses across sessions
- **Auto-Scaffolding** — Creates a `.aicouncil/` directory with config, agents, and knowledge store on first run
- **Fully Customizable** — Override models, agents, capability weights, and per-tool routing via YAML config

---

## How It Works

```
Topic → Classify Domains → Select Agents → Assign Models → Deliberate → Verdict
```

1. **Topic Classification** — An LLM classifies your topic into weighted domains (e.g., `coding: 0.95, architecture: 0.90`)
2. **Agent Selection** — Scores 40 agents by domain relevance, balancing experts (60%), builders (25%), and users (15%), plus wildcard cross-domain perspectives
3. **Model Assignment** — Uses capability-weighted routing (60% best-fit, 40% weighted random) to assign the right LLM to each agent
4. **Multi-Round Deliberation** — Agents speak sequentially, with the host AI acting as chairperson. Dynamic tone shifts prevent premature consensus
5. **Verdict & Persistence** — Final positions are captured, and the full deliberation is saved as an addendum for future reference

---

## Installation

### Prerequisites

- Python 3.11+
- [OpenRouter API key](https://openrouter.ai/)
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
git clone https://github.com/AiCouncil-ai/aicouncil.git
cd aicouncil
uv sync
```

Or with pip:

```bash
pip install -e .
```

### Configure MCP

Add to your `.mcp.json` (Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "aicouncil": {
      "command": "uv",
      "args": ["run", "aicouncil"],
      "env": {
        "OPENROUTER_API_KEY": "sk-or-v1-your-key-here"
      }
    }
  }
}
```

On first run, AI Council auto-scaffolds a `.aicouncil/` directory with default config, agent templates, and knowledge store.

---

## MCP Tools

### Council Deliberation

| Tool | Description |
|------|-------------|
| `ai_council` | Assemble a council of agents for a topic |
| `council_speak` | Get a specific agent's response in the current round |
| `save_council_addendum` | Persist the full deliberation record |

### Analysis

| Tool | Description |
|------|-------------|
| `critique` | Find flaws in code, architecture, PRDs, or designs |
| `brainstorm` | Generate ideas with pros/cons analysis |
| `validate` | Check completeness, consistency, and feasibility |
| `challenge_assumptions` | Stress-test underlying assumptions |
| `find_gaps` | Identify missing elements or blind spots |
| `propose_alternatives` | Compare alternative approaches |

### Research

| Tool | Description |
|------|-------------|
| `research_assist` | Research any topic (quick / thorough / exhaustive) |
| `research_document` | Analyze documents with multi-model perspectives |

### Codebase

| Tool | Description |
|------|-------------|
| `scan_codebase` | Analyze project structure, patterns, and issues |
| `critique_file` | Deep file review with import context |
| `analyze_dependencies` | Detect circular deps, hub modules, isolation |

### Memory

| Tool | Description |
|------|-------------|
| `remember` | Save a knowledge entry |
| `recall` | Search the knowledge base |
| `forget` | Remove a knowledge entry |
| `show_knowledge_summary` | View all stored knowledge |

---

## Built-in Agents

AI Council ships with 40 agent personas organized by type and domain:

| Type | Allocation | Agents |
|------|-----------|--------|
| **Expert** (domain specialists) | 60% | Software Architect, Security Engineer, Data Scientist, Economist, Lawyer, Tax Advisor, Financial Advisor, Actuary, Statistician, Compliance Officer, Medical Professional, Psychologist, ... |
| **Builder** (practitioners) | 25% | Backend Developer, Frontend Developer, Fullstack Developer, Mobile Developer, DevOps Engineer, Database Engineer, QA Engineer, Product Manager, UX Designer, Technical Writer, ... |
| **User** (end-user perspectives) | 15% | Consumer, Student, Employee, Parent, Freelancer, Entrepreneur, Investor, ... |

Each agent has defined domains, tier priority, and a detailed persona that shapes how they communicate and what they prioritize.

---

## Configuration

### Model Resolution

AI Council uses a **three-layer cascade** to determine which model handles a request:

```
Per-invocation override  →  Per-tool override  →  Global default
```

1. **Per-invocation** — Pass a model directly when calling a tool (highest priority)
2. **Per-tool** — Set in `tool_overrides` to always route a specific tool to a specific model
3. **Global default** — The `default_model` fallback used when no override is set

### Council Model Routing

Council deliberations work differently from single-tool calls. When a council is assembled, each agent is assigned a model from the **model pool** using capability-weighted routing:

1. **Define the pool** — List which models are available for council assignment in `model_pool`
2. **Set capability weights** — Score each model's strength per domain (coding, analysis, creative, business, legal, finance, etc.) on a 0.0-1.0 scale
3. **Automatic assignment** — The assembler matches each agent's domain to the best-scoring model:
   - **60% of the time**: Picks the top-scoring model for that domain
   - **40% of the time**: Weighted random from the pool (introduces model diversity)

This means a Security Engineer agent discussing a coding topic is more likely to get Claude (coding: 0.95), while an Economist discussing a finance topic is more likely to get GPT-4 (finance: 0.80). The randomness ensures you don't get the same model composition every time.

**To change which models the council uses**, edit the `model_pool` and `capability_weights` in `.aicouncil/config.yaml`:

```yaml
# Only these models will be assigned to council agents
model_pool:
  - "anthropic/claude-sonnet-4"
  - "openai/gpt-4.1"
  - "google/gemini-2.5-pro"
  - "deepseek/deepseek-r1"
  - "meta-llama/llama-4-maverick"

# How good each model is at each domain (0.0-1.0)
# Models without weights can still be in the pool but won't benefit from smart routing
capability_weights:
  "anthropic/claude-sonnet-4":
    context_window: 200000
    coding: 0.95
    analysis: 0.90
    creative: 0.85
    business: 0.80
    legal: 0.70
    finance: 0.75
  "openai/gpt-4.1":
    context_window: 1048576
    coding: 0.90
    analysis: 0.90
    creative: 0.85
    business: 0.85
    legal: 0.75
    finance: 0.80
  "google/gemini-2.5-pro":
    context_window: 1048576
    coding: 0.90
    analysis: 0.85
    creative: 0.80
    business: 0.80
    legal: 0.70
    finance: 0.75
  "deepseek/deepseek-r1":
    context_window: 163840
    coding: 0.90
    analysis: 0.90
    creative: 0.70
    business: 0.65
    legal: 0.60
    finance: 0.70
  "meta-llama/llama-4-maverick":
    context_window: 1048576
    coding: 0.80
    analysis: 0.75
    creative: 0.80
    business: 0.70
    legal: 0.60
    finance: 0.65
```

To add a new model, add it to both `model_pool` and `capability_weights`. To remove one, remove it from `model_pool` (weights are ignored for models not in the pool).

### Per-Tool Model Overrides

Route specific analysis tools to a preferred model (does not affect council agent assignment):

```yaml
tool_overrides:
  critique: "openai/gpt-4.1"
  brainstorm: "anthropic/claude-sonnet-4"
  research_assist: "google/gemini-2.5-pro"
```

### Full Config Example (`.aicouncil/config.yaml`)

```yaml
default_model: "anthropic/claude-sonnet-4"
temperature: 0.7
max_output_tokens: 8192
timeout_seconds: 120

tool_overrides:
  critique: "openai/gpt-4.1"

model_pool:
  - "anthropic/claude-sonnet-4"
  - "openai/gpt-4.1"
  - "google/gemini-2.5-pro"

capability_weights:
  "anthropic/claude-sonnet-4":
    context_window: 200000
    coding: 0.95
    analysis: 0.90
    creative: 0.85
    business: 0.80
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API credentials | Yes |
| `OPENROUTER_MODEL` | Override default model | No |
| `OPENROUTER_TEMPERATURE` | Generation temperature (0.0-2.0) | No |
| `OPENROUTER_MAX_TOKENS` | Max output tokens | No |
| `OPENROUTER_TIMEOUT` | API timeout in seconds | No |
| `OPENROUTER_DEFAULT_CONTEXT` | Default project context | No |

### Custom Agents

Create custom agents in `.aicouncil/agents/your-agent.md`:

```markdown
---
name: "Your Custom Expert"
role: "Principal Domain Expert"
type: "expert"
tier: 1
domains: ["your_domain", "related_domain"]
include_flag: true
---

You are a domain expert who...
```

---

## Project Structure

```
src/aicouncil/
├── server.py              # MCP server entry point
├── client.py              # OpenRouter async HTTP client
├── config.py              # YAML + env configuration
├── agent_loader.py        # Agent roster management (CSV + Markdown)
├── scaffold.py            # Auto-scaffolding of .aicouncil/
├── council/
│   ├── assembler.py       # Core assembly algorithm
│   ├── session.py         # In-memory session cache
│   ├── context.py         # Context window management
│   └── history.py         # Deliberation persistence
├── tools/
│   ├── council.py         # Council deliberation tools
│   ├── analysis.py        # Critique, brainstorm, validate
│   ├── research.py        # Research tools
│   ├── codebase.py        # Code analysis tools
│   └── memory.py          # Knowledge persistence tools
├── memory/
│   ├── store.py           # JSONL knowledge storage
│   ├── learner.py         # Insight extraction
│   └── retriever.py       # Context retrieval
├── agents/
│   ├── agent-manifest.csv # Agent registry
│   └── *.md               # 40 agent persona definitions
├── prompts/               # Prompt templates
├── scanner/               # Code analysis utilities
└── schemas/               # Pydantic models
```

---

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
pytest

# Lint & format
ruff check src/
ruff format src/
```

---

## Architecture Highlights

- **Pure Logic Separation** — Assembly logic is pure (no I/O); tools handle orchestration; server is a thin registry
- **Capability-Weighted Routing** — 60% deterministic (best model for domain) + 40% probabilistic (weighted random) balances quality with diversity
- **Dynamic Deliberation** — No fixed round count; tone shifts adversarial if consensus forms too early, agreement-seeking when positions stabilize
- **Session Caching** — Up to 50 active councils in memory, reducing redundant API calls during multi-round debates
- **Cross-Session Learning** — JSONL knowledge store with tag-based retrieval injects relevant context into future analyses

---

## License

MIT
