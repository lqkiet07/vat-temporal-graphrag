"""Behaviour tests for the VAT Copilot chat service."""
from types import SimpleNamespace

import pytest

from src.api import chat_service
from src.api.chat_models import ChatMessage
from src.engine.llm_client import generate_llm_response_stream
from src.engine.models import ArticleNode
from src.verifier.models import VerificationReport, VerificationResult

VAT_QUESTION = "Áp dụng thuế suất xuất khẩu ra sao?"
OUT_OF_SCOPE_QUESTION = "Người bị cáo cướp tài sản thì xử lý thế nào?"


def _fake_article() -> ArticleNode:
    return ArticleNode(
        id="LUAT_48_2024_D10",
        doc_id="LUAT_48_2024",
        code="D10",
        title="Thuế suất 0%",
        content="Thuế suất 0%.",
        valid_from="2025-07-01",
        valid_to="9999-12-31",
        status="ACTIVE",
    )


def _fake_verification(as_of_date: str, score: int = 0, warnings: list[str] | None = None) -> VerificationResult:
    return VerificationResult(
        as_of_date=as_of_date,
        risk_score=score,
        risk_level="LOW" if score == 0 else "MEDIUM",
        warnings=warnings or [],
        report=VerificationReport(
            as_of_date=as_of_date,
            total_citations=1,
            valid_citations=1 if score == 0 else 0,
            citations=[],
            is_clean=score == 0,
        ),
    )


@pytest.fixture
def stub_verification(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        chat_service,
        "verify_and_score",
        lambda text, as_of_date: _fake_verification(as_of_date),
    )


@pytest.fixture
def stub_retrieval(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        chat_service,
        "query_temporal_rag",
        lambda query, as_of_date: SimpleNamespace(articles=[_fake_article()]),
    )


@pytest.fixture
def stub_llm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        chat_service,
        "generate_llm_response_stream",
        lambda prompt, model="qwen2.5:7b": iter(["Thuế suất 0% [LUAT_48_2024_D10]."]),
    )


def test_out_of_scope_question_skips_retrieval(monkeypatch: pytest.MonkeyPatch):
    def _explode(query, as_of_date):
        raise AssertionError("retrieval must not run for out-of-scope questions")

    monkeypatch.setattr(chat_service, "query_temporal_rag", _explode)

    response = chat_service.build_response([{"role": "user", "content": OUT_OF_SCOPE_QUESTION}])

    assert response.in_scope is False
    assert "thuế GTGT" in response.message
    assert response.risk_score == 0
    assert response.risk_level == "LOW"


def test_vat_question_returns_citations_and_low_risk(stub_retrieval, stub_llm, stub_verification):
    response = chat_service.build_response([{"role": "user", "content": VAT_QUESTION}])

    assert response.in_scope is True
    assert response.citations == ["LUAT_48_2024_D10"]
    assert response.risk_score == 0
    assert response.risk_level == "LOW"
    assert response.llm_used is True
    assert response.message
    assert response.sources[0].id == "LUAT_48_2024_D10"
    assert response.as_of_date == "2026-09-30"


def test_vat_question_accepts_chat_message_objects(stub_retrieval, stub_llm, stub_verification):
    response = chat_service.build_response(
        [ChatMessage(role="user", content=VAT_QUESTION)],
        as_of_date="2024-05-15",
    )

    assert response.in_scope is True
    assert response.as_of_date == "2024-05-15"
    assert response.citations == ["LUAT_48_2024_D10"]


def test_offline_llm_returns_deterministic_fallback(monkeypatch: pytest.MonkeyPatch, stub_retrieval, stub_verification):
    monkeypatch.setattr(
        chat_service,
        "generate_llm_response_stream",
        lambda prompt, model="qwen2.5:7b": iter([]),
    )

    response = chat_service.build_response([{"role": "user", "content": VAT_QUESTION}])

    assert response.llm_used is False
    assert response.message
    assert response.citations == ["LUAT_48_2024_D10"]


