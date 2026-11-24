// v4.14.0: the events' photo cards in the chat, and the small ad at the bottom of the chat. Both are set in
// Admin -> Campus media. Text from the server is rendered as text (never as HTML); links must be https.
import { useEffect, useState } from "react";
import { fetchChatAds, type ChatAd } from "../services/api";
import "./CampusCards.css";

const safeUrl = (url?: string) => (typeof url === "string" && /^https:\/\//i.test(url) ? url : "");

type EventItem = { id: string; title: string; when?: string; summary?: string; image_url?: string; video_url?: string };

export function EventHighlightsCard({ card }: { card: any }) {
  const items: EventItem[] = Array.isArray(card?.items) ? card.items : [];
  if (!items.length) return null;
  const single = items.length === 1;
  return (
    <section className={`sru-events ${single ? "is-single" : ""}`} aria-label={card.title || "Events at SRU"}>
      {!single && <div className="sru-events-head">{card.title || "Events at SRU"}</div>}
      <div className="sru-events-row" role="list">
        {items.map((e) => {
          const img = safeUrl(e.image_url);
          const video = safeUrl(e.video_url);
          return (
            <article className="sru-event" role="listitem" key={e.id}>
              <div className="sru-event-img">
                {img ? (
                  <img src={img} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer"
                       onError={(ev) => { (ev.currentTarget as HTMLImageElement).style.visibility = "hidden"; }} />
                ) : null}
              </div>
              <div className="sru-event-body">
                <h4 className="sru-event-title">{e.title}</h4>
                {e.when && <div className="sru-event-when">{e.when}</div>}
                {e.summary && <p className="sru-event-summary">{e.summary}</p>}
                {video && (
                  <a className="sru-event-video" href={video} target="_blank" rel="noopener noreferrer">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>
                    Watch video
                  </a>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

const DISMISS_KEY = "sru_ads_dismissed";

/** The small ad above the message box. Shows the ads switched on in the admin panel, one at a time; the
 * student can close it for this visit. Renders nothing when there are no ads. */
export function ChatAdStrip({ preview }: { preview?: { rotate_seconds: number; items: ChatAd[] } }) {
  const [loaded, setLoaded] = useState<ChatAd[]>([]);
  const [loadedSeconds, setLoadedSeconds] = useState(8);
  const ads = preview ? preview.items : loaded;
  const seconds = preview ? preview.rotate_seconds || 8 : loadedSeconds;
  const [index, setIndex] = useState(0);
  const [closed, setClosed] = useState(() => {
    if (preview) return false;
    try { return sessionStorage.getItem(DISMISS_KEY) === "1"; } catch { return false; }
  });

  const isPreview = Boolean(preview);
  useEffect(() => {
    if (isPreview) return;
    let alive = true;
    fetchChatAds().then((res) => {
      if (!alive) return;
      setLoaded((res.items || []).filter((a) => safeUrl(a.link_url)));
      setLoadedSeconds(res.rotate_seconds || 8);
    }).catch(() => { /* no ads: nothing shown */ });
    return () => { alive = false; };
  }, [isPreview]);

  useEffect(() => {
    if (ads.length < 2) return;
    const reduce = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const t = window.setInterval(() => setIndex((i) => (i + 1) % ads.length), Math.max(4, seconds) * 1000);
    return () => window.clearInterval(t);
  }, [ads.length, seconds]);

  if (closed || !ads.length) return null;
  const ad = ads[index % ads.length];
  const img = safeUrl(ad.image_url);
  const link = safeUrl(ad.link_url);
  return (
    <div className="sru-ad" role="complementary" aria-label="From SR University">
      <a className="sru-ad-main" href={link || undefined} target="_blank" rel="noopener noreferrer">
        {img && <img className="sru-ad-img" src={img} alt="" loading="lazy" referrerPolicy="no-referrer" />}
        <span className="sru-ad-text">
          <span className="sru-ad-title">
            {ad.tag && <span className="sru-ad-tag">{ad.tag}</span>}
            {ad.title}
          </span>
          {ad.subtitle && <span className="sru-ad-sub">{ad.subtitle}</span>}
        </span>
        <span className="sru-ad-cta">{ad.cta_text || "Know more"}</span>
      </a>
      {ads.length > 1 && (
        <span className="sru-ad-dots" aria-hidden="true">
          {ads.map((a, i) => <span key={a.id} className={i === index % ads.length ? "on" : ""} />)}
        </span>
      )}
      {!preview && (
        <button type="button" className="sru-ad-close" aria-label="Close this ad"
                onClick={() => { setClosed(true); try { sessionStorage.setItem(DISMISS_KEY, "1"); } catch { /* */ } }}>
          ×
        </button>
      )}
    </div>
  );
}
