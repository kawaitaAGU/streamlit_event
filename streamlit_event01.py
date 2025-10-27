# CEF05_AllAngles.py
"""CEF05: Show all cephalometric angles stacked on the left side."""
import math
import json
import streamlit as st
import streamlit.components.v1 as components

import CEF03 as base

# 角度スタックの設定（上から順に表示される）
ANGLE_STACK_CONFIG = [
    ("Facial", "Facial", (("Pog", "N"), ("Po", "Or"))),
    ("Convexity", "Convexity", (("N", "A"), ("A", "Pog"))),
    ("SNA", "SNA", (("N", "A"), ("N", "S"))),
    ("SNB", "SNB", (("N", "B"), ("N", "S"))),
    ("ANB", "ANB", (("N", "A"), ("N", "B"))),
    ("FMA", "FMA", (("Go", "Me"), ("Po", "Or"))),
    ("Gonial", "Gonial", (("Ar", "Go"), ("Go", "Me"))),
]


def render_ceph_component(
    image_data_url: str,
    marker_size: int,
    show_labels: bool,
    point_state: dict,
) -> dict | None:
    """CEF04ベースのドラッグ処理に、複数角度スタックを加える。"""
    payload_json = base.build_component_payload(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=point_state,
    )

    # 左側縦積み角度リスト（Facialが最上段）
    angle_rows_html = "".join(
        f'<div class="angle-row" data-angle="{angle_id}">'
        f'<span class="angle-name">{label}</span>'
        f'<span class="angle-value">--.-°</span>'
        "</div>"
        for angle_id, label, _ in ANGLE_STACK_CONFIG
    )

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
      /* 左側の角度スタック */
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
        min-width: 150px;
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
      }}
      .angle-value {{
        font-variant-numeric: tabular-nums;
        font-size: 13px;
        font-weight: 600;
      }}
    </style>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="{image_data_url}" alt="cephalometric background" />
      <svg id="ceph-planes"></svg>
      <div id="ceph-stage"></div>
      <div id="ceph-coords">ポイントをドラッグして位置を調整できます。</div>
      <div id="angle-stack">{angle_rows_html}</div>
    </div>

    <script>
      const ANGLE_CONFIG = {json.dumps(ANGLE_STACK_CONFIG)};
      const payload = {payload_json};

      (function() {{
        const wrapper = document.querySelector(".ceph-wrapper");
        const image = document.getElementById("ceph-image");
        const stage = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const coords = document.getElementById("ceph-coords");
        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(
          angleRows.map((row) => [
            row.dataset.angle,
            {{ row, valueEl: row.querySelector(".angle-value") }},
          ])
        );

        const showLabels = payload.showLabels !== false;
        const defaultSize = payload.markerSize || 28;

        const postMessage = (payload) => {{
          if (!window.parent) return;
          const frameId = window.frameElement ? window.frameElement.id : "streamlit-frame";
          window.parent.postMessage({{
            isStreamlitMessage: true,
            id: frameId,
            ...payload
          }}, "*");
        }};
        const emitValue = (value) => {{
          postMessage({{
            type: "streamlit:setComponentValue",
            value,
          }});
        }};

        const clamp = (v, min, max) => Math.min(Math.max(v, min), max);
        const markers = [];
        const markerById = {{}};
        const dragOffset = {{x:0, y:0}};
        let activeMarker = null;
        const planeDefs = Array.isArray(payload.planes) ? payload.planes : [];
        const planeLines = [];

        const xy = (marker) => marker ? {{
          x: parseFloat(marker.dataset.left||"0"),
          y: parseFloat(marker.dataset.top||"0")
        }} : null;

        const computeAngleDeg = (pairA, pairB) => {{
          const a1=markerById[pairA[0]], a2=markerById[pairA[1]];
          const b1=markerById[pairB[0]], b2=markerById[pairB[1]];
          if(!a1||!a2||!b1||!b2) return null;
          const A1=xy(a1), A2=xy(a2), B1=xy(b1), B2=xy(b2);
          const vA={{x:A1.x-A2.x,y:A1.y-A2.y}}, vB={{x:B1.x-B2.x,y:B1.y-B2.y}};
          const denom=Math.hypot(vA.x,vA.y)*Math.hypot(vB.x,vB.y);
          if(!denom) return null;
          const dot=vA.x*vB.x+vA.y*vB.y;
          const ratio=Math.min(1,Math.max(-1,dot/denom));
          return (Math.acos(ratio)*180)/Math.PI;
        }};

        const updateAngleStack = () => {{
          ANGLE_CONFIG.forEach(([id,label,pairs]) => {{
            const entry=angleRowMap[id];
            if(!entry) return;
            const ang=computeAngleDeg(pairs[0],pairs[1]);
            if(ang===null||Number.isNaN(ang)){{
              entry.row.classList.add("dimmed");
              entry.valueEl.textContent="--.-°";
            }} else {{
              entry.row.classList.remove("dimmed");
              entry.valueEl.textContent=`${{ang.toFixed(1)}}°`;
            }}
          }});
        }};

        const setPosition=(m,l,t)=>{{
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const L=clamp(l,0,w),T=clamp(t,0,h);
          m.style.left=`${{L}}px`;m.style.top=`${{T}}px`;
          m.dataset.left=L;m.dataset.top=T;
          m.dataset.ratioX=w?L/w:0;m.dataset.ratioY=h?T/h:0;
        }};
        const setFromRatios=(m)=>{{
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const rx=parseFloat(m.dataset.ratioX||"0.5"),ry=parseFloat(m.dataset.ratioY||"0.5");
          setPosition(m,rx*w,ry*h);
        }};
        const emitState=(type,activeId)=>{{
          const pts=markers.map(m=>({{
            id:m.dataset.id,
            x_ratio:parseFloat(m.dataset.ratioX||"0"),
            y_ratio:parseFloat(m.dataset.ratioY||"0"),
          }}));
          emitValue({{event:type,active_id:activeId||null,points:pts}});
        }};

        const createMarker=(pt)=>{{
          const m=document.createElement("div");
          m.className="ceph-marker";
          m.dataset.id=pt.id;m.dataset.label=pt.label||pt.id;
          m.dataset.ratioX=pt.ratio_x||0.5;m.dataset.ratioY=pt.ratio_y||0.5;
          const pin=document.createElement("div");
          pin.className="pin";
          const s=pt.size||defaultSize;
          pin.style.borderLeft=`${{s/2}}px solid transparent`;
          pin.style.borderRight=`${{s/2}}px solid transparent`;
          pin.style.borderBottom=`${{s}}px solid ${{pt.color||"#f97316"}}`;
          m.appendChild(pin);
          if(showLabels){{
            const lbl=document.createElement("div");
            lbl.className="label";lbl.textContent=pt.id;
            m.appendChild(lbl);
          }}
          stage.appendChild(m);
          markers.push(m);markerById[pt.id]=m;

          m.addEventListener("pointerdown",(e)=>{{
            const rect=stage.getBoundingClientRect();
            dragOffset.x=e.clientX-(rect.left+parseFloat(m.dataset.left||"0"));
            dragOffset.y=e.clientY-(rect.top+parseFloat(m.dataset.top||"0"));
            activeMarker=m;m.classList.add("dragging");
            e.preventDefault();
          }});
          m.addEventListener("pointermove",(e)=>{{
            if(activeMarker!==m) return;
            const rect=stage.getBoundingClientRect();
            const L=e.clientX-rect.left-dragOffset.x;
            const T=e.clientY-rect.top-dragOffset.y;
            setPosition(m,L,T);
            updateAngleStack();
          }});
          m.addEventListener("pointerup",()=>{{activeMarker=null;m.classList.remove("dragging");updateAngleStack();}});
          m.addEventListener("pointercancel",()=>{{activeMarker=null;m.classList.remove("dragging");updateAngleStack();}});
        }};

        const init=()=>{{
          payload.points.forEach(pt=>createMarker(pt));
          markers.forEach(m=>setFromRatios(m));
          updateAngleStack();
        }};
        const ensureReady=()=>{{
          if(image.complete&&image.naturalWidth) init();
          else image.addEventListener("load",init,{{once:true}});
        }};
        ensureReady();
      }})();
    </script>
    """
    return components.html(html, height=850, scrolling=False)


def main():
    """CEF03ベースワークフローを再利用して多角度スタックを有効化。"""
    base.render_ceph_component = render_ceph_component
    base.main()


if __name__ == "__main__":
    main()
