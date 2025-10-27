# enlarge01＿２.py
import streamlit as st
from PIL import Image, ImageOps

st.set_page_config(page_title="iPhoneピンチ拡大テスト", layout="wide")

# ページ全体でピンチ（ズーム）を許可
st.markdown("""
<style>
  html, body, #root, .stApp { touch-action: auto !important; }
  .block-container { padding-top: 1rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("📷 画像アップロード → ピンチで拡大縮小（iPhone対応）")

file = st.file_uploader(
    "ここに画像をドラッグ&ドロップ（またはタップして選択）",
    type=["png", "jpg", "jpeg", "webp", "heic", "heif"],
    accept_multiple_files=False,
)

if file:
    # EXIFの向きを自動補正して表示（iPhone写真対策）
    img = Image.open(file)
    img = ImageOps.exif_transpose(img)
    st.image(img, caption="取り込んだ画像", use_container_width=True)
else:
    st.info("上のエリアに画像をドラッグ＆ドロップ（またはタップして選択）してください。")

st.caption("※ 画像自体に特別なズーム処理は入れていません。ページ全体のピンチ操作で自由に拡大縮小できます。")
