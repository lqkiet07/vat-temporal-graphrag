"""Tests for demo service and UI corpus viewer components."""
from unittest.mock import patch
import pytest
from src.ui.corpus_viewer import (
    load_corpus_tree,
    render_article_html,
    render_document_tree_html,
)
from src.ui.demo_service import (
    DEMO_SCENARIOS,
    execute_demo_query,
    generate_printable_html,
)


@pytest.fixture
def sample_article() -> dict:
    return {
        "id": "LUAT_48_2024_D1",
        "code": "Dieu 1",
        "title": "Pham vi dieu chinh",
        "lead": "Luat nay quy dinh ve doi tuong chiu thue...",
        "clauses": [
            {
                "id": "LUAT_48_2024_D1_K1",
                "code": "Khoan 1",
                "content": "Noi dung khoan 1",
                "points": [
                    {
                        "id": "LUAT_48_2024_D1_K1_a",
                        "code": "Diem a",
                        "content": "Noi dung diem a",
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_document(sample_article: dict) -> dict:
    return {
        "id": "LUAT_48_2024",
        "code": "48/2024/QH15",
        "title": "Luat Thue gia tri gia tang",
        "chapters": [
            {
                "id": "LUAT_48_2024_CI",
                "code": "Chuong I",
                "title": "Chuong I NHUNG QUY DINH CHUNG",
                "articles": [sample_article],
            }
        ],
    }


def test_load_corpus_tree():
    docs = load_corpus_tree("data/processed/vat_corpus.json")
    assert isinstance(docs, list)
    assert len(docs) > 0
    assert any(d.get("id") == "LUAT_48_2024" for d in docs)
    cached = load_corpus_tree("data/processed/vat_corpus.json")
    assert cached is docs


def test_render_article_html_normal(sample_article: dict):
    html = render_article_html(sample_article, active_ids=[])
    assert 'id="art-LUAT_48_2024_D1"' in html
    assert "highlighted-article" not in html
    assert "Dieu 1" in html
    assert "Pham vi dieu chinh" in html
    assert "Khoan 1" in html
    assert "Noi dung khoan 1" in html
    assert "Diem a" in html
    assert "Noi dung diem a" in html


def test_render_article_html_highlighted(sample_article: dict):
    active_ids = ["LUAT_48_2024_D1"]
    html = render_article_html(sample_article, active_ids=active_ids)
    assert 'id="art-LUAT_48_2024_D1"' in html
    assert "highlighted-article" in html
    assert "background-color: #fff9db" in html
    assert "border-left: 4px solid #f59f00" in html
    assert "Dieu 1" in html
    assert "Pham vi dieu chinh" in html


def test_render_document_tree_html(sample_document: dict):
    html = render_document_tree_html(sample_document, active_ids=["LUAT_48_2024_D1"])
    assert "Luat Thue gia tri gia tang" in html
    assert "48/2024/QH15" in html
    assert "Chuong I" in html
    assert 'id="art-LUAT_48_2024_D1"' in html
    assert "highlighted-article" in html


def test_demo_scenarios_structure():
    assert isinstance(DEMO_SCENARIOS, list)
    assert len(DEMO_SCENARIOS) == 3
    colors = [s.get("badge_color") for s in DEMO_SCENARIOS]
    assert colors == ["green", "red", "yellow"]
    for s in DEMO_SCENARIOS:
        for k in ("name", "query", "as_of_date", "badge_color"):
            assert k in s
            assert isinstance(s[k], str)
            assert len(s[k]) > 0


def test_execute_demo_query_p3():
    scenario = DEMO_SCENARIOS[0]
    res = execute_demo_query(scenario["query"], scenario["as_of_date"], pipeline="P3_FullSystem")
    assert isinstance(res, dict)
    assert res["query"] == scenario["query"]
    assert res["as_of_date"] == scenario["as_of_date"]
    assert res["pipeline"] == "P3_FullSystem"
    assert "citations" in res
    assert "active_article_ids" in res
    assert "risk_score" in res
    assert "risk_level" in res
    assert "warnings" in res
    assert "irac_sections" in res
    assert isinstance(res["irac_sections"], dict)
    for sec in ("issue", "rule", "application", "conclusion"):
        assert sec in res["irac_sections"]


def test_execute_demo_query_p2():
    scenario = DEMO_SCENARIOS[2]
    res = execute_demo_query(scenario["query"], scenario["as_of_date"], pipeline="P2_TemporalGraphRAG")
    assert isinstance(res, dict)
    assert res["pipeline"] == "P2_TemporalGraphRAG"
    assert "citations" in res
    assert "risk_score" in res


def test_execute_demo_query_p1():
    scenario = DEMO_SCENARIOS[1]
    res = execute_demo_query(scenario["query"], scenario["as_of_date"], pipeline="P1_FlatRAG")
    assert isinstance(res, dict)
    assert res["pipeline"] == "P1_FlatRAG"
    assert "citations" in res
    assert "risk_score" in res


def test_generate_printable_html():
    query = "Doanh nghiệp xuất khẩu thuế suất bao nhiêu?"
    as_of_date = "2026-03-20"
    result = {
        "query": query,
        "as_of_date": as_of_date,
        "pipeline": "P3_FullSystem",
        "citations": ["LUAT_48_2024_D9"],
        "active_article_ids": ["LUAT_48_2024_D9"],
        "risk_score": 0,
        "risk_level": "LOW",
        "warnings": [],
        "irac_sections": {
            "issue": "Xác định thuế suất GTGT xuất khẩu.",
            "rule": "Căn cứ [LUAT_48_2024_D9].",
            "application": "Dịch vụ phần mềm thuộc nhóm 0%.",
            "conclusion": "Thuế suất 0%.",
        },
    }
    html = generate_printable_html(query, as_of_date, result)
    assert isinstance(html, str)
    assert "@media print" in html
    assert query in html
    assert "0" in html or "LOW" in html
    assert "LUAT_48_2024_D9" in html
    assert "Xác định thuế suất GTGT xuất khẩu." in html


def test_execute_demo_query_with_llm_success():
    query = "Doanh nghiệp tại Cần Thơ xuất khẩu phần mềm sang Nhật Bản vào tháng 03/2026 áp dụng thuế suất thuế GTGT bao nhiêu?"
    as_of_date = "2026-03-20"
    mock_llm_text = (
        "1. Issue: Vấn đề thuế 0%\n"
        "2. Rule: [LUAT_48_2024_D9]\n"
        "3. Application: Phù hợp\n"
        "4. Conclusion: Áp dụng 0%."
    )
    with patch("src.ui.demo_service.generate_llm_response", return_value=mock_llm_text):
        result = execute_demo_query(
            query,
            as_of_date,
            pipeline="P3_FullSystem",
            use_llm=True,
            model="qwen2.5:7b",
        )
    assert result["llm_used"] is True
    assert result["raw_llm_response"] is not None
    assert "LUAT_48_2024_D9" in result["citations"]
    assert "risk_level" in result


def test_execute_demo_query_with_llm_fallback():
    query = "Doanh nghiệp tại Cần Thơ xuất khẩu phần mềm sang Nhật Bản vào tháng 03/2026 áp dụng thuế suất thuế GTGT bao nhiêu?"
    as_of_date = "2026-03-20"
    with patch("src.ui.demo_service.generate_llm_response", return_value=None):
        result = execute_demo_query(
            query,
            as_of_date,
            pipeline="P3_FullSystem",
            use_llm=True,
            model="qwen2.5:7b",
        )
    assert result["llm_used"] is False
    assert result["raw_llm_response"] is None
    assert "irac_sections" in result
    for sec in ("issue", "rule", "application", "conclusion"):
        assert sec in result["irac_sections"]

