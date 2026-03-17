from __future__ import annotations

import sys
from pathlib import Path

import click
import typer

from explain_codebase.analysis.architecture_module_detector import ArchitectureModuleDetector
from explain_codebase.analysis.architecture_smell_detector import ArchitectureSmellDetector
from explain_codebase.analysis.core_module_detector import CoreModuleDetector
from explain_codebase.analysis.dangerous_file_detector import DangerousFileDetector
from explain_codebase.analysis.entrypoint_finder import EntrypointFinder
from explain_codebase.analysis.file_explainer import FileExplainer
from explain_codebase.analysis.hotspot_detector import HotspotDetector
from explain_codebase.analysis.large_file_detector import LargeFileDetector
from explain_codebase.analysis.onboarding_path_finder import OnboardingPathFinder
from explain_codebase.analysis.side_effect_detector import SideEffectDetector
from explain_codebase.classify.file_classifier import FileClassifier
from explain_codebase.cli.target_resolution import ResolvedTarget, TargetResolver
from explain_codebase.detectors.language_detector import LanguageDetector
from explain_codebase.detectors.project_type_detector import ProjectTypeDetector
from explain_codebase.explain.explanation_engine import ExplanationEngine
from explain_codebase.graph.dependency_graph import DependencyGraphBuilder
from explain_codebase.models.analysis_result import AnalysisResult, FileExplanation
from explain_codebase.models.project_info import ProjectInfo
from explain_codebase.parsers.js_parser import JavaScriptParser
from explain_codebase.parsers.python_parser import PythonParser
from explain_codebase.parsers.ts_parser import TypeScriptParser
from explain_codebase.renderers.cli_renderer import CliRenderer
from explain_codebase.renderers.graph_renderer import GraphRenderer
from explain_codebase.renderers.html_report_renderer import HtmlReportRenderer
from explain_codebase.renderers.json_renderer import JsonRenderer
from explain_codebase.scanner.project_scanner import ProjectScanner

class PlainHelpCommand(click.Command):
    def get_help(self, ctx: click.Context) -> str:
        program_name = ctx.info_name or "explain-codebase"
        lines = [
            "Explain Codebase - understand any repository architecture",
            "",
            "Usage",
            f"  {program_name} [TARGET] [OPTIONS]",
            "",
            "Arguments",
            "  TARGET              Path to repository or GitHub repository URL",
            "",
            "Options",
            "  --verbose           Show full architecture output",
            "  --deep              Show architecture issues",
            "  --json              Output analysis as JSON",
            "  --graph             Generate dependency_graph.html",
            "  --report            Generate codebase_report.html",
            "  --ci                Exit with code 1 when architecture issues are detected",
            "  --max-files N       Limit scanned source files",
            "  -h, --help          Show this message and exit",
            "",
            "Examples",
            f"  {program_name} .",
            f"  {program_name} https://github.com/user/repo",
            f"  {program_name} . --verbose",
            f"  {program_name} . --deep",
            f"  {program_name} onboarding .",
            f"  {program_name} file src/services/user_service.ts",
        ]
        return "\n".join(lines)


