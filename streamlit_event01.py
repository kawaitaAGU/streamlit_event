# app01.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="iPhoneページ拡大テスト", layout="wide")

# --- 重要: ページ全体ではピンチを許可する ---
st.markdown("""
<style>
  /* ページ全体でピンチを許可（Most Important） */
  html, body, #root, .stApp {
    touch-action: auto !important;
    -ms-touch-action: auto !important;  /* 互換用 */
  }

  /* 画像やテキストが画面幅に気持ちよく収まるように */
  .content-wrap {
    max-width: 900px;
    margin: 0 auto;
    padding: 12px;
    line-height: 1.7;
  }

  /* （必要なら）ドラッグ専用エリアだけを個別に制御する例
     ここを将来ドラッグ対応にするときは、
     1本指ドラッグ＝OK, 2本指＝何もしない（＝ページズームを通す）実装にしてね。
     いまはデモなので touch-action は付けない。 */
  .drag-area {
    border: 1px dashed #aaa;
    border-radius: 8px;
    padding: 8px;
  }

  /* Streamlit の不要な余白を少し詰めたい場合は適宜調整 */
  .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
  }
</style>
""", unsafe_allow_html=True)

st.title("📱 iPhone ピンチでページ拡大できるかテスト")

with st.container():
    st.markdown(
        """
<div class="content-wrap">
  <p>
    これは <strong>ページ全体のピンチ拡大</strong> が効くようにした最小構成です。<br>
    画面のどこからでも 2本指ピンチでズームイン／アウトできます。
  </p>

  <h4>チェックポイント</h4>
  <ul>
    <li>Safari のアドレスバー左「aA」→「ページ表示の拡大」も併用可能</li>
    <li><code>touch-action: none</code> を<strong>全体</strong>に付けない（＝付けるなら必要箇所だけ）</li>
    <li><code>event.preventDefault()</code> を広範囲に使わない</li>
    <li>（PWAの場合）まずは Safari 本体で挙動確認</li>
  </ul>

  <p>
    下の画像はただの <code>st.image</code> です。<br>
    画像自体には特別な JS を噛ませていないので、<strong>ページズーム</strong>の邪魔をしません。
  </p>
</div>
        """,
        unsafe_allow_html=True
    )

# 画像サンプル（手元に画像がなければ Streamlit のサンプルを使用）
sample = Path(st.__file__).parent / "static" / "media" / "logo.svg"
st.image(str(sample), caption="ズームテスト用（ページ全体ピンチが効くか確認）", use_container_width=True)

st.markdown(
    """
<div class="content-wrap">
  <h4>将来、ドラッグ可能エリアを入れたい場合</h4>
  <p>
    ドラッグが必要な領域（例えばキャンバスやSVG）を <code>.drag-area</code> の中に置き、
    <strong>その要素にだけ</strong> <code>touch-action: none;</code> を付けるのがコツです。<br>
    さらに 2本指のときはドラッグ処理を止めることで、ページズームを生かせます。
  </p>
  <div class="drag-area">
    （ここは将来ドラッグ領域にする想定の箱。<br>
     いまは <code>touch-action</code> を付けていないので、ここからでもページピンチが通ります）
  </div>

  <h4>うまくいかない場合</h4>
  <ol>
    <li>外部コンポーネント（<code>components.html</code>）の <em>iframe</em> 内でピンチ開始していないか確認
      <ul>
        <li>iframe 内のピンチは「ページ」ではなく「iframe」側にかかることがあります</li>
        <li>ページズームを優先したいなら、iframe を全画面にしない／余白からピンチ開始する等で回避可能</li>
      </ul>
    </li>
    <li>グローバルに <code>touch-action: none</code> や、広範囲な <code>preventDefault()</code> が残っていないか確認</li>
  </ol>
</div>
    """,
    unsafe_allow_html=True
)
