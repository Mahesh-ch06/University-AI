/**
 * Fee card as a PNG image (v4.17.1), for sharing with family on WhatsApp and other apps.
 *
 * The image is drawn on a canvas from the SAME strings the card shows (amounts formatted by the backend fee
 * engine). Nothing is added, split or recalculated here. It carries no phone number, contact detail,
 * conversation id or chat message: only the programme, year, scholarship, semester table, first-year payable,
 * pending concessions (clearly marked) and a verification note.
 */
import { money, type SemesterBlock } from "../components/SemesterFeeTable";

/** The public scholarship calculator (same as the backend's FEE_PORTAL_URL; verified to open the calculator for a
 * new visitor with no session). */
export const SCHOLARSHIP_CALCULATOR_URL = "https://sru.edu.in/fee-scholarship/";
export const SRU_WEBSITE_URL = "https://sru.edu.in/";

export const SHARE_CAPTION =
  "Explore programmes and admissions at SR University in Warangal, Telangana.\n" +
  "Check your scholarship and get a personalized fee estimate with SRU Buddy.\n" +
  `Check your scholarship: ${SCHOLARSHIP_CALCULATOR_URL}\n` +
  `Learn more about SR University: ${SRU_WEBSITE_URL}`;

export interface FeeImageModel {
  heading: string; // "Fee estimate" / "Your fee summary"
  program: string;
  specialization?: string;
  academicYear?: string;
  scholarship?: string;
  semesters?: SemesterBlock[];
  confirmed?: { label: string; value: string };
  pendingTotal?: { label: string; value: string };
  pending?: string[];
  notes?: string[];
}

const W = 1080;
const PAD = 64;
const BRAND = "#194F90";
const INK = "#0F0F11";
const MUTED = "#5D5E6C";
const LINE = "#E4E6EB";
const PENDING = "#9A5B00";
const FONT = `"Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`;

function font(weight: number, size: number) {
  return `${weight} ${size}px ${FONT}`;
}

function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = (text || "").split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function rows(semesters: SemesterBlock[]): { label: string; kind: string }[] {
  const out: { label: string; kind: string }[] = [];
  for (const s of semesters) {
    for (const i of s.items || []) {
      const label = i.item || i.label || "";
      if (label && !out.some((r) => r.label === label)) out.push({ label, kind: i.kind || "" });
    }
  }
  return out;
}

