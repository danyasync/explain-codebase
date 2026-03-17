from __future__ import annotations

import networkx as nx

from explain_codebase.models.analysis_result import RankedModule


class CoreModuleDetector:
    def detect(self, graph: nx.DiGraph, limit: int = 5) -> tuple[list[str], list[RankedModule], dict[str, int]]:
        centrality = {node: graph.in_degree(node) for node in graph.nodes}
        ranked = sorted(
            [(node, degree) for node, degree in centrality.items() if degree > 0],
            key=lambda item: (-item[1], item[0]),
        )
        average = (sum(degree for _, degree in ranked) / len(ranked)) if ranked else 0
        threshold = max(1, int(round(average))) if average else 1

        filtered = [RankedModule(path=node, score=degree) for node, degree in ranked if degree >= threshold]
        if not filtered:
            filtered = [RankedModule(path=node, score=degree) for node, degree in ranked[:limit]]

        core_modules = [item.path for item in filtered[:limit]]
        return core_modules, filtered[:limit], centrality
