from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path


IGNORED_DIR_NAMES = {
    ".git",
    ".idea",
    ".next",
    ".env",
    ".eggs",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "env",
    "htmlcov",
    "node_modules",
    "temp",
    "tmp",
    "venv",
}

IGNORED_DIR_PATTERNS = {"*.egg-info"}
IGNORED_FILE_NAMES = {"dependency_graph.html", "codebase_report.html"}
IGNORED_FILE_PATTERNS = {"*.log", "*.pyc"}
SUPPORTED_EXTENSIONS = {".py", ".js", ".ts"}


def matches_builtin_ignore(relative_path: Path, is_dir: bool = False) -> bool:
    parts = relative_path.parts
    if not parts:
        return False

    directory_parts = parts if is_dir else parts[:-1]
    for part in directory_parts:
        if part in IGNORED_DIR_NAMES:
            return True
        if any(fnmatch(part, pattern) for pattern in IGNORED_DIR_PATTERNS):
            return True

    name = parts[-1]
    if is_dir:
        return name in IGNORED_DIR_NAMES or any(fnmatch(name, pattern) for pattern in IGNORED_DIR_PATTERNS)

    if name in IGNORED_FILE_NAMES:
        return True
    return any(fnmatch(name, pattern) for pattern in IGNORED_FILE_PATTERNS)


def is_ignored_path(path: Path, root_path: Path | None = None) -> bool:
    relative_path = path
    if root_path is not None:
        try:
            relative_path = path.relative_to(root_path)
        except ValueError:
            relative_path = path
    return matches_builtin_ignore(relative_path, is_dir=path.is_dir())


def is_supported_source_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
