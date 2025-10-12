# streamlit_app.py
import base64
from io import BytesIO
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="背景＋ドラッグ三角（Streamlit）", layout="wide")

st.title("📷 背景に写真を貼って、三角をドラッグ（iPhone対応版）")

st.caption("上で写真を撮影 / 画像を選択 → 下のキャンバスに反映されます（iPhone対応: フェード表示 & HEIC対策）。")

# ------------------------------
# 画像を dataURL(base64) に変換
# ------------------------------
def pil_to_data_url(pil_img: Image.Image, fmt: str = "JPEG", quality=92) -> str:
    buf = BytesIO()
    # iPhoneのHEICなどを含め、最終的にJPEG/WebP/PNGに正規化するのが安定
    if fmt.upper() == "JPEG":
        pil_img = pil_img.convert("RGB")
        pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    elif fmt.upper() == "WEBP":
        pil_img.save(buf, format="WEBP", quality=quality, method=6)
        mime = "image/webp"
    else:
        pil_img.save(buf, format="PNG")
        mime = "image/png"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"

# ------------------------------
# 画像入力（撮影 / アップロード）
# ------------------------------
col1, col2 = st.columns(2)
with col1:
    cam = st.camera_input("📸 ここで撮影（iPhoneでもOK）", label_visibility="visible")
with col2:
    up = st.file_uploader("🖼️ 画像を選択（JPEG/PNG/WEBP/HEIC可）", type=["jpg", "jpeg", "png", "webp", "heic", "heif"])

data_url = None

# ファイルから PIL 読み込み（HEIC/HEIF は pillow-heif がある場合に扱える想定）
def file_to_pil(file) -> Image.Image | None:
    if file is None:
        return None
    try:
        # まずPILで頑張って開く
        img = Image.open(file)
        img.load()
        return img
    except Exception:
        # pillow-heif が入っていれば HEIC も読める
        try:
            import pillow_heif
            file.seek(0)
            heif = pillow_heif.read_heif(file.read())
            img = Image.frombytes(
                heif.mode, heif.size, heif.data, "raw"
            )
            return img
        except Exception:
            return None

# 優先順位: camera_input -> uploader
src_img = None
if cam is not None:
    # cam は UploadedFile （画像バイナリ）
    src_img = file_to_pil(cam)
elif up is not None:
    src_img = file_to_pil(up)

if src_img is not None:
    # 画面に収めやすいように大きすぎる画像は縮小（iPhoneの超高解像度対策）
    max_w = 1600
    if src_img.width > max_w:
        ratio = max_w / src_img.width
        src_img = src_img.resize((max_w, int(src_img.height * ratio)))
    # iPhoneでの発色/互換重視で JPEG に正規化
    data_url = pil_to_data_url(src_img, fmt="JPEG", quality=92)

# ---------------------------------------
# HTML 側（ドラッグ三角 & 背景フェード表示）
# ---------------------------------------
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0; height: 100%; overflow: hidden; background: #111;
  }}
  /* 背景は常にDOMに存在させる（display:noneは使わない） */
  #bgimg {{
    position: fixed; inset: 0; width: 100%; height: 100%;
    object-fit: contain;               /* ← iPhoneで拡大し過ぎない */
    object-position: center center;
    z-index: 0;
    opacity: 0;                        /* フェード用: 0 → 1 */
    transition: opacity .35s ease;
    background: #000;
    display: block;
    touch-action: none;
  }}
  #stage {{
    position: fixed; inset: 0; z-index: 1; pointer-events: auto;
  }}
  #hud {{
    position: fixed; top: 10px; left: 10px; z-index: 2;
    color: #66ccff; font: 14px/1.3 monospace;
    background: rgba(0,0,0,.45);
    padding: 4px 8px; border-radius: 4px;
    user-select: none;
  }}
  .tri {{
    position: absolute; width: 0; height: 0;
    pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
  }}
  .tri:active {{ cursor: grabbing; }}
</style>
</head>
<body>
  <img id="bgimg" alt="bg">
  <div id="stage"></div>
  <div id="hud">x: –, y: –</div>

  <script>
  (function() {{
    const bgimg = document.getElementById('bgimg');
    const stage = document.getElementById('stage');
    const hud   = document.getElementById('hud');
    const isiOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

    // Python から埋め込んだ dataURL（無ければ空文字）
    const injectedSrc = {repr(data_url)};

    function setBackgroundSrc(src) {{
      if (!src) return;
      bgimg.style.opacity = 0; // フェードアウト
      const test = new Image();
      test.onload = () => {{
        bgimg.src = src;
        // 次フレームでフェードイン（Safariでの再描画トリガ）
        requestAnimationFrame(() => {{
          bgimg.style.opacity = 1;
        }});
      }};
      test.onerror = () => {{
        alert('画像の読み込みに失敗しました。');
      }};
      test.src = src;
    }}

    if (injectedSrc) {{
      // iPhoneでも安定。dataURL なので revoke 不要
      setBackgroundSrc(injectedSrc);
    }}

    // 三角の生成：iPhoneでは少し小さめで配置
    const scale = isiOS ? 0.8 : 1.0;
    function makeTri(id, x, y, size, color) {{
      const el = document.createElement('div');
      el.className = 'tri';
      const s = size * scale;
      el.style.borderLeft = (s/2) + 'px solid transparent';
      el.style.borderRight = (s/2) + 'px solid transparent';
      el.style.borderBottom = s + 'px solid ' + color;
      el.style.left = x + 'px';
      el.style.top  = y + 'px';
      stage.appendChild(el);
      return el;
    }}

    const tris = [
      {{id:'t1', x:120, y:120, size:80, color:'#ff2a2a'}},
      {{id:'t2', x:260, y:220, size:70, color:'#2aff2a'}},
      {{id:'t3', x:400, y:160, size:60, color:'#2a9dff'}},
      {{id:'t4', x:140, y:320, size:90, color:'#ffd32a'}},
    ];
    tris.forEach(t => makeTri(t.id, t.x, t.y, t.size, t.color));

    // ドラッグ（Pointer Events）
    let drag = null;
    stage.addEventListener('pointerdown', e => {{
      const tri = e.target.closest('.tri');
      if (!tri) return;
      const rect = tri.getBoundingClientRect();
      drag = {{ el: tri, dx: e.clientX - rect.left, dy: e.clientY - rect.top }};
      try {{ tri.setPointerCapture(e.pointerId); }} catch(_){{}}
      e.preventDefault();
    }});
    window.addEventListener('pointermove', e => {{
      if (!drag) return;
      const x = e.clientX - drag.dx;
      const y = e.clientY - drag.dy;
      drag.el.style.left = x + 'px';
      drag.el.style.top  = y + 'px';
      hud.textContent = `x: ${{Math.round(x)}}, y: ${{Math.round(y)}}`;
    }});
    window.addEventListener('pointerup', e => {{
      if (drag) {{ try {{ drag.el.releasePointerCapture(e.pointerId); }} catch(_){{}}; drag = null; }}
    }});
  }})();
  </script>
</body>
</html>
"""

# 画面（下部）に埋め込み
components.html(html, height=720, scrolling=False)