class Analyzer:
    ARCHITECTURE_HINT_DIRS = {
        "api",
        "components",
        "config",
        "controllers",
        "jobs",
        "middleware",
        "models",
        "repositories",
        "routes",
        "services",
        "workers",
    }

    ROOT_MARKERS = {".git", "package.json", "pyproject.toml", "requirements.txt", "manage.py"}

    def __init__(self) -> None:
        self.language_detector = LanguageDetector()
        self.project_type_detector = ProjectTypeDetector()
        self.classifier = FileClassifier()
        self.entrypoint_finder = EntrypointFinder()
        self.core_module_detector = CoreModuleDetector()
        self.side_effect_detector = SideEffectDetector()
        self.architecture_module_detector = ArchitectureModuleDetector()
        self.large_file_detector = LargeFileDetector()
        self.hotspot_detector = HotspotDetector()
        self.dangerous_file_detector = DangerousFileDetector()
        self.architecture_smell_detector = ArchitectureSmellDetector()
        self.file_explainer = FileExplainer()
        self.onboarding_path_finder = OnboardingPathFinder()
        self.graph_builder = DependencyGraphBuilder()
        self.explanation_engine = ExplanationEngine()
        self.parsers = {
            "python": PythonParser(),
            "javascript": JavaScriptParser(),
            "typescript": TypeScriptParser(),
        }

    def analyze(self, target: Path, max_files: int | None = None) -> AnalysisResult:
        project_info = self.scan_project(target, max_files=max_files)
        graph = self.build_dependency_graph(project_info)
        return self.generate_explanation(project_info, graph)

    def scan_project(self, target: Path, max_files: int | None = None) -> ProjectInfo:
        scanner = ProjectScanner(max_files=max_files)
        file_paths = scanner.scan(target)

        parsed_files = []
        languages = set()
        for path in file_paths:
            language = self.language_detector.detect(path)
            parser = self.parsers.get(language)
            if parser is None:
                continue
            info = parser.parse(path, target)
            info.language = language
            info.role = self.classifier.classify(info)
            parsed_files.append(info)
            languages.add(language)

        return ProjectInfo(
            root_path=target,
            files=parsed_files,
            languages=sorted(languages),
            project_type=self.project_type_detector.detect(target, sorted(languages)),
        )

    def build_dependency_graph(self, project_info: ProjectInfo):
        return self.graph_builder.build(project_info.files)

    def generate_explanation(self, project_info: ProjectInfo, graph) -> AnalysisResult:
        file_roles = {file.path: file.role or "unknown" for file in project_info.files}
        entrypoints = self.entrypoint_finder.find(project_info.files)
        core_modules, core_rankings, centrality = self.core_module_detector.detect(graph)
        side_effect_modules = self.side_effect_detector.detect(project_info.files)
        architecture_modules = self.architecture_module_detector.detect(project_info.files)
        large_files = self.large_file_detector.detect(project_info.files)
        hotspots = self.hotspot_detector.detect(graph)
        dangerous_files = self.dangerous_file_detector.detect(graph)
        architecture_issues = self.architecture_smell_detector.detect(graph, project_info.files)
        execution_flow = self.explanation_engine.build_execution_flow(
            graph,
            entrypoints,
            file_roles=file_roles,
        )

        result = AnalysisResult(
            project_root=str(project_info.root_path.resolve()),
            project_type=project_info.project_type,
            languages=project_info.languages,
            total_files=len(project_info.files),
            entrypoints=entrypoints,
            core_modules=core_modules,
            core_module_rankings=core_rankings,
            side_effect_modules=side_effect_modules,
            architecture_modules=architecture_modules,
            large_files=large_files,
            hotspots=hotspots,
            dangerous_files=dangerous_files,
            architecture_issues=architecture_issues,
            execution_flow=execution_flow,
            file_roles=file_roles,
            centrality=centrality,
            summary="",
        )
        result.summary = self.explanation_engine.summarize(result)
        return result

    def explain_file(self, target_file: Path, max_files: int | None = None) -> FileExplanation:
        project_root = self.guess_project_root(target_file)
        project_info = self.scan_project(project_root, max_files=max_files)
        graph = self.build_dependency_graph(project_info)
        return self.file_explainer.explain(target_file, project_info, graph)

    def build_onboarding_path(self, target: Path, max_files: int | None = None) -> tuple[AnalysisResult, list[str]]:
        project_info = self.scan_project(target, max_files=max_files)
        graph = self.build_dependency_graph(project_info)
        result = self.generate_explanation(project_info, graph)
        onboarding_path = self.onboarding_path_finder.build(
            graph,
            result.entrypoints,
            result.file_roles,
            result.core_modules,
        )
        return result, onboarding_path

    def guess_project_root(self, target_file: Path) -> Path:
        resolved_target = target_file.resolve()
        ancestors = [resolved_target.parent, *resolved_target.parents]

        for parent in ancestors:
            if self._looks_like_project_root(parent):
                return parent

        for parent in ancestors:
            if any((parent / marker).exists() for marker in self.ROOT_MARKERS):
                return parent

        return resolved_target.parent

    def _looks_like_project_root(self, directory: Path) -> bool:
        try:
            children = list(directory.iterdir())
        except OSError:
            return False

        has_entrypoint = any(
            child.is_file() and child.name.lower() in {"main.py", "app.py", "server.js", "server.ts", "cli.py"}
            for child in children
        )
        has_architecture_dirs = any(
            child.is_dir() and child.name.lower() in self.ARCHITECTURE_HINT_DIRS
            for child in children
        )
        source_file_count = sum(
            1 for child in children if child.is_file() and child.suffix.lower() in {".py", ".js", ".ts"}
        )
        return has_entrypoint or has_architecture_dirs or source_file_count >= 2


