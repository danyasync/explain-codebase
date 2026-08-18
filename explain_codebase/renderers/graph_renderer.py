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
        "entrypoint": ("#56b6b2", "#7acbc7"),
        "service": ("#5b8cff", "#7da5ff"),
        "controller": ("#6f9fcd", "#8ab3d8"),
        "repository": ("#cf626c", "#df7a83"),
        "model": ("#bd7082", "#ce8797"),
        "config": ("#d0a04d", "#dfb568"),
        "middleware": ("#8878d0", "#a093df"),
        "job": ("#bf7b55", "#d1906b"),
        "component": ("#529c9b", "#70b3b1"),
        "utility": ("#737d8a", "#8b95a2"),
        "test": ("#697483", "#838e9c"),
        "unknown": ("#69727e", "#828b96"),
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
      background: #0b0d10;
      color: #f2f4f7;
    }}
    main {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      font-weight: 650;
      letter-spacing: -0.02em;
    }}
    p {{
      max-width: 880px;
      color: #8d96a5;
      line-height: 1.55;
      margin: 0 0 18px;
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
<div class="ecb-shell" id="{container_id}-shell" data-layout-mode="static" data-motion-mode="ambient" data-collision-state="idle">
  <style>
    #{container_id}-shell {{
      position: relative;
      background: #101318;
      border: 1px solid #252a32;
      border-radius: 8px;
      overflow: hidden;
      color: #f2f4f7;
    }}
    #{container_id}-shell .ecb-toolbar {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 0 16px;
      min-height: 54px;
      background: #101318;
      border-bottom: 1px solid #252a32;
    }}
    #{container_id}-shell .ecb-toolbar-primary {{
      min-width: 0;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }}
    #{container_id}-shell .ecb-group {{
      display: flex;
      gap: 4px;
      align-items: center;
    }}
    #{container_id}-shell button, #{container_id}-shell input {{
      font: inherit;
    }}
    #{container_id}-shell .ecb-mode {{
      position: relative;
      align-self: stretch;
      border: 0;
      border-radius: 0;
      padding: 0 11px;
      background: transparent;
      color: #8d96a5;
      cursor: pointer;
      transition: color 120ms ease, background-color 120ms ease;
    }}
    #{container_id}-shell .ecb-mode:hover {{
      background: #15191f;
      color: #d8dce3;
    }}
    #{container_id}-shell .ecb-mode.is-active {{
      background: transparent;
      color: #f2f4f7;
    }}
    #{container_id}-shell .ecb-mode.is-active::after {{
      content: "";
      position: absolute;
      right: 10px;
      bottom: 0;
      left: 10px;
      height: 2px;
      background: #5b8cff;
    }}
    #{container_id}-shell .ecb-search {{
      width: min(260px, 32vw);
      min-width: 190px;
      border: 1px solid #303641;
      border-radius: 6px;
      padding: 8px 10px;
      background: #0b0d10;
      color: #f2f4f7;
      outline: none;
      transition: border-color 120ms ease;
    }}
    #{container_id}-shell .ecb-search::placeholder {{
      color: #697383;
    }}
    #{container_id}-shell .ecb-search:focus {{
      border-color: #5b8cff;
    }}
    #{container_id}-shell .ecb-export {{
      min-height: 34px;
      border: 1px solid #303641;
      border-radius: 6px;
      padding: 0 11px;
      background: #15191f;
      color: #d8dce3;
      cursor: pointer;
      transition: border-color 120ms ease, background-color 120ms ease;
    }}
    #{container_id}-shell .ecb-export:hover {{
      border-color: #4a5260;
      background: #191e25;
    }}
    #{container_id}-shell .ecb-controls {{
      display: flex;
      align-items: center;
      gap: 18px;
      min-height: 46px;
      padding: 0 16px;
      overflow-x: auto;
      overflow-y: hidden;
      border-bottom: 1px solid #252a32;
      background: #0e1115;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }}
    #{container_id}-shell .ecb-controls::-webkit-scrollbar,
    #{container_id}-shell .ecb-toolbar-primary::-webkit-scrollbar {{
      display: none;
      width: 0;
      height: 0;
    }}
    #{container_id}-shell .ecb-filter {{
      display: inline-flex;
      align-items: center;
      flex: 0 0 auto;
      gap: 7px;
      color: #9aa2ae;
      font-size: 13px;
      white-space: nowrap;
    }}
    #{container_id}-shell .ecb-filter input[type="checkbox"] {{
      width: 14px;
      height: 14px;
      margin: 0;
      accent-color: #5b8cff;
    }}
    #{container_id}-shell .ecb-filter input[type="range"] {{
      width: 108px;
      accent-color: #5b8cff;
    }}
    #{container_id}-shell .ecb-meta {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 10px 16px;
      border-bottom: 1px solid #1f242b;
      color: #7f8998;
      font-size: 12px;
      line-height: 1.4;
    }}
    #{container_id}-shell .ecb-stage {{
      position: relative;
      min-height: 680px;
      background: #101318;
    }}
    #{container_id} {{
      height: 680px;
      background: #101318;
    }}
    #{container_id}-shell .ecb-legend {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 22px;
      min-height: 42px;
      padding: 8px 16px;
      border-top: 1px solid #252a32;
      background: #0e1115;
    }}
    #{container_id}-shell .ecb-legend-item {{
      display: flex;
      align-items: center;
      gap: 7px;
      color: #8d96a5;
      font-size: 12px;
      white-space: nowrap;
    }}
    #{container_id}-shell .ecb-swatch {{
      width: 9px;
      height: 9px;
      border-radius: 50%;
      flex: 0 0 auto;
    }}
    #{container_id}-shell .ecb-note {{
      margin-left: auto;
      color: #697383;
      font-size: 12px;
    }}
    #{container_id}-shell .vis-network:focus {{
      outline: none;
    }}
    #{container_id}-shell .ecb-tooltip {{
      position: absolute;
      left: 0;
      top: 0;
      width: 300px;
      padding: 13px 14px;
      border: 1px solid #303641;
      border-radius: 6px;
      background: #15191f;
      color: #f2f4f7;
      font-size: 13px;
      line-height: 1.55;
      opacity: 0;
      pointer-events: none;
      transform: translate3d(-9999px, -9999px, 0);
      transition: opacity 80ms ease;
      z-index: 7;
    }}
    #{container_id}-shell .ecb-tooltip.is-visible {{
      opacity: 1;
    }}
    #{container_id}-shell .ecb-tooltip-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #76808e;
      margin-bottom: 4px;
    }}
    #{container_id}-shell .ecb-tooltip-value {{
      color: #f2f4f7;
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
      padding: 3px 7px;
      border-radius: 4px;
      background: #20252d;
      color: #c7cdd6;
      font-size: 12px;
      margin: 2px 4px 0 0;
    }}
    #{container_id}-shell .ecb-tooltip-meta {{
      color: #cbd1da;
    }}
    #{container_id}-shell .vis-tooltip {{
      display: none !important;
    }}
    #{container_id}-shell button:focus-visible,
    #{container_id}-shell input:focus-visible {{
      outline: 2px solid #5b8cff;
      outline-offset: 2px;
    }}
    @media (max-width: 980px) {{
      #{container_id}-shell .ecb-toolbar {{
        align-items: stretch;
        padding: 0 10px 10px;
      }}
      #{container_id}-shell .ecb-toolbar-primary {{
        width: 100%;
        min-height: 48px;
        overflow-x: auto;
      }}
      #{container_id}-shell .ecb-toolbar-primary .ecb-group {{
        height: 48px;
        width: max-content;
      }}
      #{container_id}-shell .ecb-search {{
        flex: 1 1 180px;
        width: auto;
      }}
      #{container_id}-shell .ecb-controls {{
        padding: 0 10px;
      }}
      #{container_id}-shell .ecb-meta {{
        padding: 9px 10px;
      }}
      #{container_id}-shell .ecb-stage,
      #{container_id} {{
        min-height: 600px;
        height: 600px;
      }}
      #{container_id}-shell .ecb-legend {{
        padding: 9px 10px;
      }}
    }}
    @media (max-width: 560px) {{
      #{container_id}-shell {{
        border-radius: 6px;
      }}
      #{container_id}-shell .ecb-meta {{
        display: block;
      }}
      #{container_id}-shell .ecb-meta [data-stats] {{
        margin-top: 3px;
      }}
      #{container_id}-shell .ecb-stage,
      #{container_id} {{
        min-height: 520px;
        height: 62vh;
      }}
      #{container_id}-shell .ecb-note {{
        width: 100%;
        margin-left: 0;
      }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      #{container_id}-shell * {{
        transition-duration: 0.01ms !important;
      }}
    }}
  </style>

  <div class="ecb-toolbar" aria-label="Graph controls">
    <div class="ecb-toolbar-primary">
      <div class="ecb-group" role="tablist" aria-label="Graph view">
        <button class="ecb-mode" data-view="architecture" role="tab">Architecture</button>
        <button class="ecb-mode" data-view="file" role="tab">Files</button>
        <button class="ecb-mode" data-view="entrypoint" role="tab">Entrypoint flow</button>
        <button class="ecb-mode" data-view="side-effects" role="tab">Side effects</button>
        <button class="ecb-mode" data-view="risk" role="tab">Risk</button>
      </div>
    </div>
    <div class="ecb-group">
      <input class="ecb-search" type="search" placeholder="Search files" aria-label="Search files" autocomplete="off" spellcheck="false">
      <button class="ecb-export" data-export="png" type="button">Export PNG</button>
    </div>
  </div>

  <div class="ecb-controls" aria-label="Graph filters">
    <label class="ecb-filter"><input type="checkbox" data-filter="hide-utilities"> Hide utilities</label>
    <label class="ecb-filter"><input type="checkbox" data-filter="hide-isolated"> Hide isolated nodes</label>
    <label class="ecb-filter"><input type="checkbox" data-filter="core-only"> Core modules only</label>
    <label class="ecb-filter"><input type="checkbox" data-filter="side-effects-only"> Side effects only</label>
    <label class="ecb-filter">Minimum importance <input type="range" min="0" max="30" value="0" data-filter="importance"></label>
  </div>

  <div class="ecb-meta">
    <div data-description></div>
    <div data-stats aria-live="polite"></div>
  </div>

  <div class="ecb-stage">
    <div id="{container_id}"></div>
    <div class="ecb-tooltip" data-tooltip aria-hidden="true" hidden></div>
  </div>
  <div class="ecb-legend" aria-label="Legend: node roles">
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#56b6b2"></span>Entrypoint</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#5b8cff"></span>Service</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#cf626c"></span>Repository / DB</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#d0a04d"></span>Config</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#8878d0"></span>Middleware</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#bf7b55"></span>External integration</div>
    <div class="ecb-legend-item"><span class="ecb-swatch" style="background:#737d8a"></span>Utility</div>
    <div class="ecb-note">Node size = importance · Edge = import relationship</div>
  </div>
