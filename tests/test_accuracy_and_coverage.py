from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from explain_codebase.cli.main import Analyzer
from explain_codebase.cli.main import main as cli_main
from explain_codebase.models.analysis_result import AnalysisResult
from explain_codebase.renderers.cli_renderer import CliRenderer
from explain_codebase.renderers.graph_renderer import GraphRenderer


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_auxiliary_files_stay_in_full_graph_but_not_default_rankings(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "main.py", "import src.service\n\nif __name__ == '__main__':\n    print('start')\n")
    _write(tmp_path / "src" / "service.py", "VALUE = 1\n")
    _write(
        tmp_path / "tests" / "test_runner.py",
        "import src.service\n\nif __name__ == '__main__':\n    print('test')\n",
    )
    _write(tmp_path / "fixtures" / "server.js", "app.listen(3000);\n")
    _write(tmp_path / "examples" / "demo.py", "if __name__ == '__main__':\n    print('demo')\n")

    analyzer = Analyzer()
    project_info = analyzer.scan_project(tmp_path)
    graph = analyzer.build_dependency_graph(project_info)
    result = analyzer.generate_explanation(project_info, graph)

    assert set(graph.nodes) == {
        "examples/demo.py",
        "fixtures/server.js",
        "src/main.py",
        "src/service.py",
        "tests/test_runner.py",
    }
    assert set(result.file_roles) == set(graph.nodes)
    assert result.languages == ["python"]
    assert result.entrypoints == ["src/main.py"]
    assert result.core_modules == ["src/service.py"]

    ranked_paths = (
        set(result.core_modules)
        | set(result.side_effect_modules)
        | set(result.dangerous_files)
        | {item.path for item in result.hotspots}
        | {item.path for item in result.large_files}
    )
    assert not any(path.startswith(("tests/", "fixtures/", "examples/")) for path in ranked_paths)
    assert all(
        not path.startswith(("tests/", "fixtures/", "examples/")) for flow in result.execution_flow for path in flow
    )


def test_analysis_result_reports_scan_coverage_and_truncation(tmp_path: Path) -> None:
    for name in ("a.py", "b.py", "c.py"):
        _write(tmp_path / name, "VALUE = 1\n")

    result = Analyzer().analyze(tmp_path, max_files=2)

    assert result.total_files == 2
    assert result.discovered_files == 3
    assert result.skipped_files == 1
    assert result.truncated is True


def test_file_limit_prioritizes_application_source(tmp_path: Path) -> None:
    _write(tmp_path / "examples" / "demo.py", "if __name__ == '__main__':\n    print('demo')\n")
    _write(tmp_path / "src" / "main.py", "if __name__ == '__main__':\n    print('start')\n")

    result = Analyzer().analyze(tmp_path, max_files=1)

    assert result.entrypoints == ["src/main.py"]
    assert result.languages == ["python"]
    assert result.discovered_files == 2
    assert result.skipped_files == 1
    assert result.truncated is True


def test_analysis_result_reports_parse_errors(tmp_path: Path) -> None:
    _write(tmp_path / "broken.py", "def broken(:\n")
    _write(tmp_path / "valid.py", "VALUE = 1\n")

    result = Analyzer().analyze(tmp_path)

    assert result.parse_errors == 1
    assert result.total_files == 2
    assert result.truncated is False


def test_analysis_result_counts_only_unresolved_local_imports(tmp_path: Path) -> None:
    _write(
        tmp_path / "src" / "main.js",
        'import React from "react";\nimport missing from "./missing.js";\nconsole.log(React, missing);\n',
    )

    result = Analyzer().analyze(tmp_path)

    assert result.unresolved_imports == 1


def test_python_import_statements_report_missing_child_module_once(tmp_path: Path) -> None:
    _write(tmp_path / "app" / "__init__.py", "VALUE = 1\n")
    _write(tmp_path / "app" / "service.py", "VALUE = 2\n")
    _write(
        tmp_path / "main.py",
        "import app\nimport app.missing\nfrom app.service import VALUE\n",
    )

    result = Analyzer().analyze(tmp_path)

    assert result.unresolved_imports == 1


def test_onboarding_and_starting_point_ignore_auxiliary_files(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "main.py", "import fixtures.sample\n")
    _write(tmp_path / "fixtures" / "sample.py", "VALUE = 1\n")

    result, onboarding_path = Analyzer().build_onboarding_path(tmp_path)

    assert onboarding_path == ["src/main.py"]
    assert CliRenderer()._suggested_starting_point(result) == "src/main.py"


def test_cli_onboarding_ignores_auxiliary_files(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "src" / "main.py", "import fixtures.sample\n")
    _write(tmp_path / "fixtures" / "sample.py", "VALUE = 1\n")

    cli_main(target="onboarding", extra_args=[str(tmp_path)], json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["onboarding_path"] == ["src/main.py"]


def test_starting_point_has_no_auxiliary_fallback() -> None:
    result = AnalysisResult(
        project_root="/project",
        project_type="Unknown project",
        total_files=1,
        file_roles={"examples/demo.py": "entrypoint"},
        summary="",
    )

    assert CliRenderer()._suggested_starting_point(result) == "No clear starting point inferred"


def test_graph_search_contains_an_explicit_empty_result_state() -> None:
    result = AnalysisResult(
        project_root="/project",
        project_type="Unknown project",
        total_files=1,
        file_roles={"main.py": "entrypoint"},
        summary="",
    )
    graph = nx.DiGraph()
    graph.add_node("main.py")

    fragment = GraphRenderer().build_graph_fragment(result, graph, "test-graph")

    assert "const kept = new Set(matched);" in fragment
    assert "if (matched.size)" not in fragment
    assert '"No matching files."' in fragment
