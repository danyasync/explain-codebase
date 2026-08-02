from __future__ import annotations

import os
from pathlib import Path

from explain_codebase.scanner.git_filter import is_ignored_by_gitignore, load_gitignore_spec, load_tracked_files
from explain_codebase.utils.file_utils import is_link_or_reparse_point, is_supported_source_file, matches_builtin_ignore


class ProjectScanner:
    def __init__(self, max_files: int | None = None) -> None:
        if max_files is not None and max_files <= 0:
            raise ValueError("max_files must be greater than zero")
        self.max_files = max_files

    def scan(self, root_path: Path) -> list[Path]:
        root_path = root_path.expanduser().resolve()
        if not root_path.is_dir():
            raise ValueError(f"Project root is not a directory: {root_path}")
        gitignore_spec = load_gitignore_spec(root_path)
        tracked_files = load_tracked_files(root_path)

        if tracked_files is not None:
            files = self._scan_tracked_files(root_path, tracked_files, gitignore_spec)
        else:
            files = self._scan_filesystem(root_path, gitignore_spec)

        return sorted(files)

    def _scan_tracked_files(self, root_path: Path, tracked_files: set[str], gitignore_spec) -> list[Path]:
        files: list[Path] = []
        for tracked_path in sorted(tracked_files):
            relative_path = Path(tracked_path)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                continue
            if self._is_ignored(relative_path, gitignore_spec):
                continue

            absolute_path = root_path / relative_path
            if not is_supported_source_file(absolute_path, root_path=root_path):
                continue
            files.append(absolute_path)
            if self._at_limit(files):
                break
        return files

    def _scan_filesystem(self, root_path: Path, gitignore_spec) -> list[Path]:
        files: list[Path] = []
        for current_root, dir_names, file_names in os.walk(root_path, topdown=True, followlinks=False):
            current_path = Path(current_root)

            kept_dirs: list[str] = []
            for directory in sorted(dir_names):
                directory_path = current_path / directory
                if is_link_or_reparse_point(directory_path):
                    continue
                relative_directory = directory_path.relative_to(root_path)
                if self._is_ignored(relative_directory, gitignore_spec, is_dir=True):
                    continue
                kept_dirs.append(directory)
            dir_names[:] = kept_dirs

            for file_name in sorted(file_names):
                file_path = current_path / file_name
                relative_file = file_path.relative_to(root_path)
                if self._is_ignored(relative_file, gitignore_spec):
                    continue
                if not is_supported_source_file(file_path, root_path=root_path):
                    continue
                files.append(file_path)
                if self._at_limit(files):
                    return files
        return files

    def _is_ignored(self, relative_path: Path, gitignore_spec, is_dir: bool = False) -> bool:
        if matches_builtin_ignore(relative_path, is_dir=is_dir):
            return True
        return is_ignored_by_gitignore(relative_path, gitignore_spec, is_dir=is_dir)

    def _at_limit(self, files: list[Path]) -> bool:
        return self.max_files is not None and len(files) >= self.max_files
