import streamlit as st
from streamlit.components.v1 import html

st.set_page_config(page_title="Triangles + Background", layout="wide")

# ---- HTML/CSS/JS をそのまま埋め込む ----
content = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
  html, body {
    margin: 0; height: 100%; background:#111; overflow:hidden;
    -webkit-tap-highlight-color: transparent;
  }
  /* コンテナ（iframe 内いっぱい） */
  #app {
    position: fixed; inset: 0;
  }
  /* 背景は <img> で敷く（iOS 安定）*/
  #bgimg {
    position: absolute; inset: 0; width: 100%; height: 100%;
    object-fit: contain;            /* ← モバイルは全体を収める */
    object-position: center center;
    z-index: 0; display: none;      /* 画像読み込みまで非表示 */
    background:#000;                /* 読み込み中の地 */
  }
  /* デスクトップは cover にして “広く見せる” */
  @media (min-width: 900px) {
    #bgimg { object-fit: cover; }
  }

  #stage { position: absolute; inset: 0; z-index: 1; }

  #coords {
    position: absolute; top: 10px; left: 10px;
    color: #66ccff; font: 14px/1.3 monospace;
    z-index: 3; background: rgba(0,0,0,.45);
    padding: 4px 8px; border-radius: 6px;
    pointer-events: none;
  }
  /* iPhone でも UI が被らないよう右上に少し余白を確保 */
  #uploader {
    position: absolute; right: 10px; top: 10px;
    z-index: 3; background: rgba(0,0,0,.6);
    color: #eee; font: 13px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    padding: 6px 8px; border-radius: 8px; border: 1px solid #333;
    display: flex; gap: 8px; align-items: center;
  }
  #dropzone {
    border: 1px dashed #666; padding: 4px 8px; border-radius: 6px;
    cursor: pointer; white-space: nowrap; user-select: none;
    background: rgba(255,255,255,.05);
  }

  .tri {
    position: absolute; width: 0; height: 0;
    pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,.6));
  }
  .tri:active { cursor: grabbing; }
</style>
</head>
<body>
<div id="app">
  <img id="bgimg" alt="background">
  <div id="stage"></div>

  <!-- 左上：座標表示（重ならないよう右上のUIとは逆側に置く） -->
  <div id="coords">x: –, y: –</div>

  <!-- 右上：画像選択（iPhone では “タップして選択” を使う） -->
  <div id="uploader">
    <label style="display:inline-flex; align-items:center; gap:8px;">
      <input id="fileInput" type="file" accept="image/*" capture="environment" style="display:none">
      <span id="dropzone">画像を選択 / ドロップ</span>
    </label>
  </div>
</div>

<script>
(function(){
  const bgimg = document.getElementById('bgimg');
  const stage = document.getElementById('stage');
  const coords = document.getElementById('coords');
  const fileInput = document.getElementById('fileInput');
  const dropzone  = document.getElementById('dropzone');

  const isiOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

  // ---------- 画像読込 ----------
  function setBackgroundSrc(src, revokeURL) {
    const test = new Image();
    test.onload = () => {
      bgimg.src = src;
      bgimg.style.display = 'block';
      // iOS では revoke しない（タイミングで消えることがある）
      if (revokeURL && !isiOS) requestAnimationFrame(() => { try { URL.revokeObjectURL(src); } catch(_){} });
    };
    test.onerror = () => {
      if (revokeURL && !isiOS) { try { URL.revokeObjectURL(src); } catch(_){} }
      alert('画像の読み込みに失敗しました。別の画像をお試しください。');
    };
    test.src = src;
  }

  function readAsDataURL(file) {
    const reader = new FileReader();
    reader.onload = e => setBackgroundSrc(e.target.result, /*revoke*/ false);
    reader.onerror = () => alert('画像の読み込みに失敗しました。');
    reader.readAsDataURL(file);
  }

  function applyFile(file) {
    if (!file) return;
    if (isiOS) {
      // iPhone は DataURL が安定
      readAsDataURL(file);
    } else {
      try {
        const url = URL.createObjectURL(file);
        setBackgroundSrc(url, /*revoke*/ true);
      } catch {
        readAsDataURL(file);
      }
    }
  }

  dropzone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (ev) => applyFile(ev.target.files && ev.target.files[0]));

  // Desktop では D&D 可能（iOS Safari は不可）
  ['dragenter','dragover','dragleave','drop'].forEach(evt => {
    window.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); }, false);
  });
  window.addEventListener('drop', e => applyFile(e.dataTransfer.files && e.dataTransfer.files[0]));

  // ---------- 三角形（レスポンシブサイズ） ----------
  function baseSize() {
    // 画面の短辺の 8%（36〜120pxの範囲）
    const s = Math.min(window.innerWidth, window.innerHeight) * 0.08;
    return Math.max(36, Math.min(120, Math.floor(s)));
  }

  function makeTriangle(id, x, y, size, color) {
    const el = document.createElement('div');
    el.className = 'tri';
    el.dataset.id = id;
    const b = size;
    el.style.borderLeft   = (b/2) + 'px solid transparent';
    el.style.borderRight  = (b/2) + 'px solid transparent';
    el.style.borderBottom = b + 'px solid ' + color;
    el.style.left = x + 'px';
    el.style.top  = y + 'px';
    stage.appendChild(el);
    return el;
  }

  function layoutTriangles() {
    stage.innerHTML = ''; // いったん消す（シンプルな再配置）
    const s = baseSize();
    const tris = [
      {id:'t1', x: s*1.8,  y: s*1.6,  size: s,     color:'#ff2a2a'},
      {id:'t2', x: s*3.2,  y: s*2.8,  size: s*0.9, color:'#2aff2a'},
      {id:'t3', x: s*4.6,  y: s*2.0,  size: s*0.8, color:'#2a9dff'},
      {id:'t4', x: s*1.4,  y: s*3.8,  size: s*1.1, color:'#ffd32a'},
    ];
    tris.forEach(t => makeTriangle(t.id, Math.round(t.x), Math.round(t.y), Math.round(t.size), t.color));
  }

  layoutTriangles();
  window.addEventListener('resize', layoutTriangles);

  // ---------- ドラッグ（Pointer Events） ----------
  let drag = null;
  stage.addEventListener('pointerdown', e => {
    const tri = e.target.closest('.tri');
    if (!tri) return;
    const rect = tri.getBoundingClientRect();
    drag = { el: tri, dx: e.clientX - rect.left, dy: e.clientY - rect.top };
    try { tri.setPointerCapture(e.pointerId); } catch(_) {}
    e.preventDefault();
  });
  window.addEventListener('pointermove', e => {
    if (!drag) return;
    const x = e.clientX - drag.dx;
    const y = e.clientY - drag.dy;
    drag.el.style.left = x + 'px';
    drag.el.style.top  = y + 'px';
    coords.textContent = `x:${Math.round(x)}, y:${Math.round(y)}`;
  });
  window.addEventListener('pointerup', e => {
    if (drag) { try { drag.el.releasePointerCapture(e.pointerId); } catch(_){}; drag = null; }
  });

})();
</script>
</body>
</html>
"""

# コンポーネント描画（高さはビュー高に近い値に）
# スマホでも余白なく全画面にしたいので 92vh 相当を指定
html(content, height=800, scrolling=False)
