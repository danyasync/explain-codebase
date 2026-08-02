from __future__ import annotations

from pathlib import PurePosixPath

import networkx as nx

from explain_codebase.models.file_info import FileInfo


class DependencyGraphBuilder:
    MODULE_EXTENSIONS = (".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
    INDEX_FILES = (
        "__init__.py",
        "index.js",
        "index.jsx",
        "index.mjs",
        "index.cjs",
        "index.ts",
        "index.tsx",
        "index.mts",
        "index.cts",
    )
    JAVASCRIPT_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}

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
            path = PurePosixPath(file.path)
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
        source = PurePosixPath(source_path)
        if imported.startswith("."):
            return self._resolve_relative_import(source, imported, path_map)

        normalized = imported.replace("/", ".")
        if normalized in module_index:
            return module_index[normalized]

        candidate = imported.replace(".", "/")
        for extension in self.MODULE_EXTENSIONS:
            file_candidate = f"{candidate}{extension}"
            if file_candidate in path_map:
                return file_candidate
        for index_file in self.INDEX_FILES:
            file_candidate = f"{candidate}/{index_file}"
            if file_candidate in path_map:
                return file_candidate
        return None

    def _resolve_relative_import(
        self,
        source: PurePosixPath,
        imported: str,
        path_map: dict[str, FileInfo],
    ) -> str | None:
        if source.suffix.lower() in self.JAVASCRIPT_EXTENSIONS:
            target_base = self._resolve_javascript_relative_base(source, imported)
        else:
            target_base = self._resolve_python_relative_base(source, imported)
        if target_base is None:
            return None

        candidates = [target_base.as_posix()]
        candidates.extend(f"{target_base.as_posix()}{extension}" for extension in self.MODULE_EXTENSIONS)
        candidates.extend((target_base / index_file).as_posix() for index_file in self.INDEX_FILES)
        for candidate in candidates:
            if candidate in path_map:
                return candidate
        return None

    def _resolve_python_relative_base(self, source: PurePosixPath, imported: str) -> PurePosixPath | None:
        dots = len(imported) - len(imported.lstrip("."))
        remainder = imported.lstrip(".")
        base_parts = list(source.parent.parts)
        for _ in range(max(dots - 1, 0)):
            if len(base_parts) <= 1:
                return None
            base_parts.pop()

        if "/" in remainder or "\\" in remainder:
            cleaned = remainder.lstrip("/\\")
            relative_parts = [part for part in PurePosixPath(cleaned.replace("\\", "/")).parts if part not in {".", ""}]
        else:
            relative_parts = [part for part in remainder.split(".") if part]
        base = PurePosixPath(*base_parts)
        return base.joinpath(*relative_parts) if relative_parts else base

    def _resolve_javascript_relative_base(self, source: PurePosixPath, imported: str) -> PurePosixPath | None:
        parts = list(source.parent.parts)
        for part in PurePosixPath(imported.replace("\\", "/")).parts:
            if part in {"", "."}:
                continue
            if part == "..":
                if parts:
                    parts.pop()
                else:
                    return None
                continue
            parts.append(part)
        return PurePosixPath(*parts)
