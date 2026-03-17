from __future__ import annotations

from pathlib import Path

import networkx as nx

from explain_codebase.models.file_info import FileInfo


class DependencyGraphBuilder:
    def build(self, files: list[FileInfo]) -> nx.DiGraph:
        graph = nx.DiGraph()
        path_map = {file.path: file for file in files}
        module_index = self._build_module_index(files)

        for file in files:
            graph.add_node(file.path)

        for file in files:
            for imported in file.imports:
                target = self._resolve_import(file.path, imported, module_index, path_map)
                if target:
                    graph.add_edge(file.path, target)
        return graph

    def _build_module_index(self, files: list[FileInfo]) -> dict[str, str]:
        index: dict[str, str] = {}
        for file in files:
            path = Path(file.path)
            parts = list(path.with_suffix("").parts)
            dotted = ".".join(parts)
            index[dotted] = file.path
            if parts and parts[-1] == "__init__":
                index[".".join(parts[:-1])] = file.path
        return index

    def _resolve_import(
        self,
        source_path: str,
        imported: str,
        module_index: dict[str, str],
        path_map: dict[str, FileInfo],
    ) -> str | None:
        source = Path(source_path)
        if imported.startswith("."):
            return self._resolve_relative_import(source, imported, path_map)

        normalized = imported.replace("/", ".")
        if normalized in module_index:
            return module_index[normalized]

        candidate = imported.replace(".", "/")
        for extension in [".py", ".js", ".ts"]:
            file_candidate = f"{candidate}{extension}"
            if file_candidate in path_map:
                return file_candidate
        for extension in ["/__init__.py", "/index.js", "/index.ts"]:
            file_candidate = f"{candidate}{extension}"
            if file_candidate in path_map:
                return file_candidate
        return None

    def _resolve_relative_import(
        self,
        source: Path,
        imported: str,
        path_map: dict[str, FileInfo],
    ) -> str | None:
        dots = len(imported) - len(imported.lstrip("."))
        remainder = imported.lstrip(".")
        base = source.parent
        for _ in range(max(dots - 1, 0)):
            base = base.parent

        if "/" in remainder or "\\" in remainder:
            cleaned = remainder.lstrip("/\\")
            relative_parts = [part for part in Path(cleaned).parts if part not in {".", ""}]
        else:
            relative_parts = [part for part in remainder.split(".") if part]
        target_base = base.joinpath(*relative_parts) if relative_parts else base

        candidates = [
            target_base.with_suffix(".py"),
            target_base.with_suffix(".js"),
            target_base.with_suffix(".ts"),
            target_base / "__init__.py",
            target_base / "index.js",
            target_base / "index.ts",
        ]
        for candidate in candidates:
            candidate_str = candidate.as_posix()
            if candidate_str in path_map:
                return candidate_str
        return None
