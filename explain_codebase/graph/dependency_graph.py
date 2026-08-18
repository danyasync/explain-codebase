from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

import networkx as nx

from explain_codebase.models.file_info import FileInfo


class DependencyGraphBuilder:
    PYTHON_EXTENSIONS = (".py",)
    JAVASCRIPT_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs")
    TYPESCRIPT_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts")
    MODULE_EXTENSIONS = PYTHON_EXTENSIONS + JAVASCRIPT_EXTENSIONS + TYPESCRIPT_EXTENSIONS

    def __init__(self) -> None:
        self.unresolved_imports = 0

    def build(self, files: list[FileInfo]) -> nx.DiGraph:
        self.unresolved_imports = 0
        graph = nx.DiGraph()
        path_map = {file.path: file for file in files}
        python_module_index = self._build_python_module_index(files)
        python_module_roots = {module.partition(".")[0] for module in python_module_index}

        for file in files:
            graph.add_node(file.path)

        for file in files:
            import_groups = file.import_groups or [[imported] for imported in file.imports]
            for import_group in import_groups:
                resolved = False
                looks_local = False
                for imported in import_group:
                    target = self._resolve_import(file, imported, python_module_index, path_map)
                    if target:
                        graph.add_edge(file.path, target)
                        resolved = True
                    elif self._looks_like_local_import(file, imported, python_module_index, python_module_roots):
                        looks_local = True
                if looks_local and not resolved:
                    self.unresolved_imports += 1
        return graph

    def _build_python_module_index(self, files: list[FileInfo]) -> dict[str, str]:
        candidates: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for file in files:
            if file.language != "python" or PurePosixPath(file.path).suffix.lower() != ".py":
                continue

            path = PurePosixPath(file.path)
            parts = list(path.parts)
            module_parts = parts[:-1] if path.name == "__init__.py" else [*parts[:-1], path.stem]
            if not module_parts:
                continue

            candidates[".".join(module_parts)].append((0, file.path))
            if module_parts[0] == "src" and len(module_parts) > 1:
                candidates[".".join(module_parts[1:])].append((1, file.path))

        return {
            module: min(module_candidates, key=lambda candidate: (candidate[0], candidate[1]))[1]
            for module, module_candidates in candidates.items()
        }

    def _resolve_import(
        self,
        source: FileInfo,
        imported: str,
        python_module_index: dict[str, str],
        path_map: dict[str, FileInfo],
    ) -> str | None:
        if imported.startswith("."):
            return self._resolve_relative_import(source, imported, path_map)

        if source.language != "python":
            return None

        normalized = imported.replace("/", ".")
        return python_module_index.get(normalized)

    def _resolve_relative_import(
        self,
        source: FileInfo,
        imported: str,
        path_map: dict[str, FileInfo],
    ) -> str | None:
        source_path = PurePosixPath(source.path)
        if source.language in {"javascript", "typescript"}:
            target_base = self._resolve_javascript_relative_base(source_path, imported)
        elif source.language == "python":
            target_base = self._resolve_python_relative_base(source_path, imported)
        else:
            return None
        if target_base is None:
            return None

        imported_suffix = PurePosixPath(imported.replace("\\", "/")).suffix.lower()
        if imported_suffix in self.MODULE_EXTENSIONS:
            return self._compatible_target(source, target_base.as_posix(), path_map)

        extensions = self._extension_priority(source)
        candidates = [f"{target_base.as_posix()}{extension}" for extension in extensions]
        candidates.extend(self._index_candidates(target_base, source, extensions))
        for candidate in candidates:
            target = self._compatible_target(source, candidate, path_map)
            if target is not None:
                return target
        return None

    def _extension_priority(self, source: FileInfo) -> tuple[str, ...]:
        source_suffix = PurePosixPath(source.path).suffix.lower()
        if source.language == "python":
            return self.PYTHON_EXTENSIONS
        if source.language == "javascript":
            family = self.JAVASCRIPT_EXTENSIONS
        elif source.language == "typescript":
            # JavaScript is a deliberate fallback for mixed projects; TypeScript variants always win.
            family = self.TYPESCRIPT_EXTENSIONS + self.JAVASCRIPT_EXTENSIONS
        else:
            return ()
        return (source_suffix, *(extension for extension in family if extension != source_suffix))

    def _index_candidates(
        self,
        target_base: PurePosixPath,
        source: FileInfo,
        extensions: tuple[str, ...],
    ) -> list[str]:
        if source.language == "python":
            return [(target_base / "__init__.py").as_posix()]
        return [(target_base / f"index{extension}").as_posix() for extension in extensions]

    def _compatible_target(
        self,
        source: FileInfo,
        candidate: str,
        path_map: dict[str, FileInfo],
    ) -> str | None:
        target = path_map.get(candidate)
        if target is None:
            return None
        if source.language == "python" and target.language == "python":
            return candidate
        if source.language == "javascript" and target.language == "javascript":
            return candidate
        if source.language == "typescript" and target.language in {"typescript", "javascript"}:
            return candidate
        return None

    def _looks_like_local_import(
        self,
        source: FileInfo,
        imported: str,
        python_module_index: dict[str, str],
        python_module_roots: set[str],
    ) -> bool:
        if imported.startswith("."):
            return bool(imported.strip("."))
        if source.language != "python":
            return False

        normalized = imported.replace("/", ".")
        if normalized in python_module_index:
            return False
        if any(module.startswith(f"{normalized}.") for module in python_module_index):
            return False
        return normalized.partition(".")[0] in python_module_roots

    def _resolve_python_relative_base(self, source: PurePosixPath, imported: str) -> PurePosixPath | None:
        dots = len(imported) - len(imported.lstrip("."))
        remainder = imported.lstrip(".")
        base_parts = list(source.parent.parts)
        if not base_parts:
            return None
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
