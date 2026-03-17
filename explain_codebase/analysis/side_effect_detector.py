from __future__ import annotations

from explain_codebase.models.file_info import FileInfo


class SideEffectDetector:
    def detect(self, files: list[FileInfo]) -> list[str]:
        return sorted({file.path for file in files if file.has_side_effects or file.side_effects})
