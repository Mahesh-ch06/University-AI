/**
 * Ensures legacy university numbers in assistant text are normalized to current official numbers:
 * - Admissions Helpline: 833 100 3030
 * - Campus Visit Helpline: 833 100 4040
 */
export function sanitizeHelplineNumbers(text: string): string {
  if (!text) return text;
  let out = text;

  // 1. Campus visit guidance text block with old contacts
  out = out.replace(
    /(?:-\s*)?Call\s+0870-2818333\s+or\s+0870-2818311\s*\n\s*(?:-\s*)?Call\s+or\s+WhatsApp\s+\+?91\s*70750\s*10336/gi,
    "- Call or WhatsApp: 833 100 4040"
  );
  out = out.replace(
    /Call\s+0870-2818333\s+or\s+0870-2818311\s*\n\s*Call\s+or\s+WhatsApp\s+\+?91\s*70750\s*10336/gi,
    "Call or WhatsApp: 833 100 4040"
  );

  // 2. Any remaining 70750 10336 (campus visit coordinator) -> 833 100 4040
  out = out.replace(/\+?91[\s-]?70750[\s-]?10336/g, "833 100 4040");
  out = out.replace(/\b70750[\s-]?10336\b/g, "833 100 4040");

  // 3. Old landlines 0870-2818333 / 0870-2818311
  if (/campus\s*visit|visit\s+us|visit\s+the\s+campus|planning\s+a\s+visit/i.test(out)) {
    out = out.replace(/0870[\s-]?2818333(?:\s*(?:\/|or)\s*0870[\s-]?2818311)?/g, "833 100 4040");
    out = out.replace(/0870[\s-]?2818311/g, "833 100 4040");
  } else {
    out = out.replace(/0870[\s-]?2818333(?:\s*(?:\/|or)\s*0870[\s-]?2818311)?/g, "833 100 3030");
    out = out.replace(/0870[\s-]?2818311/g, "833 100 3030");
    out = out.replace(/0870[\s-]?2818333/g, "833 100 3030");
  }

  return out;
}
