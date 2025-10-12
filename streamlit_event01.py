# streamlit_triangles.py
import streamlit as st
from PIL import Image
import base64, io, mimetypes

st.set_page_config(page_title="📸 背景画像＋三角ドラッグ（Streamlit）", layout="wide")

st.title("📸 背景画像＋ドラッグ三角（iPhone OK / Streamlit）")

# ------------------ 画像の入力（カメラ or ファイル） ------------------
col1, col2 = st.columns(2)
with col1:
    cam = st.camera_input("カメラで撮影（iPhone対応）")
with col2:
    up = st.file_uploader("画像をアップロード（JPEG/PNG/WebP/GIF）", type=["jpg","jpeg","png","webp","gif"])

def file_to_data_url(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    # そのまま bytes 取得
    data = uploaded_file.read()
    # MIME 推定
    mime = getattr(uploaded_file, "type", None)
    if not mime:
        mime, _ = mimetypes.guess_type(uploaded_file.name or "")
        if mime is None:
            # PIL でフォールバック
            try:
                im = Image.open(io.BytesIO(data))
                fmt = (im.format or "JPEG").lower()
                mime = f"image/{'jpeg' if fmt == 'jpg' else fmt}"
            except Exception:
                mime = "image/jpeg"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"

# camera > uploader の優先順
src_data_url = file_to_data_url(cam) or file_to_data_url(up)

if src_data_url:
    st.success("✅ 背景画像を受け取りました。アプリ領域に反映します。")
else:
    st.info("⬆️ カメラ撮影 または 画像アップロードを行うと背景に設定されます。")

# ------------------ 埋め込み HTML / JS（ドラッグ三角 & 座標表示） ------------------
# iPhone でも安定するよう <img id="bgimg"> に data URL を入れて表示
# 三角は CSS ボーダーで描画、Pointer Events でドラッグ
html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0; padding: 0; height: 100%; background: #111; overflow: hidden;
  }}
  /* 背景は <img> で全面に敷く（iOS 安定） */
  #bgimg {{
    position: fixed; inset: 0; width: 100vw; height: 100vh;
    object-fit: cover; object-position: center center;
    z-index: 0; {"display:block;" if src_data_url else "display:none;"} 
  }}
  /* アプリ領域 */
  #stage {{
    position: fixed; inset: 0; z-index: 1;
    touch-action: none;  /* iOSの二本指スクロール等でドラッグが切れないように */
  }}
  /* 座標表示 */
  #coords {{
    position: fixed; left: 12px; top: 12px; z-index: 3;
    color: #66ccff; font: 14px/1.3 monospace;
    background: rgba(0,0,0,0.5); padding: 4px 8px; border-radius: 6px;
    user-select: none; -webkit-user-select: none;
  }}
  /* 三角：CSS の border で描く */
  .tri {{
    position: absolute; width: 0; height: 0;
    pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
  }}
  .tri:active {{ cursor: grabbing; }}
</style>
</head>
<body>
  <img id="bgimg" alt="background" src="{src_data_url or ''}">
  <div id="stage"></div>
  <div id="coords">x: –, y: –</div>

<script>
(function() {{
  const stage  = document.getElementById('stage');
  const coords = document.getElementById('coords');

  // 三角生成
  function makeTriangle(id, x, y, size=80, color='#ff2a2a') {{
    const el = document.createElement('div');
    el.className = 'tri';
    el.dataset.id = id;
    el.style.borderLeft = (size/2) + 'px solid transparent';
    el.style.borderRight = (size/2) + 'px solid transparent';
    el.style.borderBottom = size + 'px solid ' + color;
    el.style.left = x + 'px';
    el.style.top  = y + 'px';
    stage.appendChild(el);
    return el;
  }}

  // 初期三角（4つ）
  const tris = [
    {{id:'t1', x:120, y:120, size:80, color:'#ff2a2a'}},
    {{id:'t2', x:240, y:220, size:70, color:'#2aff2a'}},
    {{id:'t3', x:360, y:160, size:60, color:'#2a9dff'}},
    {{id:'t4', x:100, y:300, size:90, color:'#ffd32a'}},
  ];
  tris.forEach(t => makeTriangle(t.id, t.x, t.y, t.size, t.color));

  // ドラッグ処理（Pointer Events）
  let drag = null;

  stage.addEventListener('pointerdown', (e) => {{
    const tri = e.target.closest('.tri');
    if (!tri) return;
    const rect = tri.getBoundingClientRect();
    drag = {{
      el: tri,
      dx: e.clientX - rect.left,
      dy: e.clientY - rect.top
    }};
    try {{ tri.setPointerCapture(e.pointerId); }} catch(_) {{}}
    e.preventDefault();
  }});

  window.addEventListener('pointermove', (e) => {{
    if (!drag) return;
    const x = e.clientX - drag.dx;
    const y = e.clientY - drag.dy;
    drag.el.style.left = x + 'px';
    drag.el.style.top  = y + 'px';
    coords.textContent = `x: ${{Math.round(x)}}, y: ${{Math.round(y)}}`;
  }});

  window.addEventListener('pointerup', (e) => {{
    if (drag) {{
      try {{ drag.el.releasePointerCapture(e.pointerId); }} catch(_) {{}}
      drag = null;
    }}
  }});
}})();
</script>
</body>
</html>
"""

# 画面全体を使うので高さは大きめを指定（スマホでも余裕を持たせる）
st.components.v1.html(html, height=850, scrolling=False)