def test_empty_retrieval_returns_no_evidence_reply(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        chat_service,
        "query_temporal_rag",
        lambda query, as_of_date: SimpleNamespace(articles=[]),
    )

    response = chat_service.build_response([{"role": "user", "content": VAT_QUESTION}])

    assert response.in_scope is True
    assert response.risk_score == 50
    assert response.risk_level == "MEDIUM"
    assert response.llm_used is False
    assert response.citations == []
    for question in chat_service.SAMPLE_QUESTIONS:
        assert question in response.message


def test_prompt_contains_clause_text_from_corpus(monkeypatch: pytest.MonkeyPatch, stub_retrieval, stub_verification):
    corpus = [
        {
            "id": "LUAT_48_2024",
            "articles": [
                {
                    "id": "LUAT_48_2024_D10",
                    "code": "Dieu 10",
                    "title": "Thuế suất 0%",
                    "clauses": [
                        {"code": "Khoan 1", "content": "Hàng hóa xuất khẩu không chịu thuế GTGT."},
                        {"code": "Khoan 2", "content": "Dịch vụ xuất khẩu theo hợp đồng."},
                    ],
                }
            ],
        }
    ]
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: corpus)
    captured: dict[str, str] = {}

    def _capture(prompt: str, model: str = "qwen2.5:7b"):
        captured["prompt"] = prompt
        return iter(["Thuế suất 0% [LUAT_48_2024_D10]."])

    monkeypatch.setattr(chat_service, "generate_llm_response_stream", _capture)

    chat_service.build_response([{"role": "user", "content": VAT_QUESTION}])

    assert "Hàng hóa xuất khẩu không chịu thuế GTGT." in captured["prompt"]
    assert "Dịch vụ xuất khẩu theo hợp đồng." in captured["prompt"]


def test_prompt_falls_back_to_article_content_without_corpus_clause(
    monkeypatch: pytest.MonkeyPatch, stub_retrieval, stub_verification
):
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: [])
    captured: dict[str, str] = {}

    def _capture(prompt: str, model: str = "qwen2.5:7b"):
        captured["prompt"] = prompt
        return iter(["Thuế suất 0% [LUAT_48_2024_D10]."])

    monkeypatch.setattr(chat_service, "generate_llm_response_stream", _capture)

    chat_service.build_response([{"role": "user", "content": VAT_QUESTION}])

    assert "Thuế suất 0%." in captured["prompt"]


def test_explicit_article_reference_enters_the_legal_basis(monkeypatch: pytest.MonkeyPatch, stub_retrieval, stub_verification):
    corpus = [
        {
            "id": "ND_181_2025",
            "code": "181/2025/ND-CP",
            "title": "Nghi dinh 181/2025",
            "valid_from": "2025-07-01",
            "valid_to": "9999-12-31",
            "articles": [
                {
                    "id": "ND_181_2025_D9",
                    "code": "Dieu 9",
                    "title": "Hoa don, chung tu",
                    "clauses": [{"code": "Khoan 1", "content": "Ho don duoc lap khi ban hang."}],
                }
            ],
        },
        {
            "id": "LUAT_48_2024",
            "code": "48/2024/QH15",
            "title": "Luat Thuê GTGT",
            "valid_from": "2025-07-01",
            "valid_to": "9999-12-31",
            "articles": [
                {
                    "id": "LUAT_48_2024_D9",
                    "code": "Dieu 9",
                    "title": "Thue suat",
                    "clauses": [{"code": "Khoan 1", "content": "Thuê suât 0%."}],
                }
            ],
        },
    ]
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: corpus)
    captured: dict[str, str] = {}

    def _capture(prompt: str, model: str = "qwen2.5:7b"):
        captured["prompt"] = prompt
        return iter(["Cau tra loi [ND_181_2025_D9]."])

    monkeypatch.setattr(chat_service, "generate_llm_response_stream", _capture)

    response = chat_service.build_response(
        [{"role": "user", "content": "Hoa don chung tu theo Dieu 9 Nghi dinh 181/2025?"}]
    )

    assert "ND_181_2025_D9" in captured["prompt"]
    assert "Ho don duoc lap khi ban hang." in captured["prompt"]
    assert "LUAT_48_2024_D9" not in captured["prompt"]
    assert response.sources[0].id == "ND_181_2025_D9"


