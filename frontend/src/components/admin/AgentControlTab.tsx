import { useEffect, useRef, useState } from "react";
import {
  acceptLiveRequest,
  fetchChatSettings,
  fetchCopilotDraft,
  fetchCopilotPriorities,
  saveChatSettings,
  type ChatSettings,
  type CopilotLead,
  type LiveRequest,
} from "../../services/api";
import { useLiveRequests } from "./useLiveRequests";
import "./AgentControlTab.css";

/**
 * Admin "Agent" tab (v4.12.0):
 *  1. Students waiting to talk to a counsellor now ("I'll call now"), also shown as a banner on every tab;
 *  2. Counsellor copilot: who to call first (ranked, with reasons) and a ready draft message;
 *  3. Chat settings: switches that change the chat at once, without a code change or redeploy.
 */

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const COUNSELLOR_KEY = "sru_admin_counsellor_name";

function readName(): string {
  try {
    return localStorage.getItem(COUNSELLOR_KEY) || "";
  } catch {
    return "";
  }
}

function caseLines(c: Record<string, any> = {}): string[] {
  const labels: [string, string][] = [
    ["program", "Course"], ["marks", "Marks"], ["scholarship", "Scholarship"],
    ["concession", "Concession"], ["hostel", "Hostel"], ["fee", "Fee"],
  ];
  const out = labels.filter(([k]) => c[k]).map(([k, label]) => `${label}: ${c[k]}`);
  if (Array.isArray(c.asked) && c.asked.length) out.push(`Asked: ${c.asked.map((a: string) => `"${a}"`).join(" | ")}`);
  return out;
}

