from __future__ import annotations

from collections import deque

import networkx as nx

from explain_codebase.models.analysis_result import AnalysisResult


class ExplanationEngine:
    def build_execution_flow(
        self,
        graph: nx.DiGraph,
        entrypoints: list[str],
        file_roles: dict[str, str] | None = None,
        max_depth: int = 5,
        max_paths: int = 5,
    ) -> list[list[str]]:
        file_roles = file_roles or {}
        role_priority = {
            "entrypoint": 0,
            "controller": 1,
            "service": 2,
            "repository": 3,
            "model": 4,
            "config": 5,
            "utility": 6,
        }
        flows: list[list[str]] = []
        for entrypoint in entrypoints[:max_paths]:
            queue: deque[tuple[str, list[str]]] = deque([(entrypoint, [entrypoint])])
            seen: set[tuple[str, ...]] = set()

            while queue and len(flows) < max_paths:
                node, path = queue.popleft()
                if len(path) >= max_depth or graph.out_degree(node) == 0:
                    flows.append(path)
                    continue

                neighbors = sorted(
                    graph.successors(node),
                    key=lambda neighbor: (
                        role_priority.get(file_roles.get(neighbor, "utility"), 99),
                        -graph.in_degree(neighbor),
                        neighbor,
                    ),
                )
                if not neighbors:
                    flows.append(path)
                    continue

                for neighbor in neighbors[:3]:
                    candidate = tuple(path + [neighbor])
                    if candidate in seen or neighbor in path:
                        continue
                    seen.add(candidate)
                    queue.append((neighbor, list(candidate)))
        return flows

    def summarize(self, result: AnalysisResult) -> str:
        return (
            f"{result.project_type} with {result.total_files} source files. "
            f"Found {len(result.entrypoints)} entrypoints, "
            f"{len(result.core_modules)} core modules, "
            f"{len(result.side_effect_modules)} side-effect modules, "
            f"{len(result.hotspots)} hotspots, and "
            f"{len(result.architecture_issues)} architecture issues."
        )
