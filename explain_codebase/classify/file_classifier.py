from __future__ import annotations

from pathlib import Path

from explain_codebase.models.file_info import FileInfo


class FileClassifier:
    ROLE_PATTERNS = {
        "entrypoint": ["main", "app", "server", "cli"],
        "config": ["config", "settings"],
        "controller": ["controller", "route", "handler"],
        "service": ["service"],
        "repository": ["repository", "repo"],
        "model": ["model", "schema", "entity"],
        "utility": ["util", "helper"],
        "test": ["test", "spec"],
        "middleware": ["middleware"],
        "job": ["job", "worker", "task"],
        "component": ["component"],
    }

    DIRECTORY_HINTS = {
        "controllers": "controller",
        "routes": "controller",
        "services": "service",
        "models": "model",
        "repositories": "repository",
        "jobs": "job",
        "middleware": "middleware",
        "components": "component",
        "tests": "test",
    }

    def classify(self, file_info: FileInfo) -> str:
        path = Path(file_info.path)
        lowered_name = path.stem.lower()
        lowered_parts = [part.lower() for part in path.parts]

        if file_info.has_main_guard or file_info.has_app_run or file_info.has_app_listen or file_info.has_create_server:
            return "entrypoint"

        for part in lowered_parts:
            if part in self.DIRECTORY_HINTS:
                return self.DIRECTORY_HINTS[part]

        for role, patterns in self.ROLE_PATTERNS.items():
            if any(pattern in lowered_name for pattern in patterns):
                return role

        if file_info.route_handlers:
            return "controller"
        if file_info.has_side_effects:
            return "service"
        return "utility"
