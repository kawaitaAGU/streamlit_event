# 05.py  — iPhoneで要素内ピンチ拡大（pinch-zoom-js 正しい使い方版）
import base64, io
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="iPhone要素内ピンチズーム", layout="wide")
st.title("📷 画像アップロード → iPhoneでピンチ拡大（要素内）")

file = st.file_uploader(
    "ここに画像をドラッグ＆ドロップ（またはタップ）",
    type=["png", "jpg", "jpeg", "webp", "heic", "heif"],
    accept_multiple_files=False,
    label_visibility="collapsed",
)

def pil_to_data_url(img: Image.Image) -> str:
    img = ImageOps.exif_transpose(img)  # iPhone写真の回転補正
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

if file:
    img = Image.open(file)
    data_url = pil_to_data_url(img)

    html = f"""
    <!-- （保険）ページのviewportをズーム許可に -->
    <script>
      (function(){{
        let m = document.querySelector('meta[name="viewport"]');
        const c = 'width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes';
        if (m) m.setAttribute('content', c);
        else {{ m = document.createElement('meta'); m.name='viewport'; m.content=c; document.head.appendChild(m); }}
      }})();
    </script>

    <!-- pinch-zoom-js（manuelstofer版）-->
    <script src="https://unpkg.com/pinch-zoom-js/dist/pinch-zoom.umd.js"></script>

    <style>
      .wrap {{
        max-width: 1000px;
        margin: 0 auto;
        border: 1px solid #ddd;
        border-radius: 12px;
        overflow: hidden;
        background: #111;
      }}
      /* ライブラリがバインドされる要素 */
      .pinch-zoom {{
        width: 100%;
        height: 75vh;             /* 表示領域の高さ */
        touch-action: none;        /* 要素内ジェスチャーをこの要素に集約 */
        position: relative;
      }}
      .pinch-zoom img {{
        display: block;
        width: 100%;
        height: auto;
        -webkit-user-drag: none;
        user-select: none;
        -webkit-user-select: none;
        -webkit-touch-callout: none;
        pointer-events: none;      /* 画像にイベントを食わせず、コンテナへ */
      }}
    </style>

    <div class="wrap">
      <!-- これが pinch-zoom-js の正しいマークアップ -->
      <div id="pz" class="pinch-zoom">
        <img src="{data_url}" alt="uploaded">
      </div>
    </div>

    <script>
      // UMD版は PinchZoom.default でコンストラクタにアクセス
      (function(){{
        const el = document.getElementById('pz');
        // オプションは必要に応じて調整
        const pz = new PinchZoom.default(el, {{
          draggableUnzoomed: true,  // 等倍時でもドラッグ可
          minZoom: 1,
          maxZoom: 8,
          tapZoomFactor: 2,         // ダブルタップ時の倍率
          animationDuration: 200
        }});
      }})();
    </script>
    """

    components.html(html, height=650, scrolling=False)
else:
    st.info("画像をアップすると、その画像の“中”でピンチズーム＆ドラッグが使えます（iPhone対応）。")