/** Draws the card; returns the canvas height used (two passes: measure, then paint). */
function paint(ctx: CanvasRenderingContext2D, m: FeeImageModel, logo: HTMLImageElement | null, draw: boolean): number {
  const text = (s: string, x: number, y: number, f: string, color = INK, align: CanvasTextAlign = "left") => {
    if (!draw) return;
    ctx.font = f;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.fillText(s, x, y);
  };
  let y = 0;
  // Header band: SR University + SRU Buddy branding
  if (draw) {
    ctx.fillStyle = BRAND;
    ctx.fillRect(0, 0, W, 150);
  }
  if (draw && logo) {
    const h = 74;
    const w = (logo.width / logo.height) * h;
    ctx.drawImage(logo, PAD, 38, w, h);
  } else {
    text("SR University", PAD, 98, font(800, 44), "#FFFFFF");
  }
  text("SRU Buddy", W - PAD, 78, font(700, 30), "#FFFFFF", "right");
  text(m.heading, W - PAD, 116, font(500, 24), "#D6E4F5", "right");
  y = 150 + 72;

  // Programme, specialisation, year
  ctx.font = font(800, 44);
  for (const ln of wrap(ctx, m.program, W - 2 * PAD)) {
    text(ln, PAD, y, font(800, 44));
    y += 54;
  }
  if (m.specialization) {
    text(m.specialization, PAD, y, font(600, 28), MUTED);
    y += 40;
  }
  if (m.academicYear) {
    text(`Academic year ${m.academicYear} · first year`, PAD, y, font(500, 28), MUTED);
    y += 40;
  }
  if (m.scholarship) {
    y += 10;
    ctx.font = font(700, 26);
    const lines = wrap(ctx, `Scholarship: ${m.scholarship}`, W - 2 * PAD - 48);
    const tw = Math.min(Math.max(...lines.map((l) => ctx.measureText(l).width)) + 48, W - 2 * PAD);
    const th = 18 + lines.length * 34;
    if (draw) {
      ctx.fillStyle = "#E8F1FB";
      ctx.beginPath();
      ctx.roundRect(PAD, y - 34, tw, th, 22);
      ctx.fill();
    }
    lines.forEach((ln, k) => text(ln, PAD + 24, y + k * 34, font(700, 26), BRAND));
    y += th - 4;
  }

  // Confirmed and pending totals, clearly separated
  y += 24;
  if (m.confirmed) {
    if (draw) {
      ctx.fillStyle = "#F4F6F9";
      ctx.beginPath();
      ctx.roundRect(PAD, y, W - 2 * PAD, 140, 22);
      ctx.fill();
    }
    text(m.confirmed.label, PAD + 32, y + 50, font(600, 26), MUTED);
    text(m.confirmed.value, PAD + 32, y + 112, font(800, 58), INK);
    y += 140 + 20;
  }
  if (m.pendingTotal) {
    if (draw) {
      ctx.strokeStyle = "#F2C46D";
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 8]);
      ctx.beginPath();
      ctx.roundRect(PAD, y, W - 2 * PAD, 120, 22);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    text(m.pendingTotal.label, PAD + 32, y + 46, font(600, 24), PENDING);
    text(m.pendingTotal.value, PAD + 32, y + 98, font(800, 44), PENDING);
    text("Pending approval", W - PAD - 32, y + 98, font(600, 24), PENDING, "right");
    y += 120 + 20;
  }

  // Semester table
  const sems = (m.semesters || []).filter(Boolean);
  if (sems.length) {
    y += 30;
    text("Semester by semester", PAD, y, font(700, 26), MUTED);
    y += 26;
    const colW = 210;
    const firstW = W - 2 * PAD - colW * sems.length;
    const rowH = 56;
    if (draw) {
      ctx.fillStyle = "#E8F1FB";
      ctx.fillRect(PAD, y, W - 2 * PAD, rowH);
    }
    text("Fee head", PAD + 20, y + 37, font(700, 24), BRAND);
    sems.forEach((s, i) =>
      text(`Sem ${s.semester}`, PAD + firstW + colW * (i + 1) - 20, y + 37, font(700, 24), BRAND, "right"));
    y += rowH;
    for (const r of rows(sems)) {
      ctx.font = font(500, 26);
      const lines = wrap(ctx, r.label + (r.kind === "concession" ? " (if approved)" : r.kind === "optional" ? " (optional)" : ""),
        firstW - 30);
      const h = Math.max(rowH, 18 + lines.length * 32);
      lines.forEach((ln, k) => text(ln, PAD + 20, y + 38 + k * 32, font(500, 26), r.kind === "concession" ? PENDING : INK));
      sems.forEach((s, i) => {
        const it = (s.items || []).find((x) => (x.item || x.label) === r.label);
        text(it ? money(it.formatted ?? it.amount) : "—", PAD + firstW + colW * (i + 1) - 20, y + 38, font(600, 26),
          INK, "right");
      });
      y += h;
      if (draw) {
        ctx.fillStyle = LINE;
        ctx.fillRect(PAD, y - 1, W - 2 * PAD, 2);
      }
    }
    if (draw) {
      ctx.fillStyle = "#F4F6F9";
      ctx.fillRect(PAD, y, W - 2 * PAD, rowH + 4);
    }
    text("Semester payable", PAD + 20, y + 40, font(800, 26));
    sems.forEach((s, i) =>
      text(money(s.formatted_total ?? s.total), PAD + firstW + colW * (i + 1) - 20, y + 40, font(800, 26), INK, "right"));
    y += rowH + 4;
  }

  // Pending items
  if (m.pending && m.pending.length) {
    y += 46;
    text("Awaiting verification", PAD, y, font(700, 26), PENDING);
    y += 12;
    ctx.font = font(500, 25);
    for (const p of m.pending) {
      for (const [k, ln] of wrap(ctx, p, W - 2 * PAD - 30).entries()) {
        y += 36;
        text((k === 0 ? "• " : "  ") + ln, PAD, y, font(500, 25), INK);
      }
    }
  }
  if (m.notes && m.notes.length) {
    y += 20;
    ctx.font = font(500, 24);
    for (const n of m.notes) {
      for (const ln of wrap(ctx, n, W - 2 * PAD)) {
        y += 34;
        text(ln, PAD, y, font(500, 24), MUTED);
      }
    }
  }

  // Verification note and footer
  y += 54;
  if (draw) {
    ctx.fillStyle = LINE;
    ctx.fillRect(PAD, y - 30, W - 2 * PAD, 2);
  }
  ctx.font = font(500, 23);
  const disclaimer =
    "Estimate from the SR University fee circular" + (m.academicYear ? ` ${m.academicYear}` : "") +
    ". Merit scholarships and special concessions apply only after the Admissions Office verifies the documents. " +
    "Please confirm the final fee with SR University.";
  for (const ln of wrap(ctx, disclaimer, W - 2 * PAD)) {
    text(ln, PAD, y, font(500, 23), MUTED);
    y += 32;
  }
  y += 18;
  text("Generated with SRU Buddy · sru.edu.in", PAD, y, font(700, 24), BRAND);
  return y + 56;
}