def test_article_reference_without_document_hint_keeps_every_match(
    monkeypatch: pytest.MonkeyPatch, stub_retrieval, stub_verification
):
    corpus = [
        {
            "id": "ND_181_2025",
            "code": "181/2025/ND-CP",
            "title": "Nghi dinh 181/2025",
            "valid_from": "2025-07-01",
            "valid_to": "9999-12-31",
            "articles": [
                {"id": "ND_181_2025_D9", "code": "Dieu 9", "title": "A", "clauses": []},
            ],
        },
        {
            "id": "LUAT_48_2024",
            "code": "48/2024/QH15",
            "title": "Luat 48/2024",
            "valid_from": "2025-07-01",
            "valid_to": "9999-12-31",
            "articles": [
                {"id": "LUAT_48_2024_D9", "code": "Dieu 9", "title": "B", "clauses": []},
            ],
        },
    ]
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: corpus)

    matched = chat_service._explicit_article_ids("Theo Dieu 9 thi ap dung the nao?")

    assert set(matched) == {"ND_181_2025_D9", "LUAT_48_2024_D9"}


def test_question_without_article_reference_has_no_explicit_articles(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: [])
    assert chat_service._explicit_article_ids("Thuê suât xuât khau la bao nhieu?") == []


def test_no_evidence_reply_explains_the_temporal_gap(monkeypatch: pytest.MonkeyPatch):
    corpus = [
        {
            "id": "LUAT_48_2024",
            "code": "48/2024/QH15",
            "title": "Luật Thuế giá trị gia tăng số 48/2024/QH15",
            "valid_from": "2025-07-01",
            "articles": [],
        }
    ]
    monkeypatch.setattr(chat_service, "load_corpus_tree", lambda *a, **k: corpus)
    monkeypatch.setattr(
        chat_service,
        "query_temporal_rag",
        lambda query, as_of_date: SimpleNamespace(articles=[]),
    )

    response = chat_service.build_response(
        [{"role": "user", "content": "thuế suất xuất khẩu dịch vụ tháng 5/2024?"}],
        as_of_date="2024-05-15",
    )

    assert response.risk_score == 50
    assert "2024-05-31" in response.message
    assert "48/2024/QH15" in response.message
    assert "2025-07-01" in response.message


def test_stream_chat_emits_meta_first_and_done_last(stub_retrieval, stub_llm, stub_verification):
    events = list(chat_service.stream_chat([{"role": "user", "content": VAT_QUESTION}]))

    assert events[0][0] == "meta"
    assert events[-1][0] == "done"
    assert events[0][1]["as_of_date"] == "2026-09-30"
    assert events[0][1]["sources"][0]["id"] == "LUAT_48_2024_D10"
    assert any(name == "token" for name, _ in events)


class _FakeStreamResponse:
    def __init__(self, lines: list[bytes]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def __iter__(self):
        return iter(self._lines)


def test_generate_llm_response_stream_yields_response_chunks(monkeypatch: pytest.MonkeyPatch):
    body = [
        b'{"response": "Thu\xe1\xba\xbf ", "done": false}\n',
        b'{"response": "0%", "done": true}\n',
    ]
    captured = {}

    def _fake_urlopen(req, timeout=None):
        captured["payload"] = req.data.decode("utf-8")
        captured["url"] = req.full_url
        return _FakeStreamResponse(body)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    chunks = list(generate_llm_response_stream("prompt", model="qwen2.5:7b"))

    assert chunks == ["Thuế ", "0%"]
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert '"stream": true' in captured["payload"]


def test_generate_llm_response_stream_stops_silently_on_error(monkeypatch: pytest.MonkeyPatch):
    def _fake_urlopen(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    assert list(generate_llm_response_stream("prompt")) == []
