from __future__ import annotations

from pathlib import Path

import pytest

from explain_codebase.analysis.entrypoint_finder import EntrypointFinder
from explain_codebase.classify.file_classifier import FileClassifier
from explain_codebase.models.file_info import FileInfo
from explain_codebase.parsers.js_parser import JavaScriptParser
from explain_codebase.parsers.python_parser import PythonParser


def _parse(tmp_path: Path, content: str, name: str = "module.py") -> FileInfo:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return PythonParser().parse(path, tmp_path)


@pytest.mark.parametrize(
    "call",
    [
        'subprocess.run(["python", "--version"])',
        "runner.run()",
        "run()",
    ],
)
def test_arbitrary_run_calls_are_not_application_entrypoints(tmp_path: Path, call: str) -> None:
    info = _parse(tmp_path, f"{call}\n")

    assert not info.has_app_run


@pytest.mark.parametrize("call", ["uvicorn.run(app)", "app.run()"])
def test_exact_application_run_calls_are_entrypoint_signals(tmp_path: Path, call: str) -> None:
    info = _parse(tmp_path, f"{call}\n")

    assert info.has_app_run


@pytest.mark.parametrize(
    "call",
    [
        "typer.run(main)",
        "click.command()",
        "argparse.ArgumentParser()",
    ],
)
def test_supported_cli_calls_remain_cli_signals(tmp_path: Path, call: str) -> None:
    info = _parse(tmp_path, f"{call}\n")

    assert info.has_cli_signal


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ('__name__ == "__main__"', True),
        ('"__main__" == __name__', True),
        ('__name__ != "__main__"', False),
    ],
)
def test_main_guard_requires_an_exact_equality(tmp_path: Path, condition: str, expected: bool) -> None:
    info = _parse(tmp_path, f"if {condition}:\n    pass\n")

    assert info.has_main_guard is expected


@pytest.mark.parametrize("path", ["client.py", "cli_renderer.py"])
def test_cli_substrings_do_not_make_filename_an_entrypoint(path: str) -> None:
    info = FileInfo(path=path, language="python")

    assert FileClassifier().classify(info) != "entrypoint"


@pytest.mark.parametrize("path", ["main.py", "cli.py", "package/__main__.py", "services/__main__.py"])
def test_exact_entrypoint_filenames_remain_entrypoints(path: str) -> None:
    info = FileInfo(path=path, language="python")

    assert FileClassifier().classify(info) == "entrypoint"


@pytest.mark.parametrize(
    "path",
    [
        "tests/main.py",
        "__tests__/main.py",
        "test_cli.py",
        "unit_tests.py",
        "pkg/spec_server.py",
        "pkg/specs_server.py",
    ],
)
def test_test_role_wins_over_entrypoint_signals(path: str) -> None:
    info = FileInfo(
        path=path,
        language="python",
        has_main_guard=True,
        has_app_run=True,
        has_cli_signal=True,
    )
    classifier = FileClassifier()
    info.role = classifier.classify(info)

    assert info.role == "test"
    assert EntrypointFinder().find([info]) == []


def test_non_test_cli_signal_remains_an_entrypoint() -> None:
    info = FileInfo(path="commands.py", language="python", role="utility", has_cli_signal=True)

    assert EntrypointFinder().find([info]) == ["commands.py"]


def test_javascript_comments_and_strings_do_not_create_entrypoint_signals(tmp_path: Path) -> None:
    path = tmp_path / "docs.js"
    path.write_text(
        '// app.listen(3000); require("./commented")\n'
        'const example = "server.listen( and require(\\\"./string\\\")";\n'
        "/* createServer() */\n",
        encoding="utf-8",
    )

    info = JavaScriptParser().parse(path, tmp_path)

    assert not info.has_app_listen
    assert not info.has_create_server
    assert info.imports == []
    assert EntrypointFinder().find([info]) == []


def test_javascript_real_listen_call_remains_an_entrypoint(tmp_path: Path) -> None:
    path = tmp_path / "worker.js"
    path.write_text("app.listen (3000);\n", encoding="utf-8")

    info = JavaScriptParser().parse(path, tmp_path)

    assert info.has_app_listen
