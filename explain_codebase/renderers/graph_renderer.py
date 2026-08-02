from __future__ import annotations

import json
from collections import Counter, deque
from dataclasses import dataclass
from html import escape
from math import log1p
from pathlib import Path
from secrets import token_urlsafe

import networkx as nx

from explain_codebase.models.analysis_result import AnalysisResult
from explain_codebase.utils.output_utils import atomic_write_text

VIS_NETWORK_URL = "https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"
VIS_NETWORK_SRI = "sha384-6ox9IspbVlrc5vabD45kZcCJ8HeSwMAQjf9Iq48U/+srTVTNzsB7EqDC5oYpA0WC"


@dataclass(frozen=True)
class GraphViewOptions:
    mode: str = "architecture"
    full: bool = False
    max_nodes: int = 40


class GraphRenderer:
    VIEW_LABELS = {
        "architecture": "Architecture view",
        "file": "File view",
        "entrypoint": "Entrypoint flow",
        "side-effects": "Side effects view",
        "risk": "Risk view",
    }

    ROLE_COLORS = {
        "entrypoint": ("#4ade80", "#22c55e"),
        "service": ("#60a5fa", "#3b82f6"),
        "controller": ("#7dd3fc", "#38bdf8"),
        "repository": ("#f87171", "#ef4444"),
        "model": ("#fb7185", "#f43f5e"),
        "config": ("#fbbf24", "#f59e0b"),
        "middleware": ("#a78bfa", "#8b5cf6"),
        "job": ("#fb923c", "#f97316"),
        "component": ("#22d3ee", "#06b6d4"),
        "utility": ("#94a3b8", "#64748b"),
        "test": ("#cbd5e1", "#94a3b8"),
        "unknown": ("#94a3b8", "#64748b"),
    }

    def render(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        output_path: Path,
        options: GraphViewOptions | None = None,
    ) -> Path:
        html = self._build_graph_document(result, graph, title="Dependency Graph", options=options or GraphViewOptions())
        atomic_write_text(output_path, html)
        return output_path

    def build_graph_fragment(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        container_id: str,
        options: GraphViewOptions | None = None,
        script_nonce: str | None = None,
    ) -> str:
        options = options or GraphViewOptions()
        payload_json = json.dumps(self._build_payload(result, graph, options)).replace("</", "<\\/")
        return self._build_fragment_markup(container_id, payload_json, script_nonce=script_nonce)

    def _build_graph_document(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        title: str,
        options: GraphViewOptions,
    ) -> str:
        script_nonce = token_urlsafe(24)
        fragment = self.build_graph_fragment(
            result,
            graph,
            container_id="dependency-graph",
            options=options,
            script_nonce=script_nonce,
        )
        content_security_policy = self.content_security_policy(script_nonce)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="{content_security_policy}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(96, 165, 250, 0.08), transparent 22%),
        radial-gradient(circle at bottom right, rgba(45, 212, 191, 0.07), transparent 20%),
        #111317;
      color: #e5edf7;
    }}
    main {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
    }}
    p {{
      max-width: 880px;
      color: #9aa8bc;
      line-height: 1.65;
      margin-bottom: 20px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <p>{escape(result.summary)}</p>
    {fragment}
  </main>
</body>
</html>
"""

    @staticmethod
    def content_security_policy(script_nonce: str) -> str:
        return (
            "default-src 'none'; "
            f"script-src 'nonce-{script_nonce}'; "
            "style-src 'unsafe-inline'; img-src data:; connect-src 'none'; "
            "font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
        )

    def _build_fragment_markup(self, container_id: str, payload_json: str, script_nonce: str | None = None) -> str:
        nonce_attribute = f' nonce="{escape(script_nonce, quote=True)}"' if script_nonce else ""
        return f"""
<div class="ecb-shell" id="{container_id}-shell">
  <style>
    #{container_id}-shell {{
      position: relative;
      background:
        radial-gradient(circle at top left, rgba(96, 165, 250, 0.08), transparent 28%),
        radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.06), transparent 24%),
        linear-gradient(180deg, rgba(20, 24, 31, 0.98) 0%, rgba(14, 17, 22, 0.98) 100%);
      border: 1px solid rgba(120, 141, 168, 0.18);
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 28px 80px rgba(0, 0, 0, 0.32);
    }}
    #{container_id}-shell .ecb-toolbar, #{container_id}-shell .ecb-meta {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 14px;
      padding: 16px 18px;
    }}
    #{container_id}-shell .ecb-toolbar {{
      border-bottom: 1px solid rgba(120, 141, 168, 0.14);
      background: rgba(15, 19, 24, 0.86);
      backdrop-filter: blur(16px);
    }}
    #{container_id}-shell .ecb-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    #{container_id}-shell button, #{container_id}-shell input {{
      font: inherit;
    }}
    #{container_id}-shell .ecb-mode {{
      border: 1px solid rgba(120, 141, 168, 0.22);
      border-radius: 999px;
      padding: 9px 14px;
      background: rgba(27, 34, 43, 0.9);
      color: #c9d6e6;
      cursor: pointer;
      transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
    }}
    #{container_id}-shell .ecb-mode:hover {{
      background: rgba(34, 43, 54, 0.96);
      border-color: rgba(125, 211, 252, 0.26);
      transform: translateY(-1px);
    }}
    #{container_id}-shell .ecb-mode.is-active {{
      background: linear-gradient(180deg, rgba(59, 130, 246, 0.24) 0%, rgba(37, 99, 235, 0.24) 100%);
      border-color: rgba(96, 165, 250, 0.6);
      color: #f8fbff;
      box-shadow: inset 0 0 0 1px rgba(191, 219, 254, 0.1);
    }}
    #{container_id}-shell .ecb-search {{
      min-width: 250px;
      border: 1px solid rgba(120, 141, 168, 0.2);
      border-radius: 999px;
      padding: 10px 15px;
      background: rgba(12, 16, 21, 0.92);
      color: #edf4ff;
      outline: none;
      transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    #{container_id}-shell .ecb-search::placeholder {{
      color: #74839a;
    }}
    #{container_id}-shell .ecb-search:focus {{
      border-color: rgba(96, 165, 250, 0.45);
      box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
    }}
    #{container_id}-shell .ecb-filter {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #9aa8bc;
      font-size: 14px;
    }}
    #{container_id}-shell .ecb-filter input[type="checkbox"] {{
      accent-color: #60a5fa;
    }}
    #{container_id}-shell .ecb-filter input[type="range"] {{
      accent-color: #60a5fa;
    }}
    #{container_id}-shell .ecb-meta {{
      color: #8ea0b6;
      font-size: 14px;
      padding-top: 12px;
      padding-bottom: 0;
    }}
    #{container_id}-shell .ecb-stage {{
      position: relative;
      min-height: 820px;
      padding: 14px;
    }}
    #{container_id} {{
      height: 780px;
      border-radius: 20px;
      background:
        radial-gradient(circle at top left, rgba(96, 165, 250, 0.08), transparent 22%),
        radial-gradient(circle at center right, rgba(34, 211, 238, 0.07), transparent 20%),
        radial-gradient(circle at bottom left, rgba(168, 85, 247, 0.05), transparent 20%),
        linear-gradient(180deg, #111317 0%, #0d1015 100%);
      border: 1px solid rgba(120, 141, 168, 0.12);
    }}
    #{container_id}-shell .ecb-legend {{
      position: absolute;
      top: 28px;
      right: 28px;
      width: 260px;
      padding: 16px 18px;
      border: 1px solid rgba(120, 141, 168, 0.16);
      border-radius: 18px;
      background: rgba(17, 21, 27, 0.82);
      box-shadow: 0 22px 48px rgba(0, 0, 0, 0.28);
      backdrop-filter: blur(16px);
      z-index: 5;
    }}
    #{container_id}-shell .ecb-legend h3 {{
      margin: 0 0 10px;
      font-size: 15px;
      color: #edf4ff;
    }}
    #{container_id}-shell .ecb-legend-item {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
      color: #9aa8bc;
      font-size: 14px;
    }}
    #{container_id}-shell .ecb-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      border: 1px solid rgba(255, 255, 255, 0.12);
      flex: 0 0 auto;
    }}
    #{container_id}-shell .ecb-note {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid rgba(120, 141, 168, 0.14);
      color: #7f90a7;
      font-size: 13px;
      line-height: 1.5;
    }}
    #{container_id}-shell .ecb-overlay-note {{
      position: absolute;
      left: 28px;
      bottom: 28px;
      padding: 12px 14px;
      border: 1px solid rgba(120, 141, 168, 0.14);
      border-radius: 14px;
      background: rgba(17, 21, 27, 0.78);
      color: #8ea0b6;
      font-size: 13px;
      line-height: 1.5;
      backdrop-filter: blur(12px);
      z-index: 5;
      max-width: 280px;
    }}
    #{container_id}-shell .vis-network:focus {{
      outline: none;
    }}
    #{container_id}-shell .ecb-tooltip {{
      position: absolute;
      left: 0;
      top: 0;
      width: 300px;
      padding: 14px 15px;
      border: 1px solid rgba(120, 141, 168, 0.2);
      border-radius: 16px;
      background: rgba(12, 16, 21, 0.96);
      box-shadow: 0 18px 40px rgba(0, 0, 0, 0.34);
      backdrop-filter: blur(14px);
      color: #edf4ff;
      font-size: 13px;
      line-height: 1.55;
      opacity: 0;
      pointer-events: none;
      transform: translate3d(-9999px, -9999px, 0);
      transition: opacity 0.16s ease, transform 0.16s ease;
      z-index: 7;
    }}
    #{container_id}-shell .ecb-tooltip.is-visible {{
      opacity: 1;
    }}
    #{container_id}-shell .ecb-tooltip-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #7f90a7;
      margin-bottom: 4px;
    }}
    #{container_id}-shell .ecb-tooltip-value {{
      color: #f8fbff;
      margin-bottom: 10px;
      word-break: break-word;
    }}
    #{container_id}-shell .ecb-tooltip-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 12px;
    }}
    #{container_id}-shell .ecb-tooltip-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(45, 55, 72, 0.46);
      color: #cbd7e6;
      font-size: 12px;
      margin-top: 2px;
    }}
    #{container_id}-shell .ecb-tooltip-meta {{
      color: #dbe7f5;
    }}
    #{container_id}-shell .vis-tooltip {{
      display: none !important;
    }}
    @media (max-width: 1040px) {{
      #{container_id}-shell .ecb-legend {{
        position: static;
        width: auto;
        margin: 0 14px 14px;
      }}
      #{container_id}-shell .ecb-overlay-note {{
        position: static;
        max-width: none;
        margin: 0 14px 14px;
      }}
    }}
  </style>

  <div class="ecb-toolbar">
    <div class="ecb-group">
      <button class="ecb-mode" data-view="architecture">Architecture view</button>
      <button class="ecb-mode" data-view="file">File view</button>
      <button class="ecb-mode" data-view="entrypoint">Entrypoint flow</button>
      <button class="ecb-mode" data-view="side-effects">Side effects view</button>
      <button class="ecb-mode" data-view="risk">Risk view</button>
      <input class="ecb-search" type="search" placeholder="Search file" aria-label="Search file">
    </div>
    <div class="ecb-group">
      <label class="ecb-filter"><input type="checkbox" data-filter="hide-utilities"> Hide utilities</label>
      <label class="ecb-filter"><input type="checkbox" data-filter="hide-isolated"> Hide isolated nodes</label>
      <label class="ecb-filter"><input type="checkbox" data-filter="core-only"> Show only core modules</label>
      <label class="ecb-filter"><input type="checkbox" data-filter="side-effects-only"> Show only side effects</label>
      <label class="ecb-filter">Minimum importance <input type="range" min="0" max="30" value="0" data-filter="importance"></label>
      <button class="ecb-mode" data-export="png">Export PNG</button>
    </div>
  </div>

  <div class="ecb-meta">
    <div data-description></div>
    <div data-stats></div>
  </div>

  <div class="ecb-stage">
    <aside class="ecb-legend">
      <h3>Legend</h3>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#22c55e"></span>Green     Entrypoint</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#3b82f6"></span>Blue      Service</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#ef4444"></span>Red       Repository / DB</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#f59e0b"></span>Yellow    Config</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#8b5cf6"></span>Purple    Middleware</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#f97316"></span>Orange    External integration</div>
      <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#94a3b8"></span>Gray      Utility</div>
      <div class="ecb-note">Node size = importance<br>Edge = import relationship</div>
    </aside>
    <div id="{container_id}"></div>
    <div class="ecb-tooltip" data-tooltip aria-hidden="true" hidden></div>
    <div class="ecb-overlay-note">Hover a node to spotlight its neighborhood. Click to pin the focus, then export the current view as PNG.</div>
  </div>
