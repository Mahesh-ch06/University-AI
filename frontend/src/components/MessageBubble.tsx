import { memo, useState, useMemo } from "react";
import { submitFeedback } from "../services/api";
import { RenderCard, deduplicateCards } from "./Cards";
import type { AcademicFormPayload } from "./Cards";
import MarkdownContent from "./MarkdownContent";
import { copyCleanText } from "../utils/cleanCopy";
import { renderUniIcon } from "./Icons";
import { sanitizeHelplineNumbers } from "../utils/sanitizeNumbers";
import "./MessageBubble.css";

function parseSuggestionChip(text: string): { icon: React.ReactNode; label: string } {
  const emojiRegex = /^(\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?|\p{Emoji_Presentation}|\p{Emoji}\uFE0F)\s*/u;
  const match = text.match(emojiRegex);
  if (match) {
    const emoji = match[1];
    const textLabel = text.slice(match[0].length).trim();
    const icon = renderUniIcon(emoji, 15, "chip-vector-icon");
    return { icon, label: textLabel || text };
  }
  if (text.includes("%") || text.includes("< 60%") || text.includes(">")) {
    return { icon: renderUniIcon("🎯", 15, "chip-vector-icon"), label: text };
  }
  return { icon: null, label: text };
}

interface Props {
  role: "user" | "assistant";
  content: string;
  sources?: any[];
  suggestions?: string[];
  cards?: any[];
  flow?: any;
  messageId?: string;
  conversationId?: string | null;
  sessionId?: string;
  createdAt?: string;
  isStreaming?: boolean;
  onSuggestionClick?: (text: string, form?: AcademicFormPayload) => void;
}

