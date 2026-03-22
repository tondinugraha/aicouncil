"""
AI Council - MCP server entry point.

Multi-model deliberation MCP server routing through OpenRouter.
Server.py is a thin registry — all tool logic lives in tools/ modules.
# v0.0.2 - release pipeline validated
"""

import logging

from mcp.server.fastmcp import FastMCP

from aicouncil.tools.analysis import (
    brainstorm,
    challenge_assumptions,
    critique,
    find_gaps,
    propose_alternatives,
    validate,
)
from aicouncil.tools.codebase import analyze_dependencies, critique_file, scan_codebase
from aicouncil.tools.council import ai_council, council_speak, save_council_addendum
from aicouncil.tools.memory import forget, recall, remember, show_knowledge_summary
from aicouncil.tools.research import research_assist, research_document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    "aicouncil",
    instructions=(
        "AI partner for brainstorming, critique, and validation.\n\n"
        "## Council Deliberation Rules\n"
        "When orchestrating council deliberations (ai_council + council_speak):\n"
        "- CRITICAL: Call council_speak ONE AGENT AT A TIME, sequentially. "
        "NEVER call multiple council_speak in parallel. Each agent must speak, "
        "have their response displayed, and have their response added to the "
        "session history BEFORE the next agent speaks. This applies to ALL "
        "rounds including Round 1. The deliberation process is the product — "
        "sequential pacing simulates a real debate.\n"
        "- After each council_speak call, display the agent's response VERBATIM. "
        "Never summarize, paraphrase, shorten, or editorialize the response.\n"
        "- Format: **Agent Name** (model):\\n\\n[exact response text, unchanged]"
        "\\n\\n**Stance:** [stance text]\n"
        "- Add your own commentary or synthesis ONLY after all agents in a round "
        "have spoken, as a separate block.\n"
        "- Drive multiple deliberation rounds, highlight agreements and "
        "disagreements, and present a final verdict table."
    ),
)

# ============================================================================
# Register all tools — tool modules are MCP-agnostic plain async functions
# ============================================================================

# Council tools
mcp.tool()(ai_council)
mcp.tool()(council_speak)
mcp.tool()(save_council_addendum)

# Analysis tools
mcp.tool()(critique)
mcp.tool()(brainstorm)
mcp.tool()(validate)
mcp.tool()(challenge_assumptions)
mcp.tool()(find_gaps)
mcp.tool()(propose_alternatives)

# Research tools
mcp.tool()(research_assist)
mcp.tool()(research_document)

# Codebase tools
mcp.tool()(scan_codebase)
mcp.tool()(critique_file)
mcp.tool()(analyze_dependencies)

# Memory tools
mcp.tool()(remember)
mcp.tool()(recall)
mcp.tool()(forget)
mcp.tool()(show_knowledge_summary)


# ============================================================================
# Main Entry Point
# ============================================================================


def main() -> None:
    """Run the AI Council server."""
    from aicouncil.scaffold import ensure_scaffold

    logger.info("Starting AI Council Server...")
    ensure_scaffold()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