function LiveRequestCard({ req, adminKey, onDone }: { req: LiveRequest; adminKey: string; onDone: () => void }) {
  const [left, setLeft] = useState(req.seconds_left);
  const [state, setState] = useState<"" | "accepting" | "accepted" | "late" | "error">("");
  const [phone, setPhone] = useState<string>("");
  const deadline = useRef(0);
  useEffect(() => {
    deadline.current = Date.now() + req.seconds_left * 1000;
    const id = window.setInterval(() => setLeft(Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000))), 250);
    return () => window.clearInterval(id);
  }, [req.seconds_left]);

  const accept = async () => {
    setState("accepting");
    try {
      const r = await acceptLiveRequest(adminKey, req.request_id, readName() || undefined);
      setPhone(r.phone);
      setState("accepted");
    } catch (err) {
      setState(/already|timed out/i.test((err as Error).message) ? "late" : "error");
      window.setTimeout(onDone, 2500);
    }
  };

  return (
    <div className={`agc-live ${state === "accepted" ? "is-accepted" : ""}`}>
      <div className="agc-live-head">
        <strong>{req.first_name || "A student"}</strong> wants to talk to a counsellor now
        {state !== "accepted" && <span className="agc-live-timer">{left}s</span>}
      </div>
      <ul className="agc-case">
        {caseLines(req.case).map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
      {state === "accepted" ? (
        <div className="agc-live-call">
          Call now: <a href={`tel:+91${phone.replace(/\D/g, "").slice(-10)}`}>{phone}</a>
          <span className="agc-muted"> (the student was told you're calling)</span>
          <button type="button" className="agc-link" onClick={onDone}>Done</button>
        </div>
      ) : state === "late" ? (
        <p className="agc-muted">Too late: the request timed out or another counsellor took it.</p>
      ) : state === "error" ? (
        <p className="agc-error">Couldn't accept. Please try again.</p>
      ) : (
        <button type="button" className="admin-btn-primary" onClick={accept} disabled={state === "accepting" || left <= 0}>
          {left <= 0 ? "Timed out: callback arranged" : state === "accepting" ? "Accepting…" : "I'll call now"}
        </button>
      )}
    </div>
  );
}

/** Rings on every admin tab while a student is waiting. */
export function LiveRequestBanner({ adminKey, onOpen }: { adminKey: string; onOpen: () => void }) {
  const { requests } = useLiveRequests(adminKey);
  useEffect(() => {
    const base = document.title.replace(/^\(\d+\) /, "");
    document.title = requests.length ? `(${requests.length}) ${base}` : base;
  }, [requests.length]);
  if (!requests.length) return null;
  return (
    <div className="agc-banner" role="alert">
      <span className="agc-bell" aria-hidden="true">🔔</span>
      <span>
        {requests.length === 1
          ? `${requests[0].first_name || "A student"} wants to talk to a counsellor now (${requests[0].seconds_left}s)`
          : `${requests.length} students want to talk to a counsellor now`}
      </span>
      <button type="button" className="admin-btn-primary" onClick={onOpen}>Open</button>
    </div>
  );
}

function SettingsPanel({ adminKey }: { adminKey: string }) {
  const [settings, setSettings] = useState<ChatSettings | null>(null);
  const [saved, setSaved] = useState<ChatSettings | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchChatSettings(adminKey)
      .then((r) => {
        setSettings(r.settings);
        setSaved(r.settings);
        setUpdatedAt(r.updated_at || null);
      })
      .catch((e) => setStatus({ kind: "error", text: (e as Error).message }));
  }, [adminKey]);

  const save = async (changes: Partial<ChatSettings>) => {
    setBusy(true);
    setStatus(null);
    try {
      const r = await saveChatSettings(adminKey, changes);
      setSettings(r.settings);
      setSaved(r.settings);
      setUpdatedAt(r.updated_at || null);
      setStatus({ kind: "ok", text: "Saved. The chat uses it from the next message." });
    } catch (e) {
      setSettings(saved);
      setStatus({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  if (!settings) {
    return (
      <section className="admin-card-panel agc-panel">
        <h3 className="panel-headline">Chat settings</h3>
        {status ? <p className="agc-error">{status.text}</p> : <p className="agc-muted">Loading…</p>}
      </section>
    );
  }

  const changed =
    saved &&
    (settings.connect_wait_seconds !== saved.connect_wait_seconds ||
      settings.office_hours_start !== saved.office_hours_start ||
      settings.office_hours_end !== saved.office_hours_end ||
      settings.office_days.join() !== saved.office_days.join());

  return (
    <section className="admin-card-panel agc-panel">
      <h3 className="panel-headline">Chat settings</h3>
      <p className="agc-muted">Changes apply to the next message students send. No code change or redeploy needed.</p>

      <div className="agc-setting">
        <div>
          <div className="agc-setting-title">Special concessions: how they are shown</div>
          <div className="agc-muted">
            Grouped: 5 folded groups and a "None of these apply" button (shorter on phones). Full table: all 19 rows.
          </div>
        </div>
        <div className="agc-segment" role="radiogroup" aria-label="Special concessions display">
          {(["grouped", "table"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={settings.concession_picker === mode}
              className={settings.concession_picker === mode ? "is-on" : ""}
              disabled={busy}
              onClick={() => settings.concession_picker !== mode && save({ concession_picker: mode })}
            >
              {mode === "grouped" ? "Grouped (recommended)" : "Full table (19 rows)"}
            </button>
          ))}
        </div>
      </div>

      <div className="agc-setting">
        <div>
          <div className="agc-setting-title">Answers written by the AI</div>
          <div className="agc-muted">
            On: SRU Buddy writes each answer for the student's own question and conversation, from the verified facts.
            Off: the verified texts are shown as they are (no AI call for them; useful if the daily AI quota runs low).
            Cards, fees and workflows are the same either way.
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={settings.ai_answers}
          className={`agc-switch ${settings.ai_answers ? "is-on" : ""}`}
          disabled={busy}
          onClick={() => save({ ai_answers: !settings.ai_answers })}
        >
          <span />
          {settings.ai_answers ? "On" : "Off"}
        </button>
      </div>

      <div className="agc-setting">
        <div>
          <div className="agc-setting-title">"Talk to a counsellor" rings this panel</div>
          <div className="agc-muted">
            On: during office hours the student waits while this panel rings, then gets a callback if nobody answers.
            Off: the callback is arranged straight away.
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={settings.connect_enabled}
          className={`agc-switch ${settings.connect_enabled ? "is-on" : ""}`}
          disabled={busy}
          onClick={() => save({ connect_enabled: !settings.connect_enabled })}
        >
          <span />
          {settings.connect_enabled ? "On" : "Off"}
        </button>
      </div>

      <div className="agc-setting agc-setting--grid">
        <label>
          Wait (seconds)
          <input
            type="number"
            min={10}
            max={120}
            value={settings.connect_wait_seconds}
            onChange={(e) => setSettings({ ...settings, connect_wait_seconds: Number(e.target.value) })}
          />
        </label>
        <label>
          Office hours from
          <input
            type="time"
            value={settings.office_hours_start}
            onChange={(e) => setSettings({ ...settings, office_hours_start: e.target.value })}
          />
        </label>
        <label>
          until
          <input
            type="time"
            value={settings.office_hours_end}
            onChange={(e) => setSettings({ ...settings, office_hours_end: e.target.value })}
          />
        </label>
        <fieldset className="agc-days">
          <legend>Working days</legend>
          {DAYS.map((d, i) => (
            <label key={d}>
              <input
                type="checkbox"
                checked={settings.office_days.includes(i)}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    office_days: e.target.checked
                      ? [...settings.office_days, i].sort()
                      : settings.office_days.filter((x) => x !== i),
                  })
                }
              />
              {d}
            </label>
          ))}
        </fieldset>
        <button
          type="button"
          className="admin-btn-primary"
          disabled={busy || !changed}
          onClick={() =>
            save({
              connect_wait_seconds: settings.connect_wait_seconds,
              office_hours_start: settings.office_hours_start,
              office_hours_end: settings.office_hours_end,
              office_days: settings.office_days,
            })
          }
        >
          Save hours
        </button>
      </div>

      {status && <p className={status.kind === "ok" ? "agc-ok" : "agc-error"}>{status.text}</p>}
      {updatedAt && <p className="agc-muted">Last changed: {new Date(updatedAt).toLocaleString()}</p>}
    </section>
  );
}

