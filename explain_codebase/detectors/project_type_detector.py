from __future__ import annotations

import json
from pathlib import Path

from explain_codebase.models.file_info import FileInfo
from explain_codebase.utils.file_utils import safe_read_text


class ProjectTypeDetector:
    PYTHON_CLI_MODULES = {"argparse", "click", "typer"}
    PYTHON_BACKEND_MODULES = {"django", "fastapi", "flask", "sqlalchemy"}

    def detect(self, root_path: Path, languages: list[str], files: list[FileInfo] | None = None) -> str:
        files = files or []
        package_json = root_path / "package.json"

        if "python" in languages:
            if self._is_python_cli(files):
                return "Python CLI tool"
            if self._has_python_backend_signals(files):
                return "Python backend service"

        if "javascript" in languages or "typescript" in languages:
            if package_json.exists():
                package_data = self._read_package_json(package_json)
                dependency_names: list[str] = []
                for section_name in ("dependencies", "devDependencies"):
                    section = package_data.get(section_name)
                    if isinstance(section, dict):
                        dependency_names.extend(str(name) for name in section)
                deps = " ".join(dependency_names).lower()
                if any(signal in deps for signal in ["react", "next", "vite"]):
                    return "Frontend application"
                if any(signal in deps for signal in ["express", "fastify", "nestjs"]):
                    return "Node backend service"
                if any(signal in deps for signal in ["commander", "yargs"]):
                    return "Node CLI tool"
            return "Node backend service"

        return "Unknown project"

    def _is_python_cli(self, files: list[FileInfo]) -> bool:
        for file in files:
            if file.has_cli_signal:
                return True
            imported_roots = {module.lstrip(".").split(".", 1)[0].lower() for module in file.imports}
            if file.role == "entrypoint" and imported_roots.intersection(self.PYTHON_CLI_MODULES):
                return True
        return False

    def _read_package_json(self, path: Path) -> dict[str, object]:
        content = safe_read_text(path, root_path=path.parent)
        if not content:
            return {}
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _has_python_backend_signals(self, files: list[FileInfo]) -> bool:
        for file in files:
            imported_roots = {module.lstrip(".").split(".", 1)[0].lower() for module in file.imports}
            if imported_roots.intersection(self.PYTHON_BACKEND_MODULES):
                return True
            if file.route_handlers:
                return True
        return False
