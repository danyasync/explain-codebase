from __future__ import annotations

from pathlib import Path

from explain_codebase.models.file_info import FileInfo
from explain_codebase.parsers.js_parser import JavaScriptParser


class TypeScriptParser(JavaScriptParser):
    def parse(self, path: Path, root_path: Path) -> FileInfo:
        info = super().parse(path, root_path)
        info.language = "typescript"
        return info
