// Admin -> Agent -> Quick Start tiles (v4.13.0): the tiles under the opening welcome message, edited here and
// used by the chat from the next page load. No code change or redeploy needed.
import { useState } from "react";
import type { WelcomeTile } from "../../services/api";
import { WelcomeActionsCard } from "../Cards";
import { WELCOME_TILE_ICONS } from "../../data/welcomeTileIcons";
import { WelcomeTileIcon } from "../WelcomeTileIcon";

const MAX_TILES = 8;

function newId(): string {
  return `tile-${Date.now().toString(36)}`.slice(0, 24);
}

export function WelcomeTilesEditor({
  tiles,
  busy,
  onSave,
}: {
  tiles: WelcomeTile[];
  busy: boolean;
  onSave: (tiles: WelcomeTile[]) => void;
}) {
  const [draft, setDraft] = useState<WelcomeTile[]>(() => tiles.map((t) => ({ ...t })));
  const [source, setSource] = useState<WelcomeTile[]>(tiles);
  // A new saved list from the server (after Save) replaces the draft.
  if (source !== tiles) {
    setSource(tiles);
    setDraft(tiles.map((t) => ({ ...t })));
  }
  const changed = JSON.stringify(draft) !== JSON.stringify(tiles);
  const invalid = draft.some((t) => !t.title.trim() || !t.prompt.trim());

  const set = (i: number, patch: Partial<WelcomeTile>) =>
    setDraft((d) => d.map((t, j) => (j === i ? { ...t, ...patch } : t)));
  const move = (i: number, by: number) =>
    setDraft((d) => {
      const j = i + by;
      if (j < 0 || j >= d.length) return d;
      const next = [...d];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });

  const shown = draft.filter((t) => t.enabled !== false && t.title.trim() && t.prompt.trim());

  return (
    <div className="agc-tiles">
      <div className="agc-setting-title">Quick Start tiles</div>
      <p className="agc-muted">
        The buttons under the opening welcome message, in this order (up to {MAX_TILES}). "Message" is what the chat
        receives when a student taps the tile. Use only verified facts in badges.
      </p>

      <div className="agc-tiles-list">
        {draft.map((t, i) => (
          <div key={t.id} className={`agc-tile-row ${t.enabled === false ? "is-off" : ""}`}>
            <div className="agc-tile-row-head">
              <span className="agc-tile-icon"><WelcomeTileIcon name={t.icon} /></span>
              <strong>{t.title || "New tile"}</strong>
              <label className="agc-tile-toggle">
                <input type="checkbox" checked={t.enabled !== false} onChange={(e) => set(i, { enabled: e.target.checked })} />
                Shown
              </label>
              <span className="agc-tile-order">
                <button type="button" aria-label="Move up" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
                <button type="button" aria-label="Move down" disabled={i === draft.length - 1} onClick={() => move(i, 1)}>↓</button>
                <button type="button" aria-label="Remove tile" className="agc-tile-remove"
                        onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}>Remove</button>
              </span>
            </div>
            <div className="agc-tile-fields">
              <label>
                Title
                <input value={t.title} maxLength={32} onChange={(e) => set(i, { title: e.target.value })} />
              </label>
              <label>
                Badge (optional)
                <input value={t.badge} maxLength={16} placeholder="e.g. Up to 40% off"
                       onChange={(e) => set(i, { badge: e.target.value })} />
              </label>
              <label>
                Icon
                <select value={t.icon} onChange={(e) => set(i, { icon: e.target.value })}>
                  {WELCOME_TILE_ICONS.map((name) => <option key={name} value={name}>{name}</option>)}
                </select>
              </label>
              <label className="agc-tile-wide">
                Message sent when tapped
                <input value={t.prompt} maxLength={120} placeholder="e.g. Why should I choose SR University?"
                       onChange={(e) => set(i, { prompt: e.target.value })} />
              </label>
              <label>
                Tooltip (optional)
                <input value={t.subtitle || ""} maxLength={48} onChange={(e) => set(i, { subtitle: e.target.value })} />
              </label>
            </div>
          </div>
        ))}
      </div>

      <div className="agc-tiles-actions">
        <button
          type="button"
          className="admin-btn-secondary"
          disabled={draft.length >= MAX_TILES}
          onClick={() => setDraft((d) => [...d, { id: newId(), title: "", badge: "", icon: "building", prompt: "", subtitle: "", enabled: true }])}
        >
          + Add tile
        </button>
        <button type="button" className="admin-btn-secondary" disabled={!changed} onClick={() => setDraft(tiles.map((t) => ({ ...t })))}>
          Undo changes
        </button>
        <button type="button" className="admin-btn-primary" disabled={busy || !changed || invalid} onClick={() => onSave(draft)}>
          Save tiles
        </button>
        {invalid && <span className="agc-error">Every tile needs a title and a message.</span>}
      </div>

      <div className="agc-tiles-preview" aria-label="Preview">
        <div className="agc-muted">Preview (as students see it)</div>
        <div className="agc-tiles-preview-frame">
          <WelcomeActionsCard card={{ heading: "⚡ Quick start", items: shown }} />
        </div>
      </div>
    </div>
  );
}
