import base64
import json
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go


st.set_page_config(page_title="Cephalo Analyzer (Streamlit版)", layout="wide")

# === 定数・初期データ =============================================================

BASE_CANVAS_WIDTH = 800
BASE_CANVAS_HEIGHT = 750



@dataclass(frozen=True)
class PolygonRow:
    label: str
    mean: float
    sd: float
    sd_ratio: float  # 0〜0.25あたりのスケール係数

POINT_IDS = [
    "N",
    "S",
    "Or",
    "Po",
    "Ar",
    "A",
    "U1",
    "L1",
    "B",
    "Pog",
    "Me",
    "Am",
    "Pm",
    "U1r",
    "L1r",
]

OPTIONAL_INITIAL_XY = {
    "N": (693, 199),
    "S": (438, 247),
    "Or": (653, 317),
    "Po": (366, 322),
    "Ar": (387, 362),
    "A": (705, 421),
    "U1": (742, 507),
    "L1": (716, 492),
    "B": (669, 565),
    "Pog": (660, 604),
    "Me": (623, 619),
    "Am": (423, 518),
    "Pm": (410, 493),
    "U1r": (673, 400),
    "L1r": (642, 559),
}

POINT_COLOR_PALETTE = [
    "#f97316",
    "#facc15",
    "#38bdf8",
    "#a855f7",
    "#ef4444",
    "#22c55e",
    "#ec4899",
    "#14b8a6",
    "#eab308",
    "#f472b6",
    "#10b981",
    "#60a5fa",
    "#f59e0b",
    "#6366f1",
    "#fb7185",
]

CEPH_POINTS = [
    {
        "id": pid,
        "label": pid,
        "color": POINT_COLOR_PALETTE[idx % len(POINT_COLOR_PALETTE)],
        "default": OPTIONAL_INITIAL_XY.get(pid, (BASE_CANVAS_WIDTH / 2, BASE_CANVAS_HEIGHT / 2)),
    }
    for idx, pid in enumerate(POINT_IDS)
]

ANGLE_DEFINITIONS: List[Tuple[str, Tuple[Tuple[str, str], Tuple[str, str]]]] = [
    ("Facial", (("Pog", "N"), ("Po", "Or"))),
    ("Convexity", (("N", "A"), ("Pog", "A"))),
    ("FH_mandiblar", (("Or", "Po"), ("Me", "Am"))),
    ("Gonial_angle", (("Ar", "Pm"), ("Me", "Am"))),
    ("Ramus_angle", (("Ar", "Pm"), ("N", "S"))),
    ("SNP", (("N", "Pog"), ("N", "S"))),
    ("SNA", (("N", "A"), ("N", "S"))),
    ("SNB", (("N", "B"), ("N", "S"))),
    ("Interincisal", (("U1", "U1r"), ("L1", "L1r"))),
    ("U1 to FH plane", (("U1", "U1r"), ("Po", "Or"))),
    ("L1 to Mandibular", (("Me", "Am"), ("L1", "L1r"))),
    ("L1_FH", (("L1", "L1r"), ("Or", "Po"))),
]

PLANE_DEFINITIONS = [
    {"id": "SN", "name": "S-N plane", "start": "S", "end": "N", "color": "#fde047", "width": 2.5},
    {"id": "FH", "name": "Or-Po (FH) plane", "start": "Or", "end": "Po", "color": "#60a5fa", "width": 2.5},
    {"id": "Facial", "name": "N-Pog plane", "start": "N", "end": "Pog", "color": "#a855f7", "width": 2.5},
    {"id": "NA", "name": "N-A plane", "start": "N", "end": "A", "color": "#fb7185", "width": 2.5},
    {"id": "APog", "name": "A-Pog plane", "start": "A", "end": "Pog", "color": "#f97316", "width": 2.5},
    {"id": "Mandibular", "name": "Me-Am plane", "start": "Me", "end": "Am", "color": "#22c55e", "width": 2.5},
    {"id": "AB", "name": "A-B plane", "start": "A", "end": "B", "color": "#facc15", "width": 2.5},
    {"id": "U1Axis", "name": "U1-U1r plane", "start": "U1", "end": "U1r", "color": "#38bdf8", "width": 2.5},
    {"id": "L1Axis", "name": "L1-L1r plane", "start": "L1", "end": "L1r", "color": "#14b8a6", "width": 2.5},
    {"id": "Ramus", "name": "Ar-Pm plane", "start": "Ar", "end": "Pm", "color": "#f59e0b", "width": 2.5},
]

