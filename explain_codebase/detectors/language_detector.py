from __future__ import annotations

from pathlib import Path


class LanguageDetector:
    EXTENSION_TO_LANGUAGE = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
    }

    def detect(self, path: Path) -> str:
        return self.EXTENSION_TO_LANGUAGE.get(path.suffix.lower(), "unknown")
