# CEF30.py — wide layout, responsive image, compact panels (angle+coords) with unified scaling

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base  # 画像/ポイント/プレーンのヘルパのみ利用（mainは使わない）

# ---- ページ設定（★ 追加）----
st.set_page_config(layout="wide")

# ===== スケール設定 =====
SD_BASE = 4.0                  # sd_ratio -> px 変換の基礎
POLY_WIDTH_SCALE = 2.0         # ポリゴン横幅を2倍
ANGLE_STACK_BASE_WIDTH = 900   # 角度/座標パネルの基準画像幅(px)

# ===== 角度定義 =====
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

# ===== ポリゴン行（"01" はくびれ用ダミー行） =====
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

def render_ceph_component(image_data_url: str, marker_size: int, show_labels: bool, point_state: dict):
    payload_json = base.build_component_payload(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=point_state,
    )

    angle_rows_html = "".join(
        f'<div class="angle-row" data-angle="{cfg["id"]}">'
        f'  <span class="angle-name">{cfg["label"]}</span>'
        f'  <span class="angle-value">--.-°</span>'
        f'</div>'
        for cfg in ANGLE_STACK_CONFIG
    )

    # coords パネル（空ボディ。JS側で行を生成）
    coord_stack_html = '<div id="coord-stack"><div class="coord-title">Coordinates</div><div id="coord-body"></div></div>'

    html = f"""
    <style>
      /* ★ ここを拡張：幅は画面に応じて 1600px まで、中央寄せ */
      .ceph-wrapper{{position:relative;width:clamp(320px,96vw,1600px);margin:0 auto;}}

      /* 画像は比率厳守 */
      #ceph-image{{width:100%;height:auto;display:block;pointer-events:none;user-select:none;-webkit-user-select:none;}}

      #ceph-planes{{position:absolute;inset:0;pointer-events:none;z-index:1;}}
      #ceph-overlay{{position:absolute;inset:0;pointer-events:none;z-index:2;}}
      #ceph-stage{{position:absolute;inset:0;pointer-events:auto;z-index:3;touch-action:none;}}

      /* 角度パネル */
      #angle-stack{{
        position:absolute;top:56px;left:12px;
        display:flex;flex-direction:column;gap:10px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#f8fafc;
        font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        pointer-events:none;z-index:4;min-width:140px;
        transform-origin:top left;transform:scale(1);
      }}
      .angle-row{{display:flex;justify-content:space-between;align-items:center;padding:2px 0;}}
      .angle-row.dimmed{{opacity:.45;}}
      .angle-name,.angle-value{{font-size:13px;font-weight:600;}}

      /* 座標パネル（角度の下） */
      #coord-stack{{
        position:absolute;top:310px;left:12px;
        display:flex;flex-direction:column;gap:6px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#e2e8f0;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
        pointer-events:none;z-index:4;min-width:160px;
        transform-origin:top left;transform:scale(1);
      }}
      #coord-stack .coord-title{{font-weight:700;color:#f8fafc;margin-bottom:4px;font-size:12px;}}
      .coord-row{{display:flex;justify-content:space-between;gap:10px;font-size:11px;}}
      .coord-id{{opacity:.85;}}
      .coord-val{{color:#fff;}}

      /* ポリゴン線＆ドット */
      #std-poly-outline{{fill:none;stroke:#1e40af;stroke-width:1.25;stroke-opacity:.9;}}
      .std-centerline{{stroke:#facc15;stroke-width:2;}}
      .std-hline{{stroke:#ffffff;stroke-width:1.25;}}
      .angle-dot{{fill:#ef4444;stroke:#ffffff;stroke-width:1.5;}}

      /* 三角マーカー（底辺1/2に） */
      .ceph-marker{{position:absolute;transform:translate(-50%,0);cursor:grab;text-align:center;}}
      .ceph-marker.dragging{{cursor:grabbing;}}
      .ceph-marker .pin{{width:0;height:0;margin:0 auto;}}
      .ceph-label{{margin-top:2px;font-size:11px;font-weight:700;color:#f8fafc;text-shadow:0 1px 2px rgba(0,0,0,.6);}}
    </style>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background"/>
      <svg id="ceph-planes"></svg>
      <svg id="ceph-overlay"></svg>
      <div id="ceph-stage"></div>
      <div id="angle-stack">{angle_rows_html}</div>
      {coord_stack_html}
    </div>

    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const POLYGON_ROWS = __POLY_ROWS_JSON__;
      const SD_BASE = __SD_BASE__;
      const POLY_WIDTH_SCALE = __POLY_WIDTH_SCALE__;
      const ANGLE_STACK_BASE_WIDTH = __ANGLE_STACK_BASE_WIDTH__;
      const payload = __PAYLOAD_JSON__;

      (function(){{
        const wrapper = document.querySelector(".ceph-wrapper");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");
        const angleStack= document.getElementById("angle-stack");
        const coordStack= document.getElementById("coord-stack");
        const coordBody = document.getElementById("coord-body");

        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(angleRows.map(r => [r.dataset.angle, {{row:r, valueEl:r.querySelector(".angle-value")}}]));

        const markers=[], markerById={{}}, planeDefs=(payload.planes||[]), planeLines=[];
        let activeMarker=null, dragOffset={{x:0,y:0}};

        const clamp=(v,lo,hi)=>Math.min(Math.max(v,lo),hi);
        const xy = m => (!m?null:{{x:parseFloat(m.dataset.left||"0"), y:parseFloat(m.dataset.top||"0")}});

        // ---- パネル縮尺（★ 強化：小画面は更に縮小）----
        function syncAngleStackScale(){{
          const base = ANGLE_STACK_BASE_WIDTH || 900;
          const w = image.clientWidth || base;
          let scale = Math.min(1, w / base);
          if (w < 700) scale *= 0.85;    // iPhone対策でさらに縮小
          applyPanelScale(scale);
        }}
        function applyPanelScale(scale){{
          angleStack.style.transform = `scale(${scale})`;
          if (coordStack){{
            coordStack.style.transformOrigin = "top left";
            coordStack.style.transform = `scale(${scale})`;
          }}
        }}

        // ---- 角度計算 ----
        const computeAngle=(pairA,pairB)=>{{
          const a1=markerById[pairA[0]], a2=markerById[pairA[1]], b1=markerById[pairB[0]], b2=markerById[pairB[1]];
          if(!a1||!a2||!b1||!b2) return null;
          const A1=xy(a1),A2=xy(a2),B1=xy(b1),B2=xy(b2);
          const vAx=A1.x-A2.x, vAy=A1.y-A2.y, vBx=B1.x-B2.x, vBy=B1.y-B2.y;
          const lenA=Math.hypot(vAx,vAy), lenB=Math.hypot(vBx,vBy);
          if(lenA<1e-6||lenB<1e-6) return null;
          let r=(vAx*vBx+vAy*vBy)/(lenA*lenB); r=Math.min(1,Math.max(-1,r));
          return Math.acos(r)*180/Math.PI;
        }};

        const angleCurrent=new Map();
        function updateAngleStack(){{
          const cache=new Map();
          ANGLE_CONFIG.forEach(cfg=>{{
            const entry=angleRowMap[cfg.id]; if(!entry) return;
            let v=null;
            if(cfg.type==="angle"){{ v=computeAngle(cfg.vectors[0], cfg.vectors[1]); }}
            else if(cfg.type==="difference"){{ const a=cache.get(cfg.minuend), b=cache.get(cfg.subtrahend); if(a!=null&&b!=null) v=a-b; }}
            if(cfg.id==="Convexity" && v!=null) v=180-v;
            if(v==null || Number.isNaN(v)){{ entry.row.classList.add("dimmed"); entry.valueEl.textContent="--.-°"; angleCurrent.set(cfg.id,null); }}
            else {{ entry.row.classList.remove("dimmed"); entry.valueEl.textContent=v.toFixed(1)+"°"; angleCurrent.set(cfg.id,v); }}
            cache.set(cfg.id,v);
          }});
        }}

        // ---- 座標スタック ----
        function buildCoordStack(){{
          if(!coordBody) return;
          coordBody.innerHTML = "";
          markers.forEach(m => {{
            const row = document.createElement("div"); row.className="coord-row"; row.dataset.id=m.dataset.id;
            const id  = document.createElement("div"); id.className="coord-id"; id.textContent = m.dataset.id;
            const val = document.createElement("div"); val.className="coord-val"; val.textContent="(—, —)";
            row.appendChild(id); row.appendChild(val); coordBody.appendChild(row);
          }});
          refreshCoordStack();
        }}
        function refreshCoordStack(){{
          if(!coordBody) return;
          markers.forEach(m => {{
            const row = coordBody.querySelector(`.coord-row[data-id="${{m.dataset.id}}"]`);
            if(!row) return;
            const val = row.querySelector(".coord-val");
            val.textContent = `(${{Math.round(parseFloat(m.dataset.left||0))}}, ${{Math.round(parseFloat(m.dataset.top||0))}})`;
          }});
        }}

        // ---- マーカー ----
        function setPosition(m,left,top){{
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const cl=clamp(left,0,w), ct=clamp(top,0,h);
          m.style.left=cl+"px"; m.style.top=ct+"px"; m.dataset.left=cl; m.dataset.top=ct;
        }}
        function createMarker(pt){{
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s=pt.size||28;

          // ★ 底辺 1/2
          const pin=document.createElement("div"); pin.className="pin";
          pin.style.borderLeft=(s*0.5/2)+"px solid transparent";
          pin.style.borderRight=(s*0.5/2)+"px solid transparent";
          pin.style.borderBottom=s+"px solid "+(pt.color||"#f97316");
          m.appendChild(pin);

          const lbl=document.createElement("div"); lbl.className="ceph-label"; lbl.textContent=pt.id; m.appendChild(lbl);

          if (typeof pt.x_px==="number" && typeof pt.y_px==="number"){{m.dataset.initPlaced="1"; m.dataset.left=pt.x_px; m.dataset.top=pt.y_px;}}
          else if (typeof pt.x==="number" && typeof pt.y==="number"){{m.dataset.initPlaced="1"; m.dataset.left=pt.x; m.dataset.top=pt.y;}}
          else {{ if (typeof pt.ratio_x==="number") m.dataset.ratioX=pt.ratio_x; if (typeof pt.ratio_y==="number") m.dataset.ratioY=pt.ratio_y; m.dataset.initPlaced="0"; }}

          stage.appendChild(m); markerById[pt.id]=m; markers.push(m);

          m.addEventListener("pointerdown",(ev)=>{{
            const rect=stage.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0"), top=parseFloat(m.dataset.top||"0");
            dragOffset={{x:ev.clientX-(rect.left+left), y:ev.clientY-(rect.top+top)}};
            activeMarker=m; m.classList.add("dragging"); ev.preventDefault();
          }});
          m.addEventListener("pointermove",(ev)=>{{
            if(activeMarker!==m) return;
            const rect=stage.getBoundingClientRect();
            setPosition(m, ev.clientX-rect.left-dragOffset.x, ev.clientY-rect.top-dragOffset.y);
            refreshCoordStack(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
          }});
          const finish=()=>{{
            if(activeMarker!==m) return;
            m.classList.remove("dragging"); activeMarker=null;
            refreshCoordStack(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
          }};
          m.addEventListener("pointerup", finish);
          m.addEventListener("pointercancel", finish);
        }}
        function placeInitMarkersOnce(){{
          const w=stage.clientWidth||0,h=stage.clientHeight||0;
          markers.forEach(m=>{{
            if(m.dataset.initPlaced==="1"){{ setPosition(m, parseFloat(m.dataset.left||"100"), parseFloat(m.dataset.top||"100")); return; }}
            const rx=(m.dataset.ratioX!==undefined)?parseFloat(m.dataset.ratioX):0.5;
            const ry=(m.dataset.ratioY!==undefined)?parseFloat(m.dataset.ratioY):0.5;
            setPosition(m, rx*w, ry*h);
            m.dataset.initPlaced="1"; delete m.dataset.ratioX; delete m.dataset.ratioY;
          }});
          refreshCoordStack();
        }}

        // ---- プレーン ----
        function initPlanes(){{
          planesSvg.innerHTML=""; planeLines.length=0;
          planeDefs.forEach(pl=>{{
            const line=document.createElementNS("http://www.w3.org/2000/svg","line");
            line.setAttribute("stroke",pl.color||"#f97316");
            line.setAttribute("stroke-width", String(pl.width||2));
            if(pl.dash) line.setAttribute("stroke-dasharray", pl.dash);
            planesSvg.appendChild(line);
            planeLines.push({{plane:pl,line}});
          }});
        }}
        function updatePlanes(){{
          const w=stage.clientWidth||0, h=stage.clientHeight||0;
          planesSvg.setAttribute("viewBox","0 0 "+w+" "+h);
          planesSvg.setAttribute("width", w); planesSvg.setAttribute("height", h);
          planeLines.forEach(({plane,line})=>{{
            const s=markerById[plane.start], e=markerById[plane.end];
            if(!s||!e){{ line.style.opacity=0; return; }}
            line.style.opacity=1;
            line.setAttribute("x1", s.dataset.left||"0"); line.setAttribute("y1", s.dataset.top||"0");
            line.setAttribute("x2", e.dataset.left||"0"); line.setAttribute("y2", e.dataset.top||"0");
          }});
        }}

        // ---- 角度カラム行の中心Y（scale反映後）----
        function measureRowCentersMap(){{
          const wrapRect = wrapper.getBoundingClientRect();
          const map = new Map();
          ANGLE_CONFIG.forEach(cfg=>{{
            const entry=angleRowMap[cfg.id]; if(!entry) return;
            const r = entry.row.getBoundingClientRect();
            map.set(cfg.id, (r.top + r.height/2) - wrapRect.top);
          }});
          return map;
        }}

        // ---- ポリゴン＆ドット ----
        function redrawPolygonAndDots(){{
          if(!overlaySvg) return;
          const w=image.clientWidth||800, h=image.clientHeight||600;
          // 小画面では少し左寄せ（重なり軽減）
          const small = w < 700 ? 1 : 0;
          const offsetX = Math.round(w*(small ? 0.16 : 0.20)) + 60;

          overlaySvg.setAttribute("viewBox","0 0 "+w+" "+h);
          overlaySvg.innerHTML="";
          const g=document.createElementNS("http://www.w3.org/2000/svg","g");
          overlaySvg.appendChild(g);

          const centersMap = measureRowCentersMap();
          const ys = [];
          for(let i=0;i<POLYGON_ROWS.length;i++){{
            const label = POLYGON_ROWS[i][0];
            if(label==="01"){{
              let prevY=null, nextY=null;
              for(let p=i-1;p>=0;p--){{const lab=POLYGON_ROWS[p][0]; if(lab!=="00"&&lab!=="01"&&lab!=="ZZ"&&centersMap.has(lab)){{prevY=centersMap.get(lab);break;}}}}
              for(let n=i+1;n<POLYGON_ROWS.length;n++){{const lab=POLYGON_ROWS[n][0]; if(lab!=="00"&&lab!=="01"&&lab!=="ZZ"&&centersMap.has(lab)){{nextY=centersMap.get(lab);break;}}}}
              let mid=Math.round(h*0.5);
              if(prevY!=null && nextY!=null) mid=(prevY+nextY)/2; else if(prevY!=null) mid=prevY+40; else if(nextY!=null) mid=nextY-40;
              ys.push(mid);
            }} else if(label==="00" || label==="ZZ"){{
              if(ys.length===0){{ let firstRealY=null; for(let n=i+1;n<POLYGON_ROWS.length;n++){{const lab=POLYGON_ROWS[n][0]; if(lab!=="00"&&lab!=="01"&&lab!=="ZZ"&&centersMap.has(lab)){{firstRealY=centersMap.get(lab);break;}}}} ys.push(firstRealY ?? Math.round(h*0.1)); }}
              else ys.push(ys[ys.length-1]);
            }} else {{
              const cy = centersMap.get(label);
              ys.push(cy ?? (ys.length? ys[ys.length-1] : Math.round(h*0.1)));
            }}
          }}

          const gaps=[]; for(let i=1;i<ys.length;i++) gaps.push(Math.abs(ys[i]-ys[i-1]));
          const median = gaps.length? gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 24;
          const unit = Math.max(14, Math.round(median));
          const spread = row => (row[3] * SD_BASE * POLY_WIDTH_SCALE * unit);
          const leftXs  = POLYGON_ROWS.map(row => offsetX - spread(row));
          const rightXs = POLYGON_ROWS.map(row => offsetX + spread(row));

          const pts=[]; for(let i=0;i<POLYGON_ROWS.length;i++) pts.push(leftXs[i]+","+ys[i]);
          for(let i=POLYGON_ROWS.length-1;i>=0;i--) pts.push(rightXs[i]+","+ys[i]);
          const poly=document.createElementNS("http://www.w3.org/2000/svg","polygon");
          poly.setAttribute("id","std-poly-outline"); poly.setAttribute("points", pts.join(" "));
          g.appendChild(poly);

          const center=document.createElementNS("http://www.w3.org/2000/svg","line");
          center.setAttribute("x1",offsetX); center.setAttribute("x2",offsetX);
          center.setAttribute("y1",ys[0]); center.setAttribute("y2",ys[ys.length-1]);
          center.setAttribute("class","std-centerline"); g.appendChild(center);

          POLYGON_ROWS.forEach((row,i)=>{{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const hl=document.createElementNS("http://www.w3.org/2000/svg","line");
            hl.setAttribute("x1", String(leftXs[i])); hl.setAttribute("x2", String(rightXs[i]));
            hl.setAttribute("y1", String(ys[i]));     hl.setAttribute("y2", String(ys[i]));
            hl.setAttribute("class","std-hline"); g.appendChild(hl);
          }});

          const dots=document.createElementNS("http://www.w3.org/2000/svg","g"); dots.setAttribute("id","std-value-dots"); g.appendChild(dots);
          POLYGON_ROWS.forEach((row,i)=>{{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const dot=document.createElementNS("http://www.w3.org/2000/svg","circle");
            dot.setAttribute("id","dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-"));
            dot.setAttribute("class","angle-dot"); dot.setAttribute("r","5"); dot.setAttribute("cy", String(ys[i]));
            dots.appendChild(dot);
          }});

          positionDots(unit, offsetX);
        }}

        function positionDots(unit, offsetX){{
          POLYGON_ROWS.forEach(row=>{{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const dot=overlaySvg.querySelector("#dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-")); if(!dot) return;
            const mean=row[1], sd=row[2];
            const sd_px = row[3] * SD_BASE * POLY_WIDTH_SCALE * unit;
            const val = angleCurrent.get(label);
            if (val==null || !isFinite(val) || !sd) dot.setAttribute("display","none");
            else {{ const x = offsetX + ((val-mean)/sd) * sd_px; dot.setAttribute("cx", String(x)); dot.removeAttribute("display"); }}
          }});
        }}

        // ---- レイアウト ----
        function updateLayout(){{
          const w=image.clientWidth||0, h=image.clientHeight||0;
          stage.style.width=w+"px"; stage.style.height=h+"px";
          syncAngleStackScale();
          placeInitMarkersOnce(); initPlanes(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
        }}

        // ---- ポインタ終端ガード ----
        window.addEventListener("pointerup", ()=>{{ if(activeMarker){{activeMarker.classList.remove("dragging"); activeMarker=null; refreshCoordStack(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();}} }});
        window.addEventListener("pointercancel", ()=>{{ if(activeMarker){{activeMarker.classList.remove("dragging"); activeMarker=null; refreshCoordStack(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();}} }});

        // ---- 起動 ----
        (payload.points||[]).forEach(pt=>createMarker(pt));
        buildCoordStack();  // 行だけ先に用意

        if (image.complete && image.naturalWidth) updateLayout();
        else image.addEventListener("load", updateLayout, {{once:true}});
        window.addEventListener("resize", updateLayout);
      }})();
    </script>
    """

    html = html.replace("__IMAGE_DATA_URL__", image_data_url)\
               .replace("__ANGLE_CONFIG_JSON__", json.dumps(ANGLE_STACK_CONFIG))\
               .replace("__POLY_ROWS_JSON__", json.dumps(POLYGON_ROWS))\
               .replace("__SD_BASE__", json.dumps(SD_BASE))\
               .replace("__POLY_WIDTH_SCALE__", json.dumps(POLY_WIDTH_SCALE))\
               .replace("__ANGLE_STACK_BASE_WIDTH__", json.dumps(ANGLE_STACK_BASE_WIDTH))\
               .replace("__PAYLOAD_JSON__", payload_json)

    return components.html(html, height=1100, scrolling=False)

# ---- 最小UI（サイドバーなし）----
def slim_main() -> None:
    base.ensure_session_state()

    st.markdown("### 画像の選択")
    uploaded = st.file_uploader("分析したいレントゲン画像をアップロードしてください。", type=["png","jpg","jpeg","gif","webp"])

    if uploaded is not None:
        image_bytes = uploaded.read()
        mime = uploaded.type or "image/png"
        image_data_url = base.to_data_url(image_bytes, mime)
        st.session_state.default_image_data_url = image_data_url
    else:
        image_data_url = st.session_state.default_image_data_url

    if not image_data_url:
        st.error("表示画像をuploadしてください。")
        return

    marker_size = 26
    show_labels = True

    component_value = render_ceph_component(
        image_data_url=image_data_url,
        marker_size=marker_size,
        show_labels=show_labels,
        point_state=st.session_state.ceph_points,
    )
    if isinstance(component_value, dict):
        base.update_state_from_component(component_value)

def main():
    slim_main()

if __name__ == "__main__":
    main()
