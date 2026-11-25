/**
 * Logic for the Fee & Scholarship Calculator. It does NO fee arithmetic.
 *
 * Every rupee shown comes from the ONE fee engine in the backend (app/sru_agent/fees.py):
 *   - /api/v1/agent/fee-config gives, for every programme and scholarship slab, the semester-wise
 *     payable the engine worked out (a generated copy is bundled as src/data/feeConfig.json so the
 *     calculator can draw instantly);
 *   - /api/v1/agent/calculate gives the exact schedule for the student's own score and options
 *     (hostel, bus).
 * This file only understands what the student typed, finds the matching slab row, and reads the
 * engine's numbers. Run the checks with:  npm run test:calc
 */

export interface FeeSlabSemester {
  semester: number;
  total: number;
  items: { label: string; amount: number; kind: string }[];
}

export interface FeeSlab {
  scholarship_percent: number;
  /** Text to show, per exam: "80 – 91.9%", "8,001 – 20,000". */
  ranges: Record<string, string>;
  /** Numbers to match a score against, per exam: [min, max]. */
  bounds: Record<string, number[]>;
  annual_tuition: number;
  saving_per_year: number;
  tuition_per_semester: number;
  semesters: FeeSlabSemester[];
  first_year_total: number;
  course_total: number | null;
  years: { year: number; annual_tuition: number; total: number }[];
}

export interface FeeProgram {
  id: string;
  name: string;
  level: string;
  tuition_per_year: number;
  yearly_increase: number;
  duration_years: number | null;
  minimum_percent: number;
  minimum_confirmed: boolean;
  eligibility: string;
  specialization_fee_applies: boolean;
  exams: { key: string; label: string }[];
  slabs: FeeSlab[];
}

export interface FeeCharge {
  label: string;
  amount?: number;
  non_ac?: number;
  ac?: number;
  kind: string;
}

export interface FeeConfig {
  status: string;
  academic_year: string;
  source: string;
  charges: Record<string, FeeCharge>;
  hostel_per_year: Record<string, number>;
  hostel_labels: Record<string, string>;
  hostel_status: string;
  special_concessions: { key: string; label: string; amount: number }[];
  terms: string[];
  programs: FeeProgram[];
}

export interface ParsedScore {
  status: "empty" | "ok" | "invalid";
  /** The exam this score belongs to. May differ from the one selected in the dropdown. */
  examKey: string;
  /** True when the typed text itself named a different exam ("EAPCET 9000") or could only be one. */
  switched: boolean;
  /** Percentage, percentile, rank or IB score, ready to compare with slab bounds. */
  value?: number;
  /** How to show the score back to the student: "Rank 9,000", "850/1000 (85%)". */
  display: string;
  /** Why the entry could not be used. */
  message?: string;
}

export interface EstimateSemester {
  semester: number;
  total: number;
  items: { label: string; amount: number; kind: string }[];
}

export interface Estimate {
  scholarshipPercent: number;
  tuitionYear: number;
  netYear: number;
  netSem: number;
  savingYear: number;
  semesters: EstimateSemester[];
  firstYearTotal: number;
  /** Total payable per year of the course (empty when the duration is not in the fee policy). */
  years: number[];
  fullCourseTotal: number | null;
  applicationFee: number;
  flags: string[];
  nextSlab: { percent: number; requires: string; extraSavingYear: number } | null;
}

const PERCENT_EXAMS = new Set(["state_board", "cbse"]);

/** Words in the typed text that name an exam. Checked in this order. */
const EXAM_HINTS: { key: string; pattern: RegExp }[] = [
  { key: "eapcet_rank", pattern: /\b(?:eapcet|eamcet|emcet|rank)\b/i },
  { key: "jee_percentile", pattern: /\bjee\b|percentile|%\s*ile/i },
  { key: "ib", pattern: /\bib\b/i },
  { key: "cbse", pattern: /\b(?:cbse|icse)\b/i },
  { key: "state_board", pattern: /\b(?:inter|intermediate|ipe|state\s*board|12th|10\s*\+\s*2)\b/i },
];

export function inr(amount: number): string {
  return "₹" + Math.round(amount).toLocaleString("en-IN");
}

/** "₹2,55,000" -> 255000 */
export function rupees(text: string | null | undefined): number {
  const digits = (text || "").replace(/[^\d]/g, "");
  return digits ? parseInt(digits, 10) : 0;
}

