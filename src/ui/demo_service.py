from src.verifier.guardrails import check_query_domain
"""Business logic and sample scenarios for the interactive VAT demo UI."""
from html import escape
from src.benchmark.baselines import run_p1_baseline_rag
from src.engine.llm_client import generate_llm_response
from src.engine.models import ArticleNode
from src.engine.prompt import build_irac_prompt
from src.engine.temporal_retriever import query_temporal_rag
from src.ui.corpus_viewer import load_corpus_tree
from src.verifier.citation_verifier import extract_citations
from src.verifier.risk_score import verify_and_score

DEMO_SCENARIOS: list[dict] = [
    {
        "name": "Kịch bản 1 (Xanh - An toàn): Thuế suất 0% phần mềm xuất khẩu năm 2026",
        "query": "Doanh nghiệp tại Cần Thơ xuất khẩu phần mềm sang Nhật Bản vào tháng 03/2026 áp dụng thuế suất thuế GTGT bao nhiêu?",
        "as_of_date": "2026-03-20",
        "badge_color": "green",
    },
    {
        "name": "Kịch bản 2 (Đỏ - Bẫy thời gian): Áp dụng Luật 48 trước ngày 01/07/2025",
        "query": "Doanh nghiệp xuất khẩu dịch vụ vào tháng 05/2024 áp dụng điều kiện theo Luật 48/2024 có được không?",
        "as_of_date": "2024-05-15",
        "badge_color": "red",
    },
    {
        "name": "Kịch bản 3 (Vàng - Sửa đổi): Điều 9 NĐ 181 bị sửa đổi bởi NĐ 144/2026",
        "query": "Quy định về hóa đơn chứng từ đối với dịch vụ xuất khẩu theo Điều 9 Nghị định 181/2025 áp dụng như thế nào vào tháng 08/2026?",
        "as_of_date": "2026-08-10",
        "badge_color": "yellow",
    },
]


def _build_irac_sections(
    query: str, as_of_date: str, citations: list[str], warnings: list[str]
) -> dict[str, str]:
    """Build structured IRAC sections based on query, citations, and risk warnings."""
    # ponytail: synthesized deterministic IRAC text; replace with LLM generation if backend attached
    rule_str = ", ".join(f"[{c}]" for c in citations) if citations else "Không có căn cứ hiệu lực"
    issue = f"Xác định quy định pháp luật áp dụng cho yêu cầu: '{query}' tại mốc thời gian {as_of_date}."
    rule = f"Căn cứ pháp lý viện dẫn: {rule_str}."
    q_lower = query.lower()
    is_software_export = (
        ("phần mềm" in q_lower or "machine learning" in q_lower or "công nghệ thông tin" in q_lower)
        and ("xuất khẩu" in q_lower or "nước ngoài" in q_lower or "nhật bản" in q_lower)
        and ("thuế suất" in q_lower or "%" in q_lower)
    )
    if is_software_export:
        conc = f"Áp dụng mức thuế suất thuế GTGT là 0% đối với dịch vụ xuất khẩu / phần mềm cho đối tác nước ngoài theo quy định hiện hành ({rule_str}) khi đáp ứng điều kiện hợp đồng và thanh toán qua ngân hàng."
        if warnings:
            warn_text = " Cảnh báo rủi ro hiệu lực: " + "; ".join(warnings)
            app = f"Tại mốc {as_of_date}, các quy định viện dẫn có cảnh báo sau:{warn_text}. Về thuế suất, dịch vụ phần mềm/machine learning xuất khẩu thuộc diện áp dụng thuế suất 0%."
        else:
            app = f"Tại thời điểm tra cứu {as_of_date}, các quy định trên đang có hiệu lực thi hành đầy đủ. Dịch vụ phần mềm/machine learning cung ứng cho tổ chức nước ngoài tiêu dùng ngoài Việt Nam áp dụng thuế suất 0%."
    elif warnings:
        warn_text = " Cảnh báo rủi ro hiệu lực: " + "; ".join(warnings)
        app = f"Tại mốc {as_of_date}, các quy định viện dẫn có cảnh báo sau:{warn_text}"
        conc = f"Cần thận trọng: Phát hiện rủi ro thời gian hoặc hiệu lực pháp lý đối với câu hỏi tại ngày {as_of_date}."
    else:
        app = f"Tại thời điểm tra cứu {as_of_date}, các quy định trên đang có hiệu lực thi hành đầy đủ."
        conc = f"Các căn cứ pháp lý {rule_str} có hiệu lực và áp dụng trực tiếp cho tình huống."
    return {
        "issue": issue,
        "rule": rule,
        "application": app,
        "conclusion": conc,
    }


