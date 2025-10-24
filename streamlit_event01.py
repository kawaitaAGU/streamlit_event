"""CEF08 (2x polygon width): Keep current UI/logic, double polygon width and keep red-dot mapping consistent."""

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base

# ==== 角度定義 ====
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

# ==== ポリゴン行 ====
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

# これまでの横スケール（SD→px 変換の基礎）
SD_BASE = 4.0
# ★ 追加：ポリゴン横幅の倍率（2倍にする）
POLY_WIDTH_SCALE = 2.0


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

    html = """
    <style>
      .ceph-wrapper { position: relative; width: min(100%, 960px); margin: 0 auto; }
      .ceph-wrapper img { width: 100%; height: auto; display: block; pointer-events: none; user-select: none; -webkit-user-select: none; }

      #ceph-planes { position: absolute; inset: 0; pointer-events: none; z-index: 1; }
      #ceph-overlay{ position: absolute; inset: 0; pointer-events: none; z-index: 2; }
      #ceph-stage  { position: absolute; inset: 0; pointer-events: auto; z-index: 3; }

      #angle-stack {
        position: absolute; top: 56px; left: 12px;
        display: flex; flex-direction: column; gap: 12px;
        padding: 12px 14px; border-radius: 10px;
        background: rgba(15,23,42,.78); color: #f8fafc;
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        pointer-events: none; z-index: 4; min-width: 140px;
      }
      .angle-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
      .angle-row.dimmed { opacity: .45; }
      .angle-name, .angle-value { font-size: 13px; font-weight: 600; }

      #std-poly-outline { fill: none; stroke: #1e40af; stroke-width: 1.25; stroke-opacity: .9; }
      .std-centerline { stroke: #facc15; stroke-width: 2; }
      .std-hline { stroke: #ffffff; stroke-width: 1.25; }
      .angle-dot { fill: #ef4444; stroke: #ffffff; stroke-width: 1.5; }
    </style>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background" />
      <svg id="ceph-planes"></svg>
      <svg id="ceph-overlay"></svg>
      <div id="ceph-stage"></div>
      <div id="angle-stack">__ANGLE_ROWS_HTML__</div>
    </div>

    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const POLYGON_ROWS = __POLY_ROWS_JSON__;
      const SD_BASE = __SD_BASE__;
      const POLY_WIDTH_SCALE = __POLY_WIDTH_SCALE__;
      const payload = __PAYLOAD_JSON__;

      (function(){
        const wrapper = document.querySelector(".ceph-wrapper");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");

        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(
          angleRows.map((row) => [row.dataset.angle, { row, valueEl: row.querySelector(".angle-value") }])
        );

        const markers = [];
        const markerById = {};
        const planeDefs = payload.planes || [];
        const planeLines = [];
        const angleCurrent = new Map();
        let activeMarker = null;
        let dragOffset = { x: 0, y: 0 };

        const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
        const xy = (m) => (!m ? null : { x: parseFloat(m.dataset.left||"0"), y: parseFloat(m.dataset.top||"0") });

        // 角度計算
        const computeAngle = (pairA, pairB) => {
          const a1=markerById[pairA[0]], a2=markerById[pairA[1]];
          const b1=markerById[pairB[0]], b2=markerById[pairB[1]];
          if(!a1||!a2||!b1||!b2) return null;
          const A1=xy(a1), A2=xy(a2), B1=xy(b1), B2=xy(b2);
          const vAx=A1.x-A2.x, vAy=A1.y-A2.y, vBx=B1.x-B2.x, vBy=B1.y-B2.y;
          const lenA=Math.hypot(vAx,vAy), lenB=Math.hypot(vBx,vBy);
          if(lenA<1e-6||lenB<1e-6) return null;
          let r=(vAx*vBx+vAy*vBy)/(lenA*lenB);
          r=Math.min(1,Math.max(-1,r));
          return Math.acos(r)*180/Math.PI;
        };

        function updateAngleStack(){
          const cache=new Map();
          ANGLE_CONFIG.forEach(cfg=>{
            const entry=angleRowMap[cfg.id]; if(!entry) return;
            let v=null;
            if(cfg.type==="angle"){ v=computeAngle(cfg.vectors[0], cfg.vectors[1]); }
            else if(cfg.type==="difference"){
              const a=cache.get(cfg.minuend), b=cache.get(cfg.subtrahend);
              if(a!=null && b!=null) v=a-b;
            }
            if(cfg.id==="Convexity" && v!=null) v=180-v; // 補角
            if(v==null || Number.isNaN(v)){
              entry.row.classList.add("dimmed"); entry.valueEl.textContent="--.-°"; angleCurrent.set(cfg.id,null);
            }else{
              entry.row.classList.remove("dimmed"); entry.valueEl.textContent=v.toFixed(1)+"°"; angleCurrent.set(cfg.id,v);
            }
            cache.set(cfg.id,v);
          });
        }

        // マーカー
        function setPosition(m, left, top){
          const w = stage.clientWidth || 1, h = stage.clientHeight || 1;
          const cl = clamp(left, 0, w), ct = clamp(top, 0, h);
          m.style.position = "absolute";
          m.style.transform = "translate(-50%, 0)";
          m.style.left = cl + "px";
          m.style.top  = ct + "px";
          m.dataset.left = cl; m.dataset.top = ct;
        }

        function createMarker(pt){
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s = pt.size || 28;
          const pin = document.createElement("div");
          pin.className="pin"; pin.style.width=0; pin.style.height=0; pin.style.margin="0 auto";
          pin.style.borderLeft=(s/2)+"px solid transparent";
          pin.style.borderRight=(s/2)+"px solid transparent";
          pin.style.borderBottom=s+"px solid "+(pt.color||"#f97316");
          m.appendChild(pin);

          if (typeof pt.x_px === "number" && typeof pt.y_px === "number"){
            m.dataset.initPlaced = "1"; m.dataset.left = pt.x_px; m.dataset.top = pt.y_px;
          } else if (typeof pt.x === "number" && typeof pt.y === "number"){
            m.dataset.initPlaced = "1"; m.dataset.left = pt.x; m.dataset.top = pt.y;
          } else {
            if (typeof pt.ratio_x === "number") m.dataset.ratioX = pt.ratio_x;
            if (typeof pt.ratio_y === "number") m.dataset.ratioY = pt.ratio_y;
            m.dataset.initPlaced = "0";
          }

          stage.appendChild(m);
          markerById[pt.id]=m; markers.push(m);

          // --- drag events (restore CEF07 behavior) ---
          m.addEventListener("pointerdown", (ev) => {
            const rect = stage.getBoundingClientRect();
            const left = parseFloat(m.dataset.left || "0");
            const top  = parseFloat(m.dataset.top  || "0");
            dragOffset = { x: ev.clientX - (rect.left + left), y: ev.clientY - (rect.top + top) };
            activeMarker = m;
            m.classList.add("dragging");
            ev.preventDefault();
          });

          m.addEventListener("pointermove", (ev) => {
            if (activeMarker !== m) return;
            const rect = stage.getBoundingClientRect();
            setPosition(m, ev.clientX - rect.left - dragOffset.x, ev.clientY - rect.top - dragOffset.y);
            updatePlanes();
            updateAngleStack();
            redrawPolygonAndDots();
          });

          const finishDrag = () => {
            if (activeMarker !== m) return;
            m.classList.remove("dragging");
            activeMarker = null;
            updatePlanes();
            updateAngleStack();
            redrawPolygonAndDots();
          };
          m.addEventListener("pointerup", finishDrag);
          m.addEventListener("pointercancel", finishDrag);
        }

        function placeInitMarkersOnce(){
          const w=stage.clientWidth||0, h=stage.clientHeight||0;
          markers.forEach(m=>{
            if (m.dataset.initPlaced === "1"){
              setPosition(m, parseFloat(m.dataset.left||"100"), parseFloat(m.dataset.top||"100"));
              return;
            }
            const rx=(m.dataset.ratioX!==undefined)?parseFloat(m.dataset.ratioX):0.5;
            const ry=(m.dataset.ratioY!==undefined)?parseFloat(m.dataset.ratioY):0.5;
            setPosition(m, rx*w, ry*h);
            m.dataset.initPlaced = "1";
            delete m.dataset.ratioX; delete m.dataset.ratioY;
          });
        }

        // プレーン
        function initPlanes(){
          planesSvg.innerHTML=""; planeLines.length=0;
          planeDefs.forEach(pl=>{
            const line=document.createElementNS("http://www.w3.org/2000/svg","line");
            line.setAttribute("stroke",pl.color||"#f97316");
            line.setAttribute("stroke-width", String(pl.width||2));
            if (pl.dash) line.setAttribute("stroke-dasharray", pl.dash);
            planesSvg.appendChild(line);
            planeLines.push({plane:pl, line});
          });
        }
        function updatePlanes(){
          const w=stage.clientWidth||0, h=stage.clientHeight||0;
          planesSvg.setAttribute("viewBox", "0 0 "+w+" "+h);
          planesSvg.setAttribute("width", w); planesSvg.setAttribute("height", h);
          planeLines.forEach(({plane,line})=>{
            const s=markerById[plane.start], e=markerById[plane.end];
            if(!s||!e){ line.style.opacity=0; return; }
            line.style.opacity=1;
            line.setAttribute("x1", s.dataset.left||"0");
            line.setAttribute("y1", s.dataset.top ||"0");
            line.setAttribute("x2", e.dataset.left||"0");
            line.setAttribute("y2", e.dataset.top ||"0");
          });
        }

        // ポリゴン（列中心に整列）
        function measureRowCenters(){
          const wrapRect = wrapper.getBoundingClientRect();
          return POLYGON_ROWS.map(row=>{
            const label=row[0];
            if (label==="00"||label==="01"||label==="ZZ") return null;
            const entry = angleRowMap[label];
            if (!entry) return null;
            const r = entry.row.getBoundingClientRect();
            return (r.top + r.height/2) - wrapRect.top;
          });
        }

        function redrawPolygonAndDots(){
          if(!overlaySvg) return;
          const w=image.clientWidth||800, h=image.clientHeight||600;
          overlaySvg.setAttribute("viewBox","0 0 "+w+" "+h);
          const offsetX = Math.round(w*0.20) + 60;

          const centers = measureRowCenters();
          let lastY = centers.find(v=>v!=null) ?? Math.round(h*0.1);
          const ys = centers.map(v => { if(v==null) return lastY; lastY=v; return v; });

          const gaps=[];
          for(let i=1;i<centers.length;i++){
            const a=centers[i-1], b=centers[i];
            if(a!=null && b!=null) gaps.push(Math.abs(b-a));
          }
          const median = gaps.length? gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 24;
          const unit = Math.max(14, Math.round(median));

          // ★ 横スケールを2倍に反映：SD_BASE * POLY_WIDTH_SCALE
          const spread = row => (row[3] * SD_BASE * POLY_WIDTH_SCALE * unit);

          const leftXs  = POLYGON_ROWS.map(row => offsetX - spread(row));
          const rightXs = POLYGON_ROWS.map(row => offsetX + spread(row));

          overlaySvg.innerHTML="";
          const g = document.createElementNS("http://www.w3.org/2000/svg","g");
          overlaySvg.appendChild(g);

          const pts=[];
          for(let i=0;i<POLYGON_ROWS.length;i++) pts.push(leftXs[i]+","+ys[i]);
          for(let i=POLYGON_ROWS.length-1;i>=0;i--) pts.push(rightXs[i]+","+ys[i]);
          const poly=document.createElementNS("http://www.w3.org/2000/svg","polygon");
          poly.setAttribute("id","std-poly-outline"); poly.setAttribute("points", pts.join(" "));
          g.appendChild(poly);

          const center=document.createElementNS("http://www.w3.org/2000/svg","line");
          center.setAttribute("x1",offsetX); center.setAttribute("x2",offsetX);
          center.setAttribute("y1",ys[0]); center.setAttribute("y2",ys[ys.length-1]);
          center.setAttribute("class","std-centerline"); g.appendChild(center);

          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const hl=document.createElementNS("http://www.w3.org/2000/svg","line");
            hl.setAttribute("x1", String(leftXs[i])); hl.setAttribute("x2", String(rightXs[i]));
            hl.setAttribute("y1", String(ys[i]));     hl.setAttribute("y2", String(ys[i]));
            hl.setAttribute("class","std-hline"); g.appendChild(hl);
          });

          // dots
          const dots=document.createElementNS("http://www.w3.org/2000/svg","g"); dots.setAttribute("id","std-value-dots"); g.appendChild(dots);
          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const dot=document.createElementNS("http://www.w3.org/2000/svg","circle");
            dot.setAttribute("id","dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-")); dot.setAttribute("class","angle-dot"); dot.setAttribute("r","5");
            dot.setAttribute("cy", String(ys[i])); dots.appendChild(dot);
          });

          // 角度→x の変換も同じスケールで
          positionDots(unit, offsetX);
        }

        function positionDots(unit, offsetX){
          POLYGON_ROWS.forEach(row=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const id="dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-");
            const dot=overlaySvg.querySelector("#"+id); if(!dot) return;

            const mean=row[1], sd=row[2];
            const sd_px = row[3] * SD_BASE * POLY_WIDTH_SCALE * unit; // ★2倍を反映
            const val = angleCurrent.get(label);

            if (val==null || !isFinite(val) || !sd){
              dot.setAttribute("display","none");
            } else {
              const x = offsetX + ((val-mean)/sd) * sd_px;
              dot.setAttribute("cx", String(x));
              dot.removeAttribute("display");
            }
          });
        }

        // レイアウト
        function updateLayout(){
          const w=image.clientWidth||0, h=image.clientHeight||0;
          stage.style.width = w+"px"; stage.style.height = h+"px";

          placeInitMarkersOnce();
          initPlanes();
          updatePlanes();
          updateAngleStack();
          redrawPolygonAndDots();
        }

        // End drag if pointer is released anywhere
        window.addEventListener("pointerup", () => {
          if (activeMarker) {
            activeMarker.classList.remove("dragging");
            activeMarker = null;
            updatePlanes();
            updateAngleStack();
            redrawPolygonAndDots();
          }
        });
        window.addEventListener("pointercancel", () => {
          if (activeMarker) {
            activeMarker.classList.remove("dragging");
            activeMarker = null;
            updatePlanes();
            updateAngleStack();
            redrawPolygonAndDots();
          }
        });

        (payload.points||[]).forEach(pt=>createMarker(pt));

        if (image.complete && image.naturalWidth) updateLayout();
        else image.addEventListener("load", updateLayout, { once:true });

        window.addEventListener("resize", updateLayout);
      })();
    </script>
    """

    html = html.replace("__IMAGE_DATA_URL__", image_data_url)
    html = html.replace("__ANGLE_ROWS_HTML__", angle_rows_html)
    html = html.replace("__ANGLE_CONFIG_JSON__", json.dumps(ANGLE_STACK_CONFIG))
    html = html.replace("__POLY_ROWS_JSON__", json.dumps(POLYGON_ROWS))
    html = html.replace("__SD_BASE__", json.dumps(SD_BASE))
    html = html.replace("__POLY_WIDTH_SCALE__", json.dumps(POLY_WIDTH_SCALE))
    html = html.replace("__PAYLOAD_JSON__", payload_json)

    return components.html(html, height=1100, scrolling=False)


def main():
    base.render_ceph_component = render_ceph_component
    base.main()


if __name__ == "__main__":
    main()
