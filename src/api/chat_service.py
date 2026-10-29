"""Chat orchestration for the VAT Copilot.

The service is the single source of truth for the conversational flow: scope routing,
temporal retrieval, prompt construction, streamed generation and citation scoring.
"""
import re
import unicodedata
from collections.abc import Iterator

from src.api.chat_domain import classify, resolve_date, rewrite_query
from src.api.chat_models import ChatMessage, ChatResponse, ChatSource
from src.engine.llm_client import generate_llm_response_stream
from src.engine.models import ArticleNode
from src.engine.temporal_retriever import query_temporal_rag
from src.ui.corpus_viewer import load_corpus_tree
from src.ui.demo_service import DEMO_SCENARIOS
from src.verifier.citation_verifier import extract_citations
from src.verifier.risk_score import verify_and_score

ChatTurn = ChatMessage | dict

DEFAULT_AS_OF_DATE = "2026-09-30"
MAX_SOURCES = 15
MAX_FALLBACK_CITATIONS = 5
MAX_CLAUSE_CHARS = 1500
MAX_EXPLICIT_ARTICLES = 3
QUERY_JOINER = " ; "

_ARTICLE_REF = re.compile(r"dieu\s+(\d{1,3})\b")
_DOCUMENT_REF = re.compile(r"(?:luat|nghi dinh|thong tu)\s*(\d{1,3}(?:[/-]\d{4})?)\b")

SAMPLE_QUESTIONS: list[str] = [scenario["query"] for scenario in DEMO_SCENARIOS]

_SAMPLE_LIST = "\n".join(f"- {question}" for question in SAMPLE_QUESTIONS)

GREETING_REPLY = (
    "Chào bạn! Tôi là VAT Copilot - trợ lý tư vấn thuế GTGT của doanh nghiệp. "
    "Tôi có thể tra cứu thuế suất, hóa đơn, khấu trừ, hoàn thuế, kê khai và xuất khẩu. "
    "Bạn có thể thử các câu hỏi mẫu:\n" + _SAMPLE_LIST
)

OUT_OF_SCOPE_REPLY = (
    "Câu hỏi của bạn nằm ngoài phạm vi của VAT Copilot. "
    "Tôi chỉ tư vấn về thuế GTGT và các quy định pháp luật liên quan đến thuế GTGT. "
    "Bạn có thể thử các câu hỏi mẫu:\n" + _SAMPLE_LIST
)

NO_EVIDENCE_WARNING = (
    "Không tìm thấy căn cứ pháp lý còn hiệu lực tại thời điểm tra cứu."
)


def _normalize_messages(messages: list[ChatTurn]) -> list[tuple[str, str]]:
    """Normalize chat messages given as models or plain dicts into (role, content) pairs."""
    history: list[tuple[str, str]] = []
    for message in messages:
        if isinstance(message, dict):
            role = message.get("role", "user")
            content = message.get("content", "")
        else:
            role = getattr(message, "role", "user")
            content = getattr(message, "content", "")
        history.append((str(role), str(content)))
    return history


def _last_user_text(history: list[tuple[str, str]]) -> str:
    """Return the content of the most recent user turn, or an empty string."""
    for role, content in reversed(history):
        if role == "user":
            return content
    return ""


def _retrieve_articles(history: list[tuple[str, str]], effective_date: str) -> list[ArticleNode]:
    """Retrieve legal articles, retrying once with the two latest user turns merged."""
    articles = list(query_temporal_rag(rewrite_query(history), effective_date).articles)
    if articles:
        return articles
    user_turns = [content for role, content in history if role == "user"]
    if len(user_turns) < 2:
        return []
    retry_query = f"{user_turns[-2]}{QUERY_JOINER}{user_turns[-1]}"
    return list(query_temporal_rag(retry_query, effective_date).articles)


def _to_source(article: ArticleNode) -> ChatSource:
    """Convert a retrieved article into the public source payload."""
    return ChatSource(
        id=article.id,
        code=article.code,
        title=article.title,
        doc_id=article.doc_id,
        valid_from=article.valid_from,
        valid_to=article.valid_to,
    )


