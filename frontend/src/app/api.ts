import { resolve, type Result, type Citation, type AuditItem } from "./data";

export const PIPELINE_LABELS = {
  P3: "Thẩm định Toàn diện (Đầy đủ Căn cứ)",
  P2: "Tra cứu theo thời điểm",
  P1: "Tra cứu cơ bản",
} as const;

const DOCUMENT_IDS: Record<string, string> = {
  l48: "LUAT_48_2024",
  nd181: "ND_181_2025",
  tt69: "TT_69_2025",
  nd359: "ND_359_2025",
  nd144: "ND_144_2026",
};

export const LEGAL_REFERENCE_PATTERN = String.raw`(?:LUAT|ND|TT)_\d+_\d{4}(?:_D\d+(?:_K\d+(?:_[a-zđ]+)?)?)?`;

export function canonicalDocumentId(docId: string): string | null {
  return DOCUMENT_IDS[docId] || (/^(?:LUAT|ND|TT)_\d+_\d{4}$/i.test(docId) ? docId.toUpperCase() : null);
}

export function legalReferenceLabel(id: string): string {
  const match = id.match(/^(LUAT|ND|TT)_(\d+)_(\d{4})(?:_D(\d+)(?:_K(\d+)(?:_([a-zđ]+))?)?)?$/i);
  if (!match) return id;
  const [, family, number, year, article, clause, point] = match;
  const doc = `${{ LUAT: "Luật", ND: "NĐ", TT: "TT" }[family.toUpperCase()]} ${number}/${year}`;
  return `${point ? `Điểm ${point.toLowerCase()} ` : ""}${clause ? `${point ? "khoản" : "Khoản"} ${clause} ` : ""}${article ? `${clause ? "điều" : "Điều"} ${article} ` : ""}${doc}`;
}

export function parseCitationId(cid: string): Citation {
  const id = cid.replace(/^\[|\]$/g, "").toUpperCase();
  const match = id.match(/^((?:LUAT|ND|TT)_\d+_\d{4})_D(\d+)(?:_K\d+(?:_[A-ZĐ]+)?)?$/);
  if (!match) return { label: "Trích dẫn chưa xác định", doc: "", art: "" };
  const doc = Object.keys(DOCUMENT_IDS).find((key) => DOCUMENT_IDS[key] === match[1]) || match[1];
  return { label: legalReferenceLabel(id), doc, art: DOCUMENT_IDS[doc] ? `${doc}-d${match[2]}` : `${match[1]}_D${match[2]}` };
}

export function citationArticleId(citation: Citation): string | null {
  const doc = canonicalDocumentId(citation.doc);
  const article = citation.art.match(/(?:-d|_D)(\d+)(?:_K\d+(?:_[a-zđ]+)?)?$/i)?.[1];
  return doc && article ? `${doc}_D${article}` : null;
}

