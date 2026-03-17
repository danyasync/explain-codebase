from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from pathspec import PathSpec
    from pathspec.patterns import GitWildMatchPattern
except ImportError:  # pragma: no cover - dependency is declared in pyproject.toml
    PathSpec = None  # type: ignore[assignment]
    GitWildMatchPattern = None  # type: ignore[assignment]


def load_gitignore_spec(root_path: Path) -> PathSpec | None:
    gitignore_path = root_path / ".gitignore"
    if PathSpec is None or GitWildMatchPattern is None or not gitignore_path.is_file():
        return None

    patterns = gitignore_path.read_text(encoding="utf-8").splitlines()
    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def is_ignored_by_gitignore(relative_path: Path, spec: PathSpec | None, is_dir: bool = False) -> bool:
    if spec is None:
        return False

    normalized = relative_path.as_posix()
    if is_dir and normalized:
        normalized = f"{normalized.rstrip('/')}/"
    return spec.match_file(normalized)


def load_tracked_files(root_path: Path) -> set[str] | None:
    if not (root_path / ".git").exists():
        return None

    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root_path,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None

    tracked_files: set[str] = set()
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        tracked_files.add(raw_path.decode("utf-8", errors="ignore"))
    return tracked_files
