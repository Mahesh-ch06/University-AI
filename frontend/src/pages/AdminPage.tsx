import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchAdminStats,
  fetchAdminDocuments,
  uploadDocument,
  deactivateDocument,
  fetchAdminFeedback,
  fetchAdminConversations,
  fetchAdminConversationDetail,
  deleteAdminConversation,
  promoteExemplar,
  downloadAllConversations,
  fetchAdminLeads,
  fetchAdminLeadStats,
  updateLeadStatus,
  exportAdminLeads,
  type AdminStats,
  type DocumentItem,
  type FeedbackItem,
  type AdminConversationItem,
  type AdminConversationDetail,
  type AdminMessageDetail,
  type ProspectiveLeadItem,
  type LeadStats,
} from "../services/api";
import "./AdminPage.css";

interface Props {
  onBackToChat: () => void;
}

/** Strips markdown formatting to display clean preview text */
function plainPreview(text: string): string {
  return (text || "")
    .replace(/\*\*|__|`|#{1,6}\s/g, "")
    .replace(/^\s*[-*•]\s+/gm, "")
    .replace(/\|/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const PROGRAM_LABEL_MAP: Record<string, string> = {
  btech_cse: "B.Tech CSE",
  btech_ai_robotics: "B.Tech AI & Robotics",
  btech_ece: "B.Tech ECE",
  btech_eee: "B.Tech EEE",
  btech_mech: "B.Tech Mechanical",
  btech_civil: "B.Tech Civil",
  btech_biotech: "B.Tech Biotechnology",
  btech_food_tech: "B.Tech Food Technology",
  btech_engg_physics: "B.Tech Engineering Physics",
  btech_iep: "B.Tech IEP (International)",
  bsc_agri: "B.Sc Agriculture",
  bdes: "B.Des (Design)",
  bba: "BBA",
  bsc_hospitality: "B.Sc Hospitality",
  bba_specialised: "BBA (Specialised)",
  bca: "BCA",
  bsc_cs: "B.Sc Computer Science",
  bsc_maths_ai: "B.Sc Mathematics & AI",
  bcom: "B.Com",
  bsc_physics: "B.Sc Physics",
  bsc_chemistry: "B.Sc Chemistry",
  mba: "MBA",
  mba_agri: "MBA Agri Business",
  mca: "MCA",
  mtech: "M.Tech",
  msc: "M.Sc",
};

/** Formats program interest into clean, professional titles and resolves missing or raw slug values */
function formatProgramInterest(raw?: string | null, meta?: any): string {
  const val = (raw || "").trim();
  const lower = val.toLowerCase();

  // If known slug
  if (PROGRAM_LABEL_MAP[lower]) {
    return PROGRAM_LABEL_MAP[lower];
  }

  // If already a valid specific name and not an unhelpful placeholder
  if (val && !["not specified", "unknown", "none", "null", "undefined", ""].includes(lower)) {
    // If it has parenthesized specialisations (e.g. "B.Tech CSE (AIML, Data Science...)"), shorten to primary
    if (val.includes(" (") && val.startsWith("B.Tech")) {
      return val.split(" (")[0];
    }
    return val;
  }

  // Attempt resolution from metadata (pending_question, query, program)
  const metaQ = meta?.pending_question || meta?.query || meta?.program_interest || meta?.program || "";
  const q = String(metaQ).toLowerCase();
  if (q) {
    if (q.includes("ai & robotics") || q.includes("ai and robotics")) return "B.Tech in AI and Robotics";
    if (q.includes("agri")) return "B.Sc Agriculture";
    if (q.includes("ece") || q.includes("electronics")) return "B.Tech ECE";
    if (q.includes("eee") || q.includes("electrical")) return "B.Tech EEE";
    if (q.includes("mech")) return "B.Tech Mechanical";
    if (q.includes("civil")) return "B.Tech Civil";
    if (q.includes("biotech")) return "B.Tech Biotechnology";
    if (q.includes("food tech")) return "B.Tech Food Technology";
    if (q.includes("mba")) return "MBA";
    if (q.includes("bba")) return "BBA";
    if (q.includes("bca")) return "BCA";
    if (q.includes("mca")) return "MCA";
    if (q.includes("design") || q.includes("bdes")) return "B.Des";
    if (q.includes("bcom") || q.includes("commerce")) return "B.Com";
    if (q.includes("cse") || q.includes("computer") || q.includes("software") || q.includes("data science") || q.includes("aiml")) return "B.Tech CSE";
  }

  return "General Admissions";
}

export default function AdminPage({ onBackToChat }: Props) {
  const [adminKey, setAdminKey] = useState<string>(
    () => sessionStorage.getItem("university_ai_admin_key") || ""
  );
  const [keyInput, setKeyInput] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"leads" | "chats" | "overview" | "documents" | "feedback">("leads");

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);

  // Conversations (Audit) state
  const [conversations, setConversations] = useState<AdminConversationItem[]>([]);
  const [conversationsTotal, setConversationsTotal] = useState<number>(0);
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [selectedConvDetail, setSelectedConvDetail] = useState<AdminConversationDetail | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);
  const [chatSearch, setChatSearch] = useState<string>("");
  const [feedbackFilter, setFeedbackFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const [isExportingAll, setIsExportingAll] = useState<boolean>(false);

  // Leads State
  const [leads, setLeads] = useState<ProspectiveLeadItem[]>([]);
  const [leadsTotal, setLeadsTotal] = useState<number>(0);
  const [leadStats, setLeadStats] = useState<LeadStats | null>(null);
  const [leadSearch, setLeadSearch] = useState<string>("");
  const [leadProgramFilter, setLeadProgramFilter] = useState<string>("all");
  const [leadSourceFilter, setLeadSourceFilter] = useState<string>("all");
  const [leadStatusFilter, setLeadStatusFilter] = useState<string>("all");
  const [leadPage, setLeadPage] = useState<number>(1);
  const [leadPageSize] = useState<number>(50);
  const [isExportingLeads, setIsExportingLeads] = useState<boolean>(false);
  const [updatingLeadId, setUpdatingLeadId] = useState<string | null>(null);

  const [promotingMessageId, setPromotingMessageId] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Upload Form state
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadType, setUploadType] = useState("policy");
  const [uploadDept, setUploadDept] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const detailScrollRef = useRef<HTMLDivElement>(null);

  const loadData = useCallback(async (key: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const [statsData, docsData, feedbackData, convsData, leadStatsData, leadsData] = await Promise.all([
        fetchAdminStats(key),
        fetchAdminDocuments(key),
        fetchAdminFeedback(key),
        fetchAdminConversations(key, { page: 1, pageSize: 50 }),
        fetchAdminLeadStats(key).catch(() => null),
        fetchAdminLeads(key, { page: 1, pageSize: 50 }).catch(() => ({ total: 0, items: [] })),
      ]);
      setStats(statsData);
      setDocuments(docsData.documents);
      setFeedback(feedbackData.items);
      setConversations(convsData.conversations);
      setConversationsTotal(convsData.total);
      if (leadStatsData) setLeadStats(leadStatsData);
      if (leadsData) {
        setLeads(leadsData.items || (leadsData as any).leads || []);
        setLeadsTotal(leadsData.total);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load admin data");
      setAdminKey("");
      sessionStorage.removeItem("university_ai_admin_key");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadConversationsOnly = useCallback(
    async (key: string, page: number, size: number, search: string, filter: string) => {
      try {
        const res = await fetchAdminConversations(key, {
          page,
          pageSize: size,
          search: search.trim() || undefined,
          feedbackFilter: filter === "all" ? undefined : filter,
        });
        setConversations(res.conversations);
        setConversationsTotal(res.total);
      } catch (err: unknown) {
        console.error("Failed to reload conversations:", err);
      }
    },
    []
  );

  const loadLeadsOnly = useCallback(
    async (
      key: string,
      page: number,
      size: number,
      search: string,
      program: string,
      source: string,
      status: string
    ) => {
      try {
        const [leadsRes, statsRes] = await Promise.all([
          fetchAdminLeads(key, {
            page,
            pageSize: size,
            search: search.trim() || undefined,
            program: program === "all" ? undefined : program,
            source: source === "all" ? undefined : source,
            status: status === "all" ? undefined : status,
          }),
          fetchAdminLeadStats(key).catch(() => null),
        ]);
        setLeads(leadsRes.items || (leadsRes as any).leads || []);
        setLeadsTotal(leadsRes.total);
        if (statsRes) setLeadStats(statsRes);
      } catch (err: unknown) {
        console.error("Failed to reload leads:", err);
      }
    },
    []
  );

  useEffect(() => {
    if (adminKey) {
      loadData(adminKey);
    }
  }, [adminKey, loadData]);

  // Refetch conversations when page, pageSize, filters or search change
  useEffect(() => {
    if (adminKey && activeTab === "chats") {
      const timer = setTimeout(() => {
        loadConversationsOnly(adminKey, currentPage, pageSize, chatSearch, feedbackFilter);
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [adminKey, activeTab, currentPage, pageSize, chatSearch, feedbackFilter, loadConversationsOnly]);

  // Refetch leads when lead filters change
  useEffect(() => {
    if (adminKey && activeTab === "leads") {
      const timer = setTimeout(() => {
        loadLeadsOnly(
          adminKey,
          leadPage,
          leadPageSize,
          leadSearch,
          leadProgramFilter,
          leadSourceFilter,
          leadStatusFilter
        );
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [
    adminKey,
    activeTab,
    leadPage,
    leadPageSize,
    leadSearch,
    leadProgramFilter,
    leadSourceFilter,
    leadStatusFilter,
    loadLeadsOnly,
  ]);

  const handleUpdateLeadStatus = async (leadId: string, newStatus: string) => {
    if (!adminKey) return;
    setUpdatingLeadId(leadId);
    try {
      const updated = await updateLeadStatus(adminKey, leadId, newStatus);
      setLeads((prev) => prev.map((l) => (l.id === leadId ? updated : l)));
      setActionNotice({
        text: `Status updated to "${newStatus}" for ${updated.name}`,
        type: "success",
      });
      fetchAdminLeadStats(adminKey).then((s) => setLeadStats(s)).catch(() => {});
    } catch (err: any) {
      setActionNotice({
        text: err.message || "Failed to update lead status",
        type: "error",
      });
    } finally {
      setUpdatingLeadId(null);
    }
  };

  const handleExportLeads = async () => {
    if (!adminKey || isExportingLeads) return;
    setIsExportingLeads(true);
    try {
      await exportAdminLeads(adminKey);
      setActionNotice({ text: "Prospective leads CSV exported successfully", type: "success" });
    } catch (err: any) {
      setActionNotice({ text: err.message || "Failed to export leads", type: "error" });
    } finally {
      setIsExportingLeads(false);
    }
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    sessionStorage.setItem("university_ai_admin_key", keyInput.trim());
    setAdminKey(keyInput.trim());
  };

  const handleLogout = () => {
    sessionStorage.removeItem("university_ai_admin_key");
    setAdminKey("");
    setStats(null);
    setDocuments([]);
    setConversations([]);
    setSelectedConvDetail(null);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadTitle.trim()) {
      alert("Please provide a title and select a document file.");
      return;
    }

    setIsUploading(true);
    setUploadSuccess(null);
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      formData.append("title", uploadTitle.trim());
      formData.append("document_type", uploadType);
      if (uploadDept.trim()) formData.append("department", uploadDept.trim());

      await uploadDocument(adminKey, formData);
      setUploadSuccess(`Successfully ingested "${uploadTitle}"!`);
      setUploadTitle("");
      setUploadDept("");
      setUploadFile(null);
      loadData(adminKey);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeactivate = async (docId: string) => {
    if (!confirm("Are you sure you want to deactivate this document?")) return;
    try {
      await deactivateDocument(adminKey, docId);
      loadData(adminKey);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Deactivation failed");
    }
  };

  const handleSelectConversation = async (convId: string) => {
    setSelectedConvId(convId);
    setIsLoadingDetail(true);
    setActionNotice(null);
    try {
      const detail = await fetchAdminConversationDetail(adminKey, convId);
      setSelectedConvDetail(detail);
      setTimeout(() => {
        if (detailScrollRef.current) {
          detailScrollRef.current.scrollTop = 0;
        }
      }, 50);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to load conversation details");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!confirm("Are you sure you want to delete this conversation log?")) return;
    try {
      await deleteAdminConversation(adminKey, convId);
      if (selectedConvId === convId) {
        setSelectedConvId(null);
        setSelectedConvDetail(null);
      }
      setActionNotice({ text: "Conversation deleted successfully.", type: "success" });
      loadConversationsOnly(adminKey, currentPage, pageSize, chatSearch, feedbackFilter);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete conversation");
    }
  };

  const handleExportAllMarkdown = async () => {
    setIsExportingAll(true);
    setActionNotice(null);
    try {
      await downloadAllConversations(adminKey, "markdown", {
        search: chatSearch,
        feedbackFilter,
      });
      setActionNotice({
        text: `📥 Complete dataset downloaded in Markdown (.md)! Ready for AI model training / evaluation.`,
        type: "success",
      });
    } catch (err: unknown) {
      setActionNotice({
        text: err instanceof Error ? err.message : "Failed to export all conversations",
        type: "error",
      });
    } finally {
      setIsExportingAll(false);
    }
  };

  const handleExportSingleJson = (conv: AdminConversationDetail) => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(conv, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `chat-${conv.id.slice(0, 8)}-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handlePrintPdf = () => {
    window.print();
  };

  const handlePromoteExemplar = async (msg: AdminMessageDetail, messages: AdminMessageDetail[]) => {
    const msgIdx = messages.findIndex((m) => m.id === msg.id);
    let question = "";
    for (let i = msgIdx - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        question = messages[i].content;
        break;
      }
    }

    if (!question) {
      alert("Could not identify the corresponding user question for this answer.");
      return;
    }

    setPromotingMessageId(msg.id);
    setActionNotice(null);
    try {
      await promoteExemplar(adminKey, {
        message_id: msg.id,
        question,
        answer: msg.content,
      });
      setActionNotice({
        text: `⭐ Exemplar Registered! Stored in ChromaDB verified_exemplars for dynamic few-shot learning.`,
        type: "success",
      });
    } catch (err: unknown) {
      setActionNotice({
        text: err instanceof Error ? err.message : "Failed to promote exemplar",
        type: "error",
      });
    } finally {
      setPromotingMessageId(null);
    }
  };

  /**
   * Always handles viewing a student's chat:
   * 1. If lead.conversation_id is present, opens directly.
   * 2. If missing, attempts matching existing conversations by phone or name.
   * 3. If not yet loaded, searches conversations via API by phone/name and selects the first match.
   */
  const handleViewLeadChat = async (lead: ProspectiveLeadItem) => {
    setActiveTab("chats");
    if (lead.conversation_id) {
      setSelectedConvId(lead.conversation_id);
      handleSelectConversation(lead.conversation_id);
      return;
    }

    const cleanPhone = lead.phone ? lead.phone.replace(/\D/g, "").slice(-10) : "";
    const matchedConv = conversations.find(
      (c) =>
        (cleanPhone && (c.title?.includes(cleanPhone) || c.last_message_preview?.includes(cleanPhone))) ||
        (lead.name && c.title?.toLowerCase().includes(lead.name.toLowerCase()))
    );

    if (matchedConv) {
      setSelectedConvId(matchedConv.id);
      handleSelectConversation(matchedConv.id);
      return;
    }

    // Fallback: search by phone or name
    const searchTerm = cleanPhone || lead.name;
    setChatSearch(searchTerm);
    setCurrentPage(1);

    try {
      const res = await fetchAdminConversations(adminKey, {
        page: 1,
        pageSize,
        search: searchTerm,
      });
      if (res.conversations.length > 0) {
        setConversations(res.conversations);
        setConversationsTotal(res.total);
        setSelectedConvId(res.conversations[0].id);
        handleSelectConversation(res.conversations[0].id);
      }
    } catch (e) {
      console.error("Auto search on lead click failed:", e);
    }
  };

  const totalPages = Math.max(1, Math.ceil(conversationsTotal / pageSize));

  // Authentication Box
  if (!adminKey) {
    return (
      <div className="admin-container">
        <header className="admin-header">
          <div className="admin-brand">
            <span className="admin-brand-icon">🏛️</span>
            <span className="admin-brand-name">SR University AI</span>
            <span className="admin-badge">Admin</span>
          </div>
          <button className="admin-btn-secondary" onClick={onBackToChat}>
            ← Student Portal
          </button>
        </header>

        <div className="admin-main-scroll admin-login-wrap">
          <div className="admin-auth-card">
            <div className="auth-card-icon">🔐</div>
            <h2>Admin Authentication</h2>
            <p>Enter the master admin key to access prospective admissions leads, student conversations, and knowledge management.</p>
            <form onSubmit={handleLogin}>
              <input
                type="password"
                className="admin-input"
                placeholder="Enter Admin API Key"
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                autoFocus
                required
              />
              {error && <div className="admin-auth-error">{error}</div>}
              <button type="submit" className="admin-btn-primary admin-btn-block">
                Access Dashboard
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      {/* Sleek Minimal Header */}
      <header className="admin-header">
        <div className="admin-brand">
          <span className="admin-brand-icon">🏛️</span>
          <span className="admin-brand-name">SRU Buddy</span>
          <span className="admin-badge">Admin Console</span>
          <span className="admin-status-indicator" title="System Online">
            <span className="status-dot"></span> Live
          </span>
        </div>

        <div className="admin-header-actions">
          <button className="admin-btn-secondary" onClick={onBackToChat}>
            💬 Student Chat
          </button>
          <button className="admin-btn-secondary" onClick={handleLogout}>
            Exit
          </button>
        </div>
      </header>

      {/* Segmented Minimal Navigation Tabs */}
      <nav className="admin-nav-bar">
        <div className="admin-tabs-list">
          <button
            className={`admin-tab-btn ${activeTab === "leads" ? "active" : ""}`}
            onClick={() => setActiveTab("leads")}
          >
            🎯 Prospective Leads
            <span className="tab-counter">{leadStats?.total_leads ?? leadsTotal}</span>
          </button>
          <button
            className={`admin-tab-btn ${activeTab === "chats" ? "active" : ""}`}
            onClick={() => setActiveTab("chats")}
          >
            💬 Student Chats
            <span className="tab-counter">{conversationsTotal || conversations.length}</span>
          </button>
          <button
            className={`admin-tab-btn ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            📊 Overview
          </button>
          <button
            className={`admin-tab-btn ${activeTab === "documents" ? "active" : ""}`}
            onClick={() => setActiveTab("documents")}
          >
            📚 Knowledge Base
            <span className="tab-counter">{documents.length}</span>
          </button>
          <button
            className={`admin-tab-btn ${activeTab === "feedback" ? "active" : ""}`}
            onClick={() => setActiveTab("feedback")}
          >
            ⭐ Feedback
            <span className="tab-counter">{feedback.length}</span>
          </button>
        </div>
      </nav>

      {/* Action Notification Toast */}
      {actionNotice && (
        <div className={`admin-toast toast-${actionNotice.type}`}>
          <span>{actionNotice.text}</span>
          <button className="toast-close-btn" onClick={() => setActionNotice(null)}>
            ✕
          </button>
        </div>
      )}

      {/* Main Scrollable Content */}
      <main className="admin-main-scroll">
        {isLoading ? (
          <div className="admin-loading-state">
            <div className="admin-spinner"></div>
            <p>Loading dashboard data...</p>
          </div>
        ) : (
          <>
            {/* =========================================================================
                TAB 1: PROSPECTIVE LEADS & ADMISSIONS CONVERSION
                ========================================================================= */}
            {activeTab === "leads" && (
              <div className="tab-pane-container">
                {/* Metric Quick Stats Ribbon */}
                <div className="admin-metrics-grid">
                  <div className="metric-box">
                    <span className="metric-title">Total Verified Leads</span>
                    <span className="metric-num num-indigo">{leadStats?.total_leads ?? leadsTotal}</span>
                    <span className="metric-caption">Authenticated prospects</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Chat Inquiries</span>
                    <span className="metric-num num-green">{leadStats?.chat_leads ?? 0}</span>
                    <span className="metric-caption">Admissions & fee questions</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Calculator Submissions</span>
                    <span className="metric-num num-amber">{leadStats?.calculator_leads ?? 0}</span>
                    <span className="metric-caption">Scholarship & merit inquiries</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Today's Leads</span>
                    <span className="metric-num num-pink">{leadStats?.today_leads ?? 0}</span>
                    <span className="metric-caption">Fresh high-intent inquiries</span>
                  </div>
                </div>

                {/* Search & Filter Toolbar */}
                <div className="admin-toolbar-card">
                  <div className="toolbar-filters">
                    <div className="admin-search-wrap">
                      <input
                        type="text"
                        className="admin-input-search"
                        placeholder="🔍 Search student name or mobile number..."
                        value={leadSearch}
                        onChange={(e) => {
                          setLeadSearch(e.target.value);
                          setLeadPage(1);
                        }}
                      />
                      {leadSearch && (
                        <button
                          className="search-clear-btn"
                          onClick={() => {
                            setLeadSearch("");
                            setLeadPage(1);
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </div>

                    <select
                      className="admin-select"
                      value={leadProgramFilter}
                      onChange={(e) => {
                        setLeadProgramFilter(e.target.value);
                        setLeadPage(1);
                      }}
                    >
                      <option value="all">All Programs</option>
                      <option value="B.Tech CSE">B.Tech CSE</option>
                      <option value="B.Tech ECE">B.Tech ECE</option>
                      <option value="B.Tech AI & Data Science">B.Tech AI & Data Science</option>
                      <option value="B.Tech Mechanical">B.Tech Mechanical</option>
                      <option value="B.Tech Civil">B.Tech Civil</option>
                      <option value="B.Tech EEE">B.Tech EEE</option>
                      <option value="BBA">BBA</option>
                      <option value="MBA">MBA</option>
                    </select>

                    <select
                      className="admin-select"
                      value={leadSourceFilter}
                      onChange={(e) => {
                        setLeadSourceFilter(e.target.value);
                        setLeadPage(1);
                      }}
                    >
                      <option value="all">All Sources</option>
                      <option value="chat_inquiry">💬 Chat Inquiry</option>
                      <option value="calculator">🧮 Calculator</option>
                    </select>

                    <select
                      className="admin-select"
                      value={leadStatusFilter}
                      onChange={(e) => {
                        setLeadStatusFilter(e.target.value);
                        setLeadPage(1);
                      }}
                    >
                      <option value="all">All Statuses</option>
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="counselled">Counselled</option>
                      <option value="applied">Applied</option>
                      <option value="enrolled">Enrolled</option>
                      <option value="lost">Lost</option>
                      <option value="do_not_contact">Do not contact</option>
                    </select>
                  </div>

                  <div className="toolbar-actions">
                    <button
                      className="admin-btn-secondary"
                      onClick={() =>
                        loadLeadsOnly(
                          adminKey,
                          leadPage,
                          leadPageSize,
                          leadSearch,
                          leadProgramFilter,
                          leadSourceFilter,
                          leadStatusFilter
                        )
                      }
                      title="Refresh Leads Table"
                    >
                      ↻ Refresh
                    </button>
                    <button
                      className="admin-btn-primary"
                      onClick={handleExportLeads}
                      disabled={isExportingLeads}
                    >
                      {isExportingLeads ? "Exporting..." : "📥 Export CSV"}
                    </button>
                  </div>
                </div>

                {/* Leads Data Table */}
                <div className="admin-table-card">
                  {leads.length === 0 ? (
                    <div className="admin-empty-state">
                      <div className="empty-icon">🎯</div>
                      <h3>No Prospective Leads Found</h3>
                      <p>
                        {leadSearch || leadProgramFilter !== "all" || leadStatusFilter !== "all" || leadSourceFilter !== "all"
                          ? "No leads matched your current filters. Try resetting the search or filter criteria."
                          : "Leads captured via Chat Fee Inquiries or Scholarship Calculator will appear here automatically."}
                      </p>
                    </div>
                  ) : (
                    <div className="admin-table-wrapper">
                      <table className="admin-clean-table">
                        <thead>
                          <tr>
                            <th className="col-name">Student Name</th>
                            <th className="col-phone">Mobile Number</th>
                            <th className="col-program">Program Interest</th>
                            <th className="col-score">Score / Qualifying Exam</th>
                            <th className="col-source">Lead Source</th>
                            <th className="col-date">Captured On</th>
                            <th className="col-status">Admission Status</th>
                            <th className="col-actions">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {leads.map((lead) => {
                            const formattedDate = new Date(lead.created_at).toLocaleString("en-IN", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            });

                            return (
                              <tr key={lead.id} className="lead-row">
                                <td className="col-name">
                                  <div className="student-name-text">{lead.name}</div>
                                  {lead.email && <div className="student-sub-email">{lead.email}</div>}
                                </td>
                                <td className="col-phone">
                                  <a href={`tel:${lead.phone}`} className="student-phone-link">
                                    📞 {lead.phone}
                                  </a>
                                </td>
                                <td className="col-program">
                                  <span className="program-badge">
                                    {formatProgramInterest(lead.program_interest, lead.metadata)}
                                  </span>
                                </td>
                                <td className="col-score">
                                  {lead.score || lead.exam_type ? (
                                    <div className="score-cell">
                                      {lead.score && <span className="score-val">{lead.score}</span>}
                                      {lead.exam_type && (
                                        <span className="exam-type-val">({lead.exam_type})</span>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="cell-muted">—</span>
                                  )}
                                </td>
                                <td className="col-source">
                                  <span className={`source-pill source-${lead.source}`}>
                                    {lead.source === "calculator" ? "🧮 Calculator" : "💬 Chat Inquiry"}
                                  </span>
                                </td>
                                <td className="col-date">{formattedDate}</td>
                                <td className="col-status">
                                  <select
                                    className={`status-select status-${lead.status}`}
                                    value={lead.status}
                                    disabled={updatingLeadId === lead.id}
                                    onChange={(e) => handleUpdateLeadStatus(lead.id, e.target.value)}
                                  >
                                    <option value="new">New</option>
                                    <option value="contacted">Contacted</option>
                                    <option value="counselled">Counselled</option>
                                    <option value="applied">Applied</option>
                                    <option value="enrolled">Enrolled</option>
                                    <option value="lost">Lost</option>
                                    <option value="do_not_contact">Do not contact</option>
                                  </select>
                                </td>
                                <td className="col-actions">
                                  <button
                                    className="admin-btn-action-view"
                                    title="Inspect student chat conversation"
                                    onClick={() => handleViewLeadChat(lead)}
                                  >
                                    View Chat ↗
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Pagination Footer */}
                  {leadsTotal > leadPageSize && (
                    <div className="admin-pagination-footer">
                      <span className="pagination-info">
                        Showing {Math.min((leadPage - 1) * leadPageSize + 1, leadsTotal)}–
                        {Math.min(leadPage * leadPageSize, leadsTotal)} of {leadsTotal} leads
                      </span>
                      <div className="pagination-ctrls">
                        <button
                          className="admin-btn-secondary"
                          disabled={leadPage <= 1}
                          onClick={() => setLeadPage((p) => Math.max(1, p - 1))}
                        >
                          ← Previous
                        </button>
                        <span className="pagination-page-label">
                          Page {leadPage} of {Math.ceil(leadsTotal / leadPageSize)}
                        </span>
                        <button
                          className="admin-btn-secondary"
                          disabled={leadPage >= Math.ceil(leadsTotal / leadPageSize)}
                          onClick={() => setLeadPage((p) => p + 1)}
                        >
                          Next →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* =========================================================================
                TAB 2: STUDENT CHATS AUDIT & MODEL IMPROVEMENT
                ========================================================================= */}
            {activeTab === "chats" && (
              <div className="tab-pane-container chats-pane">
                {/* Search & Export Toolbar */}
                <div className="admin-toolbar-card">
                  <div className="toolbar-filters">
                    <div className="admin-search-wrap">
                      <input
                        type="text"
                        className="admin-input-search"
                        placeholder="🔍 Search questions, answers, topics, mobile numbers, or session IDs..."
                        value={chatSearch}
                        onChange={(e) => {
                          setChatSearch(e.target.value);
                          setCurrentPage(1);
                        }}
                      />
                      {chatSearch && (
                        <button
                          className="search-clear-btn"
                          onClick={() => {
                            setChatSearch("");
                            setCurrentPage(1);
                          }}
                        >
                          ✕
                        </button>
                      )}
                    </div>

                    <div className="filter-chips-list">
                      <button
                        className={`filter-chip ${feedbackFilter === "all" ? "active" : ""}`}
                        onClick={() => {
                          setFeedbackFilter("all");
                          setCurrentPage(1);
                        }}
                      >
                        All Chats ({conversationsTotal})
                      </button>
                      <button
                        className={`filter-chip ${feedbackFilter === "positive" ? "active" : ""}`}
                        onClick={() => {
                          setFeedbackFilter("positive");
                          setCurrentPage(1);
                        }}
                      >
                        👍 Helpful
                      </button>
                      <button
                        className={`filter-chip ${feedbackFilter === "negative" ? "active" : ""}`}
                        onClick={() => {
                          setFeedbackFilter("negative");
                          setCurrentPage(1);
                        }}
                      >
                        👎 Inaccurate
                      </button>
                      <button
                        className={`filter-chip ${feedbackFilter === "none" ? "active" : ""}`}
                        onClick={() => {
                          setFeedbackFilter("none");
                          setCurrentPage(1);
                        }}
                      >
                        No Feedback
                      </button>
                    </div>
                  </div>

                  <div className="toolbar-actions">
                    <button
                      className="admin-btn-primary"
                      disabled={isExportingAll || conversationsTotal === 0}
                      onClick={handleExportAllMarkdown}
                      title="Download ALL conversations in Markdown (.md) to train or evaluate the AI model"
                    >
                      {isExportingAll ? "Generating Dataset..." : "📥 Export All Chats (.md for AI Training)"}
                    </button>
                  </div>
                </div>

                {/* Dual Pane Audit Workspace */}
                <div className="chat-audit-layout">
                  {/* Left Column: Conversation List */}
                  <div className="chat-audit-sidebar">
                    <div className="sidebar-head">
                      <span>Conversations ({conversations.length} of {conversationsTotal})</span>
                      <button
                        className="btn-link-action"
                        onClick={() =>
                          loadConversationsOnly(adminKey, currentPage, pageSize, chatSearch, feedbackFilter)
                        }
                        title="Refresh conversations list"
                      >
                        ↻ Refresh
                      </button>
                    </div>

                    {conversations.length === 0 ? (
                      <div className="sidebar-empty">
                        <div style={{ fontSize: "1.8rem", marginBottom: "8px" }}>🔍</div>
                        <p>No conversations found matching filters.</p>
                      </div>
                    ) : (
                      <div className="sidebar-scroll-list">
                        {conversations.map((c) => {
                          const isSelected = selectedConvId === c.id;
                          return (
                            <div
                              key={c.id}
                              className={`conv-list-item ${isSelected ? "selected" : ""}`}
                              onClick={() => handleSelectConversation(c.id)}
                            >
                              <div className="conv-item-top">
                                <span className="conv-item-title">{c.title || "Untitled Conversation"}</span>
                                <span className="conv-item-time">
                                  {new Date(c.updated_at).toLocaleDateString([], {
                                    month: "short",
                                    day: "numeric",
                                  })}
                                </span>
                              </div>

                              {c.last_message_preview && (
                                <p className="conv-item-preview">{plainPreview(c.last_message_preview)}</p>
                              )}

                              <div className="conv-item-footer">
                                <span className="conv-msg-tag">{c.message_count} msgs</span>
                                <div className="conv-feedback-tags">
                                  {c.positive_feedback_count > 0 && (
                                    <span className="fb-tag-pos">👍 {c.positive_feedback_count}</span>
                                  )}
                                  {c.negative_feedback_count > 0 && (
                                    <span className="fb-tag-neg">👎 {c.negative_feedback_count}</span>
                                  )}
                                </div>
                                <span className="conv-session-tag" title={c.session_id}>
                                  {c.session_id.slice(0, 8)}...
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Pagination Bar */}
                    <div className="sidebar-pagination">
                      <div className="page-nav-btns">
                        <button
                          className="admin-btn-secondary btn-icon"
                          disabled={currentPage <= 1}
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        >
                          ◀
                        </button>
                        <span className="page-number-text">
                          {currentPage} / {totalPages}
                        </span>
                        <button
                          className="admin-btn-secondary btn-icon"
                          disabled={currentPage >= totalPages}
                          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        >
                          ▶
                        </button>
                      </div>

                      <div className="page-size-selector">
                        <span>Show:</span>
                        <select
                          className="admin-select select-compact"
                          value={pageSize}
                          onChange={(e) => {
                            setPageSize(Number(e.target.value));
                            setCurrentPage(1);
                          }}
                        >
                          <option value={25}>25</option>
                          <option value={50}>50</option>
                          <option value={100}>100</option>
                          <option value={1000}>All</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Full Conversation Transcript */}
                  <div className="chat-audit-content">
                    {isLoadingDetail ? (
                      <div className="admin-loading-state">
                        <div className="admin-spinner"></div>
                        <p>Loading full conversation thread...</p>
                      </div>
                    ) : selectedConvDetail ? (
                      <div className="transcript-box">
                        {/* Header */}
                        <div className="transcript-top-header">
                          <div className="transcript-headline">
                            <h3>{selectedConvDetail.title}</h3>
                            <div className="transcript-meta-row">
                              <span>Session: <code>{selectedConvDetail.session_id}</code></span>
                              <span>•</span>
                              <span>Started: {new Date(selectedConvDetail.created_at).toLocaleString()}</span>
                              <span>•</span>
                              <span>{selectedConvDetail.messages.length} Messages</span>
                            </div>
                          </div>
                          <div className="transcript-toolbar-btns">
                            <button className="admin-btn-secondary" onClick={handlePrintPdf}>
                              📄 Print / PDF
                            </button>
                            <button
                              className="admin-btn-secondary"
                              onClick={() => handleExportSingleJson(selectedConvDetail)}
                            >
                              📥 JSON
                            </button>
                            <button
                              className="admin-btn-danger"
                              onClick={() => handleDeleteConversation(selectedConvDetail.id)}
                            >
                              🗑️ Delete
                            </button>
                          </div>
                        </div>

                        {/* Dialogue Thread */}
                        <div className="transcript-scroll-area" ref={detailScrollRef}>
                          {selectedConvDetail.messages.length === 0 ? (
                            <p className="transcript-empty-text">
                              No messages recorded in this conversation.
                            </p>
                          ) : (
                            selectedConvDetail.messages.map((m) => {
                              const isUser = m.role === "user";
                              return (
                                <div
                                  key={m.id}
                                  className={`transcript-message-bubble ${isUser ? "role-user" : "role-assistant"}`}
                                >
                                  <div className="msg-header-row">
                                    <span className="msg-role-badge">
                                      {isUser ? "👤 Student" : "🤖 SRU Buddy"}
                                    </span>
                                    {m.model && <span className="msg-model-tag">{m.model}</span>}
                                    <span className="msg-timestamp">
                                      {new Date(m.created_at).toLocaleTimeString([], {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                        second: "2-digit",
                                      })}
                                    </span>
                                  </div>

                                  <div className="msg-body-content">{m.content}</div>

                                  {/* Grounded Sources */}
                                  {m.sources && m.sources.length > 0 && (
                                    <div className="msg-sources-box">
                                      <div className="sources-headline">
                                        📚 Grounded Sources ({m.sources.length}):
                                      </div>
                                      <div className="sources-tags-list">
                                        {m.sources.map((src, i) => (
                                          <div key={i} className="source-citation-chip">
                                            <span>📄</span>
                                            <span className="src-title">{src.title}</span>
                                            {src.page && <span className="src-page">(Page {src.page})</span>}
                                            {src.department && (
                                              <span className="src-dept">[{src.department}]</span>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* User Feedback */}
                                  {m.feedback && (
                                    <div
                                      className={`msg-feedback-alert ${
                                        m.feedback.rating === 1 ? "fb-positive" : "fb-negative"
                                      }`}
                                    >
                                      <span>
                                        {m.feedback.rating === 1
                                          ? "👍 Student rated helpful"
                                          : "👎 Student rated inaccurate"}
                                      </span>
                                      {m.feedback.comment && (
                                        <span className="feedback-comment-quote">
                                          — "{m.feedback.comment}"
                                        </span>
                                      )}
                                    </div>
                                  )}

                                  {/* Model Improvement Action on Assistant Responses */}
                                  {!isUser && (
                                    <div className="msg-exemplar-action">
                                      <button
                                        className="btn-exemplar-promote"
                                        disabled={promotingMessageId === m.id}
                                        onClick={() => handlePromoteExemplar(m, selectedConvDetail.messages)}
                                        title="Store this verified Q&A in ChromaDB verified_exemplars to train the AI model"
                                      >
                                        {promotingMessageId === m.id
                                          ? "Registering..."
                                          : "⭐ Promote to Verified Exemplar (Train Model)"}
                                      </button>
                                    </div>
                                  )}
                                </div>
                              );
                            })
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="admin-empty-state transcript-placeholder">
                        <div className="empty-icon">💬</div>
                        <h3>Select a Conversation to Inspect</h3>
                        <p>
                          Click any conversation on the left to review student questions, AI responses, grounded citations, and feedback ratings.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* =========================================================================
                TAB 3: OVERVIEW STATS & AI TRAINING GUIDE
                ========================================================================= */}
            {activeTab === "overview" && stats && (
              <div className="tab-pane-container">
                <div className="admin-metrics-grid">
                  <div className="metric-box">
                    <span className="metric-title">Total Student Conversations</span>
                    <span className="metric-num num-indigo">{stats.total_conversations}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Total Messages Exchanged</span>
                    <span className="metric-num">{stats.total_messages}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Active Knowledge Documents</span>
                    <span className="metric-num">{stats.active_documents}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Total Knowledge Base Docs</span>
                    <span className="metric-num">{stats.total_documents}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Positive Feedback 👍</span>
                    <span className="metric-num num-green">{stats.positive_feedback}</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-title">Negative Feedback 👎</span>
                    <span className="metric-num num-red">{stats.negative_feedback}</span>
                  </div>
                </div>

                <div className="admin-card-panel">
                  <h3 className="panel-headline">Model Improvement & AI Training Guide</h3>
                  <p className="panel-subtext">
                    Follow these steps to continuously align and fine-tune your SRU Companion:
                  </p>
                  <ol className="guide-steps-list">
                    <li>
                      <strong>Audit Real Student Queries:</strong> Go to the <strong>Student Chats</strong> tab to review the exact queries students are asking and identify knowledge gaps.
                    </li>
                    <li>
                      <strong>One-Click Few-Shot Learning:</strong> Click <strong>"⭐ Promote to Verified Exemplar"</strong> on any verified high-quality response to immediately embed it in ChromaDB's <code>verified_exemplars</code> collection.
                    </li>
                    <li>
                      <strong>Bulk Export for Fine-Tuning:</strong> Click <strong>"📥 Export All Chats (.md)"</strong> to export all student interactions into a single clean training document ready for evaluation benchmarks or fine-tuning models like Gemini, Llama, or Mistral.
                    </li>
                  </ol>
                </div>
              </div>
            )}

            {/* =========================================================================
                TAB 4: KNOWLEDGE BASE DOCUMENTS
                ========================================================================= */}
            {activeTab === "documents" && (
              <div className="tab-pane-container">
                <div className="admin-card-panel">
                  <h3 className="panel-headline">Upload & Ingest Document</h3>
                  {uploadSuccess && (
                    <div className="admin-toast toast-success" style={{ marginBottom: "16px" }}>
                      <span>{uploadSuccess}</span>
                    </div>
                  )}
                  <form onSubmit={handleUpload}>
                    <div className="form-responsive-grid">
                      <div className="form-field-group">
                        <label>Document Title *</label>
                        <input
                          type="text"
                          className="admin-input"
                          placeholder="e.g. Examination Regulations 2026"
                          value={uploadTitle}
                          onChange={(e) => setUploadTitle(e.target.value)}
                          required
                        />
                      </div>
                      <div className="form-field-group">
                        <label>Document Type *</label>
                        <select
                          className="admin-select"
                          value={uploadType}
                          onChange={(e) => setUploadType(e.target.value)}
                        >
                          <option value="policy">Policy</option>
                          <option value="calendar">Academic Calendar</option>
                          <option value="regulation">Regulations / Rules</option>
                          <option value="syllabus">Syllabus / Course</option>
                          <option value="circular">Notice / Circular</option>
                        </select>
                      </div>
                      <div className="form-field-group">
                        <label>Department</label>
                        <input
                          type="text"
                          className="admin-input"
                          placeholder="e.g. Office of Academic Affairs"
                          value={uploadDept}
                          onChange={(e) => setUploadDept(e.target.value)}
                        />
                      </div>
                      <div className="form-field-group">
                        <label>File (PDF, DOCX, TXT, MD) *</label>
                        <input
                          type="file"
                          className="admin-input-file"
                          accept=".pdf,.docx,.txt,.md"
                          onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                          required
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      className="admin-btn-primary"
                      disabled={isUploading}
                      style={{ marginTop: "16px" }}
                    >
                      {isUploading ? "Extracting & Embedding..." : "Ingest Document"}
                    </button>
                  </form>
                </div>

                <div className="admin-table-card">
                  <h3 className="card-headline">Knowledge Base Documents</h3>
                  {documents.length === 0 ? (
                    <div className="admin-empty-state">
                      <p>No documents indexed yet.</p>
                    </div>
                  ) : (
                    <div className="admin-table-wrapper">
                      <table className="admin-clean-table">
                        <thead>
                          <tr>
                            <th>Title</th>
                            <th>Type</th>
                            <th>Department</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documents.map((doc) => (
                            <tr key={doc.id}>
                              <td style={{ fontWeight: 600 }}>{doc.title}</td>
                              <td>{doc.document_type}</td>
                              <td>{doc.department || "—"}</td>
                              <td>
                                <span className={`status-pill pill-${doc.status}`}>
                                  {doc.status}
                                </span>
                              </td>
                              <td className="cell-date">{new Date(doc.created_at).toLocaleDateString()}</td>
                              <td>
                                {doc.status === "active" && (
                                  <button
                                    className="admin-btn-danger"
                                    onClick={() => handleDeactivate(doc.id)}
                                  >
                                    Deactivate
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* =========================================================================
                TAB 5: STUDENT FEEDBACK
                ========================================================================= */}
            {activeTab === "feedback" && (
              <div className="tab-pane-container">
                <div className="admin-table-card">
                  <h3 className="card-headline">Student & User Feedback</h3>
                  {feedback.length === 0 ? (
                    <div className="admin-empty-state">
                      <p>No feedback submitted yet.</p>
                    </div>
                  ) : (
                    <div className="admin-table-wrapper">
                      <table className="admin-clean-table">
                        <thead>
                          <tr>
                            <th>Rating</th>
                            <th>User Question</th>
                            <th>AI Response</th>
                            <th>Comment</th>
                            <th>Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {feedback.map((f) => (
                            <tr key={f.id}>
                              <td>
                                {f.rating === 1 ? (
                                  <span className="rating-tag rating-pos">👍 Helpful</span>
                                ) : (
                                  <span className="rating-tag rating-neg">👎 Inaccurate</span>
                                )}
                              </td>
                              <td style={{ maxWidth: "260px", wordBreak: "break-word" }}>
                                {f.question || <span className="cell-muted">—</span>}
                              </td>
                              <td style={{ maxWidth: "340px", wordBreak: "break-word", fontSize: "0.85rem" }}>
                                {f.answer ? (
                                  <span>{f.answer.length > 160 ? `${f.answer.slice(0, 160)}...` : f.answer}</span>
                                ) : (
                                  <span className="cell-muted">—</span>
                                )}
                              </td>
                              <td>{f.comment || <span className="cell-muted">—</span>}</td>
                              <td className="cell-date">{new Date(f.created_at).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
