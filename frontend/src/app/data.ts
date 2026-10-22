export type Point = { l: string; text: string };
export type Clause = { n: number; text: string; points?: Point[] };
export type Article = {
  id: string;
  no: number;
  title: string;
  clauses: Clause[];
  table?: { head: string[]; rows: string[][] };
  note?: string;
};
export type Chapter = { title: string; articles: Article[] };
export type LawDoc = {
  id: string;
  tab: string;
  full: string;
  badge: { text: string; tone: "green" | "amber" | "none" };
  effective: string;
  chapters: Chapter[];
};

export const DOCS: LawDoc[] = [
  {
    id: "l48",
    tab: "Luật 48/2024/QH15",
    full: "Luật Thuế giá trị gia tăng số 48/2024/QH15 — Quốc hội thông qua 26/11/2024",
    badge: { text: "Đang áp dụng", tone: "green" },
    effective: "01/07/2025",
    chapters: [
      {
        title: "Chương I — Những quy định chung",
        articles: [
          {
            id: "l48-d5",
            no: 5,
            title: "Đối tượng không chịu thuế giá trị gia tăng",
            clauses: [
              { n: 1, text: "Sản phẩm trồng trọt, chăn nuôi, thủy sản nuôi trồng, đánh bắt chưa chế biến thành sản phẩm khác hoặc chỉ qua sơ chế thông thường của tổ chức, cá nhân tự sản xuất, đánh bắt bán ra và ở khâu nhập khẩu." },
              { n: 2, text: "Dịch vụ tài chính, ngân hàng, kinh doanh chứng khoán, bảo hiểm nhân thọ; dịch vụ y tế, dịch vụ thú y; dịch vụ giáo dục, đào tạo theo quy định của pháp luật." },
            ],
          },
        ],
      },
      {
        title: "Chương II — Căn cứ và phương pháp tính thuế",
        articles: [
          {
            id: "l48-d9",
            no: 9,
            title: "Thuế suất",
            clauses: [
              {
                n: 1,
                text: "Thuế suất 0% áp dụng đối với hàng hóa, dịch vụ xuất khẩu, bao gồm:",
                points: [
                  { l: "a", text: "Hàng hóa xuất khẩu; gia công hàng hóa xuất khẩu; hàng hóa, dịch vụ bán cho khu phi thuế quan;" },
                  { l: "b", text: "Dịch vụ cung ứng trực tiếp cho tổ chức, cá nhân ở nước ngoài và tiêu dùng ngoài lãnh thổ Việt Nam, trong đó có dịch vụ phần mềm, theo điều kiện do Chính phủ quy định;" },
                  { l: "c", text: "Vận tải quốc tế; hàng hóa, dịch vụ thuộc diện không phải kê khai, tính nộp thuế theo quy định." },
                ],
              },
              { n: 2, text: "Thuế suất 5% áp dụng đối với nước sạch phục vụ sản xuất và sinh hoạt; thiết bị, dụng cụ y tế; sách các loại; sản phẩm nông nghiệp chưa qua chế biến." },
              { n: 3, text: "Thuế suất 10% áp dụng đối với hàng hóa, dịch vụ không thuộc quy định tại khoản 1 và khoản 2 Điều này." },
            ],
            table: {
              head: ["Mức thuế suất", "Nhóm hàng hóa, dịch vụ", "Căn cứ"],
              rows: [
                ["0%", "Hàng hóa, dịch vụ xuất khẩu; vận tải quốc tế", "Điều 9 khoản 1"],
                ["5%", "Nước sạch, thiết bị y tế, sách, nông sản chưa chế biến", "Điều 9 khoản 2"],
                ["10%", "Hàng hóa, dịch vụ còn lại", "Điều 9 khoản 3"],
              ],
            },
          },
        ],
      },
      {
        title: "Chương V — Điều khoản thi hành",
        articles: [
          {
            id: "l48-d19",
            no: 19,
            title: "Hiệu lực thi hành",
            clauses: [
              { n: 1, text: "Luật này có hiệu lực thi hành từ ngày 01 tháng 7 năm 2025." },
              { n: 2, text: "Luật Thuế giá trị gia tăng số 13/2008/QH12 hết hiệu lực kể từ ngày Luật này có hiệu lực, trừ trường hợp luật định khác." },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "nd181",
    tab: "Nghị định 181/2025",
    full: "Nghị định 181/2025/NĐ-CP quy định chi tiết một số điều của Luật Thuế GTGT",
    badge: { text: "Đã sửa đổi", tone: "amber" },
    effective: "01/07/2025",
    chapters: [
      {
        title: "Chương II — Thuế suất 0%",
        articles: [
          {
            id: "nd181-d5",
            no: 5,
            title: "Điều kiện áp dụng thuế suất 0% đối với dịch vụ xuất khẩu",
            clauses: [
              {
                n: 1,
                text: "Dịch vụ, trong đó có dịch vụ phần mềm, được áp dụng thuế suất 0% khi đáp ứng đồng thời các điều kiện:",
                points: [
                  { l: "a", text: "Có hợp đồng bằng văn bản với tổ chức, cá nhân ở nước ngoài;" },
                  { l: "b", text: "Có chứng từ thanh toán qua ngân hàng;" },
                  { l: "c", text: "Người mua nằm ngoài lãnh thổ Việt Nam và tiêu dùng dịch vụ ngoài lãnh thổ." },
                ],
              },
            ],
          },
        ],
      },
      {
        title: "Chương IV — Hóa đơn, chứng từ",
        articles: [
          {
            id: "nd181-d12",
            no: 12,
            title: "Lập hóa đơn điều chỉnh, thay thế",
            clauses: [
              { n: 1, text: "Trường hợp hóa đơn đã lập có sai sót về thuế suất, tiền thuế, người bán lập hóa đơn điều chỉnh theo quy định." },
              { n: 2, text: "Thời hạn kê khai điều chỉnh thực hiện theo kỳ khai thuế phát sinh sai sót." },
            ],
            note: "Điều này đã bị thay thế bởi Điều 1 Nghị định 359/2025 kể từ 01/01/2026.",
          },
        ],
      },
    ],
  },
  {
    id: "tt69",
    tab: "Thông tư 69/2025",
    full: "Thông tư 69/2025/TT-BTC hướng dẫn thi hành Luật Thuế GTGT",
    badge: { text: "", tone: "none" },
    effective: "01/07/2025",
    chapters: [
      {
        title: "Chương I — Hướng dẫn chung",
        articles: [
          {
            id: "tt69-d3",
            no: 3,
            title: "Hồ sơ khai thuế và chứng từ chứng minh",
            clauses: [
              { n: 1, text: "Người nộp thuế lưu giữ hợp đồng, hóa đơn, chứng từ thanh toán qua ngân hàng làm căn cứ chứng minh đối tượng áp dụng thuế suất 0%." },
              { n: 2, text: "Hồ sơ hoàn thuế, khấu trừ thuế thực hiện theo mẫu ban hành kèm Thông tư này." },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "nd359",
    tab: "Nghị định 359/2025",
    full: "Nghị định 359/2025/NĐ-CP sửa đổi, bổ sung một số điều của Nghị định 181/2025/NĐ-CP",
    badge: { text: "Sửa NĐ 181", tone: "green" },
    effective: "01/01/2026",
    chapters: [
      {
        title: "Điều 1 — Sửa đổi, bổ sung Nghị định 181/2025",
        articles: [
          {
            id: "nd359-d1",
            no: 1,
            title: "Sửa đổi Điều 12 Nghị định 181/2025/NĐ-CP",
            clauses: [
              { n: 1, text: "Thay thế Điều 12 Nghị định 181/2025/NĐ-CP bằng nội dung sau: “Hóa đơn điều chỉnh được lập trên hệ thống hóa đơn điện tử có mã xác thực của cơ quan thuế.”" },
              { n: 2, text: "Nghị định này có hiệu lực kể từ ngày 01 tháng 01 năm 2026." },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "nd144",
    tab: "Nghị định 144/2026",
    full: "Nghị định 144/2026/NĐ-CP sửa đổi, bổ sung Nghị định 181/2025/NĐ-CP",
    badge: { text: "Sửa NĐ 181", tone: "green" },
    effective: "2026",
    chapters: [
      {
        title: "Điều 1 — Sửa đổi quy định về hóa đơn",
        articles: [
          {
            id: "nd144-d1",
            no: 1,
            title: "Sửa đổi quy trình điều chỉnh hóa đơn",
            clauses: [
              {
                n: 1,
                text: "Việc điều chỉnh hóa đơn đã lập sai sót được thực hiện như sau:",
                points: [
                  { l: "a", text: "Sai sót về thuế suất, tiền thuế: lập hóa đơn điều chỉnh, ghi rõ số, ký hiệu, ngày của hóa đơn bị điều chỉnh;" },
                  { l: "b", text: "Sai sót về thông tin người mua: thông báo sai sót cho cơ quan thuế, không phải lập hóa đơn mới;" },
                  { l: "c", text: "Hóa đơn điều chỉnh phải gửi cho người mua trong vòng 24 giờ kể từ khi lập." },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
];

export type Citation = { label: string; doc: string; art: string };
export type AuditItem = { tone: "ok" | "warn" | "bad"; text: string };
export type Result = {
  score: number;
  issue: string;
  rule: string;
  citations: Citation[];
  application: string[];
  conclusion: string;
  audit: AuditItem[];
  trap?: string;
};

export const SCENARIOS = [
  {
    id: 1,
    tone: "emerald",
    label: "Kịch bản 1: Xuất khẩu phần mềm năm 2026 (Thuế suất 0%)",
    query: "Công ty phần mềm tại Cần Thơ ký hợp đồng gia công phần mềm với khách hàng tại Nhật Bản, thanh toán qua ngân hàng. Dịch vụ này chịu thuế suất GTGT bao nhiêu?",
    date: "2026-03-20",
  },
  {
    id: 2,
    tone: "red",
    label: "Kịch bản 2: Bẫy niên đại trước 01/07/2025",
    query: "Giao dịch xuất khẩu phần mềm ngày 15/06/2025 có áp dụng thuế suất 0% theo Điều 9 Luật 48/2024/QH15 được không?",
    date: "2025-06-15",
  },
  {
    id: 3,
    tone: "amber",
    label: "Kịch bản 3: Sửa đổi hóa đơn theo NĐ 144/2026",
    query: "Hóa đơn xuất khẩu đã lập sai thuế suất 10%. Quy trình lập hóa đơn điều chỉnh theo Nghị định 144/2026 như thế nào?",
    date: "2026-05-10",
  },
];

const cite = {
  l48d9: { label: "Điều 9 Luật 48/2024", doc: "l48", art: "l48-d9" },
  l48d19: { label: "Điều 19 Luật 48/2024", doc: "l48", art: "l48-d19" },
  nd181d5: { label: "Điều 5 NĐ 181/2025", doc: "nd181", art: "nd181-d5" },
  nd181d12: { label: "Điều 12 NĐ 181/2025", doc: "nd181", art: "nd181-d12" },
  nd359d1: { label: "Điều 1 NĐ 359/2025", doc: "nd359", art: "nd359-d1" },
  nd144d1: { label: "Điều 1 NĐ 144/2026", doc: "nd144", art: "nd144-d1" },
  tt69d3: { label: "Điều 3 TT 69/2025", doc: "tt69", art: "tt69-d3" },
};

const R1: Result = {
  score: 8,
  issue: "Dịch vụ gia công phần mềm cung ứng cho khách hàng Nhật Bản, phát sinh ngày 20/03/2026, chịu thuế suất GTGT nào và cần điều kiện gì để áp dụng?",
  rule: "Luật 48/2024/QH15 (hiệu lực 01/07/2025) quy định thuế suất 0% đối với dịch vụ xuất khẩu, gồm dịch vụ phần mềm; NĐ 181/2025 quy định điều kiện chi tiết; TT 69/2025 hướng dẫn hồ sơ chứng minh.",
  citations: [cite.l48d9, cite.nd181d5, cite.tt69d3],
  application: [
    "Mốc 20/03/2026 nằm sau ngày 01/07/2025 nên Luật 48/2024 là văn bản có hiệu lực áp dụng; Luật 13/2008 đã hết hiệu lực.",
    "Bên mua ở Nhật Bản, tiêu dùng ngoài lãnh thổ Việt Nam, có hợp đồng văn bản và chứng từ thanh toán qua ngân hàng — đáp ứng đủ 3 điều kiện tại Điều 5 NĐ 181.",
    "Quy định thuế suất 0% tại Điều 9 khoản 1 điểm b được áp dụng trực tiếp; không có điều khoản nào của NĐ 359/2025 hay NĐ 144/2026 thay đổi nội dung này.",
  ],
  conclusion: "Áp dụng thuế suất 0%. Doanh nghiệp kê khai trên tờ khai GTGT kỳ phát sinh, lưu giữ hợp đồng, chứng từ thanh toán ngân hàng và hóa đơn để chứng minh khi thanh tra, hoàn thuế.",
  audit: [
    { tone: "ok", text: "Xác nhận: Luật 48/2024/QH15 có hiệu lực từ 01/07/2025, bao trùm mốc 20/03/2026." },
    { tone: "ok", text: "Xác nhận: Điều 5 NĐ 181/2025 không bị NĐ 359/2025 hoặc NĐ 144/2026 sửa đổi." },
    { tone: "ok", text: "Quan hệ pháp lý: NĐ 181 → hướng dẫn Điều 9 Luật 48 (HƯỚNG_DẪN)." },
  ],
};

const R2: Result = {
  score: 92,
  trap: "CẢNH BÁO: ĐIỀU LUẬT CHƯA CÓ HIỆU LỰC TẠI MỐC THỜI GIAN ĐÃ CHỌN!",
  issue: "Giao dịch ngày 15/06/2025 có thể viện dẫn Điều 9 Luật 48/2024/QH15 để áp dụng thuế suất 0% cho xuất khẩu phần mềm hay không?",
  rule: "Điều 19 Luật 48/2024 quy định hiệu lực từ 01/07/2025. Trước mốc này, Luật 13/2008/QH12 vẫn là văn bản điều chỉnh; không được viện dẫn Điều 9 Luật 48.",
  citations: [cite.l48d19, cite.l48d9],
  application: [
    "Mốc sự việc 15/06/2025 sớm hơn ngày hiệu lực 01/07/2025 là 16 ngày — Điều 9 Luật 48 chưa phát sinh hiệu lực pháp lý.",
    "NĐ 181/2025 và TT 69/2025 cùng có hiệu lực từ 01/07/2025 nên cũng không thể làm căn cứ cho giao dịch này.",
    "Cần tra cứu thuế suất theo Luật 13/2008/QH12 và văn bản hướng dẫn cũ, vốn không nằm trong kho 5 văn bản đang đóng băng.",
  ],
  conclusion: "Không được viện dẫn Điều 9 Luật 48/2024 cho giao dịch ngày 15/06/2025. Cần chuyển sang căn cứ Luật 13/2008/QH12 và rà soát lại hồ sơ kê khai.",
  audit: [
    { tone: "bad", text: "Phát hiện bẫy niên đại: Điều 9 Luật 48/2024 chỉ có hiệu lực từ 01/07/2025, sau mốc 15/06/2025." },
    { tone: "warn", text: "Kho dữ liệu hiện tại không chứa Luật 13/2008/QH12 — kết luận về thuế suất cần xác minh thủ công." },
    { tone: "ok", text: "Xác nhận: Điều 19 Luật 48/2024 quy định Luật 13/2008 hết hiệu lực từ 01/07/2025." },
  ],
};

const R3: Result = {
  score: 46,
  issue: "Hóa đơn xuất khẩu lập sai thuế suất 10% (đúng là 0%) cần được điều chỉnh theo quy trình nào tại mốc 10/05/2026?",
  rule: "Điều 12 NĐ 181/2025 đã bị thay thế bởi NĐ 359/2025 từ 01/01/2026, và quy trình điều chỉnh tiếp tục được sửa bởi Điều 1 NĐ 144/2026.",
  citations: [cite.nd181d12, cite.nd359d1, cite.nd144d1],
  application: [
    "Điều 12 NĐ 181 là căn cứ gốc nhưng không còn hiệu lực tại mốc 10/05/2026, tránh viện dẫn trực tiếp.",
    "Theo NĐ 144/2026 điều 1 khoản 1 điểm a, sai sót thuế suất phải lập hóa đơn điều chỉnh, ghi rõ số, ký hiệu, ngày hóa đơn bị điều chỉnh.",
    "Hóa đơn điều chỉnh phải gửi người mua trong 24 giờ; hóa đơn lập trên hệ thống có mã xác thực của cơ quan thuế (NĐ 359).",
  ],
  conclusion: "Lập hóa đơn điều chỉnh thuế suất từ 10% về 0%, gửi người mua trong 24 giờ và kê khai điều chỉnh tại kỳ phát sinh sai sót. Mức độ rủi ro trung bình do chồng lấn hai văn bản sửa đổi.",
  audit: [
    { tone: "warn", text: "Xác nhận: Điều 12 NĐ 181 đã bị thay thế bởi NĐ 359 từ ngày 01/01/2026." },
    { tone: "warn", text: "Chồng lấn: NĐ 144/2026 tiếp tục sửa quy trình điều chỉnh — ưu tiên văn bản ban hành sau." },
    { tone: "ok", text: "Quan hệ pháp lý: NĐ 359 → SỬA_ĐỔI → NĐ 181; NĐ 144 → SỬA_ĐỔI → NĐ 181." },
  ],
};

export function resolve(query: string, date: string, pipeline: "P3" | "P2" | "P1"): Result {
  const q = query.toLowerCase();
  let base: Result;
  if (date && date < "2025-07-01") base = R2;
  else if (q.includes("hóa đơn") || q.includes("144")) base = R3;
  else base = R1;

  if (pipeline === "P3") return base;
  const audit = [...base.audit];
  if (pipeline === "P2") {
    audit.push({ tone: "warn", text: "P2 Temporal Graph: chưa chạy lớp Citation Verifier, trích dẫn chưa được đối chiếu chéo." });
    return { ...base, audit };
  }
  if (base === R2) {
    return {
      ...base,
      score: 18,
      trap: undefined,
      conclusion: "Áp dụng thuế suất 0% theo Điều 9 Luật 48/2024 (KẾT QUẢ SAI — P1 bỏ sót bẫy niên đại).",
      audit: [
        { tone: "bad", text: "P1 Flat RAG không có lớp kiểm tra hiệu lực: đã viện dẫn điều luật chưa có hiệu lực mà không cảnh báo." },
        { tone: "warn", text: "Khuyến nghị chạy lại bằng P3: Full System để kích hoạt Temporal Graph và Verifier." },
      ],
    };
  }
  audit.push({ tone: "bad", text: "P1 Flat RAG: không kiểm tra quan hệ sửa đổi — có thể trích dẫn điều khoản đã bị thay thế." });
  return { ...base, score: Math.min(base.score + 12, 100), audit };
}
