"""Codebase tools — scan_codebase, critique_file, analyze_dependencies."""

import logging
from pathlib import Path
from typing import Literal

from aicouncil.client import OpenRouterClient
from aicouncil.config import get_config
from aicouncil.exceptions import AiCouncilError
from aicouncil.schemas.responses import (
    CodebaseScanResult,
    DependencyAnalysisResult,
    DependencyNode,
    FileAnalysisResult,
)
from aicouncil.tools import get_knowledge_context

logger = logging.getLogger(__name__)


async def scan_codebase(
    path: str | None = None,
    scan_type: Literal["overview", "full", "security"] = "overview",
    file_patterns: list[str] | None = None,
    max_files: int = 50,
    include_tests: bool = False,
    model: str | None = None,
) -> CodebaseScanResult:
    """
    Analyze codebase structure, issues, architecture (max 50 files default).
    Scan types: overview, full, security. Auto-loads project knowledge.
    """
    logger.info(f"Codebase scan requested: {scan_type} scan of {path or 'entire project'}")

    try:
        from aicouncil.memory import KnowledgeLearner
        from aicouncil.scanner import ContextBuilder

        builder = ContextBuilder(path)
        project_context = builder.build_project_context(
            scan_type=scan_type,
            include_patterns=file_patterns,
            include_tests=include_tests,
            max_files=max_files,
        )

        knowledge_context = get_knowledge_context(
            context_type="scan",
            file_paths=project_context.all_files[:20],
        )

        prompt = f"""Analyze this codebase and provide a comprehensive review.

## Project Information
- Name: {project_context.project.name}
- Type: {project_context.project.type}
- Framework: {project_context.project.framework or "None detected"}
- Total Files: {project_context.total_files}
- Total Lines: {project_context.total_lines}
- Languages: {project_context.languages}

## Key Files
{chr(10).join(f"- {f.path}: {f.summary}" for f in project_context.key_files[:15])}

## Dependencies
{", ".join(project_context.dependencies[:20]) or "None detected"}

{knowledge_context}

## File Contents
{
            chr(10).join(
                f"### {f.path}{chr(10)}```{chr(10)}"
                f"{f.content[:2000] if f.content else 'No content'}{chr(10)}```"
                for f in project_context.key_files[:10]
                if f.content
            )
        }

Provide:
1. Architecture summary
2. Code quality issues found
3. Security concerns (if any)
4. Recommendations for improvement
"""

        config = get_config()
        resolved_model = config.resolve_model("scan_codebase", per_invocation=model)
        client = OpenRouterClient(model=resolved_model, config=config)
        result = await client.generate(prompt, response_model=CodebaseScanResult)

        if isinstance(result, CodebaseScanResult):
            learner = KnowledgeLearner()
            learned_ids = learner.learn_from_scan(result.model_dump(), scan_type)
            result.knowledge_learned = learned_ids
            return result

        return CodebaseScanResult(
            project_name=project_context.project.name,
            project_type=project_context.project.type,
            framework=project_context.project.framework,
            total_files=project_context.total_files,
            total_lines=project_context.total_lines,
            languages=project_context.languages,
            architecture_summary="Scan completed with parsing issues",
            dependencies=project_context.dependencies,
        )

    except AiCouncilError as e:
        logger.error(f"Codebase scan failed: {e}")
        return CodebaseScanResult(
            project_name="Unknown",
            project_type="unknown",
            total_files=0,
            total_lines=0,
            architecture_summary=f"Scan failed: {e}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in scan_codebase: {e}")
        return CodebaseScanResult(
            project_name="Unknown",
            project_type="unknown",
            total_files=0,
            total_lines=0,
            architecture_summary=f"Unexpected error: {e}",
        )


