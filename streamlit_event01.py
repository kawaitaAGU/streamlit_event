# CEF28.py — angle/coord columns start at 0.5x size; scene pinch-zoom & pan preserved

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base  # 画像/ポイント/プレーンのヘルパーのみ使用

# ===== スケール設定 =====
SD_BASE = 4.0                  # sd_ratio -> px 変換の基礎
POLY_WIDTH_SCALE = 2.0         # ポリゴン横幅を2倍
ANGLE_STACK_BASE_WIDTH = 900   # 角度カラムの基準幅（初期スケーリング用）
ANGLE_STACK_INIT_SCALE = 0.5   # ← 角度カラム＋座標カラムの初期スケール（高さ/幅ともに半分）

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
    ["01", 0.0, 0.0, 0.0],  # くびれ中点（ダミー）
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

    html = """
    <style>
      .root-wrap{position:relative;width:min(100%,960px);margin:0 auto;touch-action:none;}
      #scene{position:relative;transform-origin:0 0;will-change:transform;}

      /* 画像のアスペクト比は height:auto で厳守 */
      #ceph-image{width:100%;height:auto;display:block;pointer-events:none;user-select:none;-webkit-user-select:none;}

      #ceph-planes{position:absolute;inset:0;pointer-events:none;z-index:1;}
      #ceph-overlay{position:absolute;inset:0;pointer-events:none;z-index:2;}
      #ceph-stage{position:absolute;inset:0;pointer-events:auto;z-index:3;touch-action:none;}

      /* 角度カラム（初期は0.5倍に） */
      #angle-stack{
        position:absolute;top:56px;left:12px;
        display:flex;flex-direction:column;gap:10px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#f8fafc;
        font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        pointer-events:none;z-index:4;min-width:140px;
        transform-origin:top left; /* JSで scale を当てる */
      }
      .angle-row{display:flex;justify-content:space-between;align-items:center;padding:2px 0;}
      .angle-row.dimmed{opacity:.45;}
      .angle-name,.angle-value{font-size:13px;font-weight:600;}

      /* 座標一覧（角度カラムの下にリスト表示） */
      #coord-stack{margin-top:10px;padding-top:8px;border-top:1px solid rgba(248,250,252,.2);font:11px/1.3 ui-monospace,Menlo,Consolas,monospace;}
      #coord-stack .coord-line{display:flex;justify-content:space-between;gap:12px;opacity:.95;}
      #coord-stack .coord-line .pt{width:42px;font-weight:700;}
      #coord-stack .coord-line .xy{flex:1;text-align:right;}

      /* ポリゴン線類＆ドット */
      #std-poly-outline{fill:none;stroke:#1e40af;stroke-width:1.25;stroke-opacity:.9;}
      .std-centerline{stroke:#facc15;stroke-width:2;}
      .std-hline{stroke:#ffffff;stroke-width:1.25;}
      .angle-dot{fill:#ef4444;stroke:#ffffff;stroke-width:1.5;}

      /* 三角マーカー（略号ラベル付き） */
      .ceph-marker{position:absolute;transform:translate(-50%,0);cursor:grab;}
      .ceph-marker.dragging{cursor:grabbing;}
      .ceph-marker .pin{width:0;height:0;margin:0 auto;}
      .ceph-label{margin-top:2px;font-size:11px;font-weight:700;color:#f8fafc;text-shadow:0 1px 2px rgba(0,0,0,.6);text-align:center;}
    </style>

    <div class="root-wrap" id="root">
      <div id="scene">
        <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background"/>
        <svg id="ceph-planes"></svg>
        <svg id="ceph-overlay"></svg>
        <div id="ceph-stage"></div>
        <div id="angle-stack">
          __ANGLE_ROWS_HTML__
          <div id="coord-stack"></div>
        </div>
      </div>
    </div>

    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const POLYGON_ROWS = __POLY_ROWS_JSON__;
      const SD_BASE = __SD_BASE__;
      const POLY_WIDTH_SCALE = __POLY_WIDTH_SCALE__;
      const ANGLE_STACK_BASE_WIDTH = __ANGLE_STACK_BASE_WIDTH__;
      const ANGLE_STACK_INIT_SCALE = __ANGLE_STACK_INIT_SCALE__;
      const payload = __PAYLOAD_JSON__;

      (function(){
        const root    = document.getElementById("root");
        const scene   = document.getElementById("scene");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");
        const angleStack= document.getElementById("angle-stack");
        const coordStack= document.getElementById("coord-stack");

        // 角度カラム参照
        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(angleRows.map(r => [r.dataset.angle, {row:r, valueEl:r.querySelector(".angle-value")}]))

        // マーカー＆プレーン
        const markers=[], markerById={}, planeDefs=(payload.planes||[]), planeLines=[];
        let activeMarker=null, dragOffset={x:0,y:0};
        const angleCurrent=new Map();

        // === 初期：角度カラムを 0.5 倍に縮小 ===
        angleStack.style.transform = `scale(${ANGLE_STACK_INIT_SCALE})`;

        // ======== シーンのパン＆ズーム（ピンチ/ドラッグ/ホイール） ========
        let sScale = 1.0;
        let sMin = 0.7, sMax = 3.5;
        let sTx = 0, sTy = 0;
        const activePtrs = new Map();
        let pinchStart = null;
        let isPanningScene = false;

        const clamp=(v,lo,hi)=>Math.min(Math.max(v,lo),hi);

        function applySceneTransform(){
          scene.style.transform = `translate(${sTx}px, ${sTy}px) scale(${sScale})`;
        }

        function getScenePoint(clientX, clientY){
          const rect = root.getBoundingClientRect();
          const x = (clientX - rect.left - sTx) / sScale;
          const y = (clientY - rect.top  - sTy) / sScale;
          return {x, y};
        }

        function onRootPointerDown(ev){
          if (ev.target.closest(".ceph-marker")) return;
          root.setPointerCapture(ev.pointerId);
          activePtrs.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});
          if (activePtrs.size === 1){
            isPanningScene = true;
          } else if (activePtrs.size === 2){
            const pts = Array.from(activePtrs.values());
            const dx = pts[1].x - pts[0].x, dy = pts[1].y - pts[0].y;
            const d = Math.hypot(dx, dy);
            const cx = (pts[0].x + pts[1].x)/2, cy = (pts[0].y + pts[1].y)/2;
            pinchStart = { d, cx, cy, sScale0: sScale, sTx0: sTx, sTy0: sTy };
            isPanningScene = false;
          }
          ev.preventDefault();
        }

        function onRootPointerMove(ev){
          if (!activePtrs.has(ev.pointerId)) return;
          activePtrs.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});

          if (activePtrs.size === 1 && isPanningScene && !activeMarker){
            const ids = Array.from(activePtrs.keys());
            const id = ids[0];
            const cur = activePtrs.get(id);
            if (!onRootPointerMove.prev) onRootPointerMove.prev = {id, x: cur.x, y: cur.y};
            const prev = onRootPointerMove.prev;
            const dx = cur.x - prev.x;
            const dy = cur.y - prev.y;
            sTx += dx; sTy += dy;
            applySceneTransform();
            onRootPointerMove.prev = {id, x: cur.x, y: cur.y};
            ev.preventDefault();
            return;
          }

          if (activePtrs.size === 2 && pinchStart && !activeMarker){
            const pts = Array.from(activePtrs.values());
            const dx = pts[1].x - pts[0].x, dy = pts[1].y - pts[0].y;
            const d2 = Math.hypot(dx, dy);
            if (d2 < 5) return;

            let nextScale = clamp(pinchStart.sScale0 * (d2 / pinchStart.d), sMin, sMax);

            const rect = root.getBoundingClientRect();
            const cx = (pts[0].x + pts[1].x)/2, cy = (pts[0].y + pts[1].y)/2;
            const sx0 = (cx - rect.left - pinchStart.sTx0) / pinchStart.sScale0;
            const sy0 = (cy - rect.top  - pinchStart.sTy0) / pinchStart.sScale0;
            sTx = cx - rect.left - sx0 * nextScale;
            sTy = cy - rect.top  - sy0 * nextScale;
            sScale = nextScale;

            applySceneTransform();
            ev.preventDefault();
            return;
          }
        }

        function onRootPointerUp(ev){
          if (activePtrs.has(ev.pointerId)) activePtrs.delete(ev.pointerId);
          root.releasePointerCapture?.(ev.pointerId);
          if (activePtrs.size === 0){
            isPanningScene = false;
            pinchStart = null;
            onRootPointerMove.prev = null;
          }
        }

        root.addEventListener("pointerdown", onRootPointerDown, {passive:false});
        root.addEventListener("pointermove", onRootPointerMove, {passive:false});
        root.addEventListener("pointerup", onRootPointerUp, {passive:false});
        root.addEventListener("pointercancel", onRootPointerUp, {passive:false});
        root.addEventListener("lostpointercapture", onRootPointerUp, {passive:false});

        // Ctrl+ホイールでズーム
        root.addEventListener("wheel", (ev)=>{
          if (!ev.ctrlKey) return;
          ev.preventDefault();
          const delta = -ev.deltaY;
          const factor = Math.exp(delta * 0.0015);
          const rect = root.getBoundingClientRect();
          const cx = ev.clientX, cy = ev.clientY;
          const sx0 = (cx - rect.left - sTx) / sScale;
          const sy0 = (cy - rect.top  - sTy) / sScale;
          const next = clamp(sScale * factor, sMin, sMax);
          sTx = cx - rect.left - sx0 * next;
          sTy = cy - rect.top  - sy0 * next;
          sScale = next;
          applySceneTransform();
        }, {passive:false});

        // ======== 角度計算 ========
        const xy = m => (!m?null:{x:parseFloat(m.dataset.left||"0"), y:parseFloat(m.dataset.top||"0")});

        const computeAngle=(pairA,pairB)=>{
          const a1=markerById[pairA[0]], a2=markerById[pairA[1]], b1=markerById[pairB[0]], b2=markerById[pairB[1]];
          if(!a1||!a2||!b1||!b2) return null;
          const A1=xy(a1),A2=xy(a2),B1=xy(b1),B2=xy(b2);
          const vAx=A1.x-A2.x, vAy=A1.y-A2.y, vBx=B1.x-B2.x, vBy=B1.y-B2.y;
          const lenA=Math.hypot(vAx,vAy), lenB=Math.hypot(vBx,vBy);
          if(lenA<1e-6||lenB<1e-6) return null;
          let r=(vAx*vBx+vAy*vBy)/(lenA*lenB); r=Math.min(1,Math.max(-1,r));
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
            if(cfg.id==="Convexity" && v!=null) v=180-v;
            if(v==null || Number.isNaN(v)){
              entry.row.classList.add("dimmed"); entry.valueEl.textContent="--.-°"; angleCurrent.set(cfg.id,null);
            }else{
              entry.row.classList.remove("dimmed"); entry.valueEl.textContent=v.toFixed(1)+"°"; angleCurrent.set(cfg.id,v);
            }
          });
          renderCoordStack();
        }

        // ======== マーカー =========
        function setPosition(m,left,top){
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const cl=Math.min(Math.max(left,0),w), ct=Math.min(Math.max(top,0),h);
          m.style.left=cl+"px"; m.style.top=ct+"px"; m.dataset.left=cl; m.dataset.top=ct;
        }

        function createMarker(pt){
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s=pt.size||28;
          const pin=document.createElement("div"); pin.className="pin";
          pin.style.borderLeft=(s/2)+"px solid transparent";
          pin.style.borderRight=(s/2)+"px solid transparent";
          pin.style.borderBottom=s+"px solid "+(pt.color||"#f97316");
          m.appendChild(pin);

          const lbl = document.createElement("div");
          lbl.className = "ceph-label";
          lbl.textContent = pt.id;
          m.appendChild(lbl);

          if (typeof pt.x_px==="number" && typeof pt.y_px==="number"){
            m.dataset.initPlaced="1"; m.dataset.left=pt.x_px; m.dataset.top=pt.y_px;
          } else if (typeof pt.x==="number" && typeof pt.y==="number") {
            m.dataset.initPlaced="1"; m.dataset.left=pt.x; m.dataset.top=pt.y;
          } else {
            if (typeof pt.ratio_x==="number") m.dataset.ratioX=pt.ratio_x;
            if (typeof pt.ratio_y==="number") m.dataset.ratioY=pt.ratio_y;
            m.dataset.initPlaced="0";
          }

          stage.appendChild(m); markerById[pt.id]=m; markers.push(m);

          m.addEventListener("pointerdown",(ev)=>{
            if (activePtrs.size >= 2) return; // ピンチ中は開始しない
            const rect = root.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0"), top=parseFloat(m.dataset.top||"0");
            const p = getScenePoint(ev.clientX, ev.clientY);
            dragOffset = { x: p.x - left, y: p.y - top };
            activeMarker=m; m.classList.add("dragging");
            ev.stopPropagation(); ev.preventDefault();
          });

          m.addEventListener("pointermove",(ev)=>{
            if(activeMarker!==m) return;
            const p = getScenePoint(ev.clientX, ev.clientY);
            setPosition(m, p.x - dragOffset.x, p.y - dragOffset.y);
            updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
            ev.stopPropagation(); ev.preventDefault();
          });

          const finish=()=>{
            if(activeMarker!==m) return;
            m.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
          };
          m.addEventListener("pointerup", finish);
          m.addEventListener("pointercancel", finish);
        }

        function placeInitMarkersOnce(){
          const w=stage.clientWidth||0,h=stage.clientHeight||0;
          markers.forEach(m=>{
            if(m.dataset.initPlaced==="1"){
              setPosition(m, parseFloat(m.dataset.left||"100"), parseFloat(m.dataset.top||"100"));
              return;
            }
            const rx=(m.dataset.ratioX!==undefined)?parseFloat(m.dataset.ratioX):0.5;
            const ry=(m.dataset.ratioY!==undefined)?parseFloat(m.dataset.ratioY):0.5;
            setPosition(m, rx*w, ry*h);
            m.dataset.initPlaced="1"; delete m.dataset.ratioX; delete m.dataset.ratioY;
          });
        }

        // ======== プレーン =========
        function initPlanes(){
          planesSvg.innerHTML=""; planeLines.length=0;
          planeDefs.forEach(pl=>{
            const line=document.createElementNS("http://www.w3.org/2000/svg","line");
            line.setAttribute("stroke",pl.color||"#f97316");
            line.setAttribute("stroke-width", String(pl.width||2));
            if(pl.dash) line.setAttribute("stroke-dasharray", pl.dash);
            planesSvg.appendChild(line);
            planeLines.push({plane:pl,line});
          });
        }
        function updatePlanes(){
          const w=stage.clientWidth||0, h=stage.clientHeight||0;
          planesSvg.setAttribute("viewBox","0 0 "+w+" "+h);
          planesSvg.setAttribute("width", w); planesSvg.setAttribute("height", h);
          planeLines.forEach(({plane,line})=>{
            const s=markerById[plane.start], e=markerById[plane.end];
            if(!s||!e){ line.style.opacity=0; return; }
            line.style.opacity=1;
            line.setAttribute("x1", s.dataset.left||"0"); line.setAttribute("y1", s.dataset.top||"0");
            line.setAttribute("x2", e.dataset.left||"0"); line.setAttribute("y2", e.dataset.top||"0");
          });
        }

        // ======== 角度カラム行の中心Y（sceneローカル） ========
        function measureRowCentersMap(){
          const rootRect = root.getBoundingClientRect();
          const map = new Map();
          ANGLE_CONFIG.forEach(cfg=>{
            const entry=angleRowMap[cfg.id]; if(!entry) return;
            const r = entry.row.getBoundingClientRect();
            const cy_screen = (r.top + r.height/2);
            const cy = (cy_screen - rootRect.top - sTy) / sScale; // scene座標に逆変換
            map.set(cfg.id, cy);
          });
          return map;
        }

        // ======== ポリゴン＆赤丸 ========
        function redrawPolygonAndDots(){
          if(!overlaySvg) return;
          const w=image.clientWidth||800, h=image.clientHeight||600;
          overlaySvg.setAttribute("viewBox","0 0 "+w+" "+h);
          const offsetX = Math.round(w*0.20) + 60;

          const centersMap = measureRowCentersMap();
          const ys = [];
          for(let i=0;i<POLYGON_ROWS.length;i++){
            const label = POLYGON_ROWS[i][0];

            if(label==="01"){
              let prevY=null, nextY=null;
              for(let p=i-1;p>=0;p--){
                const lab=POLYGON_ROWS[p][0];
                if(lab!=="00" && lab!=="01" && lab!=="ZZ" && centersMap.has(lab)){ prevY=centersMap.get(lab); break; }
              }
              for(let n=i+1;n<POLYGON_ROWS.length;n++){
                const lab=POLYGON_ROWS[n][0];
                if(lab!=="00" && lab!=="01" && lab!=="ZZ" && centersMap.has(lab)){ nextY=centersMap.get(lab); break; }
              }
              let mid=(h*0.5);
              if(prevY!=null && nextY!=null) mid=(prevY+nextY)/2;
              else if(prevY!=null) mid=prevY+40;
              else if(nextY!=null) mid=nextY-40;
              ys.push(mid);
            } else if(label==="00" || label==="ZZ"){
              if(ys.length===0){
                let firstRealY=null;
                for(let n=i+1;n<POLYGON_ROWS.length;n++){
                  const lab=POLYGON_ROWS[n][0];
                  if(lab!=="00" && lab!=="01" && lab!=="ZZ" && centersMap.has(lab)){ firstRealY=centersMap.get(lab); break; }
                }
                ys.push(firstRealY ?? Math.round(h*0.1));
              }else{
                ys.push(ys[ys.length-1]);
              }
            } else {
              const cy = centersMap.get(label);
              ys.push(cy ?? (ys.length? ys[ys.length-1] : Math.round(h*0.1)));
            }
          }

          const gaps=[]; for(let i=1;i<ys.length;i++){ gaps.push(Math.abs(ys[i]-ys[i-1])); }
          const median = gaps.length? gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 24;
          const unit = Math.max(14, Math.round(median));

          const spread = row => (row[3] * SD_BASE * POLY_WIDTH_SCALE * unit);
          const leftXs  = POLYGON_ROWS.map(row => offsetX - spread(row));
          const rightXs = POLYGON_ROWS.map(row => offsetX + spread(row));

          overlaySvg.innerHTML="";
          const g=document.createElementNS("http://www.w3.org/2000/svg","g");
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

          const dots=document.createElementNS("http://www.w3.org/2000/svg","g"); dots.setAttribute("id","std-value-dots"); g.appendChild(dots);
          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const dot=document.createElementNS("http://www.w3.org/2000/svg","circle");
            dot.setAttribute("id","dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-"));
            dot.setAttribute("class","angle-dot");
            dot.setAttribute("r","5");
            dot.setAttribute("cy", String(ys[i]));
            dots.appendChild(dot);
          });

          positionDots(unit, offsetX);
        }

        function positionDots(unit, offsetX){
          POLYGON_ROWS.forEach(row=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ") return;
            const dot=overlaySvg.querySelector("#dot-"+label.replace(/[^a-zA-Z0-9_-]/g,"-")); if(!dot) return;

            const mean=row[1], sd=row[2];
            const sd_px = row[3] * SD_BASE * POLY_WIDTH_SCALE * unit;
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

        // ======== 座標リスト（角度の下） ========
        function renderCoordStack(){
          if (!coordStack) return;
          const ids = Object.keys(markerById).sort();
          coordStack.innerHTML = ids.map(id=>{
            const m = markerById[id];
            const x = m ? Math.round(parseFloat(m.dataset.left||"0")) : 0;
            const y = m ? Math.round(parseFloat(m.dataset.top ||"0")) : 0;
            return `<div class="coord-line"><span class="pt">${id}</span><span class="xy">(${x}, ${y})</span></div>`;
          }).join("");
        }

        // ======== レイアウト初期化 ========
        function updateLayout(){
          const w=image.clientWidth||0, h=image.clientHeight||0;
          stage.style.width=w+"px"; stage.style.height=h+"px";
          placeInitMarkersOnce(); initPlanes(); updatePlanes(); updateAngleStack(); redrawPolygonAndDots();
        }

        (payload.points||[]).forEach(pt=>createMarker(pt));

        if (image.complete && image.naturalWidth) updateLayout();
        else image.addEventListener("load", updateLayout, {once:true});

        window.addEventListener("resize", updateLayout);

        // 初期 transform（必要なら少し縮小）
        const base = ANGLE_STACK_BASE_WIDTH || 900;
        const iw = image.clientWidth || base;
        if (iw < base){
          let sScale0 = Math.max(0.8, iw / base);
          // 角度カラム側はすでに 0.5x 済みなので、scene 初期スケールはそのまま
          // シーンの倍率だけ反映
          (function(){ sScale = sScale0; })();
          // translate は 0 のまま。必要に応じて中央寄せしたければここで sTx/sTy を調整
          applySceneTransform();
        }
      })();
    </script>
    """

    html = html.replace("__IMAGE_DATA_URL__", image_data_url)
    html = html.replace("__ANGLE_ROWS_HTML__", angle_rows_html)
    html = html.replace("__ANGLE_CONFIG_JSON__", json.dumps(ANGLE_STACK_CONFIG))
    html = html.replace("__POLY_ROWS_JSON__", json.dumps(POLYGON_ROWS))
    html = html.replace("__SD_BASE__", json.dumps(SD_BASE))
    html = html.replace("__POLY_WIDTH_SCALE__", json.dumps(POLY_WIDTH_SCALE))
    html = html.replace("__ANGLE_STACK_BASE_WIDTH__", json.dumps(ANGLE_STACK_BASE_WIDTH))
    html = html.replace("__ANGLE_STACK_INIT_SCALE__", json.dumps(ANGLE_STACK_INIT_SCALE))
    html = html.replace("__PAYLOAD_JSON__", payload_json)

    return components.html(html, height=1100, scrolling=False)

# ── 最小 UI の main（サイドバーは出さない） ──
def slim_main() -> None:
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
