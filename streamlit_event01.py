# app.py
import base64
import io
from pathlib import Path

import streamlit as st
from PIL import Image
import streamlit.components.v1 as components

st.set_page_config(page_title="背景＋ドラッグ可能三角", layout="wide")

st.title("📷 背景に画像を貼って、三角をドラッグ")
st.caption("PC: ドラッグ&ドロップで画像を選択 / スマホ: カメラ撮影 or ファイル選択")

def pil_image_to_data_url(img: Image.Image, fmt: str = "JPEG", quality: int = 92) -> str:
    """PIL画像 -> dataURL（iPhoneでも安定）"""
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img = img.convert("RGB")  # 透過を避ける
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format=fmt)
        mime = f"image/{fmt.lower()}"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def render_stage(background_data_url: str | None):
    """背景dataURLを受け取り、三角をドラッグできるHTMLを埋め込む"""
    # Noneなら透明にする
    bg_src = background_data_url or ""
    html = f"""
    <style>
      html, body {{
        margin: 0; height: 100%; background:#111; overflow:hidden;
      }}
      /* 背景は <img> で敷く（iOSでも安定） */
      #bgimg {{
        position: fixed; inset: 0; width: 100%; height: 100%;
        object-fit: contain;  /* 画面に収める（重要: iPhoneで拡大しすぎない） */
        object-position: center center;
        z-index: 0;
        display: {'block' if bg_src else 'none'};
      }}
      #stage {{
        position: fixed; inset: 0; z-index: 1;
      }}
      #coords {{
        position: fixed; top: 8px; left: 8px;
        color: #66ccff; font: 14px/1.3 monospace;
        z-index: 3; background: rgba(0,0,0,.45);
        padding: 2px 6px; border-radius: 4px;
      }}
      .tri {{
        position: absolute; width: 0; height: 0;
        pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
      }}
      .tri:active {{ cursor: grabbing; }}

      /* スマホでボタン類が重なりにくいように余白 */
      .spacer {{
        height: 80px;
      }}
    </style>

    <img id="bgimg" alt="background" src="{bg_src}">
    <div id="stage"></div>
    <div id="coords">x: –, y: –</div>
    <div class="spacer"></div>

    <script>
    (function() {{
      const stage  = document.getElementById('stage');
      const coords = document.getElementById('coords');

      // 三角を作る
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

      // 初期三角（PCでもスマホでも共通）
      const tris = [
        {{id:'t1', x:120, y:120, size:70, color:'#ff2a2a'}},
        {{id:'t2', x:240, y:220, size:60, color:'#2aff2a'}},
        {{id:'t3', x:360, y:160, size:50, color:'#2a9dff'}},
        {{id:'t4', x:100, y:300, size:80, color:'#ffd32a'}},
      ];
      tris.forEach(t => makeTriangle(t.id, t.x, t.y, t.size, t.color));

      // ドラッグ（Pointer Events）
      let drag = null;
      stage.addEventListener('pointerdown', e => {{
        const tri = e.target.closest('.tri');
        if (!tri) return;
        const rect = tri.getBoundingClientRect();
        drag = {{ el: tri, dx: e.clientX - rect.left, dy: e.clientY - rect.top }};
        try {{ tri.setPointerCapture(e.pointerId); }} catch(_){{
          /* iOS Safari で setPointerCapture 未サポートでもOK */
        }}
        e.preventDefault();
      }});
      window.addEventListener('pointermove', e => {{
        if (!drag) return;
        const x = e.clientX - drag.dx;
        const y = e.clientY - drag.dy;
        drag.el.style.left = x + 'px';
        drag.el.style.top  = y + 'px';
        coords.textContent = `x:${{Math.round(x)}}, y:${{Math.round(y)}}`;
      }});
      window.addEventListener('pointerup', e => {{
        if (drag) {{ try {{ drag.el.releasePointerCapture(e.pointerId); }} catch(_){{}}; drag = null; }}
      }});
    }})();
    </script>
    """
    components.html(html, height=700, scrolling=False)

# ============ UI ============

tab_pc, tab_sp = st.tabs(["💻 PC（ドラッグ&ドロップ）", "📱 スマホ（カメラ or ファイル）"])

with tab_pc:
    st.subheader("PC: 画像をドラッグ&ドロップ")
    up_pc = st.file_uploader(
        "ここに画像をドラッグ&ドロップ（またはクリックして選択）",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        accept_multiple_files=False,
        label_visibility="visible",
    )
    bg_url_pc = None
    if up_pc is not None:
        try:
            img = Image.open(up_pc)
            # 画面に収めたいので、極端に大きい場合だけ軽く縮小（任意）
            img.thumbnail((2000, 2000))
            bg_url_pc = pil_image_to_data_url(img, fmt="JPEG", quality=90)
            st.success("画像を読み込みました。👇 下のステージに反映されます。")
        except Exception as e:
            st.error(f"画像の読み込みに失敗: {e}")

    render_stage(bg_url_pc)

with tab_sp:
    st.subheader("スマホ: カメラ撮影 または ファイル選択")
    col1, col2 = st.columns(2, gap="large")

    # 1) カメラ撮影（フロント/バックは端末の設定に依存）
    with col1:
        cam = st.camera_input("ここをタップして撮影（iPhone/Android）")
        bg_url_sp_cam = None
        if cam is not None:
            try:
                img_cam = Image.open(cam)
                # iPhoneで巨大になるのを防ぐ（containで見切れ対策）
                img_cam.thumbnail((2000, 2000))
                bg_url_sp_cam = pil_image_to_data_url(img_cam, fmt="JPEG", quality=90)
                st.success("撮影画像を読み込みました。👇 下のステージに反映されます。")
            except Exception as e:
                st.error(f"撮影画像の読み込みに失敗: {e}")

    # 2) ファイルから選択（iPhoneは写真ライブラリから選べる）
    with col2:
        up_sp = st.file_uploader(
            "ファイルから選択（写真ライブラリなど）",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=False,
            label_visibility="visible",
        )
        bg_url_sp_file = None
        if up_sp is not None:
            try:
                img_sp = Image.open(up_sp)
                img_sp.thumbnail((2000, 2000))
                bg_url_sp_file = pil_image_to_data_url(img_sp, fmt="JPEG", quality=90)
                st.success("画像を読み込みました。👇 下のステージに反映されます。")
            except Exception as e:
                st.error(f"画像の読み込みに失敗: {e}")

    # 優先順位: カメラ > ファイル
    bg_url_sp = bg_url_sp_cam or bg_url_sp_file
    render_stage(bg_url_sp)