async def critique_file(
    file_path: str,
    include_related: bool = True,
    related_depth: int = 1,
    model: str | None = None,
) -> FileAnalysisResult:
    """
    Deep code review of a file with imported/related files context.
    related_depth: 1-3 levels of import following.
    """
    logger.info(f"File critique requested: {file_path}")

    try:
        from aicouncil.memory import KnowledgeLearner
        from aicouncil.scanner import ContextBuilder

        builder = ContextBuilder()
        main_context, related_contexts = builder.build_file_context(
            file_path,
            include_related=include_related,
            related_depth=min(related_depth, 3),
        )

        knowledge_context = get_knowledge_context(
            file_paths=[file_path] + [r.path for r in related_contexts],
            context_type="code",
        )

        related_section = ""
        if related_contexts:
            related_section = "\n## Related Files\n" + "\n".join(
                f"### {r.path}\n```\n{r.content[:1000] if r.content else 'No content'}\n```"
                for r in related_contexts[:5]
            )

        prompt = f"""Analyze this code file in detail.

## Main File: {main_context.path}
{main_context.summary}

### Code
```
{main_context.content or "Content not available"}
```

{related_section}

{knowledge_context}

Provide:
1. Summary of what this file does
2. Code quality issues
3. Patterns identified (good and bad)
4. Specific recommendations
"""

        config = get_config()
        resolved_model = config.resolve_model("critique_file", per_invocation=model)
        client = OpenRouterClient(model=resolved_model, config=config)
        result = await client.generate(prompt, response_model=FileAnalysisResult)

        if isinstance(result, FileAnalysisResult):
            result.file_path = file_path
            result.related_files = [r.path for r in related_contexts]

            if main_context.structure:
                learner = KnowledgeLearner()
                structure_dict = (
                    main_context.structure.model_dump()
                    if hasattr(main_context.structure, "model_dump")
                    else {}
                )
                learned_ids = learner.learn_from_file_analysis(
                    file_path, structure_dict, result.model_dump()
                )
                result.knowledge_learned = learned_ids

            return result

        return FileAnalysisResult(
            file_path=file_path,
            file_summary="Analysis completed with parsing issues",
            related_files=[r.path for r in related_contexts],
        )

    except AiCouncilError as e:
        logger.error(f"File critique failed: {e}")
        return FileAnalysisResult(
            file_path=file_path,
            file_summary=f"Analysis failed: {e}",
        )
    except Exception as e:
        logger.exception(f"Unexpected error in critique_file: {e}")
        return FileAnalysisResult(
            file_path=file_path,
            file_summary=f"Unexpected error: {e}",
        )


async def analyze_dependencies(
    path: str | None = None,
) -> DependencyAnalysisResult:
    """
    Map module dependencies, find circular deps, identify hub/isolated modules.
    """
    logger.info(f"Dependency analysis requested for {path or 'entire project'}")

    try:
        from aicouncil.scanner import CodeAnalyzer, FileWalker, ProjectDetector

        detector = ProjectDetector(path)
        project_info = detector.detect()
        root = Path(project_info.root)

        walker = FileWalker(root)
        analyzer = CodeAnalyzer(root)

        internal_modules = []
        external_deps: set[str] = set()
        import_map: dict[str, list[str]] = {}

        for file_info in walker.get_code_files()[:100]:
            structure = analyzer.analyze_file(root / file_info.path)

            local_imports = []
            for imp in structure.imports:
                if imp.is_local:
                    local_imports.append(imp.module)
                else:
                    external_deps.add(imp.module.split(".")[0])

            import_map[file_info.path] = local_imports

        imported_by_map: dict[str, list[str]] = {}
        for fp, imports in import_map.items():
            for imp in imports:
                if imp not in imported_by_map:
                    imported_by_map[imp] = []
                imported_by_map[imp].append(fp)

        for fp, imports in import_map.items():
            internal_modules.append(
                DependencyNode(
                    name=Path(fp).stem,
                    path=fp,
                    imports=imports,
                    imported_by=imported_by_map.get(fp, []),
                )
            )

        hub_modules = [m.path for m in internal_modules if len(m.imports) + len(m.imported_by) > 5]
        isolated_modules = [
            m.path for m in internal_modules if len(m.imports) == 0 and len(m.imported_by) == 0
        ]

        circular: list[list[str]] = []
        for fp, imports in import_map.items():
            for imp in imports:
                if imp in import_map and fp in import_map.get(imp, []):
                    pair = sorted([fp, imp])
                    if pair not in circular:
                        circular.append(pair)

        return DependencyAnalysisResult(
            total_modules=len(internal_modules),
            external_dependencies=sorted(external_deps)[:50],
            internal_modules=internal_modules[:50],
            circular_dependencies=circular,
            hub_modules=hub_modules[:10],
            isolated_modules=isolated_modules[:10],
            recommendations=[
                (
                    f"Found {len(circular)} circular dependencies - consider refactoring"
                    if circular
                    else "No circular dependencies found"
                ),
                (
                    f"{len(hub_modules)} hub modules detected - may need decomposition"
                    if hub_modules
                    else "No overly connected modules"
                ),
                (
                    f"{len(isolated_modules)} isolated modules - verify they're used"
                    if isolated_modules
                    else "All modules are connected"
                ),
            ],
        )

    except AiCouncilError as e:
        logger.error(f"Dependency analysis failed: {e}")
        return DependencyAnalysisResult(
            total_modules=0,
            recommendations=[f"Analysis failed: {e}"],
        )
    except Exception as e:
        logger.exception(f"Unexpected error in analyze_dependencies: {e}")
        return DependencyAnalysisResult(
            total_modules=0,
            recommendations=[f"Unexpected error: {e}"],
        )
