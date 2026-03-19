"""Code analysis and import extraction."""

import re
from pathlib import Path

from pydantic import BaseModel, Field


class ImportInfo(BaseModel):
    """Information about an import statement."""

    module: str = Field(description="Imported module/package")
    items: list[str] = Field(default_factory=list, description="Specific items imported")
    is_relative: bool = Field(default=False, description="Whether it's a relative import")
    is_local: bool = Field(default=False, description="Whether it's a local project import")
    line: int = Field(description="Line number")


class FunctionInfo(BaseModel):
    """Information about a function/method."""

    name: str
    line_start: int
    line_end: int
    params: list[str] = Field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None


class ClassInfo(BaseModel):
    """Information about a class."""

    name: str
    line_start: int
    line_end: int
    methods: list[str] = Field(default_factory=list)
    bases: list[str] = Field(default_factory=list)
    docstring: str | None = None


class CodeStructure(BaseModel):
    """Analyzed structure of a code file."""

    file_path: str
    language: str
    imports: list[ImportInfo] = Field(default_factory=list)
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[ClassInfo] = Field(default_factory=list)
    exports: list[str] = Field(default_factory=list)
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0


class CodeAnalyzer:
    """Analyze code structure and extract imports."""

    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
    }

    def __init__(self, project_root: str | Path):
        """Initialize analyzer with project root."""
        self.project_root = Path(project_root)

    def analyze_file(self, file_path: str | Path) -> CodeStructure:
        """Analyze a single file."""
        path = Path(file_path)
        ext = path.suffix.lower()
        language = self.LANGUAGE_MAP.get(ext, "unknown")

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return CodeStructure(file_path=str(file_path), language=language)

        lines = content.split("\n")

        structure = CodeStructure(
            file_path=str(file_path),
            language=language,
            total_lines=len(lines),
        )

        if language == "python":
            self._analyze_python(content, lines, structure)
        elif language in ["javascript", "typescript"]:
            self._analyze_javascript(content, lines, structure)
        elif language == "go":
            self._analyze_go(content, lines, structure)

        return structure

    def _analyze_python(self, content: str, lines: list[str], structure: CodeStructure):
        """Analyze Python code."""
        # Extract imports
        import_pattern = r"^(?:from\s+([\w.]+)\s+)?import\s+(.+?)(?:\s+as\s+\w+)?$"

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Count comment lines
            if line_stripped.startswith("#"):
                structure.comment_lines += 1
                continue

            # Count code lines
            if line_stripped:
                structure.code_lines += 1

            # Match imports
            match = re.match(import_pattern, line_stripped)
            if match:
                from_module = match.group(1)
                imports = match.group(2)

                if from_module:
                    items = [i.strip().split(" as ")[0] for i in imports.split(",")]
                    is_relative = from_module.startswith(".")
                    structure.imports.append(
                        ImportInfo(
                            module=from_module,
                            items=items,
                            is_relative=is_relative,
                            is_local=self._is_local_import(from_module),
                            line=i,
                        )
                    )
                else:
                    for mod in imports.split(","):
                        mod = mod.strip().split(" as ")[0]
                        structure.imports.append(
                            ImportInfo(
                                module=mod,
                                items=[],
                                is_relative=False,
                                is_local=self._is_local_import(mod),
                                line=i,
                            )
                        )

        # Extract functions and classes using regex (simplified)
        func_pattern = r"^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)"
        class_pattern = r"^class\s+(\w+)(?:\(([^)]*)\))?:"

        for i, line in enumerate(lines, 1):
            # Functions
            match = re.match(func_pattern, line)
            if match:
                structure.functions.append(
                    FunctionInfo(
                        name=match.group(1),
                        line_start=i,
                        line_end=i,  # Simplified - would need AST for accurate end
                        params=[
                            p.strip().split(":")[0].split("=")[0]
                            for p in match.group(2).split(",")
                            if p.strip()
                        ],
                        is_async="async" in line,
                    )
                )

            # Classes
            match = re.match(class_pattern, line)
            if match:
                bases = []
                if match.group(2):
                    bases = [b.strip() for b in match.group(2).split(",")]
                structure.classes.append(
                    ClassInfo(
                        name=match.group(1),
                        line_start=i,
                        line_end=i,
                        bases=bases,
                    )
                )

    def _analyze_javascript(self, content: str, lines: list[str], structure: CodeStructure):
        """Analyze JavaScript/TypeScript code."""
        # Import patterns
        import_patterns = [
            r"import\s+(?:{([^}]+)}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+['\"]([^'\"]+)['\"]",
            r"const\s+(?:{([^}]+)}|(\w+))\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",
        ]

        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Count comments
            if line_stripped.startswith("//") or line_stripped.startswith("/*"):
                structure.comment_lines += 1
                continue

            if line_stripped:
                structure.code_lines += 1

            # Match ES6 imports
            match = re.search(import_patterns[0], line)
            if match:
                named = match.group(1)
                default = match.group(2)
                module = match.group(3)

                items = []
                if named:
                    items = [i.strip().split(" as ")[0] for i in named.split(",")]
                if default:
                    items.append(default)

                structure.imports.append(
                    ImportInfo(
                        module=module,
                        items=items,
                        is_relative=module.startswith("."),
                        is_local=self._is_local_import(module),
                        line=i,
                    )
                )
                continue

            # Match require
            match = re.search(import_patterns[2], line)
            if match:
                module = match.group(3)
                structure.imports.append(
                    ImportInfo(
                        module=module,
                        items=[],
                        is_relative=module.startswith("."),
                        is_local=self._is_local_import(module),
                        line=i,
                    )
                )

        # Extract exports
        export_pattern = (
            r"export\s+(?:default\s+)?(?:const|let|var|function|class|async function)\s+(\w+)"
        )
        for match in re.finditer(export_pattern, content):
            structure.exports.append(match.group(1))

        # Extract functions
        func_patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
        ]

        for i, line in enumerate(lines, 1):
            for pattern in func_patterns:
                match = re.search(pattern, line)
                if match:
                    structure.functions.append(
                        FunctionInfo(
                            name=match.group(1),
                            line_start=i,
                            line_end=i,
                            is_async="async" in line,
                        )
                    )
                    break

    def _analyze_go(self, content: str, lines: list[str], structure: CodeStructure):
        """Analyze Go code."""
        # Single import
        for match in re.finditer(r'import\s+"([^"]+)"', content):
            structure.imports.append(
                ImportInfo(
                    module=match.group(1),
                    items=[],
                    is_relative=False,
                    is_local=self._is_local_import(match.group(1)),
                    line=0,
                )
            )

        # Multi import block
        in_import = False
        for i, line in enumerate(lines, 1):
            if "import (" in line:
                in_import = True
                continue
            if in_import:
                if ")" in line:
                    in_import = False
                    continue
                match = re.search(r'"([^"]+)"', line)
                if match:
                    structure.imports.append(
                        ImportInfo(
                            module=match.group(1),
                            items=[],
                            is_relative=False,
                            is_local=self._is_local_import(match.group(1)),
                            line=i,
                        )
                    )

        # Extract functions
        func_pattern = r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)"
        for i, line in enumerate(lines, 1):
            match = re.search(func_pattern, line)
            if match:
                structure.functions.append(
                    FunctionInfo(
                        name=match.group(1),
                        line_start=i,
                        line_end=i,
                    )
                )

    def _is_local_import(self, module: str) -> bool:
        """Check if import is from local project."""
        if module.startswith("."):
            return True

        # Check if module exists in project
        # This is a simplified check
        parts = module.split("/")[0].split(".")
        for part in parts:
            if (self.project_root / part).exists():
                return True
            if (self.project_root / "src" / part).exists():
                return True

        return False

    def get_related_files(self, file_path: str | Path, depth: int = 1) -> list[str]:
        """Get files related to the given file through imports."""
        structure = self.analyze_file(file_path)
        related = []

        file_path = Path(file_path)
        file_dir = file_path.parent

        for imp in structure.imports:
            if imp.is_local or imp.is_relative:
                # Try to resolve the import to a file
                if imp.is_relative:
                    # Resolve relative import
                    rel_path = imp.module.lstrip(".")
                    resolved = file_dir / rel_path.replace(".", "/")
                else:
                    resolved = self.project_root / imp.module.replace(".", "/")

                # Try various extensions
                for ext in [".py", ".js", ".ts", ".tsx", ".jsx", "/index.js", "/index.ts"]:
                    candidate = Path(str(resolved) + ext)
                    if candidate.exists():
                        related.append(str(candidate.relative_to(self.project_root)))
                        break

        # Recursively get related files
        if depth > 1:
            for rel_file in related[:]:
                nested = self.get_related_files(self.project_root / rel_file, depth=depth - 1)
                related.extend(nested)

        return list(set(related))
