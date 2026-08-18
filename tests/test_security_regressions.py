from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import click
import networkx as nx
import pytest
import typer

from explain_codebase.cli.target_resolution import GitHubRepository, TargetResolver
from explain_codebase.models.analysis_result import AnalysisResult
from explain_codebase.renderers.cli_renderer import CliRenderer
from explain_codebase.renderers.graph_renderer import (
    VIS_NETWORK_SRI,
    GraphRenderer,
    GraphViewOptions,
)
from explain_codebase.scanner import git_filter
from explain_codebase.scanner.project_scanner import ProjectScanner
from explain_codebase.utils import git_utils
from explain_codebase.utils.file_utils import MAX_SOURCE_FILE_BYTES, is_link_or_reparse_point, safe_read_text
from explain_codebase.utils.output_utils import atomic_write_text


def _analysis_result(path: str = "main.py") -> AnalysisResult:
    return AnalysisResult(
        project_root="repository",
        project_type="test",
        total_files=1,
        entrypoints=[path],
        file_roles={path: "entrypoint"},
        summary="test summary",
    )


def test_git_listing_disables_repository_hooks_and_sanitizes_environment(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    fake_git = (tmp_path / "trusted-bin" / "git").resolve()
    captured: dict[str, object] = {}
    monkeypatch.setattr(git_utils, "resolve_git_executable", lambda: fake_git)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "attacker-controlled"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("PATH", f".{os.pathsep}{tmp_path}")

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        hooks_setting = next(item for item in command if item.startswith("core.hooksPath="))
        assert Path(hooks_setting.partition("=")[2]).is_dir()
        return subprocess.CompletedProcess(command, 0, stdout=b"src/main.py\0", stderr=b"")

    monkeypatch.setattr(git_filter.subprocess, "run", fake_run)

    assert git_filter.load_tracked_files(tmp_path) == {"src/main.py"}
    command = captured["command"]
    kwargs = captured["kwargs"]
    assert command[0] == str(fake_git)
    assert "core.fsmonitor=false" in command
    assert command[-6:] == [
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
    ]
    assert kwargs["timeout"] == 20
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"]["GIT_CONFIG_COUNT"] == "0"
    assert "GIT_DIR" not in kwargs["env"]
    assert kwargs["env"]["PATH"].split(os.pathsep) == [str(tmp_path)]
    assert f"safe.directory={tmp_path.resolve()}" in command


def test_remote_clone_is_shallow_noninteractive_and_bounded(monkeypatch, tmp_path: Path) -> None:
    fake_git = (tmp_path / "trusted-bin" / "git").resolve()
    captured: dict[str, object] = {}
    monkeypatch.setattr(git_utils, "resolve_git_executable", lambda: fake_git)

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        hooks_setting = next(item for item in command if item.startswith("core.hooksPath="))
        assert Path(hooks_setting.partition("=")[2]).is_dir()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("explain_codebase.cli.target_resolution.subprocess.run", fake_run)
    destination = tmp_path / "checkout"

    TargetResolver()._clone_repository("https://github.com/example/repository.git", destination)

    command = captured["command"]
    kwargs = captured["kwargs"]
    assert command[0] == str(fake_git)
    assert "core.fsmonitor=false" in command
    assert "credential.helper=" in command
    assert "--depth=1" in command
    assert "--single-branch" in command
    assert "--no-tags" in command
    assert command[-2:] == ["https://github.com/example/repository.git", str(destination)]
    assert kwargs["timeout"] == TargetResolver.CLONE_TIMEOUT_SECONDS
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"]["GIT_ALLOW_PROTOCOL"] == "https"


def test_missing_git_is_reported_cleanly_and_temporary_directory_is_removed(monkeypatch, tmp_path: Path) -> None:
    resolver = TargetResolver()
    checkout = tmp_path / "remote-checkout"
    checkout.mkdir()
    repository = GitHubRepository(
        owner="example",
        repo="repository",
        clone_url="https://github.com/example/repository.git",
        display_url="https://github.com/example/repository",
        api_url="https://api.github.com/repos/example/repository",
    )
    monkeypatch.setattr(resolver, "_check_repository_access", lambda target: "exists")
    monkeypatch.setattr(resolver, "_ask_yes_no", lambda prompt: True)
    monkeypatch.setattr(resolver, "_clone_repository", lambda target, destination: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr("explain_codebase.cli.target_resolution.tempfile.mkdtemp", lambda prefix: str(checkout))

    with pytest.raises(click.ClickException, match="Git is required"):
        resolver._resolve_remote_target(repository)

    assert not checkout.exists()


def test_remote_confirmation_handles_noninteractive_input(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda: (_ for _ in ()).throw(EOFError()))

    with pytest.raises(typer.Exit) as exc_info:
        TargetResolver()._ask_yes_no("Continue? ")

    assert exc_info.value.exit_code == 2
    assert "Interactive confirmation is required" in capsys.readouterr().err


def test_scanner_rejects_symlink_outside_root(tmp_path: Path) -> None:
    project_root = tmp_path / "repository"
    project_root.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("SECRET = True\n", encoding="utf-8")
    link = project_root / "leak.py"
    try:
        link.symlink_to(outside_file)
    except OSError as error:
        pytest.skip(f"File symlinks are unavailable: {error}")

    assert ProjectScanner().scan(project_root) == []
    assert safe_read_text(link, root_path=project_root) == ""


def test_scanner_skips_oversized_files_and_supports_modern_js_extensions(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.py"
    oversized.write_bytes(b"x" * (MAX_SOURCE_FILE_BYTES + 1))
    extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"]
    expected = set()
    for index, extension in enumerate(extensions):
        source = tmp_path / f"source_{index}{extension}"
        source.write_text("value = 1\n", encoding="utf-8")
        expected.add(source)

    assert set(ProjectScanner().scan(tmp_path)) == expected
    assert safe_read_text(oversized) == ""


def test_max_files_is_positive_and_reports_truncation(monkeypatch, tmp_path: Path) -> None:
    for name in ["a.py", "b.py", "c.py"]:
        (tmp_path / name).write_text("value = 1\n", encoding="utf-8")

    from explain_codebase.scanner import project_scanner

    original_check = project_scanner.is_supported_source_file
    checked_paths: list[Path] = []

    def tracking_check(path: Path, **kwargs) -> bool:
        checked_paths.append(path)
        return original_check(path, **kwargs)

    monkeypatch.setattr(project_scanner, "is_supported_source_file", tracking_check)

    scanner = ProjectScanner(max_files=1)

    assert scanner.scan(tmp_path) == [tmp_path / "a.py"]
    assert checked_paths == [tmp_path / "a.py", tmp_path / "b.py", tmp_path / "c.py"]
    assert scanner.truncated is True
    assert scanner.discovered_files == 3
    assert scanner.skipped_files == 2
    with pytest.raises(ValueError, match="greater than zero"):
        ProjectScanner(max_files=0)
    with pytest.raises(ValueError, match="greater than zero"):
        ProjectScanner(max_files=-1)


def test_windows_reparse_attribute_is_treated_as_link() -> None:
    class ReparsePath:
        def is_symlink(self) -> bool:
            return False

        def lstat(self):
            return type("PathStat", (), {"st_file_attributes": 0x400})()

    assert is_link_or_reparse_point(ReparsePath())


def test_cli_treats_repository_paths_as_plain_text(capsys) -> None:
    malicious_path = "src/evil[/unexpected].py"

    CliRenderer().render(_analysis_result(malicious_path), verbose=True)

    assert malicious_path in capsys.readouterr().out


def test_cli_escapes_terminal_control_sequences(capsys) -> None:
    malicious_path = "src/evil\x1b]52;c;payload\x1b\\\r\nspoof.py"

    CliRenderer().render(_analysis_result(malicious_path), verbose=True)

    output = capsys.readouterr().out
    assert "\x1b" not in output
    assert "\r" not in output
    assert r"\x1b]52;c;payload\x1b\\r\nspoof.py" in output


def test_cli_human_output_supports_windows_legacy_encoding(monkeypatch) -> None:
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp1251")
    monkeypatch.setattr(sys, "stdout", stream)

    CliRenderer().render(_analysis_result(), verbose=True)
    stream.flush()

    output = buffer.getvalue().decode("cp1251")
    assert "Explain Codebase" in output
    assert "--------------------------------" in output


def test_atomic_graph_output_does_not_follow_existing_symlink(tmp_path: Path) -> None:
    protected_file = tmp_path / "protected.txt"
    protected_file.write_text("do not replace", encoding="utf-8")
    output_path = tmp_path / "dependency_graph.html"
    try:
        output_path.symlink_to(protected_file)
    except OSError as error:
        pytest.skip(f"File symlinks are unavailable: {error}")

    graph = nx.DiGraph()
    graph.add_node("main.py")
    GraphRenderer().render(_analysis_result(), graph, output_path)

    assert protected_file.read_text(encoding="utf-8") == "do not replace"
    assert not output_path.is_symlink()
    assert "<!DOCTYPE html>" in output_path.read_text(encoding="utf-8")


def test_atomic_output_removes_partial_file_after_sync_failure(monkeypatch, tmp_path: Path) -> None:
    output_path = tmp_path / "report.html"

    def fail_sync(_file_descriptor: int) -> None:
        raise OSError("simulated sync failure")

    monkeypatch.setattr(os, "fsync", fail_sync)

    with pytest.raises(OSError, match="simulated sync failure"):
        atomic_write_text(output_path, "sensitive report")

    assert not output_path.exists()
    assert list(tmp_path.glob(".report.html.*.tmp")) == []


def test_graph_node_limit_is_strict_even_for_required_nodes() -> None:
    scores = {f"module_{index}.py": index for index in range(100)}

    selected = GraphRenderer()._top_keys(scores, limit=10, required=set(scores))

    assert len(selected) == 10
    assert selected == {f"module_{index}.py" for index in range(90, 100)}


def test_graph_document_pins_external_script_and_sets_csp() -> None:
    graph = nx.DiGraph()
    graph.add_node("main.py")

    document = GraphRenderer()._build_graph_document(
        _analysis_result(),
        graph,
        title="Dependency Graph",
        options=GraphViewOptions(),
    )

    assert f'integrity="{VIS_NETWORK_SRI}"' in document
    assert 'crossorigin="anonymous"' in document
    assert 'referrerpolicy="no-referrer"' in document
    assert 'http-equiv="Content-Security-Policy"' in document
    assert "script-src 'nonce-" in document
    assert 'data-layout-mode="static"' in document
    assert 'data-motion-mode="ambient"' in document
    assert "physics: { enabled: false }" in document
    assert "layout: { improvedLayout: false, randomSeed: 17 }" in document
    assert "dragNodes: true" in document
    assert "fixed: { x: false, y: false }" in document
    assert 'type: "curvedCW"' in document
    assert "drawNodeBreathing" in document
    assert "drawEdgeFlow" in document
    assert "localCollisionTargets" in document
    assert "animateCollisionResolution" in document
    assert 'type: "dynamic"' not in document
    assert "startDrift" not in document
    assert "beginPhysics" not in document
    assert "startSimulation" not in document
    assert "network.focus" not in document
    assert "gradient" not in document
    assert "box-shadow" not in document
    assert "backdrop-filter" not in document
