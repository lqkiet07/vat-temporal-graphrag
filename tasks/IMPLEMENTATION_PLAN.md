# Implementation Plan - Upgrade Chat: Domain Guardrail, Strict Search, and LLM Integration

## 1. Goal
Upgrade the chat pipeline in `vat-temporal-graphrag` on branch `feature/upgradeChat`:
1. Implement a **Domain Guardrail** to detect out-of-domain queries (e.g. "thuật toán quy hoạch động", general trivia, code) and return polite guidance instead of false tax citations.
2. Improve **Lucene Full-text Search & Vector Fusion**: Use boolean `AND` / phrase queries so individual common syllables like "quy", "động" do not match unrelated queries.
3. Enhance **LLM Integration**: Support Ollama (local) and cloud LLM APIs (Gemini/OpenAI) for real IRAC comprehension with out-of-scope discernment.

## 2. Architecture & Design Decisions
- **Domain Guardrail (`src/verifier/guardrails.py`)**:
  - Deterministic entity & keyword checker for Vietnamese tax, legal, and commerce domain terms.
  - If a query is clearly out of domain (e.g. computer science algorithm, biology, weather) and contains 0 domain anchor keywords:
    - Flag query as `is_out_of_domain = True`.
    - Provide polite refusal: *"Câu hỏi của bạn không thuộc phạm vi điều chỉnh của Hệ thống Pháp lý Thuế Giá trị gia tăng (GTGT). Vui lòng đặt câu hỏi liên quan đến chính sách thuế, thuế suất hoặc quy định hóa đơn chứng từ."*
    - Set `risk_score = 0`, empty citations, and clear guidance.
- **Strict Full-text Lucene Querying (`src/engine/hybrid_retriever.py`)**:
  - Transform cleaned query tokens to Lucene boolean queries: combine domain keywords with `AND` so that multi-word queries require matching meaningful terms, not arbitrary `OR` matches on common words like "quy" or "động".
  - Add similarity threshold filter for vector search if full-text returns 0 matches.
- **Enhanced LLM Client (`src/engine/llm_client.py` & `src/engine/prompt.py`)**:
  - Support Ollama local endpoint and Gemini API via standard `urllib` / `httpx`.
  - Add explicit negative constraint to prompt: if the retrieved tax laws do not govern the user's question, the model must explicitly state that the tax articles do not regulate this matter.
- **Frontend Integration (`frontend/src/app/api.ts` & `App.tsx`)**:
  - Support out-of-domain response rendering cleanly (no false citation badges, friendly guidance).
  - Add `use_llm` toggle in Settings modal so user can switch between Deterministic and LLM modes.

## 3. Implementation Steps
1. [x] Git branch created: `feature/upgradeChat`.
2. [ ] Step 1: Implement `src/verifier/guardrails.py` with comprehensive VAT domain dictionary & regex checkers.
3. [ ] Step 2: Integrate guardrail into `src/ui/demo_service.py` and `src/api/routes.py`.
4. [ ] Step 3: Upgrade `src/engine/hybrid_retriever.py` with boolean `AND` Lucene query formatting and score thresholding.
5. [ ] Step 4: Upgrade `src/engine/llm_client.py` and `src/engine/prompt.py` to support Gemini API / Ollama and negative constraint reasoning.
6. [ ] Step 5: Update frontend `api.ts` and `App.tsx` with out-of-domain display handling and `use_llm` setting toggle.
7. [ ] Step 6: Verify backend tests with `pytest` and frontend build with `npm run build`.
8. [ ] Step 7: Test in browser using `browser_subagent` with "thuật toán quy hoạch động", "hi", and real tax queries.

## 4. Acceptance Criteria
- Querying "thuật toán quy hoạch động" returns polite out-of-domain refusal with 0 citations and 0 false warnings.
- Querying "Xuất khẩu phần mềm năm 2026" still correctly retrieves Điều 9 Luật 48, Điều 5 NĐ 181, TT 69 with 100% precision.
- Querying "bẫy thời gian trước 01/07/2025" still correctly detects temporal validity trap.
- Pytest suite passes (116+ tests).
