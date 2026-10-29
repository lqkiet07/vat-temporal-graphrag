from datetime import date
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.engine.llm_client import check_ollama_available
from src.ui.corpus_viewer import load_corpus_tree, render_document_tree_html
from src.ui.demo_service import (
    DEMO_SCENARIOS,
    execute_demo_query,
    generate_printable_html,
)

PIPELINE_MAP: dict[str, str] = {
    "P3_FullSystem (Đề xuất)": "P3_FullSystem",
    "P2_TemporalGraphRAG": "P2_TemporalGraphRAG",
    "P1_FlatRAG (Baseline)": "P1_FlatRAG",
}

RISK_COLOR_MAP: dict[str, str] = {
    "LOW": "#2b8a3e",
    "MEDIUM": "#e67700",
    "HIGH": "#d9480f",
    "CRITICAL": "#c92a2a",
}


def get_risk_badge_color(score: int) -> str:
    if score >= 76:
        return "#c92a2a"
    if score >= 51:
        return "#d9480f"
    if score >= 21:
        return "#e67700"
    return "#2b8a3e"


def get_benchmark_metrics_df() -> pd.DataFrame:
    data = [
        {
            "Pipeline": "P1_FlatRAG (Baseline)",
            "P": "2.20%",
            "R": "4.83%",
            "Acc_temp": "79.20%",
        },
        {
            "Pipeline": "P2_TemporalGraphRAG",
            "P": "21.60%",
            "R": "40.83%",
            "Acc_temp": "100.00%",
        },
        {
            "Pipeline": "P3_FullSystem (Đề xuất)",
            "P": "21.60%",
            "R": "40.83%",
            "Acc_temp": "100.00%",
        },
    ]
    return pd.DataFrame(data)


def find_doc_id_for_article(article_id: str, corpus_docs: list[dict]) -> str | None:
    for doc in corpus_docs:
        articles = doc.get("articles", [])
        for ch in doc.get("chapters", []):
            articles = articles + ch.get("articles", [])
        if any(art.get("id") == article_id for art in articles):
            return doc.get("id")
    for doc in corpus_docs:
        doc_id = doc.get("id", "")
        if doc_id and article_id.startswith(doc_id):
            return doc_id
    return None


def init_session_state() -> None:
    if "scenario_choice" not in st.session_state:
        st.session_state["scenario_choice"] = 0
    if "query_input" not in st.session_state:
        st.session_state["query_input"] = DEMO_SCENARIOS[0]["query"]
    if "as_of_date_input" not in st.session_state:
        st.session_state["as_of_date_input"] = date.fromisoformat(DEMO_SCENARIOS[0]["as_of_date"])
    if "active_article_ids" not in st.session_state:
        st.session_state["active_article_ids"] = []
    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "selected_doc_id" not in st.session_state:
        st.session_state["selected_doc_id"] = "LUAT_48_2024"
    if "use_llm" not in st.session_state:
        st.session_state["use_llm"] = False


def on_scenario_change() -> None:
    idx = st.session_state.get("scenario_choice")
    if idx is not None and 0 <= idx < len(DEMO_SCENARIOS):
        sc = DEMO_SCENARIOS[idx]
        st.session_state["query_input"] = sc["query"]
        st.session_state["as_of_date_input"] = date.fromisoformat(sc["as_of_date"])


