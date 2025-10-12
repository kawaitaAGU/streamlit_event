# app.py
import base64
import io
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="背景→三角（順序固定）", layout="wide")

st.title("📷 まず背景画像を決めてから → 三角をドラッグ")
st.caption("・PC: 画像はドラッグ&ドロップのみ / スマホ: カメラ撮影 or ファイル選択\n・背景を決めるまでは三角レイヤーは表示しません（iPhone安定化のため）")

# ---------------- ユーティリティ ----------------
def pil_to_data_url(img: Image.Image, fmt="JPEG", quality=90) -> str:
    """PIL画像 → data URL（iOSでも安定）"""
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, format=fmt)
        mime = f"image/{fmt.lower()}"
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def render_stage(bg_data_url: str):
    """背景が決まってから三角レイヤーを初期化して重ねる"""
    html = f"""
    <style>
      html, body {{
        margin: 0; height: 100%; background:#111; overflow:hidden;
      }}
      /* 背景は <img>：iPhoneで安定させる */
      #bgimg {{
        position: fixed; inset: 0; width: 100%; height: 100%;
        object-fit: contain;            /* 画面内に収める */
        object-position: center center;
        z-index: 0;
        display: block;
      }}
      #stage {{
        position: fixed; inset: 0; z-index: 1;
      }}
      #coords {{
        position: fixed; top: 10px; left: 10px;
        z-index: 2;
        color: #66ccff; font: 14px/1.3 monospace;
        background: rgba(0,0,0,.45);
        padding: 2px 6px; border-radius: 4px;
        pointer-events: none;
      }}
      .tri {{
        position: absolute; width: 0; height: 0;
        pointer-events: auto; cursor: grab; user-select: none; touch-action: none;
      }}
      .tri:active {{ cursor: grabbing; }}
    </style>

    <img id="bgimg" src="{bg_data_url}" alt="background">
    <div id="stage"></div>
    <div id="coords">x: –, y: –</div>

    <script>
    (function(){{
      const stage  = document.getElementById('stage');
      const coords = document.getElementById('coords');

      function makeTriangle(id, x, y, size=70, color='#ff2a2a') {{
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

      // 初期三角（控えめサイズ）
      const tris = [
        {{id:'t1', x:120, y:120, size:60, color:'#ff2a2a'}},
        {{id:'t2', x:240, y:220, size:50, color:'#2aff2a'}},
        {{id:'t3', x:360, y:160, size:45, color:'#2a9dff'}},
        {{id:'t4', x:100, y:300, size:70, color:'#ffd32a'}},
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
          /* iOS Safari で未サポートでもOK */
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
    # 背景が決まった“後”にだけ描画（keyを変えて確実に再初期化）
    components.html(html, height=720, scrolling=False)

# -------------- UI：画像を先に決める（PC/スマホタブ） --------------
tab_pc, tab_sp = st.tabs(["💻 PC（ドラッグ&ドロップだけ）", "📱 スマホ（カメラ or ファイル）"])

bg_data_url: str | None = None  # 最終的にここに入ったらステージを描画

with tab_pc:
    st.subheader("PC: 画像をドラッグ&ドロップ")
    up_pc = st.file_uploader(
        "ここに画像をドラッグ&ドロップ（またはクリックで選択）",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        accept_multiple_files=False,
    )
    if up_pc is not None:
        try:
            img = Image.open(up_pc)
            img.thumbnail((2000, 2000))  # 大きすぎる場合の保険
            bg_data_url = pil_to_data_url(img, fmt="JPEG", quality=90)
            st.success("画像を読み込みました。下に三角レイヤーが表示されます。")
        except Exception as e:
            st.error(f"画像の読み込みに失敗: {e}")

with tab_sp:
    st.subheader("スマホ: カメラ撮影 または ファイルから選択")
    c1, c2 = st.columns(2)
    with c1:
        cam = st.camera_input("タップして撮影（iPhone/Android）")
        if cam is not None and bg_data_url is None:
            try:
                img_cam = Image.open(cam)
                img_cam.thumbnail((2000, 2000))
                bg_data_url = pil_to_data_url(img_cam, fmt="JPEG", quality=90)
                st.success("撮影画像を読み込みました。下に三角レイヤーが表示されます。")
            except Exception as e:
                st.error(f"撮影画像の読み込みに失敗: {e}")
    with c2:
        up_sp = st.file_uploader(
            "ファイルから選択（写真ライブラリなど）",
            type=["png", "jpg", "jpeg", "webp", "gif"],
            accept_multiple_files=False,
        )
        if up_sp is not None and bg_data_url is None:
            try:
                img_sp = Image.open(up_sp)
                img_sp.thumbnail((2000, 2000))
                bg_data_url = pil_to_data_url(img_sp, fmt="JPEG", quality=90)
                st.success("画像を読み込みました。下に三角レイヤーが表示されます。")
            except Exception as e:
                st.error(f"画像の読み込みに失敗: {e}")

st.markdown("---")

# -------------- 背景が決まっていなければ「まだ表示しない」 --------------
if bg_data_url:
    render_stage(bg_data_url)
else:
    st.info("まず上で**背景画像**を選ぶ/撮ると、ここに三角レイヤーが表示されます。")
