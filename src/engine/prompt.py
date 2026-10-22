"""IRAC prompt generation module with domain relevance discernment."""
from src.engine.models import ArticleNode


def build_irac_prompt(
    query: str, as_of_date: str, articles: list[ArticleNode]
) -> str:
    """Build IRAC-formatted prompt containing active legal rules."""
    rules = []
    for art in articles:
        related = f" (Sửa đổi/liên quan: {', '.join(art.related_ids)})" if art.related_ids else ""
        rules.append(f"- [{art.id}] {art.code} - {art.title}{related}\n  {art.content}")

    rule_text = (
        "\n\n".join(rules)
        if rules
        else "Không tìm thấy điều khoản pháp luật nào còn hiệu lực phù hợp tại thời điểm tra cứu."
    )

    return (
        "Bạn là Chuyên gia Trợ lý Pháp lý Thuế Giá trị gia tăng (GTGT) Việt Nam chuyên nghiệp.\n"
        "Hãy phân tích và trả lời câu hỏi dựa trên các quy định pháp luật được cung cấp.\n"
        "Bắt buộc tuân thủ phương pháp lập luận IRAC (Issue, Rule, Application, Conclusion):\n"
        "1. Issue: Nêu rõ vấn đề pháp lý cần giải quyết.\n"
        "2. Rule: Liệt kê chính xác quy phạm pháp luật áp dụng, bắt buộc dùng mã trích dẫn dạng [DOC_ID_D...] (ví dụ: [LUAT_48_2024_D9], [ND_181_2025_D5]). Nếu không có quy phạm phù hợp, ghi rõ 'Không có quy phạm điều chỉnh'.\n"
        "3. Application: Phân tích quy định vào bối cảnh câu hỏi tại mốc thời gian quy định.\n"
        "4. Conclusion: Đưa ra câu trả lời kết luận súc tích, trực tiếp.\n\n"
        "=== QUY TẮC ĐẶC BIỆT VỀ PHẠM VI NGHIỆP VỤ ===\n"
        "- Nếu câu hỏi của người dùng KHÔNG liên quan đến thuế GTGT hoặc các quy phạm pháp luật trích xuất ở trên KHÔNG điều chỉnh tình huống được hỏi (ví dụ hỏi về toán học, tin học, đời sống, hoặc lĩnh vực khác):\n"
        "  + Tại phần Rule: Ghi rõ 'Không có căn cứ pháp luật thuế GTGT điều chỉnh nội dung này.'\n"
        "  + Tại phần Application: Nêu rõ câu hỏi không thuộc phạm vi điều chỉnh của các văn bản pháp luật về Thuế GTGT.\n"
        "  + Tại phần Conclusion: Trả lời lịch sự rằng 'Câu hỏi của bạn không thuộc phạm vi điều chỉnh của Hệ thống Pháp lý Thuế Giá trị gia tăng (GTGT). Vui lòng đặt câu hỏi liên quan đến chính sách thuế, thuế suất hoặc quy định hóa đơn chứng từ.'\n\n"
        f"=== BỐI CẢNH & VẤN ĐỀ (ISSUE) ===\n"
        f"- Câu hỏi: {query}\n"
        f"- Mốc thời gian thẩm định hiệu lực (as_of_date): {as_of_date}\n\n"
        f"=== QUY PHẠM PHÁP LUẬT HIỆU LỰC (RULE) ===\n"
        f"{rule_text}\n\n"
        "=== HƯỚNG DẪN TRÍCH DẪN ===\n"
        "Chỉ viện dẫn thông tin từ các căn cứ trên. Mọi viện dẫn căn cứ phải sử dụng tag định dạng [DOC_ID_D...] (ví dụ: [LUAT_48_2024_D9])."
    )