def main(
    target: str = ".",
    extra_args: list[str] | None = None,
    json_output: bool = False,
    verbose: bool = False,
    deep: bool = False,
    max_files: int | None = None,
    graph: bool = False,
    report: bool = False,
    ci: bool = False,
) -> None:
    extra_args = extra_args or []

    if verbose and deep:
        raise typer.BadParameter("--verbose and --deep cannot be used together.")

    if target == "onboarding":
        onboarding_target = extra_args[0] if extra_args else "."
        if len(extra_args) > 1:
            raise typer.BadParameter("Too many arguments for onboarding mode.")
        _run_onboarding_command(onboarding_target, json_output=json_output, max_files=max_files)
        return

    if target == "file":
        if len(extra_args) != 1:
            raise typer.BadParameter("The file command requires exactly one file path.")
        _run_file_command(extra_args[0], json_output=json_output, max_files=max_files)
        return

    if extra_args:
        raise typer.BadParameter(f"Unexpected extra arguments: {' '.join(extra_args)}")

    _run_project_analysis(
        target,
        json_output=json_output,
        verbose=verbose,
        deep=deep,
        max_files=max_files,
        graph=graph,
        report=report,
        ci=ci,
    )


@click.command(
    name="explain-codebase",
    cls=PlainHelpCommand,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.argument("target", required=False, default=".")
@click.argument("extra_args", nargs=-1)
@click.option("--json", "json_output", is_flag=True, help="Output analysis as JSON")
@click.option("--verbose", is_flag=True, help="Show full architecture output")
@click.option("--deep", is_flag=True, help="Show architecture issues")
@click.option("--max-files", type=int, default=None, metavar="N", help="Limit scanned source files")
@click.option("--graph", is_flag=True, help="Generate dependency_graph.html")
@click.option("--report", is_flag=True, help="Generate codebase_report.html")
@click.option("--ci", is_flag=True, help="Exit with code 1 when architecture issues are detected")
def app(
    target: str,
    extra_args: tuple[str, ...],
    json_output: bool,
    verbose: bool,
    deep: bool,
    max_files: int | None,
    graph: bool,
    report: bool,
    ci: bool,
) -> None:
    main(
        target=target,
        extra_args=list(extra_args),
        json_output=json_output,
        verbose=verbose,
        deep=deep,
        max_files=max_files,
        graph=graph,
        report=report,
        ci=ci,
    )


def run(argv: list[str] | None = None) -> None:
    try:
        app.main(args=argv, prog_name="explain-codebase", standalone_mode=False)
    except click.NoSuchOption as exc:
        option_name = exc.option_name
        if not option_name.startswith("--"):
            option_name = f"--{option_name.lstrip('-')}"
        click.echo(f"Error: Unknown option {option_name}", err=True)
        possibilities = getattr(exc, "possibilities", None) or []
        if possibilities:
            suggestion = possibilities[0]
            if not suggestion.startswith("--"):
                suggestion = f"--{suggestion.lstrip('-')}"
            click.echo(f"Did you mean {suggestion}?", err=True)
        raise SystemExit(exc.exit_code)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.format_message()}", err=True)
        raise SystemExit(exc.exit_code)
    except typer.BadParameter as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(2)
    except typer.Exit as exc:
        raise SystemExit(exc.exit_code)


