# Task Tracking: Upgrade Chat Pipeline (feature/upgradeChat)

- [x] Branch `feature/upgradeChat` created and checked out
- [x] Implement `src/verifier/guardrails.py` (Domain Guardrail for VAT legal queries)
- [x] Connect Guardrail to `src/ui/demo_service.py` & API endpoint
- [x] Upgrade `src/engine/hybrid_retriever.py` with Lucene bigram/AND phrase querying & score boosting
- [x] Enhance `src/engine/llm_client.py` and `prompt.py` for Gemini/OpenAI/Ollama with out-of-scope discernment
- [x] Update frontend `frontend/src/app/api.ts` and `App.tsx` (LLM toggle + clean guardrail refusal card)
- [x] Run backend tests (`pytest`: 115 passed) and verify frontend build (`npm run build`: 0 errors)
- [x] Test in browser with "thuật toán quy hoạch động" and verify polite refusal (verified in browser)