def render_sidebar() -> tuple[str, bool]:
    st.sidebar.title("⚖️ CT250H Demo")
    st.sidebar.markdown("### Niên luận CT250H: Temporal KG-RAG Thuế GTGT")
    st.sidebar.caption("🎓 **K49 KTPM CLC - ĐH Cần Thơ**")
    st.sidebar.markdown("---")

    st.sidebar.markdown("#### 🎯 Kịch bản Thử nghiệm")
    st.sidebar.selectbox(
        "Chọn kịch bản:",
        options=list(range(len(DEMO_SCENARIOS))),
        format_func=lambda i: DEMO_SCENARIOS[i]["name"],
        key="scenario_choice",
        on_change=on_scenario_change,
    )

    st.sidebar.markdown("#### ⚙️ Lựa chọn Pipeline")
    pipeline_label = st.sidebar.radio(
        "Kiến trúc suy luận:",
        options=[
            "P3_FullSystem (Đề xuất)",
            "P2_TemporalGraphRAG",
            "P1_FlatRAG (Baseline)",
        ],
        index=0,
    )
    pipeline_key = PIPELINE_MAP.get(pipeline_label, "P3_FullSystem")

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🤖 Cấu hình AI Engine (Local LLM)")
    use_llm = st.sidebar.checkbox("Kích hoạt Ollama Local (qwen2.5:7b)", value=False)
    if use_llm:
        ollama_online = check_ollama_available()
        if ollama_online:
            st.sidebar.success("🟢 Ollama Online (qwen2.5:7b)")
        else:
            st.sidebar.warning("⚪ Ollama chưa bật (fallback về Tất định an toàn)")
    st.session_state["use_llm"] = use_llm

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Benchmark (100 câu hỏi)")
    benchmark_df = get_benchmark_metrics_df()
    st.sidebar.dataframe(benchmark_df, hide_index=True, use_container_width=True)
    st.sidebar.caption("So sánh $P$, $R$, $Acc_{temp}$ trên tập kiểm thử 100 câu.")

    return pipeline_key, use_llm


