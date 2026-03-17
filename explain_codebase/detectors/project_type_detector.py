from __future__ import annotations

import json
from pathlib import Path


class ProjectTypeDetector:
    def detect(self, root_path: Path, languages: list[str]) -> str:
        package_json = root_path / "package.json"
        pyproject_toml = root_path / "pyproject.toml"
        requirements = root_path / "requirements.txt"

        if "python" in languages:
            if self._is_python_cli(root_path):
                return "Python CLI tool"
            if (
                pyproject_toml.exists()
                or requirements.exists()
                or (root_path / "manage.py").exists()
                or (root_path / "app.py").exists()
                or (root_path / "main.py").exists()
                or self._has_python_backend_signals(root_path)
            ):
                return "Python backend service"

        if "javascript" in languages or "typescript" in languages:
            if package_json.exists():
                package_data = self._read_package_json(package_json)
                deps = " ".join(
                    list(package_data.get("dependencies", {}).keys())
                    + list(package_data.get("devDependencies", {}).keys())
                ).lower()
                if any(signal in deps for signal in ["react", "next", "vite"]):
                    return "Frontend application"
                if any(signal in deps for signal in ["express", "fastify", "nestjs"]):
                    return "Node backend service"
                if any(signal in deps for signal in ["commander", "yargs"]):
                    return "Node CLI tool"
            return "Node backend service"

        return "Unknown project"

    def _is_python_cli(self, root_path: Path) -> bool:
        for path in root_path.rglob("*.py"):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="utf-8", errors="ignore")
            lowered = content.lower()
            if any(signal in lowered for signal in ["import typer", "import click", "import argparse"]):
                return True
        return False

    def _read_package_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _has_python_backend_signals(self, root_path: Path) -> bool:
        for path in root_path.rglob("*.py"):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = path.read_text(encoding="utf-8", errors="ignore")
            lowered = content.lower()
            if any(signal in lowered for signal in ["fastapi", "flask", "django", "sqlalchemy", "app = "]):
                return True
        return False
