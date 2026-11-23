import type { ConversationRecoveryContext } from "../services/api";
import { describeGap } from "../utils/timeAgo";
import "./WelcomeBackPanel.css";

export type WelcomeBackStatus = "idle" | "restoring" | "starting" | "error";

interface Props {
  context: ConversationRecoveryContext;
  /** "returning": the student opened SRU Buddy again. "idle": they came back to a tab left open. */
  mode: "returning" | "idle";
  status: WelcomeBackStatus;
  errorText?: string | null;
  /** A message the student typed before choosing; it is sent once they choose. */
  pendingMessage?: string | null;
  onContinue: () => void;
  onStartNew: () => void;
  /** Shared computer: forget the saved name and number, then start a new conversation. */
  onNotMe?: () => void;
  /** False when the previous conversation is no longer available (only "start a new chat" remains). */
  canContinue?: boolean;
}

function firstName(name?: string | null): string {
  const clean = (name || "").trim().split(/\s+/)[0] || "";
  return clean ? clean.charAt(0).toUpperCase() + clean.slice(1) : "";
}

/**
 * The "continue or start new" choice shown when a student returns to SRU Buddy after a break.
 * It sits inside the conversation (not a pop-up), so the chat stays visible and usable.
 */
export default function WelcomeBackPanel({
  context,
  mode,
  status,
  errorText,
  pendingMessage,
  onContinue,
  onStartNew,
  onNotMe,
  canContinue = true,
}: Props) {
  const name = firstName(context.student_name);
  const gap = describeGap(context.inactive_minutes, context.last_active_at);
  const busy = status === "restoring" || status === "starting";
  const topic = (context.title || context.topic || "").trim();
  const showTopic = topic && !/^(chat|new conversation|sru admissions|sr university admissions)$/i.test(topic);
  const lastQuestion = (context.last_user_message || "").trim();
  const details = [context.program_name, context.score_text, context.board_name].filter(Boolean) as string[];

  return (
    <section
      className={`wb-panel ${mode === "idle" ? "wb-panel--idle" : ""}`}
      role="region"
      aria-label="Continue your previous conversation"
      aria-busy={busy}
    >
      <div className="wb-head">
        <span className="wb-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12a9 9 0 1 0 3-6.7" />
            <polyline points="3 4 3 9 8 9" />
            <polyline points="12 7 12 12 15 14" />
          </svg>
        </span>
        <div className="wb-head-text">
          <h3 className="wb-title">{name ? `Welcome back, ${name}!` : "Welcome back!"}</h3>
          <p className="wb-sub">
            {mode === "idle"
              ? `Your last message here was ${gap}. Continue this conversation or start a new one?`
              : `You have a conversation from ${gap}. Would you like to continue it or start a new one?`}
          </p>
        </div>
      </div>

      {mode === "returning" && (showTopic || lastQuestion || details.length > 0) && (
        <div className="wb-preview">
          {showTopic && <div className="wb-preview-title">{topic}</div>}
          {lastQuestion && lastQuestion !== topic && (
            <div className="wb-preview-last">
              <span className="wb-preview-label">Last question</span>
              <span className="wb-preview-quote">“{lastQuestion}”</span>
            </div>
          )}
          {details.length > 0 && (
            <div className="wb-chips">
              {details.map((d) => (
                <span key={d} className="wb-chip">{d}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {pendingMessage && status !== "error" && (
        <p className="wb-pending">Choose an option and I'll answer “{pendingMessage.length > 70 ? `${pendingMessage.slice(0, 67)}…` : pendingMessage}”.</p>
      )}

      {status === "error" && (
        <p className="wb-error" role="alert">{errorText || "Something went wrong. Please try again."}</p>
      )}

      <div className="wb-actions">
        <button type="button" className="wb-btn wb-btn--primary" onClick={onContinue} disabled={busy || !canContinue}>
          {status === "restoring" ? (
            <>
              <span className="wb-spinner" aria-hidden="true" /> Restoring…
            </>
          ) : (
            <>
              {status === "error" && mode === "returning" ? "Try again" : "Continue chat"}
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </>
          )}
        </button>
        <button type="button" className="wb-btn wb-btn--secondary" onClick={onStartNew} disabled={busy}>
          {status === "starting" ? (
            <>
              <span className="wb-spinner wb-spinner--dark" aria-hidden="true" /> Starting…
            </>
          ) : (
            "Start a new chat"
          )}
        </button>
      </div>

      <p className="wb-foot">
        Starting a new chat keeps this conversation saved.
        {name && onNotMe && (
          <>
            {" "}
            <button type="button" className="wb-link" onClick={onNotMe} disabled={busy}>
              Not {name}?
            </button>
          </>
        )}
      </p>
    </section>
  );
}
