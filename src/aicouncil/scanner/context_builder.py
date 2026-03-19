"""Build context for AI Council from scanned codebase."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from aicouncil.scanner.code_analyzer import CodeAnalyzer, CodeStructure
from aicouncil.scanner.file_walker import FileInfo, FileWalker
from aicouncil.scanner.project_detector import ProjectDetector, ProjectInfo


class FileContext(BaseModel):
    """Context for a single file."""

    path: str
    summary: str
    structure: CodeStructure | None = None
    content: str | None = None  # Only for small/key files
    truncated: bool = False


class ProjectContext(BaseModel):
    """Full project context for AI Council."""

    project: ProjectInfo
    file_tree: dict = Field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    key_files: list[FileContext] = Field(default_factory=list)
    all_files: list[str] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)  # language -> file count
    dependencies: list[str] = Field(default_factory=list)


class ContextBuilder:
    """Build context for AI Council from project scan."""

    MAX_FILE_CONTENT_LINES = 200  # Max lines to include for a single file
    MAX_TOTAL_CONTENT_LINES = 2000  # Max total lines to include
    MAX_FILES_WITH_CONTENT = 20  # Max files to include full content

    def __init__(self, project_root: str | Path | None = None):
        """Initialize context builder."""
        self.detector = ProjectDetector(project_root)
        self.project_info = self.detector.detect()
        self.root = Path(self.project_info.root)
        self.analyzer = CodeAnalyzer(self.root)

    def build_project_context(
        self,
        scan_type: Literal["overview", "full", "security"] = "overview",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        include_tests: bool = False,
        max_files: int = 50,
    ) -> ProjectContext:
        """Build full project context."""
        walker = FileWalker(
            self.root,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            include_tests=include_tests,
        )

        files = list(walker.walk())[: max_files * 2]  # Get more, then prioritize

        # Build basic stats
        context = ProjectContext(
            project=self.project_info,
            file_tree=walker.get_file_tree(),
            total_files=len(files),
            total_lines=sum(f.lines for f in files),
            all_files=[f.path for f in files],
        )

        # Count languages
        for f in files:
            lang = self._get_language(f.extension)
            context.languages[lang] = context.languages.get(lang, 0) + 1

        # Identify and process key files
        key_files = self._prioritize_files(files, scan_type, max_files)
        total_lines_included = 0

        for file_info in key_files:
            if total_lines_included >= self.MAX_TOTAL_CONTENT_LINES:
                break

            file_context = self._build_file_context(
                file_info,
                include_content=(scan_type != "overview"),
                max_lines=min(
                    self.MAX_FILE_CONTENT_LINES, self.MAX_TOTAL_CONTENT_LINES - total_lines_included
                ),
            )
            context.key_files.append(file_context)

            if file_context.content:
                total_lines_included += file_context.content.count("\n")

        # Extract dependencies
        context.dependencies = self._extract_dependencies()

        return context

    def build_file_context(
        self,
        file_path: str | Path,
        include_related: bool = True,
        related_depth: int = 1,
        include_content: bool = True,
    ) -> tuple[FileContext, list[FileContext]]:
        """Build context for a specific file and optionally related files."""
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = self.root / file_path

        # Main file context
        file_info = FileInfo(
            path=str(file_path.relative_to(self.root)),
            absolute_path=str(file_path),
            size=file_path.stat().st_size,
            lines=sum(1 for _ in open(file_path, errors="ignore")),
            extension=file_path.suffix,
        )

        main_context = self._build_file_context(
            file_info,
            include_content=include_content,
            max_lines=500,  # More lines for focused analysis
        )

        # Related files
        related_contexts = []
        if include_related:
            related_paths = self.analyzer.get_related_files(file_path, depth=related_depth)

            for rel_path in related_paths[:10]:  # Limit related files
                try:
                    abs_path = self.root / rel_path
                    rel_info = FileInfo(
                        path=rel_path,
                        absolute_path=str(abs_path),
                        size=abs_path.stat().st_size,
                        lines=sum(1 for _ in open(abs_path, errors="ignore")),
                        extension=abs_path.suffix,
                    )
                    rel_context = self._build_file_context(
                        rel_info,
                        include_content=True,
                        max_lines=100,  # Less for related files
                    )
                    related_contexts.append(rel_context)
                except Exception:
                    continue

        return main_context, related_contexts

    def _build_file_context(
        self,
        file_info: FileInfo,
        include_content: bool = False,
        max_lines: int = 200,
    ) -> FileContext:
        """Build context for a single file."""
        path = Path(file_info.absolute_path)

        # Analyze structure
        structure = None
        try:
            structure = self.analyzer.analyze_file(path)
        except Exception:
            pass

        # Generate summary
        summary = self._summarize_file(file_info, structure)

        # Optionally include content
        content = None
        truncated = False
        if include_content:
            try:
                lines = path.read_text(encoding="utf-8", errors="ignore").split("\n")
                if len(lines) > max_lines:
                    content = "\n".join(lines[:max_lines])
                    truncated = True
                else:
                    content = "\n".join(lines)
            except Exception:
                pass

        return FileContext(
            path=file_info.path,
            summary=summary,
            structure=structure,
            content=content,
            truncated=truncated,
        )

    def _summarize_file(self, file_info: FileInfo, structure: CodeStructure | None) -> str:
        """Generate a brief summary of a file."""
        parts = [f"{file_info.path} ({file_info.lines} lines)"]

        if structure:
            if structure.classes:
                class_names = [c.name for c in structure.classes[:5]]
                parts.append(f"Classes: {', '.join(class_names)}")
            if structure.functions:
                func_names = [f.name for f in structure.functions[:5]]
                parts.append(f"Functions: {', '.join(func_names)}")
            if structure.exports:
                parts.append(f"Exports: {', '.join(structure.exports[:5])}")

        return " | ".join(parts)

    def _prioritize_files(
        self,
        files: list[FileInfo],
        scan_type: str,
        max_files: int,
    ) -> list[FileInfo]:
        """Prioritize which files to include in context."""

        # Score files by importance
        def score_file(f: FileInfo) -> int:
            score = 0

            # Entry points are high priority
            if f.path in self.project_info.entry_points:
                score += 100

            # Config files
            if f.is_config:
                score += 50

            # Security-relevant files for security scan
            if scan_type == "security":
                security_keywords = [
                    "auth",
                    "login",
                    "password",
                    "token",
                    "secret",
                    "api",
                    "permission",
                ]
                if any(kw in f.path.lower() for kw in security_keywords):
                    score += 80

            # Smaller files are easier to analyze
            if f.lines < 100:
                score += 20
            elif f.lines < 300:
                score += 10

            # Core source files
            if "/src/" in f.path or f.path.startswith("src/"):
                score += 30

            # Not test files (unless explicitly included)
            if not f.is_test:
                score += 15

            return score

        # Sort by score
        sorted_files = sorted(files, key=score_file, reverse=True)

        return sorted_files[:max_files]

    def _get_language(self, extension: str) -> str:
        """Map extension to language name."""
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".jsx": "React",
            ".tsx": "React/TypeScript",
            ".vue": "Vue",
            ".rs": "Rust",
            ".go": "Go",
            ".java": "Java",
            ".rb": "Ruby",
            ".php": "PHP",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".md": "Markdown",
        }
        return mapping.get(extension, "Other")

    def _extract_dependencies(self) -> list[str]:
        """Extract project dependencies."""
        deps = []

        # package.json
        pkg_json = self.root / "package.json"
        if pkg_json.exists():
            try:
                import json

                with open(pkg_json) as f:
                    data = json.load(f)
                    deps.extend(data.get("dependencies", {}).keys())
                    deps.extend(data.get("devDependencies", {}).keys())
            except Exception:
                pass

        # pyproject.toml (simplified)
        pyproject = self.root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                # Very simplified - just look for dependencies section
                in_deps = False
                for line in content.split("\n"):
                    if "dependencies" in line and "=" in line:
                        in_deps = True
                        continue
                    if in_deps:
                        if line.startswith("["):
                            in_deps = False
                            continue
                        if "=" in line or ">=" in line or line.strip().startswith('"'):
                            dep = line.split("=")[0].split(">")[0].strip().strip('"').strip("'")
                            if dep:
                                deps.append(dep)
            except Exception:
                pass

        # requirements.txt
        req_txt = self.root / "requirements.txt"
        if req_txt.exists():
            try:
                for line in req_txt.read_text().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        dep = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                        deps.append(dep)
            except Exception:
                pass

        return list(set(deps))[:50]  # Limit to 50
