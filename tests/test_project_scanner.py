from pathlib import Path

from explain_codebase.scanner.project_scanner import ProjectScanner


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_paths(root: Path, files: list[Path]) -> set[str]:
    return {file.relative_to(root).as_posix() for file in files}


def test_scanner_ignores_builtin_noise_directories_and_files(tmp_path: Path) -> None:
    _write(tmp_path / "app.py", "import src.service\n")
    _write(tmp_path / "src" / "service.py", "VALUE = 1\n")
    _write(tmp_path / ".venv" / "lib.py", "IGNORED = True\n")
    _write(tmp_path / "node_modules" / "leftpad" / "index.js", "module.exports = {}\n")
    _write(tmp_path / "temp" / "debug.py", "IGNORED = True\n")
    _write(tmp_path / "__pycache__" / "service.pyc", "binary\n")
    _write(tmp_path / "dependency_graph.html", "<html></html>\n")
    _write(tmp_path / "codebase_report.html", "<html></html>\n")

    files = ProjectScanner().scan(tmp_path)

    assert _relative_paths(tmp_path, files) == {"app.py", "src/service.py"}


def test_scanner_applies_root_gitignore_rules(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", "ignored_dir/\nartifacts/*.ts\n*.pyc\n")
    _write(tmp_path / "main.py", "print('hello')\n")
    _write(tmp_path / "src" / "feature.ts", "export const feature = true;\n")
    _write(tmp_path / "ignored_dir" / "helper.py", "IGNORED = True\n")
    _write(tmp_path / "artifacts" / "generated.ts", "export const ignored = true;\n")
    _write(tmp_path / "cache.pyc", "binary\n")

    files = ProjectScanner().scan(tmp_path)

    assert _relative_paths(tmp_path, files) == {"main.py", "src/feature.ts"}


def test_scanner_uses_git_tracked_files_only(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    _write(tmp_path / ".gitignore", "config.py\n")
    _write(tmp_path / "app.py", "print('hello')\n")
    _write(tmp_path / "config.py", "SETTING = True\n")
    _write(tmp_path / "scratch.py", "IGNORED = True\n")
    _write(tmp_path / "temp" / "local.py", "IGNORED = True\n")

    monkeypatch.setattr(
        "explain_codebase.scanner.project_scanner.load_tracked_files",
        lambda root_path: {"app.py", "config.py", "temp/local.py"},
    )

    files = ProjectScanner().scan(tmp_path)

    assert _relative_paths(tmp_path, files) == {"app.py"}
