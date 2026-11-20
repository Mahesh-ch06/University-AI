/**
 * Ensures legacy university numbers in assistant text are normalized to current official numbers:
 * - Admissions Helpline: 833 100 3030
 * - Campus Visit Helpline: 833 100 4040
 * And removes internal reference numbers/IDs so students are never shown a reference number.
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
    // Remove email lines for campus visits
    out = out.replace(/(?:-\s*)?Email:\s*info@sru\.edu\.in\s*\n?/gi, "");
    out = out.replace(/(?:-\s*)?Email\s+info@sru\.edu\.in\s*\n?/gi, "");
  } else {
    out = out.replace(/0870[\s-]?2818333(?:\s*(?:\/|or)\s*0870[\s-]?2818311)?/g, "833 100 3030");
    out = out.replace(/0870[\s-]?2818311/g, "833 100 3030");
    out = out.replace(/0870[\s-]?2818333/g, "833 100 3030");
  }

  // 4. Strip reference numbers/IDs completely
  // Handle (reference **654144b1**), (reference #654144b1), etc.
  out = out.replace(/\s*\(\s*reference\s*(?:\*\*)?[#]?[a-z0-9]+(?:\*\*)?\s*\)/gi, "");
  // Handle standalone lines like "Reference: #654144b1" or "Reference ID: #654144b1"
  out = out.replace(/(?:^|\n)\s*Reference(?:\s*ID)?:\s*#?[a-z0-9]+\s*(?:\n|$)/gi, "\n");
  // Handle inline "Reference: #654144b1"
  out = out.replace(/\s*\bReference(?:\s*ID)?:\s*#?[a-z0-9]+\b/gi, "");
  // Handle phrase like "and quote that reference, and they will remove it" -> "and they will remove it"
  out = out.replace(/\s*and quote that reference,?\s*/gi, " ");
  // Handle "with the reference"
  out = out.replace(/\s*with the reference\b/gi, "");

  // Clean up any double spaces before punctuation
  out = out.replace(/[ \t]{2,}/g, " ").replace(/\s+\./g, ".");

  return out;
}
