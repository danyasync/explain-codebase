from __future__ import annotations

import networkx as nx

from explain_codebase.models.analysis_result import HotspotRecord


class HotspotDetector:
    def detect(self, graph: nx.DiGraph, limit: int = 5) -> list[HotspotRecord]:
        hotspots = [
            HotspotRecord(
                path=node,
                incoming_imports=graph.in_degree(node),
                outgoing_imports=graph.out_degree(node),
                coupling_score=graph.in_degree(node) + graph.out_degree(node),
            )
            for node in graph.nodes
        ]
        hotspots.sort(key=lambda item: (-item.coupling_score, -item.incoming_imports, item.path))
        return hotspots[:limit]