export async function renderFeeCardPng(model: FeeImageModel): Promise<Blob> {
  const logo = await loadImage("/sru-logo-white.png");
  try {
    await (document as any).fonts?.ready;
  } catch {
    /* fonts optional */
  }
  const measure = document.createElement("canvas").getContext("2d");
  if (!measure) throw new Error("Canvas is not available");
  const height = paint(measure, model, logo, false);
  const canvas = document.createElement("canvas");
  const scale = 1;
  canvas.width = W * scale;
  canvas.height = Math.ceil(height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas is not available");
  ctx.scale(scale, scale);
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(0, 0, W, height);
  paint(ctx, model, logo, true);
  return await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Could not create the image"))), "image/png"));
}

export type ShareOutcome = "shared" | "cancelled" | "unsupported" | "failed";

/** Native share of the PNG with its caption. Returns "unsupported" when this browser / frame cannot share files
 * (the caller then offers Download / Copy caption / Copy image). Never reports a text-only share as an image. */
export async function shareFeeCardImage(blob: Blob, fileName: string, title: string): Promise<ShareOutcome> {
  const file = new File([blob], fileName, { type: "image/png" });
  const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
  if (!nav.share || !nav.canShare || !nav.canShare({ files: [file] })) return "unsupported";
  const withCaption: ShareData = { files: [file], title, text: SHARE_CAPTION };
  try {
    await nav.share(nav.canShare(withCaption) ? withCaption : { files: [file], title });
    return "shared";
  } catch (err) {
    const name = (err as Error)?.name;
    if (name === "AbortError") return "cancelled"; // the student closed the share sheet
    return name === "NotAllowedError" ? "unsupported" : "failed"; // e.g. the click's activation expired
  }
}

export function downloadBlob(blob: Blob, fileName: string): boolean {
  try {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 4000);
    return true;
  } catch {
    return false;
  }
}

export function canCopyImage(): boolean {
  return typeof (window as any).ClipboardItem === "function" && !!navigator.clipboard?.write;
}

export async function copyImage(blob: Blob): Promise<boolean> {
  try {
    await navigator.clipboard.write([new (window as any).ClipboardItem({ "image/png": blob })]);
    return true;
  } catch {
    return false;
  }
}

export async function copyCaption(): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(SHARE_CAPTION);
    return true;
  } catch {
    return false;
  }
}
