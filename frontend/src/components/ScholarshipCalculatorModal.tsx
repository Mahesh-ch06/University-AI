import React, { useEffect, useMemo, useState } from "react";
import {
  CalculatorIcon,
  AwardIcon,
  BoltIcon,
  CalendarIcon,
  PinIcon,
  FlaskIcon,
  HeartHandIcon,
  MessageSquareIcon,
  CloseIcon,
  ShieldCheckIcon,
  CheckIcon,
  InfoIcon,
} from "./Icons";
import { createLead, calculateAgentFee, fetchFeeConfig } from "../services/api";
import bundledFeeConfig from "../data/feeConfig.json";
import {
  calculateParams,
  estimateFromBackend,
  estimateFromConfig,
  inr,
  matchSlab,
  parseScore,
  scholarshipStartText,
} from "../utils/feeCalculator";
import type { Estimate, FeeConfig } from "../utils/feeCalculator";
import { getSessionId } from "../hooks/useSession";
import { saveStudentDetails } from "../utils/studentProfile";
import "./ScholarshipCalculatorModal.css";

/*
 * Fee & Scholarship Calculator.
 *
 * This component holds NO fee amounts and does NO fee arithmetic. Every rupee comes from the ONE fee
 * engine (backend/app/sru_agent/fees.py, reading fee_policy_2027_28.json): the day-scholar estimate for
 * each slab is in the fee table (GET /api/v1/agent/fee-config, bundled as src/data/feeConfig.json so
 * the calculator opens instantly), and the exact schedule for the student's score, hostel and bus comes
 * from POST /api/v1/agent/calculate.
 *
 * To change a fee: edit fee_policy_2027_28.json, run `python scripts/export_fee_config.py` in backend/.
 */

interface Props {
  onClose: () => void;
  onAskBuddy: (prompt: string) => void;
}

const ADMISSIONS_WHATSAPP = "918331003030";
const HOSTEL_ORDER = ["non_ac_4", "non_ac_3", "ac_4", "ac_3"];

