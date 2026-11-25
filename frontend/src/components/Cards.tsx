import { useEffect, useState } from "react";
import { EventHighlightsCard } from "./CampusCards";
import type { FormEvent } from "react";
import { WELCOME_QUICK_ACTIONS } from "../data/welcomeQuickActions";
import { WelcomeTileIcon } from "./WelcomeTileIcon";
import { fetchWelcomeActions } from "../services/api";
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
  BedIcon,
  ClockIcon,
  SruHostelIcon,
} from "./Icons";
import { ConcessionFeeCard, ConcessionsCard, FeePlanCard, FeeSummaryCard } from "./FeePlanCards";
import { AgentPlanCard, CounsellorConnectCard } from "./AgentCards";
import "./Cards.css";
import { SemesterFeeTable } from "./SemesterFeeTable";
import "./ChatCards.css";

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
  const hasSemesters = Array.isArray(card.semesters) && card.semesters.length > 0;

  return (
    <div className="rich-card fee-card">
      <div className="card-header">
        <span className="card-badge">
          <RupeeIcon size={14} /> Fee Structure
        </span>
        <h4 className="card-title">{card.title}</h4>
      </div>
      {hasSemesters ? (
        <>
          {card.first_year_total && (
            <div className="afc-hero">
              <div className="afc-hero-main">
                <span className="afc-hero-label">First-year payable</span>
                <span className="afc-hero-amount">{card.first_year_total}</span>
              </div>
            </div>
          )}
          <SemesterFeeTable semesters={card.semesters} />
        </>
      ) : (
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
      )}
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

// v4.15.1: the channel's repeated "| SR University | Best Private University…" tail is left out of the title.
function cleanVideoTitle(title: string): string {
  const parts = (title || "").split("|").map((p) => p.trim()).filter(Boolean);
  const boiler = /(sr\s*university|\bsru\b|private\s+university|best\s+university|university\s+in|top\s+private|no\.?\s*1)/i;
  const keep = parts.filter((p, i) => i === 0 || !boiler.test(p));
  return (keep.slice(0, 2).join(" · ") || title || "").replace(/\s{2,}/g, " ");
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
                  alt=""
                  className="yt-thumb-img"
                  loading="eager"
                  decoding="async"
                  referrerPolicy="no-referrer"
                  onError={(e) => {
                    const img = e.currentTarget as HTMLImageElement;
                    if (!img.src.includes("mqdefault")) {
                      img.src = `https://i.ytimg.com/vi/${vid.id}/mqdefault.jpg`;
                    } else {
                      img.style.display = "none";   // the thumbnail can't load: the titled fallback underneath shows
                    }
                  }}
                />

                {/* Shown only if the thumbnail can't load (it sits under the image) */}
                <div className="yt-thumb-fallback" aria-hidden="true">
                  <span>{cleanVideoTitle(vid.title)}</span>
                </div>

                {/* A small YouTube mark in the corner: the preview itself stays clean */}
                <span className="yt-mark" aria-hidden="true">
                  <svg viewBox="0 0 28 20" width="22" height="16">
                    <rect width="28" height="20" rx="5" fill="#ff0000" />
                    <path d="M11 6v8l7-4z" fill="#fff" />
                  </svg>
                </span>


                {isShort ? (
                  <span className="yt-duration-badge yt-short-badge">
                    <BoltIcon size={12} /> Shorts
                  </span>
                ) : vid.duration ? (
                  <span className="yt-duration-badge">{vid.duration}</span>
                ) : null}
              </div>

              <div className="yt-card-details">
                <div className="yt-text-meta">
                  <h5 className="yt-video-title" title={vid.title}>{cleanVideoTitle(vid.title)}</h5>
                  <div className="yt-submeta">
                    <span className="yt-channel-name">SR University · YouTube</span>
                  </div>
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
          More on the official YouTube channel ↗
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
  // Long lists are folded so the card stays a readable size in the chat; nothing is dropped.
  const [showAllOffers, setShowAllOffers] = useState(false);
  const visibleOffers = showAllOffers ? marqueeOffers : marqueeOffers.slice(0, 3);

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

      {/* 3 Consecutive Years Superstars Showcase */}
      <h6 className="placement-mnc-title">
        <AwardIcon size={13} /> Highest packages, three consecutive years
      </h6>
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

      {/* Other Marquee Superstar Achievers */}
      {marqueeOffers.length > 0 && (
        <div className="placement-marquee-section">
          <h6 className="placement-mnc-title">
            <AwardIcon size={13} /> Other marquee offers
          </h6>
          <div className="marquee-offers-grid">
            {visibleOffers.map((m: any, idx: number) => (
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
          {marqueeOffers.length > 3 && (
            <button
              type="button"
              className="card-more-btn"
              aria-expanded={showAllOffers}
              onClick={() => setShowAllOffers((v) => !v)}
            >
              {showAllOffers ? "Show fewer" : `Show all ${marqueeOffers.length} offers`}
            </button>
          )}
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
  const waiver = Number(d.scholarship_percent) || 0;
  const year = d.academic_year || d.admission_year || "2027-28";
  const hasHostel = Boolean(d.has_hostel);
  const flags: string[] = Array.isArray(d.flags) ? d.flags : [];
  // Every figure below comes from the fee engine's answer; nothing is computed or guessed here.
  const semesters = [d.semester_1 && { semester: 1, ...d.semester_1 }, d.semester_2 && { semester: 2, ...d.semester_2 }]
    .filter(Boolean) as any[];

  const handleWhatsApp = () => {
    const lines = [
      `Hello SR University Admissions! My fee estimate for ${progName} (${year}):`,
      waiver > 0 ? `Merit scholarship: ${waiver}% (${d.scholarship_basis_text || "my marks"})` : "Standard fee",
      `Semester 1: ${d.sem1_total_payable || "—"} | Semester 2: ${d.sem2_total_payable || "—"}`,
      `First year: ${d.first_year_total_payable || "—"}${hasHostel ? " (with hostel)" : ""}`,
      "Please help me with the next admission steps.",
    ];
    window.open(`https://wa.me/918331003030?text=${encodeURIComponent(lines.join("\n"))}`, "_blank");
  };

  return (
    <div className="rich-card fee-card agent-fee-card">
      <div className="card-header">
        <span className="card-badge badge-success">
          <RupeeIcon size={14} /> Official {year} fee
        </span>
        <h4 className="card-title">{progName}</h4>
        <div className="afc-chips">
          {waiver > 0 ? (
            <span className="afc-chip afc-chip--ok">{waiver}% merit scholarship</span>
          ) : (
            <span className="afc-chip">Standard fee</span>
          )}
          {d.scholarship_basis_text && <span className="afc-chip">{d.scholarship_basis_text}</span>}
          {hasHostel && d.hostel?.type && <span className="afc-chip">Hostel: {d.hostel.type}</span>}
          {d.transport_per_year && <span className="afc-chip">University bus</span>}
        </div>
      </div>

      <div className="afc-hero">
        <div className="afc-hero-main">
          <span className="afc-hero-label">First-year payable</span>
          <span className="afc-hero-amount">{d.first_year_total_payable || "—"}</span>
        </div>
        <div className="afc-hero-split">
          <span>
            Sem 1 <strong>{d.sem1_total_payable || "—"}</strong>
          </span>
          <span>
            Sem 2 <strong>{d.sem2_total_payable || "—"}</strong>
          </span>
        </div>
        {waiver > 0 && d.saving_first_year && (
          <span className="afc-hero-save">You save {d.saving_first_year} on tuition this year</span>
        )}
      </div>

      <SemesterFeeTable semesters={semesters} />

      {flags.length > 0 && (
        <div className="afc-flags" role="note">
          {flags.map((f) => (
            <p key={f}>{f}</p>
          ))}
        </div>
      )}

      <ul className="afc-notes">
        <li>Only tuition is split between the semesters; other charges sit where the fee circular places them.</li>
        {d.full_course_total && d.duration_years && (
          <li>
            Full course ({d.duration_years} years): <strong>{d.full_course_total}</strong>, with tuition rising{" "}
            {d.yearly_increase} a year.
          </li>
        )}
        {d.application_fee && <li>Application form {d.application_fee} is paid separately when you apply.</li>}
        {!hasHostel && <li>Hostel and bus are optional and not included.</li>}
        {hasHostel && d.hostel?.status && <li>{d.hostel.status}</li>}
      </ul>

      <div className="agent-card-footer">
        <span className="agent-card-source-tag">Source: SR University fee circular, {year}</span>
        <button type="button" className="agent-card-wa-btn" onClick={handleWhatsApp}>
          WhatsApp Admissions
        </button>
      </div>
    </div>
  );
}


/** The name for the confirmation, never a placeholder ("Unknown", "Student", "undefined"...). */
function callbackName(name: unknown): string {
  const n = String(name ?? "").trim().split(/\s+/)[0] || "";
  return /^(unknown|student|user|guest|null|undefined|n\/?a|none|-+)$/i.test(n) ? "" : n;
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
          {callbackName(d.name) ? <>Thank you, <strong>{callbackName(d.name)}</strong>. </> : "Thank you. "}
          Your callback request has been successfully submitted. Our admissions counsellor will contact you on your
          mobile ending in <strong>•••{d.phone_last4 || "••••"}</strong>.
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
          <div className="afc-hero">
            <div className="afc-hero-main">
              <span className="afc-hero-label">First year (standard fee)</span>
              <span className="afc-hero-amount">{card.formatted_first_year_total || "—"}</span>
            </div>
            <div className="afc-hero-split">
              <span>
                Tuition <strong>{card.tuition?.formatted_annual}</strong>/yr
              </span>
              {card.tuition?.yearly_increase && <span>+{card.tuition.yearly_increase}/yr from Year 2</span>}
            </div>
          </div>
          <SemesterFeeTable semesters={card.semesters} />
          <ul className="afc-notes">
            <li>Before any merit scholarship. Only tuition is split between the two semesters.</li>
            {card.formatted_course_total && card.duration_years && (
              <li>
                Full course ({card.duration_years} years): <strong>{card.formatted_course_total}</strong>
              </li>
            )}
            {card.application_fee && <li>Application form {card.application_fee} is paid separately.</li>}
            {card.specialization_fee && <li>Specialisation fee {card.specialization_fee} a year from Year 2, where it applies.</li>}
          </ul>
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
            <span>{card.dining_info || "Meals are included in the hostel fee."}</span>
          </div>
          {card.hostel_note && <p className="afc-notes afc-notes--plain">{card.hostel_note}</p>}
        </div>
      )}

      {activeTab === "other" && (
        <div className="fee-tab-pane">
          <div className="fee-breakdown-row">
            <span className="fee-row-label">University bus (optional, per year)</span>
            <span className="fee-row-value">{card.formatted_transport || "—"}</span>
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
  // Programmes and their tuition come from the backend (fee policy); never a built-in list.
  const rawPrograms = card.programs || [];

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
                {selectedProg.annual_tuition ? (
                  <span className="selected-course-fee">Annual Tuition: ₹{Number(selectedProg.annual_tuition).toLocaleString("en-IN")}</span>
                ) : null}
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
  const [rawLimitError, setRawLimitError] = useState<string | null>(null);
  const [stream, setStream] = useState<string | null>(v.stream || null);
  const [entrance, setEntrance] = useState<string>(v.entrance_type || "none");
  const [entranceValue, setEntranceValue] = useState<string>(v.entrance_value != null ? String(v.entrance_value) : "");
  const [submitted, setSubmitted] = useState(false);

  const isIb = board === "ib";
  // The usual total for the chosen board and status, unless the student typed their own (for Other boards).
  const suggestedMax = board && stage ? maxTable[board]?.[stage] : undefined;
  const hasDynamicFixedMax = Boolean(
    board && stage && suggestedMax && board !== "other_state_board" && board !== "nios"
  );
  const effectiveMax = hasDynamicFixedMax
    ? String(suggestedMax)
    : maxTouched
      ? maxMarks
      : suggestedMax
        ? String(suggestedMax)
        : maxMarks;

  const rawNum = raw.trim() === "" ? NaN : Number(raw);
  const maxNum = isIb ? 45 : effectiveMax.trim() === "" ? NaN : Number(effectiveMax);
  const rawCap = Number.isFinite(maxNum) && maxNum > 0 ? Math.min(2000, maxNum) : 2000;
  const entranceNum = entranceValue.trim() === "" ? NaN : Number(entranceValue);

  const handleRawChange = (val: string) => {
    if (val === "") {
      setRaw("");
      setRawLimitError(null);
      return;
    }
    if (!/^\d*(?:\.\d{0,2})?$/.test(val) || val.replace(".", "").length > 6) {
      setRawLimitError(`Please enter a valid score up to ${rawCap}.`);
      return;
    }
    const parsed = Number(val);
    if (!Number.isFinite(parsed) || parsed < 0) return;
    if (parsed > rawCap) {
      setRawLimitError(
        rawCap === 100 && !isIb
          ? "Percentage cannot exceed 100%."
          : `Marks obtained cannot exceed ${rawCap}.`
      );
      return;
    }
    setRaw(val);
    setRawLimitError(null);
  };

  const handleMaxChange = (val: string) => {
    setMaxTouched(true);
    if (val === "") {
      setMaxMarks("");
      setRawLimitError(null);
      return;
    }
    if (!/^\d*$/.test(val) || val.length > 4) return;
    const parsed = Number(val);
    if (parsed > 2000) {
      setRawLimitError("Maximum marks cannot exceed 2000.");
      return;
    }
    setMaxMarks(val);
    setRawLimitError(null);
  };

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
                onClick={() => {
                  setBoard(b.key);
                  setMaxTouched(false);
                  setRawLimitError(null);
                }}
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
                onClick={() => {
                  setStage(st.key);
                  setMaxTouched(false);
                  setRawLimitError(null);
                }}
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
              className={`counsellor-marks-input-field acad-input ${rawLimitError ? "error" : ""}`}
              type="number"
              inputMode="decimal"
              min={1}
              max={rawCap}
              step="any"
              placeholder={isIb ? "e.g. 36" : hasDynamicFixedMax && suggestedMax === 100 ? "e.g. 87.5" : "Marks"}
              value={raw}
              onKeyDown={(e) => {
                if (["-", "+", "e", "E"].includes(e.key)) e.preventDefault();
              }}
              onChange={(e) => handleRawChange(e.target.value)}
            />
            {isIb ? (
              <span className="acad-outof">out of 45</span>
            ) : hasDynamicFixedMax ? (
              <span className="acad-outof">
                {suggestedMax === 100 ? "% (out of 100)" : `out of ${suggestedMax}`}
              </span>
            ) : (
              <>
                <span className="acad-outof">out of</span>
                <input
                  aria-label="Total marks"
                  className="counsellor-marks-input-field acad-input acad-input-max"
                  type="number"
                  inputMode="numeric"
                  min={100}
                  max={2000}
                  placeholder="Total"
                  value={effectiveMax}
                  onKeyDown={(e) => {
                    if (["-", "+", "e", "E"].includes(e.key)) e.preventDefault();
                  }}
                  onChange={(e) => handleMaxChange(e.target.value)}
                />
              </>
            )}
          </div>
          {rawLimitError && <div className="counsellor-inline-error" role="alert">{rawLimitError}</div>}
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
          <BookOpenIcon size={13} /> {card.step_label || "Step 1: Schooling / Board"}
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
          <TargetIcon size={13} /> {card.step_label || "Step 2: Academic Stage"}
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

/**
 * Marks entry (v4.15.0): a labelled form, never a guess from free text.
 *  * The board's total is known (e.g. Telangana Intermediate: 1000): one field, "Marks obtained / 1000".
 *  * Not known: the student picks "Percentage" or "Marks", and for marks enters both the marks obtained and the
 *    maximum marks. Each value is checked (a number, within range) with a clear message before it is sent.
 * The value sent is the one shown, and it replaces any earlier marks on the server (agent._sync_marks).
 */
export function CounsellorMarksCard({ card, onSelect }: { card: any; onSelect?: (text: string) => void }) {
  const fixedMax: number | null = card.max_marks ? Number(card.max_marks) : null;
  const isIb = card.board_key === "ib" || fixedMax === 45;
  const hasFixedTotal = fixedMax !== null && fixedMax > 0;
  const isFixedPercent = hasFixedTotal && !isIb && fixedMax <= 100;
  const [mode, setMode] = useState<"marks" | "percent">(isFixedPercent ? "percent" : "marks");
  const [got, setGot] = useState<string>(card.default_val ? String(card.default_val) : "");
  const [total, setTotal] = useState<string>(hasFixedTotal && !isFixedPercent ? String(fixedMax) : "");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const flexible = !hasFixedTotal;
  const uid = useState(() => Math.random().toString(36).slice(2, 8))[0];

  const num = (v: string) => {
    const n = parseFloat(String(v).replace(/,/g, "").trim());
    return Number.isFinite(n) ? n : NaN;
  };

  const totalNum = num(total);
  const activeCap =
    mode === "percent" || isFixedPercent
      ? 100
      : hasFixedTotal
        ? fixedMax!
        : !isNaN(totalNum) && totalNum >= 100 && totalNum <= 2000
          ? totalNum
          : 2000;

  const handleGotChange = (val: string) => {
    if (val === "") {
      setGot("");
      setError(null);
      return;
    }
    if (!/^\d*(?:\.\d{0,2})?$/.test(val) || val.replace(".", "").length > 6) {
      setError(
        mode === "percent" || isFixedPercent
          ? "Enter a valid percentage between 1 and 100."
          : `Enter valid marks up to ${activeCap}.`
      );
      return;
    }
    const parsed = Number(val);
    if (!Number.isFinite(parsed) || parsed < 0) return;
    if (parsed > activeCap) {
      setError(
        mode === "percent" || isFixedPercent
          ? "Percentage cannot exceed 100%."
          : `Marks obtained cannot exceed ${activeCap}.`
      );
      return;
    }
    setGot(val);
    setError(null);
  };

  const handleTotalChange = (val: string) => {
    if (val === "") {
      setTotal("");
      setError(null);
      return;
    }
    if (!/^\d*$/.test(val) || val.length > 4) return;
    const parsed = Number(val);
    if (parsed > 2000) {
      setError("Maximum marks cannot exceed 2000.");
      return;
    }
    setTotal(val);
    setError(null);
  };

  const gNum = num(got);
  const isValidToSubmit =
    got.trim().length > 0 &&
    !isNaN(gNum) &&
    gNum > 0 &&
    gNum <= activeCap &&
    !(flexible && mode === "marks" && (isNaN(totalNum) || totalNum < 100 || totalNum > 2000 || gNum > totalNum));

  const submit = () => {
    if (submitted) return;
    const g = num(got);
    if (mode === "percent" || isFixedPercent) {
      if (isNaN(g) || g <= 0 || g > 100) {
        setError("Enter your percentage as a number between 1 and 100, for example 87.5.");
        return;
      }
      setError(null);
      const text = `${g}%`;
      setSubmitted(text);
      onSelect?.(text);
      return;
    }
    const t = hasFixedTotal ? fixedMax! : num(total);
    if (isNaN(t) || (!hasFixedTotal && (t < 100 || t > 2000)) || t <= 0) {
      setError("Enter the maximum marks for your exam, for example 1000 or 600.");
      return;
    }
    if (isNaN(g) || g <= 0) {
      setError(isIb ? "Enter your IB points as a number up to 45." : "Enter the marks you obtained as a number, for example 870.");
      return;
    }
    if (g > t) {
      setError(`Marks obtained can't be more than the maximum (${t}).`);
      return;
    }
    setError(null);
    const text = `${g} out of ${t}`;
    setSubmitted(text);
    onSelect?.(text);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (["-", "+", "e", "E"].includes(e.key)) {
      e.preventDefault();
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="rich-card counsellor-card counsellor-marks-card">
      <div className="counsellor-card-header">
        <span className="card-badge counsellor-step-badge">
          <AwardIcon size={13} /> {card.step_label || "Your marks"}
        </span>
        <h4 className="card-title counsellor-title">{card.title || "Enter your marks"}</h4>
        {card.subtitle && <p className="card-subtitle counsellor-subtitle">{card.subtitle}</p>}
      </div>

      {submitted ? (
        <div className="cm-marks-done" role="status">✓ Sent: <strong>{submitted}</strong></div>
      ) : (
        <div className="counsellor-marks-body cm-marks-form">
          {flexible && (
            <div className="cm-marks-mode" role="radiogroup" aria-label="How do you want to enter your marks?">
              <button type="button" role="radio" aria-checked={mode === "marks"} className={mode === "marks" ? "on" : ""}
                      onClick={() => { setMode("marks"); setGot(""); setError(null); }}>Marks</button>
              <button type="button" role="radio" aria-checked={mode === "percent"} className={mode === "percent" ? "on" : ""}
                      onClick={() => { setMode("percent"); setGot(""); setError(null); }}>Percentage</button>
            </div>
          )}
          {mode === "percent" || isFixedPercent ? (
            <label className="cm-marks-field" htmlFor={`pct-${uid}`}>
              <span className="cm-marks-label">Your percentage</span>
              <span className="counsellor-input-wrapper">
                <input id={`pct-${uid}`} type="number" inputMode="decimal" min={1} max={100} step="0.01"
                       className={`counsellor-marks-input-field ${error ? "error" : ""}`} placeholder="e.g. 87.5"
                       value={got} onChange={(e) => handleGotChange(e.target.value)} onKeyDown={onKey}
                       aria-invalid={!!error} />
                <span className="counsellor-marks-unit">%</span>
              </span>
            </label>
          ) : hasFixedTotal ? (
            <label className="cm-marks-field" htmlFor={`got-${uid}`}>
              <span className="cm-marks-label">{isIb ? "IB Diploma points" : "Marks obtained"}</span>
              <span className="counsellor-input-wrapper">
                <input id={`got-${uid}`} type="number" inputMode="numeric" min={1} max={fixedMax!} step="any"
                       className={`counsellor-marks-input-field cm-marks-fixed-input ${error ? "error" : ""}`}
                       placeholder={isIb ? "e.g. 38" : `e.g. ${Math.round(fixedMax! * 0.87)}`}
                       value={got} onChange={(e) => handleGotChange(e.target.value)} onKeyDown={onKey}
                       aria-invalid={!!error} />
                <span className="counsellor-marks-unit">/ {fixedMax}</span>
              </span>
            </label>
          ) : (
            <div className="cm-marks-pair">
              <label className="cm-marks-field" htmlFor={`got-${uid}`}>
                <span className="cm-marks-label">Marks obtained</span>
                <input id={`got-${uid}`} type="number" inputMode="numeric" min={1} max={activeCap}
                       className={`counsellor-marks-input-field ${error ? "error" : ""}`}
                       placeholder="e.g. 870"
                       value={got} onChange={(e) => handleGotChange(e.target.value)} onKeyDown={onKey}
                       aria-invalid={!!error} />
              </label>
              <span className="cm-marks-slash" aria-hidden="true">/</span>
              <label className="cm-marks-field" htmlFor={`max-${uid}`}>
                <span className="cm-marks-label">Maximum marks</span>
                <input id={`max-${uid}`} type="number" inputMode="numeric" min={100} max={2000}
                       className="counsellor-marks-input-field" placeholder="e.g. 1000" value={total}
                       onChange={(e) => handleTotalChange(e.target.value)} onKeyDown={onKey} />
              </label>
            </div>
          )}
          {error && <div className="counsellor-inline-error" role="alert">{error}</div>}
          <button type="button" className="counsellor-submit-btn cm-marks-submit" onClick={submit} disabled={!isValidToSubmit}>
            Continue
          </button>
          {card.hint && <p className="cm-marks-hint">{card.hint}</p>}
        </div>
      )}
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
  // The opening welcome message (card.live) shows the tiles set in the admin panel; the built-in list until they
  // arrive, or if they can't be loaded. Saved chats keep the tiles they showed.
  const [liveItems, setLiveItems] = useState<any[] | null>(null);
  useEffect(() => {
    if (!card.live) return;
    let alive = true;
    fetchWelcomeActions()
      .then((d) => {
        if (alive && Array.isArray(d.items) && d.items.length) setLiveItems(d.items);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [card.live]);
  const items = liveItems || card.items || WELCOME_QUICK_ACTIONS;

  const handleClick = (prompt: string) => {
    setSelectedPrompt(prompt);
    onSelect?.(prompt);
  };

  return (
    <div className="welcome-actions-card-wrapper">
      {card.heading && <div className="welcome-actions-heading">{card.heading}</div>}
      <div className={`welcome-actions-grid ${items.length % 2 ? "is-odd" : ""}`}>
        {items.map((item: any) => {
          const isSelected = selectedPrompt === item.prompt;
          const isDimmed = Boolean(selectedPrompt && !isSelected);
          return (
            <button
              key={item.id || item.title}
              type="button"
              className={`welcome-action-tile tile-${item.color || "blue"} ${isSelected ? "selected" : ""} ${isDimmed ? "dimmed" : ""}`}
              title={item.subtitle || undefined}
              onClick={() => handleClick(item.prompt)}
            >
              <span className={`welcome-action-icon-box icon-box-${item.color || "blue"}`}>
                <WelcomeTileIcon name={item.icon} />
              </span>
              <span className="welcome-action-info">
                <span className="welcome-action-title">{item.title}</span>
                {item.badge && <span className={`welcome-action-badge badge-${item.color || "blue"}`}>{item.badge}</span>}
              </span>
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
    case "counsellor_choice": // one small question with options (e.g. the 10+2 group step)
      return <CounsellorStageCard card={card} onSelect={onSelect} />;
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
    case "get_special_concessions": // the concessions table: pick one and apply it to your fee
      return <ConcessionsCard card={card} onSelect={onSelect} />;
    case "concession_fee":
      return <ConcessionFeeCard card={card} />;
    case "fee_plan": // older chats (v4.10.0)
      return <FeePlanCard card={card} />;
    case "fee_summary": // the fee evaluation agent's final card (v4.11.0)
      return <FeeSummaryCard card={card} />;
    case "agent_plan": // the agent's visible plan (v4.12.0)
      return <AgentPlanCard card={card} />;
    case "counsellor_connect": // "talk to a counsellor" (v4.12.0)
      return <CounsellorConnectCard card={card} onSelect={onSelect} />;
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
    case "event_highlights": // events' photo cards (v4.14.0, Admin -> Campus media -> Events)
      return <EventHighlightsCard card={card} />;
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