// Presentation-only replacements also apply to locally stored, older responses.
export function friendlyLegalText(text: string): string {
  return text
    .replace(/Hệ thống đã kết nối trực tiếp với Neo4j Knowledge Graph và FastAPI Backend\./gi, "Hệ thống đã sẵn sàng hỗ trợ tra cứu văn bản pháp luật.")
    .replace(/Đã đối chiếu (\d+) điều khoản viện dẫn qua Đồ thị Tri thức Neo4j tại mốc/gi, "Đã đối chiếu $1 điều khoản viện dẫn tại mốc")
    .replace(/Màng lọc Domain Guardrail đã kích hoạt để bảo vệ tính chính xác của cơ sở tri thức\./gi, "Hệ thống chỉ hỗ trợ câu hỏi về thuế giá trị gia tăng.")
    .replace(/, được vận hành bởi Đồ thị Tri thức Thời gian \(Temporal GraphRAG\)/gi, "")
    .replace(/P2 Temporal Graph: chưa chạy lớp Citation Verifier, trích dẫn chưa được đối chiếu chéo\./gi, "Chế độ tra cứu theo thời điểm chưa đối chiếu chéo các trích dẫn.")
    .replace(/P1 Flat RAG không có lớp kiểm tra hiệu lực/gi, "Chế độ tra cứu cơ bản không kiểm tra hiệu lực")
    .replace(/P1 Flat RAG: không kiểm tra quan hệ sửa đổi/gi, "Chế độ tra cứu cơ bản không kiểm tra văn bản sửa đổi")
    .replace(/P3: Full System để kích hoạt Temporal Graph và Verifier/gi, "chế độ thẩm định toàn diện để đối chiếu hiệu lực và trích dẫn")
    .replace(/Backend FastAPI/gi, "dịch vụ tra cứu")
    .replace(/Trạng thái đồ thị:/gi, "Dữ liệu tra cứu:")
    .replace(/Đã hoàn thành kiểm tra trên đồ thị\./gi, "Đã hoàn thành đối chiếu các quy định.")
    .replace(/\(HƯỚNG_DẪN\)/g, "")
    .replace(/SỬA_ĐỔI/g, "sửa đổi")
    .replace(/HƯỚNG_DẪN/g, "hướng dẫn")
    .replace(/Đồ thị Tri thức Thời gian|đồ thị tri thức|Neo4j Knowledge Graph|Temporal GraphRAG/gi, "kho văn bản pháp luật")
    .replace(/\bNeo4j\b|\bFastAPI\b/gi, "dịch vụ tra cứu")
    .replace(/Citation Verifier|\bVerifier\b/gi, "đối chiếu trích dẫn")
    .replace(/Domain Guardrail/gi, "kiểm tra phạm vi câu hỏi")
    .replace(/Rule Engine/gi, "đối chiếu điều kiện")
    .replace(/Temporal Graph/gi, "tra cứu theo thời điểm")
    .replace(/Flat RAG|Vector Search/gi, "tra cứu cơ bản")
    .replace(/bẫy niên đại/gi, "quy định chưa phù hợp với thời điểm áp dụng")
    .replace(/\bP3(?:_FullSystem)?\b/g, PIPELINE_LABELS.P3)
    .replace(/\bP2(?:_TemporalGraph)?\b/g, PIPELINE_LABELS.P2)
    .replace(/\bP1(?:_FlatRAG)?\b/g, PIPELINE_LABELS.P1)
    .trim();
}

export function legalPlainText(text: string): string {
  return friendlyLegalText(text).replace(
    new RegExp(`\\[(${LEGAL_REFERENCE_PATTERN})\\]|\\b(${LEGAL_REFERENCE_PATTERN})\\b`, "gi"),
    (_, bracketed: string, bare: string) => legalReferenceLabel(bracketed || bare),
  );
}

export type LegalPoint = { id: string; code: string; content: string };
export type LegalClause = LegalPoint & { points?: LegalPoint[] };
export type LegalArticle = LegalPoint & {
  title: string;
  lead?: string;
  tables?: string[];
  clauses?: LegalClause[];
};
export type LegalChapter = { id: string; code?: string; title: string; articles: LegalArticle[] };
export type LegalDocumentDetail = {
  id: string;
  code: string;
  title: string;
  valid_from: string;
  valid_to: string;
  chapters?: LegalChapter[];
  articles?: LegalArticle[];
};

const documentCache = new Map<string, LegalDocumentDetail>();
const pendingDocuments = new Map<string, Promise<LegalDocumentDetail>>();

export async function getLegalDocument(docId: string, refresh = false): Promise<LegalDocumentDetail> {
  const id = canonicalDocumentId(docId);
  if (!id) throw new Error("Không xác định được văn bản cần đọc.");
  const cached = documentCache.get(id);
  if (cached && !refresh) return cached;
  const pending = pendingDocuments.get(id);
  if (pending) return pending;

  const request = (async () => {
    const response = await fetch(`/api/documents/${encodeURIComponent(id)}`);
    if (!response.ok) throw new Error("Chưa tải được toàn văn. Vui lòng thử lại.");
    const document: LegalDocumentDetail = await response.json();
    if (document.id !== id || (!Array.isArray(document.articles) && !Array.isArray(document.chapters))) {
      throw new Error("Nội dung văn bản chưa sẵn sàng.");
    }
    documentCache.set(id, document);
    return document;
  })();
  pendingDocuments.set(id, request);
  try {
    return await request;
  } finally {
    pendingDocuments.delete(id);
  }
}

