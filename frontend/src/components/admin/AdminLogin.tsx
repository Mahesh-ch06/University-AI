// Admin sign-in (v4.15.0): the admin key is checked with the server BEFORE the dashboard opens, so a wrong key
// gets a clear message here (not a flash of the dashboard). The key is kept only for this browser tab
// (sessionStorage), exactly as before; nothing about authentication changes.
import { useState } from "react";
import { fetchChatSettings } from "../../services/api";
import "./AdminLogin.css";

export default function AdminLogin({ onSuccess, onBackToChat, initialError }: {
  onSuccess: (key: string) => void;
  onBackToChat: () => void;
  initialError?: string | null;
}) {
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(initialError || null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = key.trim();
    if (!value) {
      setError("Enter your admin access key.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await fetchChatSettings(value);
      onSuccess(value);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(/401|403|invalid|unauthor|forbidden|key/i.test(msg)
        ? "That admin key isn't right. Check it and try again."
        : "Can't reach the SRU Buddy server right now. Check your connection and try again.");
      setBusy(false);
    }
  };

  return (
    <div className="al-page">
      <aside className="al-brand" aria-hidden="false">
        <div className="al-brand-top">
          <img src="/sru-logo.png" alt="SR University" className="al-logo" />
          <span className="al-brand-name">SRU Buddy</span>
        </div>
        <div className="al-brand-body">
          <h1 className="al-brand-title">Admissions console</h1>
          <p className="al-brand-text">Everything the admissions team needs to follow up with prospective students.</p>
          <ul className="al-points">
            <li>Leads with marks, programme and status</li>
            <li>Every student conversation, searchable</li>
            <li>Live counsellor requests and call-backs</li>
            <li>Quick Start tiles, events, videos and ads</li>
          </ul>
        </div>
        <p className="al-brand-foot">SR University, Warangal · Official</p>
      </aside>

      <main className="al-main">
        <button type="button" className="al-back" onClick={onBackToChat}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6" /></svg>
          Back to student chat
        </button>
        <form className="al-card" onSubmit={submit} noValidate>
          <div className="al-mobile-brand">
            <img src="/sru-logo.png" alt="" />
            <span>SRU Buddy</span>
          </div>
          <h2 className="al-title">Sign in</h2>
          <p className="al-sub">Use the admin access key given to the admissions team.</p>

          <label className="al-label" htmlFor="admin-key">Admin access key</label>
          <div className={`al-field ${error ? "has-error" : ""}`}>
            <svg className="al-field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <input
              id="admin-key"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your key"
              value={key}
              onChange={(e) => { setKey(e.target.value); if (error) setError(null); }}
              aria-invalid={!!error}
              aria-describedby={error ? "admin-key-error" : undefined}
              disabled={busy}
              autoFocus
            />
            <button type="button" className="al-eye" onClick={() => setShow((v) => !v)}
                    aria-label={show ? "Hide key" : "Show key"} aria-pressed={show}>
              {show ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
              )}
            </button>
          </div>
          {error && (
            <div className="al-error" id="admin-key-error" role="alert">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
              {error}
            </div>
          )}

          <button type="submit" className="al-submit" disabled={busy}>
            {busy ? <><span className="al-spinner" aria-hidden="true" /> Checking…</> : "Sign in"}
          </button>
          <p className="al-note">The key stays in this browser tab only and is cleared when you sign out or close the tab.</p>
        </form>
      </main>
    </div>
  );
}
