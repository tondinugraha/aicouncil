"""Auto-extract and learn knowledge from analysis results."""

import logging
from typing import Any

from aicouncil.memory.schemas import KnowledgeEntry, KnowledgeType
from aicouncil.memory.store import KnowledgeStore

logger = logging.getLogger(__name__)


class KnowledgeLearner:
    """Extract and save knowledge from AI model analysis results."""

    def __init__(self, project_root: str | None = None):
        """Initialize learner."""
        self.store = KnowledgeStore(project_root)

    def learn_from_critique(
        self,
        result: dict[str, Any],
        content_type: str,
        file_paths: list[str] | None = None,
    ) -> list[str]:
        """Extract knowledge from a critique result."""
        learned_ids = []

        # Extract patterns from issues
        issues = result.get("issues", [])
        for issue in issues:
            if isinstance(issue, dict):
                category = issue.get("category", "")
                severity = issue.get("severity", "")

                # High severity issues become tracked issues
                if severity in ["critical", "high"]:
                    entry = KnowledgeEntry(
                        type="issue",
                        content=f"{category}: {issue.get('description', '')}",
                        context=f"Found during {content_type} critique",
                        tags=[category, severity, content_type],
                        references=file_paths or [],
                        confidence=0.8,
                        source_tool="critique",
                    )
                    entry_id = self.store.save(entry)
                    learned_ids.append(entry_id)

        # Extract patterns from strengths
        strengths = result.get("strengths", [])
        for strength in strengths:
            if isinstance(strength, str) and len(strength) > 20:
                # Check if it describes a pattern
                pattern_keywords = ["pattern", "consistent", "follows", "uses", "implements"]
                if any(kw in strength.lower() for kw in pattern_keywords):
                    entry = KnowledgeEntry(
                        type="pattern",
                        content=strength,
                        context=f"Identified as strength in {content_type} critique",
                        tags=["strength", content_type],
                        references=file_paths or [],
                        confidence=0.7,
                        source_tool="critique",
                    )
                    entry_id = self.store.save(entry)
                    learned_ids.append(entry_id)

        return learned_ids

    def learn_from_scan(
        self,
        scan_result: dict[str, Any],
        scan_type: str,
    ) -> list[str]:
        """Extract knowledge from a codebase scan result."""
        learned_ids = []

        # Learn project structure
        project = scan_result.get("project", {})
        if project:
            framework = project.get("framework")
            if framework:
                entry = KnowledgeEntry(
                    type="architecture",
                    content=f"Project uses {framework} framework",
                    context="Detected during codebase scan",
                    tags=["framework", framework],
                    references=[],
                    confidence=0.95,
                    source_tool="scan_codebase",
                )
                # Only save if we don't already know this
                existing = self.store.search(framework, limit=5)
                if not any(framework.lower() in e.content.lower() for e in existing):
                    entry_id = self.store.save(entry)
                    learned_ids.append(entry_id)

        # Learn from dependencies
        dependencies = scan_result.get("dependencies", [])
        key_deps = [d for d in dependencies if self._is_notable_dependency(d)]
        if key_deps:
            entry = KnowledgeEntry(
                type="architecture",
                content=f"Key dependencies: {', '.join(key_deps[:10])}",
                context="Extracted from project dependencies",
                tags=["dependencies"] + key_deps[:5],
                references=[],
                confidence=0.9,
                source_tool="scan_codebase",
            )
            entry_id = self.store.save(entry)
            learned_ids.append(entry_id)

        return learned_ids

    def learn_from_file_analysis(
        self,
        file_path: str,
        structure: dict[str, Any],
        critique_result: dict[str, Any] | None = None,
    ) -> list[str]:
        """Extract knowledge from file analysis."""
        learned_ids = []

        # Learn module relationships from imports
        imports = structure.get("imports", [])
        local_imports = [i for i in imports if isinstance(i, dict) and i.get("is_local")]

        if local_imports:
            import_modules = [i.get("module", "") for i in local_imports]
            entry = KnowledgeEntry(
                type="relation",
                content=f"{file_path} depends on: {', '.join(import_modules[:5])}",
                context="Extracted from import analysis",
                tags=["dependency", "imports"],
                references=[file_path] + import_modules[:3],
                confidence=0.95,
                source_tool="critique_file",
            )
            entry_id = self.store.save(entry)
            learned_ids.append(entry_id)

        # Learn patterns from code structure
        classes = structure.get("classes", [])

        if len(classes) > 3:
            class_names = [c.get("name", "") for c in classes if isinstance(c, dict)]
            # Try to detect patterns from naming
            pattern = self._detect_naming_pattern(class_names)
            if pattern:
                entry = KnowledgeEntry(
                    type="convention",
                    content=f"Class naming pattern: {pattern}",
                    context=f"Detected in {file_path}",
                    tags=["naming", "convention", "class"],
                    references=[file_path],
                    confidence=0.7,
                    source_tool="critique_file",
                )
                entry_id = self.store.save(entry)
                learned_ids.append(entry_id)

        return learned_ids

    def learn_explicit(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        tags: list[str] | None = None,
        references: list[str] | None = None,
        confidence: float = 0.9,
    ) -> str:
        """Explicitly save a piece of knowledge."""
        entry = KnowledgeEntry(
            type=knowledge_type,
            content=content,
            context="Explicitly saved by user",
            tags=tags or [],
            references=references or [],
            confidence=confidence,
            source_tool="remember",
            validated=True,  # User-provided knowledge is validated
        )
        return self.store.save(entry)

    def _is_notable_dependency(self, dep: str) -> bool:
        """Check if a dependency is notable enough to track."""
        notable_patterns = [
            # Frameworks
            "react",
            "vue",
            "angular",
            "svelte",
            "next",
            "nuxt",
            "django",
            "flask",
            "fastapi",
            "express",
            "nest",
            # Databases
            "postgres",
            "mysql",
            "mongo",
            "redis",
            "sqlite",
            "prisma",
            "sequelize",
            "sqlalchemy",
            "typeorm",
            # Auth
            "passport",
            "jwt",
            "oauth",
            "auth0",
            # Testing
            "jest",
            "pytest",
            "mocha",
            "cypress",
            "playwright",
            # Build
            "webpack",
            "vite",
            "esbuild",
            "rollup",
        ]
        dep_lower = dep.lower()
        return any(pattern in dep_lower for pattern in notable_patterns)

    def _detect_naming_pattern(self, names: list[str]) -> str | None:
        """Try to detect naming patterns from a list of names."""
        if len(names) < 3:
            return None

        # Check for suffixes
        suffixes = [
            "Service",
            "Controller",
            "Repository",
            "Handler",
            "Manager",
            "Factory",
            "Provider",
        ]
        for suffix in suffixes:
            if sum(1 for n in names if n.endswith(suffix)) >= 2:
                return f"Uses {suffix} suffix pattern"

        # Check for prefixes
        prefixes = ["Base", "Abstract", "I"]  # I for interfaces
        for prefix in prefixes:
            if sum(1 for n in names if n.startswith(prefix)) >= 2:
                return f"Uses {prefix} prefix pattern"

        return None