def _format_clause(clause: dict) -> str:
    """Render one clause with its points into a single readable line block."""
    content = clause.get("content") or ""
    if not content:
        return ""
    code = clause.get("code") or ""
    lines = [f"{code}: {content}".strip(": ").strip() if code else content]
    for point in clause.get("points", []):
        point_content = point.get("content") or ""
        if not point_content:
            continue
        point_code = point.get("code") or ""
        lines.append(f"  {point_code} {point_content}".strip())
    return "\n".join(lines)


def _fold(text: str) -> str:
    """Lowercase and drop Vietnamese diacritics so codes can be compared."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.replace("đ", "d").split())


def _load_corpus_index() -> dict[str, dict]:
    """Map every article id to its metadata and full clause text.

    The graph node only stores the article heading, so without this index the model
    receives titles instead of the legal wording it has to reason about.
    """
    index: dict[str, dict] = {}
    for document in load_corpus_tree():
        doc_code = document.get("code", "")
        doc_id = document.get("id", "")
        doc_valid_from = document.get("valid_from", "")
        doc_valid_to = document.get("valid_to", "")
        for article in document.get("articles", []):
            article_id = article.get("id")
            if not article_id:
                continue
            blocks = [
                block
                for block in (_format_clause(clause) for clause in article.get("clauses", []))
                if block
            ]
            index[article_id] = {
                "code": article.get("code", ""),
                "title": article.get("title", ""),
                "doc_id": doc_id,
                "doc_code": doc_code,
                "doc_title": document.get("title", ""),
                "valid_from": article.get("valid_from") or doc_valid_from,
                "valid_to": article.get("valid_to") or doc_valid_to,
                "text": "\n".join(blocks)[:MAX_CLAUSE_CHARS],
            }
    return index


def _explicit_article_ids(question: str) -> list[str]:
    """Resolve article numbers written in the question, e.g. 'Điều 9 Nghị định 181/2025'.

    A lawyer cites article numbers, so the article they name must be part of the legal
    basis even when the hybrid retriever does not rank it high.
    """
    folded = _fold(question)
    numbers = {int(value) for value in _ARTICLE_REF.findall(folded)}
    if not numbers:
        return []
    doc_hints = _DOCUMENT_REF.findall(folded)
    matched: list[str] = []
    for article_id, meta in _load_corpus_index().items():
        article_match = re.fullmatch(r"dieu\s+(\d{1,3})", _fold(meta["code"]))
        if article_match is None or int(article_match.group(1)) not in numbers:
            continue
        if doc_hints:
            doc_code = _fold(meta["doc_code"]).replace("-", "/")
            if not any(hint.replace("-", "/") in doc_code for hint in doc_hints):
                continue
        matched.append(article_id)
    return matched[:MAX_EXPLICIT_ARTICLES]


def _build_prompt(
    question: str,
    effective_date: str,
    articles: list[ArticleNode],
    explicit_ids: tuple[str, ...] = (),
) -> str:
    """Build the VAT Copilot system prompt with the legal basis to rely on."""
    corpus_index = _load_corpus_index()
    clause_index = {article_id: meta["text"] for article_id, meta in corpus_index.items()}

    direct_basis = []
    for article_id in explicit_ids:
        meta = corpus_index.get(article_id)
        if meta is None:
            continue
        direct_basis.append(
            f"- [{article_id}] {meta['code']} - {meta['title']}\n  {meta['text'] or meta['title']}"
        )

    basis = "\n".join(
        f"- [{article.id}] {article.code} - {article.title}\n"
        f"  {clause_index.get(article.id) or article.content}"
        for article in articles
    )
    direct_section = (
        "=== CĂN CỨ ĐƯỢC VIỆN DẪN TRỰC TIẾP TRONG CÂU HỎI ===\n" + "\n".join(direct_basis) + "\n\n"
        if direct_basis
        else ""
    )
    return (
        "Bạn là VAT Copilot, trợ lý tư vấn pháp luật chuyên về thuế GTGT tại Việt Nam.\n"
        "Quy tắc bắt buộc:\n"
        "1. Chỉ trả lời về thuế GTGT và các quy định pháp luật liên quan.\n"
        "2. Chỉ được dùng các căn cứ pháp lý được cung cấp dưới đây, không dùng kiến thức khác.\n"
        "3. Tuyệt đối không tự suy diễn mức thuế suất, số tiền hay ngày có hiệu lực.\n"
        "4. Mỗi căn cứ sử dụng phải được trích dẫn theo định dạng [DOC_ID_D...], "
        "ví dụ [LUAT_48_2024_D10].\n"
        "5. Trả lời bằng tiếng Việt, ngắn gọn, đúng trọng tâm và không lặp lại câu hỏi.\n"
        "6. Nếu căn cứ không đủ để kết luận thì nói rõ là chưa đủ căn cứ.\n\n"
        f"=== CÂU HỎI ===\n{question}\n\n"
        f"=== THỜI ĐIỂM TRA CỨU (as_of_date) ===\n{effective_date}\n\n"
        f"{direct_section}"
        f"=== CĂN CỨ PHÁP LÝ ===\n{basis}\n\n"
        "=== CÂU TRẢ LỜI ===\n"
    )


def _fallback_answer(articles: list[ArticleNode]) -> str:
    """Build the deterministic answer used when no LLM token could be produced."""
    references = " ".join(f"[{article.id}]" for article in articles[:MAX_FALLBACK_CITATIONS])
    return (
        "Mô hình ngôn ngữ không phản hồi, nên tôi chỉ liệt kê các căn cứ pháp lý "
        f"liên quan tại thời điểm tra cứu: {references}. "
        "Vui lòng tra cứu trực tiếp nội dung các điều khoản nêu trên."
    )


def _direct_reply_events(reply: str, effective_date: str) -> Iterator[tuple[str, dict]]:
    """Emit the event sequence for a reply that needs neither retrieval nor generation."""
    yield ("meta", {"as_of_date": effective_date, "sources": []})
    yield ("token", {"delta": reply})
    response = ChatResponse(
        message=reply,
        citations=[],
        sources=[],
        risk_score=0,
        risk_level="LOW",
        warnings=[],
        llm_used=False,
        in_scope=False,
        as_of_date=effective_date,
    )
    yield ("done", response.model_dump())


def _load_documents() -> list[dict]:
    """Return the corpus document metadata used to explain temporal gaps."""
    documents = []
    for document in load_corpus_tree():
        documents.append(
            {
                "title": document.get("title", ""),
                "code": document.get("code", ""),
                "valid_from": document.get("valid_from", ""),
            }
        )
    return documents


def _next_effective_document(as_of_date: str) -> dict | None:
    """Find the earliest document that becomes effective after the reference date."""
    candidates = [
        document
        for document in _load_documents()
        if document["valid_from"] and document["valid_from"] > as_of_date
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda document: document["valid_from"])


def _no_evidence_message(as_of_date: str) -> str:
    """Explain why no legal basis applies, naming the next document in force."""
    upcoming = _next_effective_document(as_of_date)
    if upcoming is None:
        return (
            f"Tại thời điểm {as_of_date}, kho dữ liệu pháp luật đóng băng ngày 30/09/2026 "
            "không có điều khoản nào còn hiệu lực để áp dụng cho tình huống này.\n"
            "Bạn có thể thử các câu hỏi mẫu:\n" + _SAMPLE_LIST
        )
    label = upcoming["code"] or upcoming["title"]
    return (
        f"Tại thời điểm {as_of_date}, chưa có văn bản nào trong kho dữ liệu (đóng băng ngày "
        f"30/09/2026) có hiệu lực để áp dụng cho tình huống này. Văn bản sớm nhất có hiệu lực "
        f"sau thời điểm tra cứu là {label} (hiệu lực từ {upcoming['valid_from']}), nên sự việc "
        "xảy ra trước mốc đó sẽ phải áp dụng quy định trước đây — vốn không nằm trong kho "
        "dữ liệu của hệ thống.\nBạn có thể thử các câu hỏi mẫu:\n" + _SAMPLE_LIST
    )


def _no_evidence_events(effective_date: str) -> Iterator[tuple[str, dict]]:
    """Emit the event sequence for a question with no matching legal basis."""
    message = _no_evidence_message(effective_date)
    yield ("meta", {"as_of_date": effective_date, "sources": []})
    yield ("token", {"delta": message})
    response = ChatResponse(
        message=message,
        citations=[],
        sources=[],
        risk_score=50,
        risk_level="MEDIUM",
        warnings=[NO_EVIDENCE_WARNING],
        llm_used=False,
        in_scope=True,
        as_of_date=effective_date,
    )
    yield ("done", response.model_dump())


def _explicit_sources(explicit_ids: tuple[str, ...]) -> list[ChatSource]:
    """Build source entries for the articles the question cites directly."""
    corpus_index = _load_corpus_index()
    sources: list[ChatSource] = []
    for article_id in explicit_ids:
        meta = corpus_index.get(article_id)
        if meta is None:
            continue
        sources.append(
            ChatSource(
                id=article_id,
                code=meta["code"],
                title=meta["title"],
                doc_id=meta["doc_id"],
                valid_from=str(meta["valid_from"]),
                valid_to=str(meta["valid_to"]),
            )
        )
    return sources


def _answer_events(
    question: str,
    effective_date: str,
    articles: list[ArticleNode],
    model: str,
    explicit_ids: tuple[str, ...] = (),
) -> Iterator[tuple[str, dict]]:
    """Emit the event sequence for an answer backed by retrieved legal articles."""
    selected = articles[:MAX_SOURCES]
    sources = _explicit_sources(explicit_ids) + [_to_source(article) for article in selected]
    unique_sources: list[ChatSource] = []
    seen_ids: set[str] = set()
    for source in sources:
        if source.id in seen_ids:
            continue
        seen_ids.add(source.id)
        unique_sources.append(source)
    sources = unique_sources
    yield ("meta", {"as_of_date": effective_date, "sources": [s.model_dump() for s in sources]})

    prompt = _build_prompt(question, effective_date, selected, explicit_ids)
    answer_parts: list[str] = []
    for delta in generate_llm_response_stream(prompt, model=model):
        answer_parts.append(delta)
        yield ("token", {"delta": delta})

    answer = "".join(answer_parts).strip()
    llm_used = bool(answer)
    if not answer:
        answer = _fallback_answer(selected)
        yield ("token", {"delta": answer})

    citations = extract_citations(answer) or [a.id for a in selected[:MAX_FALLBACK_CITATIONS]]
    verification = verify_and_score(" ".join(f"[{c}]" for c in citations), effective_date)
    response = ChatResponse(
        message=answer,
        citations=citations,
        sources=sources,
        risk_score=verification.risk_score,
        risk_level=verification.risk_level,
        warnings=verification.warnings,
        llm_used=llm_used,
        in_scope=True,
        as_of_date=effective_date,
    )
    yield ("done", response.model_dump())


def stream_chat(
    messages: list[ChatTurn],
    as_of_date: str | None = None,
    model: str = "qwen2.5:7b",
) -> Iterator[tuple[str, dict]]:
    """Stream the chat answer as (event_name, payload) tuples."""
    history = _normalize_messages(messages)
    last_user_text = _last_user_text(history)
    effective_date = resolve_date(last_user_text, as_of_date or DEFAULT_AS_OF_DATE)
    decision = classify(last_user_text)

    if decision.kind == "greeting":
        yield from _direct_reply_events(GREETING_REPLY, effective_date)
        return
    if decision.kind == "out_of_scope":
        yield from _direct_reply_events(OUT_OF_SCOPE_REPLY, effective_date)
        return

    articles = _retrieve_articles(history, effective_date)
    if not articles:
        yield from _no_evidence_events(effective_date)
        return
    explicit_ids = tuple(_explicit_article_ids(last_user_text))
    yield from _answer_events(last_user_text, effective_date, articles, model, explicit_ids)


def build_response(
    messages: list[ChatTurn],
    as_of_date: str | None = None,
    model: str = "qwen2.5:7b",
) -> ChatResponse:
    """Build the final chat response by consuming the streamed events."""
    final_payload: dict | None = None
    for name, payload in stream_chat(messages, as_of_date=as_of_date, model=model):
        if name == "done":
            final_payload = payload
    if final_payload is None:
        fallback_date = as_of_date or DEFAULT_AS_OF_DATE
        return ChatResponse(
            message=_no_evidence_message(fallback_date),
            risk_score=50,
            risk_level="MEDIUM",
            in_scope=True,
            as_of_date=fallback_date,
        )
    return ChatResponse(**final_payload)
