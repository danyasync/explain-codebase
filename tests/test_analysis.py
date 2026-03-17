from pathlib import Path

import pytest
import typer
from click.testing import CliRunner

from explain_codebase.cli.main import Analyzer
from explain_codebase.cli.main import app
from explain_codebase.cli.main import main as cli_main
from explain_codebase.cli.main import run
from explain_codebase.cli.target_resolution import TargetResolver


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_fastapi_entrypoint_and_core_module_detection() -> None:
    result = Analyzer().analyze(FIXTURES / "fastapi_example")

    assert "main.py" in result.entrypoints
    assert "services/user_service.py" in result.core_modules
    assert "db/client.py" in result.side_effect_modules


def test_express_dependency_flow() -> None:
    result = Analyzer().analyze(FIXTURES / "express_example")

    assert "server.js" in result.entrypoints
    assert any(flow[0] == "server.js" for flow in result.execution_flow)
    assert "services/userService.js" in result.core_modules


def test_python_cli_detection() -> None:
    result = Analyzer().analyze(FIXTURES / "python_cli_example")

    assert result.project_type == "Python CLI tool"
    assert "cli.py" in result.entrypoints


def test_analysis_includes_architecture_modules_and_hotspots() -> None:
    result = Analyzer().analyze(FIXTURES / "fastapi_example")

    assert "services/" in result.architecture_modules
    assert "repositories/" in result.architecture_modules
    assert result.hotspots
    assert result.core_module_rankings


def test_local_pipeline_progress_messages(capsys) -> None:
    cli_main(target=str(FIXTURES / "fastapi_example"), json_output=True, verbose=False, max_files=None)

    captured = capsys.readouterr()
    assert "[1/5] Resolving target..." in captured.err
    assert "[2/5] Preparing local repository..." in captured.err
    assert "[3/5] Scanning project files..." in captured.err
    assert "[4/5] Building dependency graph..." in captured.err
    assert "[5/5] Generating explanation..." in captured.err
    assert '"project_type": "Python backend service"' in captured.out


def test_default_cli_output_is_compact(capsys) -> None:
    cli_main(target=str(FIXTURES / "fastapi_example"), json_output=False, verbose=False, deep=False, max_files=None)

    captured = capsys.readouterr()
    assert "Explain Codebase" in captured.out
    assert "Repository" in captured.out
    assert "Architecture" in captured.out
    assert "Suggested starting point" in captured.out
    assert "Run with --verbose to see full architecture" in captured.out
    assert "Execution flow" not in captured.out
    assert "File roles" not in captured.out
    assert "Side-effect modules" not in captured.out


def test_verbose_cli_output_shows_full_architecture(capsys) -> None:
    cli_main(target=str(FIXTURES / "fastapi_example"), json_output=False, verbose=True, deep=False, max_files=None)

    captured = capsys.readouterr()
    assert "Architecture summary" in captured.out
    assert "Entrypoints" in captured.out
    assert "Core modules" in captured.out
    assert "Side-effect modules" in captured.out
    assert "Execution flow" in captured.out
    assert "File roles" in captured.out
    assert "Run with --deep to see architecture issues" in captured.out


def test_deep_cli_output_shows_architecture_problems(tmp_path, capsys) -> None:
    large_module = "\n".join(["value = 1"] * 820) + "\n"
    (tmp_path / "main.py").write_text("import service\n", encoding="utf-8")
    (tmp_path / "service.py").write_text("import helper\n", encoding="utf-8")
    (tmp_path / "helper.py").write_text("import service\n" + large_module, encoding="utf-8")

    cli_main(target=str(tmp_path), json_output=False, verbose=False, deep=True, max_files=None)

    captured = capsys.readouterr()
    assert "Architecture issues" in captured.out
    assert "Circular dependency" in captured.out
    assert "Large modules" in captured.out
    assert "helper.py (821 LOC)" in captured.out or "helper.py (822 LOC)" in captured.out
    assert "High coupling modules" in captured.out
    assert "File roles" not in captured.out


def test_verbose_and_deep_cannot_be_combined() -> None:
    with pytest.raises(typer.BadParameter):
        cli_main(target=str(FIXTURES / "fastapi_example"), json_output=False, verbose=True, deep=True, max_files=None)


def test_remote_target_cancelled_by_user(monkeypatch, capsys) -> None:
    monkeypatch.setattr(TargetResolver, "_check_repository_access", lambda self, repository: "exists")
    monkeypatch.setattr("builtins.input", lambda: "n")

    with pytest.raises(typer.Exit) as exc_info:
        cli_main(target="https://github.com/user/repo", json_output=True, verbose=False, max_files=None)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 0
    assert "Repository" in captured.err
    assert "  https://github.com/user/repo" in captured.err
    assert "Download repository into a temporary directory? (y/n): " in captured.err
    assert "Operation cancelled" in captured.err


