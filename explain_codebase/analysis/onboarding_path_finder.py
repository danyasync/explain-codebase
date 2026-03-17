from __future__ import annotations

from collections import deque

import networkx as nx


class OnboardingPathFinder:
    ROLE_PRIORITY = {
        "entrypoint": 0,
        "controller": 1,
        "service": 2,
        "repository": 3,
        "model": 4,
        "config": 5,
        "utility": 6,
        "component": 7,
        "middleware": 8,
        "job": 9,
    }

    def build(
        self,
        graph: nx.DiGraph,
        entrypoints: list[str],
        file_roles: dict[str, str],
        core_modules: list[str],
        limit: int = 5,
    ) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()

        queue: deque[str] = deque(entrypoints or core_modules)
        while queue and len(ordered) < limit:
            node = queue.popleft()
            if node in seen:
                continue
            seen.add(node)
            ordered.append(node)

            neighbors = sorted(
                graph.successors(node),
                key=lambda neighbor: (
                    self.ROLE_PRIORITY.get(file_roles.get(neighbor, "utility"), 99),
                    -graph.in_degree(neighbor),
                    neighbor,
                ),
            )
            for neighbor in neighbors:
                if neighbor not in seen:
                    queue.append(neighbor)

        for node in core_modules:
            if len(ordered) >= limit:
                break
            if node not in seen:
                ordered.append(node)
                seen.add(node)

        return ordered
