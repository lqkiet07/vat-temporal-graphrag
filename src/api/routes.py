"""API routes for VAT Legal Temporal GraphRAG."""
import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.chat_models import ChatRequest, ChatResponse
from src.api.chat_service import build_response, stream_chat
from src.api.models import DocumentSummary, HealthResponse, QueryRequest, QueryResponse
from src.graph.connection import get_neo4j_driver
from src.ui.corpus_viewer import load_corpus_tree
from src.ui.demo_service import DEMO_SCENARIOS, execute_demo_query

router = APIRouter(prefix="/api", tags=["Legal VAT API"])
api_router = router


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Verify Neo4j connectivity and return system operational status."""
    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        neo4j_connected = True
    except Exception:
        neo4j_connected = False

    status = "healthy" if neo4j_connected else "degraded"
    return HealthResponse(status=status, neo4j_connected=neo4j_connected, version="1.0.0")


@router.get("/documents", response_model=list[DocumentSummary])
def get_documents() -> list[DocumentSummary]:
    """Retrieve summaries of all legal documents in the knowledge base."""
    docs = load_corpus_tree()
    return [
        DocumentSummary(
            id=doc["id"],
            code=doc["code"],
            title=doc["title"],
            valid_from=doc["valid_from"],
            valid_to=doc["valid_to"],
        )
        for doc in docs
    ]


@router.get("/documents/{doc_id}")
def get_document_detail(doc_id: str) -> dict:
    """Retrieve full document detail by unique document identifier."""
    docs = load_corpus_tree()
    for doc in docs:
        if doc.get("id") == doc_id:
            return doc
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/scenarios", response_model=list[dict])
def get_scenarios() -> list[dict]:
    """Retrieve pre-configured demo scenarios."""
    return DEMO_SCENARIOS


@router.post("/query", response_model=QueryResponse)
def post_query(req: QueryRequest) -> QueryResponse:
    """Execute legal query retrieval, temporal verification, and risk analysis."""
    result = execute_demo_query(
        query=req.query,
        as_of_date=req.as_of_date,
        pipeline=req.pipeline,
        use_llm=req.use_llm,
        model=req.model,
    )
    return QueryResponse(**result)


def _sse_frame(name: str, payload: dict) -> str:
    """Format one server-sent event frame."""
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
def post_chat(req: ChatRequest) -> ChatResponse:
    """Answer a VAT Copilot question with citations and risk scoring."""
    return build_response(req.messages, as_of_date=req.as_of_date, model=req.model)


@router.post("/chat/stream")
def post_chat_stream(req: ChatRequest) -> StreamingResponse:
    """Answer a VAT Copilot question as a server-sent event stream."""
    events = stream_chat(req.messages, as_of_date=req.as_of_date, model=req.model)

    def event_stream() -> Iterator[str]:
        try:
            for name, payload in events:
                yield _sse_frame(name, payload)
        except Exception as exc:
            yield _sse_frame("error", {"message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

