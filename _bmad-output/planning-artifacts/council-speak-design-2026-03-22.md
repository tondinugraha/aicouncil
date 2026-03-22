# Council Speak — Real-Time Deliberation Tool

**Date:** 2026-03-22
**Status:** Implemented, pending live test
**Session context:** First live test of the AI Council MCP server exposed a fundamental UX flaw in the deliberation architecture.

---

## Problem

The `ai_council` tool only **assembles** a council (selects agents, assigns models, returns orchestration instructions). It does not provide any mechanism for agents to actually **speak**. There was no tool to send a prompt to a specific model with a specific agent persona and get back that agent's response.

### What happened during the first live test

1. Called `ai_council` — assembled a 5-agent council successfully.
2. To simulate deliberation, the host AI had to abuse the standalone analysis tools (`brainstorm`, `critique`, `challenge_assumptions`, `find_gaps`, `propose_alternatives`) as proxies for agent voices.
3. These tools are **not part of the council flow** — they use a generic system persona, not the agent's persona. They return structured analysis results, not in-character deliberation responses.
4. The host AI then synthesized all results backstage and presented a pre-written narrative as if a debate had occurred.

### Why this is wrong

- **No real-time debate.** The user sees nothing until the entire synthesis is complete.
- **No agent voices.** The standalone tools use their own system persona, not the council agent personas.
- **No call-and-response.** Agents can't react to what other agents said — there's no conversation history mechanism.
- **No user control.** The user can't intervene between rounds, redirect the discussion, or decide when to stop.

---

## Solution

### New tool: `council_speak`

A single MCP tool that makes one agent speak in one round, using the agent's actual persona and assigned model.

### API

```python
async def council_speak(
    agent_name: str,           # From assembly result
    agent_role: str,           # From assembly result
    agent_persona: str,        # Full markdown persona from assembly
    model: str,                # Assigned model from assembly
    topic: str,                # Council topic
    round_number: int = 1,     # Current round (1-based)
    conversation_history: list[dict[str, str]] | None = None,
        # Prior agent statements: [{"agent_name": ..., "agent_role": ..., "response": ...}]
    instruction: str = "",     # Chairperson direction for this round
    session_id: str = "",      # For log correlation
) -> CouncilSpeakResult
```

### Response schema

```python
class CouncilSpeakResult(BaseModel):
    agent_name: str       # Stamped from input (not LLM-generated)
    agent_role: str       # Stamped from input
    model: str            # Stamped from input
    response: str         # Full natural language response in agent's voice
    stance: str           # One-line stance summary
    key_points: list[str] # 2-5 extractable key points
```

### Key design decisions

1. **Agent persona IS the system prompt.** Unlike other tools that use `BasePrompts.SYSTEM_PERSONA`, `council_speak` uses the agent's own markdown persona as the system context. This ensures the model speaks in-character.

2. **Metadata is stamped, not LLM-generated.** `agent_name`, `agent_role`, and `model` are overwritten from the input parameters after the LLM call. The LLM fills `response`, `stance`, and `key_points`.

3. **Conversation history enables real debate.** The `conversation_history` parameter passes prior agent statements so each agent can agree, disagree, or build on what others said.

4. **Chairperson instruction enables orchestration.** The host AI can direct specific agents with instructions like "play devil's advocate" or "respond to the Architect's security concern."

---

## Intended deliberation flow

```
User: "Have the council discuss X"

Host AI (Chairperson):
  1. ai_council(topic=X) → assembly result with agents + models

  2. For each round:
     For each agent:
       council_speak(agent, topic, round, history) → agent response
       Display: "### Agent Name (model)\n{response}"
       Append to conversation_history

     Display: "## Orchestrator\nThe council is [converging/diverging].
               Continue to next round, or proceed to consensus?"

  3. User decides: more rounds or consensus

  4. Final round: council_speak with instruction="Give your final
     one-sentence position and most important caveat"

  5. save_council_addendum(session_id, topic, agents, narrative)
```

### Expected output format (what the user sees)

```markdown
## Round 1

### Business Strategist (anthropic/claude-sonnet-4)
[actual model response in agent's voice]

### Software Architect (openai/gpt-4.1)
[actual model response in agent's voice]

### Freelancer (openai/gpt-4.1)
[actual model response in agent's voice]

## Orchestrator
The council is showing early convergence toward X.
Do you want another round, or should we proceed to consensus?
```

---

## Files modified

| File | Change |
|------|--------|
| `src/aicouncil/schemas/responses.py` | Added `CouncilSpeakResult` model |
| `src/aicouncil/tools/__init__.py` | Added `build_council_speak_prompt()` |
| `src/aicouncil/tools/council.py` | Added `council_speak()` function |
| `src/aicouncil/server.py` | Registered `council_speak` tool |

### No changes to

- `client.py` — uses existing `OpenRouterClient.generate()` with `response_model`
- `council/assembler.py` — assembly logic unchanged
- `council/schemas.py` — council assembly schemas unchanged
- Existing tools — brainstorm, critique, etc. remain independent standalone tools

---

## Boundary compliance

| Rule | Status |
|------|--------|
| All HTTP through `client.py` | Yes — uses `OpenRouterClient.generate()` |
| Tool logic in `tools/`, not `server.py` | Yes — logic in `tools/council.py` |
| Returns Pydantic model, not raw dict/string | Yes — returns `CouncilSpeakResult` |
| Uses custom exception hierarchy | Yes — raises `CouncilError` |
| Registered via `server.py` registry | Yes — `mcp.tool()(council_speak)` |

---

## Test status

- All 375 existing tests pass
- Lint clean (ruff check + ruff format)
- Import verified: `from aicouncil.tools.council import council_speak` succeeds
- **Pending:** Live test with actual MCP server restart

---

## Future considerations

- **Parallel agent calls:** Decided against. All rounds (including Round 1) must be sequential — each agent builds on previous speakers, and sequential pacing simulates a real debate. The deliberation process IS the product.
- **Streaming:** The current architecture returns complete responses. True streaming would require SSE or a different transport, which is out of scope for stdio MCP.
- **Round management:** Could add a `council_round` tool that calls all agents in a round and returns all responses at once. Trade-off: simpler for the host AI, but less granular control.
