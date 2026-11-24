// Admin -> Campus media (v4.14.0): the events' photo cards, the official YouTube videos and the small chat ads.
// Each list is edited here and saved to the chat settings; the chat uses it from the next message (no redeploy).
import { useEffect, useMemo, useState } from "react";
import {
  fetchAdminVideos,
  fetchChatSettings,
  saveChatSettings,
  type AddedVideo,
  type BuiltinVideo,
  type ChatAd,
  type ChatSettings,
  type EventHighlight,
  type VideoChanges,
} from "../../services/api";
import { ChatAdStrip, EventHighlightsCard } from "../CampusCards";
import "./CampusMediaTab.css";

type Section = "events" | "videos" | "ads";
const MAX_EVENTS = 16;
const MAX_ADS = 6;
const isHttps = (u: string) => !u || /^https:\/\/\S+$/i.test(u.trim());
const slug = (prefix: string) => `${prefix}-${Date.now().toString(36)}`.slice(0, 30);
const ytId = (v: string) => {
  const m = (v || "").match(/(?:v=|youtu\.be\/|\/shorts\/|\/embed\/|\/live\/)([A-Za-z0-9_-]{11})/);
  return m ? m[1] : (v || "").trim();
};
const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

function useSettings(adminKey: string) {
  const [settings, setSettings] = useState<ChatSettings | null>(null);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetchChatSettings(adminKey)
      .then((r) => setSettings(r.settings))
      .catch((e) => setStatus({ kind: "error", text: (e as Error).message }));
  }, [adminKey]);
  const save = async (changes: Partial<ChatSettings>) => {
    setBusy(true);
    setStatus(null);
    try {
      const r = await saveChatSettings(adminKey, changes);
      setSettings(r.settings);
      setStatus({ kind: "ok", text: "Saved. Students see it from their next message." });
      return true;
    } catch (e) {
      setStatus({ kind: "error", text: (e as Error).message });
      return false;
    } finally {
      setBusy(false);
    }
  };
  return { settings, status, busy, save };
}

export default function CampusMediaTab({ adminKey }: { adminKey: string }) {
  const [section, setSection] = useState<Section>("events");
  const { settings, status, busy, save } = useSettings(adminKey);

  return (
    <div className="tab-pane-container cm-tab">
      <div className="cm-head">
        <div>
          <h2 className="cm-title">Campus media</h2>
          <p className="cm-muted">Event photo cards, official YouTube videos and small ads in the student chat.</p>
        </div>
        <div className="cm-seg" role="tablist" aria-label="Campus media sections">
          {(["events", "videos", "ads"] as Section[]).map((s) => (
            <button key={s} type="button" role="tab" aria-selected={section === s}
                    className={section === s ? "on" : ""} onClick={() => setSection(s)}>
              {s === "events" ? "Events" : s === "videos" ? "YouTube videos" : "Ads"}
            </button>
          ))}
        </div>
      </div>

      {status && <div className={`cm-status ${status.kind}`} role="status">{status.text}</div>}
      {!settings ? (
        <p className="cm-muted">{status ? "" : "Loading…"}</p>
      ) : section === "events" ? (
        <EventsEditor items={settings.event_highlights} busy={busy} onSave={(v) => save({ event_highlights: v })} />
      ) : section === "videos" ? (
        <VideosEditor adminKey={adminKey} changes={settings.videos} busy={busy} onSave={(v) => save({ videos: v })} />
      ) : (
        <AdsEditor items={settings.chat_ads} seconds={settings.ads_rotate_seconds} busy={busy}
                   onSave={(items, secs) => save({ chat_ads: items, ads_rotate_seconds: secs })} />
      )}
    </div>
  );
}

