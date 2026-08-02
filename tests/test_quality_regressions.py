from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import networkx as nx
import pytest
from click.testing import CliRunner

from explain_codebase.analysis.hotspot_detector import HotspotDetector
from explain_codebase.cli.main import Analyzer, app


def _write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_file_analysis_prefers_project_marker_over_nested_content(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname = 'fixture'\nversion = '0.0.0'\n")
    _write(tmp_path / "main.py", "from services.alpha import VALUE\n")
    target = _write(tmp_path / "services" / "alpha.py", "VALUE = 1\n")
    _write(tmp_path / "services" / "beta.py", "VALUE = 2\n")

    analyzer = Analyzer()

    assert analyzer.guess_project_root(target) == tmp_path.resolve()
    explanation = analyzer.explain_file(target)
    assert explanation.used_by == ["main.py"]


def test_project_type_uses_only_scanned_files(tmp_path: Path) -> None:
    _write(tmp_path / "library.py", "VALUE = 1\n")
    _write(tmp_path / ".venv" / "ignored.py", "import typer\n")

    project = Analyzer().scan_project(tmp_path)

    assert project.project_type == "Unknown project"
    assert [file.path for file in project.files] == ["library.py"]


def test_malformed_package_metadata_does_not_break_detection(tmp_path: Path) -> None:
    _write(tmp_path / "server.js", "const value = 1;\n")
    _write(tmp_path / "package.json", '{"dependencies": [], "devDependencies": "invalid"}\n')

    project = Analyzer().scan_project(tmp_path)

    assert project.project_type == "Node backend service"


def test_isolated_nodes_are_not_hotspots() -> None:
    graph = nx.DiGraph()
    graph.add_nodes_from(["first.py", "second.py"])

    assert HotspotDetector().detect(graph) == []


def test_connected_nodes_are_still_hotspots() -> None:
    graph = nx.DiGraph()
    graph.add_edge("entrypoint.py", "service.py")

    hotspots = HotspotDetector().detect(graph)

    assert {item.path for item in hotspots} == {"entrypoint.py", "service.py"}


@pytest.mark.parametrize("value", ["0", "-1"])
def test_cli_rejects_non_positive_max_files(tmp_path: Path, value: str) -> None:
    _write(tmp_path / "main.py", "VALUE = 1\n")

    result = CliRunner().invoke(app, [str(tmp_path), "--max-files", value])

    assert result.exit_code == 2
    assert "--max-files" in result.output


def test_cli_version_matches_installed_distribution() -> None:
    try:
        expected = version("explain-codebase")
    except PackageNotFoundError:
        expected = "unknown"

    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"explain-codebase, version {expected}"
