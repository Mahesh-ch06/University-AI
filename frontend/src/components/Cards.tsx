import { useState } from "react";
import type { FormEvent } from "react";
import { WELCOME_QUICK_ACTIONS } from "../data/welcomeQuickActions";
import {
  ScaleIcon,
  TargetIcon,
  BriefcaseIcon,
  FlaskIcon,
  SparklesIcon,
  RupeeIcon,
  AwardIcon,
  BookOpenIcon,
  BuildingIcon,
  FileTextIcon,
  BoltIcon,
  VideoIcon,
  BedIcon,
  ClockIcon,
  SruHostelIcon,
} from "./Icons";
import "./Cards.css";

interface CardProps {
  card: any;
}

export function ComparisonCard({ card }: CardProps) {
  const columns = card.columns || [];

  return (
    <div className="rich-card comparison-card">
      <div className="card-header">
        <span className="card-badge">
          <ScaleIcon size={14} /> Comparison
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      <div className="comparison-grid">
        {columns.map((col: any, idx: number) => (
          <div key={idx} className="comparison-col">
            <div className="col-header">
              <span className="col-badge">{col.badge}</span>
              <h5 className="col-name">{col.name}</h5>
            </div>
            <div className="col-section">
              <span className="section-label">
                <TargetIcon size={13} /> Focus:
              </span>
              <p>{col.focus}</p>
            </div>
            <div className="col-section">
              <span className="section-label">
                <BriefcaseIcon size={13} /> Career Paths:
              </span>
              <p>{col.careers}</p>
            </div>
            <div className="col-section">
              <span className="section-label">
                <FlaskIcon size={13} /> Specialized Labs:
              </span>
              <p>{col.labs}</p>
            </div>
            <div className="col-advantage">
              <span><SparklesIcon size={13} /> Key Edge:</span> {col.key_advantage}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FeeBreakdownCard({ card }: CardProps) {
  const items = card.items || [];

  return (
    <div className="rich-card fee-card">
      <div className="card-header">
        <span className="card-badge">
          <RupeeIcon size={14} /> Fee Structure
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      <div className="fee-table-wrapper">
        <table className="fee-table">
          <thead>
            <tr>
              <th>Fee Category</th>
              <th>Amount</th>
              <th>Frequency</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: any, idx: number) => (
              <tr key={idx}>
                <td className="fee-category-cell" data-label="Fee Category">{item.category}</td>
                <td className="fee-amount-cell" data-label="Amount">{item.amount}</td>
                <td className="fee-frequency-cell" data-label="Frequency">{item.frequency}</td>
                <td className="fee-note-cell" data-label="Details">{item.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {card.scholarship_note && (
        <div className="card-callout scholarship-callout">
          <span className="callout-icon">
            <AwardIcon size={15} />
          </span>
          <div>
            <strong>{card.note_label || (/scholarship|waiver/i.test(String(card.scholarship_note)) ? "Merit Scholarship Alert" : "Note")}:</strong>{" "}
            {card.scholarship_note}
          </div>
        </div>
      )}
    </div>
  );
}

export function CurriculumCard({ card }: CardProps) {
  const structure = card.structure || [];
  const [activeCategory, setActiveCategory] = useState<number>(0);

  return (
    <div className="rich-card curriculum-card">
      <div className="card-header">
        <span className="card-badge">
          <BookOpenIcon size={14} /> Curriculum
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      <div className="curriculum-tabs">
        {structure.map((cat: any, idx: number) => (
          <button
            key={idx}
            className={`curriculum-tab-btn ${activeCategory === idx ? "active" : ""}`}
            onClick={() => setActiveCategory(idx)}
          >
            {cat.category.split("(")[0].trim()}
            <span className="tab-credits">{cat.credits}</span>
          </button>
        ))}
      </div>
      <div className="curriculum-courses">
        <h5 className="category-title">
          {structure[activeCategory]?.category} —{" "}
          <span className="category-credits">{structure[activeCategory]?.credits}</span>
        </h5>
        <div className="course-badges-grid">
          {structure[activeCategory]?.courses?.map((course: string, cIdx: number) => (
            <div key={cIdx} className="course-pill">
              <span className="course-dot"></span>
              {course}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CampusTourCard({ card }: CardProps) {
  const spots = card.spots || [];

  return (
    <div className="rich-card campus-tour-card">
      <div className="card-header">
        <span className="card-badge">
          <BuildingIcon size={14} /> Campus Life
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      <div className="campus-spots-list">
        {spots.map((spot: any, idx: number) => (
          <div key={idx} className="campus-spot-item">
            <div className="spot-icon-wrapper">{spot.icon}</div>
            <div className="spot-info">
              <h5 className="spot-name">{spot.name}</h5>
              <p className="spot-desc">{spot.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProfileCard({ card }: CardProps) {
  const data = card.data || {};
  const isSuccess = data.status_color === "success";

  return (
    <div className="rich-card profile-card">
      <div className="card-header">
        <span className={`card-badge ${isSuccess ? "badge-success" : "badge-warning"}`}>
          {isSuccess ? (
            <>
              <AwardIcon size={14} /> Evaluation: Qualified
            </>
          ) : (
            <>
              <FileTextIcon size={14} /> Evaluation: Review
            </>
          )}
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      <div className="profile-grid">
        <div className="profile-field">
          <span className="field-label">Target Program</span>
          <span className="field-value">{data.degree} ({data.branch})</span>
        </div>
        <div className="profile-field">
          <span className="field-label">12th PCM Score</span>
          <span className="field-value font-mono">{data.score}</span>
        </div>
        <div className="profile-field full-width">
          <span className="field-label">Eligibility Status</span>
          <span className={`status-pill ${isSuccess ? "status-success" : "status-warning"}`}>
            {data.status}
          </span>
        </div>
        <div className="profile-field full-width next-steps-box">
          <span className="field-label">Roadmap & Next Steps</span>
          <p className="next-steps-text">{data.next_steps}</p>
        </div>
      </div>
    </div>
  );
}

const CATEGORY_COLOR_MAP: Record<string, string> = {
  "Campus Tour": "blue",
  "Hostels & Living": "purple",
  "Placements & Careers": "green",
  "Startups & Innovation (SRiX)": "orange",
  "CS, AI & Technology": "teal",
  "Sports & Activities": "red",
  "Testimonials & Reviews": "yellow",
};

function getCategoryColor(category: string | undefined): string {
  if (!category) return "grey";
  return CATEGORY_COLOR_MAP[category] ?? "grey";
}

export function VideoRecommendationsCard({ card }: { card: any }) {
  const videos = card.videos || [];
  const channelUrl = card.channel_url || "https://www.youtube.com/@SRUniversity/videos";
  const channelName = card.channel_name || "SR University Official";
  const videoCount = videos.length;

  if (!videoCount) return null;

  return (
    <div className="rich-card video-recommendations-card yt-red-border">
      <div className="video-card-header">
        <div className="video-card-header-left">
          <div>
            <div className="yt-header-title-row">
              <h4 className="video-card-title">{card.title || "Related University Videos"}</h4>
              {videoCount > 0 && (
                <span className="yt-count-pill">{videoCount} {videoCount === 1 ? "video" : "videos"}</span>
              )}
            </div>
            <span className="video-card-subtitle">Official videos from {channelName}</span>
          </div>
        </div>
        <div className="video-card-header-actions">
          <a
            href={channelUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="channel-link-btn yt-btn"
            title="Visit official YouTube channel"
          >
            <svg className="social-icon-svg" viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
              <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
            </svg>
            YouTube
          </a>
        </div>
      </div>

      <div className="yt-carousel-row">
        {videos.map((vid: any, idx: number) => {
          const isShort = vid.type === "short" || (typeof vid.url === "string" && vid.url.includes("/shorts/"));
          const categoryColor = getCategoryColor(vid.category);
          const isFirst = idx === 0;
          return (
            <a
              key={vid.id || idx}
              href={vid.url}
              target="_blank"
              rel="noopener noreferrer"
              className="yt-card-item"
              style={{ animationDelay: `${idx * 80}ms` } as React.CSSProperties}
            >
              <div className="yt-thumb-wrapper">
                <img
                  src={vid.thumbnail_url || `https://i.ytimg.com/vi/${vid.id}/hqdefault.jpg`}
                  alt={vid.title}
                  className="yt-thumb-img"
                  loading="eager"
                  decoding="async"
                  referrerPolicy="no-referrer"
                  onError={(e) => {
                    const img = e.currentTarget as HTMLImageElement;
                    if (!img.src.includes("mqdefault")) {
                      img.src = `https://i.ytimg.com/vi/${vid.id}/mqdefault.jpg`;
                    }
                  }}
                />

                {/* Central play button overlay — appears on hover */}
                <div className="yt-play-overlay" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="28" height="28" fill="#ef4444">
                    <path d="M8 5v14l11-7z"/>
                  </svg>
                </div>

                {/* "Watch" pill — slides up on hover, bottom-left */}
                <span className="yt-watch-pill">
                  <VideoIcon size={12} /> Watch
                </span>

                {/* "New" pill on first video, top-left */}
                {isFirst && <span className="yt-new-pill">New</span>}

                {isShort ? (
                  <span className="yt-duration-badge yt-short-badge">
                    <BoltIcon size={12} /> Shorts
                  </span>
                ) : vid.duration ? (
                  <span className="yt-duration-badge">{vid.duration}</span>
                ) : (
                  <span className="yt-duration-badge">
                    <VideoIcon size={12} /> Video
                  </span>
                )}
              </div>

              <div className="yt-card-details">
                <div className="yt-channel-avatar" title={vid.channel_name || "SR University"}>
                  <span>SRU</span>
                </div>

                <div className="yt-text-meta">
                  <h5 className="yt-video-title">{vid.title}</h5>
                  <div className="yt-submeta">
                    <span className="yt-channel-name">{vid.channel_name || "SR University"}</span>
                    {vid.category && (
                      <span className={`yt-category-tag yt-cat-${categoryColor}`}>{vid.category}</span>
                    )}
                  </div>
                </div>

                <div className="yt-card-action" title="Open media" onClick={(e) => e.preventDefault()}>
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                    <path d="M14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3m-2 16H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7z"/>
                  </svg>
                </div>
              </div>
            </a>
          );
        })}
      </div>

      <div className="video-card-footer">
        <a
          href={channelUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="more-videos-link yt-footer-link"
        >
          Watch more on @SRUniversity YouTube ↗
        </a>
      </div>
    </div>
  );
}

export function PlacementHighlightsCard({ card }: CardProps) {
  const superstars = card.superstars || [
    {
      name: "B. Shiva Krishna",
      role: "Software Engineer",
      company: "Microsoft",
      package: "51 LPA",
      stipend: "₹1.25L / month",
      batch: "Batch 2025",
      badge_color: "#10b981",
    },
    {
      name: "Kencha Bhavana",
      role: "Software Development Engineer",
      company: "Amazon",
      package: "46.38 LPA",
      stipend: "₹1.10L / month",
      batch: "Batch 2026",
      badge_color: "#0284c7",
    },
    {
      name: "Mohammed Akramuddin",
      role: "Associate Software Engineer",
      company: "ServiceNow",
      package: "49.30 LPA",
      stipend: "₹0.80L / month",
      batch: "Batch 2027",
      badge_color: "#6366f1",
    },
  ];

  const stats = card.stats || [
    { label: "Total Job Offers", value: "1,300+", note: "Till April and counting" },
    { label: "Paid Internships", value: "3,500+", note: "Stipends to ₹1.25L/mo" },
    { label: "Average CTC", value: "6 LPA", note: "Cohort Average" },
    { label: "Highest Stipend", value: "₹1.25L / mo", note: "Microsoft (Batch 2025)" },
    { label: "Top Recruiting MNCs", value: "80+", note: "Fortune 500 & tech leaders" },
    { label: "Placement Support", value: "100%", note: "One Student–One Job" },
  ];

  const topMncs = card.top_mnc_offers || [];
  const marqueeOffers = card.marquee_offers || [];

  return (
    <div className="rich-card placement-card">
      <div className="card-header placement-card-header">
        <span className="card-badge placement-badge">
          <AwardIcon size={14} /> Placement Excellence
        </span>
        <div className="card-header-titles">
          <h4 className="card-title">{card.title}</h4>
          {card.subtitle && <p className="card-subtitle">{card.subtitle}</p>}
        </div>
      </div>

      {/* Official 3 Superstars Banner Image */}
      <div className="placement-banner-wrapper">
        <img
          src={card.image_url || "/placements-three-years.png"}
          alt={card.image_alt || card.title}
          className="placement-banner-image"
          loading="eager"
          onClick={() => window.open(card.image_url || "/placements-three-years.png", "_blank")}
        />
        <div className="placement-banner-hint">
          <span>Click to view full resolution banner ↗</span>
        </div>
      </div>

      {/* 3 Consecutive Years Superstars Showcase */}
      <div className="superstars-showcase-grid">
        {superstars.map((star: any, idx: number) => (
          <div key={idx} className="superstar-card">
            <div className="superstar-top">
              <span className="superstar-batch-tag">{star.batch}</span>
              <span className="superstar-package-pill">{star.package}</span>
            </div>
            <h5 className="superstar-name">{star.name}</h5>
            <p className="superstar-role">{star.role}</p>
            <div className="superstar-company">
              <BriefcaseIcon size={13} />
              <span>Placed @ <strong>{star.company}</strong></span>
            </div>
            {star.stipend && (
              <div className="superstar-stipend">
                <span>Internship: <strong>{star.stipend}</strong></span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Key Milestone Stats (Non-repetitive university metrics) */}
      <div className="placement-stats-grid">
        {stats.map((s: any, idx: number) => (
          <div key={idx} className="placement-stat-box">
            <span className="stat-val">{s.value}</span>
            <span className="stat-lbl">{s.label}</span>
            {s.note && <span className="stat-sub">{s.note}</span>}
          </div>
        ))}
      </div>

      {/* Other Marquee Superstar Achievers */}
      {marqueeOffers.length > 0 && (
        <div className="placement-marquee-section">
          <h6 className="placement-mnc-title">
            <AwardIcon size={13} /> Other Marquee Superstar Achievers
          </h6>
          <div className="marquee-offers-grid">
            {marqueeOffers.map((m: any, idx: number) => (
              <div key={idx} className="marquee-offer-item">
                <div className="marquee-offer-main">
                  <span className="marquee-student-name">{m.student}</span>
                  <span className="marquee-batch-tag">{m.batch}</span>
                </div>
                <div className="marquee-offer-sub">
                  <span className="marquee-company-tag">
                    <BriefcaseIcon size={12} /> Placed @ <strong>{m.company}</strong>
                  </span>
                  <span className="marquee-package-tag">{m.package}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Recruiting MNCs Volume */}
      {topMncs.length > 0 && (
        <div className="placement-mnc-section">
          <h6 className="placement-mnc-title">
            <SparklesIcon size={13} /> Top MNC Hiring Volume
          </h6>
          <div className="placement-mnc-pills">
            {topMncs.map((m: any, idx: number) => (
              <span key={idx} className="mnc-offer-pill">
                <strong>{m.company}</strong>: {m.offers} offers
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SRU Advantage Comparison Card (Removed as per user request)
// ---------------------------------------------------------------------------

export function ProgramsOfferedCard(_props: CardProps) {
  return null;
}

export function cleanDisplayProgramName(name: string, specialization?: string): string {
  if (!name) return name;
  if (name.includes("(AIML,") || name.includes("Robotics and Automation, Quantum AI")) {
    if (specialization) {
      return `B.Tech CSE (${specialization})`;
    }
    return "B.Tech Computer Science & Engineering (CSE)";
  }
  return name;
}

export function AgentFeeCard({ card }: CardProps) {
  const d = card.data || {};
  const rawProgName = d.program_name || d.program || "Academic Program";
  const progName = cleanDisplayProgramName(rawProgName, d.specialization);
  const semTuition = d.net_tuition_per_sem ?? d.base_tuition_per_sem ?? (d.per_semester_after_scholarship || "—");
  const waiver = d.scholarship_percent || 0;
  const hasHostel = Boolean(d.has_hostel || (d.hostel && d.hostel.per_year));
  const hostelPerSem = d.hostel?.per_semester || (d.hostel?.per_year ? `₹${Math.round(parseInt(String(d.hostel.per_year).replace(/[^\d]/g, ""), 10) / 2).toLocaleString("en-IN")}` : null);
  // No built-in amounts: if the backend did not send a figure, show a dash, never a guess.
  const totalPerSem = d.total_per_semester || "—";
  const sem1Total = d.sem1_total_payable || "—";

  const handleWhatsApp = () => {
    const text = `Hello SR University Admissions! I received this fee calculation for ${progName} (${d.admission_year || "2027-28"}). Net Tuition: ${semTuition}/sem, Scholarship: ${waiver}%, Total/sem: ${totalPerSem} ${hasHostel ? "(including hostel)" : "(without hostel)"}. Please assist me with admissions.`;
    window.open(`https://wa.me/918331003030?text=${encodeURIComponent(text)}`, "_blank");
  };

  return (
    <div className="rich-card fee-card agent-fee-card">
      <div className="card-header">
        <span className="card-badge badge-success">
          <RupeeIcon size={14} /> Official 2027-28 Fee
        </span>
        <h4 className="card-title">{progName}</h4>
      </div>
      <div className="agent-fee-stats-grid">
        <div className="agent-fee-stat">
          <span className="agent-fee-stat-label">Net Tuition / Sem</span>
          <span className="agent-fee-stat-val bold-emerald">
            {typeof semTuition === "number" ? `₹${semTuition.toLocaleString("en-IN")}` : semTuition}
          </span>
          <span className="agent-fee-stat-sub">per semester tuition</span>
        </div>
        <div className="agent-fee-stat">
          <span className="agent-fee-stat-label">Merit Scholarship</span>
          <span className="agent-fee-stat-val bold-blue">{waiver > 0 ? `${waiver}% Waiver` : "Standard Slabs"}</span>
          <span className="agent-fee-stat-sub">official merit waiver</span>
        </div>
        {hasHostel ? (
          <>
            <div className="agent-fee-stat">
              <span className="agent-fee-stat-label">Hostel & Mess / Sem</span>
              <span className="agent-fee-stat-val bold-blue">{hostelPerSem}</span>
              <span className="agent-fee-stat-sub">{d.hostel?.type || "AC 4-Sharing"} (4 meals/day)</span>
            </div>
            <div className="agent-fee-stat">
              <span className="agent-fee-stat-label">Combined Total / Sem</span>
              <span className="agent-fee-stat-val bold-emerald">{totalPerSem}</span>
              <span className="agent-fee-stat-sub">Tuition + Other + Hostel</span>
            </div>
          </>
        ) : (
          <>
            <div className="agent-fee-stat">
              <span className="agent-fee-stat-label">Total / Sem (Academic)</span>
              <span className="agent-fee-stat-val bold-emerald">{totalPerSem}</span>
              <span className="agent-fee-stat-sub">Tuition + Other/Exam Fees</span>
            </div>
            <div className="agent-fee-stat">
              <span className="agent-fee-stat-label">1st Sem Total</span>
              <span className="agent-fee-stat-val">{sem1Total}</span>
              <span className="agent-fee-stat-sub">includes ₹5k enrollment</span>
            </div>
          </>
        )}
      </div>
      <div className="agent-card-footer">
        <span className="agent-card-source-tag">
          {hasHostel
            ? "🏠 Hostel & Dining included in total per semester."
            : "ℹ️ Hostel fee NOT included (separate & optional: ₹1.15L – ₹1.35L/yr)."}
        </span>
        <button type="button" className="agent-card-wa-btn" onClick={handleWhatsApp}>
          💬 WhatsApp Admissions
        </button>
      </div>
    </div>
  );
}


export function AgentCallbackCard({ card }: CardProps) {
  const d = card.data || {};
  return (
    <div className="rich-card agent-action-card callback-card">
      <div className="card-header">
        <span className="card-badge badge-success">
          ✓ Callback Requested
        </span>
        <h4 className="card-title">Admissions Counsellor Callback Requested</h4>
      </div>
      <div className="agent-action-body">
        <p className="agent-action-msg">
          Thank you, <strong>{d.name || "Student"}</strong>. An official SR University admissions counselor will contact you on your registered mobile (ending in <strong>•••{d.phone_last4 || "••••"}</strong>).
        </p>
        <div className="agent-action-meta">
          {d.preferred_time && <div><strong>Preferred Time:</strong> {d.preferred_time}</div>}
          <div><strong>Admissions Helpline:</strong> 833 100 3030</div>
        </div>
      </div>
    </div>
  );
}

export function AgentCampusVisitCard({ card }: CardProps) {
  const d = card?.data || {};
  if (d.status === "invalid" || d.status === "failed" || (!d.reference && !d.visit_date)) {
    return null;
  }

  let displayDate = d.visit_date || "Upcoming date";
  if (d.visit_date && /^\d{4}-\d{2}-\d{2}$/.test(d.visit_date)) {
    try {
      const [yr, mo, da] = d.visit_date.split("-").map((v: string) => parseInt(v, 10));
      const dateObj = new Date(yr, mo - 1, da);
      displayDate = dateObj.toLocaleDateString("en-IN", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {}
  }

  return (
    <div className="rich-card agent-action-card visit-card">
      <div className="card-header">
        <span className="card-badge badge-success">
          ✓ Visit Request Sent
        </span>
        <h4 className="card-title">Campus Visit Requested</h4>
      </div>
      <div className="agent-action-body">
        <p className="agent-action-msg">
          Visit requested for <strong>{displayDate}</strong> for <strong>{d.visitors || 1} visitor(s)</strong>. The
          admissions team will call you to confirm the time.
        </p>
        <div className="agent-action-meta">
          {d.name && <div><strong>Visitor:</strong> {d.name}</div>}
          <div><strong>Location:</strong> 170-Acre Lush Campus, Ananthasagar, Hasanparthy, Warangal, Telangana</div>
        </div>
        <div className="agent-card-footer">
          <span className="agent-card-source-tag">Visits are arranged and confirmed by the admissions team by phone.</span>
          <div className="visit-action-btns">
            <a
              href="https://maps.google.com/?q=SR+University+Warangal"
              target="_blank"
              rel="noopener noreferrer"
              className="agent-card-map-btn"
            >
              📍 Open in Google Maps
            </a>
            <a
              href="tel:8331003030"
              className="agent-card-call-btn"
            >
              📞 Call Admissions
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Campus visits are arranged by the admissions team; SRU Buddy never books or confirms one.
 * Shown for "campus_visit_contact", for the contacts tool, and in place of the old booking form
 * ("campus_visit_form") when an older chat is reopened. */
export function VisitContactCard({ card }: CardProps) {
  const d = card?.data?.campus_visit || card?.data || card || {};
  const campusVisitNum = "833 100 4040";
  const campusVisitClean = "8331004040";
  const whatsapp = `https://wa.me/91${campusVisitClean}?text=${encodeURIComponent(
    "Hi, I would like to visit the SR University campus."
  )}`;
  return (
    <div className="rich-card agent-action-card visit-contact-card">
      <div className="card-header">
        <span className="card-badge">Campus visit</span>
        <h4 className="card-title">{d.title || "Plan your visit with the admissions team"}</h4>
      </div>
      <div className="agent-action-body">
        <p className="agent-action-msg">
          {d.subtitle ||
            "Visits are arranged and confirmed by the SR University admissions team. Please contact them before you travel."}
        </p>
        <div className="agent-contacts-row">
          <a href={`tel:${campusVisitClean}`} className="agent-contact-pill">
            Call {campusVisitNum}
          </a>
          <a href={whatsapp} target="_blank" rel="noopener noreferrer" className="agent-contact-pill wa">
            WhatsApp {campusVisitNum}
          </a>
        </div>
        <div className="agent-action-meta">
          <div>
            <strong>Campus:</strong>{" "}
            {d.address || "SR University, Ananthasagar, Hasanparthy, Warangal Urban 506371, Telangana"}
          </div>
        </div>
        <div className="agent-card-footer">
          <a
            href="https://maps.google.com/?q=SR+University+Warangal"
            target="_blank"
            rel="noopener noreferrer"
            className="agent-card-map-btn"
          >
            Open in Google Maps
          </a>
          <a
            href={d.visit_page || "https://sru.edu.in/visit-us"}
            target="_blank"
            rel="noopener noreferrer"
            className="agent-card-call-btn"
          >
            Visit Us page
          </a>
        </div>
      </div>
    </div>
  );
}

/** A student's wish to visit, passed to the admissions team as a callback request (not a booking). */
export function VisitRequestCard({ card }: CardProps) {
  const d = card?.data || {};
  if (d.status !== "saved") return null;
  return (
    <div className="rich-card agent-action-card visit-card">
      <div className="card-header">
        <span className="card-badge badge-success">Request passed on</span>
        <h4 className="card-title">Campus visit: the admissions team will call you</h4>
      </div>
      <div className="agent-action-body">
        <p className="agent-action-msg">
          This is not a booking. The admissions team will call <strong>{d.name || "you"}</strong> on the number
          ending <strong>{d.phone_last4 || "••••"}</strong> to arrange the visit and confirm the day and time.
        </p>
        <div className="agent-action-meta">
          {d.preferred_date && (
            <div>
              <strong>Day you mentioned:</strong> {d.preferred_date} (not confirmed)
            </div>
          )}
          <div>
            <strong>Campus Visit:</strong> 833 100 4040 (call or WhatsApp)
          </div>
        </div>
      </div>
    </div>
  );
}

type FacultyPerson = {
  name: string;
  position?: string;
  designation?: string;
  department?: string;
  qualification?: string;
  experience_years?: number;
  research_areas?: string;
  profile_url?: string;
};

function FacultyPersonRow({ p }: { p: FacultyPerson }) {
  return (
    <li className="faculty-row">
      <div className="faculty-row-main">
        <a href={p.profile_url} target="_blank" rel="noopener noreferrer" className="faculty-row-name">
          {p.name}
        </a>
        <span className="faculty-row-position">{p.position}</span>
      </div>
      <div className="faculty-row-meta">
        {[p.department, p.qualification, p.experience_years ? `${p.experience_years} years' experience` : ""]
          .filter(Boolean)
          .join(" · ")}
      </div>
      {p.research_areas && <div className="faculty-row-research">Research: {p.research_areas}</div>}
    </li>
  );
}

/** Official faculty profiles (sru.edu.in/faculty) found by the find_faculty tool. */
export function FacultyCard({ card }: CardProps) {
  const d = card?.data || {};
  if (d.status !== "ok") return null;
  const people: FacultyPerson[] = (d.faculty || [...(d.leaders || []), ...(d.some_senior_faculty || [])] || d.deans || []).slice(0, 5);
  const listed = d.faculty_listed as number | undefined;
  const title =
    d.kind === "department"
      ? `Faculty: ${d.department}`
      : d.kind === "overview"
        ? "SR University faculty"
        : d.kind === "leaders"
          ? "Deans and heads"
          : "Faculty profiles";
  return (
    <div className="rich-card faculty-card-agent">
      <div className="card-header">
        <span className="card-badge">Official faculty profiles</span>
        <h4 className="card-title">{title}</h4>
      </div>
      {listed !== undefined && (
        <p className="faculty-summary">
          {listed} faculty listed
          {d.with_phd_listed !== undefined ? ` · ${d.with_phd_listed} with a Ph.D.` : ""}
          {d.professors !== undefined
            ? ` · ${d.professors} Professors, ${d.associate_professors} Associate, ${d.assistant_professors} Assistant`
            : ""}
        </p>
      )}
      {d.kind === "overview" && d.by_school && (
        <ul className="faculty-school-list">
          {Object.entries(d.by_school as Record<string, number>).map(([school, n]) => (
            <li key={school}>
              {school}: <strong>{n}</strong>
            </li>
          ))}
        </ul>
      )}
      <ul className="faculty-list">
        {(people.length ? people : (d.deans as FacultyPerson[]) || []).slice(0, 5).map((p) => (
          <FacultyPersonRow key={p.profile_url || p.name} p={p} />
        ))}
      </ul>
      <div className="agent-card-footer">
        <span className="agent-card-source-tag">
          Source: sru.edu.in/faculty{d.as_of ? ` (as of ${d.as_of})` : ""}
        </span>
        <a href={d.source || "https://sru.edu.in/faculty/"} target="_blank" rel="noopener noreferrer" className="agent-card-call-btn">
          Full directory
        </a>
      </div>
    </div>
  );
}

export function AgentContactLinksCard({ card }: CardProps) {
  const d = card.data || {};
  if (d.campus_visit) return <VisitContactCard card={card} />;
  const admissionsNum = "833 100 3030";
  const admissionsClean = "8331003030";
  const rawWa = d.whatsapp || "";
  const whatsappUrl = rawWa
    ? rawWa.replace(/wa\.me\/(?:\+?91)?\d+/g, `wa.me/91${admissionsClean}`)
    : `https://wa.me/91${admissionsClean}?text=${encodeURIComponent("Hi, I have a question about SR University admissions.")}`;

  return (
    <div className="rich-card agent-action-card contact-card">
      <div className="card-header">
        <span className="card-badge">
          📞 Direct Contacts
        </span>
        <h4 className="card-title">SR University Admissions Office</h4>
      </div>
      <div className="agent-contacts-row">
        <a href={`tel:${admissionsClean}`} className="agent-contact-pill">
          📞 Call {admissionsNum}
        </a>
        <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="agent-contact-pill wa">
          💬 WhatsApp Us
        </a>
        {d.apply_online && (
          <a href={d.apply_online} target="_blank" rel="noopener noreferrer" className="agent-contact-pill primary">
            📝 Apply Online 2027-28
          </a>
        )}
      </div>
    </div>
  );
}

export function ApplicationAdCard({ card }: CardProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) {
    return null;
  }

  const d = card.data || card;
  const sponsorName = d.sponsor_name || "SR University Admissions";
  const sponsorLogo = d.sponsor_logo || "/sru-logo.png";
  const title = d.title || "Early Bird: 50% Off Online Application";
  const description =
    d.description ||
    "Apply early for 2027-28 admissions & save 50% on application fee (₹550 instead of ₹1,100).";
  const ctaText = d.cta_text || "Apply Now ↗";
  const ctaUrl = d.cta_url || "https://apply.sru.edu.in";
  const imageUrl = d.image_url || "/early-bird-offer.png";
  const introText = d.intro_text;

  return (
    <div className="application-ad-container">
      {introText && <div className="application-ad-intro">{introText}</div>}
      <div className="application-ad-card">
        <div className="application-ad-thumb-col">
          <img
            src={imageUrl}
            alt={title}
            className="application-ad-thumb-img"
            onError={(e) => {
              (e.target as HTMLImageElement).src = "/sru-logo.png";
            }}
          />
        </div>
        <div className="application-ad-content-col">
          <div className="application-ad-header-row">
            <div className="application-ad-sponsor-info">
              <img src={sponsorLogo} alt="Sponsor" className="application-ad-sponsor-icon" />
              <span className="application-ad-sponsor-name">{sponsorName}</span>
            </div>
            <div className="application-ad-header-right">
              <span className="application-ad-pill">Ad</span>
              <button
                type="button"
                className="application-ad-remove-btn"
                onClick={() => setDismissed(true)}
                title="Remove ad"
                aria-label="Remove ad"
              >
                ✕
              </button>
            </div>
          </div>
          <h4 className="application-ad-title">{title}</h4>
          <p className="application-ad-desc">{description}</p>
          <div className="application-ad-footer-row">
            <a
              href={ctaUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="application-ad-cta-link"
            >
              {ctaText}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SchoolSelectionCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const schools = card.schools || [];
  return (
    <div className="rich-card school-selection-card">
      <div className="card-header">
        <span className="card-badge">
          <BookOpenIcon size={14} /> Academic Areas
        </span>
        <h4 className="card-title">{card.title || "Select Academic School"}</h4>
        {card.subtitle && <p className="card-subtitle">{card.subtitle}</p>}
      </div>

      <div className="school-selection-grid">
        {schools.map((s: any, idx: number) => (
          <button
            key={idx}
            type="button"
            className="school-card-choice-btn"
            onClick={() => onSelect?.(s.name)}
          >
            <div className="school-card-choice-icon">{s.icon}</div>
            <div className="school-card-choice-content">
              <div className="school-card-choice-title">{s.name}</div>
              {s.highlight && <div className="school-card-choice-desc">{s.highlight}</div>}
            </div>
            <div className="school-card-choice-arrow">→</div>
          </button>
        ))}
      </div>

      <div className="school-card-manual-hint">
        <span>Can't find your programme?</span>
        <button
          type="button"
          className="school-manual-btn"
          onClick={() => onSelect?.("Type manual course")}
        >
          Type your course manually
        </button>
      </div>
    </div>
  );
}

export function CourseSelectionCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const isUgOnly = card.level === "ug";
  const isPgOnly = card.level === "pg";
  const ugProgs = isPgOnly ? [] : (card.programs_ug || []);
  const pgProgs = isUgOnly ? [] : (card.programs_pg || []);

  return (
    <div className="rich-card course-selection-card">
      <div className="card-header">
        <span className="card-badge">
          <span>{card.icon || "🎓"}</span> {card.school_name || "Academic School"}
        </span>
        <h4 className="card-title">{card.title || "Offered Programmes"}</h4>
        {card.subtitle && <p className="card-subtitle">{card.subtitle}</p>}
      </div>

      {ugProgs.length > 0 && (
        <div className="course-group-section">
          <div className="course-group-label">Undergraduate Degrees (UG)</div>
          <div className="course-pills-grid">
            {ugProgs.map((prog: any, idx: number) => (
              <button
                key={idx}
                type="button"
                className="course-choice-pill"
                onClick={() => onSelect?.(prog.name)}
              >
                <span className="course-choice-name">{prog.name}</span>
                <span className="course-choice-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {pgProgs.length > 0 && (
        <div className="course-group-section">
          <div className="course-group-label">Postgraduate Degrees (PG)</div>
          <div className="course-pills-grid">
            {pgProgs.map((prog: any, idx: number) => (
              <button
                key={idx}
                type="button"
                className="course-choice-pill"
                onClick={() => onSelect?.(prog.name)}
              >
                <span className="course-choice-name">{prog.name}</span>
                <span className="course-choice-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="course-card-actions">
        <button
          type="button"
          className="course-back-btn"
          onClick={() => onSelect?.("Change school")}
        >
          ← Change School
        </button>
      </div>
    </div>
  );
}

export function DetailedFeeStructureCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [activeTab, setActiveTab] = useState<"tuition" | "hostel" | "other">("tuition");

  return (
    <div className="rich-card detailed-fee-card">
      <div className="card-header">
        <div className="fee-card-badge-row">
          <span className="card-badge">
            <RupeeIcon size={14} /> Verified Fee Breakdown
          </span>
          <span className="academic-year-badge">{card.academic_year || "2027-28"}</span>
        </div>
        <h4 className="card-title">{cleanDisplayProgramName(card.title || card.program_name || "", card.specialization)}</h4>
        <p className="card-subtitle">{card.school_name}</p>
      </div>

      {/* Tabs */}
      <div className="fee-card-tabs" role="tablist">
        <button
          type="button"
          className={`fee-card-tab-btn ${activeTab === "tuition" ? "active" : ""}`}
          onClick={() => setActiveTab("tuition")}
        >
          Tuition & Academic
        </button>
        <button
          type="button"
          className={`fee-card-tab-btn ${activeTab === "hostel" ? "active" : ""}`}
          onClick={() => setActiveTab("hostel")}
        >
          Hostel & Living
        </button>
        <button
          type="button"
          className={`fee-card-tab-btn ${activeTab === "other" ? "active" : ""}`}
          onClick={() => setActiveTab("other")}
        >
          Transport & Deposits
        </button>
      </div>

      {activeTab === "tuition" && (
        <div className="fee-tab-pane">
          <div className="fee-breakdown-row highlight">
            <span className="fee-row-label">Annual Tuition Fee</span>
            <span className="fee-row-value">{card.tuition?.formatted_annual}</span>
          </div>
          <div className="fee-breakdown-row sub">
            <span className="fee-row-label">Per Semester Tuition</span>
            <span className="fee-row-value">{card.tuition?.formatted_semester}</span>
          </div>

          <div className="fee-section-divider">One-Time & Academic Charges</div>
          {(card.one_time_charges || []).map((c: any, i: number) => (
            <div key={i} className="fee-breakdown-row">
              <span className="fee-row-label">{c.label}</span>
              <span className="fee-row-value">{c.formatted}</span>
            </div>
          ))}
          {(card.annual_academic_charges || []).map((c: any, i: number) => (
            <div key={i} className="fee-breakdown-row">
              <span className="fee-row-label">{c.label}</span>
              <span className="fee-row-value">{c.formatted}</span>
            </div>
          ))}

          <div className="fee-total-box">
            <div className="fee-total-label">Total First Year Academic:</div>
            <div className="fee-total-amount">{card.formatted_first_year_academic}</div>
          </div>
        </div>
      )}

      {activeTab === "hostel" && (
        <div className="fee-tab-pane">
          <div className="hostel-options-grid">
            {(card.hostel_options || []).map((h: any, i: number) => (
              <div key={i} className="hostel-option-card">
                <div className="hostel-option-title">{h.type}</div>
                <div className="hostel-option-price">{h.formatted} <span className="per-yr">/yr</span></div>
              </div>
            ))}
          </div>
          <div className="dining-highlight-box">
            <SparklesIcon size={14} />
            <span>{card.dining_info || "Central multi-cuisine mess included in residential fee with 4,000-seat central dining facility."}</span>
          </div>
        </div>
      )}

      {activeTab === "other" && (
        <div className="fee-tab-pane">
          <div className="fee-breakdown-row">
            <span className="fee-row-label">Tri-Cities Bus Transport (Annual)</span>
            <span className="fee-row-value">{card.formatted_transport || "₹30,000"}</span>
          </div>
          {(card.hostel_deposits || []).map((d: any, i: number) => (
            <div key={i} className="fee-breakdown-row">
              <span className="fee-row-label">{d.label}</span>
              <span className="fee-row-value">{d.formatted}</span>
            </div>
          ))}
        </div>
      )}

      {/* Card Action CTAs */}
      <div className="fee-card-actions-row">
        <button
          type="button"
          className="fee-action-primary-btn"
          onClick={() => onSelect?.("Calculate scholarship for my marks")}
        >
          <AwardIcon size={14} /> Calculate Scholarship
        </button>
        <button
          type="button"
          className="fee-action-secondary-btn"
          onClick={() => onSelect?.("Change school / programme")}
        >
          Change Course
        </button>
      </div>
    </div>
  );
}

export function HostelFacilitiesCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const roomTypes = card.room_types || [];
  const amenities = card.amenities || [];
  const rules = card.rules_summary || [];

  return (
    <div className="rich-card hostel-facilities-card">
      <div className="card-header">
        <span className="card-badge hostel-badge">
          <SruHostelIcon size={14} /> Campus Hostels
        </span>
        <h4 className="card-title">{card.title || "SR University Residential Living & Campus Hostels"}</h4>
        {card.subtitle && <p className="card-subtitle">{card.subtitle}</p>}
      </div>

      {/* Room Configurations */}
      <div className="hostel-section">
        <div className="hostel-section-title">
          <BedIcon size={14} /> Room Types & Sharing
        </div>
        <div className="hostel-rooms-grid">
          {roomTypes.map((r: any, idx: number) => (
            <div key={idx} className="hostel-room-item">
              <span className="room-type-badge">{r.name}</span>
              <p className="room-amenities-text">{r.amenities}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Key Living Amenities */}
      <div className="hostel-section">
        <div className="hostel-section-title">
          <SparklesIcon size={14} /> Campus Amenities & Facilities
        </div>
        <div className="hostel-amenities-grid">
          {amenities.map((a: any, idx: number) => (
            <div key={idx} className="hostel-amenity-card">
              <div className="amenity-title">
                <span className="amenity-bullet">•</span> {a.title}
              </div>
              <div className="amenity-desc">{a.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Discipline & Curfew Highlights */}
      {rules.length > 0 && (
        <div className="hostel-section">
          <div className="hostel-section-title">
            <ClockIcon size={14} /> Timings & Discipline Guidelines
          </div>
          <div className="hostel-rules-box">
            {rules.map((rule: string, idx: number) => (
              <div key={idx} className="hostel-rule-row">
                <span className="rule-check">✓</span>
                <span>{rule}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Quick Inquiries */}
      <div className="hostel-action-buttons">
        <button
          type="button"
          className="hostel-action-btn fee-btn"
          onClick={() => onSelect?.("Hostel fee breakdown")}
        >
          <RupeeIcon size={13} /> View Room & Mess Fees
        </button>
        <button
          type="button"
          className="hostel-action-btn"
          onClick={() => onSelect?.("Tell me about mess food and timings")}
        >
          Mess Menu & Timings
        </button>
        <button
          type="button"
          className="hostel-action-btn"
          onClick={() => onSelect?.("What are the hostel rules and curfew?")}
        >
          Curfew & Rules
        </button>
      </div>
    </div>
  );
}

export function FeeScholarshipFormCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const isPg = card.level === "pg";
  const rawPrograms = card.programs || [
    { key: "btech_cse", name: "B.Tech Computer Science & Engineering (CSE)", level: "ug", annual_tuition: 340000 },
    { key: "btech_ai_robotics", name: "B.Tech in Artificial Intelligence & Robotics", level: "ug", annual_tuition: 400000 },
    { key: "btech_ece", name: "B.Tech Electronics & Communication (ECE)", level: "ug", annual_tuition: 270000 },
    { key: "btech_mech", name: "B.Tech Mechanical Engineering", level: "ug", annual_tuition: 200000 },
    { key: "btech_civil", name: "B.Tech Civil Engineering", level: "ug", annual_tuition: 200000 },
    { key: "btech_eee", name: "B.Tech Electrical & Electronics (EEE)", level: "ug", annual_tuition: 200000 },
    { key: "bsc_agri", name: "B.Sc (Hons.) Agriculture (ICAR Accredited)", level: "ug", annual_tuition: 200000 },
    { key: "bba", name: "BBA (Bachelor of Business Administration)", level: "ug", annual_tuition: 150000 },
    { key: "bca", name: "BCA (Bachelor of Computer Applications)", level: "ug", annual_tuition: 150000 },
    { key: "bdes", name: "B.Des (School of Design)", level: "ug", annual_tuition: 210000 },
    { key: "bcom", name: "B.Com (Bachelor of Commerce)", level: "ug", annual_tuition: 100000 },
    { key: "mba", name: "MBA (Master of Business Administration)", level: "pg", annual_tuition: 300000 },
    { key: "mca", name: "MCA (Master of Computer Applications)", level: "pg", annual_tuition: 150000 },
    { key: "mtech", name: "M.Tech CSE", level: "pg", annual_tuition: 100000 },
  ];

  // Filter programs strictly: if only_selected, keep only selected. Else scope strictly to level.
  const filtered = card.only_selected && card.selected_program
    ? rawPrograms.filter((p: any) => p.key === card.selected_program)
    : (isPg ? rawPrograms.filter((p: any) => p.level === "pg") : rawPrograms.filter((p: any) => p.level !== "pg"));

  const programs = filtered.length > 0 ? filtered : rawPrograms;

  const boards = card.boards || (isPg ? [
    { key: "degree_university", label: "Recognised University / College", slab_key: "pg" },
  ] : [
    { key: "ts_state_board", label: "Telangana State Board (BIE TS)", slab_key: "state_board" },
    { key: "ap_state_board", label: "Andhra Pradesh State Board (BIE AP)", slab_key: "state_board" },
    { key: "cbse", label: "CBSE (Central Board)", slab_key: "cbse" },
    { key: "icse", label: "ICSE / ISC (CISCE)", slab_key: "cbse" },
    { key: "other_state_board", label: "Other State Boards (All Over India)", slab_key: "state_board" },
    { key: "nios", label: "NIOS / National Open School", slab_key: "cbse" },
    { key: "ib", label: "International Baccalaureate (IB)", slab_key: "ib" },
  ]);

  const [selectedProgKey, setSelectedProgKey] = useState<string>(card.selected_program || programs[0]?.key || "btech_cse");
  const [selectedBoardKey, setSelectedBoardKey] = useState<string>(card.selected_board || boards[0]?.key || "ts_state_board");
  const [scoreInput, setScoreInput] = useState<string>("");
  const [rankInput, setRankInput] = useState<string>("");
  const [activeScoreType, setActiveScoreType] = useState<"marks" | "eapcet" | "jee">("marks");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const selectedProg = programs.find((p: any) => p.key === selectedProgKey) || programs[0];
  const selectedBoard = boards.find((b: any) => b.key === selectedBoardKey) || boards[0];
  const isEngineeringOrAgri = !isPg && (selectedProgKey.startsWith("btech_") || selectedProgKey === "bsc_agri");
  const isSingleLockedProg = Boolean(card.only_selected || programs.length === 1);

  // Calculate live scholarship slab
  const getScholarshipPct = (): number => {
    const isCbseFamily = selectedBoard.slab_key === "cbse";
    if (activeScoreType === "marks" && scoreInput) {
      const raw = parseFloat(scoreInput.replace(/[^\d.]/g, ""));
      const pct = raw > 100 && raw <= 1000 ? raw / 10 : raw;
      if (pct >= (isCbseFamily ? 95 : 98)) return 40;
      if (pct >= (isCbseFamily ? 90 : 92)) return 30;
      if (pct >= 80) return 25;
      if (pct >= 70) return 20;
      if (pct >= 65) return 15;
      if (pct >= 60) return 10;
    } else if (activeScoreType === "jee" && scoreInput) {
      const p = parseFloat(scoreInput.replace(/[^\d.]/g, ""));
      if (p >= 95) return 40;
      if (p >= 90) return 30;
      if (p >= 80) return 25;
      if (p >= 70) return 20;
      if (p >= 60) return 15;
      if (p >= 50) return 10;
    } else if (activeScoreType === "eapcet" && rankInput) {
      const r = parseInt(rankInput.replace(/[^\d]/g, ""), 10);
      if (r >= 1 && r <= 2000) return 40;
      if (r > 2000 && r <= 8000) return 30;
      if (r > 8000 && r <= 20000) return 25;
    }
    return 0;
  };

  const previewWaiver = getScholarshipPct();
  const baseTuition = selectedProg?.annual_tuition || 340000;
  const netTuition = Math.round(baseTuition * (1 - previewWaiver / 100));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!scoreInput.trim() && !rankInput.trim()) {
      setErrorMsg(isPg ? "Please enter your qualifying degree marks (%)." : "Please enter your marks (%) or entrance rank.");
      return;
    }
    setErrorMsg(null);
    let prompt = `Calculate fee for ${selectedProg.name}`;
    if (!isPg && selectedBoard?.label) {
      prompt += `, ${selectedBoard.label}`;
    }
    if (scoreInput.trim()) {
      prompt += ` with ${scoreInput.trim()}% marks`;
    }
    if (rankInput.trim() && !isPg) {
      prompt += activeScoreType === "jee" ? ` and JEE Main ${rankInput.trim()} percentile` : ` and EAPCET rank ${rankInput.trim()}`;
    }
    onSelect?.(prompt);
  };

  return (
    <div className="rich-card fee-scholarship-form-card">
      <div className="card-header">
        <span className="card-badge">
          <AwardIcon size={14} /> Fee & Scholarship Assessment
        </span>
        <h4 className="card-title">{card.title || "Fee & Merit Scholarship Assessment Form"}</h4>
        <p className="card-subtitle">
          {card.subtitle || (isPg
            ? "Enter your qualifying degree marks to calculate your postgraduate fee and scholarship."
            : "Select your course and 10+2 board, then enter your marks or rank to calculate your exact net fee.")}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="fee-form-body">
        {/* Step 1: Course Selection */}
        <div className="fee-form-group">
          <label className="fee-form-label">
            <span className="step-num-pill">1</span> {isSingleLockedProg ? "Selected Programme" : (isPg ? "Postgraduate Programme" : "Intended Course / Programme")}
          </label>
          {isSingleLockedProg ? (
            <div className="fee-form-selected-badge">
              <span className="selected-course-icon">🎓</span>
              <div className="selected-course-details">
                <span className="selected-course-name">{selectedProg.name}</span>
                <span className="selected-course-fee">Annual Tuition: ₹{(selectedProg.annual_tuition || 340000).toLocaleString("en-IN")}</span>
              </div>
            </div>
          ) : (
            <select
              className="fee-form-select"
              value={selectedProgKey}
              onChange={(e) => setSelectedProgKey(e.target.value)}
            >
              {programs.map((p: any) => (
                <option key={p.key} value={p.key}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Step 2: Board / University Selection */}
        <div className="fee-form-group">
          <label className="fee-form-label">
            <span className="step-num-pill">2</span> {isPg ? "Qualifying Degree Board / University" : "10+2 / Intermediate Board (All Over India)"}
          </label>
          <select
            className="fee-form-select"
            value={selectedBoardKey}
            onChange={(e) => setSelectedBoardKey(e.target.value)}
          >
            {boards.map((b: any) => (
              <option key={b.key} value={b.key}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        {/* Step 3: Marks / Rank Input */}
        <div className="fee-form-group">
          <label className="fee-form-label">
            <span className="step-num-pill">3</span> {isPg ? "Qualifying Degree Percentage (%)" : "Marks or Entrance Rank"}
          </label>
          {isEngineeringOrAgri && (
            <div className="score-type-tabs">
              <button
                type="button"
                className={`score-type-btn ${activeScoreType === "marks" ? "active" : ""}`}
                onClick={() => setActiveScoreType("marks")}
              >
                10+2 Marks (%)
              </button>
              <button
                type="button"
                className={`score-type-btn ${activeScoreType === "eapcet" ? "active" : ""}`}
                onClick={() => setActiveScoreType("eapcet")}
              >
                TG/AP EAPCET Rank
              </button>
              <button
                type="button"
                className={`score-type-btn ${activeScoreType === "jee" ? "active" : ""}`}
                onClick={() => setActiveScoreType("jee")}
              >
                JEE Main %ile
              </button>
            </div>
          )}

          {activeScoreType === "marks" && (
            <div className="fee-input-wrap">
              <input
                type="text"
                className="fee-form-input"
                placeholder={isPg ? "Enter qualifying degree marks (e.g. 75% or 80%)" : "Enter 10+2 marks (e.g. 88% or 880/1000)"}
                value={scoreInput}
                onChange={(e) => {
                  setScoreInput(e.target.value);
                  setErrorMsg(null);
                }}
              />
            </div>
          )}

          {activeScoreType === "eapcet" && !isPg && (
            <div className="fee-input-wrap">
              <input
                type="text"
                className="fee-form-input"
                placeholder="Enter TG / AP EAPCET Rank (e.g. 12500)"
                value={rankInput}
                onChange={(e) => {
                  setRankInput(e.target.value);
                  setErrorMsg(null);
                }}
              />
            </div>
          )}

          {activeScoreType === "jee" && !isPg && (
            <div className="fee-input-wrap">
              <input
                type="text"
                className="fee-form-input"
                placeholder="Enter JEE Main Percentile (e.g. 91.5)"
                value={scoreInput}
                onChange={(e) => {
                  setScoreInput(e.target.value);
                  setErrorMsg(null);
                }}
              />
            </div>
          )}

          {errorMsg && <div className="fee-form-error">{errorMsg}</div>}
        </div>

        {/* Live Scholarship Preview */}
        {previewWaiver > 0 && (
          <div className="fee-form-live-preview">
            <div className="preview-badge">
              <SparklesIcon size={13} /> {previewWaiver}% Merit Scholarship Qualified!
            </div>
            <div className="preview-amounts">
              <span>Net Annual Tuition:</span>
              <strong>₹{netTuition.toLocaleString("en-IN")}</strong>
              <small>(₹{Math.round(netTuition / 2).toLocaleString("en-IN")}/sem)</small>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="fee-form-actions">
          <button type="submit" className="fee-form-submit-btn">
            Calculate Fee & Scholarship →
          </button>
        </div>
      </form>
    </div>
  );
}

/**
 * Deduplicates cards so the user is never shown duplicate cards (e.g. multiple video cards or repeated contact cards).
 */
export function deduplicateCards(cards: any[] | undefined | null): any[] {
  if (!cards || !Array.isArray(cards) || cards.length <= 1) return cards || [];
  const result: any[] = [];
  const seenCategories = new Set<string>();

  for (const card of cards) {
    if (!card) continue;
    const type = card.type || "";
    let category = type;
    if (type === "get_university_videos" || type === "video_recommendations") {
      category = "video_recommendations";
    } else if (type === "campus_visit_contact" || type === "get_contact_and_apply_links") {
      category = `contact_${Boolean(card.data?.campus_visit)}`;
    } else if (type === "calculate_fee" || type === "fee_breakdown") {
      category = "fee_card";
    }

    if (seenCategories.has(category)) {
      continue;
    }
    seenCategories.add(category);
    result.push(card);
  }
  return result;
}

export type AcademicFormPayload = {
  mode: "eligibility" | "scholarship";
  program?: string | null;
  board_key?: string | null;
  academic_stage?: string | null;
  raw_marks?: number | null;
  max_marks?: number | null;
  stream?: string | null;
  show_stream?: boolean;
  show_entrance?: boolean;
  entrance_type?: string | null;
  entrance_value?: number | null;
};

/**
 * One form for the academic details an admission journey needs: board -> current status -> marks
 * (+ 10+2 group, + optional entrance score). Values already shared in this chat are pre-filled.
 * Submitting sends the details as structured data; the agent validates and evaluates them.
 */
export function AcademicDetailsFormCard({
  card,
  onSelect,
}: {
  card: any;
  onSelect?: (text: string, form?: AcademicFormPayload) => void;
}) {
  const v = card.values || {};
  const boards: { key: string; label: string }[] = card.boards || [];
  const stages: { key: string; label: string }[] = card.stages || [];
  const streams: { key: string; label: string }[] = card.streams || [];
  const entrances: { key: string; label: string }[] = card.entrances || [];
  const maxTable: Record<string, Record<string, number>> = card.max_marks_table || {};

  const [board, setBoard] = useState<string | null>(v.board_key || null);
  const [stage, setStage] = useState<string | null>(v.academic_stage || null);
  const [raw, setRaw] = useState<string>(v.raw_marks != null ? String(Number(v.raw_marks)) : "");
  const [maxMarks, setMaxMarks] = useState<string>(v.max_marks != null ? String(Number(v.max_marks)) : "");
  const [maxTouched, setMaxTouched] = useState<boolean>(v.max_marks != null);
  const [stream, setStream] = useState<string | null>(v.stream || null);
  const [entrance, setEntrance] = useState<string>(v.entrance_type || "none");
  const [entranceValue, setEntranceValue] = useState<string>(v.entrance_value != null ? String(v.entrance_value) : "");
  const [submitted, setSubmitted] = useState(false);

  const isIb = board === "ib";
  // The usual total for the chosen board and status, unless the student typed their own.
  const suggestedMax = board && stage ? maxTable[board]?.[stage] : undefined;
  const effectiveMax = maxTouched ? maxMarks : suggestedMax ? String(suggestedMax) : maxMarks;

  const rawNum = raw.trim() === "" ? NaN : Number(raw);
  const maxNum = isIb ? 45 : effectiveMax.trim() === "" ? NaN : Number(effectiveMax);
  const entranceNum = entranceValue.trim() === "" ? NaN : Number(entranceValue);

  const problems: string[] = [];
  if (!board) problems.push("Select your education board");
  if (!stage) problems.push("Select your current academic status");
  if (!Number.isFinite(rawNum) || rawNum <= 0) problems.push(isIb ? "Enter your IB points" : "Enter your marks");
  else if (!Number.isFinite(maxNum) || maxNum <= 0) problems.push("Enter the total marks");
  else if (rawNum > maxNum) problems.push("Marks cannot be more than the total");
  if (card.show_stream && !stream) problems.push("Select your 10+2 group");
  if (card.show_entrance && entrance !== "none") {
    if (!Number.isFinite(entranceNum)) problems.push("Enter your entrance score, or choose 'No entrance score'");
    else if (entrance === "jee_main" && (entranceNum < 0 || entranceNum > 100)) problems.push("JEE Main percentile must be 0 to 100");
    else if (entrance !== "jee_main" && (entranceNum < 1 || !Number.isInteger(entranceNum))) problems.push("EAPCET rank must be a whole number");
  }
  const valid = problems.length === 0;
  const percent = Number.isFinite(rawNum) && Number.isFinite(maxNum) && maxNum > 0 && !isIb ? (rawNum / maxNum) * 100 : null;

  const boardLabel = boards.find((b) => b.key === board)?.label;
  const stageLabel = stages.find((s) => s.key === stage)?.label;
  const marksLabel =
    stage === "1st_year" || stage === "2nd_year"
      ? "Your Intermediate 1st-year marks (used for a preliminary estimate)"
      : isIb
        ? "Your IB Diploma points"
        : "Your final Intermediate / Class 12 marks";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid || submitted) return;
    const marksText = isIb ? `${rawNum}/45 IB points` : `${rawNum}/${maxNum}`;
    const parts = [boardLabel, stageLabel, marksText, card.show_stream ? stream : null];
    if (card.show_entrance && entrance !== "none") {
      parts.push(entrance === "jee_main" ? `JEE Main ${entranceNum} percentile` : `${entrance === "ap_eapcet" ? "AP" : "TG"} EAPCET rank ${entranceNum}`);
    }
    const summary = `My details: ${parts.filter(Boolean).join(", ")}`;
    setSubmitted(true);
    onSelect?.(summary, {
      mode: card.mode === "scholarship" ? "scholarship" : "eligibility",
      program: card.program || null,
      board_key: board,
      academic_stage: stage,
      raw_marks: rawNum,
      max_marks: maxNum,
      stream: stream,
      show_stream: Boolean(card.show_stream),
      show_entrance: Boolean(card.show_entrance),
      entrance_type: card.show_entrance ? entrance : null,
      entrance_value: card.show_entrance && entrance !== "none" ? entranceNum : null,
    });
  };

  return (
    <div className="rich-card counsellor-card acad-form-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <BookOpenIcon size={13} /> {card.program_name ? `${card.program_name} · ` : ""}Academic details
        </span>
        <h4 className="card-title counsellor-title">{card.title || "Your academic details"}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>

      {card.saved_summary && !submitted && (
        <button
          type="button"
          className="acad-saved-btn"
          onClick={() => onSelect?.(`Use my saved details (${card.saved_summary})`)}
        >
          Use my saved details ({card.saved_summary})
        </button>
      )}

      {submitted ? (
        <div className="acad-submitted" aria-live="polite">
          <span className="acad-submitted-tick" aria-hidden="true">✓</span>
          <span className="acad-submitted-text">
            {boardLabel} · {stageLabel} · {isIb ? `${rawNum}/45 points` : `${rawNum}/${maxNum}`}
            {card.show_stream && stream ? ` · ${stream}` : ""}
            {card.show_entrance && entrance !== "none" && Number.isFinite(entranceNum)
              ? ` · ${entrance === "jee_main" ? `JEE ${entranceNum} percentile` : `EAPCET rank ${entranceNum}`}`
              : ""}
          </span>
          <button type="button" className="acad-edit-btn" onClick={() => setSubmitted(false)}>
            Edit details
          </button>
        </div>
      ) : (
      <form className="acad-form" onSubmit={handleSubmit} noValidate>
        <fieldset className="acad-field" disabled={submitted}>
          <legend className="acad-legend"><span className="acad-num">1</span> Education board</legend>
          <div className="counsellor-options-grid">
            {boards.map((b) => (
              <button
                key={b.key}
                type="button"
                aria-pressed={board === b.key}
                className={`counsellor-opt-btn ${board === b.key ? "selected" : ""}`}
                onClick={() => setBoard(b.key)}
              >
                <span className="counsellor-opt-label">{b.label}</span>
                {board === b.key && <span className="counsellor-check">✓</span>}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="acad-field" disabled={submitted}>
          <legend className="acad-legend"><span className="acad-num">2</span> Current academic status</legend>
          <div className="acad-stage-list">
            {stages.map((st) => (
              <button
                key={st.key}
                type="button"
                aria-pressed={stage === st.key}
                className={`counsellor-opt-btn acad-stage-btn ${stage === st.key ? "selected" : ""}`}
                onClick={() => setStage(st.key)}
              >
                <span className="counsellor-opt-label">{st.label}</span>
                {stage === st.key && <span className="counsellor-check">✓</span>}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="acad-field" disabled={submitted}>
          <legend className="acad-legend"><span className="acad-num">3</span> Marks</legend>
          <label className="acad-help" htmlFor={`acad-raw-${card.mode}`}>{marksLabel}</label>
          <div className="acad-marks-row">
            <input
              id={`acad-raw-${card.mode}`}
              className="counsellor-marks-input-field acad-input"
              type="number"
              inputMode="decimal"
              min={0}
              step="any"
              placeholder={isIb ? "e.g. 36" : "Marks obtained"}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
            />
            {!isIb && (
              <>
                <span className="acad-outof">out of</span>
                <input
                  aria-label="Total marks"
                  className="counsellor-marks-input-field acad-input acad-input-max"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  placeholder="Total"
                  value={effectiveMax}
                  onChange={(e) => {
                    setMaxTouched(true);
                    setMaxMarks(e.target.value);
                  }}
                />
              </>
            )}
            {isIb && <span className="acad-outof">out of 45</span>}
          </div>
        </fieldset>

        {card.show_stream && (
          <fieldset className="acad-field" disabled={submitted}>
            <legend className="acad-legend"><span className="acad-num">4</span> 10+2 / Intermediate group</legend>
            <div className="acad-stage-list">
              {streams.map((st) => (
                <button
                  key={st.key}
                  type="button"
                  aria-pressed={stream === st.key}
                  className={`counsellor-opt-btn acad-stage-btn ${stream === st.key ? "selected" : ""}`}
                  onClick={() => setStream(st.key)}
                >
                  <span className="counsellor-opt-label">{st.label}</span>
                  {stream === st.key && <span className="counsellor-check">✓</span>}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {card.show_entrance && (
          <fieldset className="acad-field" disabled={submitted}>
            <legend className="acad-legend">
              <span className="acad-num">{card.show_stream ? 5 : 4}</span> Entrance score <span className="acad-optional">(optional)</span>
            </legend>
            <div className="acad-marks-row">
              <select
                aria-label="Entrance exam"
                className="counsellor-marks-input-field acad-input acad-select"
                value={entrance}
                onChange={(e) => setEntrance(e.target.value)}
              >
                {entrances.map((en) => (
                  <option key={en.key} value={en.key}>{en.label}</option>
                ))}
              </select>
              {entrance !== "none" && (
                <input
                  aria-label={entrance === "jee_main" ? "JEE Main percentile" : "EAPCET rank"}
                  className="counsellor-marks-input-field acad-input acad-input-max"
                  type="number"
                  inputMode="decimal"
                  placeholder={entrance === "jee_main" ? "Percentile" : "Rank"}
                  value={entranceValue}
                  onChange={(e) => setEntranceValue(e.target.value)}
                />
              )}
            </div>
          </fieldset>
        )}

        <div className="acad-review" aria-live="polite">
          {valid ? (
            <span>
              {boardLabel} · {stageLabel} · {isIb ? `${rawNum}/45 points` : `${rawNum}/${maxNum}`}
              {percent !== null ? ` (${Math.round(percent * 100) / 100}%)` : ""}
              {card.show_stream && stream ? ` · ${stream}` : ""}
            </span>
          ) : (
            <span className="acad-todo">{problems[0]}</span>
          )}
        </div>

        <button type="submit" className="counsellor-submit-btn acad-submit" disabled={!valid}>
          {card.submit_label || "Submit"}
        </button>
      </form>
      )}
    </div>
  );
}

export function CounsellorBoardCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [selected, setSelected] = useState<string | null>(card.selected_board || null);
  const options = card.options || [];

  const handleSelect = (opt: any) => {
    setSelected(opt.key);
    if (onSelect) {
      onSelect(opt.label);
    }
  };

  return (
    <div className="rich-card counsellor-card counsellor-board-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <BookOpenIcon size={13} /> Step 1: Schooling / Board
        </span>
        <h4 className="card-title counsellor-title">{card.title}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>
      <div className="counsellor-options-grid">
        {options.map((opt: any) => (
          <button
            key={opt.key}
            type="button"
            className={`counsellor-opt-btn ${selected === opt.key ? "selected" : ""} ${selected && selected !== opt.key ? "dimmed" : ""}`}
            onClick={() => handleSelect(opt)}
          >
            <div className="counsellor-opt-content">
              <span className="counsellor-opt-code">{opt.code || opt.short}</span>
              <span className="counsellor-opt-label">{opt.label}</span>
            </div>
            {selected === opt.key && <span className="counsellor-check">✓</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export function CounsellorStageCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [selected, setSelected] = useState<string | null>(card.selected_stage || null);
  const options = card.options || [];

  const handleSelect = (opt: any) => {
    setSelected(opt.key);
    if (onSelect) {
      onSelect(opt.label);
    }
  };

  return (
    <div className="rich-card counsellor-card counsellor-stage-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <TargetIcon size={13} /> Step 2: Academic Stage
        </span>
        <h4 className="card-title counsellor-title">{card.title}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>
      <div className="counsellor-stage-list">
        {options.map((opt: any) => (
          <button
            key={opt.key}
            type="button"
            className={`counsellor-stage-btn ${selected === opt.key ? "selected" : ""} ${selected && selected !== opt.key ? "dimmed" : ""}`}
            onClick={() => handleSelect(opt)}
          >
            <div className="counsellor-stage-info">
              <span className="counsellor-stage-label">{opt.label}</span>
              <span className="counsellor-stage-desc">{opt.desc}</span>
            </div>
            {selected === opt.key ? <span className="counsellor-check">✓</span> : <span className="counsellor-arrow">→</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export function CounsellorMarksCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [val, setVal] = useState<string>(card.default_val ? String(card.default_val) : "");
  const [submitted, setSubmitted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const maxMarks = card.max_marks || 1000;
  const isPercentage = maxMarks <= 100;

  const handleSubmit = (marksVal?: number) => {
    if (submitted) return;
    const num = marksVal !== undefined ? marksVal : parseFloat(val.replace(/[^\d.]/g, ""));
    if (isNaN(num) || num <= 0) {
      setError(`Please enter a valid score (between 1 and ${maxMarks}).`);
      return;
    }
    if (num > maxMarks) {
      setError(`Entered score exceeds the maximum marks (${maxMarks}).`);
      return;
    }
    setError(null);
    setSubmitted(true);
    if (onSelect) {
      if (isPercentage) {
        onSelect(`${num}%`);
      } else {
        onSelect(`${num} out of ${maxMarks}`);
      }
    }
  };

  const quickMarks = isPercentage
    ? [80, 88, 92, 96]
    : [Math.round(maxMarks * 0.85), Math.round(maxMarks * 0.92), Math.round(maxMarks * 0.96)];

  return (
    <div className="rich-card counsellor-card counsellor-marks-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <AwardIcon size={13} /> {card.step_label || "Step 3: Academic Marks"}
        </span>
        <h4 className="card-title counsellor-title">{card.title}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>

      <div className="counsellor-marks-body">
        <div className="counsellor-input-row">
          <div className="counsellor-input-wrapper">
            <input
              type="number"
              className={`counsellor-marks-input-field ${error ? "error" : ""}`}
              placeholder={card.placeholder || (isPercentage ? "e.g. 88" : `e.g. ${Math.round(maxMarks * 0.88)}`)}
              value={val}
              onChange={(e) => {
                setVal(e.target.value);
                if (error) setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
              }}
              disabled={submitted}
              autoFocus
            />
            <span className="counsellor-marks-unit">{isPercentage ? "%" : `/ ${maxMarks}`}</span>
          </div>
          <button
            type="button"
            className="counsellor-submit-btn"
            onClick={() => handleSubmit()}
            disabled={submitted || !val.trim()}
          >
            {submitted ? "Submitted ✓" : "Continue →"}
          </button>
        </div>

        {error && <div className="counsellor-inline-error">{error}</div>}

        {!submitted && (
          <div className="counsellor-benchmarks">
            <span className="counsellor-benchmarks-title">Quick select:</span>
            <div className="counsellor-benchmarks-chips">
              {quickMarks.map((qm) => (
                <button
                  key={qm}
                  type="button"
                  className="counsellor-benchmark-chip"
                  onClick={() => {
                    setVal(String(qm));
                    handleSubmit(qm);
                  }}
                >
                  {isPercentage ? `${qm}%` : `${qm} / ${maxMarks}`}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function CounsellorRouteCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [selected, setSelected] = useState<string | null>(card.selected_route || null);
  const options = card.options || [];

  const handleSelect = (opt: any) => {
    setSelected(opt.key);
    if (onSelect) {
      onSelect(opt.label);
    }
  };

  return (
    <div className="rich-card counsellor-card counsellor-route-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <SparklesIcon size={13} /> {card.step_label || "Step 5: Admission Route"}
        </span>
        <h4 className="card-title counsellor-title">{card.title}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>
      <div className="counsellor-route-grid">
        {options.map((opt: any) => (
          <button
            key={opt.key}
            type="button"
            className={`counsellor-route-btn ${selected === opt.key ? "selected" : ""} ${selected && selected !== opt.key ? "dimmed" : ""}`}
            onClick={() => handleSelect(opt)}
          >
            <div className="counsellor-route-info">
              <span className="counsellor-route-label">{opt.label}</span>
              <span className="counsellor-route-desc">{opt.desc}</span>
            </div>
            {selected === opt.key && <span className="counsellor-check">✓</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export function CounsellorProgramCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [selected, setSelected] = useState<string | null>(card.selected_program || null);
  const programs = card.programs || [];

  const handleSelect = (prog: any) => {
    setSelected(prog.key);
    if (onSelect) {
      onSelect(prog.name);
    }
  };

  return (
    <div className="rich-card counsellor-card counsellor-program-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <RupeeIcon size={13} /> {card.step_label || "Preferred Programme"}
        </span>
        <h4 className="card-title counsellor-title">{card.title}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>
      <div className="counsellor-prog-list">
        {programs.map((prog: any) => (
          <button
            key={prog.key}
            type="button"
            className={`counsellor-prog-btn ${selected === prog.key ? "selected" : ""} ${selected && selected !== prog.key ? "dimmed" : ""}`}
            onClick={() => handleSelect(prog)}
          >
            <div className="counsellor-prog-main">
              <span className="counsellor-prog-name">{prog.name}</span>
              <span className="counsellor-prog-fee">{prog.annual_tuition}/year</span>
            </div>
            {selected === prog.key ? <span className="counsellor-check">✓</span> : <span className="counsellor-arrow">→</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export function WelcomeActionsCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);

  const items = card.items || WELCOME_QUICK_ACTIONS;

  const handleClick = (prompt: string) => {
    setSelectedPrompt(prompt);
    onSelect?.(prompt);
  };

  const renderIcon = (iconName: string) => {
    switch (iconName) {
      case "graduation-cap":
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
            <path d="M6 12v5c3 3 9 3 12 0v-5" />
          </svg>
        );
      case "calculator":
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="4" y="2" width="16" height="20" rx="2" />
            <line x1="8" y1="6" x2="16" y2="6" />
            <line x1="16" y1="14" x2="16" y2="18" />
            <path d="M16 10h.01M12 10h.01M8 10h.01M12 14h.01M8 14h.01M12 18h.01M8 18h.01" />
          </svg>
        );
      case "wallet":
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="5" width="20" height="14" rx="2" />
            <line x1="2" y1="10" x2="22" y2="10" />
          </svg>
        );
      case "briefcase":
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="7" width="20" height="14" rx="2" />
            <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
            <line x1="2" y1="13" x2="22" y2="13" />
          </svg>
        );
      case "send":
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        );
      case "building":
      default:
        return (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="21" x2="21" y2="21" />
            <line x1="6" y1="21" x2="6" y2="11" />
            <line x1="10" y1="21" x2="10" y2="11" />
            <line x1="14" y1="21" x2="14" y2="11" />
            <line x1="18" y1="21" x2="18" y2="11" />
            <polygon points="12 3 2 8 22 8 12 3" />
          </svg>
        );
    }
  };

  return (
    <div className="welcome-actions-card-wrapper">
      {card.heading && <div className="welcome-actions-heading">{card.heading}</div>}
      <div className="welcome-actions-grid">
        {items.map((item: any) => {
          const isSelected = selectedPrompt === item.prompt;
          const isDimmed = Boolean(selectedPrompt && !isSelected);
          return (
            <button
              key={item.id || item.title}
              type="button"
              className={`welcome-action-tile tile-${item.color || "blue"} ${isSelected ? "selected" : ""} ${isDimmed ? "dimmed" : ""}`}
              onClick={() => handleClick(item.prompt)}
            >
              <div className="welcome-action-top">
                <div className={`welcome-action-icon-box icon-box-${item.color || "blue"}`}>
                  {renderIcon(item.icon)}
                </div>
                {item.badge && <span className={`welcome-action-badge badge-${item.color || "blue"}`}>{item.badge}</span>}
              </div>
              <div className="welcome-action-info">
                <span className="welcome-action-title">{item.title}</span>
                <span className="welcome-action-subtitle">{item.subtitle}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function RenderCard({ card, onSelect }: { card: any; onSelect?: (text: string, form?: AcademicFormPayload) => void }) {
  if (!card || !card.type) return null;

  switch (card.type) {
    case "session_recovery":
      // Replaced by the welcome-back panel (components/WelcomeBackPanel.tsx); this card was only ever
      // created in the browser, so nothing saved needs it.
      return null;
    case "welcome_actions":
      return <WelcomeActionsCard card={card} onSelect={onSelect} />;
    case "academic_details_form":
      return <AcademicDetailsFormCard card={card} onSelect={onSelect} />;
    case "counsellor_board_selection":
      return <CounsellorBoardCard card={card} onSelect={onSelect} />;
    case "counsellor_stage_selection":
      return <CounsellorStageCard card={card} onSelect={onSelect} />;
    case "counsellor_marks_input":
      return <CounsellorMarksCard card={card} onSelect={onSelect} />;
    case "counsellor_route_selection":
      return <CounsellorRouteCard card={card} onSelect={onSelect} />;
    case "counsellor_program_selection":
      return <CounsellorProgramCard card={card} onSelect={onSelect} />;
    case "fee_scholarship_form":
      return <FeeScholarshipFormCard card={card} onSelect={onSelect} />;
    case "school_selection":
      return <SchoolSelectionCard card={card} onSelect={onSelect} />;
    case "course_selection":
      return <CourseSelectionCard card={card} onSelect={onSelect} />;
    case "fee_structure_detailed":
      return <DetailedFeeStructureCard card={card} onSelect={onSelect} />;
    case "comparison":
      return <ComparisonCard card={card} />;
    case "fee_breakdown":
      return <FeeBreakdownCard card={card} />;
    case "hostel_facilities":
      return <HostelFacilitiesCard card={card} onSelect={onSelect} />;
    case "calculate_fee":
      return <AgentFeeCard card={card} />;
    case "request_counsellor_callback":
      return <AgentCallbackCard card={card} />;
    case "book_campus_visit": // older chats only
      return <AgentCampusVisitCard card={card} />;
    case "request_campus_visit_callback":
      return <VisitRequestCard card={card} />;
    case "campus_visit_form": // older chats: the booking form is gone (visits are never booked here)
    case "campus_visit_contact":
      return <VisitContactCard card={card} />;
    case "find_faculty":
      return <FacultyCard card={card} />;
    case "get_contact_and_apply_links":
      return <AgentContactLinksCard card={card} />;
    case "get_university_videos":
      return <VideoRecommendationsCard card={card.data?.videos ? card.data : card} />;
    case "curriculum":
      return <CurriculumCard card={card} />;
    case "campus_tour":
      return <CampusTourCard card={card} />;
    case "profile":
      return <ProfileCard card={card} />;
    case "video_recommendations":
      return <VideoRecommendationsCard card={card} />;
    case "placement_highlights":
      return <PlacementHighlightsCard card={card} />;
    case "sru_comparison":
    case "programs_offered":
      return null;
    case "application_ad":
    case "ad":
      return <ApplicationAdCard card={card} />;
    default:
      return null;
  }
}


