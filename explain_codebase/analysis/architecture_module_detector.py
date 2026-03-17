from __future__ import annotations

from pathlib import Path

from explain_codebase.models.file_info import FileInfo


class ArchitectureModuleDetector:
    KNOWN_MODULES = {
        "api",
        "components",
        "config",
        "controllers",
        "db",
        "integrations",
        "jobs",
        "middleware",
        "models",
        "repositories",
        "routes",
        "services",
        "workers",
    }

    def detect(self, files: list[FileInfo]) -> list[str]:
        modules: set[str] = set()
        for file in files:
            for part in Path(file.path).parts[:-1]:
                normalized = part.lower()
                if normalized in self.KNOWN_MODULES:
                    modules.add(f"{normalized}/")
        return sorted(modules)
