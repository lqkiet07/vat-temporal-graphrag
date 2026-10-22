# Implementation Plan: Public Service Legal Tech UI - Vietnamese VAT

## 1. Goal
Refactor the interface from generic Gemini mockups into an authentic Vietnamese Public Service Legal QA System ("Hệ thống Hỏi đáp Pháp lý Thuế GTGT"), tailored for citizens and businesses:
- Real logo: National / Public Legal Emblem (tai-xuong.png).
- Title: "Hệ thống Hỏi đáp Pháp lý Thuế GTGT".
- Clean Public Service Identity: No commercial tiers (Pro/Ultra removed).
- Guest & Login System: Default as "Khách" with Login modal; personalize greeting only after login ("Huỳnh Tấn Phúc").
- Settings Modal: Keep strictly operational controls:
  - AI Reasoning Pipeline (P3 Temporal GraphRAG / P2 Graph Engine / P1 Flat RAG)
  - Language: Tiếng Việt / English
  - Default Evaluation Date (Mốc thời gian mặc định)
  - Display Theme (Giao diện Sáng / Tối)
  - Account Sign-in / Sign-out
- Clean Background: Elegant Dong Son bronze drum watermark centered in chat canvas.
- Internal Documents tab ("Tài liệu nội bộ") in sidebar:
  - Add internal files (PDF, DOCX, TXT, XML invoice) or paste contract text.
- Comprehensive Legal Library ("Thư viện văn bản") in sidebar:
  - Categorized: Luật, Nghị định, Thông tư, Hướng dẫn nghiệp vụ.
- Top Contextual Law Drawer ("Văn bản liên quan"):
  - Dedicated to displaying ONLY articles/documents cited in the active query/answer.
- Remove: "Xuất PDF" button and "Nhiệm vụ" tab.

## 2. Steps
- [ ] 1. Update frontend/index.html title & metadata
- [ ] 2. Update App.tsx with proper logo, branding, guest/login state, and public-service layout
- [ ] 3. Implement Internal Documents drawer / upload modal
- [ ] 4. Categorize Library documents into Luật, Nghị định, Thông tư
- [ ] 5. Implement Top bar "Văn bản liên quan" contextual drawer
- [ ] 6. Streamline Settings dialog to purely functional options
- [ ] 7. Run npm run build and verify in browser