RESULT_ORDER = [
    "Facial",
    "Convexity",
    "FH_mandiblar",
    "Gonial_angle",
    "Ramus_angle",
    "SNP",
    "SNA",
    "SNB",
    "SNA-SNB diff",
    "Interincisal",
    "U1 to FH plane",
    "L1 to Mandibular",
    "L1_FH",
]

POLYGON_ROWS: List[PolygonRow] = [
    PolygonRow("00", 0.0, 0.0, 0.0),  # 上部ダミー
    PolygonRow("Facial", 83.1, 2.5, 0.1036),
    PolygonRow("Convexity", 11.3, 4.6, 0.1607),
    PolygonRow("FH_mandiblar", 32.0, 2.4, 0.0893),
    PolygonRow("Gonial_angle", 129.2, 4.7, 0.1786),
    PolygonRow("Ramus_angle", 89.7, 3.7, 0.1429),
    PolygonRow("SNP", 76.1, 2.8, 0.1250),
    PolygonRow("SNA", 80.9, 3.1, 0.1250),
    PolygonRow("SNB", 76.2, 2.8, 0.1286),
    PolygonRow("SNA-SNB diff", 4.7, 1.8, 0.0714),
    PolygonRow("01", 0.0, 0.0, 0.0),  # 中央の切れ目
    PolygonRow("Interincisal", 124.3, 6.9, 0.2500),
    PolygonRow("U1 to FH plane", 109.8, 5.3, 0.1679),
    PolygonRow("L1 to Mandibular", 93.8, 5.9, 0.2107),
    PolygonRow("L1_FH", 57.2, 3.9, 0.2500),
    PolygonRow("ZZ", 0.0, 0.0, 0.0),  # 下部ダミー
]

SD_PERCENT_SCALE = 4.0
SD_PERCENT_MAP = {
    "Facial": 0.1036,
    "Convexity": 0.1607,
    "FH_mandiblar": 0.0893,
    "Gonial_angle": 0.1786,
    "Ramus_angle": 0.1429,
    "SNP": 0.1250,
    "SNA": 0.1250,
    "SNB": 0.1286,
    "SNA-SNB diff": 0.0714,
    "Interincisal": 0.2500,
    "U1 to FH plane": 0.1679,
    "L1 to Mandibular": 0.2107,
    "L1_FH": 0.2500,
}


REFERENCE_DATA: Dict[str, Tuple[float, float]] = {
    "Facial": (83.1, 2.5),
    "Convexity": (11.3, 4.6),
    "FH_mandiblar": (32.0, 2.4),
    "Gonial_angle": (129.2, 4.7),
    "Ramus_angle": (89.7, 3.7),
    "SNP": (76.1, 2.8),
    "SNA": (80.9, 3.1),
    "SNB": (76.2, 2.8),
    "SNA-SNB diff": (4.7, 1.8),
    "Interincisal": (124.3, 6.9),
    "U1 to FH plane": (109.8, 5.3),
    "L1 to Mandibular": (93.8, 5.9),
    "L1_FH": (57.2, 3.9),
}

SD_PERCENT_SCALE = 4.0
SD_PERCENT_MAP = {
    "Facial": 0.1036,
    "Convexity": 0.1607,
    "FH_mandiblar": 0.0893,
    "Gonial_angle": 0.1786,
    "Ramus_angle": 0.1429,
    "SNP": 0.1250,
    "SNA": 0.1250,
    "SNB": 0.1286,
    "SNA-SNB diff": 0.0714,
    "Interincisal": 0.2500,
    "U1 to FH plane": 0.1679,
    "L1 to Mandibular": 0.2107,
    "L1_FH": 0.2500,
}


