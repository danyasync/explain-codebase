from __future__ import annotations

import networkx as nx


class DangerousFileDetector:
    def detect(self, graph: nx.DiGraph, limit: int = 5) -> list[str]:
        ranked = sorted(
            graph.nodes,
            key=lambda node: (-graph.in_degree(node), -(graph.in_degree(node) + graph.out_degree(node)), node),
        )
        return [node for node in ranked if graph.in_degree(node) > 0][:limit]
