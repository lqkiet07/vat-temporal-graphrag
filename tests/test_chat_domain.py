"""Behaviour tests for the pure VAT Copilot domain helpers."""
from src.api.chat_domain import classify, resolve_date, rewrite_query


def test_classify_vat_question_returns_in_scope_vat():
    decision = classify("Thuế suất xuất khẩu phần mềm năm 2026 là bao nhiêu?")
    assert decision.kind == "vat"
    assert decision.in_scope is True


def test_classify_criminal_question_returns_out_of_scope():
    decision = classify("Người bị cáo cướp tài sản thì xử lý thế nào?")
    assert decision.kind == "out_of_scope"
    assert decision.in_scope is False


def test_classify_greeting_returns_out_of_scope_greeting():
    decision = classify("Chào bạn")
    assert decision.kind == "greeting"
    assert decision.in_scope is False


def test_classify_keeps_vat_priority_over_greeting_keyword():
    decision = classify("Chào bạn, thuế suất GTGT năm 2026 là bao nhiêu?")
    assert decision.kind == "vat"
    assert decision.in_scope is True


def test_resolve_date_reads_explicit_day():
    assert resolve_date("Sự việc ngày 15/05/2024", "2026-09-30") == "2024-05-15"


def test_resolve_date_reads_explicit_day_with_dashes():
    assert resolve_date("Sự việc ngày 15-05-2024", "2026-09-30") == "2024-05-15"


def test_resolve_date_uses_last_day_of_detected_month():
    assert resolve_date("trong tháng 5/2024", "2026-09-30") == "2024-05-31"


def test_resolve_date_uses_year_end_when_only_year_detected():
    assert resolve_date("áp dụng trong năm 2024", "2026-09-30") == "2024-12-31"


def test_resolve_date_returns_default_when_no_date_detected():
    assert resolve_date("thuế suất là bao nhiêu", "2026-09-30") == "2026-09-30"


def test_resolve_date_ignores_invalid_day_and_month():
    assert resolve_date("ngày 32/13/2024", "2026-09-30") == "2026-09-30"


def test_resolve_date_ignores_invalid_day_in_valid_month():
    assert resolve_date("ngày 31/02/2024", "2026-09-30") == "2026-09-30"


def test_rewrite_query_combines_short_follow_up_with_previous_turn():
    history = [
        ("user", "Thuế suất xuất khẩu phần mềm là bao nhiêu?"),
        ("user", "tháng 5/2024 thì sao?"),
    ]
    result = rewrite_query(history)
    assert "5/2024" in result
    assert "xuất khẩu" in result


def test_rewrite_query_returns_last_user_turn_when_long_enough():
    history = [("user", "Thuế suất xuất khẩu phần mềm là bao nhiêu?")]
    assert rewrite_query(history) == "Thuế suất xuất khẩu phần mềm là bao nhiêu?"


def test_rewrite_query_returns_empty_when_no_user_turn():
    assert rewrite_query([("assistant", "Tôi có thể giúp gì?")]) == ""