# === ユーティリティ ===============================================================

def to_data_url(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def load_default_image_data_url() -> Optional[str]:
    path = Path(__file__).with_name("zzz.gif")
    if not path.exists():
        return None
    return to_data_url(path.read_bytes(), "image/gif")


def get_default_point_state() -> Dict[str, Dict[str, float]]:
    state: Dict[str, Dict[str, float]] = {}
    for item in CEPH_POINTS:
        default_x, default_y = item["default"]
        state[item["id"]] = {
            "x_ratio": default_x / BASE_CANVAS_WIDTH,
            "y_ratio": default_y / BASE_CANVAS_HEIGHT,
        }
    return state


def ensure_session_state() -> None:
    if "ceph_points" not in st.session_state:
        st.session_state.ceph_points = get_default_point_state()
    if "ceph_stage" not in st.session_state:
        st.session_state.ceph_stage = {"width": BASE_CANVAS_WIDTH, "height": BASE_CANVAS_HEIGHT}
    if "default_image_data_url" not in st.session_state:
        st.session_state.default_image_data_url = load_default_image_data_url()


def build_component_payload(
    image_data_url: str,
    marker_size: int,
    show_labels: bool,
    point_state: Dict[str, Dict[str, float]],
) -> str:
    payload = {
        "image": image_data_url,
        "markerSize": marker_size,
        "showLabels": show_labels,
        "points": [
            {
                "id": item["id"],
                "label": item["label"],
                "color": item["color"],
                "ratio_x": point_state.get(item["id"], {}).get("x_ratio", 0.5),
                "ratio_y": point_state.get(item["id"], {}).get("y_ratio", 0.5),
            }
            for item in CEPH_POINTS
        ],
        "planes": [
            {
                "id": plane["id"],
                "name": plane["name"],
                "start": plane["start"],
                "end": plane["end"],
                "color": plane.get("color", "#fde68a"),
                "width": plane.get("width", 2),
                "dash": plane.get("dash"),
            }
            for plane in PLANE_DEFINITIONS
        ],
    }
    json_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return json_payload


def render_ceph_component(
    image_data_url: str,
    marker_size: int,
    show_labels: bool,
    point_state: Dict[str, Dict[str, float]],
) -> Optional[Dict]:
    payload_json = build_component_payload(image_data_url, marker_size, show_labels, point_state)

    html = f"""
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
      }}
    </style>
    <div class="ceph-wrapper">
      <img id="ceph-image" src="{image_data_url}" alt="cephalometric background" />
      <svg id="ceph-planes"></svg>
      <div id="ceph-stage"></div>
      <div id="ceph-coords">ポイントをドラッグして位置を調整できます。</div>
    </div>
    <script>
      const payload = {payload_json};
      (function() {{
        const wrapper = document.querySelector(".ceph-wrapper");
        const image = document.getElementById("ceph-image");
        const stage = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const coords = document.getElementById("ceph-coords");
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
            try {{
              marker.setPointerCapture(event.pointerId);
            }} catch (err) {{}}
            coords.textContent = `${{marker.dataset.baseLabel}}: x=${{Math.round(left)}}, y=${{Math.round(top)}}`;
            updateMarkerLabel(marker);
            event.preventDefault();
          }});
        }};

        payload.points.forEach(createMarker);

        planeDefs.forEach(function(plane) {{
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("stroke", plane.color || "#fde047");
          line.setAttribute("stroke-width", plane.width || 2);
          line.setAttribute("stroke-linecap", "round");
          if (plane.dash) {{
            line.setAttribute("stroke-dasharray", plane.dash);
          }}
          line.setAttribute("data-plane-id", plane.id || "");
          line.style.opacity = 0;
          planesSvg.appendChild(line);
          planeLines.push({{ plane: plane, line: line }});
        }});

        const updateLayout = () => {{
          markers.forEach(setFromRatios);
          updatePlanes();
          coords.textContent = "位置情報を取得しました。";
          emitState("layout", null);
        }};

        const handlePointerMove = (event) => {{
          if (!activeMarker) {{
            return;
          }}
          const stageRect = stage.getBoundingClientRect();
          const left = event.clientX - stageRect.left - dragOffset.x;
          const top = event.clientY - stageRect.top - dragOffset.y;
          setPosition(activeMarker, left, top);
          updatePlanes();
          coords.textContent = `${{activeMarker.dataset.baseLabel}}: x=${{Math.round(parseFloat(activeMarker.dataset.left || "0"))}}, y=${{Math.round(parseFloat(activeMarker.dataset.top || "0"))}}`;
          event.preventDefault();
        }};

        const stopDragging = (eventType) => (event) => {{
          if (!activeMarker) {{
            return;
          }}
          try {{
            activeMarker.releasePointerCapture(event.pointerId);
          }} catch (err) {{}}
          const activeId = activeMarker.dataset.id;
          activeMarker.classList.remove("dragging");
          coords.textContent = `${{activeMarker.dataset.baseLabel}}: x=${{Math.round(parseFloat(activeMarker.dataset.left || "0"))}}, y=${{Math.round(parseFloat(activeMarker.dataset.top || "0"))}}`;
          updatePlanes();
          activeMarker = null;
          emitState(eventType, activeId);
        }};

        window.addEventListener("pointermove", handlePointerMove, {{ passive: false }});
        window.addEventListener("pointerup", stopDragging("pointerup"), {{ passive: false }});
        window.addEventListener("pointercancel", stopDragging("pointercancel"), {{ passive: false }});
        window.addEventListener("resize", () => {{
          updateLayout();
          coords.textContent = "レイアウトを再調整しました。";
        }});

        const ensureReady = () => {{
          if (image.complete && image.naturalWidth) {{
            updateLayout();
          }} else {{
            image.addEventListener("load", updateLayout, {{ once: true }});
          }}
        }};

        ensureReady();
        emitState("init", null);
      }})();
    </script>
    """

    return components.html(html, height=820, scrolling=False)


def angle_between(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], p4: Tuple[float, float]) -> float:
    ax, ay = p1[0] - p2[0], p1[1] - p2[1]
    bx, by = p3[0] - p4[0], p3[1] - p4[1]
    denom = math.hypot(ax, ay) * math.hypot(bx, by)
    if denom == 0:
        return float("nan")
    cos_theta = max(-1.0, min(1.0, (ax * bx + ay * by) / denom))
    return math.degrees(math.acos(cos_theta))


