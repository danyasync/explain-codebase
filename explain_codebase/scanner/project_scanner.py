from __future__ import annotations

import os
from pathlib import Path

from explain_codebase.scanner.git_filter import is_ignored_by_gitignore, load_gitignore_spec, load_tracked_files
from explain_codebase.utils.file_utils import is_supported_source_file, matches_builtin_ignore


class ProjectScanner:
    def __init__(self, max_files: int | None = None) -> None:
        self.max_files = max_files

    def scan(self, root_path: Path) -> list[Path]:
        root_path = root_path.expanduser().resolve()
        gitignore_spec = load_gitignore_spec(root_path)
        tracked_files = load_tracked_files(root_path)

        if tracked_files is not None:
            files = self._scan_tracked_files(root_path, tracked_files, gitignore_spec)
        else:
            files = self._scan_filesystem(root_path, gitignore_spec)

        files = sorted(files)
        if self.max_files is not None:
            return files[: self.max_files]
        return files

    def _scan_tracked_files(self, root_path: Path, tracked_files: set[str], gitignore_spec) -> list[Path]:
        files: list[Path] = []
        for tracked_path in tracked_files:
            relative_path = Path(tracked_path)
            if self._is_ignored(relative_path, gitignore_spec):
                continue

            absolute_path = root_path / relative_path
            if not is_supported_source_file(absolute_path):
                continue
            files.append(absolute_path)
        return files

    def _scan_filesystem(self, root_path: Path, gitignore_spec) -> list[Path]:
        files: list[Path] = []
        for current_root, dir_names, file_names in os.walk(root_path, topdown=True):
            current_path = Path(current_root)

            kept_dirs: list[str] = []
            for directory in sorted(dir_names):
                relative_directory = (current_path / directory).relative_to(root_path)
                if self._is_ignored(relative_directory, gitignore_spec, is_dir=True):
                    continue
                kept_dirs.append(directory)
            dir_names[:] = kept_dirs

            for file_name in sorted(file_names):
                file_path = current_path / file_name
                relative_file = file_path.relative_to(root_path)
                if self._is_ignored(relative_file, gitignore_spec):
                    continue
                if not is_supported_source_file(file_path):
                    continue
                files.append(file_path)
        return files

    def _is_ignored(self, relative_path: Path, gitignore_spec, is_dir: bool = False) -> bool:
        if matches_builtin_ignore(relative_path, is_dir=is_dir):
            return True
        return is_ignored_by_gitignore(relative_path, gitignore_spec, is_dir=is_dir)