// ------------------------------------------------------------------ shared list helpers
function useDraft<T>(items: T[]) {
  const [draft, setDraft] = useState<T[]>(() => items.map((t) => ({ ...t })));
  const [source, setSource] = useState(items);
  if (source !== items) {
    setSource(items);
    setDraft(items.map((t) => ({ ...t })));
  }
  const set = (i: number, patch: Partial<T>) => setDraft((d) => d.map((t, j) => (j === i ? { ...t, ...patch } : t)));
  const move = (i: number, by: number) =>
    setDraft((d) => {
      const j = i + by;
      if (j < 0 || j >= d.length) return d;
      const next = [...d];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  const remove = (i: number) => setDraft((d) => d.filter((_, j) => j !== i));
  return { draft, setDraft, set, move, remove, changed: !same(draft, items) };
}

function RowTools({ i, n, on, onToggle, onMove, onRemove }: {
  i: number; n: number; on: boolean; onToggle: (v: boolean) => void; onMove: (by: number) => void; onRemove: () => void;
}) {
  return (
    <div className="cm-row-tools">
      <label className="cm-switch">
        <input type="checkbox" checked={on} onChange={(e) => onToggle(e.target.checked)} />
        <span>{on ? "Shown" : "Hidden"}</span>
      </label>
      <button type="button" className="cm-icon-btn" aria-label="Move up" disabled={i === 0} onClick={() => onMove(-1)}>↑</button>
      <button type="button" className="cm-icon-btn" aria-label="Move down" disabled={i === n - 1} onClick={() => onMove(1)}>↓</button>
      <button type="button" className="cm-icon-btn danger" onClick={onRemove}>Remove</button>
    </div>
  );
}

function SaveBar({ changed, invalid, busy, onUndo, onSave, error }: {
  changed: boolean; invalid: boolean; busy: boolean; onUndo: () => void; onSave: () => void; error?: string;
}) {
  return (
    <div className={`cm-savebar ${changed ? "is-dirty" : ""}`}>
      {error && <span className="cm-error">{error}</span>}
      <button type="button" className="admin-btn-secondary" disabled={!changed || busy} onClick={onUndo}>Undo changes</button>
      <button type="button" className="admin-btn-primary" disabled={!changed || invalid || busy} onClick={onSave}>
        {busy ? "Saving…" : "Save"}
      </button>
    </div>
  );
}

// ------------------------------------------------------------------ events
function EventsEditor({ items, busy, onSave }: { items: EventHighlight[]; busy: boolean; onSave: (v: EventHighlight[]) => void }) {
  const { draft, setDraft, set, move, remove, changed } = useDraft(items);
  const [open, setOpen] = useState<string | null>(null);
  const problem = draft.find((e) => !e.title.trim()) ? "Every event needs a title."
    : draft.find((e) => !isHttps(e.image_url)) ? "Image links must start with https://" : "";
  const shown = draft.filter((e) => e.enabled !== false && e.title.trim());

  return (
    <div className="cm-grid">
      <section className="admin-card-panel cm-panel">
        <h3 className="panel-headline">Events ({draft.length}/{MAX_EVENTS})</h3>
        <p className="cm-muted">Shown as photo cards when students ask about events, fests or campus life, in this
          order. A student who names an event (by its title or any of its other names) gets that event's card. Use
          only verified facts.</p>
        <div className="cm-list">
          {draft.map((e, i) => (
            <div key={e.id} className={`cm-row ${e.enabled === false ? "is-off" : ""}`}>
              <button type="button" className="cm-row-head" aria-expanded={open === e.id}
                      onClick={() => setOpen(open === e.id ? null : e.id)}>
                <span className="cm-thumb">{e.image_url && isHttps(e.image_url) ? <img src={e.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" /> : null}</span>
                <span className="cm-row-name">
                  <strong>{e.title || "New event"}</strong>
                  <small>{e.when || "No date"}</small>
                </span>
                <span className="cm-chevron" aria-hidden="true">{open === e.id ? "▴" : "▾"}</span>
              </button>
              <RowTools i={i} n={draft.length} on={e.enabled !== false} onToggle={(v) => set(i, { enabled: v })}
                        onMove={(by) => move(i, by)} onRemove={() => remove(i)} />
              {open === e.id && (
                <div className="cm-fields">
                  <label>Title<input value={e.title} maxLength={60} onChange={(x) => set(i, { title: x.target.value })} /></label>
                  <label>When<input value={e.when} maxLength={60} placeholder="e.g. 26 January 2027 or Every year"
                                    onChange={(x) => set(i, { when: x.target.value })} /></label>
                  <label className="wide">Description<textarea value={e.summary} maxLength={220} rows={2}
                                                             onChange={(x) => set(i, { summary: x.target.value })} /></label>
                  <label className="wide">Image link (https)<input value={e.image_url} maxLength={400}
                                                                  placeholder="https://sru.edu.in/wp-content/uploads/…"
                                                                  onChange={(x) => set(i, { image_url: x.target.value.trim() })} /></label>
                  <label>YouTube video (link or id, optional)<input value={e.video_id} maxLength={80}
                                                                    onChange={(x) => set(i, { video_id: ytId(x.target.value) })} /></label>
                  <label>Other names students use<input value={e.keywords} maxLength={200} placeholder="comma separated"
                                                        onChange={(x) => set(i, { keywords: x.target.value })} /></label>
                </div>
              )}
            </div>
          ))}
        </div>
        <button type="button" className="admin-btn-secondary cm-add" disabled={draft.length >= MAX_EVENTS}
                onClick={() => {
                  const id = slug("event");
                  setDraft((d) => [...d, { id, title: "", when: "", summary: "", image_url: "", video_id: "", keywords: "", enabled: true }]);
                  setOpen(id);
                }}>+ Add event</button>
        <SaveBar changed={changed} invalid={!!problem} busy={busy} error={changed ? problem : ""}
                 onUndo={() => setDraft(items.map((t) => ({ ...t })))} onSave={() => onSave(draft)} />
      </section>
      <aside className="admin-card-panel cm-panel cm-preview">
        <div className="cm-muted">Preview (as students see it)</div>
        <EventHighlightsCard card={{
          title: "Events at SRU",
          items: shown.map((e) => ({ ...e, video_url: e.video_id ? `https://www.youtube.com/watch?v=${e.video_id}` : "" })),
        }} />
      </aside>
    </div>
  );
}

// ------------------------------------------------------------------ videos
type VideoRow = { id: string; title: string; category: string; type: string; added: boolean; keywords?: string };

function VideosEditor({ adminKey, changes, busy, onSave }: {
  adminKey: string; changes: VideoChanges; busy: boolean; onSave: (v: VideoChanges) => void;
}) {
  const [builtin, setBuiltin] = useState<BuiltinVideo[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<VideoChanges>(changes);
  const [source, setSource] = useState(changes);
  if (source !== changes) {
    setSource(changes);
    setDraft(changes);
  }
  const [query, setQuery] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [form, setForm] = useState<AddedVideo>({ id: "", title: "", category: "Campus Life & Fests", type: "video", keywords: "" });

  useEffect(() => {
    fetchAdminVideos(adminKey)
      .then((r) => { setBuiltin(r.builtin); setTopics(r.topics); })
      .catch((e) => setError((e as Error).message));
  }, [adminKey]);

  const rows: VideoRow[] = useMemo(() => [
    ...draft.added.map((a) => ({ ...a, added: true })),
    ...builtin.map((v) => ({ id: v.id, title: v.title, category: v.category, type: v.type, added: false })),
  ], [builtin, draft.added]);
  const topicOf = (r: VideoRow) => draft.topics[r.id] || r.category;
  const hidden = new Set(draft.hidden);
  const q = query.trim().toLowerCase();
  const visible = rows.filter((r) => (!q || r.title.toLowerCase().includes(q)) && (!topicFilter || topicOf(r) === topicFilter));
  const counts = topics.map((t) => [t, rows.filter((r) => topicOf(r) === t && !hidden.has(r.id)).length] as const);

  const setTopic = (r: VideoRow, topic: string) =>
    setDraft((d) => {
      if (r.added) return { ...d, added: d.added.map((a) => (a.id === r.id ? { ...a, category: topic } : a)) };
      const t = { ...d.topics };
      if (topic === r.category) delete t[r.id]; else t[r.id] = topic;
      return { ...d, topics: t };
    });
  const setShown = (id: string, on: boolean) =>
    setDraft((d) => ({ ...d, hidden: on ? d.hidden.filter((x) => x !== id) : [...d.hidden, id] }));
  const id = ytId(form.id);
  const formProblem = !form.id ? "" : !/^[A-Za-z0-9_-]{11}$/.test(id) ? "Paste a YouTube link or its 11-character id."
    : rows.some((r) => r.id === id) ? "This video is already in the list." : !form.title.trim() ? "Add a title." : "";

  return (
    <div className="cm-grid single">
      <section className="admin-card-panel cm-panel">
        <h3 className="panel-headline">Official YouTube videos ({rows.length - hidden.size} shown)</h3>
        <p className="cm-muted">When a student asks about a topic, the chat picks 2 videos of that topic at random (and
          not ones already shown in that chat), so students see different videos. Add more official SRU videos to give
          it more to choose from.</p>
        {error && <p className="cm-error">{error}</p>}

        <div className="cm-topic-chips" aria-label="Videos per topic">
          <button type="button" className={!topicFilter ? "on" : ""} onClick={() => setTopicFilter("")}>All</button>
          {counts.map(([t, n]) => (
            <button key={t} type="button" className={topicFilter === t ? "on" : ""} onClick={() => setTopicFilter(t)}>
              {t} <span>{n}</span>
            </button>
          ))}
        </div>

        <details className="cm-addbox">
          <summary>+ Add a YouTube video</summary>
          <div className="cm-fields">
            <label className="wide">YouTube link<input value={form.id} placeholder="https://www.youtube.com/watch?v=…"
                                                       onChange={(e) => setForm({ ...form, id: e.target.value.trim() })} /></label>
            <label className="wide">Title<input value={form.title} maxLength={140} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            <label>Topic<select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {topics.map((t) => <option key={t}>{t}</option>)}</select></label>
            <label>Type<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value as "video" | "short" })}>
              <option value="video">Video</option><option value="short">Short</option></select></label>
            <label className="wide">Words students may use (optional)<input value={form.keywords} maxLength={200}
                                                                             placeholder="e.g. lumina, hostel night"
                                                                             onChange={(e) => setForm({ ...form, keywords: e.target.value })} /></label>
          </div>
          {formProblem && <p className="cm-error">{formProblem}</p>}
          <button type="button" className="admin-btn-secondary" disabled={!form.id || !!formProblem}
                  onClick={() => {
                    setDraft((d) => ({ ...d, added: [{ ...form, id }, ...d.added] }));
                    setForm({ id: "", title: "", category: form.category, type: "video", keywords: "" });
                  }}>Add to the list</button>
        </details>

        <input className="admin-input cm-search" type="search" placeholder="Search videos" value={query}
               onChange={(e) => setQuery(e.target.value)} aria-label="Search videos" />

        <div className="cm-videos">
          {visible.map((r) => (
            <div key={r.id} className={`cm-video ${hidden.has(r.id) ? "is-off" : ""}`}>
              <a href={r.type === "short" ? `https://www.youtube.com/shorts/${r.id}` : `https://www.youtube.com/watch?v=${r.id}`}
                 target="_blank" rel="noopener noreferrer" className="cm-video-thumb">
                <img src={`https://i.ytimg.com/vi/${r.id}/mqdefault.jpg`} alt="" loading="lazy" referrerPolicy="no-referrer" />
              </a>
              <div className="cm-video-body">
                <div className="cm-video-title">{r.title}{r.added && <span className="cm-badge">Added</span>}</div>
                <div className="cm-video-tools">
                  <select value={topicOf(r)} aria-label="Topic" onChange={(e) => setTopic(r, e.target.value)}>
                    {topics.map((t) => <option key={t}>{t}</option>)}
                  </select>
                  <label className="cm-switch">
                    <input type="checkbox" checked={!hidden.has(r.id)} onChange={(e) => setShown(r.id, e.target.checked)} />
                    <span>{hidden.has(r.id) ? "Hidden" : "Shown"}</span>
                  </label>
                  {r.added && (
                    <button type="button" className="cm-icon-btn danger"
                            onClick={() => setDraft((d) => ({ ...d, added: d.added.filter((a) => a.id !== r.id),
                                                              hidden: d.hidden.filter((x) => x !== r.id) }))}>Remove</button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {!visible.length && <p className="cm-muted">No videos match.</p>}
        </div>
        <SaveBar changed={!same(draft, changes)} invalid={false} busy={busy}
                 onUndo={() => setDraft(changes)} onSave={() => onSave(draft)} />
      </section>
    </div>
  );
}

// ------------------------------------------------------------------ ads
function AdsEditor({ items, seconds, busy, onSave }: {
  items: ChatAd[]; seconds: number; busy: boolean; onSave: (items: ChatAd[], seconds: number) => void;
}) {
  const { draft, setDraft, set, move, remove, changed } = useDraft(items);
  const [secs, setSecs] = useState(seconds);
  const [open, setOpen] = useState<string | null>(null);
  const problem = draft.find((a) => !a.title.trim()) ? "Every ad needs a highlight."
    : draft.find((a) => !isHttps(a.image_url) || !isHttps(a.link_url)) ? "Links must start with https://"
    : draft.find((a) => a.enabled !== false && !a.link_url.trim()) ? "An ad that is shown needs a button link." : "";
  const live = draft.filter((a) => a.enabled !== false && a.title.trim() && a.link_url.trim());

  return (
    <div className="cm-grid">
      <section className="admin-card-panel cm-panel">
        <h3 className="panel-headline">Ads ({draft.length}/{MAX_ADS})</h3>
        <p className="cm-muted">A small ad above the message box: a cover image, a highlight, a tag and a button. The
          ads that are shown take turns; a student can close them for the visit. Verified offers only.</p>
        <div className="cm-list">
          {draft.map((a, i) => (
            <div key={a.id} className={`cm-row ${a.enabled === false ? "is-off" : ""}`}>
              <button type="button" className="cm-row-head" aria-expanded={open === a.id}
                      onClick={() => setOpen(open === a.id ? null : a.id)}>
                <span className="cm-thumb">{a.image_url && isHttps(a.image_url) ? <img src={a.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" /> : null}</span>
                <span className="cm-row-name">
                  <strong>{a.title || "New ad"}</strong>
                  <small>{a.tag ? `${a.tag} · ` : ""}{a.cta_text || "Know more"}</small>
                </span>
                <span className="cm-chevron" aria-hidden="true">{open === a.id ? "▴" : "▾"}</span>
              </button>
              <RowTools i={i} n={draft.length} on={a.enabled !== false} onToggle={(v) => set(i, { enabled: v })}
                        onMove={(by) => move(i, by)} onRemove={() => remove(i)} />
              {open === a.id && (
                <div className="cm-fields">
                  <label className="wide">Highlight<input value={a.title} maxLength={70} placeholder="e.g. Admissions open for 2027-28"
                                                         onChange={(x) => set(i, { title: x.target.value })} /></label>
                  <label className="wide">Line under it (optional)<input value={a.subtitle} maxLength={90}
                                                                        onChange={(x) => set(i, { subtitle: x.target.value })} /></label>
                  <label>Tag (optional)<input value={a.tag} maxLength={18} placeholder="e.g. New"
                                              onChange={(x) => set(i, { tag: x.target.value })} /></label>
                  <label>Button text<input value={a.cta_text} maxLength={24} onChange={(x) => set(i, { cta_text: x.target.value })} /></label>
                  <label className="wide">Cover image link (https)<input value={a.image_url} maxLength={400}
                                                                        onChange={(x) => set(i, { image_url: x.target.value.trim() })} /></label>
                  <label className="wide">Button link (https)<input value={a.link_url} maxLength={400} placeholder="https://apply.sru.edu.in"
                                                                   onChange={(x) => set(i, { link_url: x.target.value.trim() })} /></label>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="cm-inline">
          <button type="button" className="admin-btn-secondary cm-add" disabled={draft.length >= MAX_ADS}
                  onClick={() => {
                    const id = slug("ad");
                    setDraft((d) => [...d, { id, title: "", subtitle: "", tag: "", image_url: "", cta_text: "Know more", link_url: "", enabled: false }]);
                    setOpen(id);
                  }}>+ Add ad</button>
          <label className="cm-secs">Each ad shows for
            <input type="number" min={4} max={60} value={secs} onChange={(e) => setSecs(Math.max(4, Math.min(60, Number(e.target.value) || 8)))} />
            seconds</label>
        </div>
        <SaveBar changed={changed || secs !== seconds} invalid={!!problem} busy={busy}
                 error={changed ? problem : ""} onUndo={() => { setDraft(items.map((t) => ({ ...t }))); setSecs(seconds); }}
                 onSave={() => onSave(draft, secs)} />
      </section>
      <aside className="admin-card-panel cm-panel cm-preview">
        <div className="cm-muted">Preview (as students see it)</div>
        <div className="cm-ad-frame">
          {live.length ? <ChatAdStrip preview={{ rotate_seconds: secs, items: live }} />
            : <p className="cm-muted">No ad is shown. Switch one on and add its link.</p>}
        </div>
      </aside>
    </div>
  );
}
