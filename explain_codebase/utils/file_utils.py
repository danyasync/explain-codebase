from __future__ import annotations

import os
import stat
from contextlib import suppress
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
SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}
MAX_SOURCE_FILE_BYTES = 1024 * 1024


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


def is_link_or_reparse_point(path: Path) -> bool:
    """Return whether a path can redirect traversal through a link or Windows reparse point."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction is not None and is_junction():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        return bool(reparse_flag and attributes & reparse_flag)
    except OSError:
        return True


def is_supported_source_file(
    path: Path,
    *,
    root_path: Path | None = None,
    max_bytes: int = MAX_SOURCE_FILE_BYTES,
) -> bool:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    if is_link_or_reparse_point(path):
        return False

    try:
        path_stat = path.lstat()
        if not stat.S_ISREG(path_stat.st_mode) or path_stat.st_size > max_bytes:
            return False
        if root_path is not None and not path.resolve(strict=True).is_relative_to(root_path.resolve(strict=True)):
            return False
    except (OSError, RuntimeError):
        return False
    return True


def safe_read_text(
    path: Path,
    *,
    root_path: Path | None = None,
    max_bytes: int = MAX_SOURCE_FILE_BYTES,
) -> str:
    if is_link_or_reparse_point(path):
        return ""

    descriptor: int | None = None
    try:
        if root_path is not None and not path.resolve(strict=True).is_relative_to(root_path.resolve(strict=True)):
            return ""

        flags = os.O_RDONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as source_file:
            descriptor = None
            file_stat = os.fstat(source_file.fileno())
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_size > max_bytes:
                return ""
            content = source_file.read(max_bytes + 1)
            if len(content) > max_bytes:
                return ""
        return content.decode("utf-8", errors="ignore")
    except (OSError, RuntimeError, ValueError):
        return ""
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
