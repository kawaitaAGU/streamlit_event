# CEF46_pinch_stable.py — minimal patch for reliable iPhone pinch + stable drag
# 変更点:
# - (#) viewport を user-scalable=yes に（保険）                               // ★
# - (#) .ceph-wrapper に overscroll-behavior: contain                         // ★
# - (#) #ceph-stage の touch-action: pinch-zoom → auto                         // ★
# - (#) タッチは setPointerCapture を使わず、2本指以上はドラッグ無効           // ★
# - (#) releasePointerCapture の event 参照バグ修正（pointerId保持）           // ★

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base

SD_BASE = 4.0
POLY_WIDTH_SCALE = 2.0
ANGLE_STACK_BASE_WIDTH = 900

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

POLYGON_ROWS = [
    ["VTOP", 0.0, 0.0, 0.0],
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
    ["VBOT", 0.0, 0.0, 0.0],
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
      .ceph-wrapper{
        position:relative;width:min(100%,960px);margin:0 auto;
        overscroll-behavior: contain; /* ★ ラバーバンド軽減 */
      }
      #ceph-image{width:100%;height:auto;display:block;pointer-events:none;user-select:none;-webkit-user-select:none;}
      #ceph-planes{position:absolute;inset:0;pointer-events:none;z-index:1;}
      #ceph-overlay{position:absolute;inset:0;pointer-events:none;z-index:2;}
      #ceph-stage{
        position:absolute;inset:0;pointer-events:auto;z-index:3;
        touch-action:auto;    /* ★ pinch-zoom → auto に変更（ブラウザに任せる） */
        -webkit-user-select:none;user-select:none;
      }
      #angle-stack{
        position:absolute;top:56px;left:12px;
        display:flex;flex-direction:column;gap:8px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#f8fafc;
        font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        pointer-events:none;z-index:4;min-width:140px;
        transform-origin:top left;transform:scale(1);
      }
      .angle-row{display:flex;justify-content:space-between;align-items:center;padding:2px 0;}
      .angle-row.dimmed{opacity:.45;}
      .angle-name,.angle-value{font-size:13px;font-weight:600;}

      #coord-stack{margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,.18);
                   font-size:11px;line-height:1.25;max-height:200px;overflow:auto;white-space:nowrap;}
      #coord-stack .coord-item{display:flex;justify-content:space-between;gap:10px;opacity:.9;}

      #std-poly-outline{fill:none;stroke:#ffffff;stroke-width:1.6;stroke-opacity:.95;}
      .std-centerline{stroke:#facc15;stroke-width:2;}
      .std-hline{stroke:#ffffff;stroke-width:1.1;}
      .std-patient{stroke:#ef4444;stroke-width:2;fill:none;}

      .ceph-marker{position:absolute;transform:translate(-50%,0);cursor:grab;}
      .ceph-marker.dragging{cursor:grabbing;}
      .ceph-marker .pin{width:0;height:0;margin:0 auto;}
      .ceph-label{margin-top:2px;font-size:11px;font-weight:700;color:#f8fafc;text-shadow:0 1px 2px rgba(0,0,0,.6);text-align:center;}
    </style>

    <!-- ★ 保険: ページの viewport をズーム許可に -->
    <script>
      (function(){
        try{
          let m=document.querySelector('meta[name="viewport"]');
          const c='width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes';
          if(m) m.setAttribute('content',c);
          else{ m=document.createElement('meta'); m.name='viewport'; m.content=c; document.head.appendChild(m); }
        }catch(e){}
      })();
    </script>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background"/>
      <svg id="ceph-planes"></svg>
      <svg id="ceph-overlay"></svg>
      <div id="ceph-stage"></div>
      <div id="angle-stack">
        __ANGLE_ROWS_HTML__
        <div id="coord-stack"></div>
      </div>
    </div>

    <script>
      const ANGLE_CONFIG = __ANGLE_CONFIG_JSON__;
      const POLYGON_ROWS = __POLY_ROWS_JSON__;
      const SD_BASE = __SD_BASE__;
      const POLY_WIDTH_SCALE = __POLY_WIDTH_SCALE__;
      const ANGLE_STACK_BASE_WIDTH = __ANGLE_STACK_BASE_WIDTH__;
      const payload = __PAYLOAD_JSON__;

      (function(){
        const wrapper = document.querySelector(".ceph-wrapper");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");
        const angleStack= document.getElementById("angle-stack");
        const coordStack= document.getElementById("coord-stack");

        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(angleRows.map(r => [r.dataset.angle, {row:r, valueEl:r.querySelector(".angle-value")}]))

        const markers=[], markerById={}, planeDefs=(payload.planes||[]), planeLines=[];
        let activeMarker=null, dragOffset={x:0,y:0};

        // ★ 追加: アクティブな pointer を追跡（2本指以上ならドラッグ禁止）
        const activePointers = new Set();
        let capturedPointerId = null;  // ★ mouse の時だけ保持

        const clamp=(v,lo,hi)=>Math.min(Math.max(v,lo),hi);
        const xy = m => (!m?null:{x:parseFloat(m.dataset.left||"0"), y:parseFloat(m.dataset.top||"0")});

        function syncAngleStackScale(){
          const base = ANGLE_STACK_BASE_WIDTH || 900;
          const w = image.clientWidth || base;
          const scale = Math.min(1, w / base);
          angleStack.style.transform = 'scale(' + scale + ')';
        }

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

        const angleCurrent=new Map();
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
            cache.set(cfg.id,v);
          });
        }

        function updateCoordStack(){
          const ids = Object.keys(markerById).sort();
          coordStack.innerHTML = ids.map(id=>{
            const m = markerById[id]; if(!m) return "";
            const x = Math.round(parseFloat(m.dataset.left||"0"));
            const y = Math.round(parseFloat(m.dataset.top||"0"));
            return `<div class="coord-item"><span>${id}</span><span>(${x}, ${y})</span></div>`;
          }).join("");
        }

        // ===== markers (thin triangles) =====
        function setPosition(m,left,top){
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const cl=Math.round(clamp(left,0,w));
          const ct=Math.round(clamp(top,0,h));
          m.style.left=cl+"px"; m.style.top=ct+"px"; m.dataset.left=cl; m.dataset.top=ct;
        }
        function createMarker(pt){
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s=pt.size||28;

          const pin=document.createElement("div"); pin.className="pin";
          pin.style.borderLeft=(s/4)+"px solid transparent";
          pin.style.borderRight=(s/4)+"px solid transparent";
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
            // preventDefault はしない（ピンチ阻害を避ける）
            if (ev.pointerType === "touch") {
              activePointers.add(ev.pointerId);
              // 2本指以上 → ピンチに委ね、ドラッグ開始しない
              if (activePointers.size >= 2) return;
              // 単指: capture しない（iOSでピンチと競合しにくい）
              capturedPointerId = null;
            } else if (ev.pointerType === "mouse") {
              m.setPointerCapture?.(ev.pointerId);
              capturedPointerId = ev.pointerId;
            }

            const rect=stage.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0"), top=parseFloat(m.dataset.top||"0");
            dragOffset={x:ev.clientX-(rect.left+left), y:ev.clientY-(rect.top+top)};
            activeMarker=m; m.classList.add("dragging");
          }, {passive:true});

          m.addEventListener("pointermove",(ev)=>{
            // 2本指以上が乗っている間は動かさない（＝ピンチ優先）
            if (activePointers.size >= 2) return;
            if(activeMarker!==m) return;
            const rect=stage.getBoundingClientRect();
            setPosition(m, ev.clientX-rect.left-dragOffset.x, ev.clientY-rect.top-dragOffset.y);
            updatePlanes(); updateAngleStack(); redrawPolygon(); updateCoordStack();
          }, {passive:true});

          const finish=(ev)=>{
            if (ev?.pointerType === "touch") {
              activePointers.delete(ev.pointerId);
            }
            if(activeMarker!==m) return;
            if (capturedPointerId!=null) {
              m.releasePointerCapture?.(capturedPointerId);  // ★ event 未定義バグを修正
              capturedPointerId = null;
            }
            m.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygon(); updateCoordStack();
          };
          m.addEventListener("pointerup", finish, {passive:true});
          m.addEventListener("pointercancel", finish, {passive:true});
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

        // ===== planes =====
        function initPlanes(){
          planesSvg.innerHTML=""; planeLines.length=0;
          (payload.planes||[]).forEach(pl=>{
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
          planeLines.forEach(pair=>{
            const pl = pair.plane, line = pair.line;
            const s=markerById[pl.start], e=markerById[pl.end];
            if(!s||!e){ line.style.opacity=0; return; }
            line.style.opacity=1;
            line.setAttribute("x1", s.dataset.left||"0"); line.setAttribute("y1", s.dataset.top||"0");
            line.setAttribute("x2", e.dataset.left||"0"); line.setAttribute("y2", e.dataset.top||"0");
          });
        }

        // ===== polygon =====
        function measureRowCentersMap(){
          const wrapRect = wrapper.getBoundingClientRect();
          const map = new Map();
          ANGLE_CONFIG.forEach(cfg=>{
            const entry=angleRowMap[cfg.id]; if(!entry) return;
            const r = entry.row.getBoundingClientRect();
            map.set(cfg.id, (r.top + r.height/2) - wrapRect.top);
          });
          return map;
        }

        function redrawPolygon(){
          if(!overlaySvg) return;
          const w=image.clientWidth||800, h=image.clientHeight||600;
          overlaySvg.setAttribute("viewBox","0 0 "+w+" "+h);
          const offsetX = Math.round(w*0.20) + 60;

          const centersMap = measureRowCentersMap();
          const ys = new Array(POLYGON_ROWS.length).fill(null);

          for(let i=0;i<POLYGON_ROWS.length;i++){
            const label = POLYGON_ROWS[i][0];
            if(label==="00"||label==="01"||label==="ZZ"||label==="VTOP"||label==="VBOT") continue;
            const cy = centersMap.get(label);
            if (typeof cy === "number") ys[i] = cy;
          }
          for(let i=0;i<ys.length;i++){
            if(ys[i]==null){
              let prev=null,next=null;
              for(let p=i-1;p>=0;p--){ if(ys[p]!=null){ prev=ys[p]; break; } }
              for(let n=i+1;n<ys.length;n++){ if(ys[n]!=null){ next=ys[n]; break; } }
              if(prev!=null && next!=null) ys[i]=(prev+next)/2;
              else if(prev!=null) ys[i]=prev+40;
              else if(next!=null) ys[i]=next-40;
              else ys[i]=Math.round(h*0.1);
            }
          }

          const gaps=[]; for(let i=1;i<ys.length;i++) gaps.push(Math.abs(ys[i]-ys[i-1]));
          const median = gaps.length? gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 24;
          const unit = Math.max(14, Math.round(median));

          const idxVTOP = POLYGON_ROWS.findIndex(r=>r[0]==="VTOP");
          const idxVBOT = POLYGON_ROWS.findIndex(r=>r[0]==="VBOT");
          let firstRealY=null, lastRealY=null;
          for(let i=0;i<POLYGON_ROWS.length;i++){
            const lb=POLYGON_ROWS[i][0];
            if(lb!=="00"&&lb!=="01"&&lb!=="ZZ"&&lb!=="VTOP"&&lb!=="VBOT"){ firstRealY = ys[i]; break; }
          }
          for(let i=POLYGON_ROWS.length-1;i>=0;i--){
            const lb=POLYGON_ROWS[i][0];
            if(lb!=="00"&&lb!=="01"&&lb!=="ZZ"&&lb!=="VTOP"&&lb!=="VBOT"){ lastRealY = ys[i]; break; }
          }
          if(idxVTOP>=0 && firstRealY!=null) ys[idxVTOP] = firstRealY - unit;
          if(idxVBOT>=0 && lastRealY!=null)  ys[idxVBOT] = lastRealY + unit;

          const yInt = ys.map(v=>Math.round(v));
          const offsetXInt = Math.round(offsetX);

          const spread = row => (row[3] * SD_BASE * POLY_WIDTH_SCALE * unit);
          const leftXs  = POLYGON_ROWS.map(row => Math.round(offsetX - spread(row)));
          const rightXs = POLYGON_ROWS.map(row => Math.round(offsetX + spread(row)));

          overlaySvg.innerHTML="";
          const g=document.createElementNS("http://www.w3.org/2000/svg","g");
          overlaySvg.appendChild(g);

          const pts=[];
          for(let i=0;i<POLYGON_ROWS.length;i++) pts.push(leftXs[i]+","+yInt[i]);
          for(let i=POLYGON_ROWS.length-1;i>=0;i--) pts.push(rightXs[i]+","+yInt[i]);
          const poly=document.createElementNS("http://www.w3.org/2000/svg","polygon");
          poly.setAttribute("id","std-poly-outline"); poly.setAttribute("points", pts.join(" "));
          g.appendChild(poly);

          const center=document.createElementNS("http://www.w3.org/2000/svg","line");
          center.setAttribute("x1",offsetXInt); center.setAttribute("x2",offsetXInt);
          center.setAttribute("y1",yInt[0]);   center.setAttribute("y2",yInt[yInt.length-1]);  // 同一整数座標
          center.setAttribute("class","std-centerline"); g.appendChild(center);

          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||"01"||"ZZ"||"VTOP"||"VBOT") return;
            const hl=document.createElementNS("http://www.w3.org/2000/svg","line");
            hl.setAttribute("x1", String(leftXs[i])); hl.setAttribute("x2", String(rightXs[i]));
            hl.setAttribute("y1", String(yInt[i]));   hl.setAttribute("y2", String(yInt[i]));
            hl.setAttribute("class","std-hline"); g.appendChild(hl);
          });

          // 患者 赤ポリライン（端点も整数）
          const patientPts=[];
          if(idxVTOP>=0) patientPts.push([offsetXInt, yInt[idxVTOP]]);
          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ"||label==="VTOP"||label==="VBOT") return;
            const mean=row[1], sd=row[2], ratio=row[3];
            const val = angleCurrent.get(label);
            if(!sd || !ratio || val==null || !isFinite(val)) return;
            const sd_px = ratio * SD_BASE * POLY_WIDTH_SCALE * unit;
            const x = Math.round(offsetX + ((val-mean)/sd) * sd_px);
            patientPts.push([x, yInt[i]]);
          });
          if(idxVBOT>=0) patientPts.push([offsetXInt, yInt[idxVBOT]]);
          if(patientPts.length>=2){
            const pl=document.createElementNS("http://www.w3.org/2000/svg","polyline");
            pl.setAttribute("class","std-patient");
            pl.setAttribute("points", patientPts.map(p=>p[0]+","+p[1]).join(" "));
            g.appendChild(pl);
          }
        }

        function updateLayout(){
          const w=image.clientWidth||0, h=image.clientHeight||0;
          stage.style.width=w+"px"; stage.style.height=h+"px";
          const base = ANGLE_STACK_BASE_WIDTH || 900;
          const scale = Math.min(1, (image.clientWidth||base)/base);
          angleStack.style.transform = 'scale(' + scale + ')';
          placeInitMarkersOnce(); initPlanes(); updatePlanes(); updateAngleStack(); redrawPolygon(); updateCoordStack();
        }

        window.addEventListener("pointerup", (ev)=>{
          if (ev?.pointerType === "touch") activePointers.delete(ev.pointerId);
          if(activeMarker){ activeMarker.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygon(); updateCoordStack(); }
        }, {passive:true});
        window.addEventListener("pointercancel", (ev)=>{
          if (ev?.pointerType === "touch") activePointers.delete(ev.pointerId);
          if(activeMarker){ activeMarker.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygon(); updateCoordStack(); }
        }, {passive:true});

        (payload.points||[]).forEach(pt=>createMarker(pt));
        if (image.complete && image.naturalWidth) updateLayout();
        else image.addEventListener("load", updateLayout, {once:true});
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
    html = html.replace("__ANGLE_STACK_BASE_WIDTH__", json.dumps(ANGLE_STACK_BASE_WIDTH))
    html = html.replace("__PAYLOAD_JSON__", payload_json)

    return components.html(html, height=1100, scrolling=False)

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
