import { useEffect, useRef, useState } from "react";
import { getSessionId } from "../hooks/useSession";
import { fetchConnectStatus, type CounsellorConnectStatus } from "../services/api";
import { CheckIcon, PhoneIcon, SparklesIcon } from "./Icons";
import "./AgentCards.css";

/**
 * v4.12.0 agent cards:
 *  * AgentPlanCard: the agent's visible plan (lowest-fee goal), each step done / now / to do;
 *  * CounsellorConnectCard: "Talk to a counsellor". It counts down while the admin panel rings, then shows
 *    either "a counsellor will call you now" or "all counsellors are busy, we'll call you back".
 */

type Step = { title: string; status: "done" | "now" | "todo" | "skipped"; detail?: string | null };

export function AgentPlanCard({ card }: { card: any }) {
  const d = card.data || {};
  const steps: Step[] = d.steps || [];
  const done = steps.filter((s) => s.status === "done").length;
  return (
    <div className="rich-card ag-plan" aria-label="The agent's plan">
      <div className="ag-plan-head">
        <span className="card-badge">
          <SparklesIcon size={14} /> {d.title || "My plan"}
        </span>
        <span className="ag-plan-count">
          {done}/{steps.length}
        </span>
      </div>
      <ol className="ag-steps">
        {steps.map((s) => (
          <li key={s.title} className={`ag-step ag-step--${s.status}`}>
            <span className="ag-step-icon" aria-hidden="true">
              {s.status === "done" ? (
                <CheckIcon size={12} strokeWidth={3} />
              ) : s.status === "now" ? (
                <span className="ag-dot" />
              ) : s.status === "skipped" ? (
                <span className="ag-dash" />
              ) : null}
            </span>
            <span className="ag-step-text">
              <span className="ag-step-title">{s.title}</span>
              {s.detail && <span className="ag-step-detail">{s.detail}</span>}
            </span>
            <span className="sr-only">
              {s.status === "done" ? "done" : s.status === "now" ? "in progress" : s.status === "skipped" ? "skipped" : "to do"}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function mmss(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function CounsellorConnectCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const initial: CounsellorConnectStatus = card.data || {};
  const [st, setSt] = useState<CounsellorConnectStatus>(initial);
  const [left, setLeft] = useState<number>(initial.seconds_left ?? 0);
  const [lost, setLost] = useState(false);
  const deadline = useRef<number>(0);
  const box = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    deadline.current = Date.now() + (initial.seconds_left ?? 0) * 1000;
  }, [initial.seconds_left]);
  // The student must see the countdown and the outcome: bring the card into view when it appears and when the
  // status changes (only for a live request; an old one in a restored chat stays where it is).
  useEffect(() => {
    if (initial.status === "waiting" && box.current) {
      box.current.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [st.status, initial.status]);

  // Ask the server for the real status: on open (a reloaded chat) and every 3 s while waiting.
  useEffect(() => {
    if (!initial.request_id) return;
    let stop = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const next = await fetchConnectStatus(initial.request_id, getSessionId());
        if (stop) return;
        setSt(next);
        if (next.status === "waiting") {
          deadline.current = Date.now() + next.seconds_left * 1000;
          timer = window.setTimeout(poll, 3000);
        }
      } catch (err) {
        if (stop) return;
        if ((err as Error).message === "not_found") {
          setLost(true); // older than a day: the callback request itself is with the admissions team
        } else {
          timer = window.setTimeout(poll, 4000); // network hiccup: try again
        }
      }
    };
    poll();
    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [initial.request_id]);

  // The visible countdown.
  useEffect(() => {
    if (st.status !== "waiting") return;
    const id = window.setInterval(() => setLeft((deadline.current - Date.now()) / 1000), 250);
    return () => window.clearInterval(id);
  }, [st.status]);

  const masked = `******${st.phone_last4 || initial.phone_last4 || ""}`;

  if (lost) {
    return (
      <div className="rich-card ag-connect ag-connect--busy" role="status">
        <p className="ag-connect-msg">Your request is with the admissions team. They'll call you on {masked}.</p>
      </div>
    );
  }

  if (st.status === "accepted") {
    return (
      <div ref={box} className="rich-card ag-connect ag-connect--ok" role="status">
        <span className="ag-connect-icon">
          <PhoneIcon size={18} />
        </span>
        <div>
          <p className="ag-connect-title">Connected</p>
          <p className="ag-connect-msg">
            {st.counsellor ? `${st.counsellor}, a counsellor,` : "A counsellor"} will call you now on <strong>{masked}</strong>.
          </p>
        </div>
      </div>
    );
  }

  if (st.status === "busy") {
    return (
      <div ref={box} className="rich-card ag-connect ag-connect--busy" role="status">
        <span className="ag-connect-icon">
          <CheckIcon size={18} />
        </span>
        <div>
          <p className="ag-connect-title">All our counsellors are busy right now</p>
          <p className="ag-connect-msg">
            They're helping other students. Our admissions team will call you back on <strong>{masked}</strong>.
          </p>
          {onSelect && (
            <button type="button" className="card-more-btn ag-connect-change" onClick={() => onSelect("Change my number")}>
              Not your number? Change it
            </button>
          )}
        </div>
      </div>
    );
  }

  const total = st.wait_seconds || initial.wait_seconds || 30;
  const pct = Math.max(0, Math.min(100, (left / total) * 100));
  return (
    <div ref={box} className="rich-card ag-connect ag-connect--waiting" role="status" aria-live="polite">
      <div className="ag-connect-row">
        <span className="ag-spinner" aria-hidden="true" />
        <div>
          <p className="ag-connect-title">Connecting you to a counsellor…</p>
          <p className="ag-connect-msg">Please stay on this page.</p>
        </div>
        <span className="ag-timer" aria-label={`${Math.ceil(left)} seconds left`}>
          {mmss(left)}
        </span>
      </div>
      <div className="ag-bar" aria-hidden="true">
        <span style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
