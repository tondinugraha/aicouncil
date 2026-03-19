"""JSONL-based knowledge storage."""

import hashlib
import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from aicouncil.memory.schemas import KnowledgeEntry, KnowledgeSummary, KnowledgeType

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """Persistent knowledge storage using JSONL files."""

    MEMORY_DIR = ".aicouncil"
    KNOWLEDGE_DIR = "knowledge"
    INDEX_FILE = "index.json"
    README_CONTENT = """# AI Council Knowledge Store

This directory contains learned knowledge about your project that AI Council
uses to provide better, project-specific analysis and recommendations.

## Structure

- `knowledge/` - JSONL files containing learned insights by type
  - `patterns.jsonl` - Code patterns discovered
  - `architecture.jsonl` - Architectural insights
  - `relations.jsonl` - File/module relationships
  - `issues.jsonl` - Known issues and tech debt
  - `conventions.jsonl` - Project conventions
  - `insights.jsonl` - General insights
- `index.json` - Quick lookup index
- `config.yaml` - Memory configuration

## Should I commit this?

**Yes!** Sharing project knowledge across your team helps everyone get
better AI assistance. The knowledge is specific to your codebase.

## Clearing knowledge

Delete specific entries using the `forget` tool, or delete this entire
directory to start fresh.
"""

    def __init__(self, project_root: str | Path | None = None):
        """Initialize knowledge store."""
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Try to detect project root from environment or by scanning
            import os

            env_root = os.environ.get("PROJECT_ROOT")
            if env_root:
                self.project_root = Path(env_root)
            else:
                # Use project detector to find actual project root
                try:
                    from aicouncil.scanner import ProjectDetector

                    detector = ProjectDetector()
                    info = detector.detect()
                    self.project_root = Path(info.root)
                except Exception:
                    self.project_root = Path.cwd()

        self.memory_dir = self.project_root / self.MEMORY_DIR
        self.knowledge_dir = self.memory_dir / self.KNOWLEDGE_DIR
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure directory structure exists."""
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True)
            # Create README
            readme_path = self.memory_dir / "README.md"
            readme_path.write_text(self.README_CONTENT)
            logger.info(f"Created AI Council knowledge store at {self.memory_dir}")

        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir()

    def _get_file_for_type(self, knowledge_type: KnowledgeType) -> Path:
        """Get the JSONL file path for a knowledge type."""
        filename = f"{knowledge_type}s.jsonl"
        return self.knowledge_dir / filename

    def save(self, entry: KnowledgeEntry) -> str:
        """Save a knowledge entry. Returns entry ID."""
        entry.updated_at = datetime.utcnow()

        # Calculate file hashes for referenced files
        for ref in entry.references:
            ref_path = self.project_root / ref
            if ref_path.exists():
                try:
                    content = ref_path.read_bytes()
                    entry.file_hashes[ref] = hashlib.md5(content).hexdigest()[:8]
                except Exception:
                    pass

        file_path = self._get_file_for_type(entry.type)

        # Check for duplicate/update
        existing = self.get(entry.id)
        if existing:
            # Update existing entry
            entries = list(self._read_all(entry.type))
            entries = [e for e in entries if e.id != entry.id]
            entries.append(entry)
            self._write_all(entry.type, entries)
        else:
            # Append new entry
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")

        self._update_index()
        logger.info(f"Saved knowledge entry: {entry.id} ({entry.type})")
        return entry.id

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """Get a specific entry by ID."""
        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            for entry in self._read_all(knowledge_type):
                if entry.id == entry_id:
                    return entry
        return None

    def delete(self, entry_id: str) -> bool:
        """Delete an entry by ID."""
        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            entries = list(self._read_all(knowledge_type))
            original_count = len(entries)
            entries = [e for e in entries if e.id != entry_id]

            if len(entries) < original_count:
                self._write_all(knowledge_type, entries)
                self._update_index()
                logger.info(f"Deleted knowledge entry: {entry_id}")
                return True

        return False

    def query(
        self,
        knowledge_type: KnowledgeType | None = None,
        tags: list[str] | None = None,
        references: list[str] | None = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[KnowledgeEntry]:
        """Query knowledge entries."""
        results = []

        types_to_search = (
            [knowledge_type]
            if knowledge_type
            else ["pattern", "architecture", "relation", "issue", "convention", "insight"]
        )

        for ktype in types_to_search:
            for entry in self._read_all(ktype):
                # Filter by confidence
                if entry.confidence < min_confidence:
                    continue

                # Filter by tags
                if tags:
                    if not any(tag in entry.tags for tag in tags):
                        continue

                # Filter by references
                if references:
                    if not any(ref in entry.references for ref in references):
                        continue

                results.append(entry)

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        # Sort by confidence and recency
        results.sort(key=lambda e: (e.confidence, e.updated_at), reverse=True)
        return results[:limit]

    def search(self, query: str, limit: int = 20) -> list[KnowledgeEntry]:
        """Search knowledge by text content. Supports word-based matching."""
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) >= 2]
        results = []
        scores = []

        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            for entry in self._read_all(knowledge_type):
                score = 0
                content_lower = entry.content.lower()
                context_lower = entry.context.lower()

                # Check for exact phrase match (higher score)
                if query_lower in content_lower:
                    score += 15

                # Check for individual word matches in content
                for word in query_words:
                    if word in content_lower:
                        score += 5
                    if word in context_lower:
                        score += 2

                # Check tags
                for tag in entry.tags:
                    tag_lower = tag.lower()
                    if query_lower in tag_lower:
                        score += 8
                    for word in query_words:
                        if word in tag_lower:
                            score += 3

                if score > 0:
                    results.append(entry)
                    scores.append(score * entry.confidence)

        # Sort by score
        sorted_results = [r for _, r in sorted(zip(scores, results), reverse=True)]
        return sorted_results[:limit]

    def get_summary(self) -> KnowledgeSummary:
        """Get summary of all knowledge."""
        summary = KnowledgeSummary(project_root=str(self.project_root))
        all_tags: dict[str, int] = {}
        recent: list[KnowledgeEntry] = []

        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            entries = list(self._read_all(knowledge_type))
            count = len(entries)

            if count > 0:
                summary.entries_by_type[knowledge_type] = count
                summary.total_entries += count

                for entry in entries:
                    # Track tags
                    for tag in entry.tags:
                        all_tags[tag] = all_tags.get(tag, 0) + 1

                    # Track validated
                    if entry.validated:
                        summary.validated_count += 1

                    # Track stale (simplified check)
                    if self._is_stale(entry):
                        summary.stale_count += 1

                    # Track recent
                    recent.append(entry)

                    # Track last updated
                    if summary.last_updated is None or entry.updated_at > summary.last_updated:
                        summary.last_updated = entry.updated_at

        # Sort recent by date
        recent.sort(key=lambda e: e.updated_at, reverse=True)
        summary.recent_entries = recent[:10]

        # Sort tags by count
        summary.top_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:20]

        return summary

    def get_for_context(
        self,
        file_paths: list[str] | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[KnowledgeEntry]:
        """Get relevant knowledge for building context."""
        results = []

        # Get by file references
        if file_paths:
            for entry in self.query(references=file_paths, limit=limit):
                if entry not in results:
                    results.append(entry)

        # Get by tags
        if tags:
            for entry in self.query(tags=tags, limit=limit):
                if entry not in results:
                    results.append(entry)

        # Get recent high-confidence entries if we don't have enough
        if len(results) < limit:
            for entry in self.query(min_confidence=0.7, limit=limit - len(results)):
                if entry not in results:
                    results.append(entry)

        return results[:limit]

    def _read_all(self, knowledge_type: str) -> Iterator[KnowledgeEntry]:
        """Read all entries of a type."""
        file_path = self._get_file_for_type(knowledge_type)
        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            yield KnowledgeEntry.model_validate(data)
                        except Exception as e:
                            logger.warning(f"Failed to parse knowledge entry: {e}")
        except Exception as e:
            logger.error(f"Failed to read knowledge file: {e}")

    def _write_all(self, knowledge_type: str, entries: list[KnowledgeEntry]):
        """Write all entries of a type (overwrites file)."""
        file_path = self._get_file_for_type(knowledge_type)

        with open(file_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.model_dump_json() + "\n")

    def _update_index(self):
        """Update the quick lookup index."""
        index = {
            "updated_at": datetime.utcnow().isoformat(),
            "counts": {},
            "tags": [],
        }

        all_tags = set()
        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            entries = list(self._read_all(knowledge_type))
            index["counts"][knowledge_type] = len(entries)
            for entry in entries:
                all_tags.update(entry.tags)

        index["tags"] = list(all_tags)[:100]  # Limit tags in index

        index_path = self.memory_dir / self.INDEX_FILE
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def _is_stale(self, entry: KnowledgeEntry) -> bool:
        """Check if entry is stale based on file changes."""
        for ref, stored_hash in entry.file_hashes.items():
            ref_path = self.project_root / ref
            if ref_path.exists():
                try:
                    content = ref_path.read_bytes()
                    current_hash = hashlib.md5(content).hexdigest()[:8]
                    if current_hash != stored_hash:
                        return True
                except Exception:
                    pass
            else:
                # Referenced file no longer exists
                return True
        return False

    def prune_stale(self) -> int:
        """Remove stale entries. Returns count removed."""
        removed = 0

        for knowledge_type in [
            "pattern",
            "architecture",
            "relation",
            "issue",
            "convention",
            "insight",
        ]:
            entries = list(self._read_all(knowledge_type))
            original_count = len(entries)
            entries = [e for e in entries if not self._is_stale(e)]

            if len(entries) < original_count:
                self._write_all(knowledge_type, entries)
                removed += original_count - len(entries)

        if removed > 0:
            self._update_index()
            logger.info(f"Pruned {removed} stale knowledge entries")

        return removed
