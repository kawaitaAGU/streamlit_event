# CEF38.py — pinch zoom restored + slim triangle (no layout break)

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base  # main() は呼ばず、ヘルパーだけ利用

# ===== 定数 ======================================================
SD_BASE = 4.0
POLY_WIDTH_SCALE = 2.0
ANGLE_STACK_BASE_WIDTH = 900

# ===== 角度設定 =================================================
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

# ===== Polygon標準値 =============================================
POLYGON_ROWS = [
    ["00", 0.0, 0.0, 0.0],
    ["Facial", 83.1, 2.5, 0.1036],
    ["Convexity", 11.3, 4.6, 0.1607],
    ["FH_mandiblar", 32.0, 2.4, 0.0893],
    ["Gonial_angle", 129.2, 4.7, 0.1786],
    ["Ramus_angle", 89.7, 3.7, 0.1429],
    ["SNP", 76.1, 2.8, 0.1250],
    ["SNA", 80.9, 3.1, 0.1250],
    ["SNB", 76.2, 2.8, 0.1286],
    ["SNA-SNB diff", 4.7, 1.8, 0.0714],
    ["01", 0.0, 0.0, 0.0],
    ["Interincisal", 124.3, 6.9, 0.2500],
    ["U1 to FH plane", 109.8, 5.3, 0.1679],
    ["L1 to Mandibular", 93.8, 5.9, 0.2107],
    ["L1_FH", 57.2, 3.9, 0.2500],
    ["ZZ", 0.0, 0.0, 0.0],
]

# ====== コンポーネントHTML生成 ===================================
def render_ceph_component(image_data_url: str, marker_size: int, show_labels: bool, point_state: dict):
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
        f'</div>'
        for cfg in ANGLE_STACK_CONFIG
    )

    html = f"""
    <style>
      .ceph-wrapper {{
        position: relative;
        width: min(100%, 960px);
        margin: 0 auto;
        touch-action: pan-x pan-y pinch-zoom; /* ← ピンチズームを許可 */
      }}
      #ceph-image {{
        width: 100%;
        height: auto;
        display: block;
        pointer-events: none;
      }}
      #ceph-stage {{
        position: absolute;
        inset: 0;
        pointer-events: auto;
        z-index: 3;
        touch-action: pinch-zoom; /* ← iPhoneズームOK */
      }}
      .ceph-marker {{
        position: absolute;
        transform: translate(-50%, 0);
        cursor: grab;
      }}
      .ceph-marker.dragging {{ cursor: grabbing; }}
      .pin {{ width: 0; height: 0; margin: 0 auto; }}
      .ceph-label {{
        margin-top: 2px;
        font-size: 11px;
        font-weight: 700;
        color: #f8fafc;
        text-shadow: 0 1px 2px rgba(0,0,0,.6);
        text-align: center;
      }}
      #angle-stack {{
        position: absolute;
        top: 56px; left: 12px;
        display: flex; flex-direction: column; gap: 10px;
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(15,23,42,.78);
        color: #f8fafc;
        font-family: "Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        z-index: 4;
        min-width: 140px;
      }}
      .angle-row {{
        display: flex; justify-content: space-between;
        align-items: center; padding: 2px 0;
      }}
      .angle-name,.angle-value {{ font-size: 13px; font-weight: 600; }}
    </style>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="{image_data_url}" alt="cephalometric background"/>
      <div id="ceph-stage"></div>
      <div id="angle-stack">{angle_rows_html}</div>
    </div>

    <script>
      const ANGLE_CONFIG = {json.dumps(ANGLE_STACK_CONFIG)};
      const payload = {payload_json};

      (function(){{
        const stage = document.getElementById("ceph-stage");
        const image = document.getElementById("ceph-image");
        const markers = [], markerById = {{}};
        let activeMarker = null, dragOffset = {{x:0,y:0}};

        function setPosition(m,left,top){{
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          left=Math.min(Math.max(left,0),w);
          top=Math.min(Math.max(top,0),h);
          m.style.left=left+"px"; m.style.top=top+"px";
          m.dataset.left=left; m.dataset.top=top;
        }}

        function createMarker(pt){{
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s=pt.size||28;
          const pin=document.createElement("div"); pin.className="pin";
          /* 底辺を半分に（片側 s/4 → 全幅 s/2）*/
          const halfBase=Math.max(4,Math.round(s*0.25));
          pin.style.borderLeft=halfBase+"px solid transparent";
          pin.style.borderRight=halfBase+"px solid transparent";
          pin.style.borderBottom=s+"px solid "+(pt.color||"#f97316");
          m.appendChild(pin);

          const lbl=document.createElement("div");
          lbl.className="ceph-label";
          lbl.textContent=pt.id;
          m.appendChild(lbl);

          if(typeof pt.x_px==="number" && typeof pt.y_px==="number"){{
            m.dataset.left=pt.x_px; m.dataset.top=pt.y_px;
          }} else if(typeof pt.x==="number" && typeof pt.y==="number"){{
            m.dataset.left=pt.x; m.dataset.top=pt.y;
          }} else {{
            m.dataset.left="100"; m.dataset.top="100";
          }}
          stage.appendChild(m); markers.push(m); markerById[pt.id]=m;

          m.addEventListener("pointerdown",(ev)=>{{
            if(ev.isPrimary) ev.preventDefault();
            const rect=stage.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0"),top=parseFloat(m.dataset.top||"0");
            dragOffset={{x:ev.clientX-(rect.left+left),y:ev.clientY-(rect.top+top)}};
            activeMarker=m; m.classList.add("dragging");
          }});
          m.addEventListener("pointermove",(ev)=>{{
            if(activeMarker!==m)return;
            const rect=stage.getBoundingClientRect();
            setPosition(m,ev.clientX-rect.left-dragOffset.x,ev.clientY-rect.top-dragOffset.y);
          }});
          const finish=()=>{{if(activeMarker===m){{m.classList.remove("dragging");activeMarker=null;}}}};
          m.addEventListener("pointerup",finish);
          m.addEventListener("pointercancel",finish);
        }}

        (payload.points||[]).forEach(pt=>createMarker(pt));

        function updateLayout(){{
          const w=image.clientWidth||0,h=image.clientHeight||0;
          stage.style.width=w+"px"; stage.style.height=h+"px";
        }}

        if(image.complete && image.naturalWidth) updateLayout();
        else image.addEventListener("load",updateLayout);
        window.addEventListener("resize",updateLayout);
      }})();
    </script>
    """
    return components.html(html, height=1100, scrolling=False)


# ====== Streamlit main ==========================================
def slim_main():
    base.ensure_session_state()

    st.markdown("### 画像の選択")
    uploaded = st.file_uploader(
        "分析したいレントゲン画像をアップロードしてください。",
        type=["png", "jpg", "jpeg", "gif", "webp"],
    )
    if uploaded is not None:
        image_bytes = uploaded.read()
        mime = uploaded.type or "image/png"
        image_data_url = base.to_data_url(image_bytes, mime)
        st.session_state.default_image_data_url = image_data_url
    else:
        image_data_url = st.session_state.default_image_data_url

    if not image_data_url:
        st.error("画像をアップロードしてください。")
        return

    marker_size = 26
    show_labels = True
    render_ceph_component(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=st.session_state.ceph_points,
    )


def main():
    slim_main()


if __name__ == "__main__":
    main()
