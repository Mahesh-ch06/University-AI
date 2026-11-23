import React, { lazy, Suspense, useState, useEffect, useRef } from "react";
import MessageBubble from "../components/MessageBubble";
import ChatLeadForm from "../components/ChatLeadForm";
import { CalculatorIcon } from "../components/Icons";
import { getSessionId } from "../hooks/useSession";
import { applyServerProfile, cleanPhone, forgetStudentDetails, readStudentDetails, syncStudentDetails } from "../utils/studentProfile";
import { deduplicateCards } from "../components/Cards";
import RecoveryCard from "../components/RecoveryCard";
import {
  sendMessageStream,
  fetchRecoveryContext,
  resetSessionConversation,
  getConversation,
  type ConversationRecoveryContext,
  type MessageData,
  type ChatResponse,
} from "../services/api";
import { playChime, triggerConfetti, isEligibleResponse } from "../utils/effects";
import { APP_VERSION } from "../version";
import "./ChatPage.css";

const ScholarshipCalculatorModal = lazy(() => import("../components/ScholarshipCalculatorModal"));
const LeadAuthModal = lazy(() => import("../components/LeadAuthModal"));
const SettingsModal = lazy(() => import("../components/SettingsModal"));

interface Props {
  onOpenAdmin?: () => void;
  variant?: "full" | "widget";
}

/** Tell the page that embeds the widget to close it (public/widget.js listens for this). */
function closeWidget() {
  try {
    window.parent?.postMessage({ type: "sru-buddy:close" }, "*");
  } catch {
    /* not embedded */
  }
}

const LOCKED_WELCOME_CONTENT =
  "Welcome to SR University! 👋\n" +
  "I’m SRU Buddy, your AI companion at a Next-Gen Living and Learning Campus.\n\n" +
  "🏆 Top Private University in Telangana & AP\n\n" +
  "Which program are you interested in? I’ll guide you on eligibility, fees, scholarships and campus life.\n\n" +
  "🌐 Ask in English, हिंदी, తెలుగు or any language.";

const LOCKED_WELCOME_SUGGESTIONS = [
  "B.Tech programmes offered",
  "Calculate my scholarship",
  "Hostel fees & facilities",
  "How to apply for 2027-28",
];

const WELCOME_VARIANTS: Array<{ content: string; suggestions: string[] }> = [
  {
    content: LOCKED_WELCOME_CONTENT,
    suggestions: LOCKED_WELCOME_SUGGESTIONS,
  },
];

export function getInitialWelcomeMessage(_seed: string = ""): MessageData {
  const v = WELCOME_VARIANTS[0];
  return {
    id: "welcome-sru-buddy",
    role: "assistant",
    content: v.content,
    created_at: new Date().toISOString(),
    suggestions: v.suggestions,
  };
}

export const DEFAULT_WELCOME_MESSAGE: MessageData = getInitialWelcomeMessage();

const MESSAGE_RENDER_WINDOW = 60;
const INACTIVITY_THRESHOLD_MS = 30 * 60 * 1000; // 30-minute inactivity threshold for conversation recovery