</div>
<script src="{VIS_NETWORK_URL}" integrity="{VIS_NETWORK_SRI}" crossorigin="anonymous" referrerpolicy="no-referrer"{nonce_attribute}></script>
<script{nonce_attribute}>
(function() {{
  const payload = {payload_json};
  const shell = document.getElementById("{container_id}-shell");
  const container = document.getElementById("{container_id}");
  if (typeof vis === "undefined") {{
    container.innerHTML = '<div style="padding:32px;color:#9aa8bc">Graph library could not be loaded in this browser.</div>';
    return;
  }}

  const state = {{
    view: payload.defaultView,
    search: "",
    spotlight: null,
    hoveredNode: null,
    draggingNode: null,
    scale: 1,
    filters: {{ hideUtilities: false, hideIsolated: false, coreOnly: false, sideEffectsOnly: false, minImportance: 0 }},
  }};
  let physicsTimer = null;
  let physicsFrame = null;
  let driftFrame = null;
  let previousPositions = null;
  let stableFrames = 0;
  let physicsActive = false;
  let physicsStartedAt = 0;
  let driftStartedAt = 0;
  const VELOCITY_THRESHOLD = 0.02;
  const STABLE_FRAMES_REQUIRED = 60;
  const MAX_PHYSICS_DURATION_MS = 5000;
  const DRAG_RESTABILIZE_DELAY_MS = 120;
  const CANVAS_PADDING = 100;
  const DRIFT_AMPLITUDE = 1.2;
  const DRIFT_PERIOD_MS = 8000;
  const descriptionEl = shell.querySelector("[data-description]");
  const statsEl = shell.querySelector("[data-stats]");
  const tooltipEl = shell.querySelector("[data-tooltip]");
  const nodeSet = new vis.DataSet([]);
  const edgeSet = new vis.DataSet([]);
  const visibleState = {{
    nodes: [],
    edges: [],
    nodeMap: new Map(),
    basePositions: new Map(),
  }};
  const network = new vis.Network(container, {{ nodes: nodeSet, edges: edgeSet }}, {{
    layout: {{ improvedLayout: true, randomSeed: 17 }},
    interaction: {{
      hover: true,
      hoverConnectedEdges: false,
      navigationButtons: true,
      keyboard: true,
      tooltipDelay: 120,
      zoomView: true,
      dragView: true,
      hideEdgesOnDrag: false
    }},
    physics: {{
      enabled: true,
      solver: "barnesHut",
      stabilization: {{ enabled: true, iterations: 420, fit: true }},
      barnesHut: {{
        gravitationalConstant: -1800,
        centralGravity: 0.015,
        springLength: 260,
        springConstant: 0.018,
        damping: 0.92,
        avoidOverlap: 1.55
      }},
      minVelocity: 0.02,
      maxVelocity: 18,
      timestep: 0.45,
      adaptiveTimestep: true
    }},
    nodes: {{
      borderWidth: 1.8,
      borderWidthSelected: 3.2,
      labelHighlightBold: false,
      font: {{ face: "Segoe UI", size: 13, color: "#dbe7f5", strokeWidth: 4, strokeColor: "rgba(17,19,23,0.92)" }}
    }},
    edges: {{
      arrows: {{ to: {{ enabled: true, scaleFactor: 0.45 }} }},
      smooth: {{ type: "dynamic", roundness: 0.24 }},
      selectionWidth: 0,
      hoverWidth: 0
    }}
  }});

  function rgba(hex, alpha) {{
    const clean = (hex || "#94a3b8").replace("#", "");
    const normalized = clean.length === 3 ? clean.split("").map((p) => p + p).join("") : clean;
    const n = parseInt(normalized, 16);
    return `rgba(${{(n >> 16) & 255}}, ${{(n >> 8) & 255}}, ${{n & 255}}, ${{alpha}})`;
  }}

  function visibleView() {{
    return payload.views[state.view] || payload.views.architecture;
  }}

  function activeFocusId() {{
    return state.hoveredNode || state.spotlight;
  }}

  function currentPositions(nodeIds) {{
    if (!nodeIds.length) {{
      return {{}};
    }}
    try {{
      return network.getPositions(nodeIds);
    }} catch (error) {{
      return {{}};
    }}
  }}

  function escapeHtml(value) {{
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }}

  function seedPositions(nodes) {{
    const clusters = new Map();
    nodes.forEach((node) => {{
      const key = node.cluster || node.id;
      if (!clusters.has(key)) {{
        clusters.set(key, []);
      }}
      clusters.get(key).push(node);
    }});
    const orderedClusters = Array.from(clusters.entries()).sort((left, right) => left[0].localeCompare(right[0]));
    const positions = new Map();
    const clusterCount = Math.max(orderedClusters.length, 1);
    const clusterRadius = clusterCount === 1 ? 0 : 320 + Math.min(200, clusterCount * 14);
    orderedClusters.forEach(([clusterName, members], clusterIndex) => {{
      const baseHash = clusterName.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
      const baseAngle = clusterCount === 1 ? 0 : ((clusterIndex / clusterCount) * Math.PI * 2) + ((baseHash % 17) * 0.02);
      const centerX = Math.cos(baseAngle) * clusterRadius;
      const centerY = Math.sin(baseAngle) * clusterRadius * 0.74;
      const orderedMembers = members.slice().sort((left, right) => right.importance - left.importance || left.id.localeCompare(right.id));
      orderedMembers.forEach((node, memberIndex) => {{
        const ringIndex = Math.floor(memberIndex / 6);
        const localCount = Math.min(6, orderedMembers.length - ringIndex * 6);
        const localIndex = memberIndex % 6;
        const localAngle = localCount <= 1 ? 0 : (localIndex / localCount) * Math.PI * 2;
        const localRadius = 42 + ringIndex * 46 + Math.min(14, Math.log1p(Math.max(node.importance, 1)) * 4);
        const centerBias = node.isEntrypoint || node.isCore ? 0.72 : 1;
        positions.set(node.id, {{
          x: centerX + Math.cos(localAngle + baseAngle * 0.2) * localRadius * centerBias,
          y: centerY + Math.sin(localAngle + baseAngle * 0.2) * localRadius * centerBias,
        }});
      }});
    }});
    return positions;
  }}

  function tooltipMarkup(node) {{
    const sideEffects = Array.isArray(node.sideEffects) && node.sideEffects.length ? node.sideEffects : ["none"];
    const riskMarkup = node.risk
      ? `<div><div class="ecb-tooltip-label">Risk score</div><div class="ecb-tooltip-meta">${{escapeHtml(node.risk)}}</div></div>`
      : "";
    return `
      <div class="ecb-tooltip-label">File path</div>
      <div class="ecb-tooltip-value">${{escapeHtml(node.path || node.id)}}</div>
      <div class="ecb-tooltip-grid">
        <div><div class="ecb-tooltip-label">Role</div><div class="ecb-tooltip-meta">${{escapeHtml(node.roleLabel || node.role || "unknown")}}</div></div>
        <div><div class="ecb-tooltip-label">Incoming imports</div><div class="ecb-tooltip-meta">${{node.incoming ?? 0}}</div></div>
        <div><div class="ecb-tooltip-label">Outgoing imports</div><div class="ecb-tooltip-meta">${{node.outgoing ?? 0}}</div></div>
        ${{riskMarkup}}
      </div>
      <div class="ecb-tooltip-label" style="margin-top:10px;">Side effects</div>
      <div class="ecb-tooltip-value">
        ${{sideEffects.map((item) => `<span class="ecb-tooltip-chip">${{escapeHtml(item)}}</span>`).join("")}}
      </div>
    `;
  }}

  function placeTooltip(pointer) {{
    if (tooltipEl.hidden) {{
      return;
    }}
    const width = tooltipEl.offsetWidth || 300;
    const height = tooltipEl.offsetHeight || 160;
    let left = pointer.x + 20;
    let top = pointer.y + 20;
    left = Math.min(left, container.clientWidth - width - 18);
    top = Math.min(top, container.clientHeight - height - 18);
    left = Math.max(18, left);
    top = Math.max(18, top);
    tooltipEl.style.transform = `translate3d(${{left}}px, ${{top}}px, 0)`;
  }}

  function showTooltip(nodeId, pointer) {{
    const node = visibleState.nodeMap.get(nodeId);
    if (!node) {{
      return;
    }}
    tooltipEl.innerHTML = tooltipMarkup(node);
    tooltipEl.hidden = false;
    tooltipEl.setAttribute("aria-hidden", "false");
    placeTooltip(pointer);
    window.requestAnimationFrame(() => tooltipEl.classList.add("is-visible"));
  }}

  function hideTooltip() {{
    tooltipEl.classList.remove("is-visible");
    tooltipEl.setAttribute("aria-hidden", "true");
    window.setTimeout(() => {{
      if (!tooltipEl.classList.contains("is-visible")) {{
        tooltipEl.hidden = true;
        tooltipEl.style.transform = "translate3d(-9999px, -9999px, 0)";
      }}
    }}, 170);
  }}

  function updateVisibleState(nodes, edges) {{
    visibleState.nodes = nodes;
    visibleState.edges = edges;
    visibleState.nodeMap = new Map(nodes.map((node) => [node.id, node]));
  }}

  function resolveBasePositions(nodes, livePositions, seededPositions) {{
    const nextBasePositions = new Map(visibleState.basePositions);
    nodes.forEach((node) => {{
      if (nextBasePositions.has(node.id)) {{
        return;
      }}
      nextBasePositions.set(node.id, livePositions[node.id] || seededPositions.get(node.id) || {{ x: 0, y: 0 }});
    }});
    return nextBasePositions;
  }}

  function neighbors(nodeId, edges) {{
    const incoming = new Set();
    const outgoing = new Set();
    edges.forEach((edge) => {{
      if (edge.from === nodeId) outgoing.add(edge.to);
      if (edge.to === nodeId) incoming.add(edge.from);
    }});
    return {{ incoming, outgoing }};
  }}

  function filterView(view) {{
    const query = state.search.trim().toLowerCase();
    let nodes = view.nodes.filter((node) => {{
      if (state.filters.hideUtilities && node.role === "utility") return false;
      if (state.filters.hideIsolated && node.isIsolated) return false;
      if (state.filters.coreOnly && !node.isCore) return false;
      if (state.filters.sideEffectsOnly && !node.isSideEffect) return false;
      if (node.importance < state.filters.minImportance) return false;
      return true;
    }});
    let ids = new Set(nodes.map((node) => node.id));
    let edges = view.edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to));
    if (query) {{
      const matched = new Set();
      nodes.forEach((node) => {{
        const haystack = [node.id, node.label, node.cluster, node.role].join(" ").toLowerCase();
        if (haystack.includes(query)) matched.add(node.id);
      }});
      if (matched.size) {{
        const kept = new Set(matched);
        edges.forEach((edge) => {{
          if (matched.has(edge.from) || matched.has(edge.to)) {{
            kept.add(edge.from);
            kept.add(edge.to);
          }}
        }});
        nodes = nodes.filter((node) => kept.has(node.id));
        ids = kept;
        edges = edges.filter((edge) => ids.has(edge.from) && ids.has(edge.to));
      }}
    }}
    return {{ nodes, edges }};
  }}

  function persistBasePositions(nodeIds = nodeSet.getIds()) {{
    if (typeof network.storePositions === "function") {{
      try {{
        network.storePositions();
      }} catch (error) {{
        // Ignore storePositions failures and fall back to reading live coordinates.
      }}
    }}
    const positions = currentPositions(nodeIds);
    const nextBasePositions = new Map(visibleState.basePositions);
    Object.entries(positions).forEach(([nodeId, position]) => {{
      nextBasePositions.set(nodeId, position);
    }});
    visibleState.basePositions = nextBasePositions;
    driftStartedAt = performance.now();
  }}

  function applyVisualPositions(anchors) {{
    if (!anchors || !anchors.size) {{
      return;
    }}
    let changed = false;
    anchors.forEach((position, nodeId) => {{
      const bodyNode = network.body?.nodes?.[nodeId];
      if (!bodyNode) {{
        return;
      }}
      bodyNode.x = position.x;
      bodyNode.y = position.y;
      if (bodyNode.options) {{
        bodyNode.options.x = position.x;
        bodyNode.options.y = position.y;
      }}
      changed = true;
    }});
    if (changed) {{
      network.redraw();
    }}
  }}

  function stopDrift(resetToAnchors = false) {{
    if (driftFrame) {{
      window.cancelAnimationFrame(driftFrame);
      driftFrame = null;
    }}
    if (resetToAnchors && visibleState.basePositions.size) {{
      applyVisualPositions(visibleState.basePositions);
    }}
  }}

  function startDrift() {{
    stopDrift(true);
    if (!visibleState.basePositions.size) {{
      persistBasePositions();
    }}
    if (!visibleState.basePositions.size) {{
      return;
    }}
    const anchors = new Map(visibleState.basePositions);
    const driftStep = (timestamp) => {{
      if (physicsActive || state.draggingNode) {{
        driftFrame = window.requestAnimationFrame(driftStep);
        return;
      }}
      const updates = [];
      anchors.forEach((anchor, nodeId) => {{
        if (!nodeSet.get(nodeId)) {{
          return;
        }}
        const phaseSeed = nodeId.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
        const phase = phaseSeed * 0.07;
        const elapsed = (timestamp - driftStartedAt) / DRIFT_PERIOD_MS;
        const importance = visibleState.nodeMap.get(nodeId)?.importance || 1;
        const amplitude = DRIFT_AMPLITUDE + Math.min(0.75, Math.log1p(importance) * 0.16);
        const dx = Math.sin((elapsed * Math.PI * 2) + phase) * amplitude;
        const dy = Math.cos((elapsed * Math.PI * 2 * 0.92) + phase) * amplitude * 0.72;
        updates.push({{ id: nodeId, x: anchor.x + dx, y: anchor.y + dy }});
      }});
      if (updates.length) {{
        applyVisualPositions(new Map(updates.map((item) => [item.id, {{ x: item.x, y: item.y }}])));
      }}
      driftFrame = window.requestAnimationFrame(driftStep);
    }};
    driftFrame = window.requestAnimationFrame(driftStep);
  }}

  function stopPhysics() {{
    physicsActive = false;
    previousPositions = null;
    stableFrames = 0;
    if (physicsTimer) {{
      window.clearTimeout(physicsTimer);
      physicsTimer = null;
    }}
    if (physicsFrame) {{
      window.cancelAnimationFrame(physicsFrame);
      physicsFrame = null;
    }}
    network.stopSimulation();
    network.setOptions({{ physics: {{ enabled: false }} }});
    persistBasePositions();
    shell.classList.add("is-settled");
    startDrift();
  }}

  function monitorPhysics(nodeIds) {{
    if (!physicsActive) {{
      return;
    }}
    const positions = currentPositions(nodeIds);
    const ids = Object.keys(positions);
    if (previousPositions) {{
      let totalMovement = 0;
      let samples = 0;
      ids.forEach((id) => {{
        const current = positions[id];
        const previous = previousPositions[id];
        if (!current || !previous) {{
          return;
        }}
        totalMovement += Math.hypot(current.x - previous.x, current.y - previous.y);
        samples += 1;
      }});
      const averageVelocity = samples ? totalMovement / samples : 0;
      stableFrames = averageVelocity < VELOCITY_THRESHOLD ? stableFrames + 1 : 0;
      if (stableFrames >= STABLE_FRAMES_REQUIRED || performance.now() - physicsStartedAt > MAX_PHYSICS_DURATION_MS) {{
        stopPhysics();
        return;
      }}
    }}
    previousPositions = positions;
    physicsFrame = window.requestAnimationFrame(() => monitorPhysics(nodeIds));
  }}

  function beginPhysics(nodeIds) {{
    shell.classList.remove("is-settled");
    stopDrift(true);
    if (physicsTimer) {{
      window.clearTimeout(physicsTimer);
      physicsTimer = null;
    }}
    if (physicsFrame) {{
      window.cancelAnimationFrame(physicsFrame);
      physicsFrame = null;
    }}
    physicsActive = true;
    physicsStartedAt = performance.now();
    previousPositions = null;
    stableFrames = 0;
    network.setOptions({{ physics: {{ enabled: true }} }});
    network.startSimulation();
    physicsTimer = window.setTimeout(() => monitorPhysics(nodeIds), 80);
  }}

  function applyInteractiveStyles(focusSearch = false) {{
    const focusId = activeFocusId();
    const spotlightNeighbors = focusId ? neighbors(focusId, visibleState.edges) : {{ incoming: new Set(), outgoing: new Set() }};
    nodeSet.update(visibleState.nodes.map((node) => {{
      const highlighted = !focusId || node.id === focusId || spotlightNeighbors.incoming.has(node.id) || spotlightNeighbors.outgoing.has(node.id);
      const showLabel = node.showLabel
        || state.scale >= 1.34
        || node.id === focusId
        || ((spotlightNeighbors.incoming.has(node.id) || spotlightNeighbors.outgoing.has(node.id)) && state.scale >= 1.08);
      return {{
        id: node.id,
        label: showLabel ? node.fullLabel : "",
        title: "",
        color: {{
          background: highlighted ? node.backgroundColor : rgba(node.backgroundColor, 0.1),
          border: highlighted ? node.borderColor : rgba(node.borderColor, 0.14),
          highlight: {{ background: node.backgroundColor, border: node.borderColor }},
          hover: {{ background: node.backgroundColor, border: node.borderColor }}
        }},
        font: {{
          face: "Segoe UI",
          size: showLabel ? 13 : 1,
          color: highlighted ? "#edf4ff" : "rgba(154,168,188,0.24)",
          strokeWidth: showLabel ? 4 : 0,
          strokeColor: "rgba(17,19,23,0.94)"
        }},
        borderWidth: node.id === focusId ? 3.2 : (node.isEntrypoint ? 2.5 : 1.6),
        shadow: highlighted ? {{ enabled: true, color: rgba(node.borderColor, node.id === focusId ? 0.42 : 0.24), size: node.id === focusId ? 28 : 18, x: 0, y: 0 }} : {{ enabled: false, size: 0, x: 0, y: 0 }},
      }};
    }}));
    edgeSet.update(visibleState.edges.map((edge) => {{
      const baseColor = edge.dashes && edge.color === "#94a3b8" ? "#f59e0b" : edge.color;
      const baseAlpha = edge.width >= 4 ? 0.6 : (edge.width >= 2.6 ? 0.32 : 0.15);
      let color = rgba(baseColor, baseAlpha);
      let width = edge.width;
      const isOutgoingFocus = focusId && edge.from === focusId;
      const isIncomingFocus = focusId && edge.to === focusId;
      const isFocusedEdge = Boolean(isOutgoingFocus || isIncomingFocus);
      if (focusId) {{
        if (isOutgoingFocus) {{ color = rgba("#60a5fa", 0.98); width = Math.max(width + 1.8, 3.8); }}
        else if (isIncomingFocus) {{ color = rgba("#67e8f9", 0.98); width = Math.max(width + 1.8, 3.8); }}
        else {{ color = rgba(baseColor, 0.06); width = Math.max(0.8, width * 0.6); }}
      }}
      return {{
        id: edge.id,
        title: "",
        color: {{ color, highlight: color, hover: color }},
        width,
        shadow: isFocusedEdge ? {{ enabled: true, color: rgba("#38bdf8", 0.34), size: 18, x: 0, y: 0 }} : {{ enabled: false, size: 0, x: 0, y: 0 }},
      }};
    }}));
    descriptionEl.textContent = focusId
      ? `${{visibleView().description}} Spotlight mode highlights direct dependencies.`
      : visibleView().description;
    statsEl.textContent = `${{visibleState.nodes.length}} nodes - ${{visibleState.edges.length}} edges`;
    shell.querySelectorAll(".ecb-mode[data-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.view === state.view));
    if (focusSearch && state.search.trim()) {{
      const query = state.search.trim().toLowerCase();
      const firstMatch = visibleState.nodes.find((node) => [node.id, node.label, node.cluster, node.role].join(" ").toLowerCase().includes(query));
      if (firstMatch) {{
        network.selectNodes([firstMatch.id]);
        network.focus(firstMatch.id, {{ scale: Math.max(state.scale, 1.18), animation: {{ duration: 280, easingFunction: "easeInOutQuad" }} }});
      }}
    }} else if (focusId) {{
      network.selectNodes([focusId]);
    }} else {{
      network.unselectAll();
    }}
  }}

  function render(focusSearch = false, restartLayout = false) {{
    const view = visibleView();
    const filtered = filterView(view);
    if (state.spotlight && !filtered.nodes.some((node) => node.id === state.spotlight)) {{
      state.spotlight = null;
    }}
    if (state.hoveredNode && !filtered.nodes.some((node) => node.id === state.hoveredNode)) {{
      state.hoveredNode = null;
    }}
    const nodeIds = filtered.nodes.map((node) => node.id);
    const livePositions = currentPositions(nodeIds);
    const seededPositions = seedPositions(filtered.nodes);
    updateVisibleState(filtered.nodes, filtered.edges);
    stopDrift(true);
    const basePositions = resolveBasePositions(filtered.nodes, livePositions, seededPositions);
    visibleState.basePositions = basePositions;
    nodeSet.clear();
    edgeSet.clear();
    nodeSet.add(filtered.nodes.map((node) => {{
      const position = basePositions.get(node.id) || {{ x: 0, y: 0 }};
      return {{
        id: node.id,
        label: "",
        title: "",
        shape: node.shape,
        path: node.path,
        x: position.x,
        y: position.y,
        size: node.size,
        color: {{
          background: node.backgroundColor,
          border: node.borderColor,
          highlight: {{ background: node.backgroundColor, border: node.borderColor }},
          hover: {{ background: node.backgroundColor, border: node.borderColor }}
        }},
        font: {{
          face: "Segoe UI",
          size: 1,
          color: "#edf4ff",
          strokeWidth: 0,
          strokeColor: "rgba(17,19,23,0.94)"
        }},
        borderWidth: node.isEntrypoint ? 2.5 : 1.6,
        mass: Math.max(1, node.size / 8),
        shadow: {{ enabled: true, color: rgba(node.borderColor, 0.18), size: 14, x: 0, y: 0 }},
      }};
    }}));
    edgeSet.add(filtered.edges.map((edge) => {{
      const baseColor = edge.dashes && edge.color === "#94a3b8" ? "#f59e0b" : edge.color;
      const baseAlpha = edge.width >= 4 ? 0.6 : (edge.width >= 2.6 ? 0.32 : 0.15);
      return {{
        id: edge.id,
        from: edge.from,
        to: edge.to,
        title: "",
        arrows: "to",
        width: edge.width,
        dashes: edge.dashes,
        color: {{ color: rgba(baseColor, baseAlpha), highlight: rgba(baseColor, baseAlpha), hover: rgba(baseColor, baseAlpha) }},
        smooth: {{ type: "dynamic", roundness: 0.24 }},
        shadow: {{ enabled: false, size: 0, x: 0, y: 0 }},
      }};
    }}));
    applyInteractiveStyles(focusSearch);
    if (restartLayout) {{
      beginPhysics(nodeIds);
      window.setTimeout(() => {{
        network.fit({{ animation: {{ duration: 260, easingFunction: "easeInOutQuad" }} }});
      }}, 120);
      window.setTimeout(() => {{
        const nextScale = Math.max(0.72, network.getScale() * (1 - CANVAS_PADDING / 1250));
        network.moveTo({{ scale: nextScale, animation: {{ duration: 260, easingFunction: "easeInOutQuad" }} }});
      }}, 420);
    }} else if (!physicsActive) {{
      startDrift();
    }}
  }}

  shell.querySelectorAll(".ecb-mode[data-view]").forEach((button) => button.addEventListener("click", () => {{
    state.view = button.dataset.view;
    state.spotlight = null;
    state.hoveredNode = null;
    hideTooltip();
    render(true, true);
  }}));
  shell.querySelector(".ecb-search").addEventListener("input", (event) => {{
    state.search = event.target.value;
    state.spotlight = null;
    state.hoveredNode = null;
    hideTooltip();
    render(true, false);
  }});
  shell.querySelectorAll("input[data-filter]").forEach((input) => input.addEventListener("input", () => {{
    state.filters.hideUtilities = shell.querySelector('input[data-filter="hide-utilities"]').checked;
    state.filters.hideIsolated = shell.querySelector('input[data-filter="hide-isolated"]').checked;
    state.filters.coreOnly = shell.querySelector('input[data-filter="core-only"]').checked;
    state.filters.sideEffectsOnly = shell.querySelector('input[data-filter="side-effects-only"]').checked;
    state.filters.minImportance = Number(shell.querySelector('input[data-filter="importance"]').value);
    state.spotlight = null;
    state.hoveredNode = null;
    hideTooltip();
    render(true, false);
  }}));
  shell.querySelector('[data-export="png"]').addEventListener("click", () => {{
    const canvas = container.querySelector("canvas");
    if (!canvas) return;
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = "dependency_graph.png";
    link.click();
  }});
  network.on("click", (params) => {{
    if (params.nodes.length) {{
      state.spotlight = state.spotlight === params.nodes[0] ? null : params.nodes[0];
    }} else {{
      state.spotlight = null;
      hideTooltip();
    }}
    applyInteractiveStyles(false);
  }});
  network.on("hoverNode", (params) => {{
    state.hoveredNode = params.node;
    showTooltip(params.node, params.pointer.DOM);
    applyInteractiveStyles(false);
  }});
  network.on("blurNode", () => {{
    state.hoveredNode = null;
    hideTooltip();
    applyInteractiveStyles(false);
  }});
  network.on("mousemove", (params) => {{
    if (state.hoveredNode && params.pointer && params.pointer.DOM) {{
      placeTooltip(params.pointer.DOM);
    }}
  }});
  network.on("dragStart", (params) => {{
    state.hoveredNode = null;
    state.draggingNode = params.nodes.length ? params.nodes[0] : null;
    hideTooltip();
    beginPhysics(nodeSet.getIds());
  }});
  network.on("dragEnd", () => {{
    const draggedNodeId = state.draggingNode;
    if (draggedNodeId) {{
      persistBasePositions([draggedNodeId]);
    }}
    state.draggingNode = null;
    window.setTimeout(() => {{
      if (!physicsActive) {{
        beginPhysics(nodeSet.getIds());
      }}
    }}, DRAG_RESTABILIZE_DELAY_MS);
  }});
  network.on("zoom", (params) => {{
    state.scale = params.scale;
    applyInteractiveStyles(false);
  }});
  render(false, true);
}})();
</script>
"""

    def _build_payload(self, result: AnalysisResult, graph: nx.DiGraph, options: GraphViewOptions) -> dict[str, object]:
        file_nodes = self._build_file_nodes(result, graph)
        cycle_edges = self._cycle_edges(graph)
        return {
            "defaultView": options.mode if options.mode in self.VIEW_LABELS else "architecture",
            "views": {
                "architecture": self._architecture_view(result, graph, file_nodes, cycle_edges, options.max_nodes),
                "file": self._file_view(result, graph, file_nodes, cycle_edges, options.max_nodes, options.full),
                "entrypoint": self._entrypoint_view(result, graph, file_nodes, cycle_edges, options.max_nodes),
                "side-effects": self._side_effect_view(result, graph, file_nodes, cycle_edges, options.max_nodes),
                "risk": self._risk_view(result, graph, file_nodes, cycle_edges, options.max_nodes),
            },
        }

    def _build_file_nodes(self, result: AnalysisResult, graph: nx.DiGraph) -> dict[str, dict[str, object]]:
        hotspots = {item.path: item.coupling_score for item in result.hotspots}
        large_files = {item.path for item in result.large_files}
        issue_paths = {path for issue in result.architecture_issues for path in issue.affected_paths}
        core_paths = {item.path for item in result.core_module_rankings}
        side_effect_paths = set(result.side_effect_modules)
        dangerous_paths = set(result.dangerous_files)

        nodes: dict[str, dict[str, object]] = {}
        for path in graph.nodes:
            role = result.file_roles.get(path, "unknown")
            incoming = graph.in_degree(path)
            outgoing = graph.out_degree(path)
            coupling = hotspots.get(path, incoming + outgoing)
            centrality = result.centrality.get(path, incoming)
            importance = incoming + centrality + coupling
            side_effects = result.file_side_effects.get(path, [])
            background, border = self._node_colors(role, side_effects)
            is_core = path in core_paths
            is_entrypoint = path in result.entrypoints
            is_side_effect = path in side_effect_paths or bool(side_effects)
            risk = self._risk_level(path, importance, coupling, is_core, is_side_effect, dangerous_paths, large_files, issue_paths)
            nodes[path] = {
                "id": path,
                "path": path,
                "label": Path(path).name,
                "fullLabel": Path(path).name,
                "cluster": self._cluster_name(path, result),
                "role": role,
                "roleLabel": role,
                "shape": "dot",
                "importance": importance,
                "incoming": incoming,
                "outgoing": outgoing,
                "sideEffects": side_effects,
                "risk": risk,
                "size": round(min(42.0, 12.0 + log1p(max(importance, 1)) * 6.0 + (5.0 if is_core else 0.0) + (4.0 if is_entrypoint else 0.0)), 2),
                "backgroundColor": background,
                "borderColor": border,
                "showLabel": False,
                "isCore": is_core,
                "isEntrypoint": is_entrypoint,
                "isSideEffect": is_side_effect,
                "isIsolated": graph.degree(path) == 0,
                "title": (
                    f"<strong>File:</strong> {escape(path)}<br>"
                    f"<strong>Role:</strong> {escape(role)}<br>"
                    f"<strong>Incoming imports:</strong> {incoming}<br>"
                    f"<strong>Outgoing imports:</strong> {outgoing}<br>"
                    f"<strong>Side effects:</strong> {escape(', '.join(side_effects) if side_effects else 'none')}<br>"
                    f"<strong>Risk level:</strong> {risk}"
                ),
            }
        labeled_paths = {
            path
            for path, _ in sorted(
                ((path, int(node["importance"])) for path, node in nodes.items()),
                key=lambda item: (-item[1], item[0]),
            )[:20]
        }
        labeled_paths.update(result.entrypoints)
        labeled_paths.update(core_paths)
        for path, node in nodes.items():
            node["showLabel"] = path in labeled_paths
        return nodes

    def _architecture_view(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
        max_nodes: int,
    ) -> dict[str, object]:
        groups: dict[str, dict[str, object]] = {}
        for path, node in file_nodes.items():
            group = str(node["cluster"])
            entry = groups.setdefault(group, {"members": [], "importance": 0, "incoming": 0, "outgoing": 0, "roles": Counter(), "side_effect": False, "entrypoint": False})
            entry["members"].append(path)
            entry["importance"] += int(node["importance"])
            entry["incoming"] += int(node["incoming"])
            entry["outgoing"] += int(node["outgoing"])
            entry["roles"][str(node["role"])] += 1
            entry["side_effect"] = bool(entry["side_effect"] or node["isSideEffect"])
            entry["entrypoint"] = bool(entry["entrypoint"] or node["isEntrypoint"])

        scores = {group: int(data["importance"]) for group, data in groups.items()}
        required = {str(file_nodes[path]["cluster"]) for path in result.entrypoints if path in file_nodes}
        selected_groups = self._top_keys(scores, max_nodes, required)

        nodes = []
        for group in sorted(selected_groups, key=lambda item: (-scores[item], item)):
            data = groups[group]
            role = self._group_role(data["roles"], bool(data["entrypoint"]), bool(data["side_effect"]))
            background, border = self._node_colors(role, ["external"] if data["side_effect"] and role not in {"repository", "config", "middleware", "entrypoint"} else [])
            label = f"{group}/" if "/" not in group and len(Path(group).parts) == 1 else group
            nodes.append(
                {
                    "id": f"cluster::{group}",
                    "path": group,
                    "label": label,
                    "fullLabel": label,
                    "cluster": group,
                    "role": role,
                    "roleLabel": role,
                    "shape": "dot",
                    "importance": int(data["importance"]),
                    "incoming": int(data["incoming"]),
                    "outgoing": int(data["outgoing"]),
                    "sideEffects": ["external"] if data["side_effect"] else [],
                    "risk": "medium" if data["side_effect"] else "low",
                    "size": round(min(42.0, 14.0 + log1p(max(int(data["importance"]), 1)) * 6.0), 2),
                    "backgroundColor": background,
                    "borderColor": border,
                    "showLabel": True,
                    "isCore": False,
                    "isEntrypoint": bool(data["entrypoint"]),
                    "isSideEffect": bool(data["side_effect"]),
                    "isIsolated": False,
                    "title": (
                        f"<strong>Module:</strong> {escape(group)}<br>"
                        f"<strong>Role:</strong> {escape(role)}<br>"
                        f"<strong>Incoming imports:</strong> {data['incoming']}<br>"
                        f"<strong>Outgoing imports:</strong> {data['outgoing']}<br>"
                        f"<strong>Files:</strong> {len(data['members'])}"
                    ),
                }
            )

        selected_ids = {f"cluster::{group}" for group in selected_groups}
        edge_counter: dict[tuple[str, str], dict[str, object]] = {}
        for source, target in graph.edges:
            source_group = f"cluster::{file_nodes[source]['cluster']}"
            target_group = f"cluster::{file_nodes[target]['cluster']}"
            if source_group == target_group or source_group not in selected_ids or target_group not in selected_ids:
                continue
            entry = edge_counter.setdefault((source_group, target_group), {"count": 0, "side_effect": False, "cycle": False})
            entry["count"] += 1
            entry["side_effect"] = bool(entry["side_effect"] or file_nodes[source]["isSideEffect"] or file_nodes[target]["isSideEffect"])
            entry["cycle"] = bool(entry["cycle"] or (source, target) in cycle_edges)

        edges = [
            {
                "id": f"{source}->{target}",
                "from": source,
                "to": target,
                "width": min(6.0, 1.6 + data["count"] * 0.7),
                "color": "#dc2626" if data["side_effect"] else "#94a3b8",
                "dashes": bool(data["cycle"]),
                "title": f"Import relationships: {data['count']}",
            }
            for (source, target), data in sorted(edge_counter.items())
        ]
        return {
            "label": self.VIEW_LABELS["architecture"],
            "description": "Grouped by folders and architectural modules to explain the project shape quickly.",
            "nodes": nodes,
            "edges": edges,
        }

    def _file_view(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
        max_nodes: int,
        full: bool,
    ) -> dict[str, object]:
        required = set(result.entrypoints) | set(result.core_modules[:10]) | set(result.side_effect_modules[:10])
        selected = set(file_nodes) if full else self._top_keys({path: int(node["importance"]) for path, node in file_nodes.items()}, max_nodes, required)
        return {
            "label": self.VIEW_LABELS["file"],
            "description": "Complete file view." if full else f"Focused file-level graph showing the top {max_nodes} important files.",
            "nodes": self._file_view_nodes(selected, file_nodes),
            "edges": self._file_view_edges(selected, graph, file_nodes, cycle_edges),
        }

    def _entrypoint_view(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
        max_nodes: int,
    ) -> dict[str, object]:
        seeds = [path for path in result.entrypoints if path in file_nodes]
        selected = self._walk(graph, file_nodes, seeds, max_nodes, 4)
        if not selected:
            selected = self._top_keys({path: int(node["importance"]) for path, node in file_nodes.items()}, min(max_nodes, 20), set(result.entrypoints))
        return {
            "label": self.VIEW_LABELS["entrypoint"],
            "description": "Starts from detected entrypoints to highlight likely execution flow.",
            "nodes": self._file_view_nodes(selected, file_nodes),
            "edges": self._file_view_edges(selected, graph, file_nodes, cycle_edges),
        }

    def _side_effect_view(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
        max_nodes: int,
    ) -> dict[str, object]:
        selected = set(path for path in result.side_effect_modules if path in file_nodes)
        for path in list(selected):
            selected.update(graph.predecessors(path))
            selected.update(graph.successors(path))
        selected &= set(file_nodes)
        selected = self._top_keys({path: int(file_nodes[path]["importance"]) for path in selected}, max_nodes, set(result.side_effect_modules))
        return {
            "label": self.VIEW_LABELS["side-effects"],
            "description": "Shows modules that interact with database, network, filesystem, or cache.",
            "nodes": self._file_view_nodes(selected, file_nodes),
            "edges": self._file_view_edges(selected, graph, file_nodes, cycle_edges),
        }

    def _risk_view(
        self,
        result: AnalysisResult,
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
        max_nodes: int,
    ) -> dict[str, object]:
        risky = set(result.dangerous_files)
        risky.update(item.path for item in result.large_files)
        risky.update(item.path for item in result.hotspots)
        risky.update(path for issue in result.architecture_issues for path in issue.affected_paths)
        risky &= set(file_nodes)
        expanded = set(risky)
        for path in list(risky):
            expanded.update(graph.predecessors(path))
            expanded.update(graph.successors(path))
        expanded &= set(file_nodes)
        selected = self._top_keys({path: int(file_nodes[path]["importance"]) for path in expanded}, max_nodes, risky)
        return {
            "label": self.VIEW_LABELS["risk"],
            "description": "Highlights hotspots, large files, circular dependencies, and risky modules to modify.",
            "nodes": self._file_view_nodes(selected, file_nodes),
            "edges": self._file_view_edges(selected, graph, file_nodes, cycle_edges),
        }

    def _file_view_nodes(self, selected: set[str], file_nodes: dict[str, dict[str, object]]) -> list[dict[str, object]]:
        return [file_nodes[path] for path in sorted(selected, key=lambda item: (-int(file_nodes[item]["importance"]), item))]

    def _file_view_edges(
        self,
        selected: set[str],
        graph: nx.DiGraph,
        file_nodes: dict[str, dict[str, object]],
        cycle_edges: set[tuple[str, str]],
    ) -> list[dict[str, object]]:
        edges = []
        for source, target in graph.edges:
            if source not in selected or target not in selected:
                continue
            edges.append(
                {
                    "id": f"{source}->{target}",
                    "from": source,
                    "to": target,
                    "width": min(5.4, 1.2 + log1p(max(int(file_nodes[target]["importance"]), 1)) * 0.8),
                    "color": "#dc2626" if file_nodes[source]["isSideEffect"] or file_nodes[target]["isSideEffect"] else "#94a3b8",
                    "dashes": (source, target) in cycle_edges,
                    "title": "Import relationship",
                }
            )
        return edges

    def _cycle_edges(self, graph: nx.DiGraph) -> set[tuple[str, str]]:
        edges: set[tuple[str, str]] = set()
        for component in nx.strongly_connected_components(graph):
            if len(component) < 2:
                continue
            component_nodes = set(component)
            for source, target in graph.edges(component_nodes):
                if source in component_nodes and target in component_nodes:
                    edges.add((source, target))
        return edges

    def _walk(self, graph: nx.DiGraph, file_nodes: dict[str, dict[str, object]], seeds: list[str], limit: int, depth_limit: int) -> set[str]:
        if not seeds:
            return set()
        selected: set[str] = set()
        queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds if seed in graph)
        while queue and len(selected) < limit:
            node, depth = queue.popleft()
            if node in selected:
                continue
            selected.add(node)
            if depth >= depth_limit:
                continue
            neighbors = sorted(graph.successors(node), key=lambda item: (-int(file_nodes[item]["importance"]), item))
            for neighbor in neighbors:
                if neighbor not in selected:
                    queue.append((neighbor, depth + 1))
        return selected

    def _top_keys(self, scores: dict[str, int], limit: int, required: set[str]) -> set[str]:
        if limit <= 0:
            return set()
        required = {item for item in required if item in scores}
        selected = list(sorted(required, key=lambda item: (-scores[item], item)))[:limit]
        for item in sorted(scores, key=lambda key: (-scores[key], key)):
            if item in required:
                continue
            if len(selected) >= limit:
                break
            selected.append(item)
        return set(selected)

    def _cluster_name(self, path: str, result: AnalysisResult) -> str:
        normalized = Path(path).as_posix()
        for module in sorted(result.architecture_modules, key=len, reverse=True):
            prefix = module.rstrip("/")
            if normalized.startswith(f"{prefix}/"):
                return prefix
        parts = Path(path).parts
        if len(parts) > 1:
            return parts[0]
        return Path(path).name

    def _group_role(self, roles: Counter[str], has_entrypoint: bool, has_side_effect: bool) -> str:
        if has_entrypoint:
            return "entrypoint"
        if "repository" in roles:
            return "repository"
        if "service" in roles:
            return "service"
        if "middleware" in roles:
            return "middleware"
        if "config" in roles:
            return "config"
        if has_side_effect:
            return "job"
        return roles.most_common(1)[0][0] if roles else "utility"

    def _node_colors(self, role: str, side_effects: list[str]) -> tuple[str, str]:
        if side_effects and role not in {"entrypoint", "repository", "config", "middleware"}:
            return "#f97316", "#c2410c"
        return self.ROLE_COLORS.get(role, self.ROLE_COLORS["unknown"])

    def _risk_level(
        self,
        path: str,
        importance: int,
        coupling: int,
        is_core: bool,
        is_side_effect: bool,
        dangerous_paths: set[str],
        large_files: set[str],
        issue_paths: set[str],
    ) -> str:
        if path in dangerous_paths or path in large_files or path in issue_paths or coupling >= 10 or importance >= 14:
            return "high"
        if is_core or is_side_effect or coupling >= 5 or importance >= 7:
            return "medium"
        return "low"