def _check_temporal_trap(query: str, as_of_date: str) -> list[str]:
    """Check if query references a legal document not yet effective at as_of_date."""
    docs = load_corpus_tree()
    q_norm = query.lower()
    warnings = []
    for doc in docs:
        doc_code = doc.get("code", "").lower()
        title = doc.get("title", "")
        valid_from = doc.get("valid_from", "")
        num_code = doc_code.split("/")[0] if "/" in doc_code else doc_code
        match = (
            doc_code in q_norm
            or (num_code and f"luật {num_code}" in q_norm)
            or (num_code and f"luat {num_code}" in q_norm)
            or (num_code and f"nghị định {num_code}" in q_norm)
            or (num_code and f"thông tư {num_code}" in q_norm)
            or (num_code and f"{num_code}/20" in q_norm)
        )
        if match and valid_from and as_of_date < valid_from:
            warnings.append(
                f"Văn bản {title} ({doc.get('code')}) chưa có hiệu lực tại ngày {as_of_date} (có hiệu lực từ ngày {valid_from})."
            )
    return warnings


def _parse_irac_sections(raw_text: str) -> dict[str, str]:
    """Parse raw LLM response into IRAC sections."""
    sections: dict[str, str] = {
        "issue": "",
        "rule": "",
        "application": "",
        "conclusion": "",
        "raw_text": raw_text,
    }
    current_key: str | None = None
    for line in raw_text.splitlines():
        stripped = line.strip().lstrip("#* -0123456789.:").strip()
        lower_header = stripped.lower()
        if lower_header.startswith("issue"):
            current_key = "issue"
            val = line.split(":", 1)[-1].strip() if ":" in line else ""
            if val and val.lower() != "issue":
                sections[current_key] = val
        elif lower_header.startswith("rule"):
            current_key = "rule"
            val = line.split(":", 1)[-1].strip() if ":" in line else ""
            if val and val.lower() != "rule":
                sections[current_key] = val
        elif lower_header.startswith("application"):
            current_key = "application"
            val = line.split(":", 1)[-1].strip() if ":" in line else ""
            if val and val.lower() != "application":
                sections[current_key] = val
        elif lower_header.startswith("conclusion"):
            current_key = "conclusion"
            val = line.split(":", 1)[-1].strip() if ":" in line else ""
            if val and val.lower() != "conclusion":
                sections[current_key] = val
        elif current_key and line.strip():
            sections[current_key] = (sections[current_key] + " " + line.strip()).strip()
    if not any([sections["issue"], sections["rule"], sections["application"], sections["conclusion"]]):
        sections["application"] = raw_text
    return sections


def _fetch_pipeline_articles(
    pipeline: str, query: str, as_of_date: str
) -> tuple[list[str], list[str], list[ArticleNode]]:
    """Retrieve citations, active IDs, and articles for the selected pipeline."""
    if pipeline == "P1_FlatRAG":
        citations = run_p1_baseline_rag(query, as_of_date, top_k=5)
        return citations, citations, []
    res = query_temporal_rag(query, as_of_date)
    raw_ids = [art.id for art in res.articles]
    active_ids = raw_ids[:5]
    return active_ids, active_ids, res.articles


