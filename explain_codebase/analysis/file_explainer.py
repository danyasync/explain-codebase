from __future__ import annotations

from pathlib import Path

import networkx as nx

from explain_codebase.models.analysis_result import FileExplanation
from explain_codebase.models.file_info import FileInfo
from explain_codebase.models.project_info import ProjectInfo


class FileExplainer:
    ROLE_LABELS = {
        "component": "Component layer",
        "config": "Configuration layer",
        "controller": "Controller layer",
        "entrypoint": "Entrypoint",
        "job": "Job layer",
        "middleware": "Middleware layer",
        "model": "Model layer",
        "repository": "Repository layer",
        "service": "Service layer",
        "test": "Test layer",
        "utility": "Utility layer",
    }

    ROLE_RESPONSIBILITIES = {
        "component": "UI composition",
        "config": "configuration management",
        "controller": "request handling",
        "entrypoint": "application startup",
        "job": "background processing",
        "middleware": "cross-cutting request processing",
        "model": "data modeling",
        "repository": "data access",
        "service": "business logic orchestration",
        "test": "behavior verification",
        "utility": "shared helper logic",
    }

    def explain(self, target_path: Path, project_info: ProjectInfo, graph: nx.DiGraph) -> FileExplanation:
        relative_path = self._normalize_target_path(target_path, project_info.root_path)
        file_map = {file.path: file for file in project_info.files}
        file_info = file_map.get(relative_path)
        if file_info is None:
            raise FileNotFoundError(f"File not found in analyzed project: {target_path}")

        role = file_info.role or "utility"
        return FileExplanation(
            path=file_info.path,
            role=self.ROLE_LABELS.get(role, role.title()),
            used_by=sorted(graph.predecessors(file_info.path)),
            depends_on=sorted(graph.successors(file_info.path)),
            responsibilities=self._build_responsibilities(file_info),
            line_count=file_info.line_count,
            incoming_imports=graph.in_degree(file_info.path),
            outgoing_imports=graph.out_degree(file_info.path),
            side_effects=sorted(file_info.side_effects),
        )

    def _normalize_target_path(self, target_path: Path, root_path: Path) -> str:
        resolved_target = target_path.resolve()
        return resolved_target.relative_to(root_path.resolve()).as_posix()

    def _build_responsibilities(self, file_info: FileInfo) -> list[str]:
        responsibilities: list[str] = []
        role = file_info.role or "utility"

        default_responsibility = self.ROLE_RESPONSIBILITIES.get(role)
        if default_responsibility is not None:
            responsibilities.append(default_responsibility)

        normalized_names = [name.lower() for name in [Path(file_info.path).stem, *file_info.functions, *file_info.classes]]
        if any("auth" in name or "password" in name or "login" in name for name in normalized_names):
            responsibilities.append("authentication and password handling")
        if any("user" in name for name in normalized_names):
            responsibilities.append("user lookup and management")
        if any("payment" in name or "billing" in name for name in normalized_names):
            responsibilities.append("billing and payment flows")
        if file_info.route_handlers:
            responsibilities.append("HTTP route handling")
        if "database" in file_info.side_effects:
            responsibilities.append("database access")
        if "network" in file_info.side_effects:
            responsibilities.append("network communication")
        if "filesystem" in file_info.side_effects:
            responsibilities.append("filesystem access")
        if "cache" in file_info.side_effects:
            responsibilities.append("cache integration")

        return list(dict.fromkeys(responsibilities))[:5]
