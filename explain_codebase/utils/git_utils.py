from __future__ import annotations

import os
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path


def resolve_git_executable(path_value: str | None = None) -> Path:
    """Resolve Git from absolute PATH entries without consulting the current directory."""
    search_path = os.environ.get("PATH", os.defpath) if path_value is None else path_value
    directory_entries = _absolute_path_entries(search_path)
    executable_names = _git_executable_names()

    for directory in directory_entries:
        for executable_name in executable_names:
            candidate = directory / executable_name
            try:
                candidate_stat = candidate.stat()
            except OSError:
                continue
            if not stat.S_ISREG(candidate_stat.st_mode) or not os.access(candidate, os.X_OK):
                continue
            try:
                return candidate.resolve(strict=True)
            except OSError:
                continue

    raise FileNotFoundError("Git executable was not found in an absolute PATH directory.")


def safe_git_environment(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment that does not inherit caller-controlled Git behavior."""
    source = os.environ if environ is None else environ
    result = {
        key: value
        for key, value in source.items()
        if not key.upper().startswith("GIT_") and key.upper() != "PATH"
    }
    source_path = next((value for key, value in source.items() if key.upper() == "PATH"), os.defpath)
    result["PATH"] = os.pathsep.join(str(path) for path in _absolute_path_entries(source_path))
    result.update(
        {
            "GIT_ALLOW_PROTOCOL": "https",
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return result


@contextmanager
def hardened_git_runtime(safe_directory: Path | None = None) -> Iterator[tuple[list[str], dict[str, str]]]:
    """Yield a hardened Git command prefix and environment for one operation."""
    executable = resolve_git_executable()
    with tempfile.TemporaryDirectory(prefix="explain_codebase_git_hooks_") as hooks_directory:
        hooks_path = Path(hooks_directory).resolve().as_posix()
        command_prefix = [
            str(executable),
            "-c",
            "core.fsmonitor=false",
            "-c",
            f"core.hooksPath={hooks_path}",
        ]
        if safe_directory is not None:
            command_prefix.extend(["-c", f"safe.directory={safe_directory.resolve(strict=True)}"])
        yield command_prefix, safe_git_environment()


def _absolute_path_entries(path_value: str) -> list[Path]:
    result: list[Path] = []
    for raw_entry in path_value.split(os.pathsep):
        normalized = raw_entry.strip().strip('"')
        if not normalized:
            continue
        expanded = Path(os.path.expandvars(normalized)).expanduser()
        if expanded.is_absolute():
            result.append(expanded)
    return result


def _git_executable_names() -> list[str]:
    if os.name != "nt":
        return ["git"]

    extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
    normalized_extensions = [extension for extension in extensions if extension]
    return [f"git{extension}" for extension in normalized_extensions]
