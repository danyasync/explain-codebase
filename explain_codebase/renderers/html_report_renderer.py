from __future__ import annotations

from html import escape
from pathlib import Path

import networkx as nx

from explain_codebase.models.analysis_result import AnalysisResult
from explain_codebase.renderers.graph_renderer import GraphRenderer


class HtmlReportRenderer:
    def __init__(self) -> None:
        self.graph_renderer = GraphRenderer()

    def render(self, result: AnalysisResult, graph: nx.DiGraph, output_path: Path) -> Path:
        graph_fragment = self.graph_renderer.build_graph_fragment(result, graph, container_id="architecture-graph")
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Explain Codebase Report</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --text: #0f172a;
      --muted: #475569;
      --border: #dbe3ef;
      --accent: #0f766e;
      --warn: #b45309;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #eff6ff 0%, var(--bg) 160px);
      color: var(--text);
    }}
    main {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1, h2 {{
      margin-bottom: 10px;
    }}
    p {{
      color: var(--muted);
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
    }}
    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
    }}
    li {{
      margin-bottom: 6px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: #ecfeff;
      color: var(--accent);
      margin-right: 8px;
      margin-bottom: 8px;
      font-size: 14px;
    }}
    .warning {{
      color: var(--warn);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Explain Codebase Report</h1>
      <p>{escape(result.summary)}</p>
    </header>

    <section>
      <h2>Project Summary</h2>
      <div class="grid">
        <div><strong>Project type</strong><br>{escape(result.project_type)}</div>
        <div><strong>Languages</strong><br>{escape(', '.join(result.languages) or 'unknown')}</div>
        <div><strong>Source files</strong><br>{result.total_files}</div>
        <div><strong>Entrypoints</strong><br>{len(result.entrypoints)}</div>
      </div>
    </section>

    <section>
      <h2>Entrypoints</h2>
      {self._list_html(result.entrypoints)}
    </section>

    <section>
      <h2>Core Modules</h2>
      {self._ranked_modules_table(result)}
    </section>

    <section>
      <h2>Side-effect Modules</h2>
      {self._list_html(result.side_effect_modules)}
    </section>

    <section>
      <h2>Architecture Modules</h2>
      {self._pill_list(result.architecture_modules)}
    </section>

    <section>
      <h2>Large Files</h2>
      {self._large_files_table(result)}
    </section>

    <section>
      <h2>Hotspots</h2>
      {self._hotspots_table(result)}
    </section>

    <section>
      <h2>Dangerous Files</h2>
      {self._list_html(result.dangerous_files)}
    </section>

    <section>
      <h2>Architecture Issues</h2>
      {self._issues_html(result)}
    </section>

    <section>
      <h2>Execution Flow</h2>
      {self._execution_flow_html(result)}
    </section>

    <section>
      <h2>Dependency Graph</h2>
      {graph_fragment}
    </section>
  </main>
</body>
</html>
"""
        output_path.write_text(html, encoding="utf-8")
        return output_path

    def _list_html(self, values: list[str]) -> str:
        if not values:
            return "<p>None detected.</p>"
        items = "".join(f"<li>{escape(value)}</li>" for value in values)
        return f"<ul>{items}</ul>"

    def _pill_list(self, values: list[str]) -> str:
        if not values:
            return "<p>None detected.</p>"
        return "".join(f'<span class="pill">{escape(value)}</span>' for value in values)

    def _ranked_modules_table(self, result: AnalysisResult) -> str:
        if not result.core_module_rankings:
            return "<p>None detected.</p>"
        rows = "".join(
            f"<tr><td>{index}</td><td>{escape(item.path)}</td><td>{item.score}</td></tr>"
            for index, item in enumerate(result.core_module_rankings, start=1)
        )
        return f"<table><thead><tr><th>#</th><th>File</th><th>Incoming imports</th></tr></thead><tbody>{rows}</tbody></table>"

    def _large_files_table(self, result: AnalysisResult) -> str:
        if not result.large_files:
            return "<p>None detected.</p>"
        rows = "".join(
            f"<tr><td>{escape(item.path)}</td><td>{item.loc}</td></tr>"
            for item in result.large_files
        )
        return f"<table><thead><tr><th>File</th><th>LOC</th></tr></thead><tbody>{rows}</tbody></table>"

    def _hotspots_table(self, result: AnalysisResult) -> str:
        if not result.hotspots:
            return "<p>None detected.</p>"
        rows = "".join(
            f"<tr><td>{escape(item.path)}</td><td>{item.incoming_imports}</td><td>{item.outgoing_imports}</td><td>{item.coupling_score}</td></tr>"
            for item in result.hotspots
        )
        return (
            "<table><thead><tr><th>File</th><th>Incoming</th><th>Outgoing</th><th>Coupling</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    def _issues_html(self, result: AnalysisResult) -> str:
        if not result.architecture_issues:
            return "<p>No architecture issues detected.</p>"
        items = "".join(
            f'<li><span class="warning">{escape(issue.issue_type)}</span>: {escape(issue.description)}</li>'
            for issue in result.architecture_issues
        )
        return f"<ul>{items}</ul>"

    def _execution_flow_html(self, result: AnalysisResult) -> str:
        if not result.execution_flow:
            return "<p>No clear execution flow inferred.</p>"
        items = "".join(f"<li>{escape(' -> '.join(path))}</li>" for path in result.execution_flow)
        return f"<ul>{items}</ul>"
