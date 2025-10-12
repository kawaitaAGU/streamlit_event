# streamlit_event_fixed.py
import streamlit as st
from PIL import Image, ImageOps
import io, base64
import sys

st.set_page_config(page_title="背景+三角ドラッグ（Streamlit）", layout="wide")

st.title("📷 背景に画像を貼って、三角をドラッグ（PC: ドロップのみ / スマホ: 撮影 or 画像選択）")

# -----------------------
# 画像入力（PC=ドロップ推奨 / スマホ=撮影 or ファイル）
# -----------------------
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("PC／スマホ共通: 画像をドロップ or 選択")
    file = st.file_uploader("ここに画像をドロップ（または選択）", type=["jpg", "jpeg", "png", "webp", "gif"])

with col2:
    st.subheader("スマホ向け: カメラで撮影")
    cam_file = st.camera_input("ここをタップして撮影（iPhone/Android）")

# スマホではカメラ優先、無ければファイル
uploaded_file = cam_file if cam_file is not None else file

if not uploaded_file:
    st.info("画像をドロップ／選択、または（スマホなら）撮影してください。")
    st.stop()

# -----------------------
# 画像のEXIFを使った回転補正 & 圧縮
# -----------------------
def load_and_fix_image(uploaded) -> Image.Image:
    try:
        # StreamlitのUploadedFileは .read() できる
        data = uploaded.read()
        img = Image.open(io.BytesIO(data))
        # EXIFの向きを補正（iPhoneの縦横問題に対応）
        img = ImageOps.exif_transpose(img)
        # RGBAなどはJPEG不可のためRGBに
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return img
    except Exception as e:
        st.error(f"画像の読み込みに失敗しました: {e}")
        raise

img = load_and_fix_image(uploaded_file)

# 画像を大きすぎないサイズに縮小（長辺1600px程度）
MAX_LONG = 1600
w, h = img.size
scale = min(1.0, MAX_LONG / max(w, h))
if scale < 1.0:
    img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    w, h = img.size

# data URL 化（PNGで可逆、座標・回転済み）
buf = io.BytesIO()
img.save(buf, format="PNG")
data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

# -----------------------
# JS/CSSで背景と三角のドラッグUIをHTMLとして埋め込み
# -----------------------

container_height_vh = 72  # 表示領域の高さ（画面高に対する%）
triangle_base = 60        # 三角の基準サイズ（px）

html = f"""
<style>
  /* コンテナは画面幅いっぱい、高さは{container_height_vh}vh */
  .wrap {{
    position: relative;
    width: 100%;
    height: {container_height_vh}vh;
    background: #111;
    overflow: hidden;
    border-radius: 8px;
  }}
  /* 背景画像は常に全体が収まるように（左右上下のレターボックスOK） */
  .wrap > img#bg {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;       /* ← はみ出さずに収める */
    object-position: center center;
    display: block;
    z-index: 0;
    user-select: none;
    -webkit-user-drag: none;
    pointer-events: none;      /* 画像はポインタイベントを拾わない */
  }}
  /* ドラッグする舞台 */
  .stage {{
    position: absolute;
    inset: 0;
    z-index: 1;
    touch-action: none;  /* スクロールよりドラッグを優先（モバイル） */
  }}
  /* 座標HUDは右下へ退避（ボタンと被らないように） */
  .coords {{
    position: absolute;
    right: 8px;
    bottom: 8px;
    z-index: 2;
    background: rgba(0,0,0,.5);
    color: #66ccff;
    font: 14px/1.2 monospace;
    padding: 4px 8px;
    border-radius: 6px;
    user-select: none;
  }}
  .tri {{
    position: absolute; width: 0; height: 0;
    pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
  }}
  .tri:active {{ cursor: grabbing; }}
</style>

<div class="wrap" id="wrap">
  <img id="bg" src="{data_url}" alt="bg">
  <div id="stage" class="stage"></div>
  <div id="coords" class="coords">x: –, y: –</div>
</div>

<script>
(() => {{
  const stage = document.getElementById('stage');
  const coords = document.getElementById('coords');
  const wrap   = document.getElementById('wrap');

  // 端末サイズで三角の基本サイズを微調整（モバイルは少し小さめ）
  const isNarrow = window.matchMedia('(max-width: 600px)').matches;
  const BASE = {triangle_base} * (isNarrow ? 0.75 : 1.0);

  function makeTri(id, x, y, size, color) {{
    const el = document.createElement('div');
    el.className = 'tri';
    el.dataset.id = id;
    const s = size || BASE;
    el.style.borderLeft  = (s/2) + 'px solid transparent';
    el.style.borderRight = (s/2) + 'px solid transparent';
    el.style.borderBottom=  s     + 'px solid ' + (color || '#ff2a2a');
    el.style.left = (x||80) + 'px';
    el.style.top  = (y||80) + 'px';
    stage.appendChild(el);
    return el;
  }}

  // 初期三角（4つ）
  const tris = [
    {{id:'t1', x: 80,  y: 80,  size: BASE,     color:'#ff2a2a'}},
    {{id:'t2', x: 210, y: 150, size: BASE*0.9, color:'#2aff2a'}},
    {{id:'t3', x: 330, y: 100, size: BASE*0.8, color:'#2a9dff'}},
    {{id:'t4', x: 120, y: 240, size: BASE*1.1, color:'#ffd32a'}},
  ];
  tris.forEach(t => makeTri(t.id, t.x, t.y, t.size, t.color));

  // ドラッグ状態
  let drag = null;

  // ステージ上の移動で座標HUDをアップデート（ホバー中も更新）
  stage.addEventListener('pointermove', (e) => {{
    const rect = stage.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    coords.textContent = `x: ${Math.round(x)}, y: ${Math.round(y)}`;

    if (!drag) return;
    // ドラッグ対象の位置を更新（ステージ内に制限）
    const nx = Math.min(Math.max(0, e.clientX - rect.left - drag.dx), rect.width);
    const ny = Math.min(Math.max(0, e.clientY - rect.top  - drag.dy),  rect.height);
    drag.el.style.left = nx + 'px';
    drag.el.style.top  = ny + 'px';
  }});

  stage.addEventListener('pointerdown', (e) => {{
    const tri = e.target.closest('.tri');
    if (!tri) return;
    const rect = tri.getBoundingClientRect();
    drag = {{
      el: tri,
      dx: e.clientX - rect.left,
      dy: e.clientY - rect.top,
    }};
    try {{ tri.setPointerCapture(e.pointerId); }} catch(_) {{}}
    e.preventDefault();
  }});

  window.addEventListener('pointerup', (e) => {{
    if (drag) {{
      try {{ drag.el.releasePointerCapture(e.pointerId); }} catch(_) {{}}
      drag = null;
    }}
  }});
}})();
</script>
"""

st.components.v1.html(html, height=int(0.8 * st.session_state.get("viewport_h", 900)), scrolling=False)

# viewport 高さの推定（初回は既定値。必要ならJSで測ってsession_stateに入れる実装も可能）
