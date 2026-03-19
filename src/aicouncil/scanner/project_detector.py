"""Project type and root detection."""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ProjectType = Literal[
    "python",
    "javascript",
    "typescript",
    "react",
    "nextjs",
    "vue",
    "rust",
    "go",
    "java",
    "csharp",
    "ruby",
    "php",
    "unknown",
]


class ProjectInfo(BaseModel):
    """Information about the detected project."""

    root: str = Field(description="Absolute path to project root")
    type: ProjectType = Field(description="Detected project type")
    name: str = Field(description="Project name")
    entry_points: list[str] = Field(default_factory=list, description="Main entry point files")
    config_files: list[str] = Field(default_factory=list, description="Configuration files found")
    has_git: bool = Field(default=False, description="Whether project has git")
    framework: str | None = Field(default=None, description="Detected framework if any")


class ProjectDetector:
    """Detect project type, root, and key files."""

    # Files that indicate project root
    ROOT_MARKERS = [
        ".git",
        "package.json",
        "pyproject.toml",
        "setup.py",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
        ".sln",
    ]

    # Project type detection rules
    TYPE_INDICATORS = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "javascript": ["package.json"],
        "typescript": ["tsconfig.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "java": ["pom.xml", "build.gradle"],
        "csharp": [".csproj", ".sln"],
        "ruby": ["Gemfile"],
        "php": ["composer.json"],
    }

    # Framework detection
    FRAMEWORK_INDICATORS = {
        "react": ["react", "react-dom"],
        "nextjs": ["next"],
        "vue": ["vue"],
        "django": ["django"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "express": ["express"],
        "nestjs": ["@nestjs/core"],
    }

    def __init__(self, start_path: str | None = None):
        """Initialize detector with optional starting path."""
        if start_path:
            self.start_path = Path(start_path)
        else:
            # Check for PROJECT_ROOT environment variable first
            env_root = os.environ.get("PROJECT_ROOT")
            self.start_path = Path(env_root) if env_root else Path.cwd()

    def detect(self) -> ProjectInfo:
        """Detect project information."""
        root = self._find_root()
        project_type = self._detect_type(root)
        name = self._detect_name(root, project_type)
        entry_points = self._find_entry_points(root, project_type)
        config_files = self._find_config_files(root)
        has_git = (root / ".git").exists()
        framework = self._detect_framework(root, project_type)

        return ProjectInfo(
            root=str(root.absolute()),
            type=project_type,
            name=name,
            entry_points=entry_points,
            config_files=config_files,
            has_git=has_git,
            framework=framework,
        )

    def _find_root(self) -> Path:
        """Find project root by looking for marker files."""
        current = self.start_path.absolute()

        while current != current.parent:
            for marker in self.ROOT_MARKERS:
                if (current / marker).exists():
                    return current
            current = current.parent

        # Fallback to start path
        return self.start_path.absolute()

    def _detect_type(self, root: Path) -> ProjectType:
        """Detect project type from files."""
        for ptype, indicators in self.TYPE_INDICATORS.items():
            for indicator in indicators:
                if (root / indicator).exists():
                    # Special case: check if it's TypeScript
                    if ptype == "javascript" and (root / "tsconfig.json").exists():
                        return "typescript"
                    return ptype

        return "unknown"

    def _detect_name(self, root: Path, project_type: ProjectType) -> str:
        """Extract project name from config files."""
        import json

        # Try package.json
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json) as f:
                    data = json.load(f)
                    if "name" in data:
                        return data["name"]
            except Exception:
                pass

        # Try pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                for line in content.split("\n"):
                    if line.startswith("name"):
                        # Extract name = "value"
                        if "=" in line:
                            name = line.split("=")[1].strip().strip("\"'")
                            return name
            except Exception:
                pass

        # Fallback to directory name
        return root.name

    def _find_entry_points(self, root: Path, project_type: ProjectType) -> list[str]:
        """Find likely entry point files."""
        entry_points = []

        candidates = {
            "python": ["main.py", "app.py", "run.py", "__main__.py", "src/main.py"],
            "javascript": ["index.js", "main.js", "app.js", "src/index.js"],
            "typescript": ["index.ts", "main.ts", "app.ts", "src/index.ts"],
            "rust": ["src/main.rs", "src/lib.rs"],
            "go": ["main.go", "cmd/main.go"],
        }

        for candidate in candidates.get(project_type, []):
            if (root / candidate).exists():
                entry_points.append(candidate)

        return entry_points

    def _find_config_files(self, root: Path) -> list[str]:
        """Find configuration files."""
        config_patterns = [
            "*.config.js",
            "*.config.ts",
            "*.config.json",
            ".eslintrc*",
            ".prettierrc*",
            "tsconfig*.json",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "package.json",
            "Cargo.toml",
            "go.mod",
            ".env.example",
            "docker-compose*.yml",
            "Dockerfile",
        ]

        configs = []
        for item in root.iterdir():
            if item.is_file():
                name = item.name
                if any(
                    name.endswith(p.replace("*", "")) or name.startswith(p.replace("*", ""))
                    for p in config_patterns
                    if "*" in p
                ):
                    configs.append(name)
                elif name in [p for p in config_patterns if "*" not in p]:
                    configs.append(name)

        return configs[:20]  # Limit to 20

    def _detect_framework(self, root: Path, project_type: ProjectType) -> str | None:
        """Detect framework from dependencies."""
        import json

        if project_type in ["javascript", "typescript"]:
            pkg_json = root / "package.json"
            if pkg_json.exists():
                try:
                    with open(pkg_json) as f:
                        data = json.load(f)
                        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

                        for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                            for indicator in indicators:
                                if indicator in deps:
                                    return framework
                except Exception:
                    pass

        elif project_type == "python":
            # Check pyproject.toml or requirements.txt
            for req_file in ["pyproject.toml", "requirements.txt"]:
                req_path = root / req_file
                if req_path.exists():
                    try:
                        content = req_path.read_text().lower()
                        for framework, indicators in self.FRAMEWORK_INDICATORS.items():
                            for indicator in indicators:
                                if indicator in content:
                                    return framework
                    except Exception:
                        pass

        return None
