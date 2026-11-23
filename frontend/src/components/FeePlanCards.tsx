import { useMemo, useState } from "react";
import { AwardIcon, CheckIcon, RupeeIcon, ShareIcon, ShieldCheckIcon } from "./Icons";
import "./FeePlanCards.css";

/**
 * Fee-plan cards (v4.10.0), all filled from the official 2027-28 fee data by the backend
 * (app/sru_agent/fee_plan.py and fees.special_concessions):
 *  * ConcessionsTableCard: the 19 special concessions as a table; pick one and apply it to your fee;
 *  * ConcessionFeeCard: one card with the tuition after the chosen concession and the proof note;
 *  * FeePlanCard: the complete first-year fee chart with a Share button.
 */

type Select = (text: string) => void;

function amountValue(text: string): number {
  return Number(String(text || "").replace(/[^0-9]/g, "")) || 0;
}

export function ConcessionsTableCard({ card, onSelect }: { card: any; onSelect?: Select }) {
  const data = card.data || card;
  const rows: { category: string; per_year: string }[] = useMemo(
    () =>
      [...(data.all_categories || [])].sort(
        (a: any, b: any) => amountValue(b.per_year) - amountValue(a.per_year)
      ),
    [data.all_categories]
  );
  const [picked, setPicked] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  const apply = () => {
    if (!picked || applied || !onSelect) return;
    setApplied(true);
    onSelect(`Apply the "${picked}" concession to my fee`);
  };

  return (
    <div className="rich-card fp-card fp-concessions">
      <div className="card-header">
        <span className="card-badge">
          <AwardIcon size={14} /> Special concessions
        </span>
        <h4 className="card-title">
          {rows.length} categories · per year · {data.academic_year || "2027-28"}
        </h4>
      </div>
      <p className="fp-hint">Tap the one that applies to you, then apply it to your fee.</p>
      <div className="fp-table-wrap">
        <table className="fp-table fp-select-table">
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col" className="fp-num">Per year</th>
            </tr>
          </thead>
          <tbody role="radiogroup" aria-label="Special concession categories">
            {rows.map((r) => {
              const on = picked === r.category;
              return (
                <tr
                  key={r.category}
                  role="radio"
                  aria-checked={on}
                  tabIndex={applied ? -1 : 0}
                  className={`fp-select-row${on ? " is-on" : ""}${applied ? " is-locked" : ""}`}
                  onClick={() => !applied && setPicked(r.category)}
                  onKeyDown={(e) => {
                    if (applied) return;
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setPicked(r.category);
                    }
                  }}
                >
                  <td>
                    <span className="fp-pick">
                      <span className="fp-radio" aria-hidden="true">
                        {on && <CheckIcon size={11} strokeWidth={3} />}
                      </span>
                      <span className="fp-cat">{r.category}</span>
                    </span>
                  </td>
                  <td className="fp-num">{r.per_year}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="agent-card-footer fp-footer">
        <button
          type="button"
          className="agent-card-map-btn fp-apply"
          onClick={apply}
          disabled={!picked || applied || !onSelect}
        >
          {applied ? (
            <>
              <CheckIcon size={14} /> Applied
            </>
          ) : picked ? (
            "Apply to my fee"
          ) : (
            "Select a category"
          )}
        </button>
        <span className="agent-card-source-tag">
          Each concession needs valid proof, verified by the Admissions Office.
        </span>
      </div>
    </div>
  );
}

export function ConcessionFeeCard({ card }: { card: any }) {
  const d = card.data || {};
  return (
    <div className="rich-card fp-card fp-concession-fee">
      <div className="card-header">
        <span className="card-badge fp-badge-green">
          <ShieldCheckIcon size={14} /> Fee with concession
        </span>
        <h4 className="card-title">
          {d.program} · {d.academic_year}
        </h4>
      </div>
      <div className="fp-hero">
        <span className="fp-hero-label">Tuition after concession</span>
        <span className="fp-hero-amount">
          {d.tuition_after_concession}
          <small> / year</small>
        </span>
        <span className="fp-hero-sub">{d.per_semester_after_concession} per semester</span>
      </div>
      <dl className="fp-lines">
        <div>
          <dt>Tuition (first year)</dt>
          <dd>{d.tuition}</dd>
        </div>
        <div className="is-discount">
          <dt>{d.concession}</dt>
          <dd>− {d.concession_amount}</dd>
        </div>
        <div className="is-total">
          <dt>Tuition with concession</dt>
          <dd>{d.tuition_after_concession}</dd>
        </div>
      </dl>
      {d.merit_percent ? (
        <p className="fp-merit">
          Your <strong>{d.merit_percent}% merit scholarship</strong> brings tuition to{" "}
          <strong>{d.tuition_after_merit}</strong>. {d.combine_note}
        </p>
      ) : null}
      <div className="fp-proof" role="note">
        <ShieldCheckIcon size={16} />
        <span>{d.proof_note}</span>
      </div>
    </div>
  );
}

export function FeePlanCard({ card }: { card: any }) {
  const d = card.data || {};
  const rows: any[] = d.rows || [];
  const [status, setStatus] = useState<"" | "copied" | "failed">("");
  const shareText: string = d.share_text || "";

  const share = async () => {
    const title = `SR University fee chart: ${d.program}`;
    try {
      if (navigator.share) {
        await navigator.share({ title, text: shareText });
        return;
      }
      await navigator.clipboard.writeText(shareText);
      setStatus("copied");
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return; // the student closed the share sheet
      try {
        await navigator.clipboard.writeText(shareText);
        setStatus("copied");
      } catch {
        setStatus("failed");
      }
    }
    window.setTimeout(() => setStatus(""), 2400);
  };

  return (
    <div className="rich-card fp-card fp-plan">
      <div className="card-header">
        <span className="card-badge">
          <RupeeIcon size={14} /> Fee chart
        </span>
        <h4 className="card-title">
          {d.program} · {d.academic_year} · first year
        </h4>
      </div>
      <div className="fp-table-wrap">
        <table className="fp-table">
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col" className="fp-num">Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.item} className={r.kind === "discount" ? "is-discount" : undefined}>
                <td>
                  <span className="fp-cat">{r.item}</span>
                  {r.note && <span className="fp-note">{r.note}</span>}
                </td>
                <td className="fp-num">{r.amount}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="is-total">
              <th scope="row">First-year total</th>
              <td className="fp-num">{d.first_year_total}</td>
            </tr>
            {d.concession && (
              <tr className="is-concession">
                <th scope="row">
                  With {d.concession.label} concession <span className="fp-note">if approved</span>
                </th>
                <td className="fp-num">{d.concession.total_if_approved}</td>
              </tr>
            )}
          </tfoot>
        </table>
      </div>
      <ul className="fp-foot-notes">
        {d.per_semester && <li>Regular semester: {d.per_semester}</li>}
        {d.application_fee && <li>Application fee {d.application_fee}, paid when you apply.</li>}
        {d.not_included?.length > 0 && <li>Not included: {d.not_included.join(", ")}.</li>}
        {d.concession?.note && <li>{d.concession.note}</li>}
      </ul>
      <div className="agent-card-footer fp-footer">
        <button type="button" className="agent-card-map-btn" onClick={share} disabled={!shareText}>
          <ShareIcon size={14} /> {status === "copied" ? "Copied" : "Share"}
        </button>
        <a
          className="agent-card-wa-btn"
          href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          WhatsApp
        </a>
        {status === "failed" && (
          <span className="agent-card-source-tag" role="status">
            Couldn't share. Long-press the chart to copy it.
          </span>
        )}
        <span className="agent-card-source-tag">Source: official SR University fee card, {d.academic_year}.</span>
      </div>
    </div>
  );
}