function examLabel(program: FeeProgram, key: string): string {
  return program.exams.find((e) => e.key === key)?.label || key;
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

/**
 * Understand what the student typed: "88%", "850", "850/1000", "EAPCET 9000", "rank 4,500",
 * "jee 92.4", "IB 36". If the text names an exam, or can only belong to one, that exam is used
 * even when a different one is selected in the dropdown.
 */
export function parseScore(program: FeeProgram, selectedExamKey: string, raw: string): ParsedScore {
  const text = (raw || "").trim();
  const offered = program.exams.map((e) => e.key);
  const fallbackExam = offered.includes(selectedExamKey) ? selectedExamKey : offered[0];
  if (!text) return { status: "empty", examKey: fallbackExam, switched: false, display: "" };

  const invalid = (message: string, examKey = fallbackExam): ParsedScore => ({
    status: "invalid", examKey, switched: false, display: "", message,
  });

  // 1. Which exam? A keyword in the text wins over the dropdown.
  let examKey = fallbackExam;
  const hint = EXAM_HINTS.find((h) => h.pattern.test(text));
  if (hint) {
    if (!offered.includes(hint.key)) {
      // "cbse 92" on a PG course still means a percentage; other exams are simply not used there.
      if (PERCENT_EXAMS.has(hint.key) && offered.includes("state_board")) {
        examKey = "state_board";
      } else {
        const names: Record<string, string> = {
          eapcet_rank: "An EAPCET rank", jee_percentile: "A JEE Main percentile", ib: "An IB score",
        };
        return invalid(`${names[hint.key] || "That exam"} is not used for ${program.name}. ` +
          `Please enter your ${examLabel(program, fallbackExam)}.`);
      }
    } else {
      examKey = hint.key;
    }
  }

  // 2. The numbers. "4,500" is one number; "850/1000" or "850 out of 1000" is a fraction.
  const cleaned = text.replace(/(\d),(?=\d)/g, "$1");
  const fraction = cleaned.match(/(\d+(?:\.\d+)?)\s*(?:\/|out\s+of)\s*(\d+(?:\.\d+)?)/i);
  const first = cleaned.match(/\d+(?:\.\d+)?/);
  if (!first) return invalid("Please type your marks, percentage or rank as a number.", examKey);
  const num = parseFloat(first[0]);
  const hasPercentSign = /\d\s*%(?!\s*ile)/i.test(cleaned);

  // 3. Text that can only be one kind of score, whatever is selected.
  if (!hint) {
    if (fraction || hasPercentSign) {
      if (!PERCENT_EXAMS.has(examKey)) examKey = offered.includes("state_board") ? "state_board" : examKey;
    } else if (num > 1000 && offered.includes("eapcet_rank")) {
      examKey = "eapcet_rank"; // marks never exceed 1000, so a bigger number is a rank
    }
  }
  const switched = examKey !== fallbackExam;
  const ok = (value: number, display: string): ParsedScore => ({ status: "ok", examKey, switched, value, display });

  if (examKey === "eapcet_rank") {
    if (fraction || hasPercentSign) return invalid("An EAPCET rank is a whole number, for example 4500.", examKey);
    const rank = Math.round(num);
    if (rank < 1) return invalid("Please enter a valid EAPCET rank, for example 4500.", examKey);
    return ok(rank, `EAPCET rank ${rank.toLocaleString("en-IN")}`);
  }
  if (examKey === "jee_percentile") {
    if (num > 100) return invalid("A JEE Main percentile is between 0 and 100.", examKey);
    return ok(round2(num), `JEE Main ${round2(num)} percentile`);
  }
  if (examKey === "ib") {
    if (num > 45) return invalid("An IB Diploma score is out of 45.", examKey);
    return ok(Math.round(num), `IB score ${Math.round(num)}/45`);
  }

  // Percentage exams: a percentage, a fraction, or raw marks.
  if (fraction) {
    const got = parseFloat(fraction[1]);
    const max = parseFloat(fraction[2]);
    if (max <= 0 || got > max) return invalid("Marks obtained cannot be more than the maximum marks.", examKey);
    const pct = round2((got / max) * 100);
    return ok(pct, `${got}/${max} (${pct}%)`);
  }
  if (num <= 100) return ok(round2(num), `${round2(num)}%`);
  if (hasPercentSign) return invalid("A percentage cannot be more than 100.", examKey);
  if (examKey === "cbse" && num <= 500) {
    const pct = round2((num / 500) * 100);
    return ok(pct, `${num}/500 (${pct}%)`);
  }
  if (num <= 1000) {
    const pct = round2(num / 10);
    return ok(pct, `${num}/1000 (${pct}%)`);
  }
  return invalid("That is more than the maximum marks. Enter marks out of 1000, or a percentage.", examKey);
}

/** Scholarship % for a score. 0 when the score is outside every slab. */
export function matchSlab(program: FeeProgram, examKey: string, value: number): number {
  for (const slab of program.slabs) {
    const b = slab.bounds[examKey];
    if (b && value >= b[0] && value <= b[1]) return slab.scholarship_percent;
  }
  return 0;
}

/** "Merit scholarship starts at 60%" / "Rank scholarships cover ranks up to 20,000". */
export function scholarshipStartText(program: FeeProgram, examKey: string): string {
  const withExam = program.slabs.filter((s) => s.bounds[examKey]);
  if (!withExam.length) return "";
  if (examKey === "eapcet_rank") {
    const worstRank = Math.max(...withExam.map((s) => s.bounds[examKey][1]));
    return `Rank scholarships cover EAPCET ranks up to ${worstRank.toLocaleString("en-IN")}`;
  }
  const lowest = Math.min(...withExam.map((s) => s.bounds[examKey][0]));
  if (examKey === "ib") return `Merit scholarship starts at an IB score of ${lowest}`;
  if (examKey === "jee_percentile") return `Merit scholarship starts at ${lowest} percentile`;
  return `Merit scholarship starts at ${lowest}%`;
}

/** The next higher slab for this exam (what it needs and the extra saving the engine computed). */
function nextSlabFor(program: FeeProgram, pct: number, examKey: string, current: FeeSlab | undefined) {
  const better = program.slabs
    .filter((s) => s.scholarship_percent > pct && s.bounds[examKey])
    .sort((a, b) => a.scholarship_percent - b.scholarship_percent)[0];
  if (!better) return null;
  return {
    percent: better.scholarship_percent,
    requires: `${examLabel(program, examKey)}: ${better.ranges[examKey]}`,
    extraSavingYear: better.saving_per_year - (current?.saving_per_year || 0),
  };
}

/**
 * The day-scholar estimate for one scholarship %, read straight from the engine's slab row
 * (no arithmetic here). Hostel / bus estimates come from the backend (estimateFromBackend).
 */
export function estimateFromConfig(config: FeeConfig, program: FeeProgram, scholarshipPercent: number,
  examKey: string): Estimate {
  const slab = program.slabs.find((s) => s.scholarship_percent === scholarshipPercent)
    || program.slabs.find((s) => s.scholarship_percent === 0) as FeeSlab;
  return {
    scholarshipPercent: slab.scholarship_percent,
    tuitionYear: program.tuition_per_year,
    netYear: slab.annual_tuition,
    netSem: slab.tuition_per_semester,
    savingYear: slab.saving_per_year,
    semesters: slab.semesters,
    firstYearTotal: slab.first_year_total,
    years: slab.years.map((y) => y.total),
    fullCourseTotal: slab.course_total,
    applicationFee: config.charges.application_fee?.amount || 0,
    flags: [],
    nextSlab: nextSlabFor(program, slab.scholarship_percent, examKey, slab),
  };
}

/** What to send to POST /api/v1/agent/calculate for this score. */
export function calculateParams(programId: string, parsed: ParsedScore, hostelKey: string, transport = false) {
  const v = parsed.status === "ok" ? parsed.value : undefined;
  return {
    program: programId,
    board: parsed.examKey === "cbse" ? "cbse" : "state_board",
    percent: PERCENT_EXAMS.has(parsed.examKey) ? v : undefined,
    eapcet_rank: parsed.examKey === "eapcet_rank" ? v : undefined,
    jee_percentile: parsed.examKey === "jee_percentile" ? v : undefined,
    ib_score: parsed.examKey === "ib" ? v : undefined,
    hostel: hostelKey || "none",
    transport,
  };
}

/** The backend's answer (the engine's schedule for this exact score and options) in the Estimate shape. */
export function estimateFromBackend(res: any): Estimate {
  const sem = (block: any, n: number): EstimateSemester => ({
    semester: n,
    total: rupees(block?.total),
    items: (block?.items || []).map((i: any) => ({ label: i.item, amount: rupees(i.amount), kind: i.kind })),
  });
  return {
    scholarshipPercent: Number(res.scholarship_percent) || 0,
    tuitionYear: rupees(res.tuition_first_year),
    netYear: rupees(res.tuition_first_year_after_scholarship),
    netSem: rupees(res.per_semester_after_scholarship),
    savingYear: rupees(res.saving_first_year),
    semesters: [sem(res.semester_1, 1), sem(res.semester_2, 2)],
    firstYearTotal: rupees(res.first_year_total_payable),
    years: Array.isArray(res.year_by_year) ? res.year_by_year.map((y: any) => rupees(y.total_payable)) : [],
    fullCourseTotal: res.full_course_total ? rupees(res.full_course_total) : null,
    applicationFee: rupees(res.application_fee),
    flags: Array.isArray(res.flags) ? res.flags : [],
    nextSlab: res.next_scholarship_slab
      ? {
          percent: res.next_scholarship_slab.scholarship_percent,
          requires: res.next_scholarship_slab.requires,
          extraSavingYear: rupees(res.next_scholarship_slab.extra_saving_first_year),
        }
      : null,
  };
}
