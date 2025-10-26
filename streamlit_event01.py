# CEF39_fixed.py — single-canvas, safe JS embedding, pinch-zoom, thin triangles,
# polygon with top/bottom apex points, white outline, no red dots,
# apex connected to Facial & L1-FH shoulders.

import json
import streamlit as st
import streamlit.components.v1 as components
import CEF03 as base  # 画像/ポイント/プレーンのヘルパーだけ利用（mainは呼ばない）

# ===== スケール設定 =====
SD_BASE = 4.0                 # sd_ratio -> px 変換の基礎
POLY_WIDTH_SCALE = 2.0        # ポリゴン横幅を2倍
ANGLE_STACK_BASE_WIDTH = 900  # 角度カラムのスケール基準となる画像幅(px)

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

# ===== ポリゴン行 =====
# 00/ZZ: 従来のダミー。01: くびれ用中点ダミー。
# 今回さらに VTOP / VBOT を最上・最下のダミー点として追加（幅0の頂点）
POLYGON_ROWS = [
    ["VTOP", 0.0, 0.0, 0.0],               # 新: 最上の頂点（幅なし）
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
    ["01", 0.0, 0.0, 0.0],                  # くびれ中点（ダミー）
    ["Interincisal", 124.3, 6.9, 0.2500],
    ["U1 to FH plane", 109.8, 5.3, 0.1679],
    ["L1 to Mandibular", 93.8, 5.9, 0.2107],
    ["L1_FH", 57.2, 3.9, 0.2500],
    ["ZZ", 0.0, 0.0, 0.0],
    ["VBOT", 0.0, 0.0, 0.0],               # 新: 最下の頂点（幅なし）
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
      .ceph-wrapper{position:relative;width:min(100%,960px);margin:0 auto;}
      #ceph-image{width:100%;height:auto;display:block;pointer-events:none;user-select:none;-webkit-user-select:none;}

      #ceph-planes{position:absolute;inset:0;pointer-events:none;z-index:1;}
      #ceph-overlay{position:absolute;inset:0;pointer-events:none;z-index:2;}
      /* ピンチズーム許可（iOSでも拡大可）。ドラッグはマーカー自身で扱う */
      #ceph-stage{position:absolute;inset:0;pointer-events:auto;z-index:3;touch-action:pinch-zoom;}

      #angle-stack{
        position:absolute;top:56px;left:12px;
        display:flex;flex-direction:column;gap:10px;
        padding:10px 12px;border-radius:10px;
        background:rgba(15,23,42,.78);color:#f8fafc;
        font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
        pointer-events:none;z-index:4;min-width:140px;
        transform-origin:top left;transform:scale(1);
      }
      .angle-row{display:flex;justify-content:space-between;align-items:center;padding:2px 0;}
      .angle-row.dimmed{opacity:.45;}
      .angle-name,.angle-value{font-size:13px;font-weight:600;}

      /* ポリゴン類（白枠／補助線も白） */
      #std-poly-outline{fill:none;stroke:#ffffff;stroke-width:1.6;stroke-opacity:.95;}
      .std-centerline{stroke:#facc15;stroke-width:2;}
      .std-hline{stroke:#ffffff;stroke-width:1.1;}
      .std-helper{stroke:#ffffff;stroke-width:1.4;} /* 最上/最下の肩を結ぶ補助線 */

      /* 三角マーカー（底辺1/2を維持） */
      .ceph-marker{position:absolute;transform:translate(-50%,0);cursor:grab;touch-action:none;}
      .ceph-marker.dragging{cursor:grabbing;}
      .ceph-marker .pin{width:0;height:0;margin:0 auto;}
      /* 底辺 (=左右の透明ボーダー) を半分に：s/4 + s/4 */
      .ceph-marker .pin[data-size]{
        /* JS側でサイズ個別指定するのでここはダミー */
      }
      .ceph-label{margin-top:2px;font-size:11px;font-weight:700;color:#f8fafc;text-shadow:0 1px 2px rgba(0,0,0,.6);text-align:center;}
    </style>

    <div class="ceph-wrapper">
      <img id="ceph-image" src="__IMAGE_DATA_URL__" alt="cephalometric background"/>
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
      const ANGLE_STACK_BASE_WIDTH = __ANGLE_STACK_BASE_WIDTH__;
      const payload = __PAYLOAD_JSON__;

      (function(){
        const wrapper = document.querySelector(".ceph-wrapper");
        const image   = document.getElementById("ceph-image");
        const stage   = document.getElementById("ceph-stage");
        const planesSvg = document.getElementById("ceph-planes");
        const overlaySvg= document.getElementById("ceph-overlay");
        const angleStack= document.getElementById("angle-stack");

        const angleRows = Array.from(document.querySelectorAll("#angle-stack .angle-row"));
        const angleRowMap = Object.fromEntries(angleRows.map(r => [r.dataset.angle, {row:r, valueEl:r.querySelector(".angle-value")}]))

        const markers=[], markerById={}, planeDefs=(payload.planes||[]), planeLines=[];
        let activeMarker=null, dragOffset={x:0,y:0};

        const clamp=(v,lo,hi)=>Math.min(Math.max(v,lo),hi);
        const xy = m => (!m?null:{x:parseFloat(m.dataset.left||"0"), y:parseFloat(m.dataset.top||"0")});

        // 角度カラムのスケーリング（テンプレ文字列は使わない）
        function syncAngleStackScale(){
          const base = ANGLE_STACK_BASE_WIDTH || 900;
          const w = image.clientWidth || base;
          const scale = Math.min(1, w / base);
          angleStack.style.transform = 'scale(' + scale + ')';
        }

        // 角度計算
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

        // マーカー
        function setPosition(m,left,top){
          const w=stage.clientWidth||1,h=stage.clientHeight||1;
          const cl=clamp(left,0,w), ct=clamp(top,0,h);
          m.style.left=cl+"px"; m.style.top=ct+"px"; m.dataset.left=cl; m.dataset.top=ct;
        }

        function createMarker(pt){
          const m=document.createElement("div"); m.className="ceph-marker"; m.dataset.id=pt.id;
          const s=pt.size||28;

          // 底辺を半分に（左右透明ボーダーを s/4 ずつ）
          const pin=document.createElement("div"); pin.className="pin"; pin.setAttribute("data-size", String(s));
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
            // ピンチズーム中の誤作動防止：2本指ならドラッグ開始しない
            if (ev.pointerType === 'touch' && ev.width && ev.height && (ev.pressure===0 || ev.isPrimary===false)) return;
            const rect=stage.getBoundingClientRect();
            const left=parseFloat(m.dataset.left||"0"), top=parseFloat(m.dataset.top||"0");
            dragOffset={x:ev.clientX-(rect.left+left), y:ev.clientY-(rect.top+top)};
            activeMarker=m; m.classList.add("dragging"); ev.preventDefault();
          });
          m.addEventListener("pointermove",(ev)=>{
            if(activeMarker!==m) return;
            const rect=stage.getBoundingClientRect();
            setPosition(m, ev.clientX-rect.left-dragOffset.x, ev.clientY-rect.top-dragOffset.y);
            updatePlanes(); updateAngleStack(); redrawPolygonAndLines();
          });
          const finish=()=>{
            if(activeMarker!==m) return;
            m.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygonAndLines();
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

        // プレーン
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
          planeLines.forEach((pair)=>{
            const plane = pair.plane;
            const line  = pair.line;
            const s=markerById[plane.start], e=markerById[plane.end];
            if(!s||!e){ line.style.opacity=0; return; }
            line.style.opacity=1;
            line.setAttribute("x1", s.dataset.left||"0"); line.setAttribute("y1", s.dataset.top||"0");
            line.setAttribute("x2", e.dataset.left||"0"); line.setAttribute("y2", e.dataset.top||"0");
          });
        }

        // 角度カラム行の中心Y（scale適用後の見た目に基づく）
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

        // ポリゴン（白枠）＋ 補助線（白）※赤丸は廃止
        function redrawPolygonAndLines(){
          if(!overlaySvg) return;
          const w=image.clientWidth||800, h=image.clientHeight||600;
          overlaySvg.setAttribute("viewBox","0 0 "+w+" "+h);
          const offsetX = Math.round(w*0.20) + 60;

          const centersMap = measureRowCentersMap();
          const ys = [];
          for(let i=0;i<POLYGON_ROWS.length;i++){
            const label = POLYGON_ROWS[i][0];

            if(label==="01"){
              // 中点
              let prevY=null, nextY=null;
              for(let p=i-1;p>=0;p--){
                const lab=POLYGON_ROWS[p][0];
                if(lab!=="00" && lab!=="01" && lab!=="ZZ" && lab!=="VTOP" && lab!=="VBOT" && centersMap.has(lab)){ prevY=centersMap.get(lab); break; }
              }
              for(let n=i+1;n<POLYGON_ROWS.length;n++){
                const lab=POLYGON_ROWS[n][0];
                if(lab!=="00" && lab!=="01" && lab!=="ZZ" && lab!=="VTOP" && lab!=="VBOT" && centersMap.has(lab)){ nextY=centersMap.get(lab); break; }
              }
              let mid=Math.round(h*0.5);
              if(prevY!=null && nextY!=null) mid=(prevY+nextY)/2;
              else if(prevY!=null) mid=prevY+40;
              else if(nextY!=null) mid=nextY-40;
              ys.push(mid);

            } else if(label==="VTOP" || label==="VBOT"){
              // 最上/最下の頂点：実データの最初と最後から一定距離
              // ここでは間隔の中央値から推定して ±1ユニット外側に配置
              // （下で unit を計算後に改めて補正するため、仮置き→後で再配置）
              ys.push(null);

            } else if(label==="00" || label==="ZZ"){
              if(ys.length===0){
                let firstRealY=null;
                for(let n=i+1;n<POLYGON_ROWS.length;n++){
                  const lab=POLYGON_ROWS[n][0];
                  if(lab!=="00" && lab!=="01" && lab!=="ZZ" && lab!=="VTOP" && lab!=="VBOT" && centersMap.has(lab)){ firstRealY=centersMap.get(lab); break; }
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

          // unit 算出
          const gaps=[]; for(let i=1;i<ys.length;i++){ if(ys[i]!=null && ys[i-1]!=null) gaps.push(Math.abs(ys[i]-ys[i-1])); }
          const median = gaps.length? gaps.sort((a,b)=>a-b)[Math.floor(gaps.length/2)] : 24;
          const unit = Math.max(14, Math.round(median));

          // VTOP/VBOT の再配置（最初/最後の実データ行から1ユニット外側）
          const idxFacial = POLYGON_ROWS.findIndex(r=>r[0]==="Facial");
          const idxL1FH   = POLYGON_ROWS.findIndex(r=>r[0]==="L1_FH");
          const idxVTOP   = POLYGON_ROWS.findIndex(r=>r[0]==="VTOP");
          const idxVBOT   = POLYGON_ROWS.findIndex(r=>r[0]==="VBOT");

          if (idxVTOP>=0){
            // Facial のYが基準。なければ最初の実データ行のY
            let firstRealY = null;
            for(let n=0;n<POLYGON_ROWS.length;n++){
              const lab=POLYGON_ROWS[n][0];
              if(lab!=="00"&&lab!=="01"&&lab!=="ZZ"&&lab!=="VTOP"&&lab!=="VBOT" && ys[n]!=null){ firstRealY=ys[n]; break; }
            }
            if(firstRealY==null) firstRealY = Math.round(h*0.15);
            ys[idxVTOP] = firstRealY - unit;
          }
          if (idxVBOT>=0){
            let lastRealY = null;
            for(let n=POLYGON_ROWS.length-1;n>=0;n--){
              const lab=POLYGON_ROWS[n][0];
              if(lab!=="00"&&lab!=="01"&&lab!=="ZZ"&&lab!=="VTOP"&&lab!=="VBOT" && ys[n]!=null){ lastRealY=ys[n]; break; }
            }
            if(lastRealY==null) lastRealY = Math.round(h*0.85);
            ys[idxVBOT] = lastRealY + unit;
          }

          // 横方向スプレッド
          const spread = row => (row[3] * SD_BASE * POLY_WIDTH_SCALE * unit);
          const leftXs  = POLYGON_ROWS.map(row => offsetX - spread(row));
          const rightXs = POLYGON_ROWS.map(row => offsetX + spread(row));

          overlaySvg.innerHTML="";
          const g=document.createElementNS("http://www.w3.org/2000/svg","g");
          overlaySvg.appendChild(g);

          // 外形ポリゴン（白枠）
          const pts=[];
          for(let i=0;i<POLYGON_ROWS.length;i++) pts.push(leftXs[i]+","+ys[i]);
          for(let i=POLYGON_ROWS.length-1;i>=0;i--) pts.push(rightXs[i]+","+ys[i]);
          const poly=document.createElementNS("http://www.w3.org/2000/svg","polygon");
          poly.setAttribute("id","std-poly-outline"); poly.setAttribute("points", pts.join(" "));
          g.appendChild(poly);

          // 中心線（ダミーも含め最上〜最下まで）
          const center=document.createElementNS("http://www.w3.org/2000/svg","line");
          center.setAttribute("x1",offsetX); center.setAttribute("x2",offsetX);
          center.setAttribute("y1",ys[0]); center.setAttribute("y2",ys[ys.length-1]);
          center.setAttribute("class","std-centerline"); g.appendChild(center);

          // 水平白線（実データ行のみ）
          POLYGON_ROWS.forEach((row,i)=>{
            const label=row[0]; if(label==="00"||label==="01"||label==="ZZ"||label==="VTOP"||label==="VBOT") return;
            const hl=document.createElementNS("http://www.w3.org/2000/svg","line");
            hl.setAttribute("x1", String(leftXs[i])); hl.setAttribute("x2", String(rightXs[i]));
            hl.setAttribute("y1", String(ys[i]));     hl.setAttribute("y2", String(ys[i]));
            hl.setAttribute("class","std-hline"); g.appendChild(hl);
          });

          // 補助線：最上頂点 ↔ Facial 肩
          if (idxVTOP>=0 && idxFacial>=0){
            const l1=document.createElementNS("http://www.w3.org/2000/svg","line");
            l1.setAttribute("x1", String(offsetX));   l1.setAttribute("y1", String(ys[idxVTOP]));
            l1.setAttribute("x2", String(leftXs[idxFacial])); l1.setAttribute("y2", String(ys[idxFacial]));
            l1.setAttribute("class","std-helper"); g.appendChild(l1);

            const l2=document.createElementNS("http://www.w3.org/2000/svg","line");
            l2.setAttribute("x1", String(offsetX));   l2.setAttribute("y1", String(ys[idxVTOP]));
            l2.setAttribute("x2", String(rightXs[idxFacial])); l2.setAttribute("y2", String(ys[idxFacial]));
            l2.setAttribute("class","std-helper"); g.appendChild(l2);
          }

          // 補助線：最下頂点 ↔ L1-FH 肩
          if (idxVBOT>=0 && idxL1FH>=0){
            const l3=document.createElementNS("http://www.w3.org/2000/svg","line");
            l3.setAttribute("x1", String(offsetX));   l3.setAttribute("y1", String(ys[idxVBOT]));
            l3.setAttribute("x2", String(leftXs[idxL1FH])); l3.setAttribute("y2", String(ys[idxL1FH]));
            l3.setAttribute("class","std-helper"); g.appendChild(l3);

            const l4=document.createElementNS("http://www.w3.org/2000/svg","line");
            l4.setAttribute("x1", String(offsetX));   l4.setAttribute("y1", String(ys[idxVBOT]));
            l4.setAttribute("x2", String(rightXs[idxL1FH])); l4.setAttribute("y2", String(ys[idxL1FH]));
            l4.setAttribute("class","std-helper"); g.appendChild(l4);
          }
        }

        // レイアウト
        function updateLayout(){
          const w=image.clientWidth||0, h=image.clientHeight||0;
          stage.style.width=w+"px"; stage.style.height=h+"px";
          syncAngleStackScale();
          placeInitMarkersOnce(); initPlanes(); updatePlanes(); updateAngleStack(); redrawPolygonAndLines();
        }

        window.addEventListener("pointerup", ()=>{
          if(activeMarker){ activeMarker.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygonAndLines(); }
        });
        window.addEventListener("pointercancel", ()=>{
          if(activeMarker){ activeMarker.classList.remove("dragging"); activeMarker=null;
            updatePlanes(); updateAngleStack(); redrawPolygonAndLines(); }
        });

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

# ── 余分なサイドバーは出さない最小UI ──
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