def compute_angles(points_px: Dict[str, Tuple[float, float]]) -> Dict[str, float]:
    results: Dict[str, float] = {}
    for name, ((a1, a2), (b1, b2)) in ANGLE_DEFINITIONS:
        if a1 not in points_px or a2 not in points_px or b1 not in points_px or b2 not in points_px:
            results[name] = float("nan")
            continue
        value = angle_between(points_px[a1], points_px[a2], points_px[b1], points_px[b2])
        if name == "Convexity":
            value = 180.0 - value
        results[name] = value
    if "SNA" in results and "SNB" in results:
        sna = results.get("SNA")
        snb = results.get("SNB")
        if sna is None or snb is None or math.isnan(sna) or math.isnan(snb):
            results["SNA-SNB diff"] = float("nan")
        else:
            results["SNA-SNB diff"] = sna - snb
    else:
        results["SNA-SNB diff"] = float("nan")
    return results


def format_float(value: float, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "—"
    return f"{value:.{digits}f}"


def build_points_px(stage: Dict[str, float], state: Dict[str, Dict[str, float]]) -> Dict[str, Tuple[float, float]]:
    width = stage.get("width") or BASE_CANVAS_WIDTH
    height = stage.get("height") or BASE_CANVAS_HEIGHT
    points: Dict[str, Tuple[float, float]] = {}
    for pid, info in state.items():
        x_px = info.get("x_px")
        y_px = info.get("y_px")
        if x_px is None or y_px is None:
            x_px = info.get("x_ratio", 0.5) * width
            y_px = info.get("y_ratio", 0.5) * height
        points[pid] = (float(x_px), float(y_px))
    return points


def update_state_from_component(component_value: Dict) -> None:
    if not component_value:
        return
    stage = component_value.get("stage") or {}
    width = stage.get("width") or st.session_state.ceph_stage.get("width")
    height = stage.get("height") or st.session_state.ceph_stage.get("height")
    if width and height:
        st.session_state.ceph_stage = {"width": width, "height": height}
    points = component_value.get("points") or []
    for entry in points:
        pid = entry.get("id")
        if pid not in st.session_state.ceph_points:
            st.session_state.ceph_points[pid] = {}
        st.session_state.ceph_points[pid].update(
            {
                "x_ratio": entry.get("x_ratio", st.session_state.ceph_points[pid].get("x_ratio", 0.5)),
                "y_ratio": entry.get("y_ratio", st.session_state.ceph_points[pid].get("y_ratio", 0.5)),
                "x_px": entry.get("x_px"),
                "y_px": entry.get("y_px"),
            }
        )
    st.session_state.ceph_last_event = component_value.get("event")
    st.session_state.ceph_active_id = component_value.get("active_id")


def build_reference_text(name: str) -> str:
    reference = REFERENCE_DATA.get(name)
    if not reference:
        return "—"
    mean, sd = reference
    return f"{mean:.1f} ± {sd:.1f}"


def compute_sigma(value: float, name: str) -> Optional[float]:
    if math.isnan(value):
        return None
    reference = REFERENCE_DATA.get(name)
    if not reference:
        return None
    mean, sd = reference
    if sd == 0:
        return None
    return (value - mean) / sd


def create_results_table(angles: Dict[str, float]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for name in RESULT_ORDER:
        formatted_value = format_float(angles.get(name))
        sigma = compute_sigma(angles.get(name, float("nan")), name)
        rows.append(
            {
                "計測項目": name,
                "角度 (°)": formatted_value,
                "平均±SD": build_reference_text(name),
                "偏差 (σ)": format_float(sigma, digits=2) if sigma is not None else "—",
            }
        )
    return rows


def build_points_table(points_px: Dict[str, Tuple[float, float]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in CEPH_POINTS:
        pid = item["id"]
        px = points_px.get(pid, (float("nan"), float("nan")))
        rows.append(
            {
                "Point": pid,
                "x (px)": format_float(px[0], digits=1),
                "y (px)": format_float(px[1], digits=1),
            }
        )
    return rows


def build_polygon_figure(angles: Dict[str, float]) -> Optional[go.Figure]:
    """日本人標準枠と測定値ポリゴンを重ねて描画する。"""
    rows = POLYGON_ROWS
    labels = [row.label for row in rows]
    means = [row.mean for row in rows]
    sds = [row.sd for row in rows]
    ratios = [row.sd_ratio for row in rows]

    y_positions = list(range(len(rows)))
    left_base = [-(ratio * SD_PERCENT_SCALE) for ratio in ratios]
    right_base = [(ratio * SD_PERCENT_SCALE) for ratio in ratios]

    patient_offsets: List[float] = []
    sigmas: List[Optional[float]] = []
    for row in rows:
        if row.sd == 0 or row.mean == 0:
            patient_offsets.append(0.0)
            sigmas.append(None)
            continue
        value = angles.get(row.label)
        if value is None or math.isnan(value):
            patient_offsets.append(0.0)
            sigmas.append(None)
            continue
        sigma = (value - row.mean) / row.sd
        offset = sigma * row.sd_ratio * SD_PERCENT_SCALE
        patient_offsets.append(offset)
        sigmas.append(sigma)

    valid_indices = [idx for idx, sigma in enumerate(sigmas) if sigma is not None]

    fig = go.Figure()
    max_y = len(rows) - 1

    for idx, label in enumerate(labels):
        fig.add_shape(
            type="line",
            x0=-3.2,
            x1=3.2,
            y0=idx,
            y1=idx,
            line=dict(color="rgba(148, 163, 184, 0.25)", width=1),
            layer="below",
        )

    for x0, x1, color in [
        (-3, 3, "rgba(148, 163, 184, 0.08)"),
        (-2, 2, "rgba(148, 163, 184, 0.14)"),
        (-1, 1, "rgba(148, 163, 184, 0.22)"),
    ]:
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=-0.5,
            y1=max_y + 0.5,
            line=dict(width=0),
            fillcolor=color,
            layer="below",
        )

    fig.add_shape(
        type="line",
        x0=0,
        x1=0,
        y0=-0.5,
        y1=max_y + 0.5,
        line=dict(color="#475569", width=2),
        layer="below",
    )

    base_polygon_x = left_base + right_base[::-1] + [left_base[0]]
    base_polygon_y = y_positions + y_positions[::-1] + [y_positions[0]]
    fig.add_trace(
        go.Scatter(
            x=base_polygon_x,
            y=base_polygon_y,
            fill="toself",
            fillcolor="rgba(30, 64, 175, 0.25)",
            line=dict(color="#1e40af", width=2),
            mode="lines",
            hoverinfo="skip",
            showlegend=False,
            name="標準枠",
        )
    )

    patient_polygon_x = patient_offsets + patient_offsets[::-1] + [patient_offsets[0]]
    patient_polygon_y = y_positions + y_positions[::-1] + [y_positions[0]]
    fig.add_trace(
        go.Scatter(
            x=patient_polygon_x,
            y=patient_polygon_y,
            fill="toself",
            fillcolor="rgba(249, 115, 22, 0.18)",
            line=dict(color="rgba(249, 115, 22, 0.65)", width=2),
            mode="lines",
            hoverinfo="skip",
            showlegend=False,
            name="測定値",
        )
    )

    if valid_indices:
        fig.add_trace(
            go.Scatter(
                x=[patient_offsets[i] for i in valid_indices],
                y=[y_positions[i] for i in valid_indices],
                mode="markers+text",
                text=[f"{sigmas[i]:.2f}" for i in valid_indices],
                textposition="middle right",
                marker=dict(size=11, color="#f97316", line=dict(color="#0f172a", width=1)),
                hovertemplate="<b>%{customdata[0]}</b><br>計測値: %{customdata[1]:.2f}°<br>平均: %{customdata[2]:.2f}°<br>SD: %{customdata[3]:.2f}°<br>偏差: %{customdata[4]:.2f} σ<extra></extra>",
                customdata=[
                    (rows[i].label, angles.get(rows[i].label, float("nan")), means[i], sds[i], sigmas[i])
                    for i in valid_indices
                ],
                showlegend=False,
            )
        )

    for idx, row in enumerate(rows):
        if row.mean:
            fig.add_annotation(
                xref="paper",
                yref="y",
                x=1.02,
                y=idx,
                text=f"{row.mean:.1f}",
                showarrow=False,
                font=dict(size=11, color="#0b3fb3"),
                align="left",
            )
        if row.sd:
            fig.add_annotation(
                xref="paper",
                yref="y",
                x=1.12,
                y=idx,
                text=f"{row.sd:.1f}",
                showarrow=False,
                font=dict(size=11, color="#0b3fb3"),
                align="left",
            )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=1.02,
        y=1.02,
        text="平均",
        showarrow=False,
        font=dict(size=12, color="#0b3fb3"),
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=1.12,
        y=1.02,
        text="SD",
        showarrow=False,
        font=dict(size=12, color="#0b3fb3"),
    )

    fig.add_annotation(
        x=-1,
        y=max_y + 0.6,
        text="−1σ",
        showarrow=False,
        font=dict(size=11, color="#1f2937"),
    )
    fig.add_annotation(
        x=1,
        y=max_y + 0.6,
        text="+1σ",
        showarrow=False,
        font=dict(size=11, color="#1f2937"),
    )

    fig.update_xaxes(
        title="標準偏差スケール",
        range=[-3.2, 3.2],
        tickmode="array",
        tickvals=[-3, -2, -1, 0, 1, 2, 3],
        zeroline=False,
        showgrid=True,
        gridcolor="rgba(148, 163, 184, 0.3)",
    )
    fig.update_yaxes(
        tickvals=y_positions,
        ticktext=labels,
        autorange="reversed",
        title=None,
        showgrid=False,
    )
    fig.update_layout(
        margin=dict(l=32, r=120, t=36, b=24),
        height=max(420, 36 * len(rows)),
        plot_bgcolor="rgba(163, 163, 163, 0.25)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def main() -> None:
    ensure_session_state()

    st.title("🦷 ZZZ.gif Cephalometric Analyzer (Streamlit 移植版)")
    st.caption("Tkinter 版 `ce_simple51.py` を Streamlit + コンポーネントで再構築したアプリです。")

    with st.sidebar:
        st.header("表示設定")
        show_labels = st.checkbox("ポイントラベルを表示", value=True)
        marker_size = st.slider("マーカーサイズ (px)", min_value=12, max_value=48, value=26, step=2)
        if st.button("ポイント位置を初期値に戻す", width="stretch"):
            st.session_state.ceph_points = get_default_point_state()
            st.session_state.ceph_stage = {"width": BASE_CANVAS_WIDTH, "height": BASE_CANVAS_HEIGHT}
            st.session_state.ceph_last_event = "reset"
            st.session_state.ceph_active_id = None
            st.experimental_rerun()

    st.markdown("### 画像の選択")
    uploaded = st.file_uploader(
        "分析したいレントゲン画像をアップロードしてください（未選択時は付属の `zzz.gif` を使用）。",
        type=["png", "jpg", "jpeg", "gif", "webp"],
    )

    if uploaded is not None:
        image_bytes = uploaded.read()
        mime = uploaded.type or "image/png"
        image_data_url = to_data_url(image_bytes, mime)
        st.session_state.default_image_data_url = image_data_url
        st.success("アップロードした画像を読み込みました。")
    else:
        image_data_url = st.session_state.default_image_data_url
        if image_data_url:
            st.info("画像が未選択のため、同梱の `zzz.gif` を表示しています。")
        else:
            st.error("表示できる画像が見つかりません。`zzz.gif` を同じフォルダに配置してください。")
            return

    component_value = render_ceph_component(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=st.session_state.ceph_points,
    )

    if isinstance(component_value, dict):
        update_state_from_component(component_value)

    points_px = build_points_px(st.session_state.ceph_stage, st.session_state.ceph_points)
    angles = compute_angles(points_px)

    left_col, right_col = st.columns([1.3, 0.7])

    with left_col:
        st.markdown("### 計測結果")
        rows = create_results_table(angles)
        st.dataframe(rows, width="stretch", hide_index=True)
        polygon_fig = build_polygon_figure(angles)
        if polygon_fig is not None:
            st.markdown("### 標準偏差ポリゴン")
            st.plotly_chart(
                polygon_fig,
                width="stretch",
                config={"displayModeBar": False},
            )
        else:
            st.info("ポリゴン図を表示できる計測値がありません。")

    with right_col:
        st.markdown("### 現在の座標 (px)")
        st.dataframe(build_points_table(points_px), width="stretch", hide_index=True, height=400)

        stage = st.session_state.ceph_stage
        st.markdown(
            f"""
            **ステージ情報**  
            - 幅: {stage.get('width', BASE_CANVAS_WIDTH)} px  
            - 高さ: {stage.get('height', BASE_CANVAS_HEIGHT)} px
            """
        )
        last_event = st.session_state.get("ceph_last_event")
        active_id = st.session_state.get("ceph_active_id")
        if last_event:
            st.caption(f"最後のイベント: {last_event} / アクティブポイント: {active_id or '—'}")


if __name__ == "__main__":
    main()
