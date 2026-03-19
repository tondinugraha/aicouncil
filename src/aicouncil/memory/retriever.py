"""Knowledge retrieval for building context."""

import logging
from pathlib import Path

from aicouncil.memory.schemas import KnowledgeEntry
from aicouncil.memory.store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """Retrieve relevant knowledge for tool context."""

    def __init__(self, project_root: str | Path | None = None):
        """Initialize retriever."""
        self.store = KnowledgeStore(project_root)

    def get_context_for_file(
        self,
        file_path: str,
        include_related: bool = True,
        limit: int = 15,
    ) -> list[KnowledgeEntry]:
        """Get knowledge relevant to a specific file."""
        results = []

        # Direct references to this file
        direct = self.store.query(references=[file_path], limit=limit)
        results.extend(direct)

        if include_related:
            # Extract potential tags from file path
            path_parts = file_path.lower().replace("\\", "/").split("/")
            potential_tags = [
                p for p in path_parts if p and p not in ["src", "lib", "app", "index", "main"]
            ]

            # Also add the file name without extension
            if "." in path_parts[-1]:
                potential_tags.append(path_parts[-1].rsplit(".", 1)[0])

            # Search by tags
            if potential_tags:
                tag_results = self.store.query(tags=potential_tags, limit=limit)
                for entry in tag_results:
                    if entry not in results:
                        results.append(entry)

        return results[:limit]

    def get_context_for_scan(
        self,
        scan_type: str = "overview",
        file_paths: list[str] | None = None,
        limit: int = 20,
    ) -> list[KnowledgeEntry]:
        """Get knowledge relevant to a codebase scan."""
        results = []

        # For security scans, prioritize security-related knowledge
        if scan_type == "security":
            security_tags = [
                "security",
                "auth",
                "authentication",
                "authorization",
                "vulnerability",
                "injection",
            ]
            results.extend(self.store.query(tags=security_tags, limit=limit))

        # Get architecture knowledge for overview
        if scan_type in ["overview", "full"]:
            arch = self.store.query(knowledge_type="architecture", limit=10)
            results.extend([e for e in arch if e not in results])

            patterns = self.store.query(knowledge_type="pattern", limit=10)
            results.extend([e for e in patterns if e not in results])

        # Get file-specific knowledge
        if file_paths:
            for path in file_paths[:10]:  # Limit paths checked
                file_knowledge = self.get_context_for_file(path, include_related=False, limit=3)
                results.extend([e for e in file_knowledge if e not in results])

        # Get issues
        issues = self.store.query(knowledge_type="issue", limit=5)
        results.extend([e for e in issues if e not in results])

        # Get conventions
        conventions = self.store.query(knowledge_type="convention", limit=5)
        results.extend([e for e in conventions if e not in results])

        return results[:limit]

    def get_context_for_architecture(self, limit: int = 25) -> list[KnowledgeEntry]:
        """Get knowledge specifically for architecture analysis."""
        results = []

        # Architecture knowledge
        arch = self.store.query(knowledge_type="architecture", limit=15)
        results.extend(arch)

        # Patterns
        patterns = self.store.query(knowledge_type="pattern", limit=10)
        results.extend([e for e in patterns if e not in results])

        # Relations
        relations = self.store.query(knowledge_type="relation", limit=10)
        results.extend([e for e in relations if e not in results])

        return results[:limit]

    def get_context_for_code(self, limit: int = 20) -> list[KnowledgeEntry]:
        """Get knowledge for code critique/analysis."""
        results = []

        # Patterns and conventions are most relevant
        patterns = self.store.query(knowledge_type="pattern", limit=10)
        results.extend(patterns)

        conventions = self.store.query(knowledge_type="convention", limit=10)
        results.extend([e for e in conventions if e not in results])

        # Issues to watch for
        issues = self.store.query(knowledge_type="issue", limit=5)
        results.extend([e for e in issues if e not in results])

        return results[:limit]

    def format_for_prompt(self, entries: list[KnowledgeEntry]) -> str:
        """Format knowledge entries for inclusion in a prompt."""
        if not entries:
            return ""

        sections = {
            "pattern": [],
            "architecture": [],
            "relation": [],
            "issue": [],
            "convention": [],
            "insight": [],
        }

        for entry in entries:
            sections[entry.type].append(entry)

        parts = ["## Project Knowledge (from previous analysis)\n"]

        type_labels = {
            "pattern": "Code Patterns",
            "architecture": "Architecture",
            "relation": "Module Relations",
            "issue": "Known Issues",
            "convention": "Conventions",
            "insight": "Insights",
        }

        for ktype, label in type_labels.items():
            if sections[ktype]:
                parts.append(f"\n### {label}")
                for entry in sections[ktype]:
                    refs = f" (refs: {', '.join(entry.references[:3])})" if entry.references else ""
                    parts.append(f"- {entry.content}{refs}")

        return "\n".join(parts)

    def should_load_knowledge(self, tool_name: str, params: dict) -> bool:
        """Determine if knowledge should be loaded for this tool call."""
        # Always load for codebase tools
        codebase_tools = [
            "scan_codebase",
            "critique_file",
            "analyze_dependencies",
            "remember",
            "recall",
            "show_knowledge_summary",
            "forget",
        ]
        if tool_name in codebase_tools:
            return True

        # Conditional loading based on content_type
        if tool_name in ["critique", "find_gaps"]:
            content_type = params.get("content_type", "general")
            return content_type in ["code", "architecture"]

        # Technical brainstorming benefits from code knowledge
        if tool_name == "brainstorm":
            return params.get("brainstorm_type") == "technical"

        # Propose alternatives for technical/architecture
        if tool_name == "propose_alternatives":
            context = params.get("context", "").lower()
            return any(
                kw in context for kw in ["code", "architecture", "technical", "implementation"]
            )

        return False