function MessageBubble({
  role,
  content,
  sources,
  suggestions,
  cards,
  flow,
  messageId,
  conversationId,
  sessionId,
  isStreaming,
  onSuggestionClick,
}: Props) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const hasPlacementCard = cards?.some(
    (c) => c.type === "placement_highlights" || c.image_url === "/placements-three-years.png"
  );
  const displayContent = sanitizeHelplineNumbers(
    hasPlacementCard
      ? content.replace(/!\[.*?\]\(\/placements-three-years\.png\)/g, "").trim()
      : content
  );

  const hasCards = Boolean(!isStreaming && role === "assistant" && cards && cards.length > 0);
  const { mainText, followupText } = useMemo(() => {
    if (!hasCards || !displayContent) {
      return { mainText: displayContent, followupText: null };
    }
    const trimmed = displayContent.trim();
    const paragraphs = trimmed.split(/\n\s*\n/);
    if (paragraphs.length < 2) {
      return { mainText: displayContent, followupText: null };
    }
    const lastPara = paragraphs[paragraphs.length - 1].trim();
    // Exclude markdown tables, lists, headers, blockquotes, and code fences
    if (
      lastPara.startsWith("|") ||
      lastPara.startsWith("-") ||
      lastPara.startsWith("*") ||
      lastPara.startsWith("#") ||
      lastPara.startsWith("```") ||
      lastPara.startsWith(">") ||
      /^\d+\./.test(lastPara)
    ) {
      return { mainText: displayContent, followupText: null };
    }
    // Check if last paragraph ends with '?' or starts with a typical follow-up invitation
    const isQuestion = lastPara.endsWith("?");
    const isCallToAction = /^(would you|do you|if you|let me know|feel free|shall i|should i|can i|want me to|could i|reach out to)\b/i.test(lastPara);

    if (isQuestion || isCallToAction) {
      return {
        mainText: paragraphs.slice(0, -1).join("\n\n"),
        followupText: lastPara,
      };
    }
    return { mainText: displayContent, followupText: null };
  }, [displayContent, hasCards]);

  const handleCopy = async () => {
    const success = await copyCleanText(displayContent);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRating = async (rating: 1 | -1) => {
    const type = rating === 1 ? "up" : "down";
    if (feedback === type) return;
    setFeedback(type);

    if (messageId && conversationId && sessionId && !isSubmitting) {
      setIsSubmitting(true);
      try {
        await submitFeedback({
          session_id: sessionId,
          conversation_id: conversationId,
          message_id: messageId,
          rating,
        });
      } catch (err) {
        console.error("Failed to submit feedback:", err);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className={`message-bubble-row ${role}`}>
      {role === "assistant" && (
        <div className="message-avatar-col">
          <div className="assistant-avatar-badge" title="SRU Buddy">
            <img src="/sru-logo.png" alt="SRU" className="assistant-avatar-img" />
          </div>
        </div>
      )}

      <div className="message-content-col">
        {/* Guided Flow Progress (if active) */}
        {role === "assistant" && flow && (
          <div className="flow-step-banner">
            <div className="flow-step-header">
              <span className="flow-badge">Admission Wizard</span>
              <span className="flow-step-count">
                Step {flow.step} of {flow.total_steps}
              </span>
            </div>
            <div className="flow-progress-bar">
              <div
                className="flow-progress-fill"
                style={{ width: `${(flow.step / flow.total_steps) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Message Content Bubble */}
        {mainText && mainText.trim().length > 0 && (
          <div className={`message-text-bubble ${role}`}>
            <MarkdownContent content={mainText} isStreaming={isStreaming} />
          </div>
        )}

        {/* Rich Interactive Cards (placed seamlessly under main response text) */}
        {!isStreaming && role === "assistant" && cards && cards.length > 0 && (
          <div className="message-cards-container">
            {deduplicateCards(cards).map((card, idx) => (
              <RenderCard key={idx} card={card} onSelect={onSuggestionClick} />
            ))}
          </div>
        )}

        {/* Follow-up question / closing call-to-action (placed after the card) */}
        {!isStreaming && role === "assistant" && followupText && (
          <div className={`message-text-bubble ${role} message-followup-bubble`}>
            <MarkdownContent content={followupText} />
          </div>
        )}

        {/* Verified Sources Cited (AGENTS.md Rules 19 & 20) */}
        {!isStreaming && role === "assistant" && sources && sources.length > 0 && (
          <div className="message-sources-wrapper">
            <details className="message-sources-details">
              <summary className="message-sources-summary">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="sources-icon">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                <span>Verified Sources ({sources.length})</span>
              </summary>
              <div className="message-sources-list">
                {sources.map((src: any, i: number) => (
                  <div key={src.document_id || i} className="source-citation-card">
                    <div className="source-citation-title">
                      {src.page_url ? (
                        <a href={src.page_url} target="_blank" rel="noopener noreferrer" className="source-link">
                          {src.title} ↗
                        </a>
                      ) : (
                        <span>{src.title}</span>
                      )}
                    </div>
                    {src.section && <div className="source-citation-section">{src.section}</div>}
                    {src.department && <span className="source-citation-badge">{src.department}</span>}
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* Clean Suggestion Chips */}
        {!isStreaming && role === "assistant" && suggestions && suggestions.length > 0 && (
          <div className="suggestion-chips-wrapper">
            <div className="suggestion-chips-list">
              {suggestions.map((suggestion, idx) => {
                const cleanSuggestion = suggestion.replace(/Ask admissions to call me/gi, "Ask counsellor to call me");
                const { icon, label } = parseSuggestionChip(cleanSuggestion);
                return (
                  <button
                    key={idx}
                    className="suggestion-chip"
                    onClick={() => onSuggestionClick?.(cleanSuggestion)}
                    type="button"
                  >
                    {icon && <span className="suggestion-chip-icon">{icon}</span>}
                    {(() => {
                      // "AC 4-sharing (₹1,25,000)": the price in a lighter, smaller style (v4.13.0) so two options
                      // fit on one line; the text sent and read is unchanged.
                      const m = label.match(/^(.*\S)\s(\(₹[^)]*\))$/);
                      return m ? (
                        <span className="suggestion-chip-text">
                          {m[1]} <span className="suggestion-chip-meta">{m[2]}</span>
                        </span>
                      ) : (
                        <span className="suggestion-chip-text">{label}</span>
                      );
                    })()}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Buttons (Copy + Feedback) - at the very bottom of the whole response */}
        {role === "assistant" && content && content.trim().length > 0 && !isStreaming && (
          <div className="message-bottom-bar">
            <div className="minimal-action-bar">
              <button
                className="action-icon-btn"
                onClick={handleCopy}
                title={copied ? "Copied!" : "Copy message"}
                aria-label="Copy message"
                type="button"
              >
                {copied ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                )}
              </button>

              <button
                className={`action-icon-btn ${feedback === "up" ? "active" : ""}`}
                onClick={() => handleRating(1)}
                title="Good response"
                aria-label="Good response"
                type="button"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill={feedback === "up" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
                </svg>
              </button>

              <button
                className={`action-icon-btn ${feedback === "down" ? "active" : ""}`}
                onClick={() => handleRating(-1)}
                title="Poor response"
                aria-label="Poor response"
                type="button"
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill={feedback === "down" ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3" />
                </svg>
              </button>

              {copied && <span className="copy-feedback-label">Copied</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const areMessagePropsEqual = (previous: Props, next: Props): boolean =>
  previous.role === next.role &&
  previous.content === next.content &&
  previous.sources === next.sources &&
  previous.suggestions === next.suggestions &&
  previous.cards === next.cards &&
  previous.flow === next.flow &&
  previous.messageId === next.messageId &&
  previous.conversationId === next.conversationId &&
  previous.sessionId === next.sessionId &&
  previous.isStreaming === next.isStreaming;

export default memo(MessageBubble, areMessagePropsEqual);
