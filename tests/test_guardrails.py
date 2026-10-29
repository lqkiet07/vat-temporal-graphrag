import pytest
from src.verifier.guardrails import check_query_domain


@pytest.mark.parametrize("query", ["", "   ", "\t\n  "])
def test_empty_query(query: str):
    result = check_query_domain(query)
    assert not result.is_allowed
    assert result.reason == "EMPTY_QUERY"


@pytest.mark.parametrize("query", ["hi", "xin chào", "alo"])
def test_greetings(query: str):
    result = check_query_domain(query)
    assert not result.is_allowed
    assert result.is_greeting is True
    assert result.reason == "GREETING"


@pytest.mark.parametrize(
    "query",
    [
        "Thuật toán quy hoạch động tìm đường đi ngắn nhất",
        "Dự báo thời tiết ngày mai",
        "Viết một bài thơ về mùa thu",
    ],
)
def test_pure_out_of_domain(query: str):
    result = check_query_domain(query)
    assert not result.is_allowed
    assert result.reason == "EXPLICIT_OUT_OF_DOMAIN"


def test_in_domain_nominal_tax_query():
    query = "Xuất khẩu phần mềm năm 2026 áp dụng thuế suất bao nhiêu?"
    result = check_query_domain(query)
    assert result.is_allowed is True
    assert result.reason == "IN_DOMAIN"


@pytest.mark.parametrize(
    "query",
    [
        "Dịch vụ phát triển machine learning cho đối tác nước ngoài chịu thuế suất GTGT mấy %?",
        "Gia công phần mềm bằng lập trình python xuất khẩu có chịu thuế GTGT không?",
        "Chi phí đào tạo nhân viên học react js có được khấu trừ thuế GTGT không?",
    ],
)
def test_tech_related_tax_queries_regression(query: str):
    result = check_query_domain(query)
    assert result.is_allowed is True
    assert result.reason == "IN_DOMAIN"


def test_non_domain_arbitrary_query():
    result = check_query_domain("Quả cam màu gì?")
    assert not result.is_allowed
    assert result.reason == "NO_DOMAIN_ENTITY"
