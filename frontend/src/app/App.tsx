import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AlertTriangle, ArrowUp, BookOpen, CalendarDays, CheckCircle2, ChevronDown, ChevronRight,
  Clock, Copy, ExternalLink, FileCode, FileSearch, FileText, Filter, Folder,
  History, Info, Layers, LayoutGrid, Lightbulb, Loader2, Lock,
  LogOut, MapPin, MessageSquare, Mic, MoreHorizontal, PanelLeft, PanelLeftClose,
  Paperclip, Plus, RotateCcw, Search, Send, Settings, Share2, Sliders,
  Sparkles, SquarePen, ThumbsDown, ThumbsUp, Trash2, User, UserCheck, X,
} from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/app/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/app/components/ui/popover";
import emblem from "@/imports/tai-xuong.png";
import drum from "@/imports/img_6-hinh-nen-powerpoint-trong-dong.jpg";
import { DOCS, SCENARIOS, type Result, type LawDoc, type Citation } from "./data";
import {
  PIPELINE_LABELS, LEGAL_REFERENCE_PATTERN, canonicalDocumentId, citationArticleId,
  friendlyLegalText, getLegalDocument, legalPlainText, legalReferenceLabel, parseCitationId,
  queryLegalApi, type LegalDocumentDetail, type LegalChapter,
} from "./api";

type Pipeline = "P3" | "P2" | "P1";
type Msg = { id: number; q: string; date: string; pipeline: Pipeline; result: Result | null };
type Conversation = { id: string; title: string; updated: number; messages: Msg[] };

type UserState = {
  isLoggedIn: boolean;
  name: string;
  role: string;
  taxCode?: string;
};

type SystemSettings = {
  pipeline: Pipeline;
  language: "vi" | "en";
  defaultDate: string;
  theme: "light" | "dark" | "system";
  useLlm: boolean;
};

const DEFAULT_USER: UserState = {
  isLoggedIn: false,
  name: "Khách truy cập",
  role: "Chưa đăng nhập",
  taxCode: "",
};

const LOGGED_IN_USER_PRESET: UserState = {
  isLoggedIn: true,
  name: "Huỳnh Tấn Phúc",
  role: "Người nộp thuế / Doanh nghiệp",
  taxCode: "1801234567",
};

const DEFAULT_SETTINGS: SystemSettings = {
  pipeline: "P3",
  language: "vi",
  defaultDate: "2026-03-20",
  theme: "light",
  useLlm: false,
};

const PIPELINES = [
  { key: "P3", label: PIPELINE_LABELS.P3, desc: "Đối chiếu quy định, thời điểm áp dụng và các trích dẫn" },
  { key: "P2", label: PIPELINE_LABELS.P2, desc: "Tra cứu quy định theo ngày diễn ra sự việc; chưa đối chiếu chéo trích dẫn" },
  { key: "P1", label: PIPELINE_LABELS.P1, desc: "Tìm nội dung liên quan; cần kiểm tra thêm hiệu lực và văn bản sửa đổi" },
] as const;

const STEPS = [
  "Đang đọc tình huống và ngày diễn ra sự việc...",
  "Đang tra cứu các quy định liên quan...",
  "Đang đối chiếu điều kiện và mức thuế áp dụng...",
  "Đang tổng hợp kết quả và những điểm cần lưu ý...",
];

function fmtDate(iso: string): string {
  try {
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  } catch {
    return iso;
  }
}

const store = {
  get<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  },
  set<T>(key: string, value: T) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* ignore */
    }
  },
};

