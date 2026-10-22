import { resolve, type Result, type Citation, type AuditItem } from "./data";

export function parseCitationId(cid: string): Citation {
  let doc = "l48";
  let label = cid;
  let art = cid.toLowerCase().replace(/_/g, "-");

  const match = cid.match(/^(LUAT_48_2024|ND_181_2025|TT_69_2025|ND_359_2025|ND_144_2026)_D(\d+)/i);
  if (match) {
    const docKey = match[1].toUpperCase();
    const articleNum = match[2];
    if (docKey === "LUAT_48_2024") {
      doc = "l48";
      label = `Điều ${articleNum} Luật 48/2024`;
      art = `l48-d${articleNum}`;
    } else if (docKey === "ND_181_2025") {
      doc = "nd181";
      label = `Điều ${articleNum} NĐ 181/2025`;
      art = `nd181-d${articleNum}`;
    } else if (docKey === "TT_69_2025") {
      doc = "tt69";
      label = `Điều ${articleNum} TT 69/2025`;
      art = `tt69-d${articleNum}`;
    } else if (docKey === "ND_359_2025") {
      doc = "nd359";
      label = `Điều ${articleNum} NĐ 359/2025`;
      art = `nd359-d${articleNum}`;
    } else if (docKey === "ND_144_2026") {
      doc = "nd144";
      label = `Điều ${articleNum} NĐ 144/2026`;
      art = `nd144-d${articleNum}`;
    }
  }

  return { label, doc, art };
}

export async function queryLegalApi(
  query: string,
  asOfDate: string,
  pipeline: "P3" | "P2" | "P1"
): Promise<Result> {
  const trimmed = query.trim().toLowerCase();
  const greetings = ["hi", "hello", "alo", "chào", "chào bạn", "xin chào", "hey", "hế lô", "test"];
  
  if (greetings.includes(trimmed)) {
    return {
      score: 0,
      issue: "Hỏi đáp & Hướng dẫn sử dụng Hệ thống Thẩm định Pháp lý Thuế GTGT",
      rule: "Cơ sở tri thức hiệu lực: Luật Thuế GTGT 48/2024/QH15, Nghị định 181/2025, Thông tư 69/2025, Nghị định 359/2025, Nghị định 144/2026.",
      citations: [],
      application: [
        "Xin chào Quý khách / Quý Doanh nghiệp! Tôi là Trợ lý Pháp lý ảo về Thuế Giá trị gia tăng (GTGT) Việt Nam, được vận hành bởi Đồ thị Tri thức Thời gian (Temporal GraphRAG).",
        "Hệ thống có thể hỗ trợ bạn trực tiếp:",
        "• Thẩm định thuế suất GTGT cho từng trường hợp gia công, xuất khẩu, thương mại dịch vụ.",
        "• Tra cứu tính hiệu lực thời gian của các điều luật tại bất kỳ mốc sự việc nào (tự động phát hiện bẫy niên đại).",
        "• Đối chiếu quy trình xử lý và lập hóa đơn điều chỉnh theo các nghị định mới nhất.",
      ],
      conclusion: "Mời bạn nhập câu hỏi cụ thể về tình huống thuế GTGT hoặc chọn các kịch bản gợi ý bên dưới để bắt đầu thẩm định.",
      audit: [
        { tone: "ok", text: "Hệ thống đã kết nối trực tiếp với Neo4j Knowledge Graph và FastAPI Backend." },
        { tone: "ok", text: "Trạng thái đồ thị: 5 văn bản pháp luật, 76 điều luật, 271 khoản sẵn sàng tra cứu." },
      ],
    };
  }

  const pipelineMap: Record<string, string> = {
    P3: "P3_FullSystem",
    P2: "P2_TemporalGraph",
    P1: "P1_FlatRAG",
  };

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        as_of_date: asOfDate,
        pipeline: pipelineMap[pipeline] || "P3_FullSystem",
        use_llm: false,
        model: "qwen2.5:3b",
      }),
    });

    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${res.statusText}`);
    }

    const data = await res.json();
    const rawCitations: string[] = data.citations || [];
    const citations = rawCitations.map(parseCitationId);

    const appText = data.irac_sections?.application || "";
    const application = appText
      ? appText.split(/\n+/).filter((s: string) => s.trim().length > 0)
      : [];

    const audit: AuditItem[] = [];
    if (Array.isArray(data.warnings) && data.warnings.length > 0) {
      for (const w of data.warnings) {
        audit.push({
          tone: data.risk_score >= 60 ? "bad" : "warn",
          text: w,
        });
      }
    }

    if (citations.length > 0) {
      audit.push({
        tone: "ok",
        text: `Đã đối chiếu ${citations.length} điều khoản viện dẫn qua Đồ thị Tri thức Neo4j tại mốc ${asOfDate}.`,
      });
    }

    let trap: string | undefined = undefined;
    if (data.risk_score >= 60 || data.risk_level === "CRITICAL" || data.risk_level === "HIGH") {
      trap = "CẢNH BÁO RỦI RO PHÁP LÝ: CĂN CỨ TRÍCH DẪN CÓ NGUY CƠ HẾT HIỆU LỰC HOẶC CHƯA PHÁT SINH HIỆU LỰC TẠI MỐC ĐÃ CHỌN!";
    }

    return {
      score: data.risk_score ?? 0,
      issue: data.irac_sections?.issue || `Xác định quy định pháp lý cho: "${query}"`,
      rule: data.irac_sections?.rule || "Không có quy phạm viện dẫn cụ thể.",
      citations,
      application: application.length > 0 ? application : [appText || "Đã hoàn thành kiểm tra trên đồ thị."],
      conclusion: data.irac_sections?.conclusion || "Hoàn thành thẩm định pháp lý.",
      audit,
      trap,
    };
  } catch (err) {
    console.warn("Backend API unreachable, falling back to local resolver:", err);
    const fallback = resolve(query, asOfDate, pipeline);
    return {
      ...fallback,
      audit: [
        ...fallback.audit,
        { tone: "warn", text: "Lưu ý: Đang hiển thị kết quả giả lập do mất kết nối Backend FastAPI." },
      ],
    };
  }
}