function CopilotPanel({ adminKey }: { adminKey: string }) {
  const [leads, setLeads] = useState<CopilotLead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ leadId: string; text: string; wa?: string | null } | null>(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    setError(null);
    try {
      setLeads((await fetchCopilotPriorities(adminKey)).leads);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openDraft = async (leadId: string) => {
    setCopied(false);
    try {
      const d = await fetchCopilotDraft(adminKey, leadId);
      setDraft({ leadId, text: d.text, wa: d.whatsapp_url });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <section className="admin-card-panel agc-panel">
      <div className="agc-row">
        <h3 className="panel-headline">Counsellor copilot</h3>
        <button type="button" className="admin-btn-primary" onClick={load}>
          {leads ? "Refresh" : "Who should I call first?"}
        </button>
      </div>
      <p className="agc-muted">
        Open requests of the last 14 days, ranked by what the student did in the chat. Drafts are written from the
        verified fee data; you read, edit and send them yourself.
      </p>
      {error && <p className="agc-error">{error}</p>}
      {leads && leads.length === 0 && <p className="agc-muted">No open requests. 🎉</p>}
      {leads && leads.length > 0 && (
        <ol className="agc-leads">
          {leads.map((l) => (
            <li key={l.lead_id} className={`agc-lead agc-lead--${l.tier}`}>
              <div className="agc-lead-head">
                <span className={`agc-tier agc-tier--${l.tier}`}>{l.tier}</span>
                <strong>{l.name}</strong>
                <span className="agc-muted">{l.program || ""}</span>
                <a className="agc-phone" href={`tel:+91${l.phone.replace(/\D/g, "").slice(-10)}`}>{l.phone}</a>
              </div>
              <div className="agc-reasons">{l.reasons.join(" · ")}</div>
              {caseLines(l.case).length > 0 && (
                <ul className="agc-case">
                  {caseLines(l.case).map((x) => (
                    <li key={x}>{x}</li>
                  ))}
                </ul>
              )}
              <button type="button" className="agc-link" onClick={() => openDraft(l.lead_id)}>
                Draft a message
              </button>
              {draft?.leadId === l.lead_id && (
                <div className="agc-draft">
                  <textarea
                    value={draft.text}
                    onChange={(e) => setDraft({ ...draft, text: e.target.value })}
                    rows={5}
                    aria-label="Draft message"
                  />
                  <div className="agc-row">
                    <button
                      type="button"
                      className="admin-btn-primary"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(draft.text);
                          setCopied(true);
                        } catch {}
                      }}
                    >
                      {copied ? "Copied" : "Copy"}
                    </button>
                    {draft.wa && (
                      <a
                        className="agc-wa"
                        href={`${draft.wa.split("?")[0]}?text=${encodeURIComponent(draft.text)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open in WhatsApp
                      </a>
                    )}
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function AgentControlTab({ adminKey }: { adminKey: string }) {
  const { requests, inHours, reload } = useLiveRequests(adminKey);
  const [name, setName] = useState<string>(readName());
  return (
    <div className="tab-pane-container agc">
      <section className="admin-card-panel agc-panel">
        <div className="agc-row">
          <h3 className="panel-headline">Students waiting now</h3>
          <span className={`agc-hours ${inHours ? "is-open" : ""}`}>
            {inHours === null ? "" : inHours ? "Office hours: ringing is on" : "Outside office hours: callbacks only"}
          </span>
        </div>
        <label className="agc-name">
          Your name (shown to the student when you accept)
          <input
            value={name}
            maxLength={40}
            onChange={(e) => {
              setName(e.target.value);
              try {
                localStorage.setItem(COUNSELLOR_KEY, e.target.value);
              } catch {}
            }}
            placeholder="e.g. Priya"
          />
        </label>
        {requests.length === 0 ? (
          <p className="agc-muted">Nobody is waiting. A request appears here (and as a banner on every tab) for its wait time.</p>
        ) : (
          requests.map((r) => <LiveRequestCard key={r.request_id} req={r} adminKey={adminKey} onDone={reload} />)
        )}
      </section>
      <CopilotPanel adminKey={adminKey} />
      <SettingsPanel adminKey={adminKey} />
    </div>
  );
}