def execute_demo_query(
    query: str,
    as_of_date: str,
    pipeline: str = "P3_FullSystem",
    use_llm: bool = False,
    model: str = "qwen2.5:7b",
) -> dict:
    """Execute a query against specified pipeline and return IRAC analysis with risk score."""
    # 1. Domain guardrail check
    guard = check_query_domain(query)
    if not guard.is_allowed:
        return {
            "query": query,
            "as_of_date": as_of_date,
            "pipeline": pipeline,
            "citations": [],
            "active_article_ids": [],
            "risk_score": 0,
            "risk_level": "LOW",
            "warnings": [],
            "irac_sections": {
                "issue": f"Phạm vi áp dụng pháp lý: '{query}'",
                "rule": "Phạm vi điều chỉnh: Các văn bản pháp luật về Thuế Giá trị gia tăng (Luật 48/2024, NĐ 181/2025, TT 69/2025, NĐ 359/2025, NĐ 144/2026).",
                "application": guard.refusal_message,
                "conclusion": guard.refusal_message,
            },
            "llm_used": False,
            "raw_llm_response": None,
            "is_out_of_domain": not guard.is_greeting,
            "is_greeting": guard.is_greeting,
        }

    citations, active_ids, articles = _fetch_pipeline_articles(pipeline, query, as_of_date)

    if not citations and not articles:
        trap_warnings = _check_temporal_trap(query, as_of_date)
        if trap_warnings:
            return {
                "query": query,
                "as_of_date": as_of_date,
                "pipeline": pipeline,
                "citations": [],
                "active_article_ids": [],
                "risk_score": 100,
                "risk_level": "CRITICAL",
                "warnings": trap_warnings,
                "irac_sections": {
                    "issue": f"Xác định hiệu lực và khả năng áp dụng: '{query}' tại mốc {as_of_date}.",
                    "rule": "Quy định về thời điểm có hiệu lực thi hành của văn bản quy phạm pháp luật.",
                    "application": "; ".join(trap_warnings),
                    "conclusion": f"Cảnh báo bẫy thời gian: Văn bản được hỏi chưa có hiệu lực thi hành tại mốc {as_of_date}. Doanh nghiệp không được áp dụng các điều kiện hay quy định của văn bản này vào thời điểm trên.",
                },
                "llm_used": False,
                "raw_llm_response": None,
                "is_out_of_domain": False,
                "is_greeting": False,
            }
        return {
            "query": query,
            "as_of_date": as_of_date,
            "pipeline": pipeline,
            "citations": [],
            "active_article_ids": [],
            "risk_score": 0,
            "risk_level": "LOW",
            "warnings": ["Không tìm thấy điều khoản pháp luật thuế GTGT nào điều chỉnh nội dung này tại mốc thời gian tra cứu."],
            "irac_sections": {
                "issue": f"Xác định quy định pháp luật cho: '{query}' tại mốc {as_of_date}.",
                "rule": "Không tìm thấy điều khoản pháp luật thuế GTGT phù hợp.",
                "application": f"Tại mốc {as_of_date}, hệ thống đã đối chiếu qua cơ sở dữ liệu pháp luật thuế GTGT nhưng không tìm thấy điều khoản nào quy định nội dung này.",
                "conclusion": "Câu hỏi không có căn cứ pháp luật thuế GTGT điều chỉnh tại mốc thời gian đã chọn.",
            },
            "llm_used": False,
            "raw_llm_response": None,
            "is_out_of_domain": False,
            "is_greeting": False,
        }

    if use_llm:
        prompt_articles = articles if pipeline != "P1_FlatRAG" else []
        prompt = build_irac_prompt(query, as_of_date, prompt_articles)
        raw_response = generate_llm_response(
            prompt,
            model=model,
            options={"num_ctx": 4096, "num_predict": 1024},
        )
        if raw_response is not None:
            extracted = extract_citations(raw_response)
            llm_citations = extracted if extracted else active_ids
            v_res = verify_and_score(raw_response, as_of_date)
            irac = _parse_irac_sections(raw_response)
            return {
                "query": query,
                "as_of_date": as_of_date,
                "pipeline": pipeline,
                "citations": llm_citations,
                "active_article_ids": active_ids,
                "risk_score": v_res.risk_score,
                "risk_level": v_res.risk_level,
                "warnings": v_res.warnings,
                "irac_sections": irac,
                "llm_used": True,
                "raw_llm_response": raw_response,
            }

    cite_text = " ".join(f"[{cid}]" for cid in citations)
    v_res = verify_and_score(cite_text, as_of_date)
    irac = _build_irac_sections(query, as_of_date, citations, v_res.warnings)

    return {
        "query": query,
        "as_of_date": as_of_date,
        "pipeline": pipeline,
        "citations": citations,
        "active_article_ids": active_ids,
        "risk_score": v_res.risk_score,
        "risk_level": v_res.risk_level,
        "warnings": v_res.warnings,
        "irac_sections": irac,
        "llm_used": False,
        "raw_llm_response": None,
    }