def render_corpus_viewer(corpus_docs: list[dict], active_ids: list[str]) -> None:
    st.markdown("### 📜 Cột Trái: Trình đọc Văn bản Luật Gốc")
    if not corpus_docs:
        st.warning("Không tìm thấy dữ liệu văn bản pháp luật.")
        return

    doc_ids = [d["id"] for d in corpus_docs]
    doc_map = {d["id"]: d for d in corpus_docs}

    current_id = st.session_state.get("selected_doc_id")
    if current_id not in doc_map:
        current_id = doc_ids[0]
        st.session_state["selected_doc_id"] = current_id

    selected_doc_id = st.selectbox(
        "Chọn văn bản pháp quy:",
        options=doc_ids,
        format_func=lambda did: f"{doc_map[did].get('code', did)} - {doc_map[did].get('title', '')}",
        key="selected_doc_id",
    )
    selected_doc = doc_map.get(selected_doc_id, corpus_docs[0])

    active_in_doc = [aid for aid in active_ids if aid.startswith(selected_doc_id)]
    if active_in_doc:
        st.info(f"🎯 **Điều khoản viện dẫn kích hoạt:** {', '.join(f'`{aid}`' for aid in active_in_doc)}")

    raw_html = render_document_tree_html(selected_doc, active_ids)
    scroll_script = """
    <script>
      window.addEventListener('load', function() {
        const el = document.querySelector('.highlighted-article');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });
    </script>
    """
    wrapped_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 12px; background: #ffffff; border: 1px solid #dee2e6; border-radius: 6px;">
        {raw_html}
    </div>
    {scroll_script}
    """
    components.html(wrapped_html, height=700, scrolling=True)


def _render_warnings_and_meter(last_result: dict) -> None:
    score = last_result.get("risk_score", 0)
    level = last_result.get("risk_level", "LOW")
    badge_color = get_risk_badge_color(score)
    warnings = last_result.get("warnings", [])

    st.markdown("---")
    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span style="font-weight: bold; font-size: 15px;">Chỉ số Rủi ro Pháp lý (Risk Score):</span>
            <span style="background-color: {badge_color}; color: white; padding: 4px 14px; border-radius: 12px; font-weight: bold; font-size: 13px;">
                {level} ({score}/100)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(score / 100.0)

    if warnings:
        for w in warnings:
            if score >= 51:
                st.error(f"⚠️ {w}")
            else:
                st.warning(f"⚠️ {w}")
    else:
        st.success("✅ **An toàn pháp lý:** Toàn bộ căn cứ pháp lý viện dẫn đều đang có hiệu lực thi hành tại thời điểm tra cứu.")


def _render_irac_and_download(last_result: dict) -> None:
    irac = last_result.get("irac_sections", {})
    tab_issue, tab_rule, tab_app, tab_conc = st.tabs([
        "📌 Issue (Vấn đề)",
        "📜 Rule (Căn cứ pháp lý)",
        "🔍 Application (Áp dụng)",
        "⚖️ Conclusion (Kết luận)",
    ])

    with tab_issue:
        st.markdown(f"**Vấn đề pháp lý:**\n\n{irac.get('issue', '')}")

    with tab_rule:
        st.markdown(f"**Căn cứ pháp lý viện dẫn:**\n\n{irac.get('rule', '')}")
        cites = last_result.get("citations", [])
        if cites:
            st.markdown(f"**Danh sách điều khoản:** {', '.join(f'`{c}`' for c in cites)}")

    with tab_app:
        st.markdown(f"**Áp dụng & Phân tích:**\n\n{irac.get('application', '')}")

    with tab_conc:
        st.markdown(f"**Kết luận tư vấn:**\n\n{irac.get('conclusion', '')}")

    st.markdown("---")
    as_of_str = last_result.get("as_of_date", "")
    printable_html = generate_printable_html(
        query=last_result.get("query", ""),
        as_of_date=as_of_str,
        result=last_result,
    )
    st.download_button(
        label="📄 Tải / In Báo cáo Thẩm định (Printable HTML)",
        data=printable_html,
        file_name=f"vat_report_{as_of_str}.html",
        mime="text/html",
        use_container_width=True,
    )


def handle_run_pipeline(
    corpus_docs: list[dict],
    pipeline_key: str,
    use_llm: bool | None = None,
) -> None:
    query_text = st.session_state.get("query_input", "").strip()
    if not query_text:
        st.session_state["query_error"] = "Vui lòng nhập nội dung câu hỏi."
        return

    st.session_state["query_error"] = None
    as_of_val = st.session_state.get("as_of_date_input")
    as_of_str = as_of_val.isoformat() if hasattr(as_of_val, "isoformat") else str(as_of_val)

    if use_llm is None:
        use_llm = st.session_state.get("use_llm", False)

    res = execute_demo_query(
        query=query_text,
        as_of_date=as_of_str,
        pipeline=pipeline_key,
        use_llm=use_llm,
        model="qwen2.5:7b",
    )
    st.session_state["last_result"] = res
    st.session_state["active_article_ids"] = res.get("active_article_ids", [])

    if res.get("active_article_ids"):
        top_art = res["active_article_ids"][0]
        target_doc_id = find_doc_id_for_article(top_art, corpus_docs)
        if target_doc_id:
            st.session_state["selected_doc_id"] = target_doc_id


def render_reasoning_column(
    corpus_docs: list[dict],
    pipeline_key: str,
    use_llm: bool = False,
) -> None:
    st.markdown("### ⚖️ Cột Phải: Khung Phân tích Tư vấn & Thẩm định")

    st.text_area(
        "Nội dung câu hỏi / Tình huống thực tế:",
        key="query_input",
        height=95,
    )
    st.date_input(
        "Mốc thời gian tra cứu (as_of_date):",
        key="as_of_date_input",
    )

    st.button(
        "⚖️ Tra cứu & Thẩm định (Run Pipeline)",
        type="primary",
        use_container_width=True,
        on_click=handle_run_pipeline,
        args=(corpus_docs, pipeline_key, use_llm),
    )

    if st.session_state.get("query_error"):
        st.warning(st.session_state["query_error"])

    last_result = st.session_state.get("last_result")
    if last_result is None:
        st.info("💡 Chọn kịch bản mẫu ở thanh bên trái hoặc nhập câu hỏi, sau đó nhấn **'⚖️ Tra cứu & Thẩm định'**.")
        return

    if last_result.get("llm_used"):
        st.caption("🤖 Lập luận tự nhiên sinh bởi Ollama Local (qwen2.5:7b) • Đã qua chốt chặn Verifier")
    else:
        st.caption("⚙️ Chế độ Tất định An toàn (Deterministic Safe Mode • 0 VNĐ)")

    _render_warnings_and_meter(last_result)
    _render_irac_and_download(last_result)


def main() -> None:
    st.set_page_config(
        layout="wide",
        page_title="CT250H - VAT Temporal GraphRAG",
        page_icon="⚖️",
    )
    init_session_state()
    pipeline_key, use_llm = render_sidebar()
    corpus_docs = load_corpus_tree()

    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        render_corpus_viewer(
            corpus_docs=corpus_docs,
            active_ids=st.session_state.get("active_article_ids", []),
        )

    with col_right:
        render_reasoning_column(
            corpus_docs=corpus_docs,
            pipeline_key=pipeline_key,
            use_llm=use_llm,
        )


if __name__ == "__main__":
    main()