</div>
<script src="{VIS_NETWORK_URL}" integrity="{VIS_NETWORK_SRI}" crossorigin="anonymous" referrerpolicy="no-referrer"{nonce_attribute}></script>
<script{nonce_attribute}>
(function() {{
  const payload = {payload_json};
  const shell = document.getElementById("{container_id}-shell");
  const container = document.getElementById("{container_id}");
  if (typeof vis === "undefined") {{
    container.innerHTML = '<div style="padding:32px;color:#8d96a5">Graph library could not be loaded in this browser.</div>';
    return;
  }}

  const state = {{
    view: payload.defaultView,
    search: "",
    spotlight: null,
    hoveredNode: null,
    draggingNode: null,
    filters: {{ hideUtilities: false, hideIsolated: false, coreOnly: false, sideEffectsOnly: false, minImportance: 0 }},
  }};
  let searchTimer = null;
  let tooltipFrame = null;
  let filterFrame = null;
  let ambientFrame = null;
  let ambientTimestamp = performance.now();
  let lastAmbientPaint = 0;
  let collisionFrame = null;
  let collisionTargets = null;
  let collisionView = null;
  let dragOrigin = null;
  let graphInViewport = true;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const COLLISION_PADDING = 18;
  const MAX_COLLISION_NODES = 16;
  const MAX_COLLISION_DISPLACEMENT = 260;
  const COLLISION_DURATION_MS = 180;
  const descriptionEl = shell.querySelector("[data-description]");
  const statsEl = shell.querySelector("[data-stats]");
  const tooltipEl = shell.querySelector("[data-tooltip]");
  const nodeSet = new vis.DataSet([]);
  const edgeSet = new vis.DataSet([]);
  const layoutCache = new Map();
  const visibleState = {{
    nodes: [],
    edges: [],
    nodeMap: new Map(),
  }};
  const network = new vis.Network(container, {{ nodes: nodeSet, edges: edgeSet }}, {{
    layout: {{ improvedLayout: false, randomSeed: 17 }},
    interaction: {{
      hover: true,
      hoverConnectedEdges: false,
      navigationButtons: false,
      keyboard: true,
      tooltipDelay: 80,
      zoomView: true,
      dragView: true,
      dragNodes: true,
      hideEdgesOnDrag: false,
      selectConnectedEdges: false
    }},
    physics: {{ enabled: false }},
    nodes: {{
      borderWidth: 1.5,
      borderWidthSelected: 2,
      labelHighlightBold: false,
      chosen: false,
      font: {{ face: "Segoe UI", size: 13, color: "#d8dce3", strokeWidth: 2, strokeColor: "#101318" }}
    }},
    edges: {{
      arrows: {{ to: {{ enabled: true, scaleFactor: 0.38 }} }},
      smooth: {{ enabled: true, type: "curvedCW", roundness: 0.08 }},
      selectionWidth: 0,
      hoverWidth: 0,
      chosen: false
    }}
  }});

  function rgba(hex, alpha) {{
    const clean = (hex || "#68717e").replace("#", "");
    const normalized = clean.length === 3 ? clean.split("").map((p) => p + p).join("") : clean;
    const n = parseInt(normalized, 16);
    return `rgba(${{(n >> 16) & 255}}, ${{(n >> 8) & 255}}, ${{n & 255}}, ${{alpha}})`;
  }}

  function visibleView() {{
    return payload.views[state.view] || payload.views.architecture;
  }}

  function activeFocusId() {{
    return state.spotlight;
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
    const orderedClusters = Array.from(clusters.entries())
      .map(([name, members]) => [name, members.slice().sort((left, right) => right.importance - left.importance || left.id.localeCompare(right.id))])
      .sort((left, right) => right[1].length - left[1].length || left[0].localeCompare(right[0]));
    const positions = new Map();

    function clusterExtent(memberCount) {{
      if (memberCount <= 1) return 0;
      let remaining = memberCount - 1;
      let ring = 0;
      while (remaining > 0) {{
        ring += 1;
        remaining -= 8 + ((ring - 1) * 6);
      }}
      return ring * 140;
    }}

    function placeCluster(clusterName, members, centerX, centerY) {{
      if (!members.length) return;
      positions.set(members[0].id, {{ x: centerX, y: centerY }});
      let memberIndex = 1;
      let ring = 1;
      const phase = (clusterName.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 24) * (Math.PI / 96);
      while (memberIndex < members.length) {{
        const capacity = 8 + ((ring - 1) * 6);
        const ringCount = Math.min(capacity, members.length - memberIndex);
        const radius = ring * 140;
        for (let ringIndex = 0; ringIndex < ringCount; ringIndex += 1) {{
          const node = members[memberIndex + ringIndex];
          const angle = phase + (ringIndex / ringCount) * Math.PI * 2;
          positions.set(node.id, {{
            x: centerX + Math.cos(angle) * radius,
            y: centerY + Math.sin(angle) * radius,
          }});
        }}
        memberIndex += ringCount;
        ring += 1;
      }}
    }}

    if (!orderedClusters.length) return positions;
    const totalNodes = nodes.length;
    const centralCluster = orderedClusters[0];
    const useCentralCluster = orderedClusters.length === 1
      || (centralCluster[1].length >= 3 && centralCluster[1].length >= Math.ceil(totalNodes * 0.36));
    const outerClusters = useCentralCluster ? orderedClusters.slice(1) : orderedClusters;
    const centralExtent = useCentralCluster ? clusterExtent(centralCluster[1].length) : 0;
    if (useCentralCluster) placeCluster(centralCluster[0], centralCluster[1], 0, 0);
    if (outerClusters.length) {{
      const outerExtent = Math.max(...outerClusters.map(([, members]) => clusterExtent(members.length)));
      const minimumOrbit = totalNodes <= 5 ? 180 : 260;
      const orbitRadius = centralExtent + outerExtent + Math.max(minimumOrbit, outerClusters.length * 60);
      outerClusters.forEach(([clusterName, members], clusterIndex) => {{
        const angle = (clusterIndex / outerClusters.length) * Math.PI * 2;
        const centerX = Math.cos(angle) * orbitRadius;
        const centerY = Math.sin(angle) * orbitRadius * 0.55;
        placeCluster(clusterName, members, centerX, centerY);
      }});
    }}
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
    if (tooltipFrame) window.cancelAnimationFrame(tooltipFrame);
    tooltipFrame = window.requestAnimationFrame(() => {{
      tooltipFrame = null;
      if (state.hoveredNode === nodeId && !tooltipEl.hidden) {{
        tooltipEl.classList.add("is-visible");
      }}
    }});
  }}

  function hideTooltip() {{
    if (tooltipFrame) {{
      window.cancelAnimationFrame(tooltipFrame);
      tooltipFrame = null;
    }}
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

  function positionsForView(viewName, view) {{
    if (!layoutCache.has(viewName)) {{
      layoutCache.set(viewName, seedPositions(view.nodes));
    }}
    return layoutCache.get(viewName);
  }}

  function syncPositionSignature() {{
    const positions = currentPositions(nodeSet.getIds());
    let hash = 2166136261;
    Object.keys(positions).sort().forEach((id) => {{
      const position = positions[id];
      const token = `${{id}}:${{Math.round(position.x * 10)}}:${{Math.round(position.y * 10)}}`;
      for (let index = 0; index < token.length; index += 1) {{
        hash ^= token.charCodeAt(index);
        hash = Math.imul(hash, 16777619);
      }}
    }});
    shell.dataset.positionSignature = `${{Object.keys(positions).length}}:${{hash >>> 0}}`;
  }}

  function hashText(value) {{
    let hash = 2166136261;
    const text = String(value);
    for (let index = 0; index < text.length; index += 1) {{
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }}
    return hash >>> 0;
  }}

  function curveDetails(edge) {{
    const hash = hashText(edge.id);
    return {{
      direction: hash % 2 === 0 ? 1 : -1,
      roundness: 0.065 + ((hash % 4) * 0.012),
    }};
  }}

  function nodePosition(nodeId) {{
    const bodyNode = network.body && network.body.nodes ? network.body.nodes[nodeId] : null;
    if (!bodyNode || !Number.isFinite(bodyNode.x) || !Number.isFinite(bodyNode.y)) return null;
    return {{ x: bodyNode.x, y: bodyNode.y }};
  }}

  function drawNodeBreathing(context) {{
    if (reducedMotion.matches || visibleState.nodes.length > 180) return;
    const scale = Math.max(network.getScale(), 0.2);
    context.save();
    context.lineWidth = 1 / scale;
    visibleState.nodes.forEach((node) => {{
      const position = nodePosition(node.id);
      if (!position) return;
      const phase = (hashText(node.id) % 628) / 100;
      const pulse = (Math.sin((ambientTimestamp / 1250) + phase) + 1) / 2;
      const radius = node.size * (1.035 + pulse * 0.045);
      context.beginPath();
      context.arc(position.x, position.y, radius, 0, Math.PI * 2);
      context.strokeStyle = rgba(node.borderColor, 0.16 + pulse * 0.1);
      context.stroke();
    }});
    context.restore();
  }}

  function drawEdgeFlow(context) {{
    if (reducedMotion.matches || visibleState.edges.length > 360) return;
    const focusId = activeFocusId();
    const scale = Math.max(network.getScale(), 0.2);
    let drawn = 0;
    const maxAmbientEdges = focusId ? 120 : 64;
    context.save();
    visibleState.edges.forEach((edge) => {{
      const focused = focusId && (edge.from === focusId || edge.to === focusId);
      if (focusId && !focused) return;
      if (drawn >= maxAmbientEdges) return;
      const phase = (hashText(edge.id) % 1000) / 1000;
      const progress = ((ambientTimestamp / 2600) + phase) % 1;
      const flowAlpha = Math.pow(Math.sin(Math.PI * progress), 1.4);
      const t = 0.08 + progress * 0.84;
      const bodyEdge = network.body && network.body.edges ? network.body.edges[edge.id] : null;
      const edgePath = bodyEdge && bodyEdge.edgeType;
      let point = null;
      if (edgePath && typeof edgePath.getPoint === "function") {{
        try {{
          point = edgePath.getPoint(t);
        }} catch (error) {{
          point = null;
        }}
      }}
      if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) {{
        const source = nodePosition(edge.from);
        const target = nodePosition(edge.to);
        if (!source || !target) return;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const distance = Math.max(Math.hypot(dx, dy), 1);
        const curve = curveDetails(edge);
        const bend = Math.min(96, distance * curve.roundness) * curve.direction;
        const controlX = (source.x + target.x) / 2 - (dy / distance) * bend;
        const controlY = (source.y + target.y) / 2 + (dx / distance) * bend;
        const inverse = 1 - t;
        point = {{
          x: (inverse * inverse * source.x) + (2 * inverse * t * controlX) + (t * t * target.x),
          y: (inverse * inverse * source.y) + (2 * inverse * t * controlY) + (t * t * target.y),
        }};
      }}
      const baseColor = focused ? (edge.from === focusId ? "#5b8cff" : "#56b6b2") : edge.color;
      context.beginPath();
      context.arc(point.x, point.y, (focused ? 2.1 : 1.35) / scale, 0, Math.PI * 2);
      context.fillStyle = rgba(baseColor, (focused ? 0.9 : 0.52) * flowAlpha);
      context.fill();
      drawn += 1;
    }});
    context.restore();
  }}

  function startAmbientAnimation() {{
    if (
      ambientFrame
      || document.hidden
      || reducedMotion.matches
      || !graphInViewport
      || state.draggingNode
      || collisionTargets
      || visibleState.nodes.length > 180
      || visibleState.edges.length > 360
    ) return;
    const animate = (timestamp) => {{
      if (document.hidden || reducedMotion.matches || !graphInViewport || state.draggingNode || collisionTargets) {{
        ambientFrame = null;
        return;
      }}
      if (visibleState.nodes.length > 180 || visibleState.edges.length > 360) {{
        ambientFrame = null;
        return;
      }}
      const interval = visibleState.nodes.length > 100 || visibleState.edges.length > 220 ? 66 : 33;
      if (timestamp - lastAmbientPaint >= interval) {{
        ambientTimestamp = timestamp;
        lastAmbientPaint = timestamp;
        network.redraw();
      }}
      ambientFrame = window.requestAnimationFrame(animate);
    }};
    ambientFrame = window.requestAnimationFrame(animate);
  }}

  function setNodePosition(nodeId, position) {{
    const bodyNode = network.body && network.body.nodes ? network.body.nodes[nodeId] : null;
    if (!bodyNode) return;
    bodyNode.x = position.x;
    bodyNode.y = position.y;
  }}

  function persistLayoutPositions(positionMap, viewName = state.view) {{
    const view = payload.views[viewName] || visibleView();
    const cachedPositions = positionsForView(viewName, view);
    const updates = [];
    positionMap.forEach((position, nodeId) => {{
      cachedPositions.set(nodeId, {{ x: position.x, y: position.y }});
      if (viewName === state.view && nodeSet.get(nodeId)) {{
        updates.push({{ id: nodeId, x: position.x, y: position.y }});
      }}
    }});
    if (updates.length) nodeSet.update(updates);
  }}

  function localCollisionTargets(draggedNodeId, fallbackPosition) {{
    const view = visibleView();
    const nodeMap = new Map(view.nodes.map((node) => [node.id, node]));
    const cachedPositions = positionsForView(state.view, view);
    const livePositions = currentPositions(nodeSet.getIds());
    const targets = new Map();
    view.nodes.forEach((node) => {{
      const position = livePositions[node.id] || cachedPositions.get(node.id) || {{ x: 0, y: 0 }};
      targets.set(node.id, {{ x: position.x, y: position.y }});
    }});
    const originals = new Map(Array.from(targets, ([nodeId, position]) => [nodeId, {{ x: position.x, y: position.y }}]));
    const nodeIds = Array.from(targets.keys()).sort();
    const maximumRadius = Math.max(1, ...view.nodes.map((node) => Number(node.size) || 1));
    const cellSize = Math.max(96, maximumRadius * 2 + COLLISION_PADDING);
    const cells = new Map();
    const affected = new Set([draggedNodeId]);
    const queue = [draggedNodeId];
    const pending = new Set(queue);
    let overflow = false;
    let processed = 0;

    function cellCoordinates(position) {{
      return {{ x: Math.floor(position.x / cellSize), y: Math.floor(position.y / cellSize) }};
    }}

    function cellKey(position) {{
      const coordinates = cellCoordinates(position);
      return `${{coordinates.x}}:${{coordinates.y}}`;
    }}

    function addToCell(nodeId, position) {{
      const key = cellKey(position);
      if (!cells.has(key)) cells.set(key, new Set());
      cells.get(key).add(nodeId);
    }}

    function removeFromCell(nodeId, position) {{
      const key = cellKey(position);
      const bucket = cells.get(key);
      if (!bucket) return;
      bucket.delete(nodeId);
      if (!bucket.size) cells.delete(key);
    }}

    function nearbyNodeIds(position) {{
      const coordinates = cellCoordinates(position);
      const nearby = new Set();
      for (let offsetX = -1; offsetX <= 1; offsetX += 1) {{
        for (let offsetY = -1; offsetY <= 1; offsetY += 1) {{
          const bucket = cells.get(`${{coordinates.x + offsetX}}:${{coordinates.y + offsetY}}`);
          if (bucket) bucket.forEach((nodeId) => nearby.add(nodeId));
        }}
      }}
      return Array.from(nearby).sort();
    }}

    function moveTarget(nodeId, position) {{
      const previous = targets.get(nodeId);
      const original = originals.get(nodeId);
      if (!previous || !original || nodeId === draggedNodeId) return false;
      if (!affected.has(nodeId) && affected.size >= MAX_COLLISION_NODES) return false;
      if (Math.hypot(position.x - original.x, position.y - original.y) > MAX_COLLISION_DISPLACEMENT) return false;
      removeFromCell(nodeId, previous);
      targets.set(nodeId, position);
      addToCell(nodeId, position);
      affected.add(nodeId);
      if (!pending.has(nodeId)) {{
        queue.push(nodeId);
        pending.add(nodeId);
      }}
      return true;
    }}

    nodeIds.forEach((nodeId) => addToCell(nodeId, targets.get(nodeId)));
    while (queue.length && processed < MAX_COLLISION_NODES * 8) {{
      const currentId = queue.shift();
      pending.delete(currentId);
      processed += 1;
      const current = targets.get(currentId);
      const currentNode = nodeMap.get(currentId);
      if (!current || !currentNode) continue;
      const candidates = nearbyNodeIds(current);
      for (const otherId of candidates) {{
        if (otherId === currentId) continue;
        const other = targets.get(otherId);
        const otherNode = nodeMap.get(otherId);
        if (!other || !otherNode) continue;
        const anchorId = otherId === draggedNodeId ? otherId : currentId;
        const moverId = otherId === draggedNodeId ? currentId : otherId;
        if (moverId === draggedNodeId) continue;
        const anchor = targets.get(anchorId);
        const mover = targets.get(moverId);
        const anchorNode = nodeMap.get(anchorId);
        const moverNode = nodeMap.get(moverId);
        if (!anchor || !mover || !anchorNode || !moverNode) continue;
        let dx = mover.x - anchor.x;
        let dy = mover.y - anchor.y;
        let distance = Math.hypot(dx, dy);
        const minimumDistance = anchorNode.size + moverNode.size + COLLISION_PADDING;
        if (distance >= minimumDistance) continue;
        if (distance < 0.001) {{
          const angle = (hashText(`${{anchorId}}|${{moverId}}`) % 628) / 100;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }}
        const overlap = minimumDistance - distance + 0.5;
        const nextPosition = {{
          x: mover.x + (dx / distance) * overlap,
          y: mover.y + (dy / distance) * overlap,
        }};
        if (!moveTarget(moverId, nextPosition)) overflow = true;
      }}
    }}
    if (queue.length) overflow = true;

    affected.forEach((nodeId) => {{
      if (overflow) return;
      const position = targets.get(nodeId);
      const node = nodeMap.get(nodeId);
      if (!position || !node) return;
      for (const otherId of nearbyNodeIds(position)) {{
        if (otherId === nodeId) continue;
        const other = targets.get(otherId);
        const otherNode = nodeMap.get(otherId);
        if (!other || !otherNode) continue;
        if (Math.hypot(other.x - position.x, other.y - position.y) < node.size + otherNode.size + COLLISION_PADDING - 0.5) {{
          overflow = true;
          break;
        }}
      }}
    }});

    if (overflow) {{
      const draggedNode = nodeMap.get(draggedNodeId);
      const droppedPosition = originals.get(draggedNodeId);
      if (fallbackPosition) {{
        return new Map([[draggedNodeId, fallbackPosition]]);
      }}
      const otherIds = nodeIds.filter((nodeId) => nodeId !== draggedNodeId);
      const isAvailable = (candidate) => otherIds.every((nodeId) => {{
        const other = originals.get(nodeId);
        const otherNode = nodeMap.get(nodeId);
        return !other || !otherNode || Math.hypot(other.x - candidate.x, other.y - candidate.y) >= draggedNode.size + otherNode.size + COLLISION_PADDING;
      }});
      if (draggedNode && droppedPosition) {{
        const ringStep = Math.max(28, draggedNode.size * 0.8);
        const phase = (hashText(draggedNodeId) % 628) / 100;
        for (let ring = 1; ring <= 16; ring += 1) {{
          const samples = 12 + ring * 4;
          for (let sample = 0; sample < samples; sample += 1) {{
            const angle = phase + (sample / samples) * Math.PI * 2;
            const candidate = {{
              x: droppedPosition.x + Math.cos(angle) * ring * ringStep,
              y: droppedPosition.y + Math.sin(angle) * ring * ringStep,
            }};
            if (isAvailable(candidate)) return new Map([[draggedNodeId, candidate]]);
          }}
        }}
      }}
      return new Map([[draggedNodeId, droppedPosition || {{ x: 0, y: 0 }}]]);
    }}

    const changedTargets = new Map();
    affected.forEach((nodeId) => {{
      const target = targets.get(nodeId);
      if (target) changedTargets.set(nodeId, target);
    }});
    return changedTargets;
  }}

  function finishCollisionResolution() {{
    if (!collisionTargets || !collisionView) return;
    if (collisionFrame) window.cancelAnimationFrame(collisionFrame);
    if (collisionView === state.view) {{
      collisionTargets.forEach((position, nodeId) => setNodePosition(nodeId, position));
    }}
    persistLayoutPositions(collisionTargets, collisionView);
    collisionFrame = null;
    collisionTargets = null;
    collisionView = null;
    shell.dataset.collisionState = "idle";
    network.redraw();
    syncPositionSignature();
    startAmbientAnimation();
  }}

  function animateCollisionResolution(targets) {{
    if (!targets.size) return;
    const starts = currentPositions(Array.from(targets.keys()));
    const startedAt = performance.now();
    collisionTargets = targets;
    collisionView = state.view;
    shell.dataset.collisionState = "settling";

    if (reducedMotion.matches) {{
      finishCollisionResolution();
      return;
    }}

    const step = (timestamp) => {{
      const progress = Math.min(1, (timestamp - startedAt) / COLLISION_DURATION_MS);
      const eased = 1 - Math.pow(1 - progress, 3);
      targets.forEach((target, nodeId) => {{
        const start = starts[nodeId] || target;
        setNodePosition(nodeId, {{
          x: start.x + (target.x - start.x) * eased,
          y: start.y + (target.y - start.y) * eased,
        }});
      }});
      network.redraw();
      if (progress < 1) {{
        collisionFrame = window.requestAnimationFrame(step);
      }} else {{
        finishCollisionResolution();
      }}
    }};
    collisionFrame = window.requestAnimationFrame(step);
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
    return {{ nodes, edges }};
  }}

  function applyInteractiveStyles(selectSearchMatch = false) {{
    if (selectSearchMatch && state.search.trim()) {{
      const query = state.search.trim().toLowerCase();
      const firstMatch = visibleState.nodes.find((node) =>
        [node.id, node.label, node.cluster, node.role].join(" ").toLowerCase().includes(query)
      );
      state.spotlight = firstMatch ? firstMatch.id : null;
    }}
    const focusId = activeFocusId();
    const spotlightNeighbors = focusId ? neighbors(focusId, visibleState.edges) : {{ incoming: new Set(), outgoing: new Set() }};
    nodeSet.update(visibleState.nodes.map((node) => {{
      const highlighted = !focusId || node.id === focusId || spotlightNeighbors.incoming.has(node.id) || spotlightNeighbors.outgoing.has(node.id);
      const showLabel = node.showLabel || node.id === focusId;
      const baseBorder = node.isEntrypoint ? node.borderColor : rgba(node.borderColor, 0.86);
      return {{
        id: node.id,
        label: showLabel ? node.fullLabel : "",
        title: "",
        color: {{
          background: highlighted ? node.backgroundColor : rgba(node.backgroundColor, 0.14),
          border: node.id === focusId ? "#9bb5ff" : (highlighted ? baseBorder : rgba(node.borderColor, 0.18)),
          highlight: {{ background: node.backgroundColor, border: "#9bb5ff" }},
          hover: {{ background: node.backgroundColor, border: baseBorder }}
        }},
        font: {{
          face: "Segoe UI",
          size: showLabel ? 13 : 1,
          color: highlighted ? "#d8dce3" : "rgba(141,150,165,0.28)",
          strokeWidth: showLabel ? 2 : 0,
          strokeColor: "#101318"
        }},
        borderWidth: node.isEntrypoint ? 2 : 1.5,
        shadow: false,
      }};
    }}));
    edgeSet.update(visibleState.edges.map((edge) => {{
      const baseColor = edge.dashes && edge.color === "#68717e" ? "#d0a04d" : edge.color;
      const baseAlpha = edge.width >= 4 ? 0.52 : (edge.width >= 2.6 ? 0.28 : 0.14);
      let color = rgba(baseColor, baseAlpha);
      const isOutgoingFocus = focusId && edge.from === focusId;
      const isIncomingFocus = focusId && edge.to === focusId;
      if (focusId) {{
        if (isOutgoingFocus) color = rgba("#5b8cff", 0.92);
        else if (isIncomingFocus) color = rgba("#56b6b2", 0.92);
        else color = rgba(baseColor, 0.05);
      }}
      return {{
        id: edge.id,
        title: "",
        color: {{ color, highlight: color, hover: color }},
        width: edge.width,
        shadow: false,
      }};
    }}));
    const emptySearch = Boolean(state.search.trim()) && visibleState.nodes.length === 0;
    descriptionEl.textContent = emptySearch
      ? "No matching files."
      : focusId
        ? `${{visibleView().description}} Direct dependencies are highlighted.`
        : visibleView().description;
    statsEl.textContent = `${{visibleState.nodes.length}} nodes - ${{visibleState.edges.length}} edges`;
    shell.querySelectorAll(".ecb-mode[data-view]").forEach((button) => {{
      const active = button.dataset.view === state.view;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    }});
    if (focusId) {{
      network.selectNodes([focusId]);
    }} else {{
      network.unselectAll();
    }}
  }}

  function replaceItems(dataSet, items) {{
    const nextIds = new Set(items.map((item) => item.id));
    const removedIds = dataSet.getIds().filter((id) => !nextIds.has(id));
    if (removedIds.length) dataSet.remove(removedIds);
    if (items.length) dataSet.update(items);
  }}

  function render(selectSearchMatch = false, fitView = false) {{
    if (collisionTargets) finishCollisionResolution();
    const view = visibleView();
    const filtered = filterView(view);
    if (state.spotlight && !filtered.nodes.some((node) => node.id === state.spotlight)) {{
      state.spotlight = null;
    }}
    if (state.hoveredNode && !filtered.nodes.some((node) => node.id === state.hoveredNode)) {{
      state.hoveredNode = null;
    }}
    updateVisibleState(filtered.nodes, filtered.edges);
    const positions = positionsForView(state.view, view);
    replaceItems(nodeSet, filtered.nodes.map((node) => {{
      const position = positions.get(node.id) || {{ x: 0, y: 0 }};
      return {{
        id: node.id,
        label: "",
        title: "",
        shape: node.shape,
        path: node.path,
        x: position.x,
        y: position.y,
        fixed: {{ x: false, y: false }},
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
          color: "#d8dce3",
          strokeWidth: 0,
          strokeColor: "#101318"
        }},
        borderWidth: node.isEntrypoint ? 2 : 1.5,
        chosen: false,
        shadow: false,
      }};
    }}));
    replaceItems(edgeSet, filtered.edges.map((edge) => {{
      const baseColor = edge.dashes && edge.color === "#68717e" ? "#d0a04d" : edge.color;
      const baseAlpha = edge.width >= 4 ? 0.52 : (edge.width >= 2.6 ? 0.28 : 0.14);
      const curve = curveDetails(edge);
      return {{
        id: edge.id,
        from: edge.from,
        to: edge.to,
        title: "",
        arrows: "to",
        width: edge.width,
        dashes: edge.dashes,
        color: {{ color: rgba(baseColor, baseAlpha), highlight: rgba(baseColor, baseAlpha), hover: rgba(baseColor, baseAlpha) }},
        smooth: {{
          enabled: true,
          type: curve.direction > 0 ? "curvedCW" : "curvedCCW",
          roundness: curve.roundness,
        }},
        chosen: false,
        shadow: false,
      }};
    }}));
    applyInteractiveStyles(selectSearchMatch);
    if (fitView && filtered.nodes.length) {{
      network.fit({{ nodes: filtered.nodes.map((node) => node.id), animation: false }});
    }}
    syncPositionSignature();
    startAmbientAnimation();
  }}

  shell.querySelectorAll(".ecb-mode[data-view]").forEach((button) => button.addEventListener("click", () => {{
    state.view = button.dataset.view;
    state.spotlight = null;
    state.hoveredNode = null;
    hideTooltip();
    render(false, true);
  }}));
  shell.querySelector(".ecb-search").addEventListener("input", (event) => {{
    state.search = event.target.value;
    state.spotlight = null;
    state.hoveredNode = null;
    hideTooltip();
    if (searchTimer) window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => render(true, false), 90);
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
    if (filterFrame) window.cancelAnimationFrame(filterFrame);
    filterFrame = window.requestAnimationFrame(() => {{
      filterFrame = null;
      render(false, false);
    }});
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
    syncPositionSignature();
  }});
  network.on("hoverNode", (params) => {{
    state.hoveredNode = params.node;
    container.style.cursor = "grab";
    showTooltip(params.node, params.pointer.DOM);
  }});
  network.on("blurNode", () => {{
    state.hoveredNode = null;
    if (!state.draggingNode) container.style.cursor = "default";
    hideTooltip();
  }});
  network.on("mousemove", (params) => {{
    if (state.hoveredNode && params.pointer && params.pointer.DOM) {{
      placeTooltip(params.pointer.DOM);
    }}
  }});
  network.on("dragStart", (params) => {{
    if (!params.nodes.length) return;
    if (collisionTargets) finishCollisionResolution();
    if (ambientFrame) {{
      window.cancelAnimationFrame(ambientFrame);
      ambientFrame = null;
    }}
    state.draggingNode = params.nodes[0];
    dragOrigin = currentPositions([state.draggingNode])[state.draggingNode] || null;
    state.hoveredNode = null;
    container.style.cursor = "grabbing";
    hideTooltip();
  }});
  network.on("dragEnd", (params) => {{
    const draggedNodeId = state.draggingNode || params.nodes[0];
    state.draggingNode = null;
    container.style.cursor = "default";
    if (!draggedNodeId || !dragOrigin) {{
      dragOrigin = null;
      startAmbientAnimation();
      return;
    }}
    const droppedPosition = currentPositions([draggedNodeId])[draggedNodeId];
    const movementThreshold = 5 / Math.max(network.getScale(), 0.2);
    const movedDistance = droppedPosition
      ? Math.hypot(droppedPosition.x - dragOrigin.x, droppedPosition.y - dragOrigin.y)
      : 0;
    if (!droppedPosition || movedDistance < movementThreshold) {{
      const original = new Map([[draggedNodeId, dragOrigin]]);
      original.forEach((position, nodeId) => setNodePosition(nodeId, position));
      persistLayoutPositions(original);
      network.redraw();
      syncPositionSignature();
      startAmbientAnimation();
      dragOrigin = null;
      return;
    }}
    const fallbackPosition = dragOrigin;
    dragOrigin = null;
    animateCollisionResolution(localCollisionTargets(draggedNodeId, fallbackPosition));
  }});
  network.on("beforeDrawing", (context) => drawNodeBreathing(context));
  network.on("afterDrawing", (context) => drawEdgeFlow(context));
  if (typeof IntersectionObserver !== "undefined") {{
    const visibilityObserver = new IntersectionObserver((entries) => {{
      graphInViewport = entries.some((entry) => entry.isIntersecting);
      if (graphInViewport) {{
        startAmbientAnimation();
      }} else if (ambientFrame) {{
        window.cancelAnimationFrame(ambientFrame);
        ambientFrame = null;
      }}
    }}, {{ threshold: 0.01 }});
    visibilityObserver.observe(shell);
  }}
  document.addEventListener("visibilitychange", () => {{
    if (document.hidden && ambientFrame) {{
      window.cancelAnimationFrame(ambientFrame);
      ambientFrame = null;
    }} else if (!document.hidden) {{
      startAmbientAnimation();
    }}
  }});
  render(false, true);
  startAmbientAnimation();
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
                "color": "#b95d66" if data["side_effect"] else "#68717e",
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
                    "color": "#b95d66" if file_nodes[source]["isSideEffect"] or file_nodes[target]["isSideEffect"] else "#68717e",
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
            return "#bf7b55", "#d1906b"
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
