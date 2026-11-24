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
    <div className="wb-row" role="region" aria-label="Continue your previous conversation" aria-busy={busy}>
      <div className="wb-avatar" aria-hidden="true">
        <img src="/sru-logo.png" alt="" />
      </div>
      <section className={`wb-panel ${mode === "idle" ? "wb-panel--idle" : ""}`}>
        <p className="wb-greeting">
          {name ? <>Hey <strong>{name}</strong>! Welcome back.</> : <>Welcome back!</>}{" "}
          Would you like to continue our previous conversation or start a fresh chat?
        </p>

        {mode === "returning" && (showTopic || lastQuestion || details.length > 0 || gap) && (
          <div className="wb-preview">
            <div className="wb-preview-top">
              <span className="wb-preview-label">Previous conversation</span>
              {gap && <span className="wb-preview-when">{gap}</span>}
            </div>
            {showTopic && <div className="wb-preview-title">{topic}</div>}
            {lastQuestion && lastQuestion !== topic && (
              <div className="wb-preview-quote">“{lastQuestion}”</div>
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

        {status === "error" && (
          <p className="wb-error" role="alert">{errorText || "Something went wrong. Please try again."}</p>
        )}

        <div className="wb-actions">
          <button type="button" className="wb-btn wb-btn--primary" onClick={onContinue} disabled={busy || !canContinue}>
            {status === "restoring" ? (
              <>
                <span className="wb-spinner" aria-hidden="true" /> Restoring…
              </>
            ) : status === "error" && mode === "returning" && canContinue ? (
              "Try again"
            ) : (
              "Continue previous chat"
            )}
          </button>
          <button type="button" className="wb-btn wb-btn--secondary" onClick={onStartNew} disabled={busy}>
            {status === "starting" ? (
              <>
                <span className="wb-spinner wb-spinner--dark" aria-hidden="true" /> Starting…
              </>
            ) : (
              "Start fresh"
            )}
          </button>
        </div>

        <p className="wb-foot">
          {pendingMessage && status !== "error"
            ? "I'll answer your message as soon as you choose. "
            : ""}
          Starting fresh keeps the earlier chat saved.
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
    </div>
  );
}