export function App() {
  // Settings & User state
  const [settings, setSettings] = useState<SystemSettings>(() => store.get("vat_public_settings", DEFAULT_SETTINGS));
  const [user, setUser] = useState<UserState>(() => store.get("vat_user_state", DEFAULT_USER));

  // Current query parameters
  const [date, setDate] = useState<string>(settings.defaultDate);
  const [pipeline, setPipeline] = useState<Pipeline>(settings.pipeline);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);

  // Layout & Drawers state
  const [sidebarOpen, setSidebarOpen] = useState(() => window.matchMedia("(min-width: 768px)").matches);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [libraryCategory, setLibraryCategory] = useState<"all" | "luat" | "nghidinh" | "thongtu">("all");
  const [activeLibraryDoc, setActiveLibraryDoc] = useState("l48");
  const [librarySearch, setLibrarySearch] = useState("");
  const [activeLibraryArticle, setActiveLibraryArticle] = useState<string | null>(null);
  const [documentRetry, setDocumentRetry] = useState(0);
  const [articleFocusVersion, setArticleFocusVersion] = useState(0);
  const [documentState, setDocumentState] = useState<{
    doc: string;
    status: "loading" | "ready" | "error";
    data?: LegalDocumentDetail;
  } | null>(null);

  const [relatedOpen, setRelatedOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [pipelineMenuOpen, setPipelineMenuOpen] = useState(false);

  // Conversations & Messages
  const [convs, setConvs] = useState<Conversation[]>(() =>
    store.get("vat_public_convs", [
      {
        id: "c-1",
        title: "Xuất khẩu phần mềm năm 2026 (Thuế 0%)",
        updated: Date.now() - 3600000,
        messages: [],
      },
      {
        id: "c-2",
        title: "Bẫy niên đại trước 01/07/2025 (Luật 13 vs 48)",
        updated: Date.now() - 86400000,
        messages: [],
      },
      {
        id: "c-3",
        title: "Xử lý hóa đơn điện tử theo NĐ 144/2026",
        updated: Date.now() - 172800000,
        messages: [],
      },
    ])
  );
  const [activeId, setActiveId] = useState<string>("c-1");
  const [messages, setMessages] = useState<Msg[]>([]);

  const taRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  // Sync state to local storage
  useEffect(() => {
    store.set("vat_public_settings", settings);
  }, [settings]);

  useEffect(() => {
    store.set("vat_user_state", user);
  }, [user]);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 768px)");
    const collapseOnMobile = () => { if (!desktop.matches) setSidebarOpen(false); };
    desktop.addEventListener("change", collapseOnMobile);
    return () => desktop.removeEventListener("change", collapseOnMobile);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, step]);

  // Latest citations for top-bar "Văn bản liên quan"
  const latestResult = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].result) return messages[i].result;
    }
    return null;
  }, [messages]);

  const latestCitations: Citation[] = useMemo(() => {
    return latestResult?.citations || [];
  }, [latestResult]);

  function openDocument(doc: string, article: string | null = null) {
    setRelatedOpen(false);
    setActiveLibraryDoc(doc);
    setActiveLibraryArticle(article);
    setDocumentRetry(0);
    setArticleFocusVersion((value) => value + 1);
    setLibraryOpen(true);
  }

  function openCitation(citation: Citation) {
    const article = citationArticleId(citation);
    setLibraryCategory("all");
    setLibrarySearch("");
    openDocument(article ? citation.doc : "", article);
  }

  function openRelated() {
    setLibraryOpen(false);
    setRelatedOpen(true);
  }

  useEffect(() => {
    if (!libraryOpen) return;
    let cancelled = false;
    setDocumentState({ doc: activeLibraryDoc, status: "loading" });
    getLegalDocument(activeLibraryDoc, documentRetry > 0).then(
      (data) => { if (!cancelled) setDocumentState({ doc: activeLibraryDoc, status: "ready", data }); },
      () => { if (!cancelled) setDocumentState({ doc: activeLibraryDoc, status: "error" }); },
    );
    return () => { cancelled = true; };
  }, [libraryOpen, activeLibraryDoc, documentRetry]);

  useEffect(() => {
    if (!libraryOpen || !activeLibraryArticle || documentState?.doc !== activeLibraryDoc || documentState.status === "loading") return;
    const frame = requestAnimationFrame(() => {
      const article = document.getElementById(`lib-art-${activeLibraryArticle}`);
      article?.focus({ preventScroll: true });
      article?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
    return () => cancelAnimationFrame(frame);
  }, [libraryOpen, activeLibraryDoc, activeLibraryArticle, documentState, articleFocusVersion]);

  useEffect(() => {
    if (!libraryOpen && !relatedOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setLibraryOpen(false);
        setRelatedOpen(false);
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [libraryOpen, relatedOpen]);

  function newChat() {
    const id = `c_${Date.now()}`;
    const newConv: Conversation = { id, title: "Cuộc trò chuyện mới", updated: Date.now(), messages: [] };
    setConvs((prev) => [newConv, ...prev]);
    setActiveId(id);
    setMessages([]);
    setQuery("");
    setTimeout(() => taRef.current?.focus(), 50);
  }

  function selectConv(id: string) {
    setActiveId(id);
    const found = convs.find((c) => c.id === id);
    if (found) {
      setMessages(found.messages || []);
    }
  }

  function deleteConv(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    const rest = convs.filter((c) => c.id !== id);
    setConvs(rest);
    store.set("vat_public_convs", rest);
    if (activeId === id) {
      if (rest.length > 0) {
        setActiveId(rest[0].id);
        setMessages(rest[0].messages || []);
      } else {
        newChat();
      }
    }
  }

  async function send(customQ?: string, customDate?: string) {
    const q = (customQ ?? query).trim();
    const d = customDate ?? date;
    if (!q || loading) return;

    const id = Date.now();
    const userMsg: Msg = {
      id,
      q,
      date: d,
      pipeline,
      result: null,
    };
    const nextMsgs = [...messages, userMsg];
    setMessages(nextMsgs);
    setQuery("");
    setLoading(true);
    setStep(0);

    // Update conversation title if first message
    setConvs((prev) =>
      prev.map((c) => {
        if (c.id === activeId) {
          const title = c.title === "Cuộc trò chuyện mới" ? q.slice(0, 36) + (q.length > 36 ? "..." : "") : c.title;
          return { ...c, title, updated: Date.now(), messages: nextMsgs };
        }
        return c;
      })
    );

    // Multi-step reasoning & real backend API query
    const apiPromise = queryLegalApi(q, d, pipeline, settings.useLlm);
    for (let s = 0; s < STEPS.length - 1; s++) {
      setStep(s);
      await new Promise((r) => setTimeout(r, 260));
    }
    const res = await apiPromise;
    setStep(STEPS.length - 1);
    await new Promise((r) => setTimeout(r, 160));
    const finalMsgs = nextMsgs.map((m) => (m.id === id ? { ...m, result: res } : m));
    setMessages(finalMsgs);
    setLoading(false);

    setConvs((prev) =>
      prev.map((c) => (c.id === activeId ? { ...c, updated: Date.now(), messages: finalMsgs } : c))
    );
  }

  // Filter library docs by category and search
  const categorizedDocs = useMemo(() => {
    return DOCS.filter((d) => {
      const isLuat = d.id.startsWith("l");
      const isNghiDinh = d.id.startsWith("nd");
      const isThongTu = d.id.startsWith("tt");

      if (libraryCategory === "luat" && !isLuat) return false;
      if (libraryCategory === "nghidinh" && !isNghiDinh) return false;
      if (libraryCategory === "thongtu" && !isThongTu) return false;

      if (!librarySearch.trim()) return true;
      const term = librarySearch.toLowerCase();
      return (
        d.tab.toLowerCase().includes(term) ||
        d.full.toLowerCase().includes(term) ||
        d.chapters.some((c) =>
          c.articles.some((a) =>
            a.title.toLowerCase().includes(term) ||
            a.clauses.some((cl) => cl.text.toLowerCase().includes(term))
          )
        )
      );
    });
  }, [libraryCategory, librarySearch]);

  const activeDocData = useMemo(() => {
    return DOCS.find((d) => d.id === activeLibraryDoc);
  }, [activeLibraryDoc]);

  const currentDocumentState = documentState?.doc === activeLibraryDoc ? documentState : null;
  const libraryDocument = currentDocumentState?.data;
  const librarySections = useMemo(() => {
    if (libraryDocument) return documentSections(libraryDocument);
    if (currentDocumentState?.status === "error" && activeDocData) return documentSections(localExcerpt(activeDocData));
    return [];
  }, [libraryDocument, currentDocumentState?.status, activeDocData]);
  const articleUnavailable = Boolean(activeLibraryArticle && currentDocumentState?.status !== "loading" && currentDocumentState &&
    !librarySections.some((section) => section.articles.some((article) => article.id === activeLibraryArticle)));

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-[#FFFFFF] font-sans text-[#1F1F1F] antialiased">
      {/* =========================================================================
          1. LEFT SIDEBAR (PUBLIC SERVICE LEGAL ASSISTANT)
         ========================================================================= */}
      <aside
        className={`z-30 flex h-full shrink-0 flex-col border-r border-[#E5E7EB] bg-[#F8FAFC] transition-all duration-300 ease-in-out ${
          sidebarOpen ? "absolute inset-y-0 left-0 w-[280px] md:relative" : "relative w-[68px]"
        }`}
      >
        {/* Top Header: National Emblem Logo + Web Title */}
        <div className="flex h-14 items-center justify-between border-b border-[#F1F5F9] px-3">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[#475569] transition hover:bg-[#E2E8F0]"
              title={sidebarOpen ? "Thu gọn thanh bên" : "Mở rộng thanh bên"}
            >
              <PanelLeft className="h-5 w-5" />
            </button>
            {sidebarOpen && (
              <div className="flex items-center gap-2 min-w-0">
                <img
                  src={emblem}
                  alt="Biểu trưng Pháp luật Việt Nam"
                  className="h-7 w-auto object-contain drop-shadow-xs"
                />
                <div className="flex flex-col min-w-0">
                  <span className="truncate text-[13.5px] font-bold text-[#1E3A8A]">
                    Pháp Lý Thuế GTGT
                  </span>
                  <span className="text-[10px] text-[#64748B] truncate">
                    Cổng dịch vụ công phục vụ dân
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action: + Cuộc trò chuyện mới */}
        <div className="px-3 py-2.5">
          <button
            onClick={newChat}
            className={`group flex items-center rounded-full bg-[#1E3A8A] text-white font-medium shadow-xs transition hover:bg-[#1E40AF] active:scale-98 ${
              sidebarOpen ? "w-full gap-2.5 px-4 py-2.5 text-[13.5px]" : "h-10 w-10 justify-center p-0"
            }`}
            title="Tạo cuộc hội thoại mới"
          >
            <SquarePen className="h-4 w-4 shrink-0 transition group-hover:scale-110" />
            {sidebarOpen && <span>Cuộc trò chuyện mới</span>}
          </button>
        </div>

        {/* Scrollable Navigation & Lists */}
        <div className="scroll-quiet flex-1 space-y-4 overflow-y-auto px-2.5 py-1 text-[13px]">
          {/* Main Public Service Menu Items */}
          <div className="space-y-0.5">
            {/* THƯ VIỆN TOÀN BỘ VĂN BẢN (CHIA THEO MỤC) */}
            <button
              onClick={() => openDocument(activeLibraryDoc)}
              className={`flex w-full items-center rounded-xl py-2 text-[#334155] transition hover:bg-[#E2E8F0] ${
                sidebarOpen ? "gap-3 px-3" : "justify-center px-0"
              }`}
              title="Thư viện toàn bộ văn bản pháp luật GTGT"
            >
              <BookOpen className="h-4 w-4 text-[#1E3A8A] shrink-0" />
              {sidebarOpen && (
                <div className="flex flex-1 items-center justify-between">
                  <span className="font-medium text-[#1E293B]">Thư viện văn bản</span>
                  <span className="rounded-full bg-[#E0E7FF] px-2 py-0.5 text-[10px] font-bold text-[#1E3A8A]">5 VB</span>
                </div>
              )}
            </button>
          </div>

          {/* ===================================================================
              SECTION: LỊCH SỬ TRA CỨU
             =================================================================== */}
          {sidebarOpen && (
            <div className="pt-2 border-t border-[#E2E8F0]/70">
              <div className="flex items-center gap-1.5 px-2.5 pb-1 text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                <History className="h-3.5 w-3.5 text-[#1E3A8A]" />
                <span>Lịch sử tra cứu</span>
              </div>
              <div className="space-y-0.5">
                {convs.map((c) => {
                  const isActive = c.id === activeId;
                  return (
                    <div
                      key={c.id}
                      onClick={() => selectConv(c.id)}
                      className={`group relative flex cursor-pointer items-center justify-between rounded-xl px-2.5 py-1.5 text-[12.5px] transition ${
                        isActive
                          ? "bg-[#E2E8F0] font-semibold text-[#1E293B]"
                          : "text-[#475569] hover:bg-[#F1F5F9]"
                      }`}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        <MessageSquare className={`h-3.5 w-3.5 shrink-0 ${isActive ? "text-[#1E3A8A]" : "text-[#94A3B8]"}`} />
                        <span className="truncate">{c.title}</span>
                      </div>
                      <button
                        onClick={(e) => deleteConv(c.id, e)}
                        className="hidden h-5 w-5 shrink-0 items-center justify-center rounded-full text-[#94A3B8] hover:bg-black/10 hover:text-red-600 group-hover:flex"
                        title="Xóa hội thoại"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* =====================================================================
            SIDEBAR FOOTER: USER STATUS (KHÁCH / ĐÃ ĐĂNG NHẬP) & SETTINGS
           ===================================================================== */}
        <div className="border-t border-[#E2E8F0] p-2 bg-[#F1F5F9]/50">
          <div className="flex items-center justify-between gap-2">
            {/* User Profile / Guest Button */}
            <button
              onClick={() => {
                if (!user.isLoggedIn) {
                  setLoginModalOpen(true);
                } else {
                  setSettingsOpen(true);
                }
              }}
              className={`flex items-center rounded-xl p-1.5 transition hover:bg-[#E2E8F0] ${
                sidebarOpen ? "gap-2.5 min-w-0 flex-1 text-left" : "justify-center"
              }`}
              title={user.isLoggedIn ? "Tài khoản người dùng" : "Bấm để đăng nhập tài khoản"}
            >
              <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white font-bold text-[12px] ${
                user.isLoggedIn ? "bg-[#1E3A8A]" : "bg-[#64748B]"
              }`}>
                {user.isLoggedIn ? user.name.slice(0, 2).toUpperCase() : <User className="h-4 w-4" />}
              </div>

              {sidebarOpen && (
                <div className="flex-1 min-w-0">
                  <div className="truncate text-[12.5px] font-semibold text-[#1E293B]">
                    {user.name}
                  </div>
                  <div className="truncate text-[10.5px] text-[#64748B]">
                    {user.isLoggedIn ? user.role : "Bấm để đăng nhập"}
                  </div>
                </div>
              )}
            </button>

            {/* Functional Settings Icon */}
            {sidebarOpen && (
              <button
                onClick={() => setSettingsOpen(true)}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[#64748B] hover:bg-[#E2E8F0] hover:text-[#1E3A8A]"
                title="Cài đặt hệ thống (Mô hình, Ngôn ngữ, Mốc thời gian, Giao diện)"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* =========================================================================
          2. MAIN CHAT WORKSPACE (PUBLIC SERVICE PORTAL WITH TRỐNG ĐỒNG WATERMARK)
         ========================================================================= */}
      <main className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden bg-[#FFFFFF]">
        {/* =====================================================================
            HOA VĂN TRỐNG ĐỒNG ĐÔNG SƠN MỜ NẰM CHÍNH GIỮA BACKGROUND KHUNG CHAT
           ===================================================================== */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-0 h-[580px] w-[580px] rounded-full bg-contain bg-center bg-no-repeat opacity-[0.075] select-none"
          style={{
            backgroundImage: `url(${drum})`,
            maskImage: "radial-gradient(circle, rgba(0,0,0,1) 48%, rgba(0,0,0,0) 76%)",
            WebkitMaskImage: "radial-gradient(circle, rgba(0,0,0,1) 48%, rgba(0,0,0,0) 76%)",
          }}
        />

        {/* Top Header Bar */}
        <header className="relative z-20 flex h-14 shrink-0 items-center justify-between px-5 bg-white/80 border-b border-[#F1F5F9] backdrop-blur-md">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <button
                onClick={() => setSidebarOpen(true)}
                className="mr-1 flex h-8 w-8 items-center justify-center rounded-lg text-[#475569] hover:bg-[#F1F5F9]"
                title="Mở thanh bên"
              >
                <PanelLeft className="h-4 w-4" />
              </button>
            )}

            <div className="flex items-center gap-2">
              <img
                src={emblem}
                alt="Quốc huy Việt Nam"
                className="h-6 w-auto object-contain"
              />
            <span className="hidden lg:inline text-[16.5px] font-bold tracking-tight text-[#1E3A8A]">
                Hệ thống Hỏi đáp Pháp lý Thuế GTGT
              </span>
            </div>

            <span className="hidden md:inline-flex rounded-full bg-[#EFF6FF] px-2.5 py-0.5 text-[10.5px] font-semibold text-[#1E3A8A] border border-[#BFDBFE]">
              Dữ liệu cập nhật đến 30/09/2026
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Nút: Văn bản liên quan (Chỉ mở các tài liệu có liên kết đến câu hỏi AI vừa trả lời) */}
            <button
              onClick={openRelated}
              className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[12px] font-medium transition ${
                relatedOpen
                  ? "bg-[#1E3A8A] text-white shadow-xs"
                  : latestCitations.length > 0
                  ? "border border-[#BFDBFE] bg-[#EFF6FF] text-[#1E3A8A] hover:bg-[#DBEAFE]"
                  : "border border-[#E2E8F0] bg-white text-[#64748B] hover:bg-[#F8FAFC]"
              }`}
              title="Mở danh sách văn bản và điều khoản pháp luật được trích dẫn trong câu trả lời hiện tại"
            >
              <FileSearch className="h-3.5 w-3.5" />
              <span>
                Văn bản liên quan {latestCitations.length > 0 ? `(${latestCitations.length})` : ""}
              </span>
            </button>

            {/* Quick new chat */}
            <button
              onClick={newChat}
              className="flex h-8 w-8 items-center justify-center rounded-full text-[#475569] hover:bg-[#F1F5F9]"
              title="Làm mới cuộc trò chuyện"
            >
              <SquarePen className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* Scrollable Conversation Canvas */}
        <div className="scroll-quiet relative z-10 min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full w-full max-w-[820px] flex-col justify-center px-4 py-6">
            {messages.length === 0 ? (
              /* ===============================================================
                 CENTER WELCOME STATE (Khi chưa có câu hỏi nào)
                 =============================================================== */
              <div className="my-auto flex flex-col items-center justify-center text-center">
                {/* Official Public Emblem Badge */}
                <div className="mb-3.5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#EFF6FF] border border-[#BFDBFE] shadow-sm">
                  <img
                    src={emblem}
                    alt="Biểu trưng Quốc gia"
                    className="h-9 w-auto object-contain"
                  />
                </div>

                {/* Greeting according to Login State */}
                <h1 className="text-[30px] sm:text-[34px] font-medium tracking-tight text-[#0F172A]">
                  Chúng ta nên bắt đầu từ đâu nhỉ?
                </h1>
                <p className="mt-2.5 max-w-lg text-[14px] text-[#475569] leading-relaxed">
                  {user.isLoggedIn ? (
                    <>
                      Chào <strong className="text-[#1E3A8A]">{user.name}</strong>, hãy nhập tình huống và ngày diễn ra sự việc để tra cứu quy định thuế GTGT áp dụng cho bạn.
                    </>
                  ) : (
                    <>
                      Chào bạn, hãy nhập tình huống và ngày diễn ra sự việc để tra cứu quy định thuế GTGT áp dụng cho bạn.
                    </>
                  )}
                </p>

                {/* Pill Composer Container */}
                <div className="mt-7 w-full max-w-[720px]">
                  <div className="rounded-[28px] border border-[#CBD5E1] bg-[#F8FAFC]/90 hover:bg-[#F8FAFC] focus-within:bg-white focus-within:shadow-[0_4px_24px_rgba(30,58,138,0.08)] focus-within:border-[#93C5FD] transition-all p-3.5 pl-5">
                    <textarea
                      ref={taRef}
                      value={query}
                      rows={2}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          send();
                        }
                      }}
                      placeholder="Hỏi về thuế suất GTGT, dịch vụ phần mềm, hoàn thuế, xuất hóa đơn..."
                      className="block w-full resize-none bg-transparent pt-1 text-[15px] leading-relaxed outline-none placeholder:text-[#94A3B8]"
                    />

                    {/* Action Row inside Composer */}
                    <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-[#E2E8F0] pt-2.5">
                      <div className="flex min-w-0 flex-wrap items-center gap-2">
                        {/* Evaluation Date Pill */}
                        <label
                          className="flex items-center gap-1.5 rounded-full border border-[#CBD5E1] bg-white px-3 py-1 text-[11.5px] font-medium text-[#334155] hover:bg-[#F8FAFC] cursor-pointer shadow-2xs"
                          title="Mốc thời điểm diễn ra sự việc để đối chiếu luật có hiệu lực"
                        >
                          <CalendarDays className="h-3.5 w-3.5 text-[#1E3A8A]" />
                          <span>Mốc:</span>
                          <input
                            type="date"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="bg-transparent font-mono text-[11.5px] font-bold text-[#0F172A] outline-none cursor-pointer"
                          />
                        </label>

                        {/* Pipeline Selector Pill */}
                        <Popover open={pipelineMenuOpen} onOpenChange={setPipelineMenuOpen}>
                          <PopoverTrigger asChild>
                            <button
                              className="flex items-center gap-1.5 rounded-full border border-[#CBD5E1] bg-white px-3 py-1 text-[11.5px] font-semibold text-[#1E3A8A] hover:bg-[#F8FAFC] shadow-2xs"
                              title="Chọn cách tra cứu"
                            >
                              <span>{PIPELINE_LABELS[pipeline]}</span>
                              <ChevronDown className="h-3.5 w-3.5 text-[#64748B]" />
                            </button>
                          </PopoverTrigger>
                          <PopoverContent align="start" className="w-[280px] rounded-2xl border border-[#CBD5E1] bg-white p-1.5 shadow-xl">
                            <div className="px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
                              Chọn cách tra cứu
                            </div>
                            {PIPELINES.map((p) => (
                              <button
                                key={p.key}
                                onClick={() => { setPipeline(p.key); setPipelineMenuOpen(false); }}
                                className={`flex w-full flex-col rounded-xl px-3 py-2 text-left transition ${
                                  pipeline === p.key ? "bg-[#EFF6FF] text-[#1E3A8A]" : "hover:bg-[#F8FAFC] text-[#0F172A]"
                                }`}
                              >
                                <span className="text-[12.5px] font-bold">{p.label}</span>
                                <span className="text-[11px] text-[#64748B]">{p.desc}</span>
                              </button>
                            ))}
                          </PopoverContent>
                        </Popover>
                      </div>

                      {/* Send Button */}
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => alert("Chức năng ghi âm câu hỏi (Voice Input) đang sẵn sàng.")}
                          className="flex h-8 w-8 items-center justify-center rounded-full text-[#64748B] hover:bg-[#E2E8F0]"
                          title="Nhập bằng giọng nói"
                        >
                          <Mic className="h-4 w-4" />
                        </button>

                        <button
                          onClick={() => send()}
                          disabled={!query.trim() || loading}
                          className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1E3A8A] text-white shadow-2xs transition hover:bg-[#1E40AF] active:scale-95 disabled:bg-[#CBD5E1] disabled:text-[#94A3B8]"
                          title="Gửi câu hỏi"
                        >
                          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Suggestion Chips */}
                  <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                    {SCENARIOS.map((s) => (
                      <button
                        key={s.id}
                        onClick={() => {
                          setQuery(s.query);
                          setDate(s.date);
                          send(s.query, s.date);
                        }}
                        className="flex items-center gap-1.5 rounded-full border border-[#CBD5E1] bg-white px-3.5 py-1.5 text-[12px] font-medium text-[#334155] shadow-2xs transition hover:border-[#1E3A8A] hover:bg-[#F8FAFC]"
                      >
                        <FileText className="h-3 w-3 text-[#1E3A8A]" />
                        <span>{s.label.replace(/^Kịch bản \d+:\s*/, "").replace("Bẫy niên đại trước", "Quy định trước")}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              /* ===============================================================
                 ACTIVE CONVERSATION DISPLAY
                 =============================================================== */
              <div className="space-y-6 pb-28">
                {messages.map((m) => (
                  <div key={m.id} className="space-y-4">
                    {/* User Prompt */}
                    <div className="flex justify-end">
                      <div className="max-w-[85%] rounded-3xl rounded-br-md bg-[#F1F5F9] px-5 py-3.5 text-[#0F172A] shadow-2xs border border-[#CBD5E1]">
                        <p className="text-[14.5px] leading-relaxed">{m.q}</p>
                        <div className="mt-2 flex flex-wrap items-center justify-end gap-2 text-[11px] text-[#64748B]">
                          <CalendarDays className="h-3 w-3 text-[#1E3A8A]" />
                          <span>Mốc sự kiện: <strong>{fmtDate(m.date)}</strong></span>
                          <span>•</span>
                          <span className="font-semibold text-[#1E3A8A]">{PIPELINE_LABELS[m.pipeline]}</span>
                        </div>
                      </div>
                    </div>

                    {/* AI Response or Multi-step Loading */}
                    {m.result ? (
                      <Answer
                        msg={m}
                        onOpenCitation={openCitation}
                      />
                    ) : (
                      <div className="rounded-2xl border border-[#CBD5E1] bg-white p-4 shadow-xs">
                        <div className="mb-3 flex items-center gap-2 text-[13px] font-bold text-[#1E3A8A]">
                          <Loader2 className="h-4 w-4 animate-spin text-[#1E3A8A]" />
                          <span>Đang tra cứu quy định thuế GTGT cho bạn...</span>
                        </div>
                        <ul className="space-y-2 text-[12.5px]">
                          {STEPS.map((l, i) => (
                            <li
                              key={l}
                              className={`flex items-center gap-2.5 transition ${
                                i <= step ? "text-[#0F172A]" : "text-[#94A3B8]"
                              }`}
                            >
                              {i < step ? (
                                <CheckCircle2 className="h-4 w-4 text-[#059669] shrink-0" />
                              ) : i === step ? (
                                <Loader2 className="h-4 w-4 animate-spin text-[#1E3A8A] shrink-0" />
                              ) : (
                                <span className="h-4 w-4 rounded-full border border-[#CBD5E1] shrink-0" />
                              )}
                              <span>{l}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
                <div ref={endRef} />
              </div>
            )}
          </div>
        </div>

        {/* Bottom Floating Composer (khi đã có tin nhắn) */}
        {messages.length > 0 && (
          <div className="relative z-20 shrink-0 border-t border-[#F1F5F9] bg-white/90 px-4 py-3 backdrop-blur-md">
            <div className="mx-auto w-full max-w-[760px]">
              <div className="rounded-2xl sm:rounded-full border border-[#CBD5E1] bg-[#F8FAFC] pl-4 pr-2 py-1.5 shadow-xs transition focus-within:border-[#1E3A8A] focus-within:bg-white focus-within:ring-2 focus-within:ring-[#1E3A8A]/15 flex flex-wrap items-center gap-2">
                <textarea
                  ref={taRef}
                  value={query}
                  rows={1}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  placeholder="Nhập câu hỏi tiếp theo về thuế GTGT..."
                  className="min-w-0 basis-full sm:basis-0 flex-1 resize-none bg-transparent py-1 text-[14px] outline-none placeholder:text-[#94A3B8]"
                />

                <label className="order-1 flex items-center gap-1 rounded-full border border-[#CBD5E1] bg-white px-2.5 py-1 text-[11px] font-medium text-[#334155] cursor-pointer shadow-2xs">
                  <CalendarDays className="h-3 w-3 text-[#1E3A8A]" />
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="bg-transparent font-mono text-[11px] font-semibold text-[#0F172A] outline-none cursor-pointer"
                  />
                </label>

                <select
                  value={pipeline}
                  aria-label="Cách tra cứu"
                  onChange={(e) => setPipeline(e.target.value as Pipeline)}
                  className="order-3 sm:order-2 min-w-0 max-w-full basis-full sm:basis-auto flex-1 rounded-full border border-[#CBD5E1] bg-white px-2.5 py-1 text-[11px] font-semibold text-[#1E3A8A] outline-none cursor-pointer shadow-2xs"
                >
                  {PIPELINES.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
                </select>

                <button
                  onClick={() => send()}
                  disabled={!query.trim() || loading}
                  className="order-2 sm:order-3 ml-auto flex h-8 w-8 items-center justify-center rounded-full bg-[#1E3A8A] text-white transition hover:bg-[#1E40AF] active:scale-95 disabled:bg-[#CBD5E1] disabled:text-[#94A3B8]"
                >
                  {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowUp className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* =========================================================================
          DRAWER 1: THƯ VIỆN TOÀN BỘ VĂN BẢN (CHIA THEO MỤC: LUẬT, NGHỊ ĐỊNH, THÔNG TƯ)
         ========================================================================= */}
      <aside
        aria-label="Thư viện văn bản pháp luật"
        hidden={!libraryOpen}
        className={`fixed inset-y-0 right-0 z-40 h-full shrink-0 flex-col border-l border-[#CBD5E1] bg-[#F8FAFC] shadow-2xl xl:relative ${
          libraryOpen ? "flex w-full sm:w-[480px]" : "!hidden"
        }`}
      >
        <div className="flex min-h-14 shrink-0 items-center justify-between gap-2 border-b border-[#CBD5E1] bg-white px-4">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-[#1E3A8A]" />
            <span className="font-bold text-[14px] text-[#1E3A8A]">
              Kho Văn Bản Pháp Luật GTGT Toàn Thư
            </span>
          </div>
          <button
            onClick={() => setLibraryOpen(false)}
            className="rounded-full p-1.5 text-[#64748B] hover:bg-[#F1F5F9]"
            title="Đóng thư viện"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Categories Tabs: Tất cả, Luật, Nghị định, Thông tư */}
        <div className="flex shrink-0 overflow-x-auto border-b border-[#CBD5E1] bg-white px-3 pt-2 gap-1 whitespace-nowrap text-[12px]">
          <button
            onClick={() => setLibraryCategory("all")}
            className={`px-3 py-1.5 font-semibold rounded-t-lg transition ${
              libraryCategory === "all" ? "bg-[#EFF6FF] text-[#1E3A8A] border-b-2 border-[#1E3A8A]" : "text-[#64748B] hover:bg-gray-50"
            }`}
          >
            Tất cả ({DOCS.length})
          </button>
          <button
            onClick={() => setLibraryCategory("luat")}
            className={`px-3 py-1.5 font-semibold rounded-t-lg transition ${
              libraryCategory === "luat" ? "bg-[#EFF6FF] text-[#1E3A8A] border-b-2 border-[#1E3A8A]" : "text-[#64748B] hover:bg-gray-50"
            }`}
          >
            Luật ({DOCS.filter((doc) => doc.id.startsWith("l")).length})
          </button>
          <button
            onClick={() => setLibraryCategory("nghidinh")}
            className={`px-3 py-1.5 font-semibold rounded-t-lg transition ${
              libraryCategory === "nghidinh" ? "bg-[#EFF6FF] text-[#1E3A8A] border-b-2 border-[#1E3A8A]" : "text-[#64748B] hover:bg-gray-50"
            }`}
          >
            Nghị định ({DOCS.filter((doc) => doc.id.startsWith("nd")).length})
          </button>
          <button
            onClick={() => setLibraryCategory("thongtu")}
            className={`px-3 py-1.5 font-semibold rounded-t-lg transition ${
              libraryCategory === "thongtu" ? "bg-[#EFF6FF] text-[#1E3A8A] border-b-2 border-[#1E3A8A]" : "text-[#64748B] hover:bg-gray-50"
            }`}
          >
            Thông tư ({DOCS.filter((doc) => doc.id.startsWith("tt")).length})
          </button>
        </div>

        {/* Search bar inside library */}
        <div className="p-3 border-b border-[#CBD5E1] bg-[#F1F5F9]">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#94A3B8]" />
            <input
              type="text"
              value={librarySearch}
              onChange={(e) => setLibrarySearch(e.target.value)}
              placeholder="Tìm kiếm điều, khoản, từ khóa trong kho văn bản..."
              className="w-full rounded-xl border border-[#CBD5E1] bg-white pl-8 pr-3 py-1.5 text-[12px] outline-none focus:border-[#1E3A8A]"
            />
          </div>
        </div>

        {/* Document Selector Pills */}
        <div className="flex gap-1.5 overflow-x-auto border-b border-[#CBD5E1] bg-white p-2 text-[11.5px]">
          {categorizedDocs.map((d) => (
            <button
              key={d.id}
              onClick={() => openDocument(d.id)}
              className={`shrink-0 rounded-full px-3 py-1 font-semibold transition ${
                activeLibraryDoc === d.id
                  ? "bg-[#1E3A8A] text-white shadow-xs"
                  : "bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]"
              }`}
            >
              {d.tab}
            </button>
          ))}
        </div>

        {/* Selected Document Details & Content */}
        <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto p-4 space-y-4" aria-busy={!currentDocumentState || currentDocumentState.status === "loading"}>
          <div className="rounded-2xl border border-[#BFDBFE] bg-[#EFF6FF] p-3 text-[12px]">
            <div className="font-bold text-[#1E3A8A]">{libraryDocument ? `${legalReferenceLabel(libraryDocument.id)} — ${libraryDocument.title}` : activeDocData?.full || legalReferenceLabel(canonicalDocumentId(activeLibraryDoc) || "Văn bản được trích dẫn")}</div>
            {libraryDocument && <div className="mt-1 text-[#475569]">Có hiệu lực từ: {fmtDate(libraryDocument.valid_from)}{libraryDocument.valid_to && libraryDocument.valid_to !== "9999-12-31" ? ` đến ${fmtDate(libraryDocument.valid_to)}` : ""}</div>}
          </div>

          {(!currentDocumentState || currentDocumentState.status === "loading") && (
            <p role="status" className="flex items-center gap-2 text-[13px] text-[#475569]"><Loader2 className="h-4 w-4 animate-spin" />Đang tải toàn văn...</p>
          )}
          {currentDocumentState?.status === "error" && (
            <div role="alert" className="rounded-xl border border-[#FED7AA] bg-[#FFF7ED] p-3 text-[13px] text-[#9A3412]">
              <p>Chưa tải được toàn văn văn bản.</p>
              {activeDocData && <p className="mt-1 font-semibold">Bên dưới chỉ là trích đoạn lưu sẵn, không phải toàn văn.</p>}
              <button onClick={() => setDocumentRetry((value) => value + 1)} className="mt-2 rounded-lg border border-[#FDBA74] px-3 py-1 font-semibold focus-visible:outline-2">Thử lại</button>
            </div>
          )}
          {articleUnavailable && <div role="status" className="rounded-xl border border-[#FED7AA] bg-[#FFF7ED] p-3 text-[13px] text-[#9A3412]">
            <p>Chưa có nội dung {legalReferenceLabel(activeLibraryArticle!)} trong phần văn bản hiện có.</p>
            {currentDocumentState?.status === "ready" && <button onClick={() => setDocumentRetry((value) => value + 1)} className="mt-2 rounded-lg border border-[#FDBA74] px-3 py-1 font-semibold">Tải lại toàn văn</button>}
          </div>}

          {librarySections.map((ch, idx) => (
            <div key={idx} className="space-y-3">
              {ch.title && <div className="font-bold text-[12px] uppercase text-[#64748B] border-b border-[#CBD5E1]/50 pb-1">{ch.title}</div>}
              {ch.articles.map((art) => (
                <div
                  key={art.id}
                  id={`lib-art-${art.id}`}
                  tabIndex={-1}
                  data-selected={art.id === activeLibraryArticle}
                  className={`scroll-mt-3 rounded-2xl border p-3.5 text-[12.5px] outline-none ${art.id === activeLibraryArticle ? "border-[#2563EB] bg-[#EFF6FF] ring-2 ring-[#BFDBFE]" : "border-[#CBD5E1] bg-white"}`}
                >
                  <div className="font-bold text-[#1E3A8A]">
                    {art.code.replace(/^Dieu\b/i, "Điều")}: {art.title}
                  </div>
                  <div className="mt-2 space-y-2 whitespace-pre-wrap break-words leading-relaxed text-[#334155]">
                    {art.lead && <p>{art.lead}</p>}
                    {!art.lead && !art.clauses?.length && art.content && <p>{art.content}</p>}
                    {(art.clauses || []).map((c, clauseIndex) => (
                      <div key={`${c.id}-${clauseIndex}`}>
                        <span className="font-semibold text-[#0F172A]">{c.code.replace(/^Khoan\b/i, "Khoản")}. </span>
                        <span>{c.content}</span>
                        {(c.points || []).map((point, pointIndex) => <p key={`${point.id}-${pointIndex}`} className="mt-1.5 pl-3"><strong>{point.code.replace(/^Diem\b/i, "Điểm")}. </strong>{point.content}</p>)}
                      </div>
                    ))}
                    {(art.tables || []).map((table, index) => <LegalTable key={index} text={table} />)}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </aside>

      {/* =========================================================================
          DRAWER 2: VĂN BẢN LIÊN QUAN TRỰC TIẾP ĐẾN CÂU HỎI VỪA TRẢ LỜI
         ========================================================================= */}
      <aside
        aria-label="Văn bản liên quan"
        hidden={!relatedOpen}
        className={`fixed inset-y-0 right-0 z-40 h-full shrink-0 flex-col border-l border-[#CBD5E1] bg-[#F8FAFC] shadow-2xl xl:relative ${
          relatedOpen ? "flex w-full sm:w-[440px]" : "!hidden"
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-[#CBD5E1] bg-white px-4">
          <div className="flex items-center gap-2">
            <FileSearch className="h-4 w-4 text-[#1E3A8A]" />
            <span className="font-bold text-[14px] text-[#1E3A8A]">
              Văn Bản Liên Quan Đến Câu Trả Lời
            </span>
          </div>
          <button
            onClick={() => setRelatedOpen(false)}
            className="rounded-full p-1.5 text-[#64748B] hover:bg-[#F1F5F9]"
            title="Đóng ngăn kéo"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="scroll-quiet flex-1 overflow-y-auto p-4 space-y-3.5">
          {latestCitations.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#CBD5E1] p-6 text-center text-[#64748B]">
              <FileSearch className="mx-auto h-8 w-8 text-[#94A3B8] mb-2" />
              <div className="font-semibold text-[13px] text-[#0F172A]">Chưa có trích dẫn pháp lý nào</div>
              <p className="mt-1 text-[12px]">
                Hãy gửi một câu hỏi pháp lý hoặc chọn một kịch bản mẫu để hệ thống trích xuất các điều khoản liên quan.
              </p>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-[#BFDBFE] bg-[#EFF6FF] p-3 text-[12px] text-[#1E3A8A]">
                Danh sách dưới đây gồm các điều khoản được trích dẫn trong câu trả lời gần nhất. Chọn “Mở toàn văn” để đọc đúng điều khoản.
              </div>

              {latestCitations.map((c, i) => {
                const targetDoc = DOCS.find((d) => d.id === c.doc);
                let targetArticle = null;
                if (targetDoc) {
                  for (const ch of targetDoc.chapters) {
                    for (const a of ch.articles) {
                      if (a.id === c.art) {
                        targetArticle = a;
                        break;
                      }
                    }
                  }
                }

                return (
                  <div
                    key={i}
                    className="rounded-2xl border border-[#CBD5E1] bg-white p-4 shadow-xs"
                  >
                    <div className="flex items-center justify-between gap-2 border-b border-[#F1F5F9] pb-2">
                      <span className="font-bold text-[13px] text-[#1E3A8A]">{legalPlainText(c.label)}</span>
                      <button
                        onClick={() => openCitation(c)}
                        className="flex items-center gap-1 text-[11px] font-semibold text-[#2563EB] hover:underline"
                      >
                        <span>Mở toàn văn</span>
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </div>

                    {targetArticle ? (
                      <div className="mt-2 text-[12px] text-[#334155] leading-relaxed">
                        <div className="font-semibold text-[#0F172A]">
                          Điều {targetArticle.no}: {targetArticle.title}
                        </div>
                        <div className="mt-1 space-y-1">
                          {targetArticle.clauses.slice(0, 2).map((cl) => (
                            <p key={cl.n}>
                              <strong>{cl.n}.</strong> {cl.text}
                            </p>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="mt-2 text-[12px] text-[#64748B]">
                        Chọn “Mở toàn văn” để tải nội dung điều khoản được trích dẫn.
                      </p>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </div>
      </aside>

      {/* =========================================================================
          MODAL 1: CÀI ĐẶT THỰC SỰ DÙNG (MODEL, NGÔN NGỮ, NGÀY THÁNG, GIAO DIỆN)
         ========================================================================= */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-[17px] font-bold text-[#1E3A8A] flex items-center gap-2">
              <Settings className="h-5 w-5" />
              <span>Cài đặt hệ thống</span>
            </DialogTitle>
            <DialogDescription className="text-[12.5px] text-[#64748B]">
              Chọn cách tra cứu, ngôn ngữ và ngày diễn ra sự việc mặc định
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2 text-[13px]">
            {/* 1. Model Pipeline Selection */}
            <div>
              <label className="font-bold text-[#0F172A] block mb-1">1. Cách tra cứu</label>
              <select
                value={settings.pipeline}
                onChange={(e) => {
                  const p = e.target.value as Pipeline;
                  setSettings({ ...settings, pipeline: p });
                  setPipeline(p);
                }}
                className="w-full rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-2.5 font-medium text-[13px] outline-none focus:border-[#1E3A8A]"
              >
                {PIPELINES.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
              </select>
              <p className="mt-1 text-[11px] text-[#64748B]">
                Chọn thẩm định toàn diện để đối chiếu thêm hiệu lực văn bản và căn cứ trích dẫn tại ngày diễn ra sự việc.
              </p>
            </div>

            {/* 2. Language Selection */}
            <div>
              <label className="font-bold text-[#0F172A] block mb-1">2. Ngôn ngữ giao diện &amp; Báo cáo</label>
              <select
                value={settings.language}
                onChange={(e) => setSettings({ ...settings, language: e.target.value as "vi" | "en" })}
                className="w-full rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-2.5 font-medium text-[13px] outline-none focus:border-[#1E3A8A]"
              >
                <option value="vi">Tiếng Việt (Chuẩn pháp điển hóa Việt Nam)</option>
                <option value="en">English (International Tax Guidance)</option>
              </select>
            </div>

            {/* 3. Default Evaluation Date */}
            <div>
              <label className="font-bold text-[#0F172A] block mb-1">3. Ngày diễn ra sự việc mặc định</label>
              <input
                type="date"
                value={settings.defaultDate}
                onChange={(e) => {
                  setSettings({ ...settings, defaultDate: e.target.value });
                  setDate(e.target.value);
                }}
                className="w-full rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-2.5 font-medium text-[13px] outline-none focus:border-[#1E3A8A]"
              />
              <p className="mt-1 text-[11px] text-[#64748B]">
                Mốc ngày mặc định áp dụng khi mở phiên hỏi đáp mới.
              </p>
            </div>

            {/* 4. Display Theme */}
            <div>
              <label className="font-bold text-[#0F172A] block mb-1">4. Giao diện</label>
              <div className="grid grid-cols-3 gap-2 text-center text-[12px]">
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, theme: "light" })}
                  className={`rounded-xl p-2 border font-medium ${
                    settings.theme === "light" ? "border-[#1E3A8A] bg-[#EFF6FF] text-[#1E3A8A]" : "border-[#CBD5E1] text-[#475569]"
                  }`}
                >
                  Sáng
                </button>
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, theme: "dark" })}
                  className={`rounded-xl p-2 border font-medium ${
                    settings.theme === "dark" ? "border-[#1E3A8A] bg-[#EFF6FF] text-[#1E3A8A]" : "border-[#CBD5E1] text-[#475569]"
                  }`}
                >
                  Tối
                </button>
                <button
                  type="button"
                  onClick={() => setSettings({ ...settings, theme: "system" })}
                  className={`rounded-xl p-2 border font-medium ${
                    settings.theme === "system" ? "border-[#1E3A8A] bg-[#EFF6FF] text-[#1E3A8A]" : "border-[#CBD5E1] text-[#475569]"
                  }`}
                >
                  Tự động
                </button>
              </div>
            </div>

            {/* 5. LLM Mode Toggle */}
            <div className="flex items-center justify-between rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-3">
              <div>
                <div className="font-bold text-[#0F172A] text-[13px]">Bật hỗ trợ diễn giải bằng AI</div>
                <div className="text-[11.5px] text-[#64748B]">Diễn giải tình huống, căn cứ và kết luận thành câu trả lời dễ đọc</div>
              </div>
              <input
                type="checkbox"
                checked={settings.useLlm}
                onChange={(e) => setSettings({ ...settings, useLlm: e.target.checked })}
                className="h-4 w-4 rounded accent-[#1E3A8A] cursor-pointer"
              />
            </div>

            {/* 5. Account Management: Login / Logout */}
            <div className="border-t border-[#E2E8F0] pt-3">
              <label className="font-bold text-[#0F172A] block mb-1">5. Trạng thái người dùng</label>
              {user.isLoggedIn ? (
                <div className="flex items-center justify-between rounded-xl bg-[#F1F5F9] p-3 text-[12px]">
                  <div>
                    <div className="font-bold text-[#1E293B]">{user.name}</div>
                    <div className="text-[#64748B]">{user.role} (MST: {user.taxCode})</div>
                  </div>
                  <button
                    onClick={() => {
                      setUser(DEFAULT_USER);
                      setSettingsOpen(false);
                    }}
                    className="flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-[11px] font-semibold text-red-600 border border-[#CBD5E1] hover:bg-red-50"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                    <span>Đăng xuất</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setSettingsOpen(false);
                    setLoginModalOpen(true);
                  }}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1E3A8A] py-2 text-[13px] font-semibold text-white hover:bg-[#1E40AF]"
                >
                  <User className="h-4 w-4" />
                  <span>Đăng nhập tài khoản cá nhân / doanh nghiệp</span>
                </button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* =========================================================================
          MODAL 2: ĐĂNG NHẬP (DÀNH CHO NGƯỜI NỘP THUẾ / DOANH NGHIỆP)
         ========================================================================= */}
      <Dialog open={loginModalOpen} onOpenChange={setLoginModalOpen}>
        <DialogContent className="max-w-md rounded-2xl bg-white p-6 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-[17px] font-bold text-[#1E3A8A] flex items-center gap-2">
              <UserCheck className="h-5 w-5" />
              <span>Đăng nhập Cổng Dịch vụ Pháp lý Thuế GTGT</span>
            </DialogTitle>
            <DialogDescription className="text-[12.5px] text-[#64748B]">
              Dành cho cá nhân, hộ kinh doanh và doanh nghiệp kê khai, nộp thuế
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 pt-2 text-[13px]">
            <div>
              <label className="font-semibold text-[#0F172A] block mb-1">Tên Người nộp thuế / Doanh nghiệp</label>
              <input
                type="text"
                defaultValue="Huỳnh Tấn Phúc"
                id="login-name"
                className="w-full rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-2.5 text-[13px] outline-none focus:border-[#1E3A8A]"
                placeholder="Nhập họ và tên hoặc tên công ty..."
              />
            </div>

            <div>
              <label className="font-semibold text-[#0F172A] block mb-1">Mã số thuế / Căn cước công dân</label>
              <input
                type="text"
                defaultValue="1801234567"
                id="login-mst"
                className="w-full rounded-xl border border-[#CBD5E1] bg-[#F8FAFC] p-2.5 text-[13px] outline-none focus:border-[#1E3A8A]"
                placeholder="Ví dụ: 1801234567"
              />
            </div>

            <div className="rounded-xl bg-[#EFF6FF] p-3 text-[11.5px] text-[#1E3A8A] border border-[#BFDBFE]">
              Hệ thống công cộng phục vụ tra cứu miễn phí. Sau khi đăng nhập, hệ thống sẽ chào theo tên của bạn và ghi nhớ các mốc sự kiện liên quan.
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setLoginModalOpen(false)}
                className="flex-1 rounded-xl border border-[#CBD5E1] py-2 font-medium text-[#475569] hover:bg-[#F1F5F9]"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={() => {
                  const inputName = (document.getElementById("login-name") as HTMLInputElement)?.value || "Huỳnh Tấn Phúc";
                  const inputMst = (document.getElementById("login-mst") as HTMLInputElement)?.value || "1801234567";
                  setUser({
                    isLoggedIn: true,
                    name: inputName.trim(),
                    role: "Người nộp thuế / Doanh nghiệp",
                    taxCode: inputMst.trim(),
                  });
                  setLoginModalOpen(false);
                }}
                className="flex-1 rounded-xl bg-[#1E3A8A] py-2 font-semibold text-white hover:bg-[#1E40AF]"
              >
                Đăng nhập
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function documentSections(document: LegalDocumentDetail): LegalChapter[] {
  const seen = new Set<string>();
  const takeNewArticles = (articles: LegalChapter["articles"] = []) => articles.filter((article) => {
    if (seen.has(article.id)) return false;
    seen.add(article.id);
    return true;
  });
  const sections = (document.chapters || []).map((chapter) => ({
    ...chapter,
    title: chapter.title || chapter.code || "",
    articles: takeNewArticles(chapter.articles),
  })).filter((chapter) => chapter.articles.length > 0);
  const remaining = takeNewArticles(document.articles);
  if (remaining.length) sections.push({ id: `${document.id}-remaining`, title: "", articles: remaining });
  return sections;
}

function localExcerpt(document: LawDoc): LegalDocumentDetail {
  const docId = canonicalDocumentId(document.id)!;
  return {
    id: docId, code: document.tab, title: document.full,
    valid_from: document.effective.split("/").reverse().join("-"), valid_to: "",
    chapters: document.chapters.map((chapter, index) => ({
      id: `${docId}-chapter-${index}`, title: chapter.title,
      articles: chapter.articles.map((article) => ({
        id: `${docId}_D${article.no}`, code: `Điều ${article.no}`, title: article.title,
        content: "", lead: article.note,
        clauses: article.clauses.map((clause) => ({
          id: `${article.id}-clause-${clause.n}`, code: `Khoản ${clause.n}`, content: clause.text,
          points: clause.points?.map((point) => ({ id: `${article.id}-${clause.n}-${point.l}`, code: `Điểm ${point.l}`, content: point.text })),
        })),
        tables: article.table ? [[article.table.head, article.table.head.map(() => "---"), ...article.table.rows].map((row) => `| ${row.join(" | ")} |`).join("\n")] : [],
      })),
    })),
  };
}

function LegalTable({ text }: { text: string }) {
  const rows = text.trim().split(/\r?\n/).map((line) => line.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, "|")));
  if (rows.length < 2 || !rows[1].every((cell) => /^:?-{3,}:?$/.test(cell))) {
    return <p className="whitespace-pre-wrap">{text}</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-[#CBD5E1] whitespace-normal">
      <table className="w-full border-collapse text-left text-[12px]">
        <thead className="bg-[#F1F5F9]"><tr>{rows[0].map((cell, index) => <th scope="col" key={index} className="border-b border-[#CBD5E1] px-3 py-2">{cell}</th>)}</tr></thead>
        <tbody>{rows.slice(2).map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column} className="border-b border-[#E2E8F0] px-3 py-2 align-top">{cell}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function splitLegalParagraphs(text: string): string[] {
  return text.split(/\r?\n+/).flatMap((line) => {
    const cases = [...line.matchAll(/(?:^|\s)\((\d+)\)/g)];
    if (cases.length < 2 || !cases.every((item, index) => Number(item[1]) === index + 1)) return [line.trim()];
    const starts = cases.map((item) => item.index! + (item[0].startsWith("(") ? 0 : 1));
    return [line.slice(0, starts[0]).trim(), ...starts.map((start, index) => line.slice(start, starts[index + 1]).trim())];
  }).filter(Boolean);
}

function supplementaryRule(result: Result): string {
  const rule = result.rule.replace(/^(?:(?:Căn cứ(?: pháp lý(?: viện dẫn)?)?)\s*:\s*)+/i, "").trim();
  const ids = [...rule.matchAll(new RegExp(`\\[(${LEGAL_REFERENCE_PATTERN})\\]|\\b(${LEGAL_REFERENCE_PATTERN})\\b`, "gi"))];
  const remainder = rule.replace(new RegExp(`\\[${LEGAL_REFERENCE_PATTERN}\\]|\\b${LEGAL_REFERENCE_PATTERN}\\b`, "gi"), "").replace(/[\s,;.()[\]]/g, "");
  const listedArticles = new Set((result.citations || []).map(citationArticleId));
  return ids.length > 0 && !remainder && ids.every((match) => listedArticles.has(citationArticleId(parseCitationId(match[1] || match[2])))) ? "" : rule;
}

function SmartLegalText({ text, onOpenCitation }: { text: string; onOpenCitation: (citation: Citation) => void }) {
  const content = friendlyLegalText(text);
  const tokens = new RegExp(`\\[${LEGAL_REFERENCE_PATTERN}\\]|\\b${LEGAL_REFERENCE_PATTERN}\\b|\\d+(?:[.,]\\d+)?[ \\t]*%`, "gi");
  const parts: ReactNode[] = [];
  let position = 0;
  for (const match of content.matchAll(tokens)) {
    const start = match.index!;
    parts.push(content.slice(position, start));
    const token = match[0];
    if (token.endsWith("%")) {
      parts.push(<strong key={start} data-tax-rate className="inline-block rounded-md bg-[#DBEAFE] px-1.5 py-0.5 font-bold text-[#1E3A8A]">{token}</strong>);
    } else {
      const id = token.replace(/^\[|\]$/g, "");
      if (/_D\d+/i.test(id)) {
        const citation = parseCitationId(id);
        parts.push(<button key={start} type="button" onClick={() => onOpenCitation(citation)} aria-label={`Đọc ${citation.label}`} title={`Đọc ${citation.label}`} className="mx-0.5 inline-flex max-w-full items-baseline gap-1 rounded-full border border-[#BFDBFE] bg-[#EFF6FF] px-2 py-0.5 align-baseline text-left text-[0.85em] font-semibold leading-normal text-[#1E3A8A] transition hover:bg-[#DBEAFE] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#2563EB]"><FileText aria-hidden="true" className="relative top-0.5 h-3 w-3 shrink-0" /><span>{citation.label}</span></button>);
      } else {
        parts.push(<span key={start}>{legalReferenceLabel(id)}</span>);
      }
    }
    position = start + token.length;
  }
  parts.push(content.slice(position));
  return <>{parts}</>;
}

// Answer Component with Public Legal Reasoning, Citations, and Actions
function Answer({
  msg,
  onOpenCitation,
}: {
  msg: Msg;
  onOpenCitation: (citation: Citation) => void;
}) {
  const r = msg.result!;
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const rule = supplementaryRule(r);
  const shareText = legalPlainText(r.conclusion) + (rule ? "\n\nCăn cứ: " + legalPlainText(rule) : "") +
    ((r.citations || []).length ? "\n\nVăn bản trích dẫn: " + r.citations.map((citation) => legalPlainText(citation.label)).join("; ") : "");

  async function copyText() {
    await navigator.clipboard.writeText(shareText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="group min-w-0 break-words rounded-3xl border border-[#CBD5E1] bg-white/95 backdrop-blur-xs p-4 sm:p-5 shadow-xs transition hover:shadow-md">
      {/* Header Row: Public Legal Emblem + Temporal Validity Tag */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#F1F5F9] pb-3.5">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#EFF6FF] border border-[#BFDBFE]">
            <img src={emblem} alt="Quốc huy" className="h-4 w-auto" />
          </div>
          <span className="font-bold text-[14px] text-[#1E3A8A]">Thẩm định Pháp lý Thuế GTGT</span>
          <span className="rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[10.5px] font-semibold text-[#1E3A8A] border border-[#BFDBFE]">
            {PIPELINE_LABELS[msg.pipeline]}
          </span>
        </div>

        <div className="flex items-center gap-1.5 rounded-full bg-[#F8FAFC] px-3 py-1 text-[11px] font-semibold text-[#475569] border border-[#E2E8F0]">
          <CalendarDays className="h-3 w-3 text-[#1E3A8A]" />
          <span>Thời điểm thẩm định: <strong>{fmtDate(msg.date)}</strong></span>
        </div>
      </div>

      {/* Main Legal Conclusion Box */}
      <div className="mt-3.5 rounded-2xl bg-[#F8FAFC] p-4 border border-[#E2E8F0]">
        <div className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider">
          {r.is_out_of_domain ? (
            <>
              <AlertTriangle className="h-4 w-4 text-[#D97706]" />
              <span className="text-[#D97706]">Lưu ý phạm vi nghiệp vụ</span>
            </>
          ) : r.is_greeting ? (
            <>
              <Sparkles className="h-4 w-4 text-[#2563EB]" />
              <span className="text-[#2563EB]">Chào mừng &amp; Hướng dẫn tra cứu</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4 text-[#059669]" />
              <span className="text-[#1E3A8A]">Kết luận pháp lý</span>
            </>
          )}
        </div>
        <div className="mt-2 space-y-3 text-[15px] font-semibold leading-relaxed text-[#0F172A]">
          {splitLegalParagraphs(r.conclusion).map((paragraph, index) => <p key={index}><SmartLegalText text={paragraph} onOpenCitation={onOpenCitation} /></p>)}
        </div>
        {!r.is_out_of_domain && !r.is_greeting && rule && (
          <p className="mt-2 text-[13px] leading-relaxed text-[#475569]">
            <strong>Căn cứ:</strong> <SmartLegalText text={rule} onOpenCitation={onOpenCitation} />
          </p>
        )}
      </div>

      {/* Warning / Temporal Trap Box */}
      {r.trap && (
        <div className="mt-3 flex items-start gap-2.5 rounded-2xl border border-[#FED7AA] bg-[#FFF7ED] p-3.5 text-[12.5px] text-[#9A3412]">
          <AlertTriangle className="h-4 w-4 shrink-0 text-[#EA580C] mt-0.5" />
          <div className="leading-relaxed">
            <strong>Lưu ý về thời điểm áp dụng:</strong> <SmartLegalText text={r.trap} onOpenCitation={onOpenCitation} />
          </div>
        </div>
      )}

      {/* Application Steps */}
      {r.application && r.application.length > 0 && (
        <div className="mt-3.5 space-y-1.5">
          <div className="text-[11.5px] font-bold uppercase tracking-wider text-[#64748B]">
            Giải thích cho tình huống của bạn:
          </div>
          <ul className="space-y-1 text-[13px] text-[#334155]">
            {r.application.flatMap(splitLegalParagraphs).map((app, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[#1E3A8A] shrink-0" />
                <span className="min-w-0"><SmartLegalText text={app} onOpenCitation={onOpenCitation} /></span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Audit Checklist */}
      <div className="mt-3.5 space-y-1.5">
        <div className="text-[11.5px] font-bold uppercase tracking-wider text-[#64748B]">
          Kết quả đối chiếu và lưu ý:
        </div>
        <ul className="space-y-1.5 text-[13px]">
          {(r.audit || []).map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-[#334155]">
              <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${a.tone === "ok" ? "bg-[#059669]" : a.tone === "bad" ? "bg-[#DC2626]" : "bg-[#EA580C]"}`} />
              <span className="min-w-0"><SmartLegalText text={a.text} onOpenCitation={onOpenCitation} /></span>
            </li>
          ))}
        </ul>
      </div>

      {/* Citations Badges */}
      {!r.is_out_of_domain && !r.is_greeting && r.citations && r.citations.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-[#F1F5F9] pt-3">
          <span className="text-[11px] font-bold text-[#64748B]">Văn bản trích dẫn:</span>
          {r.citations.map((c) => (
            <button
              key={c.label}
              onClick={() => onOpenCitation(c)}
              className="flex items-center gap-1 rounded-full border border-[#BFDBFE] bg-[#EFF6FF] px-2.5 py-0.5 text-[11px] font-semibold text-[#1E3A8A] transition hover:bg-[#DBEAFE]"
              title={`Đọc ${legalPlainText(c.label)}`}
            >
              <span>{legalPlainText(c.label)}</span>
              <ExternalLink className="h-2.5 w-2.5" />
            </button>
          ))}
        </div>
      )}

      {/* Action Toolbar: Copy, Thumbs Up/Down, Share */}
      <div className="mt-3 flex items-center justify-between border-t border-[#F1F5F9] pt-2.5 text-[#64748B]">
        <div className="flex items-center gap-1">
          <button
            onClick={copyText}
            className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-[#F1F5F9] text-[#64748B]"
            title="Sao chép kết luận"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setFeedback(feedback === "up" ? null : "up")}
            className={`flex h-7 w-7 items-center justify-center rounded-full hover:bg-[#F1F5F9] ${feedback === "up" ? "text-[#059669] bg-green-50" : "text-[#64748B]"}`}
            title="Phản hồi chính xác"
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setFeedback(feedback === "down" ? null : "down")}
            className={`flex h-7 w-7 items-center justify-center rounded-full hover:bg-[#F1F5F9] ${feedback === "down" ? "text-[#DC2626] bg-red-50" : "text-[#64748B]"}`}
            title="Phản hồi chưa thỏa đáng"
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => {
              if (navigator.share) {
                navigator.share({ title: "Tư vấn thuế GTGT", text: shareText });
              } else {
                copyText();
              }
            }}
            className="flex h-7 w-7 items-center justify-center rounded-full hover:bg-[#F1F5F9] text-[#64748B]"
            title="Chia sẻ"
          >
            <Share2 className="h-3.5 w-3.5" />
          </button>
        </div>

        {copied && (
          <span className="text-[11px] font-semibold text-[#059669]">Đã sao chép!</span>
        )}
      </div>
    </div>
  );
}

export default App;
