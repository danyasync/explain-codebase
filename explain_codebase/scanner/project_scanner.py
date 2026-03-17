from __future__ import annotations

from pathlib import Path

from explain_codebase.utils.file_utils import is_ignored_path, is_supported_source_file


class ProjectScanner:
    def __init__(self, max_files: int | None = None) -> None:
        self.max_files = max_files

    def scan(self, root_path: Path) -> list[Path]:
        files: list[Path] = []
        for path in root_path.rglob("*"):
            if is_ignored_path(path):
                continue
            if not is_supported_source_file(path):
                continue
            files.append(path)
            if self.max_files is not None and len(files) >= self.max_files:
                break
        return sorted(files)
