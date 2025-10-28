# app.py
import io, base64
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="iPhoneピンチ確実版（OpenSeadragon）", layout="wide")
st.title("📷 画像アップ → iPhoneでピンチズーム（要素内・確実版）")

file = st.file_uploader(
    "ここに画像をドラッグ&ドロップ（またはタップ）",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=False,
    label_visibility="collapsed",
)

def pil_to_data_url(img: Image.Image) -> str:
    img = ImageOps.exif_transpose(img)  # iPhoneの回転補正
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

if file:
    img = Image.open(file)
    data_url = pil_to_data_url(img)

    html = f"""
    <!-- 念のため viewport をズーム許可に -->
    <script>
      (function(){{
        let m = document.querySelector('meta[name="viewport"]');
        const c = 'width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes';
        if (m) m.setAttribute('content', c);
        else {{ m = document.createElement('meta'); m.name='viewport'; m.content=c; document.head.appendChild(m); }}
      }})();
    </script>

    <!-- OpenSeadragon 読み込み -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/openseadragon.min.js" integrity="sha512-+x4m1z9qkU6vSIO2xkqf5nZJ1J7iLrM3XqS2z0QXjzY0wChJbIh8p8Y0tXgq8z5a0mJ7Yl4kqk6O3s4j9t9GSA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/openseadragon.min.css" integrity="sha512-1x3nYqk4y0ql8S7G3K7Vw0bX3zQ2Oa7w8xwQv3m3YgJ3F3rZk3b7Z9c9l1n0c1gV3m1k2y5m0C8l6i5f0j5fZQ==" crossorigin="anonymous" referrerpolicy="no-referrer" />

    <style>
      /* 要素内ジェスチャーを優先させる */
      #osd-container {{
        width: 100%;
        height: 75vh;
        background: #111;
        border-radius: 12px;
        overflow: hidden;
        touch-action: none;              /* iOSでの要素内ピンチ */
        -webkit-user-select: none;
        user-select: none;
      }}
    </style>

    <div id="osd-container"></div>

    <script>
      // 単一画像をそのままDeepZoomなしで読み込み
      const viewer = OpenSeadragon({{
        id: "osd-container",
        prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/images/",
        tileSources: {{
          type: "image",
          url: "{data_url}"
        }},
        showNavigationControl: false,
        gestureSettingsMouse: {{
          clickToZoom: false,   // ダブルクリックズーム無効化（必要なら true）
          dblClickToZoom: true,
          scrollToZoom: true
        }},
        gestureSettingsTouch: {{
          pinchToZoom: true,    // ← iPhoneでのピンチズーム
          flickEnabled: true,
          clickToZoom: false,
          dblClickToZoom: false
        }},
        maxZoomPixelRatio: 4,   // 拡大の上限調整
        visibilityRatio: 1.0,
        constrainDuringPan: true
      }});
    </script>
    """
    components.html(html, height=650, scrolling=False)
else:
    st.info("画像をアップすると、その画像の“中”でピンチズーム＆ドラッグが使えます（iPhone対応・確実版）。")