export default function ChatPage({ onOpenAdmin, variant = "full" }: Props) {
  const isWidget = variant === "widget";
  const sessionId = getSessionId();

  // Widget visibility state: closed by default so floating bubble is visible, clicks open it
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  // Queries
  const [dockQuery, setDockQuery] = useState("");
  const [widgetInput, setWidgetInput] = useState("");
  const widgetTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const portalTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  const adjustTextareaHeight = (el: HTMLTextAreaElement | null) => {
    if (!el) return;
    el.style.height = "34px";
    const scrollH = el.scrollHeight;
    const targetHeight = Math.min(Math.max(scrollH, 34), 136);
    el.style.height = `${targetHeight}px`;
  };

  useEffect(() => {
    adjustTextareaHeight(widgetTextareaRef.current);
    adjustTextareaHeight(portalTextareaRef.current);
  }, [widgetInput]);

  // Chat message state
  const hasValidContactDetails = (): boolean => {
    const details = readStudentDetails();
    return Boolean(details?.name?.trim() && cleanPhone(details?.phone || ""));
  };

  const [messages, setMessages] = useState<MessageData[]>(() => [getInitialWelcomeMessage(sessionId)]);
  const [showInlineLeadForm, setShowInlineLeadForm] = useState<boolean>(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const pendingQuestionRef = useRef<string | null>(null);
  const [visibleMessageCount, setVisibleMessageCount] = useState(MESSAGE_RENDER_WINDOW);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const activeConvIdRef = useRef<string | null>(activeConvId);

  useEffect(() => {
    activeConvIdRef.current = activeConvId;
    if (activeConvId) {
      sessionStorage.setItem("sru_active_conv_id", activeConvId);
    }
  }, [activeConvId]);

  const handleLeadFormComplete = () => {
    setShowInlineLeadForm(false);
    setError(null);
    const q = pendingQuestionRef.current || pendingQuestion;
    // Clear immediately so that it can never be submitted more than once
    pendingQuestionRef.current = null;
    setPendingQuestion(null);
    if (q) {
      executeSendMessage(q, true);
    }
  };

  const [isLoading, setIsLoading] = useState(false);
  const [activeToolStatus, setActiveToolStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamingMsgId, setStreamingMsgId] = useState<string | null>(null);

  // Modals
  const [isCalculatorOpen, setIsCalculatorOpen] = useState(false);
  const [showLeadAuthModal, setShowLeadAuthModal] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [pendingAuthMessage, setPendingAuthMessage] = useState<string | null>(null);

  // Voice recognition
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const messagesAreaRef = useRef<HTMLDivElement>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  // Smart Conversation Recovery state
  const [recoveryContext, setRecoveryContext] = useState<ConversationRecoveryContext | null>(null);
  const [showRecoveryCard, setShowRecoveryCard] = useState<boolean>(false);
  const [isRestoringConv, setIsRestoringConv] = useState<boolean>(false);
  const [pendingRecoveryQuery, setPendingRecoveryQuery] = useState<string | null>(null);
  const pendingRecoveryQueryRef = useRef<string | null>(null);

  const isLoadingRef = useRef(isLoading);
  const dockQueryRef = useRef(dockQuery);
  const widgetInputRef = useRef(widgetInput);

  useEffect(() => { isLoadingRef.current = isLoading; }, [isLoading]);
  useEffect(() => { dockQueryRef.current = dockQuery; }, [dockQuery]);
  useEffect(() => { widgetInputRef.current = widgetInput; }, [widgetInput]);

  const recordUserActivity = () => {
    try {
      localStorage.setItem("sru_last_active_time", Date.now().toString());
    } catch {}
  };

  // Condition A: Immediate check on page reload / fresh session mount
  useEffect(() => {
    recordUserActivity();
    let isMounted = true;
    fetchRecoveryContext(sessionId)
      .then((ctx) => {
        if (isMounted && ctx && ctx.has_resumable_conversation) {
          setRecoveryContext(ctx);
          setShowRecoveryCard(true);
          setIsWidgetOpen(true);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  // Condition B: 30-minute inactivity threshold check
  useEffect(() => {
    const checkInactivity = () => {
      if (document.visibilityState !== "visible") return;
      if (isLoadingRef.current || widgetInputRef.current || dockQueryRef.current) return;
      const lastActiveStr = localStorage.getItem("sru_last_active_time");
      const lastActive = lastActiveStr ? parseInt(lastActiveStr, 10) : 0;
      if (lastActive > 0 && Date.now() - lastActive >= INACTIVITY_THRESHOLD_MS) {
        fetchRecoveryContext(sessionId)
          .then((ctx) => {
            if (ctx && ctx.has_resumable_conversation) {
              setRecoveryContext(ctx);
              setShowRecoveryCard(true);
              setIsWidgetOpen(true);
            }
          })
          .catch(() => {});
      }
    };

    document.addEventListener("visibilitychange", checkInactivity);
    window.addEventListener("focus", checkInactivity);
    return () => {
      document.removeEventListener("visibilitychange", checkInactivity);
      window.removeEventListener("focus", checkInactivity);
    };
  }, [sessionId]);

  const handleContinueConversation = async () => {
    if (!recoveryContext?.conversation_id) {
      setShowRecoveryCard(false);
      setRecoveryContext(null);
      return;
    }
    setIsRestoringConv(true);
    try {
      const conv = await getConversation(recoveryContext.conversation_id, sessionId);
      if (conv && conv.messages && conv.messages.length > 0) {
        setMessages(conv.messages);
        setActiveConvId(recoveryContext.conversation_id);
        activeConvIdRef.current = recoveryContext.conversation_id;
        setShowRecoveryCard(false);
        setRecoveryContext(null);
        recordUserActivity();

        const pending = pendingRecoveryQueryRef.current || pendingRecoveryQuery;
        pendingRecoveryQueryRef.current = null;
        setPendingRecoveryQuery(null);

        if (pending) {
          setTimeout(() => {
            executeSendMessage(pending, false);
          }, 150);
        } else {
          requestAnimationFrame(() => {
            if (messagesAreaRef.current) {
              messagesAreaRef.current.scrollTo({
                top: messagesAreaRef.current.scrollHeight,
                behavior: "smooth",
              });
            }
          });
        }
      } else {
        setShowRecoveryCard(false);
        setRecoveryContext(null);
      }
    } catch {
      setShowRecoveryCard(false);
      setRecoveryContext(null);
    } finally {
      setIsRestoringConv(false);
    }
  };

  const handleStartNewConversation = async () => {
    setShowRecoveryCard(false);
    const prevContext = recoveryContext;
    const prevConvId = activeConvId || prevContext?.conversation_id;
    setRecoveryContext(null);

    // Forget verified student identity so fresh start requires name & phone intake
    try {
      await forgetStudentDetails(sessionId);
    } catch {}
    try {
      localStorage.removeItem("sru_student_lead");
    } catch {}

    handleResetChat();
    recordUserActivity();
    await resetSessionConversation(sessionId, prevConvId);

    const pending = pendingRecoveryQueryRef.current || pendingRecoveryQuery;
    pendingRecoveryQueryRef.current = null;
    setPendingRecoveryQuery(null);

    if (pending) {
      const userMsgId = crypto.randomUUID();
      const userMsg: MessageData = {
        id: userMsgId,
        role: "user",
        content: pending,
        created_at: new Date().toISOString(),
      };
      setMessages([getInitialWelcomeMessage(`${sessionId}-fresh`), userMsg]);
      setPendingQuestion(pending);
      pendingQuestionRef.current = pending;
      setShowInlineLeadForm(true);
    }
  };

  // Real-time connection status: setting_up -> connected -> thinking
  const [connStatus, setConnStatus] = useState<"setting_up" | "connected">("setting_up");

  // Auto-sync profile on mount and set connection status
  useEffect(() => {
    let isMounted = true;
    syncStudentDetails(sessionId)
      .then(() => {
        if (isMounted) setConnStatus("connected");
      })
      .catch(() => {
        if (isMounted) setConnStatus("connected");
      });
    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  // Listen for messages from parent window (e.g. public/widget.js register button)
  useEffect(() => {
    const handleWidgetMessage = (e: MessageEvent) => {
      if (e.data?.type === "sru-buddy:register") {
        setShowLeadAuthModal(true);
      }
    };
    window.addEventListener("message", handleWidgetMessage);
    return () => window.removeEventListener("message", handleWidgetMessage);
  }, []);

  // Dynamically bind to visualViewport for mobile virtual keyboards to prevent blank screen & panning
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const handleViewportChange = () => {
      const height = Math.round(vv.height);
      document.documentElement.style.setProperty("--visual-viewport-height", `${height}px`);
      // Keep document at 0, 0 so mobile browser doesn't scroll the fixed page upwards
      if (window.scrollY > 0) {
        window.scrollTo(0, 0);
      }
    };

    handleViewportChange();
    vv.addEventListener("resize", handleViewportChange);
    vv.addEventListener("scroll", handleViewportChange);
    return () => {
      vv.removeEventListener("resize", handleViewportChange);
      vv.removeEventListener("scroll", handleViewportChange);
    };
  }, []);

  const currentStatus = isLoading
    ? { text: activeToolStatus || "Thinking...", type: "thinking" }
    : connStatus === "setting_up"
      ? { text: "Setting up...", type: "setting_up" }
      : error
        ? { text: "Setting up...", type: "setting_up" }
        : { text: "Connected", type: "connected" };
  const visibleMessages = messages.length > visibleMessageCount
    ? messages.slice(-visibleMessageCount)
    : messages;

  const lastSentUserMsgIdRef = useRef<string | null>(null);

  // Position newly sent user message at comfortable top reading view without jumping to bottom
  useEffect(() => {
    if (!messagesAreaRef.current) return;
    const container = messagesAreaRef.current;

    if (lastSentUserMsgIdRef.current) {
      const msgId = lastSentUserMsgIdRef.current;
      requestAnimationFrame(() => {
        const userMsgEl = document.getElementById(`sru-msg-${msgId}`);
        if (userMsgEl && container) {
          const topOffset = userMsgEl.offsetTop - container.offsetTop - 12;
          container.scrollTo({ top: Math.max(0, topOffset), behavior: "smooth" });
          lastSentUserMsgIdRef.current = null;
        }
      });
    }
  }, [messages, showInlineLeadForm]);

  // Voice typing toggle
  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const w = window as any;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice typing is not supported by your browser. Please try Chrome or Edge.");
      return;
    }

    try {
      const rec = new SpeechRecognition();
      rec.lang = "en-IN";
      rec.interimResults = true;
      rec.continuous = false;

      rec.onresult = (e: any) => {
        const transcript = Array.from(e.results)
          .map((r: any) => r[0]?.transcript || "")
          .join("");
        setWidgetInput(transcript);
      };

      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);

      rec.start();
      recognitionRef.current = rec;
      setListening(true);
    } catch {
      setListening(false);
    }
  };

  async function handleSendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    recordUserActivity();

    // 1. Direct triggers for recovery choices (from chips, buttons, or typed commands)
    if (/^\s*(?:[▶\s]*(?:continue|resume|pick\s*up)(?:\s+(?:previous|prior|my))?\s*(?:conversation|chat)?)\s*$/i.test(trimmed)) {
      if (showRecoveryCard || recoveryContext) {
        handleContinueConversation();
        return;
      }
    }
    if (/^\s*(?:[↺\s]*(?:start\s*fresh|new\s*(?:chat|conversation)|restart(?:\s*fresh)?|refresh(?:\s*chat)?))\s*$/i.test(trimmed)) {
      if (showRecoveryCard || recoveryContext) {
        handleStartNewConversation();
        return;
      }
    }

    // 2. Strict Recovery Guard:
    // If recovery card is active, do NOT dismiss it!
    // Intercept the query, keep the card visible, and prompt the student to choose.
    if (showRecoveryCard && recoveryContext) {
      setPendingRecoveryQuery(trimmed);
      pendingRecoveryQueryRef.current = trimmed;

      const userMsgId = crypto.randomUUID();
      const promptMsgId = crypto.randomUUID();

      const userMsg: MessageData = {
        id: userMsgId,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      const promptMsg: MessageData = {
        id: promptMsgId,
        role: "assistant",
        content: `Welcome back! To best assist you with **"${trimmed}"**, please let me know:\n\nWould you like to **continue your previous conversation** or **start a fresh session**?`,
        suggestions: ["▶ Continue Previous Chat", "↺ Start Fresh"],
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, promptMsg]);
      return;
    }

    // Check for explicit modal calculator trigger
    if (/^\s*(?:🧮\s*calculator|open\s+(?:the\s+)?(?:fee\s+|scholarship\s+)?calculator)\s*$/i.test(trimmed)) {
      setIsCalculatorOpen(true);
      return;
    }

    if (!hasValidContactDetails()) {
      const userMsgId = crypto.randomUUID();
      const tempUserMsg: MessageData = {
        id: userMsgId,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };
      lastSentUserMsgIdRef.current = userMsgId;
      setMessages((prev) => [...prev, tempUserMsg]);
      setPendingQuestion(trimmed);
      pendingQuestionRef.current = trimmed;
      setShowInlineLeadForm(true);
      setError(null);
      return;
    }

    await executeSendMessage(trimmed, false);
  }

  async function executeSendMessage(text: string, skipAppendUserMsg = false) {
    if (isLoading && cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }

    setIsLoading(true);
    setError(null);

    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();
    setStreamingMsgId(assistantMsgId);

    if (!skipAppendUserMsg) {
      const tempUserMsg: MessageData = {
        id: userMsgId,
        role: "user",
        content: text,
        created_at: new Date().toISOString(),
      };
      lastSentUserMsgIdRef.current = userMsgId;
      setMessages((prev) => [...prev, tempUserMsg]);
    }

    let assistantAppended = false;
    let accumulatedContent = "";
    const accumulatedCards: any[] = [];
    let renderFrame: number | null = null;

    const cancelScheduledRender = () => {
      if (renderFrame !== null) {
        window.cancelAnimationFrame(renderFrame);
        renderFrame = null;
      }
    };

    const flushAssistantRender = () => {
      renderFrame = null;
      if (!assistantAppended) {
        assistantAppended = true;
        setMessages((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            role: "assistant",
            content: accumulatedContent,
            cards: accumulatedCards.length ? [...accumulatedCards] : undefined,
            created_at: new Date().toISOString(),
          },
        ]);
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsgId
              ? {
                ...m,
                content: accumulatedContent,
                cards: accumulatedCards.length ? [...accumulatedCards] : undefined,
              }
              : m
          )
        );
      }
    };

    const scheduleAssistantRender = () => {
      if (renderFrame === null) {
        renderFrame = window.requestAnimationFrame(flushAssistantRender);
      }
    };

    const convIdToSend = activeConvIdRef.current || activeConvId;
    const cancelFn = sendMessageStream(sessionId, text, convIdToSend, {
      onStart: (convId) => {
        if (convId) {
          setActiveConvId(convId);
          activeConvIdRef.current = convId;
        }
      },
      onTool: (tool) => {
        if (tool.status === "running") {
          setActiveToolStatus(tool.label || "Working...");
        } else {
          setActiveToolStatus(null);
        }
      },
      onCard: (card) => {
        const isVideo = card?.type === "get_university_videos" || card?.type === "video_recommendations";
        const alreadyHasVideo = accumulatedCards.some(
          (c) => c?.type === "get_university_videos" || c?.type === "video_recommendations"
        );
        if (isVideo && alreadyHasVideo) return;
        accumulatedCards.push(card);
        scheduleAssistantRender();
      },
      onToken: (delta) => {
        setActiveToolStatus(null);
        accumulatedContent += delta;
        scheduleAssistantRender();
      },
      onDone: (data: ChatResponse) => {
        cancelScheduledRender();
        setIsLoading(false);
        setActiveToolStatus(null);
        setStreamingMsgId(null);
        cancelStreamRef.current = null;

        if (data.conversation_id) {
          setActiveConvId(data.conversation_id);
          activeConvIdRef.current = data.conversation_id;
        }
        applyServerProfile(data.profile);
        playChime();

        if (isEligibleResponse(data)) {
          triggerConfetti();
        }

        const rawCards = data.cards?.length ? data.cards : accumulatedCards;
        const finalCards = deduplicateCards(rawCards);

        if (!assistantAppended) {
          assistantAppended = true;
          setMessages((prev) => [
            ...prev,
            {
              id: data.message_id || assistantMsgId,
              role: "assistant",
              content: data.answer || accumulatedContent,
              sources: data.sources?.length ? data.sources : undefined,
              suggestions: data.suggestions?.length ? data.suggestions : undefined,
              cards: finalCards.length ? finalCards : undefined,
              flow: data.flow,
              model: data.model,
              created_at: new Date().toISOString(),
            },
          ]);
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? {
                  ...m,
                  id: data.message_id || m.id,
                  content: data.answer || accumulatedContent,
                  sources: data.sources?.length ? data.sources : undefined,
                  suggestions: data.suggestions?.length ? data.suggestions : undefined,
                  cards: finalCards.length ? finalCards : undefined,
                  flow: data.flow,
                  model: data.model,
                }
                : m
            )
          );
        }
      },
      onError: (err) => {
        cancelScheduledRender();
        setIsLoading(false);
        setActiveToolStatus(null);
        setStreamingMsgId(null);
        cancelStreamRef.current = null;
        setError(err.message || "Failed to get response.");
        setMessages((prev) =>
          prev.filter((m) => m.id !== assistantMsgId || accumulatedContent.length > 0)
        );
      },
    });

    cancelStreamRef.current = cancelFn;
  }

  function handleResetChat() {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setIsLoading(false);
    setStreamingMsgId(null);
    setActiveConvId(null);
    activeConvIdRef.current = null;
    setMessages([getInitialWelcomeMessage(sessionId + Date.now().toString())]);
    setVisibleMessageCount(MESSAGE_RENDER_WINDOW);
    setError(null);
    setShowInlineLeadForm(false);
    setPendingQuestion(null);
  }

  // Handle bottom floating dock input submit
  const handleDockSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = dockQuery.trim();
    if (!query) return;
    setIsWidgetOpen(true);
    setIsMinimized(false);
    handleSendMessage(query);
    setDockQuery("");
  };

  // Handle widget input submit
  const handleWidgetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const input = widgetInput.trim();
    if (!input || isLoading || showInlineLeadForm) return;
    handleSendMessage(input);
    setWidgetInput("");
  };

  // Render Widget View directly if variant === "widget" (used inside public/widget.js iframe)
  if (isWidget) {
    return (
      <div className="sru-portal-root sru-portal--widget sru-widget-iframe-root">
        <div className="sru-widget-container sru-widget-iframe-container">
          {/* Header */}
          <div className="sru-widget-header">
            <div className="sru-widget-header-left">
              <div className="sru-widget-avatar-wrap">
                <img src="/sru-logo.png" alt="SRU" className="sru-widget-avatar-img" />
              </div>
              <div className="sru-widget-title-col">
                <div className="sru-widget-title-row">
                  <span className="sru-widget-title">SRU Buddy</span>
                  <span className="sru-version-pill" title={`SR University AI Companion v${APP_VERSION}`}>v{APP_VERSION}</span>
                </div>
                <span className="sru-widget-status">
                  <span className={`sru-widget-status-dot ${currentStatus.type}`} />
                  {currentStatus.text}
                </span>
              </div>
            </div>

            <div className="sru-widget-header-actions">
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setShowSettings(true)}
                title="Student Profile & Settings"
                aria-label="Student Profile & Settings"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setIsCalculatorOpen(true)}
                title="Fee Calculator"
                aria-label="Fee Calculator"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="4" y="2" width="16" height="20" rx="2" />
                  <line x1="8" y1="6" x2="16" y2="6" />
                  <line x1="16" y1="14" x2="16" y2="18" />
                  <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={handleResetChat}
                title="Reset / New Chat"
                aria-label="Reset Chat"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                  <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                  <path d="M8 16H3v5" />
                </svg>
              </button>
              <a
                className="sru-widget-hdr-btn"
                href="/"
                target="_blank"
                rel="noopener noreferrer"
                title="Open full screen"
                aria-label="Open full screen"
                style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", textDecoration: "none", color: "white" }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              </a>
              <button
                className="sru-widget-hdr-btn"
                onClick={closeWidget}
                title="Close"
                aria-label="Close"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="sru-widget-body" ref={messagesAreaRef}>
            {showRecoveryCard && recoveryContext && (
              <RecoveryCard
                context={recoveryContext}
                onContinue={handleContinueConversation}
                onStartFresh={handleStartNewConversation}
                isContinuing={isRestoringConv}
              />
            )}
            {messages.length > visibleMessages.length && (
              <button
                type="button"
                onClick={() => setVisibleMessageCount((count) => Math.min(messages.length, count + MESSAGE_RENDER_WINDOW))}
                style={{ alignSelf: "center", margin: "8px auto", color: "#0055a4", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "999px", padding: "5px 12px", cursor: "pointer", fontSize: "0.75rem", fontWeight: 600 }}
              >
                Load older messages
              </button>
            )}
            {visibleMessages
              .filter((msg) => !(showRecoveryCard && msg.id.startsWith("welcome-sru-buddy")))
              .map((msg, index) => (
              <div
                key={msg.id || index}
                id={msg.id ? `sru-msg-${msg.id}` : undefined}
                style={{ width: "100%" }}
              >
                <MessageBubble
                  role={msg.role}
                  content={msg.content}
                  cards={msg.cards}
                  suggestions={msg.suggestions}
                  flow={msg.flow}
                  messageId={msg.id}
                  conversationId={activeConvId}
                  sessionId={sessionId}
                  isStreaming={msg.id === streamingMsgId}
                  onSuggestionClick={(prompt) => handleSendMessage(prompt)}
                />
              </div>
            ))}

            {showInlineLeadForm && (
              <ChatLeadForm onComplete={handleLeadFormComplete} pendingQuestion={pendingQuestion} />
            )}

            {isLoading && !messages.some((m) => m.id === streamingMsgId && ((m.content && m.content.trim().length > 0) || (m.cards && m.cards.length > 0))) && (
              <div className="message-bubble-row assistant sru-thinking-bubble-row">
                <div className="message-avatar-col">
                  <div className="assistant-avatar-badge" title="SRU Buddy">
                    <img src="/sru-logo.png" alt="SRU" className="assistant-avatar-img" />
                  </div>
                </div>
                <div className="message-content-col">
                  <div className="message-text-bubble assistant sru-typing-bubble">
                    <div className="sru-typing-dots" aria-hidden="true">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span className="sru-typing-tool-label">{activeToolStatus || "Thinking..."}</span>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div style={{ color: "#b91c1c", fontSize: "0.82rem", padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px" }}>
                {error}
              </div>
            )}

          </div>

          {/* Footer / Input Bar */}
          <div className="sru-widget-footer">
            {showRecoveryCard && recoveryContext && (
              <div className="sru-recovery-dock" role="region" aria-label="Conversation recovery choices">
                <div className="sru-recovery-dock-header">
                  <span className="sru-recovery-dock-badge">✨ Session Saved</span>
                  <span className="sru-recovery-dock-text">Please choose to proceed:</span>
                </div>
                <div className="sru-recovery-dock-actions">
                  <button
                    type="button"
                    className="sru-recovery-dock-btn sru-recovery-dock-btn--continue"
                    onClick={handleContinueConversation}
                    disabled={isRestoringConv}
                    aria-label="Continue previous conversation"
                  >
                    {isRestoringConv ? (
                      <span>Restoring...</span>
                    ) : (
                      <>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                          <polygon points="6 4 20 12 6 20 6 4" />
                        </svg>
                        <span>Continue Chat</span>
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    className="sru-recovery-dock-btn sru-recovery-dock-btn--fresh"
                    onClick={handleStartNewConversation}
                    disabled={isRestoringConv}
                    aria-label="Start fresh conversation"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                      <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                    </svg>
                    <span>Start Fresh</span>
                  </button>
                </div>
              </div>
            )}
            <form className="sru-widget-input-row" onSubmit={handleWidgetSubmit}>
              <textarea
                ref={widgetTextareaRef}
                className="sru-widget-textarea"
                placeholder={
                  showRecoveryCard
                    ? "Choose Continue or Start Fresh above..."
                    : showInlineLeadForm
                    ? "Please share your name & mobile number above to chat"
                    : "Ask SRU Buddy..."
                }
                rows={1}
                value={widgetInput}
                disabled={showInlineLeadForm || isLoading}
                aria-label="Ask SRU Buddy"
                onChange={(e) => {
                  setWidgetInput(e.target.value);
                  adjustTextareaHeight(e.target);
                }}
                onFocus={() => {
                  if (showRecoveryCard && messagesAreaRef.current) {
                    messagesAreaRef.current.scrollTo({
                      top: messagesAreaRef.current.scrollHeight,
                      behavior: "smooth",
                    });
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    handleWidgetSubmit(e);
                  }
                }}
              />

              <button
                type="button"
                className={`sru-widget-voice-btn ${listening ? "listening" : ""}`}
                onClick={toggleVoice}
                disabled={showInlineLeadForm}
                title={listening ? "Stop voice recording" : "Voice Typing"}
                aria-label={listening ? "Stop voice recording" : "Start voice typing"}
                aria-pressed={listening}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
              </button>

              <button
                type="submit"
                className="sru-widget-send-btn"
                disabled={showInlineLeadForm || !widgetInput.trim() || isLoading}
                title="Send Message"
                aria-label="Send message"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" />
                </svg>
              </button>
            </form>

            <div className="sru-widget-watermark">
              <span className="sru-watermark-version">v{APP_VERSION}</span>
              <span className="sru-watermark-dot">•</span>
              <span className="sru-watermark-text">powered by</span>
              <span className="sru-watermark-badge" title="SR University Student Ambassadors">
                <img src="/student-ambassadors.png" alt="Student Ambassadors" className="sru-watermark-logo" />
              </span>
            </div>
          </div>
        </div>

        <Suspense fallback={null}>
          {isCalculatorOpen && (
            <ScholarshipCalculatorModal
              onClose={() => setIsCalculatorOpen(false)}
              onAskBuddy={(prompt) => {
                setIsCalculatorOpen(false);
                handleSendMessage(prompt);
              }}
            />
          )}

          {showLeadAuthModal && (
            <LeadAuthModal
              isOpen
              onClose={() => {
                setShowLeadAuthModal(false);
                try {
                  sessionStorage.setItem("sru_lead_skipped", "1");
                } catch {
                  /* ignore */
                }
                if (pendingAuthMessage) {
                  const nextMsg = pendingAuthMessage;
                  setPendingAuthMessage(null);
                  executeSendMessage(nextMsg);
                }
              }}
              onSuccess={(_lead) => {
                setShowLeadAuthModal(false);
                if (pendingAuthMessage) {
                  const nextMsg = pendingAuthMessage;
                  setPendingAuthMessage(null);
                  executeSendMessage(nextMsg);
                }
              }}
            />
          )}

          {showSettings && (
            <SettingsModal
              isOpen
              onClose={() => setShowSettings(false)}
              sessionId={sessionId}
            />
          )}
        </Suspense>
      </div>
    );
  }

  // Full Portal Landing Page + Floating Minimal Assistant Widget
  return (
    <div className="sru-portal-root">
      {/* 1. Top Announcement Ribbon */}
      <div className="sru-top-ribbon">
        <div className="sru-ribbon-left">
          <span className="sru-ribbon-tag">Admissions 2027-28</span>
          <span className="sru-ribbon-version-pill" title={`Release v${APP_VERSION}`}>v{APP_VERSION}</span>
          <span className="sru-ribbon-text">
            Applications Open for Academic Session 2027-28
          </span>
          <button
            className="sru-btn-register"
            style={{ padding: "2px 8px", fontSize: "0.68rem" }}
            onClick={() => setShowLeadAuthModal(true)}
          >
            REGISTER NOW
          </button>
        </div>

        <div className="sru-ribbon-right">
          <button
            className="sru-btn-embed"
            onClick={() => {
              const code = `<script src="https://university-ai-companion.vercel.app/widget.js" defer></script>`;
              navigator.clipboard?.writeText(code);
              alert("Copied embed script to clipboard!\n\nAdd this tag before </body> on your university website to add this chat bubble:\n\n" + code);
            }}
            title="Copy script tag to add this chat bubble to your official university website"
          >
            📋 Add Bubble to Website
          </button>

          <a
            href="https://wa.me/919640606408"
            target="_blank"
            rel="noopener noreferrer"
            className="sru-ribbon-link"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
            WhatsApp
          </a>

          <a href="tel:8331003030" className="sru-ribbon-link">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
            </svg>
            833 100 3030
          </a>

          <div className="sru-ribbon-socials">
            <span className="sru-social-icon" title="Facebook">f</span>
            <span className="sru-social-icon" title="X / Twitter">𝕏</span>
            <span className="sru-social-icon" title="LinkedIn">in</span>
            <span className="sru-social-icon" title="Instagram">ig</span>
            <span className="sru-social-icon" title="YouTube">yt</span>
          </div>

          {onOpenAdmin && (
            <button className="sru-admin-badge" onClick={onOpenAdmin}>
              Admin Console
            </button>
          )}
        </div>
      </div>

      {/* 2. Main University Navigation Bar */}
      <header className="sru-main-nav">
        <div className="sru-nav-brand">
          <div className="sru-brand-logo-badge" title="SR University">
            <img src="/sru-logo-white.png" alt="SR University" className="sru-brand-logo-img" />
          </div>
          <div className="sru-brand-meta">
            <span className="sru-brand-title">SR UNIVERSITY</span>
            <span className="sru-brand-sub">WARANGAL, TELANGANA • NAAC 'A' GRADE</span>
          </div>
        </div>

        <nav>
          <ul className="sru-nav-menu">
            <li className="sru-nav-item"><span className="sru-nav-link">ABOUT US ▾</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link sru-ai-nav-pill">AI FEATURES</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">ACADEMICS ▾</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">PROGRAMS ▾</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">ADMISSIONS ▾</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">CAMPUS LIFE ▾</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">RESEARCH</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">PLACEMENTS</span></li>
            <li className="sru-nav-item"><span className="sru-nav-link">CONTACT US</span></li>
          </ul>
        </nav>

        <div className="sru-nav-cta-group">
          <button
            className="sru-btn-calc"
            onClick={() => setIsCalculatorOpen(true)}
            title="Open Fee & Scholarship Calculator"
          >
            <CalculatorIcon size={16} />
            <span>Fee Calculator</span>
          </button>
          <button
            className="sru-btn-register"
            onClick={() => setShowLeadAuthModal(true)}
          >
            REGISTER NOW
          </button>
        </div>
      </header>

      {/* 3. Hero Section (Center Stage matching reference image) */}
      <main className="sru-hero-section">
        <div className="sru-hero-badge">
          ✨ Admissions Open • Academic Session 2027-28
        </div>
        <h1 className="sru-hero-title">
          India's First AI-Augmented Multidisciplinary University
        </h1>
        <p className="sru-hero-desc">
          In an era propelled by the advent of artificial intelligence, SR University, Telangana,
          has embraced customised learning pathways, data-driven insights, virtual reality experiences,
          and real-world simulations to transform every classroom into a future-ready launchpad,
          empowering students to learn smarter, think sharper, and graduate career-ready.
        </p>

        <div className="sru-hero-stats">
          <div className="sru-stat-card">
            <span className="sru-stat-value">₹51 LPA</span>
            <span className="sru-stat-label">Highest Package @ Microsoft</span>
          </div>
          <div className="sru-stat-card">
            <span className="sru-stat-value">91st</span>
            <span className="sru-stat-label">NIRF Rank in Engineering</span>
          </div>
          <div className="sru-stat-card">
            <span className="sru-stat-value">170 Acres</span>
            <span className="sru-stat-label">Green Tech Campus & Labs</span>
          </div>
          <div className="sru-stat-card">
            <span className="sru-stat-value">NAAC 'A'</span>
            <span className="sru-stat-label">Tier-I NBA Accredited</span>
          </div>
        </div>
      </main>

      {/* 4. Floating Bottom Launcher Dock (Matches Reference Image 2) */}
      {(!isWidgetOpen || isMinimized) && (
        <div className="sru-floating-dock">
          <form className="sru-dock-input-pill" onSubmit={handleDockSubmit}>
            <input
              type="text"
              className="sru-dock-field"
              placeholder={showInlineLeadForm ? "Share your name & mobile number in chat to continue" : "Ask anything about us...."}
              value={dockQuery}
              onChange={(e) => setDockQuery(e.target.value)}
            />
            <button type="submit" className="sru-dock-btn">
              Just Ask
            </button>
          </form>

          <div className="sru-launcher-cluster">
            <button
              className="sru-dock-register-btn"
              onClick={() => setShowLeadAuthModal(true)}
            >
              <span>REGISTER</span>
              <span>NOW</span>
            </button>

            <button
              className="sru-launcher-avatar-btn"
              onClick={() => {
                setIsWidgetOpen(true);
                setIsMinimized(false);
              }}
              title="Open SRU Buddy AI Assistant"
              aria-label="Open SRU Buddy AI Assistant"
            >
              <div className="sru-launcher-pulse" />
              <img src="/sru-logo-white.png" alt="SRU" className="sru-launcher-img" />
              <div className="sru-launcher-tooltip">Ask SRU Buddy</div>
            </button>
          </div>
        </div>
      )}

      {/* 5. Floating AI Assistant Widget Modal (Matches Reference Image 1) */}
      {isWidgetOpen && (
        <div className={`sru-widget-container ${isMinimized ? "sru-widget-minimized" : ""}`}>
          {/* Header */}
          <div className="sru-widget-header">
            <div className="sru-widget-header-left">
              <div className="sru-widget-avatar-wrap">
                <img src="/sru-logo.png" alt="SRU" className="sru-widget-avatar-img" />
              </div>
              <div className="sru-widget-title-col">
                <div className="sru-widget-title-row">
                  <span className="sru-widget-title">SRU Buddy</span>
                  <span className="sru-version-pill" title={`SR University AI Companion v${APP_VERSION}`}>v{APP_VERSION}</span>
                </div>
                <span className="sru-widget-status">
                  <span className={`sru-widget-status-dot ${currentStatus.type}`} />
                  {currentStatus.text}
                </span>
              </div>
            </div>

            <div className="sru-widget-header-actions">
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setShowSettings(true)}
                title="Student Profile & Settings"
                aria-label="Student Profile & Settings"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setIsCalculatorOpen(true)}
                title="Fee Calculator"
                aria-label="Fee Calculator"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="4" y="2" width="16" height="20" rx="2" />
                  <line x1="8" y1="6" x2="16" y2="6" />
                  <line x1="16" y1="14" x2="16" y2="18" />
                  <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={handleResetChat}
                title="Reset / New Chat"
                aria-label="Reset Chat"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                  <path d="M21 3v5h-5" />
                  <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                  <path d="M8 16H3v5" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setIsMinimized((prev) => !prev)}
                title={isMinimized ? "Expand" : "Minimize"}
                aria-label="Minimize"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </button>
              <button
                className="sru-widget-hdr-btn"
                onClick={() => setIsWidgetOpen(false)}
                title="Close"
                aria-label="Close"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>

          {/* Body */}
          {!isMinimized && (
            <>
              <div className="sru-widget-body" ref={messagesAreaRef}>
                {showRecoveryCard && recoveryContext && (
                  <RecoveryCard
                    context={recoveryContext}
                    onContinue={handleContinueConversation}
                    onStartFresh={handleStartNewConversation}
                    isContinuing={isRestoringConv}
                  />
                )}
                {messages.length > visibleMessages.length && (
                  <button
                    type="button"
                    onClick={() => setVisibleMessageCount((count) => Math.min(messages.length, count + MESSAGE_RENDER_WINDOW))}
                    style={{ alignSelf: "center", margin: "8px auto", color: "#0055a4", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "999px", padding: "5px 12px", cursor: "pointer", fontSize: "0.75rem", fontWeight: 600 }}
                  >
                    Load older messages
                  </button>
                )}
                {visibleMessages
                  .filter((msg) => !(showRecoveryCard && msg.id.startsWith("welcome-sru-buddy")))
                  .map((msg, index) => (
                  <div
                    key={msg.id || index}
                    id={msg.id ? `sru-msg-${msg.id}` : undefined}
                    style={{ width: "100%" }}
                  >
                    <MessageBubble
                      role={msg.role}
                      content={msg.content}
                      cards={msg.cards}
                      suggestions={msg.suggestions}
                      flow={msg.flow}
                      messageId={msg.id}
                      conversationId={activeConvId}
                      sessionId={sessionId}
                      isStreaming={msg.id === streamingMsgId}
                      onSuggestionClick={(prompt) => handleSendMessage(prompt)}
                    />
                  </div>
                ))}

                {showInlineLeadForm && (
                  <ChatLeadForm onComplete={handleLeadFormComplete} pendingQuestion={pendingQuestion} />
                )}

                {isLoading && !messages.some((m) => m.id === streamingMsgId && ((m.content && m.content.trim().length > 0) || (m.cards && m.cards.length > 0))) && (
                  <div className="message-bubble-row assistant sru-thinking-bubble-row">
                    <div className="message-avatar-col">
                      <div className="assistant-avatar-badge" title="SRU Buddy">
                        <img src="/sru-logo.png" alt="SRU" className="assistant-avatar-img" />
                      </div>
                    </div>
                    <div className="message-content-col">
                      <div className="message-text-bubble assistant sru-typing-bubble">
                        <div className="sru-typing-dots" aria-hidden="true">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                        <span className="sru-typing-tool-label">{activeToolStatus || "Thinking..."}</span>
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div style={{ color: "#b91c1c", fontSize: "0.82rem", padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px" }}>
                    {error}
                  </div>
                )}

              </div>

              {/* Footer / Input Bar */}
              <div className="sru-widget-footer">
                {showRecoveryCard && recoveryContext && (
                  <div className="sru-recovery-dock" role="region" aria-label="Conversation recovery choices">
                    <div className="sru-recovery-dock-header">
                      <span className="sru-recovery-dock-badge">✨ Session Saved</span>
                      <span className="sru-recovery-dock-text">Please choose to proceed:</span>
                    </div>
                    <div className="sru-recovery-dock-actions">
                      <button
                        type="button"
                        className="sru-recovery-dock-btn sru-recovery-dock-btn--continue"
                        onClick={handleContinueConversation}
                        disabled={isRestoringConv}
                        aria-label="Continue previous conversation"
                      >
                        {isRestoringConv ? (
                          <span>Restoring...</span>
                        ) : (
                          <>
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                              <polygon points="6 4 20 12 6 20 6 4" />
                            </svg>
                            <span>Continue Chat</span>
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        className="sru-recovery-dock-btn sru-recovery-dock-btn--fresh"
                        onClick={handleStartNewConversation}
                        disabled={isRestoringConv}
                        aria-label="Start fresh conversation"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                        </svg>
                        <span>Start Fresh</span>
                      </button>
                    </div>
                  </div>
                )}
                <form className="sru-widget-input-row" onSubmit={handleWidgetSubmit}>
                  <textarea
                    ref={portalTextareaRef}
                    className="sru-widget-textarea"
                    placeholder={
                      showRecoveryCard
                        ? "Choose Continue or Start Fresh above..."
                        : showInlineLeadForm
                        ? "Please share your name & mobile number above to chat"
                        : "Ask SRU Buddy..."
                    }
                    rows={1}
                    value={widgetInput}
                    disabled={showInlineLeadForm || isLoading}
                    aria-label="Ask SRU Buddy"
                    onChange={(e) => {
                      setWidgetInput(e.target.value);
                      adjustTextareaHeight(e.target);
                    }}
                    onFocus={() => {
                      if (showRecoveryCard && messagesAreaRef.current) {
                        messagesAreaRef.current.scrollTo({
                          top: messagesAreaRef.current.scrollHeight,
                          behavior: "smooth",
                        });
                      }
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                        e.preventDefault();
                        handleWidgetSubmit(e);
                      }
                    }}
                  />

                  <button
                    type="button"
                    className={`sru-widget-voice-btn ${listening ? "listening" : ""}`}
                    onClick={toggleVoice}
                    disabled={showInlineLeadForm}
                    title={listening ? "Stop voice recording" : "Voice Typing"}
                    aria-label={listening ? "Stop voice recording" : "Start voice typing"}
                    aria-pressed={listening}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                  </button>

                  <button
                    type="submit"
                    className="sru-widget-send-btn"
                    disabled={showInlineLeadForm || !widgetInput.trim() || isLoading}
                    title="Send Message"
                    aria-label="Send message"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="22" y1="2" x2="11" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor" />
                    </svg>
                  </button>
                </form>

                <div className="sru-widget-watermark">
                  <span className="sru-watermark-version">v{APP_VERSION}</span>
                  <span className="sru-watermark-dot">•</span>
                  <span className="sru-watermark-text">powered by</span>
                  <span className="sru-watermark-badge" title="SR University Student Ambassadors">
                    <img src="/student-ambassadors.png" alt="Student Ambassadors" className="sru-watermark-logo" />
                  </span>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      <Suspense fallback={null}>
        {isCalculatorOpen && (
          <ScholarshipCalculatorModal
            onClose={() => setIsCalculatorOpen(false)}
            onAskBuddy={(prompt) => {
              setIsCalculatorOpen(false);
              handleSendMessage(prompt);
            }}
          />
        )}

        {showLeadAuthModal && (
          <LeadAuthModal
            isOpen
            onClose={() => {
              setShowLeadAuthModal(false);
              try {
                sessionStorage.setItem("sru_lead_skipped", "1");
              } catch {
                /* ignore */
              }
              if (pendingAuthMessage) {
                const nextMsg = pendingAuthMessage;
                setPendingAuthMessage(null);
                executeSendMessage(nextMsg);
              }
            }}
            onSuccess={(_lead) => {
              setShowLeadAuthModal(false);
              if (pendingAuthMessage) {
                const nextMsg = pendingAuthMessage;
                setPendingAuthMessage(null);
                executeSendMessage(nextMsg);
              }
            }}
          />
        )}

        {showSettings && (
          <SettingsModal
            isOpen
            onClose={() => setShowSettings(false)}
            sessionId={sessionId}
          />
        )}
      </Suspense>
    </div>
  );
}