export async function queryLegalApi(
  query: string,
  asOfDate: string,
  pipeline: "P3" | "P2" | "P1",
  useLlm: boolean = false
): Promise<Result> {
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
        use_llm: useLlm,
        model: "qwen2.5:7b",
      }),
    });

    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${res.statusText}`);
    }

    const data = await res.json();

    // 1. Out of domain query handling
    if (data.is_out_of_domain) {
      return {
        score: 0,
        issue: data.irac_sections?.issue || `Kiểm tra phạm vi áp dụng: "${query}"`,
        rule: data.irac_sections?.rule || "Không có quy phạm pháp luật thuế GTGT điều chỉnh nội dung này.",
        citations: [],
        application: [
          data.irac_sections?.application ||
            "Câu hỏi của bạn không thuộc phạm vi điều chỉnh của Hệ thống Pháp lý Thuế Giá trị gia tăng (GTGT).",
        ],
        conclusion:
          data.irac_sections?.conclusion ||
          "Câu hỏi của bạn không thuộc phạm vi điều chỉnh của Hệ thống Pháp lý Thuế Giá trị gia tăng (GTGT). Vui lòng đặt câu hỏi liên quan đến chính sách thuế, thuế suất hoặc quy định hóa đơn chứng từ.",
        audit: [
          {
            tone: "warn",
            text: "Phát hiện câu hỏi nằm ngoài phạm vi nghiệp vụ Pháp lý Thuế GTGT.",
          },
          {
            tone: "ok",
            text: "Hệ thống chỉ hỗ trợ câu hỏi về thuế giá trị gia tăng.",
          },
        ],
        is_out_of_domain: true,
      };
    }

    // 2. Conversational greeting handling
    if (data.is_greeting) {
      return {
        score: 0,
        issue: "Hỏi đáp & Hướng dẫn sử dụng Hệ thống Thẩm định Pháp lý Thuế GTGT",
        rule: "Cơ sở tri thức hiệu lực: Luật Thuế GTGT 48/2024/QH15, Nghị định 181/2025, Thông tư 69/2025, Nghị định 359/2025, Nghị định 144/2026.",
        citations: [],
        application: [
          "Xin chào! Tôi là trợ lý tra cứu Thuế Giá trị gia tăng (GTGT) Việt Nam dành cho người dân và doanh nghiệp.",
          "Hệ thống có thể hỗ trợ bạn trực tiếp:",
          "• Thẩm định thuế suất GTGT cho từng trường hợp gia công, xuất khẩu, thương mại dịch vụ.",
          "• Tra cứu tính hiệu lực thời gian của các điều luật tại bất kỳ mốc sự việc nào (tự động phát hiện bẫy niên đại).",
          "• Đối chiếu quy trình xử lý và lập hóa đơn điều chỉnh theo các nghị định mới nhất.",
        ],
        conclusion: "Mời bạn nhập câu hỏi cụ thể về tình huống thuế GTGT hoặc chọn các kịch bản gợi ý bên dưới để bắt đầu thẩm định.",
        audit: [
          { tone: "ok", text: "Hệ thống đã sẵn sàng hỗ trợ tra cứu văn bản pháp luật." },
          { tone: "ok", text: "Bạn có thể chọn ngày diễn ra sự việc để tra cứu quy định tại thời điểm đó." },
        ],
        is_greeting: true,
      };
    }

    // 3. Normal in-domain tax query
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
        text: `Đã đối chiếu ${citations.length} điều khoản viện dẫn tại mốc ${asOfDate}.`,
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
      application: application.length > 0 ? application : [appText || "Đã hoàn thành đối chiếu các quy định."],
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
        { tone: "warn", text: "Lưu ý: Đang hiển thị kết quả giả lập do mất kết nối dịch vụ tra cứu." },
      ],
    };
  }
}
