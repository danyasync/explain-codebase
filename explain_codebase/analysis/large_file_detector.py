from __future__ import annotations

from explain_codebase.models.analysis_result import LargeFileRecord
from explain_codebase.models.file_info import FileInfo


class LargeFileDetector:
    def detect(self, files: list[FileInfo], threshold: int = 800) -> list[LargeFileRecord]:
        large_files = [
            LargeFileRecord(path=file.path, loc=file.line_count)
            for file in files
            if file.line_count > threshold
        ]
        return sorted(large_files, key=lambda item: (-item.loc, item.path))
