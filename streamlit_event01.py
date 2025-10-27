"""CEF05: Extend CEF04 with a left-side angle stack (SNA, Facial)."""
import json
import math
import streamlit as st
import streamlit.components.v1 as components

import CEF03 as base

# 画面左側に縦積みで表示する角度の定義
ANGLE_STACK_CONFIG = [
    {"id": "Facial", "label": "Facial", "type": "angle", "vectors": [["Pog", "N"], ["Po", "Or"]]},
    {"id": "Convexity", "label": "Convexity", "type": "angle", "vectors": [["N", "A"], ["Pog", "A"]]},
    {"id": "FH_mandiblar", "label": "FH mandiblar", "type": "angle", "vectors": [["Or", "Po"], ["Me", "Am"]]},
    {"id": "Gonial_angle", "label": "Gonial angle", "type": "angle", "vectors": [["Ar", "Pm"], ["Me", "Am"]]},
    {"id": "Ramus_angle", "label": "Ramus angle", "type": "angle", "vectors": [["Ar", "Pm"], ["N", "S"]]},
    {"id": "SNP", "label": "SNP", "type": "angle", "vectors": [["N", "Pog"], ["N", "S"]]},
    {"id": "SNA", "label": "SNA", "type": "angle", "vectors": [["N", "A"], ["N", "S"]]},
    {"id": "SNB", "label": "SNB", "type": "angle", "vectors": [["N", "B"], ["N", "S"]]},
    {"id": "SNA-SNB diff", "label": "SNA - SNB", "type": "difference", "minuend": "SNA", "subtrahend": "SNB"},
    {"id": "Interincisal", "label": "Interincisal", "type": "angle", "vectors": [["U1", "U1r"], ["L1", "L1r"]]},
    {"id": "U1 to FH plane", "label": "U1 - FH plane", "type": "angle", "vectors": [["U1", "U1r"], ["Po", "Or"]]},
    {"id": "L1 to Mandibular", "label": "L1 - Mandibular", "type": "angle", "vectors": [["Me", "Am"], ["L1", "L1r"]]},
    {"id": "L1_FH", "label": "L1 - FH", "type": "angle", "vectors": [["L1", "L1r"], ["Or", "Po"]]},
]


