from __future__ import annotations

import subprocess
from pathlib import Path

from explain_codebase.utils.file_utils import safe_read_text
from explain_codebase.utils.git_utils import hardened_git_runtime

try:
    from pathspec.gitignore import GitIgnoreSpec
except ImportError:  # pragma: no cover - dependency is declared in pyproject.toml
    GitIgnoreSpec = None  # type: ignore[assignment]


def load_gitignore_spec(root_path: Path) -> GitIgnoreSpec | None:
    gitignore_path = root_path / ".gitignore"
    if GitIgnoreSpec is None or not gitignore_path.is_file():
        return None

    patterns = safe_read_text(gitignore_path, root_path=root_path).splitlines()
    if not patterns:
        return None
    return GitIgnoreSpec.from_lines(patterns)


def is_ignored_by_gitignore(relative_path: Path, spec: GitIgnoreSpec | None, is_dir: bool = False) -> bool:
    if spec is None:
        return False

    normalized = relative_path.as_posix()
    if is_dir and normalized:
        normalized = f"{normalized.rstrip('/')}/"
    return spec.match_file(normalized)


def load_tracked_files(root_path: Path) -> set[str] | None:
    """Return tracked files and untracked files that are visible to Git."""
    if not (root_path / ".git").exists():
        return None

    try:
        with hardened_git_runtime(safe_directory=root_path) as (command_prefix, environment):
            completed = subprocess.run(
                [
                    *command_prefix,
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "-z",
                    "--",
                ],
                cwd=root_path,
                capture_output=True,
                check=False,
                env=environment,
                timeout=20,
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None

    visible_files: set[str] = set()
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        visible_files.add(raw_path.decode("utf-8", errors="ignore"))
    return visible_files
