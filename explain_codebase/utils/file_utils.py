from __future__ import annotations

from pathlib import Path


IGNORED_DIR_NAMES = {
    ".git",
    ".next",
    ".env",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts"}


def is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_DIR_NAMES for part in path.parts)


def is_supported_source_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file()


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")
