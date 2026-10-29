"""Behaviour tests for the VAT Copilot HTTP endpoints."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api import chat_service
from src.api.chat_models import ChatResponse
from src.engine.models import ArticleNode
from src.verifier.models import VerificationReport, VerificationResult

VAT_QUESTION = "Áp dụng thuế suất xuất khẩu ra sao?"


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


@pytest.fixture
def client():
    from src.api.main import app

    return TestClient(app)


@pytest.fixture
def stub_backend(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        chat_service,
        "query_temporal_rag",
        lambda query, as_of_date: SimpleNamespace(articles=[_fake_article()]),
    )
    monkeypatch.setattr(
        chat_service,
        "generate_llm_response_stream",
        lambda prompt, model="qwen2.5:7b": iter(["Thuế suất 0% [LUAT_48_2024_D10]."]),
    )
    monkeypatch.setattr(
        chat_service,
        "verify_and_score",
        lambda text, as_of_date: VerificationResult(
            as_of_date=as_of_date,
            risk_score=0,
            risk_level="LOW",
            warnings=[],
            report=VerificationReport(
                as_of_date=as_of_date,
                total_citations=1,
                valid_citations=1,
                citations=[],
                is_clean=True,
            ),
        ),
    )


def _event_names(body: str) -> list[str]:
    return [
        line.removeprefix("event: ")
        for line in body.splitlines()
        if line.startswith("event: ")
    ]


def test_post_chat_stream_emits_meta_first_and_done_last(client: TestClient, stub_backend):
    response = client.post(
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": VAT_QUESTION}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"

    names = _event_names(response.text)
    assert names[0] == "meta"
    assert names[-1] == "done"
    assert "token" in names


def test_post_chat_stream_emits_error_event_instead_of_raising(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def _explode(query, as_of_date):
        raise RuntimeError("retrieval backend down")

    monkeypatch.setattr(chat_service, "query_temporal_rag", _explode)

    response = client.post(
        "/api/chat/stream",
        json={"messages": [{"role": "user", "content": VAT_QUESTION}]},
    )

    assert response.status_code == 200
    names = _event_names(response.text)
    assert names[-1] == "error"
    assert "retrieval backend down" in response.text


def test_post_chat_greeting_is_out_of_scope(client: TestClient, stub_backend):
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Chào bạn"}]},
    )

    assert response.status_code == 200
    data = response.json()
    payload = ChatResponse(**data)
    assert payload.in_scope is False
    assert payload.risk_score == 0
    assert payload.risk_level == "LOW"
    assert payload.message


def test_post_chat_returns_citations_for_vat_question(client: TestClient, stub_backend):
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": VAT_QUESTION}], "as_of_date": "2024-05-15"},
    )

    assert response.status_code == 200
    payload = ChatResponse(**response.json())
    assert payload.in_scope is True
    assert payload.citations == ["LUAT_48_2024_D10"]
    assert payload.as_of_date == "2024-05-15"
    assert payload.llm_used is True


def test_post_chat_rejects_empty_message_list(client: TestClient):
    response = client.post("/api/chat", json={"messages": []})

    assert response.status_code == 422