def test_remote_target_downloads_and_cleans_workspace(monkeypatch, capsys) -> None:
    temp_directories: list[Path] = []

    def fake_clone_repository(self, target: str, destination: Path) -> None:
        temp_directories.append(destination)
        (destination / "main.py").write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.setattr(TargetResolver, "_check_repository_access", lambda self, repository: "exists")
    monkeypatch.setattr("builtins.input", lambda: "y")
    monkeypatch.setattr(TargetResolver, "_clone_repository", fake_clone_repository)

    cli_main(target="https://github.com/user/repo", json_output=True, verbose=False, max_files=None)

    captured = capsys.readouterr()
    assert "Temporary workspace" in captured.err
    assert "[2/5] Cloning repository..." in captured.err
    assert "Cleaning temporary workspace..." in captured.err
    assert "Temporary workspace removed" in captured.err
    assert temp_directories
    assert not temp_directories[0].exists()


def test_remote_target_not_found_exits_before_prompt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(TargetResolver, "_check_repository_access", lambda self, repository: "not_found")
    monkeypatch.setattr("builtins.input", lambda: (_ for _ in ()).throw(AssertionError("input should not be called")))

    with pytest.raises(typer.Exit) as exc_info:
        cli_main(target="https://github.com/user/non-existing-repo", json_output=True, verbose=False, max_files=None)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "[1/5] Resolving target..." in captured.err
    assert "Error: Repository not found" in captured.err
    assert "https://github.com/user/non-existing-repo" in captured.err
    assert "Make sure the repository exists and is publicly accessible." in captured.err
    assert "Download repository into a temporary directory? (y/n): " not in captured.err


def test_remote_target_not_accessible_exits_before_prompt(monkeypatch, capsys) -> None:
    monkeypatch.setattr(TargetResolver, "_check_repository_access", lambda self, repository: "not_accessible")
    monkeypatch.setattr("builtins.input", lambda: (_ for _ in ()).throw(AssertionError("input should not be called")))

    with pytest.raises(typer.Exit) as exc_info:
        cli_main(target="https://github.com/user/private-repo", json_output=True, verbose=False, max_files=None)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "Error: Repository is not accessible" in captured.err
    assert "https://github.com/user/private-repo" in captured.err
    assert "Only public repositories are supported." in captured.err
    assert "Download repository into a temporary directory? (y/n): " not in captured.err


def test_github_repository_detection_is_strict() -> None:
    resolver = TargetResolver()

    assert resolver._parse_github_repository("https://github.com/user/repo") is not None
    assert resolver._parse_github_repository("https://github.com/user/repo.git") is not None
    assert resolver._parse_github_repository("https://github.com/user/repo/issues") is None
    assert resolver._parse_github_repository("https://github.com/user") is None
    assert resolver._parse_github_repository("https://www.github.com/user/repo") is None
    assert resolver._parse_github_repository("https://example.com/user/repo") is None


def test_file_command_explains_single_file(monkeypatch, capsys) -> None:
    cli_main(
        target="file",
        extra_args=[str(FIXTURES / "fastapi_example" / "services" / "user_service.py")],
        json_output=True,
        verbose=False,
        max_files=None,
        graph=False,
        report=False,
        ci=False,
    )

    captured = capsys.readouterr()
    assert '"role": "Service layer"' in captured.out
    assert '"depends_on": [' in captured.out
    assert '"used_by": [' in captured.out


def test_onboarding_mode_returns_reading_path(capsys) -> None:
    cli_main(
        target="onboarding",
        extra_args=[str(FIXTURES / "express_example")],
        json_output=True,
        verbose=False,
        max_files=None,
        graph=False,
        report=False,
        ci=False,
    )

    captured = capsys.readouterr()
    assert '"onboarding_path": [' in captured.out


def test_graph_and_report_outputs_are_generated(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    cli_main(
        target=str(FIXTURES / "fastapi_example"),
        extra_args=[],
        json_output=True,
        verbose=False,
        max_files=None,
        graph=True,
        report=True,
        ci=False,
    )

    captured = capsys.readouterr()
    assert (tmp_path / "dependency_graph.html").exists()
    assert (tmp_path / "codebase_report.html").exists()
    assert '"dependency_graph_output":' in captured.out
    assert '"html_report_output":' in captured.out


def test_ci_mode_fails_on_architecture_issues(tmp_path) -> None:
    (tmp_path / "main.py").write_text("import a\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("import a\n", encoding="utf-8")

    with pytest.raises(typer.Exit) as exc_info:
        cli_main(
            target=str(tmp_path),
            extra_args=[],
            json_output=True,
            verbose=False,
            max_files=None,
            graph=False,
            report=False,
            ci=True,
        )

    assert exc_info.value.exit_code == 1


def test_help_output_uses_plain_cli_style() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Explain Codebase - understand any repository architecture" in result.output
    assert "Usage" in result.output
    assert "Arguments" in result.output
    assert "Options" in result.output
    assert "Examples" in result.output
    assert "╭" not in result.output
    assert "│" not in result.output


def test_run_formats_unknown_option_without_boxes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["--reporty"])

    captured = capsys.readouterr()
    assert exc_info.value.code != 0
    assert "Error: Unknown option --reporty" in captured.err
    assert "╭" not in captured.err


def test_run_formats_click_errors_without_boxes(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run(["file"])

    captured = capsys.readouterr()
    assert exc_info.value.code != 0
    assert captured.err.startswith("Error:")
    assert "╭" not in captured.err