def generate_printable_html(query: str, as_of_date: str, result: dict) -> str:
    """Generate clean printable HTML report with print-optimized CSS."""
    # ponytail: pure HTML/CSS without external PDF binary dependencies
    sections = result.get("irac_sections", {})
    warnings = result.get("warnings", [])
    warn_html = "".join(f"<li>{escape(w)}</li>" for w in warnings) or "<li>Không phát hiện rủi ro</li>"
    cites = ", ".join(result.get("citations", [])) or "None"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Báo cáo tư vấn thuế GTGT - {escape(as_of_date)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; color: #212529; margin: 20px; }}
.header {{ border-bottom: 2px solid #228be6; padding-bottom: 10px; margin-bottom: 20px; }}
.badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; background: #e7f5ff; color: #1c7ed6; }}
.risk-box {{ background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; margin: 15px 0; }}
.section-title {{ font-size: 14px; font-weight: bold; text-transform: uppercase; color: #495057; margin-top: 15px; margin-bottom: 5px; }}
.section-content {{ margin-bottom: 15px; white-space: pre-line; }}
@media print {{
  body {{ margin: 0; font-size: 12pt; }}
  .no-print {{ display: none; }}
  .page-break {{ page-break-after: always; }}
}}
</style>
</head>
<body>
<div class="header">
  <h2>BÁO CÁO PHÂN TÍCH THUẾ GTGT THEO THỜI ĐIỂM</h2>
  <div><strong>Ngày tra cứu (As-of Date):</strong> {escape(as_of_date)} | <strong>Pipeline:</strong> {escape(result.get("pipeline", "N/A"))}</div>
</div>
<div class="risk-box">
  <div><strong>Câu hỏi tra cứu:</strong> {escape(query)}</div>
  <div><strong>Điểm rủi ro (Risk Score):</strong> {result.get("risk_score", 0)}/100 (Mức độ: {escape(result.get("risk_level", "LOW"))})</div>
  <div><strong>Căn cứ trích dẫn:</strong> {escape(cites)}</div>
  <div><strong>Cảnh báo:</strong> <ul>{warn_html}</ul></div>
</div>
<div class="section-title">1. Vấn đề pháp lý (Issue)</div>
<div class="section-content">{escape(sections.get("issue", ""))}</div>
<div class="section-title">2. Quy phạm áp dụng (Rule)</div>
<div class="section-content">{escape(sections.get("rule", ""))}</div>
<div class="section-title">3. Áp dụng phân tích (Application)</div>
<div class="section-content">{escape(sections.get("application", ""))}</div>
<div class="section-title">4. Kết luận (Conclusion)</div>
<div class="section-content">{escape(sections.get("conclusion", ""))}</div>
</body>
</html>"""
