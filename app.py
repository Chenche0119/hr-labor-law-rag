"""
Streamlit 前端介面
"""
import streamlit as st
from src.rag_engine import RAGEngine, RAGResult

st.set_page_config(
    page_title="企業HR勞動法規查詢AI",
    page_icon="⚖️",
    layout="centered",
)

st.title("⚖️ 企業HR勞動法規查詢AI")
st.caption("基於 RAG 技術，結合全國法規資料庫與勞工法教授著作，提供準確的法規查詢與實務解說。")

# 初始化 engine（只建立一次）
@st.cache_resource
def get_engine() -> RAGEngine:
    return RAGEngine()


engine = get_engine()

# 對話歷史
if "history" not in st.session_state:
    st.session_state.history = []

# 顯示歷史對話
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "meta" in msg:
            meta = msg["meta"]
            _type_label = {"A": "直接查詢型", "B": "爭議解釋型", "out_of_scope": "超出範疇", "no_law": "無明確法條"}.get(
                meta["query_type"], meta["query_type"]
            )
            st.caption(f"問題類型：{_type_label}")

# 輸入框
if prompt := st.chat_input("請輸入您的勞工法規問題..."):
    # 顯示使用者訊息
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 呼叫 RAG
    with st.chat_message("assistant"):
        with st.spinner("查詢中..."):
            result: RAGResult = engine.query(prompt)

        st.markdown(result.answer)

        _type_label = {
            "A": "直接查詢型（法條庫）",
            "B": "爭議解釋型（書籍庫＋法條庫）",
            "out_of_scope": "超出服務範疇",
            "no_law": "現行法規無明確規定",
        }.get(result.query_type, result.query_type)
        st.caption(f"問題類型：{_type_label}")

        # 展開顯示來源
        if result.chunks:
            with st.expander(f"參考來源（{len(result.chunks)} 筆）"):
                for chunk in result.chunks:
                    badge = "🔵 法條" if chunk.collection == "laws" else "📚 書籍"
                    st.markdown(f"**{badge} {chunk.source}**（距離分數：{chunk.distance:.3f}）")
                    st.text(chunk.content[:200] + ("..." if len(chunk.content) > 200 else ""))
                    st.divider()

    st.session_state.history.append({
        "role": "assistant",
        "content": result.answer,
        "meta": {"query_type": result.query_type},
    })

# 側邊欄說明
with st.sidebar:
    st.header("系統說明")
    st.markdown("""
**問題流程：**
1. **Guardrail** — 判斷是否屬台灣勞工法範疇
2. **Router** — 分類為 A（直接查詢）或 B（爭議解釋）
3. **檢索** — A 型只查法條庫；B 型查書籍庫＋法條庫
4. **信心門檻** — A 型問題若無高度相關法條，直接回覆「無明確規定」
5. **LLM 生成** — Claude Haiku 整合 context 產出白話回答

**資料來源：**
- 全國法規資料庫（勞基法、勞退條例、性平法、勞保條例）
- 勞工法教授著作（5 本）

**使用限制：**
本系統提供法規資訊，不構成正式法律意見。
""")
    st.divider()
    if st.button("清除對話紀錄"):
        st.session_state.history = []
        st.rerun()