export default function ScholarshipCalculatorModal({ onClose, onAskBuddy }: Props) {
  // Details saved earlier by the "verify" step, if any
  const savedLead = useMemo(() => {
    try {
      const raw = localStorage.getItem("sru_student_lead");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const digits = (parsed?.phone || "").replace(/\D/g, "");
      if (digits.length >= 10 && Boolean(parsed?.name)) {
        return { name: parsed.name.trim(), phone: parsed.phone.trim() };
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  const [isVerified, setIsVerified] = useState<boolean>(Boolean(savedLead?.name && savedLead?.phone));

  // The fee table: bundled copy first, then the live one from the backend
  const [config, setConfig] = useState<FeeConfig>(bundledFeeConfig as unknown as FeeConfig);
  useEffect(() => {
    const controller = new AbortController();
    fetchFeeConfig<FeeConfig>(controller.signal)
      .then((live) => {
        if (live?.status === "ok" && Array.isArray(live.programs) && live.programs.length > 0) setConfig(live);
      })
      .catch(() => {
        /* keep the bundled table */
      });
    return () => controller.abort();
  }, []);

  // What the student chose and typed
  const [selectedProgramId, setSelectedProgramId] = useState<string>("btech_cse");
  const [selectedExamKey, setSelectedExamKey] = useState<string>("state_board");
  const [enteredScore, setEnteredScore] = useState<string>("");
  const [showSlabsPreview, setShowSlabsPreview] = useState<boolean>(false);
  const [includeHostel, setIncludeHostel] = useState<boolean>(false);
  const [hostelKey, setHostelKey] = useState<string>("non_ac_4");
  const [includeBus, setIncludeBus] = useState<boolean>(false);

  // Optional callback request
  const [studentName, setStudentName] = useState<string>(savedLead?.name || "");
  const [studentPhone, setStudentPhone] = useState<string>(savedLead?.phone || "");
  const [consentAgreed, setConsentAgreed] = useState<boolean>(true);
  const [leadSuccessMsg, setLeadSuccessMsg] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null); // about the score
  const [callbackError, setCallbackError] = useState<string | null>(null); // about the callback form

  // Everything below is worked out from the inputs on every render, so nothing can go stale.
  const program = useMemo(
    () => config.programs.find((p) => p.id === selectedProgramId) || config.programs[0],
    [config, selectedProgramId]
  );
  const parsed = useMemo(
    () => parseScore(program, selectedExamKey, enteredScore),
    [program, selectedExamKey, enteredScore]
  );
  // The exam actually in use. Typing "EAPCET 9000" switches it even if "State Board" is selected.
  const examKey = parsed.examKey;
  const exam = program.exams.find((e) => e.key === examKey) || program.exams[0];
  const hasScore = parsed.status === "ok" && parsed.value !== undefined;
  const hostelChoice = includeHostel ? hostelKey : "none";
  const localPercent = hasScore ? matchSlab(program, examKey, parsed.value as number) : 0;
  // Day-scholar figures straight from the engine's slab row; hostel / bus need the backend schedule.
  const localEstimate = useMemo(
    () => estimateFromConfig(config, program, localPercent, examKey),
    [config, program, localPercent, examKey]
  );
  const needsBackend = includeHostel || includeBus;

  // Confirm with the backend (the same engine the chat agent uses). A slow answer for an
  // older entry is ignored: only the answer for what is on screen now is shown.
  const inputsKey = `${program.id}|${examKey}|${hasScore ? parsed.value : ""}|${hostelChoice}|${includeBus}`;
  const [confirmed, setConfirmed] = useState<{ key: string; estimate: Estimate } | null>(null);
  useEffect(() => {
    if (!hasScore) return;
    let stale = false;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      calculateAgentFee(calculateParams(program.id, parsed, hostelChoice, includeBus), controller.signal)
        .then((res) => {
          if (res?.status === "ok" && !stale) {
            setConfirmed({ key: inputsKey, estimate: estimateFromBackend(res) });
          }
        })
        .catch(() => {
          /* offline or waking up: the day-scholar estimate from the fee table stays on screen */
        });
    }, 350);
    return () => {
      stale = true;
      window.clearTimeout(timer);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputsKey]);

  const isConfirmed = Boolean(confirmed && confirmed.key === inputsKey);
  // With hostel or bus chosen, only the engine's own answer is shown (never a figure worked out here).
  const estimate: Estimate = isConfirmed && confirmed ? confirmed.estimate : localEstimate;
  const optionsPending = needsBackend && !isConfirmed;
  const pct = estimate.scholarshipPercent;
  const matchedRange = program.slabs.find((s) => s.scholarship_percent === pct)?.ranges[examKey] || "";
  const belowMinimum =
    hasScore && (examKey === "state_board" || examKey === "cbse") && (parsed.value as number) < program.minimum_percent;
  const year = config.academic_year;
  const shortProgramName = program.name.split(" (")[0];
  const hostelLabel = config.hostel_labels[hostelKey] || hostelKey;
  const charge = (key: string) => config.charges[key]?.amount || 0;

  const concessionGroups = useMemo(() => {
    const groups = new Map<number, string[]>();
    for (const c of config.special_concessions) {
      groups.set(c.amount, [...(groups.get(c.amount) || []), c.label]);
    }
    return [...groups.entries()].sort((a, b) => b[0] - a[0]);
  }, [config]);

  const handleResetScore = () => {
    setEnteredScore("");
    setValidationError(null);
    setIncludeHostel(false);
  };

  const handleScoreChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEnteredScore(e.target.value);
    if (validationError) setValidationError(null);
  };

  const handleProgramChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const next = config.programs.find((p) => p.id === e.target.value);
    setSelectedProgramId(e.target.value);
    if (next && !next.exams.some((x) => x.key === selectedExamKey)) setSelectedExamKey(next.exams[0].key);
    setValidationError(null);
  };

  const handleExamChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedExamKey(e.target.value);
    setValidationError(null);
  };

  // "Calculate" button. The fee already updates while typing; this validates the entry and, for a
  // student who verified earlier, records the estimate ONCE (never on every keystroke).
  const handleCalculateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (parsed.status === "empty") {
      setValidationError("Please enter your marks (out of 1000), percentage (%), or EAPCET rank.");
      return;
    }
    if (parsed.status === "invalid") {
      setValidationError(parsed.message || "Please check the score you entered.");
      return;
    }
    setValidationError(null);
    if (!savedLead) return;
    const onceKey = `sru_calc_lead:${inputsKey}`;
    try {
      if (sessionStorage.getItem(onceKey)) return;
      sessionStorage.setItem(onceKey, "1");
    } catch {
      /* private mode: fall through and save once for this click */
    }
    try {
      const activeConv = sessionStorage.getItem("sru_active_conv_id");
      await createLead({
        name: savedLead.name,
        phone: savedLead.phone,
        program_interest: program.name,
        score: parsed.display,
        exam_type: exam.label,
        source: "scholarship_calculator",
        conversation_id: activeConv || undefined,
        metadata: {
          calculated_discount: Math.round(estimate.savingYear / 2),
          scholarship_percent: pct,
          payable_sem: estimate.netSem,
          admission_year: year,
        },
      });
    } catch (err) {
      console.warn("Lead registration note:", err);
    }
  };

  // Optional admissions callback, only with consent and only when the button is pressed
  const handleRequestCallback = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = studentName.trim();
    const cleanPhone = studentPhone.replace(/\D/g, "").replace(/^(?:91|0)(?=[6-9]\d{9}$)/, "");
    if (cleanName.length < 2) {
      setCallbackError("Please enter student name.");
      return;
    }
    if (!/^[6-9]\d{9}$/.test(cleanPhone)) {
      setCallbackError("Please enter a valid 10-digit mobile number.");
      return;
    }
    if (!consentAgreed) {
      setCallbackError("Please agree that SR University may contact you about admissions.");
      return;
    }

    setCallbackError(null);
    try {
      await saveStudentDetails(getSessionId(), { name: cleanName, phone: cleanPhone });
      setIsVerified(true);
      const activeConv = sessionStorage.getItem("sru_active_conv_id");
      await createLead({
        name: cleanName,
        phone: cleanPhone,
        program_interest: program.name,
        score: parsed.display || "Direct Inquiry",
        exam_type: exam.label,
        source: "scholarship_calculator_callback",
        conversation_id: activeConv || undefined,
        metadata: {
          consent_given: true,
          request_type: "callback",
          calculated_discount: Math.round(estimate.savingYear / 2),
          scholarship_percent: pct,
          payable_sem: estimate.netSem,
          admission_year: year,
        },
      });
      setLeadSuccessMsg("Callback requested. An admissions counsellor will call you on this number.");
    } catch (err) {
      console.warn("Lead registration note:", err);
      setLeadSuccessMsg(null);
      setCallbackError("We could not save your request just now. Please try again, or call 833 100 3030.");
    }
  };

  const handleWhatsAppShare = () => {
    if (!hasScore) return;
    const lines = [
      `Hello SR University Admissions! I calculated my fee estimate for ${program.name} (Admissions ${year}).`,
      `• Score/Rank: ${parsed.display}`,
      `• Merit scholarship: ${pct}%`,
      `• Net tuition: ${inr(estimate.netSem)}/sem (${inr(estimate.netYear)}/year)`,
    ];
    if (includeHostel) lines.push(`• Hostel: ${hostelLabel}`);
    if (includeBus) lines.push("• University bus: yes");
    lines.push(
      ...estimate.semesters.map((s) => `• Semester ${s.semester}: ${inr(s.total)}`),
      `• Total 1st year: ${inr(estimate.firstYearTotal)} (application form ${inr(estimate.applicationFee)} separately)`,
      "Please share further admission and counselling guidance."
    );
    window.open(`https://wa.me/${ADMISSIONS_WHATSAPP}?text=${encodeURIComponent(lines.join("\n"))}`, "_blank");
  };

  const handlePrint = () => {
    window.print();
  };

  const upgradeMessage = estimate.nextSlab
    ? `${estimate.nextSlab.requires} unlocks the ${estimate.nextSlab.percent}% scholarship, saving a further ` +
      `${inr(estimate.nextSlab.extraSavingYear)} in the first year.`
    : "";
  const scoreSummary = parsed.display;

  return (
    <div className="scholarship-modal-backdrop" onClick={onClose}>
      <div className="scholarship-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="calc-header">
          <div className="calc-title-group">
            <div className="calc-icon-badge" aria-hidden="true">
              <CalculatorIcon size={20} />
            </div>
            <div>
              <h3 className="calc-title">Fee & Scholarship Calculator</h3>
              <p className="calc-subtitle">SR University fees and merit scholarships, admissions {year}</p>
            </div>
          </div>
          <button className="calc-close-btn" onClick={onClose} aria-label="Close calculator" type="button">
            <CloseIcon size={18} />
          </button>
        </div>

        {/* 1. Verified student strip */}
        {isVerified && savedLead && (
          <div className="calc-verified-strip">
            <div className="calc-verified-info">
              <span className="calc-verified-check"><CheckIcon size={13} /></span>
              <span className="calc-verified-text">
                Verified Student: <strong>{savedLead.name}</strong> <span className="calc-verified-phone">({savedLead.phone})</span>
              </span>
            </div>
            <span className="calc-verified-tag">Authenticated</span>
          </div>
        )}

        {/* 2. Program and exam */}
        <div className="calc-selectors-grid">
          <div className="calc-select-group">
            <label htmlFor="calc-prog-select">Degree Program</label>
            <div className="calc-select-wrap">
              <select
                id="calc-prog-select"
                value={program.id}
                onChange={handleProgramChange}
                className="calc-select-modern"
              >
                <optgroup label="Bachelors Degrees">
                  {config.programs.filter((p) => p.level !== "pg").map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Masters Degrees">
                  {config.programs.filter((p) => p.level === "pg").map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
          </div>

          <div className="calc-select-group">
            <label htmlFor="calc-exam-select">Qualifying Exam / Board</label>
            <div className="calc-select-wrap">
              <select
                id="calc-exam-select"
                value={exam.key}
                onChange={handleExamChange}
                className="calc-select-modern"
              >
                {program.exams.map((ex) => (
                  <option key={ex.key} value={ex.key}>
                    {ex.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* 3. Score input */}
        <form onSubmit={handleCalculateSubmit} className="calc-input-section">
          <div className="calc-input-box">
            <label htmlFor="calc-marks-input" className="calc-input-label">
              <span>Enter Your Score / Percentage / Rank</span>
              <span className="calc-input-subtext">e.g. 850 marks in Inter, 88%, or EAPCET 4500</span>
            </label>

            <div className="calc-input-action-row">
              <div className="calc-input-field-wrap">
                <input
                  id="calc-marks-input"
                  type="text"
                  className="calc-main-input"
                  placeholder="Type marks, percentage, or rank..."
                  value={enteredScore}
                  onChange={handleScoreChange}
                  autoFocus
                />
                {enteredScore && (
                  <button
                    type="button"
                    className="calc-input-clear-btn"
                    onClick={handleResetScore}
                    title="Clear marks"
                    aria-label="Clear marks"
                  >
                    ✕
                  </button>
                )}
              </div>

              <button type="submit" className="calc-submit-btn">
                <BoltIcon size={16} />
                <span>Calculate</span>
              </button>
            </div>

            {hasScore && pct > 0 && (
              <div className="calc-matched-badge">
                <AwardIcon size={14} />
                <span>
                  <strong>{pct}% Scholarship Matched</strong>
                  {" • "}{exam.label}: {matchedRange}
                  {` (${scoreSummary})`}
                </span>
              </div>
            )}
            {hasScore && pct === 0 && (
              <div className="calc-matched-badge below-cutoff">
                <InfoIcon size={14} />
                <span>
                  <strong>Standard Tuition</strong>
                  {" • "}{scoreSummary}
                  {" • "}{scholarshipStartText(program, examKey)}
                </span>
              </div>
            )}
            {belowMinimum && (
              <div className="calc-matched-badge below-cutoff">
                <InfoIcon size={14} />
                <span>
                  {parsed.value as number}% is below the {program.minimum_percent}% minimum for this course on the
                  2027-28 fee card, so you do not meet the general eligibility on these marks. Please contact the
                  Admissions Office (833 100 3030) to discuss your options.
                </span>
              </div>
            )}
            {parsed.status === "invalid" && !validationError && (
              <div className="calc-error-banner" style={{ marginTop: "4px" }}>
                <span>{parsed.message}</span>
              </div>
            )}
            {validationError && (
              <div className="calc-error-banner" style={{ marginTop: "4px" }}>
                <span>{validationError}</span>
              </div>
            )}
          </div>
        </form>

        {/* 4a. Before a score is entered */}
        {!hasScore && (
          <div className="calc-empty-card">
            <div className="calc-empty-icon">🎯</div>
            <div className="calc-empty-info">
              <h4>Enter your marks to see your personalized fee</h4>
              <p>
                {shortProgramName}: tuition {inr(program.tuition_per_year)} per year. Merit scholarships of{" "}
                {program.slabs[0]?.scholarship_percent}% to {program.slabs[program.slabs.length - 1]?.scholarship_percent}%
                {" "}are available, subject to marksheet verification.
              </p>
            </div>
            <button
              type="button"
              className="calc-toggle-slabs-btn"
              onClick={() => setShowSlabsPreview(!showSlabsPreview)}
            >
              {showSlabsPreview ? "Hide Merit Slabs Table ▴" : "View Official Slabs & Criteria ▾"}
            </button>

            {showSlabsPreview && (
              <div className="calc-slabs-preview-table">
                <div className="slabs-table-header">
                  <span>Merit Waiver</span>
                  <span>{exam.label}</span>
                  <span>Tuition / semester</span>
                </div>
                {program.slabs.map((slab) => (
                  <div key={slab.scholarship_percent} className="slabs-table-row">
                    <span className="slab-badge-min">{slab.scholarship_percent}% Waiver</span>
                    <span className="slab-criteria-min">{slab.ranges[exam.key] || "Not applicable"}</span>
                    <span className="slab-payable-min">{inr(slab.tuition_per_semester)}/sem</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 4b. The estimate */}
        {hasScore && (
          <div className="calc-results-container">
            <div className="calc-results-header">
              <div className="calc-status-badge-wrap">
                <span className="calc-result-heading">Your estimate for {shortProgramName}</span>
              </div>
              <button
                type="button"
                className="calc-reset-action"
                onClick={handleResetScore}
                title="Test another score"
              >
                ↺ Test Another Score
              </button>
            </div>

            <div className="calc-metrics-grid">
              <div className="calc-metric-card primary-card">
                <span className="metric-tag">Net Payable Tuition</span>
                <div className="metric-primary-val">
                  {inr(estimate.netSem)}
                  <span className="metric-unit"> / semester</span>
                </div>
                <div className="metric-sub-val">{inr(estimate.netYear)} / year</div>
              </div>

              <div className={`calc-metric-card ${pct > 0 ? "savings-card" : "neutral-card"}`}>
                <span className="metric-tag">{pct > 0 ? "Merit Scholarship Savings" : "Scholarship Status"}</span>
                <div className="metric-primary-val green">
                  {pct > 0 ? `Save ${inr(estimate.savingYear)}/yr` : "Standard Fee"}
                </div>
                <div className="metric-sub-val">
                  {pct > 0
                    ? `${pct}% off first-year tuition of ${inr(estimate.tuitionYear)}`
                    : scholarshipStartText(program, examKey)}
                </div>
              </div>
            </div>

            {/* First-year breakdown, semester by semester (engine figures only) */}
            <div className="calc-breakdown-card">
              <div className="breakdown-card-header">
                <strong>First-Year Fee, Semester by Semester ({year})</strong>
                <span className="breakdown-badge">{shortProgramName}</span>
              </div>

              <div className="calc-option-row">
                <label className="hostel-toggle-label">
                  <input
                    type="checkbox"
                    checked={includeHostel}
                    onChange={(e) => setIncludeHostel(e.target.checked)}
                    className="hostel-checkbox"
                  />
                  <span className="hostel-toggle-text"><strong>Add hostel</strong> (optional)</span>
                </label>
                <label className="hostel-toggle-label">
                  <input
                    type="checkbox"
                    checked={includeBus}
                    onChange={(e) => setIncludeBus(e.target.checked)}
                    className="hostel-checkbox"
                  />
                  <span className="hostel-toggle-text">
                    <strong>Add university bus</strong> ({inr(charge("bus"))}/yr, optional)
                  </span>
                </label>
              </div>
              {includeHostel && (
                <div className="hostel-sub-picker">
                  {HOSTEL_ORDER.filter((k) => config.hostel_per_year[k] !== undefined).map((k) => (
                    <label key={k} className={`hostel-type-pill ${hostelKey === k ? "selected" : ""}`}>
                      <input
                        type="radio"
                        name="hostelType"
                        value={k}
                        checked={hostelKey === k}
                        onChange={() => setHostelKey(k)}
                      />
                      <span>{config.hostel_labels[k] || k}: {inr(config.hostel_per_year[k])} / year</span>
                    </label>
                  ))}
                </div>
              )}

              {optionsPending ? (
                <div className="calc-sem-pending" role="status">Working out your semester fees with these options…</div>
              ) : (
                <div className="calc-sem-table-wrap">
                  <table className="calc-sem-table">
                    <thead>
                      <tr>
                        <th scope="col">Component</th>
                        {estimate.semesters.map((s) => (
                          <th scope="col" key={s.semester}>Sem {s.semester}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {Array.from(new Set(estimate.semesters.flatMap((s) => s.items.map((i) => i.label)))).map((label) => (
                        <tr key={label}>
                          <th scope="row">{label}</th>
                          {estimate.semesters.map((s) => {
                            const item = s.items.find((i) => i.label === label);
                            return (
                              <td key={s.semester} className={item && item.amount < 0 ? "is-discount" : undefined}>
                                {item ? inr(item.amount) : "—"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th scope="row">Semester payable</th>
                        {estimate.semesters.map((s) => (
                          <td key={s.semester}>{inr(s.total)}</td>
                        ))}
                      </tr>
                    </tfoot>
                  </table>
                  <div className="breakdown-total-row">
                    <span className="total-label">First-year total (Sem 1 + Sem 2):</span>
                    <span className="total-val bold-emerald">{inr(estimate.firstYearTotal)}</span>
                  </div>
                  {estimate.fullCourseTotal ? (
                    <div className="breakdown-line sub">
                      <span className="line-label">Full course ({estimate.years.length} years):</span>
                      <span className="line-val">{inr(estimate.fullCourseTotal)}</span>
                    </div>
                  ) : null}
                  <div className="breakdown-line sub">
                    <span className="line-label">Application form (paid separately):</span>
                    <span className="line-val">{inr(estimate.applicationFee || charge("application_fee"))}</span>
                  </div>
                </div>
              )}
              {estimate.flags.length > 0 && (
                <div className="calc-flags" role="note">
                  {estimate.flags.map((f) => (
                    <p key={f}>⚠️ {f}</p>
                  ))}
                </div>
              )}
            </div>

            {estimate.nextSlab && (
              <div className="calc-upgrade-card">
                <div className="upgrade-card-icon">💡</div>
                <div className="upgrade-card-text">
                  <strong>Next scholarship level: </strong>
                  <span>{upgradeMessage}</span>
                </div>
              </div>
            )}

            {!optionsPending && estimate.years.length > 1 && (
              <div className="calc-progression-card">
                <div className="progression-header">
                  <CalendarIcon size={14} />
                  <span>
                    Payable each year (tuition rises by {inr(program.yearly_increase)} a year, irrespective of
                    scholarship):
                  </span>
                </div>
                <div className="progression-pill-grid">
                  {estimate.years.map((amount, i) => (
                    <div key={i} className="prog-pill">
                      <span className="prog-yr">Year {i + 1}</span>
                      <span className="prog-amt">{inr(amount)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="calc-notes">
              <div className="note-item">
                <PinIcon size={15} />
                <div>
                  <strong>How the charges are placed:</strong> only tuition is split between the two semesters.
                  Semester 1 of Year 1 has the enrollment fee ({inr(charge("enrollment_fee"))}) and exam fee (
                  {inr(charge("exam_fee"))}); the other fee ({inr(charge("other_fee"))}) is paid in Semester 1 every
                  year. Merit scholarships reduce tuition only.
                </div>
              </div>
              {program.specialization_fee_applies && (
                <div className="note-item">
                  <FlaskIcon size={15} />
                  <div>
                    <strong>Specialisation Fee:</strong> {inr(charge("specialization_fee"))} per year from the 2nd
                    year where a specialisation applies (not included above).
                  </div>
                </div>
              )}
              {concessionGroups.length > 0 && (
                <div className="note-item special-scholarship">
                  <HeartHandIcon size={15} />
                  <div>
                    <details>
                      <summary>
                        <strong>{config.special_concessions.length} Special Category Concessions</strong> (per year,
                        subject to document verification). Tap to view.
                      </summary>
                      {concessionGroups.map(([amount, labels]) => (
                        <p key={amount} style={{ margin: "6px 0 0" }}>
                          <strong>{inr(amount)} per year:</strong> {labels.join("; ")}.
                        </p>
                      ))}
                    </details>
                  </div>
                </div>
              )}
              <div className="note-item">
                <InfoIcon size={15} />
                <div>
                  {isConfirmed ? "Checked against the official fee table. " : ""}
                  This is an estimate for {year}. The scholarship is subject to marksheet verification and admission
                  depends on seat availability.
                </div>
              </div>
            </div>

            {/* Optional callback request */}
            <div className="calc-auth-box">
              <div className="calc-auth-header">
                <ShieldCheckIcon size={15} />
                <span>Request an Admissions Counsellor Callback (Optional)</span>
              </div>
              <p className="calc-auth-subtext">
                Share this estimate with the admissions team and get guidance for {year} admissions.
              </p>
              {leadSuccessMsg ? (
                <div className="calc-lead-success">
                  <CheckIcon size={16} />
                  <span>{leadSuccessMsg}</span>
                </div>
              ) : (
                <div className="calc-callback-form-wrap">
                  <div className="calc-auth-grid">
                    <div className="calc-field">
                      <label htmlFor="calc-student-name">Student Full Name</label>
                      <input
                        id="calc-student-name"
                        type="text"
                        className="calc-input"
                        placeholder="Enter full name"
                        value={studentName}
                        onChange={(e) => {
                          setStudentName(e.target.value);
                          if (callbackError) setCallbackError(null);
                        }}
                      />
                    </div>
                    <div className="calc-field">
                      <label htmlFor="calc-student-phone">10-Digit Mobile Number</label>
                      <input
                        id="calc-student-phone"
                        type="tel"
                        className="calc-input"
                        placeholder="e.g. 9876543210"
                        inputMode="numeric"
                        autoComplete="tel"
                        value={studentPhone}
                        onChange={(e) => {
                          const digits = e.target.value.replace(/\D/g, "").slice(0, 10);
                          setStudentPhone(digits);
                          if (callbackError) setCallbackError(null);
                        }}
                        maxLength={10}
                      />
                    </div>
                  </div>
                  <label className="calc-consent-label">
                    <input
                      type="checkbox"
                      checked={consentAgreed}
                      onChange={(e) => setConsentAgreed(e.target.checked)}
                    />
                    <span>I agree that SR University may contact me about admissions.</span>
                  </label>
                  {callbackError && (
                    <div className="calc-error-banner">
                      <span>{callbackError}</span>
                    </div>
                  )}
                  <button type="button" onClick={handleRequestCallback} className="calc-callback-btn">
                    Request Admissions Callback
                  </button>
                </div>
              )}
            </div>

            <div className="calc-footer-actions">
              <button type="button" className="btn-whatsapp" onClick={handleWhatsAppShare}>
                <span>💬 Send Estimate to WhatsApp</span>
              </button>
              <button type="button" className="btn-print" onClick={handlePrint}>
                <span>🖨️ Download / Print PDF</span>
              </button>
              <button
                type="button"
                className="btn-ask-buddy"
                onClick={() => {
                  onClose();
                  const hostelText = includeHostel ? `, with ${hostelLabel} hostel` : "";
                  onAskBuddy(
                    `I used the fee calculator for ${program.name} with ${parsed.display}. It shows a ${pct}% merit ` +
                      `scholarship and ${inr(estimate.netSem)} tuition per semester${hostelText}. ` +
                      `Please confirm this and tell me the next steps for admission.`
                  );
                }}
              >
                <MessageSquareIcon size={16} />
                <span>Ask SRU Buddy About This Fee</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