def render_ceph_component(
    image_data_url: str,
    marker_size: int,
    show_labels: bool,
    point_state: dict,
) -> dict | None:
    """CEF04ベースのドラッグ処理に、SNA/Facial の角度スタックを加える。"""
    payload_json = base.build_component_payload(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=point_state,
    )
    angle_rows_html = "".join(
        f'<div class="angle-row" data-angle="{cfg["id"]}">'
        f'<span class="angle-name">{cfg["label"]}</span>'
        f'<span class="angle-value">--.-°</span>'
        "</div>"
        for cfg in ANGLE_STACK_CONFIG
    )

    html = """
    <style>
      .ceph-wrapper {{
        position: relative;
        width: min(100%, 960px);
        margin: 0 auto;
      }}
      .ceph-wrapper img {{
        width: 100%;
        height: auto;
        display: block;
        pointer-events: none;
        user-select: none;
        -webkit-user-select: none;
      }}
      #ceph-planes {{
        position: absolute;
        inset: 0;
        pointer-events: none;
      }}
      #ceph-stage {{
        position: absolute;
        inset: 0;
        pointer-events: none;
      }}
      .ceph-marker {{
        position: absolute;
        transform: translate(-50%, 0);
        cursor: grab;
        pointer-events: auto;
        touch-action: none;
        text-align: center;
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .ceph-marker.dragging {{
        cursor: grabbing;
      }}
      .ceph-marker .pin {{
        width: 0;
        height: 0;
        margin: 0 auto;
      }}
      .ceph-marker .label {{
        margin-top: 4px;
        font-size: 12px;
        font-weight: 600;
        color: #f8fafc;
        text-shadow: 0 1px 2px rgba(15, 23, 42, 0.8);
        letter-spacing: 0.04em;
      }}
      #ceph-coords {{
        position: absolute;
        top: 12px;
        left: 12px;
        background: rgba(15, 23, 42, 0.68);
        color: #e2e8f0;
        padding: 6px 10px;
        border-radius: 6px;
        font: 12px/1.4 monospace;
        pointer-events: none;
        z-index: 3;
      }}
      #angle-stack {{
        position: absolute;
        top: 56px;
        left: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 10px 12px;
        border-radius: 8px;
        background: rgba(15, 23, 42, 0.78);
        color: #f8fafc;
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        pointer-events: none;
        z-index: 3;
        min-width: 120px;
      }}
      .angle-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
      }}
      .angle-row.dimmed {{
        opacity: 0.45;
      }}
      .angle-name {{
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.04em;
      }}
      .angle-value {{
        font-variant-numeric: tabular-nums;
        font-size: 13px;
        font-weight: 600;
      }}
      /* --- minimal overlay (Facial mean ±1SD & 0点) --- */
      #ceph-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 2; /* above image, below angle stack */
      }
      #ceph-overlay .zero-dot { fill: #f43f5e; }
      #ceph-overlay .mean-line { stroke: #e2e8f0; stroke-width: 2; }
      #ceph-overlay .sd-line, #ceph-overlay .tick { stroke: #94a3b8; stroke-width: 1.5; shape-rendering: crispEdges; }
      #ceph-overlay .label {
        font: 11px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        fill: #e2e8f0;
        paint-order: stroke;
        stroke: rgba(15,23,42,0.6);
        stroke-width: 2px;
      }
    </style>
    <div class="ceph-wrapper">
      <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background" />
      <svg id="ceph-planes"></svg>
      <svg id="ceph-overlay"></svg>
      <div id="ceph-stage"></div>
      <div id="ceph-coords">ポイントをドラッグして位置を調整できます。</div>
      <div id="angle-stack">__ANGLE_ROWS_HTML__</div>
    </div>
    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const payload = __PAYLOAD_JSON__;

      (function() {{
        const wrapper = document.querySelector(".ceph-wrapper");
        const image = document.getElementById("ceph-image");
        const stage = document.getElementById("ceph-stage");
        // --- Minimal Facial polygon overlay ---
        const overlaySvg = document.getElementById("ceph-overlay");
        const drawFacialOverlay = function() {
          if (!overlaySvg) { return; }
          const img = document.getElementById("ceph-image");
          const w = (img && img.clientWidth) ? img.clientWidth : ((overlaySvg && overlaySvg.clientWidth) ? overlaySvg.clientWidth : 800);
          const h = (img && img.clientHeight) ? img.clientHeight : ((overlaySvg && overlaySvg.clientHeight) ? overlaySvg.clientHeight : 600);
          overlaySvg.setAttribute("viewBox", "0 0 " + String(w) + " " + String(h));
          overlaySvg.innerHTML = "";
          var cx = Math.round(w * 0.5);
          var y0 = Math.round(h * 0.12);
          var measured = 84.34, mean = 83.1, sd = 2.5;
          var px_per_deg = Math.max(4, Math.round(Math.min(w, h) * 0.008));
          var dx_sd = sd * px_per_deg;
          var dx_meas = (measured - mean) * px_per_deg;
          var zero = document.createElementNS("http://www.w3.org/2000/svg", "circle");
          zero.setAttribute("cx", String(cx)); zero.setAttribute("cy", String(y0 - 16)); zero.setAttribute("r", "4"); zero.setAttribute("class", "zero-dot");
          overlaySvg.appendChild(zero);
          var meanLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
          meanLine.setAttribute("x1", String(cx)); meanLine.setAttribute("x2", String(cx)); meanLine.setAttribute("y1", String(y0 - 10)); meanLine.setAttribute("y2", String(y0 + 14)); meanLine.setAttribute("class", "mean-line");
          overlaySvg.appendChild(meanLine);
          var sdLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
          sdLine.setAttribute("x1", String(cx - dx_sd)); sdLine.setAttribute("x2", String(cx + dx_sd)); sdLine.setAttribute("y1", String(y0)); sdLine.setAttribute("y2", String(y0)); sdLine.setAttribute("class", "sd-line");
          overlaySvg.appendChild(sdLine);
          var tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
          tick.setAttribute("x1", String(cx + dx_meas)); tick.setAttribute("x2", String(cx + dx_meas)); tick.setAttribute("y1", String(y0 - 6)); tick.setAttribute("y2", String(y0 + 6)); tick.setAttribute("class", "tick");
          overlaySvg.appendChild(tick);
          var label = document.createElementNS("http://www.w3.org/2000/svg", "text");
          label.setAttribute("x", String(cx + dx_sd + 8)); label.setAttribute("y", String(y0 + 4)); label.setAttribute("class", "label");
          label.textContent = "Facial  " + measured.toFixed(2) + "  （平均 " + mean.toFixed(1) + " ± " + sd.toFixed(1) + "）";
          overlaySvg.appendChild(label);
        };
        const planesSvg = document.getElementById("ceph-planes");
        const coords = document.getElementById("ceph-coords");
        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(
          angleRows.map((row) => [
            row.dataset.angle,
            {{ row, valueEl: row.querySelector(".angle-value") }},
          ])
        );
        if (!wrapper || !image || !stage || !planesSvg) {{
          return;
        }}

        const showLabels = payload.showLabels !== false;
        const defaultSize = payload.markerSize || 28;
        const frameId = window.frameElement ? window.frameElement.id : "streamlit-frame";

        const postMessage = (payload) => {{
          if (!window.parent) {{
            return;
          }}
          window.parent.postMessage(
            {{
              isStreamlitMessage: true,
              id: frameId,
              ...payload,
            }},
            "*"
          );
        }};

        const emitValue = (value) => {{
          postMessage({{
            type: "streamlit:setComponentValue",
            value,
          }});
        }};

        const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
        const markers = [];
        const markerById = {{}};
        const dragOffset = {{ x: 0, y: 0 }};
        let activeMarker = null;

        const planeDefs = Array.isArray(payload.planes) ? payload.planes : [];
        const planeLines = [];

        const setPosition = (marker, left, top) => {{
          const width = stage.clientWidth || 1;
          const height = stage.clientHeight || 1;
          const clampedLeft = clamp(left, 0, width);
          const clampedTop = clamp(top, 0, height);
          marker.style.left = `${{clampedLeft}}px`;
          marker.style.top = `${{clampedTop}}px`;
          marker.dataset.left = String(clampedLeft);
          marker.dataset.top = String(clampedTop);
          marker.dataset.ratioX = width ? clampedLeft / width : 0;
          marker.dataset.ratioY = height ? clampedTop / height : 0;
          updateMarkerLabel(marker);
        }};

        const setFromRatios = (marker) => {{
          const width = stage.clientWidth || 1;
          const height = stage.clientHeight || 1;
          const ratioX = parseFloat(marker.dataset.ratioX || "0.5");
          const ratioY = parseFloat(marker.dataset.ratioY || "0.5");
          setPosition(marker, ratioX * width, ratioY * height);
        }};

        const emitState = (eventType, activeId) => {{
          const width = Math.round(stage.clientWidth || 0);
          const height = Math.round(stage.clientHeight || 0);
          const points = markers.map((marker) => ({{
            id: marker.dataset.id,
            label: marker.dataset.label,
            x_px: parseFloat(marker.dataset.left || "0"),
            y_px: parseFloat(marker.dataset.top || "0"),
            x_ratio: parseFloat(marker.dataset.ratioX || "0"),
            y_ratio: parseFloat(marker.dataset.ratioY || "0"),
          }}));
          emitValue({{
            event: eventType,
            active_id: activeId || null,
            stage: {{ width, height }},
            points,
          }});
        }};

        const updatePlanes = () => {{
          if (!planesSvg) {{
            return;
          }}
          const width = stage.clientWidth || 0;
          const height = stage.clientHeight || 0;
          planesSvg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);
          planesSvg.setAttribute("width", width);
          planesSvg.setAttribute("height", height);
          planeLines.forEach((entry) => {{
            const plane = entry.plane;
            const line = entry.line;
            const startMarker = markerById[plane.start];
            const endMarker = markerById[plane.end];
            if (!startMarker || !endMarker) {{
              line.style.opacity = 0;
              return;
            }}
            line.style.opacity = 1;
            line.setAttribute("x1", startMarker.dataset.left || "0");
            line.setAttribute("y1", startMarker.dataset.top || "0");
            line.setAttribute("x2", endMarker.dataset.left || "0");
            line.setAttribute("y2", endMarker.dataset.top || "0");
          }});
        }};

        const updateMarkerLabel = (marker) => {{
          if (!showLabels) {{
            return;
          }}
          const labelEl = marker.querySelector(".label");
          if (!labelEl) {{
            return;
          }}
          const baseLabel = marker.dataset.baseLabel || marker.dataset.id || "";
          const x = Math.round(parseFloat(marker.dataset.left || "0"));
          const y = Math.round(parseFloat(marker.dataset.top || "0"));
          labelEl.textContent = `${{baseLabel}} (${{x}}, ${{y}})`;
        }};

        const xy = (marker) => {{
          if (!marker) {{
            return null;
          }}
          return {{
            x: parseFloat(marker.dataset.left || "0"),
            y: parseFloat(marker.dataset.top || "0"),
          }};
        }};

        const computeAngleDeg = (pairA, pairB) => {{
          const a1 = markerById[pairA[0]];
          const a2 = markerById[pairA[1]];
          const b1 = markerById[pairB[0]];
          const b2 = markerById[pairB[1]];
          if (!a1 || !a2 || !b1 || !b2) {{
            return null;
          }}
          const A1 = xy(a1);
          const A2 = xy(a2);
          const B1 = xy(b1);
          const B2 = xy(b2);
          const vecA = {{ x: A1.x - A2.x, y: A1.y - A2.y }};
          const vecB = {{ x: B1.x - B2.x, y: B1.y - B2.y }};
          const denom = Math.hypot(vecA.x, vecA.y) * Math.hypot(vecB.x, vecB.y);
          if (!denom) {{
            return null;
          }}
          const dot = vecA.x * vecB.x + vecA.y * vecB.y;
          const ratio = Math.min(1, Math.max(-1, dot / denom));
          return (Math.acos(ratio) * 180) / Math.PI;
        }};

        const updateAngleStack = () => {{
          const angleValues = new Map();
          ANGLE_CONFIG.forEach((config) => {{
            const entry = angleRowMap[config.id];
            if (!entry) {{
              return;
            }}
            let value = null;
            if (config.type === "angle") {{
              value = computeAngleDeg(config.vectors[0], config.vectors[1]);
            }} else if (config.type === "difference") {{
              const minuend = angleValues.get(config.minuend);
              const subtrahend = angleValues.get(config.subtrahend);
              if (minuend != null && !Number.isNaN(minuend) && subtrahend != null && !Number.isNaN(subtrahend)) {{
                value = minuend - subtrahend;
              }}
            }}
            if (value === null || Number.isNaN(value)) {{
              entry.row.classList.add("dimmed");
              entry.valueEl.textContent = "--.-°";
            }} else {{
              entry.row.classList.remove("dimmed");
              entry.valueEl.textContent = `${{value.toFixed(1)}}°`;
            }}
            angleValues.set(config.id, value);
          }});
        }};

        const createMarker = (pt) => {{
          const marker = document.createElement("div");
          marker.className = "ceph-marker";
          marker.dataset.id = pt.id;
          marker.dataset.label = pt.label || pt.id;
          marker.dataset.baseLabel = pt.label || pt.id;
          marker.dataset.ratioX = typeof pt.ratio_x === "number" ? pt.ratio_x : 0.5;
          marker.dataset.ratioY = typeof pt.ratio_y === "number" ? pt.ratio_y : 0.5;
          marker.dataset.size = pt.size || defaultSize;

          const pin = document.createElement("div");
          pin.className = "pin";
          const size = parseFloat(marker.dataset.size || defaultSize);
          pin.style.borderLeft = `${{size / 2}}px solid transparent`;
          pin.style.borderRight = `${{size / 2}}px solid transparent`;
          pin.style.borderBottom = `${{size}}px solid ${{pt.color || "#f97316"}}`;
          marker.appendChild(pin);

          if (showLabels) {{
            const label = document.createElement("div");
            label.className = "label";
            marker.appendChild(label);
          }}

          stage.appendChild(marker);
          markers.push(marker);
          markerById[pt.id] = marker;

          marker.addEventListener("pointerdown", (event) => {{
            const stageRect = stage.getBoundingClientRect();
            const left = parseFloat(marker.dataset.left || "0");
            const top = parseFloat(marker.dataset.top || "0");
            dragOffset.x = event.clientX - (stageRect.left + left);
            dragOffset.y = event.clientY - (stageRect.top + top);
            activeMarker = marker;
            marker.classList.add("dragging");
            emitState("pointerdown", marker.dataset.id);
            event.preventDefault();
          }});

          marker.addEventListener("pointermove", (event) => {{
            if (activeMarker !== marker) {{
              return;
            }}
            const stageRect = stage.getBoundingClientRect();
            const newLeft = event.clientX - stageRect.left - dragOffset.x;
            const newTop = event.clientY - stageRect.top - dragOffset.y;
            setPosition(marker, newLeft, newTop);
            updatePlanes();
            updateAngleStack();
            emitState("pointermove", marker.dataset.id);
          }});

          const finish = (eventType) => {{
            if (activeMarker !== marker) {{
              return;
            }}
            marker.classList.remove("dragging");
            activeMarker = null;
            updateAngleStack();
            emitState(eventType, marker.dataset.id);
            updatePlanes();
          }};

          marker.addEventListener("pointerup", () => finish("pointerup"));
          marker.addEventListener("pointercancel", () => finish("pointercancel"));

          return marker;
        }};

        const initPlanes = () => {{
          planesSvg.innerHTML = "";
          planeLines.length = 0;
          planeDefs.forEach((plane) => {{
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("stroke", plane.color || "#f97316");
            line.setAttribute("stroke-width", String(plane.width || 2));
            if (plane.dash) {{
              line.setAttribute("stroke-dasharray", plane.dash);
            }}
            planesSvg.appendChild(line);
            planeLines.push({{ plane, line }});
          }});
        }};

        const updateLayout = () => {{
          const width = image.clientWidth;
          const height = image.clientHeight;
          stage.style.width = `${{width}}px`;
          stage.style.height = `${{height}}px`;
          initPlanes();
          markers.forEach((marker) => setFromRatios(marker));
          updatePlanes();
          updateAngleStack();
          coords.textContent = `ステージサイズ: ${{width}} × ${{height}}`;
        }};

        payload.points.forEach((pt) => createMarker(pt));
        initPlanes();
        updatePlanes();
        updateAngleStack();
        coords.textContent = "ポイントをドラッグして位置調整";

        window.addEventListener("pointerup", () => {{
          if (activeMarker) {{
            activeMarker.classList.remove("dragging");
            activeMarker = null;
            updateAngleStack();
            emitState("pointerup", null);
          }}
        }});
        window.addEventListener("pointercancel", () => {{
          if (activeMarker) {{
            activeMarker.classList.remove("dragging");
            activeMarker = null;
            updateAngleStack();
            emitState("pointercancel", null);
          }}
        }});
        window.addEventListener("resize", () => {
          drawFacialOverlay();{
          updateLayout();
        drawFacialOverlay();
          coords.textContent = "レイアウトを再調整しました。";
        }});

        const ensureReady = () => {{
          if (image.complete && image.naturalWidth) {{
            updateLayout();
        drawFacialOverlay();
            updateAngleStack();
          }} else {{
            image.addEventListener("load", () => {{
              updateLayout();
        drawFacialOverlay();
              updateAngleStack();
            }}, {{ once: true }});
          }}
        }};

        ensureReady();
        emitState("init", null);
      }})();
    </script>
    """
    
    # --- substitute tokens safely (no f-strings / no .format on HTML) ---
    html = html.replace("__IMAGE_DATA_URL__", image_data_url)
    html = html.replace("__PAYLOAD_JSON__", payload_json)
    html = html.replace("__ANGLE_ROWS_HTML__", angle_rows_html)
    html = html.replace("__ANGLE_CONFIG_JSON__", json.dumps(ANGLE_STACK_CONFIG))
return components.html(html, height=1100, scrolling=False)


def main() -> None:
    """CEF03 のワークフローを再利用して角度スタックを有効化する。"""
    base.render_ceph_component = render_ceph_component
    base.main()


if __name__ == "__main__":
    main()
