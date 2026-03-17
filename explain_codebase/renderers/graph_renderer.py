from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from explain_codebase.models.analysis_result import AnalysisResult


class GraphRenderer:
    def render(self, result: AnalysisResult, graph: nx.DiGraph, output_path: Path) -> Path:
        html = self._build_graph_document(result, graph, title="Dependency Graph")
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def build_graph_fragment(self, result: AnalysisResult, graph: nx.DiGraph, container_id: str) -> str:
        variable_id = container_id.replace("-", "_")
        nodes_json = json.dumps(self._build_nodes(result))
        edges_json = json.dumps(self._build_edges(graph))
        options_json = json.dumps(self._build_options())
        return f"""
<div id="{container_id}" style="height: 720px; border: 1px solid #d0d7de; border-radius: 12px;"></div>
<script src="https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"></script>
<script>
const nodes_{variable_id} = new vis.DataSet({nodes_json});
const edges_{variable_id} = new vis.DataSet({edges_json});
const container_{variable_id} = document.getElementById("{container_id}");
const data_{variable_id} = {{ nodes: nodes_{variable_id}, edges: edges_{variable_id} }};
const options_{variable_id} = {options_json};
new vis.Network(container_{variable_id}, data_{variable_id}, options_{variable_id});
</script>
"""

    def _build_graph_document(self, result: AnalysisResult, graph: nx.DiGraph, title: str) -> str:
        fragment = self.build_graph_fragment(result, graph, container_id="dependency-graph")
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: #f6f8fb;
      color: #0f172a;
    }}
    main {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px;
    }}
    h1 {{
      margin-bottom: 8px;
    }}
    p {{
      color: #475569;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{title}</h1>
    <p>{result.summary}</p>
    {fragment}
  </main>
</body>
</html>
"""

    def _build_nodes(self, result: AnalysisResult) -> list[dict[str, object]]:
        core_paths = {item.path for item in result.core_module_rankings}
        side_effect_paths = set(result.side_effect_modules)
        hotspots = {item.path for item in result.hotspots}

        nodes = []
        for path, role in sorted(result.file_roles.items()):
            tags = []
            if path in core_paths:
                tags.append("core")
            if path in side_effect_paths:
                tags.append("side-effect")
            if path in hotspots:
                tags.append("hotspot")
            tag_suffix = f" [{', '.join(tags)}]" if tags else ""
            nodes.append(
                {
                    "id": path,
                    "label": Path(path).name,
                    "title": f"{path}\\nrole={role}{tag_suffix}",
                    "group": role,
                    "shape": "dot",
                    "size": 18 if path in core_paths else 12,
                }
            )
        return nodes

    def _build_edges(self, graph: nx.DiGraph) -> list[dict[str, str]]:
        return [{"from": source, "to": target, "arrows": "to"} for source, target in graph.edges]

    def _build_options(self) -> dict[str, object]:
        return {
            "layout": {"improvedLayout": True},
            "interaction": {"hover": True, "navigationButtons": True},
            "physics": {"enabled": True, "solver": "forceAtlas2Based"},
            "nodes": {"font": {"face": "Segoe UI", "size": 13}},
            "edges": {"color": {"color": "#94a3b8"}, "smooth": {"type": "dynamic"}},
        }
