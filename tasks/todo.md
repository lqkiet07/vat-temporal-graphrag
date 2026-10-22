# Task Tracking: Refactor Public Legal Service UI (VAT Temporal GraphRAG)

- [x] Update index.html title to "Hệ thống Hỏi đáp Pháp lý Thuế GTGT" and add emblem favicon
- [x] Replace header and sidebar branding with tai-xuong.png logo and public service title
- [x] Remove "Xuất PDF" button completely
- [x] Remove "Nhiệm vụ" segmented pill button completely
- [x] Implement Guest vs Authenticated state (Guest by default, modal login to Huỳnh Tấn Phúc)
- [x] Refactor Settings modal to only include: Model, Language, Default Date, Theme, Login/Logout
- [x] Build Categorized Library ("Thư viện văn bản") with sections (Tất cả, Luật, Nghị định, Thông tư)
- [x] Link Top bar "Văn bản liên quan" strictly to cited articles of active query
- [x] Remove "Văn bản nội bộ" feature and UI elements completely as requested by user
- [x] Start Neo4j container & seed 5 legal documents, 76 articles, temporal relations into graph
- [x] Connect React frontend with FastAPI backend (`/api/query`, `/api/health`, `/api/documents`)
- [x] Handle conversational greetings (e.g. "hi", "xin chào") with polite introduction and usage guidance
- [x] Verify build with npm run build (0 errors) & capture browser screenshots
