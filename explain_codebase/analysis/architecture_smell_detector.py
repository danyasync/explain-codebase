from __future__ import annotations

from itertools import islice

import networkx as nx

from explain_codebase.models.analysis_result import ArchitectureIssue
from explain_codebase.models.file_info import FileInfo


class ArchitectureSmellDetector:
    def detect(self, graph: nx.DiGraph, files: list[FileInfo], limit: int = 5) -> list[ArchitectureIssue]:
        issues: list[ArchitectureIssue] = []
        file_map = {file.path: file for file in files}

        for cycle in islice(nx.simple_cycles(graph), limit):
            if len(cycle) < 2:
                continue
            issues.append(
                ArchitectureIssue(
                    issue_type="circular_dependency",
                    description=f"Circular dependency: {' -> '.join(cycle + [cycle[0]])}",
                    affected_paths=cycle,
                )
            )

        incoming = [graph.in_degree(node) for node in graph.nodes if graph.in_degree(node) > 0]
        average_incoming = (sum(incoming) / len(incoming)) if incoming else 0
        threshold = max(5, int(average_incoming * 3) if average_incoming else 5)

        for node in graph.nodes:
            file_info = file_map.get(node)
            if file_info is None:
                continue
            lowered = node.lower()
            if file_info.role != "utility" and not any(token in lowered for token in ["util", "helper", "types"]):
                continue
            in_degree = graph.in_degree(node)
            if in_degree >= threshold:
                issues.append(
                    ArchitectureIssue(
                        issue_type="god_module",
                        description=f"Utility module too large: {node} used by {in_degree} modules",
                        affected_paths=[node],
                    )
                )

        return issues[:limit]