def _run_project_analysis(
    target: str,
    json_output: bool,
    verbose: bool,
    deep: bool,
    max_files: int | None,
    graph: bool,
    report: bool,
    ci: bool,
) -> None:
    analyzer = Analyzer()
    resolver = TargetResolver()
    resolved: ResolvedTarget | None = None

    try:
        resolved = resolver.resolve(target)

        typer.echo("[3/5] Scanning project files...", err=True)
        project_info = analyzer.scan_project(resolved.analysis_path, max_files=max_files)

        typer.echo("[4/5] Building dependency graph...", err=True)
        dependency_graph = analyzer.build_dependency_graph(project_info)

        typer.echo("[5/5] Generating explanation...", err=True)
        result = analyzer.generate_explanation(project_info, dependency_graph)

        _generate_optional_outputs(result, dependency_graph, graph=graph, report=report)

        if json_output:
            typer.echo(JsonRenderer().render(result))
        else:
            CliRenderer().render(result, verbose=verbose, deep=deep)

        if ci and result.architecture_issues:
            typer.echo("Architecture warnings detected:", err=True)
            for issue in result.architecture_issues:
                typer.echo(issue.description, err=True)
            raise typer.Exit(code=1)
    finally:
        if resolved is not None:
            resolver.cleanup(resolved)


def _run_onboarding_command(target: str, json_output: bool, max_files: int | None) -> None:
    analyzer = Analyzer()
    resolver = TargetResolver()
    resolved: ResolvedTarget | None = None

    try:
        resolved = resolver.resolve(target)

        typer.echo("[3/5] Scanning project files...", err=True)
        project_info = analyzer.scan_project(resolved.analysis_path, max_files=max_files)

        typer.echo("[4/5] Building dependency graph...", err=True)
        dependency_graph = analyzer.build_dependency_graph(project_info)

        typer.echo("[5/5] Generating explanation...", err=True)
        result = analyzer.generate_explanation(project_info, dependency_graph)
        onboarding_path = analyzer.onboarding_path_finder.build(
            dependency_graph,
            result.entrypoints,
            result.file_roles,
            result.core_modules,
        )

        if json_output:
            typer.echo(
                JsonRenderer().render_data(
                    {
                        "project_root": result.project_root,
                        "project_type": result.project_type,
                        "onboarding_path": onboarding_path,
                    }
                )
            )
            return

        CliRenderer().render_onboarding(result.project_root, onboarding_path)
    finally:
        if resolved is not None:
            resolver.cleanup(resolved)


def _run_file_command(target_file: str, json_output: bool, max_files: int | None) -> None:
    analyzer = Analyzer()
    file_path = Path(target_file).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise typer.BadParameter(f"Target file does not exist: {target_file}")

    project_root = analyzer.guess_project_root(file_path)
    typer.echo("[1/5] Resolving target...", err=True)
    typer.echo("[2/5] Preparing local repository...", err=True)
    typer.echo("[3/5] Scanning project files...", err=True)
    project_info = analyzer.scan_project(project_root, max_files=max_files)
    typer.echo("[4/5] Building dependency graph...", err=True)
    dependency_graph = analyzer.build_dependency_graph(project_info)
    typer.echo("[5/5] Generating explanation...", err=True)
    explanation = analyzer.file_explainer.explain(file_path, project_info, dependency_graph)

    if json_output:
        typer.echo(JsonRenderer().render_data(explanation.model_dump()))
        return

    CliRenderer().render_file_explanation(explanation)


def _generate_optional_outputs(result: AnalysisResult, dependency_graph, graph: bool, report: bool) -> None:
    output_root = Path.cwd()

    if graph:
        graph_path = output_root / "dependency_graph.html"
        GraphRenderer().render(result, dependency_graph, graph_path)
        result.dependency_graph_output = str(graph_path.resolve())
        typer.echo(f"Dependency graph written to {graph_path.resolve()}", err=True)

    if report:
        report_path = output_root / "codebase_report.html"
        HtmlReportRenderer().render(result, dependency_graph, report_path)
        result.html_report_output = str(report_path.resolve())
        typer.echo(f"HTML report written to {report_path.resolve()}", err=True)


if __name__ == "__main__":
    run(sys.argv[1:])
