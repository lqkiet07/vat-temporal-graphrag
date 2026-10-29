"""Pure domain helpers for VAT Copilot: scope classification, date resolution, query rewriting.

This module is intentionally free of I/O: no network calls, no database access and no
imports from the API layer, so its behaviour is fully deterministic and unit testable.
"""
import calendar
import re
from dataclasses import dataclass
from typing import Literal

ScopeKind = Literal["vat", "greeting", "out_of_scope"]

VAT_KEYWORDS: tuple[str, ...] = (
    "thuế",
    "gtgt",
    "vat",
    "hóa đơn",
    "khấu trừ",
    "hoàn thuế",
    "xuất khẩu",
    "nhập khẩu",
    "kê khai",
    "mã số thuế",
    "miễn giảm",
    "giảm trừ",
    "thuế suất",
)

OUT_OF_SCOPE_KEYWORDS: tuple[str, ...] = (
    "ly hôn",
    "hình sự",
    "đất đai",
    "thừa kế",
    "lao động",
    "tố tụng",
    "chứng khoán",
    "lưu trú",
    "bảo hiểm xã hội",
    "cướp",
    "bị cáo",
    "tội phạm",
    "đánh bạc",
    "ma túy",
)

GREETING_KEYWORDS: tuple[str, ...] = ("chào", "hello", "hey")

_GREETING_MAX_CHARS = 40
_FOLLOW_UP_MAX_CHARS = 25
_QUERY_JOINER = " ; "
_MIN_YEAR = 2000
_MAX_YEAR = 2100

_DAY_PATTERN = re.compile(r"ngày\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
_MONTH_PATTERN = re.compile(r"tháng\s+(\d{1,2})[/-](\d{4})")
_YEAR_PATTERN = re.compile(r"năm\s+(\d{4})")


@dataclass(frozen=True)
class ScopeDecision:
    """Outcome of the scope classification of a user message."""

    kind: ScopeKind
    in_scope: bool
    reason: str


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace so keyword matching ignores formatting."""
    return " ".join(text.lower().split())


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Report whether the text contains at least one of the given keywords."""
    return any(keyword in text for keyword in keywords)


def classify(text: str) -> ScopeDecision:
    """Classify a user message as VAT question, greeting or out-of-scope request."""
    lowered = text.lower()
    if _contains_any(lowered, VAT_KEYWORDS):
        return ScopeDecision(
            kind="vat",
            in_scope=True,
            reason="Câu hỏi chứa từ khóa thuế GTGT nên được xử lý theo phạm vi thuế.",
        )

    normalized = _normalize(text)
    if len(normalized) <= _GREETING_MAX_CHARS and _contains_any(normalized, GREETING_KEYWORDS):
        return ScopeDecision(
            kind="greeting",
            in_scope=False,
            reason="Câu chào ngắn, chưa có nội dung pháp lý cần tra cứu.",
        )

    if _contains_any(lowered, OUT_OF_SCOPE_KEYWORDS):
        return ScopeDecision(
            kind="out_of_scope",
            in_scope=False,
            reason="Câu hỏi nằm ngoài phạm vi thuế GTGT của trợ lý.",
        )

    return ScopeDecision(
        kind="vat",
        in_scope=True,
        reason="Không phát hiện từ khóa ngoài phạm vi nên áp dụng mặc định thuế GTGT.",
    )


def _is_valid_year(year: int) -> bool:
    """Report whether the year falls inside the supported legal corpus range."""
    return _MIN_YEAR <= year <= _MAX_YEAR


def _to_iso_date(year: int, month: int, day: int) -> str | None:
    """Convert a date triple to ISO format, or None when the date is not a real date."""
    if not _is_valid_year(year) or not 1 <= month <= 12:
        return None
    if not 1 <= day <= calendar.monthrange(year, month)[1]:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _resolve_day(lowered: str) -> str | None:
    """Resolve an explicit 'ngày DD/MM/YYYY' reference."""
    match = _DAY_PATTERN.search(lowered)
    if match is None:
        return None
    day, month, year = (int(group) for group in match.groups())
    return _to_iso_date(year, month, day)


def _resolve_month(lowered: str) -> str | None:
    """Resolve a 'tháng MM/YYYY' reference to the last day of that month."""
    match = _MONTH_PATTERN.search(lowered)
    if match is None:
        return None
    month, year = int(match.group(1)), int(match.group(2))
    if not _is_valid_year(year) or not 1 <= month <= 12:
        return None
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-{last_day:02d}"


def _resolve_year(lowered: str) -> str | None:
    """Resolve a 'năm YYYY' reference to the end of that year."""
    match = _YEAR_PATTERN.search(lowered)
    if match is None:
        return None
    year = int(match.group(1))
    if not _is_valid_year(year):
        return None
    return f"{year:04d}-12-31"


def resolve_date(text: str, default: str) -> str:
    """Resolve the effective reference date mentioned in the text, else keep the default."""
    lowered = text.lower()
    for resolver in (_resolve_day, _resolve_month, _resolve_year):
        resolved = resolver(lowered)
        if resolved is not None:
            return resolved
    return default


def rewrite_query(history: list[tuple[str, str]]) -> str:
    """Rewrite the conversation history into a single retrieval query.

    A short follow-up turn carries no subject on its own, so the previous user turn is
    prepended to keep the retrieval anchored on the same legal topic.
    """
    user_turns = [content for role, content in history if role == "user"]
    if not user_turns:
        return ""
    last_turn = user_turns[-1]
    if len(last_turn) <= _FOLLOW_UP_MAX_CHARS and len(user_turns) >= 2:
        return f"{user_turns[-2]}{_QUERY_JOINER}{last_turn}"
    return last_turn
