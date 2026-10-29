import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.models import DocumentSummary, HealthResponse, QueryRequest, QueryResponse


def test_query_request_validation():
    req = QueryRequest(query="Doanh nghiệp xã hội là gì?", as_of_date="2024-01-01")
    assert req.query == "Doanh nghiệp xã hội là gì?"
    assert req.as_of_date == "2024-01-01"
    assert req.pipeline == "P3_FullSystem"
    assert req.use_llm is False
    assert req.model == "qwen2.5:7b"

    with pytest.raises(ValidationError):
        QueryRequest(query="Thiếu ngày")


def test_document_summary_model():
    doc = DocumentSummary(
        id="doc_1",
        code="59/2020/QH14",
        title="Luật Doanh nghiệp 2020",
        valid_from="2021-01-01",
        valid_to="2030-01-01",
    )
    assert doc.id == "doc_1"
    assert doc.code == "59/2020/QH14"
    assert doc.title == "Luật Doanh nghiệp 2020"
    assert doc.valid_from == "2021-01-01"
    assert doc.valid_to == "2030-01-01"

    with pytest.raises(ValidationError):
        DocumentSummary(id="doc_1", code="59/2020/QH14")


def test_health_response_model():
    health = HealthResponse(status="ok", neo4j_connected=True)
    assert health.status == "ok"
    assert health.neo4j_connected is True
    assert health.version == "1.0.0"

    health_custom = HealthResponse(status="degraded", neo4j_connected=False, version="1.1.0")
    assert health_custom.status == "degraded"
    assert health_custom.neo4j_connected is False
    assert health_custom.version == "1.1.0"

    with pytest.raises(ValidationError):
        HealthResponse(status="ok")


def test_query_response_model():
    res = QueryResponse(
        query="Quy định thành lập doanh nghiệp?",
        as_of_date="2024-01-01",
        pipeline="P3_FullSystem",
        risk_score=0,
        risk_level="LOW",
        irac_sections={"Issue": "Thành lập doanh nghiệp", "Rule": "Điều 17 Luật Doanh nghiệp"},
    )
    assert res.query == "Quy định thành lập doanh nghiệp?"
    assert res.as_of_date == "2024-01-01"
    assert res.pipeline == "P3_FullSystem"
    assert res.citations == []
    assert res.active_article_ids == []
    assert res.risk_score == 0
    assert res.risk_level == "LOW"
    assert res.warnings == []
    assert res.irac_sections == {
        "Issue": "Thành lập doanh nghiệp",
        "Rule": "Điều 17 Luật Doanh nghiệp",
    }
    assert res.llm_used is False
    assert res.raw_llm_response is None

    res_full = QueryResponse(
        query="Quy định?",
        as_of_date="2024-01-01",
        pipeline="P3_FullSystem",
        citations=["LUAT_59_2020_D17"],
        active_article_ids=["LUAT_59_2020_D17"],
        risk_score=15,
        risk_level="LOW",
        warnings=["Cảnh báo kiểm tra lại"],
        irac_sections={"Analysis": "Phân tích"},
        llm_used=True,
        raw_llm_response="Nội dung LLM",
    )
    assert res_full.citations == ["LUAT_59_2020_D17"]
    assert res_full.active_article_ids == ["LUAT_59_2020_D17"]
    assert res_full.risk_score == 15
    assert res_full.warnings == ["Cảnh báo kiểm tra lại"]
    assert res_full.llm_used is True
    assert res_full.raw_llm_response == "Nội dung LLM"


@pytest.fixture
def client():
    from src.api.main import app

    return TestClient(app)


def test_get_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["neo4j_connected"] is True


def test_get_documents_endpoint(client: TestClient):
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    for item in data:
        summary = DocumentSummary(**item)
        assert summary.id
        assert summary.code
        assert summary.title


def test_get_document_detail_success(client: TestClient):
    response = client.get("/api/documents/LUAT_48_2024")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["id"] == "LUAT_48_2024"
    assert "articles" in data
    assert isinstance(data["articles"], list)


def test_get_document_detail_not_found(client: TestClient):
    response = client.get("/api/documents/NON_EXISTENT_DOC")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_get_scenarios_endpoint(client: TestClient):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3


def test_post_query_endpoint(client: TestClient):
    payload = {
        "query": "Thuế suất phần mềm xuất khẩu năm 2026",
        "as_of_date": "2026-03-20",
        "pipeline": "P3_FullSystem",
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    res = QueryResponse(**data)
    assert res.risk_score is not None
    assert res.risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert isinstance(res.citations, list)
    assert isinstance(res.irac_sections, dict)
    assert "issue" in res.irac_sections or "Issue" in res.irac_sections


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
