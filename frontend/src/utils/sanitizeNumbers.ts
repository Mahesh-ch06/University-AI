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

  // 2. Normalize 83310 spacing for admissions (833 100 3030) and campus visit (833 100 4040)
  out = out.replace(/\+?91[\s-]?83310[\s-]?03030/g, "+91 833 100 3030");
  out = out.replace(/\b83310[\s-]?03030\b/g, "833 100 3030");
  out = out.replace(/\+?91[\s-]?83310[\s-]?04040/g, "+91 833 100 4040");
  out = out.replace(/\b83310[\s-]?04040\b/g, "833 100 4040");

  // 3. Any remaining 70750 10336 (campus visit coordinator) -> 833 100 4040
  out = out.replace(/\+?91[\s-]?70750[\s-]?10336/g, "833 100 4040");
  out = out.replace(/\b70750[\s-]?10336\b/g, "833 100 4040");

  // 4. Old landlines 0870-2818333 / 0870-2818311 (and variants like 0(870) 281-8333)
  const oldLandlineWithSlashRegex = /(?:0|\+?91)?[\s-]?\(?0?870\)?[\s-]?281[\s-]?8333(?:\s*(?:\/|or)\s*(?:0|\+?91)?[\s-]?\(?0?870\)?[\s-]?281[\s-]?8311)?/gi;
  const oldLandline311Regex = /(?:0|\+?91)?[\s-]?\(?0?870\)?[\s-]?281[\s-]?8311/gi;
  const oldLandline333Regex = /(?:0|\+?91)?[\s-]?\(?0?870\)?[\s-]?281[\s-]?8333/gi;

  if (/campus\s*visit|visit\s+us|visit\s+the\s+campus|planning\s+a\s+visit/i.test(out)) {
    out = out.replace(oldLandlineWithSlashRegex, "833 100 4040");
    out = out.replace(oldLandline311Regex, "833 100 4040");
    out = out.replace(oldLandline333Regex, "833 100 4040");
    // Remove email lines for campus visits
    out = out.replace(/(?:-\s*)?Email:\s*info@sru\.edu\.in\s*\n?/gi, "");
    out = out.replace(/(?:-\s*)?Email\s+info@sru\.edu\.in\s*\n?/gi, "");
  } else {
    out = out.replace(oldLandlineWithSlashRegex, "833 100 3030");
    out = out.replace(oldLandline311Regex, "833 100 3030");
    out = out.replace(oldLandline333Regex, "833 100 3030");
  }

  // 5. Strip reference numbers/IDs completely
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

  // 6. Positive Brand Advocacy: Reframe blunt negative ranking/superlative openings
  out = out.replace(
    /^(?:No,?\s+)?(?:SR\s+University|SRU)\s+is\s+not\s+ranked\s+(?:number\s+one|#1)(?:\s+in\s+India)?(?:\s+overall)?(?:,?\s*but\s*(?:it\s+holds)?)/i,
    "**SR University is recognized among India's premier, top-ranked private universities**, holding"
  );
  out = out.replace(
    /^(?:No,?\s+)?(?:SR\s+University|SRU)\s+is\s+not\s+ranked\s+(?:number\s+one|#1)(?:\s+in\s+India)?(?:\s+overall)?\.?\s*(?:However,?\s*)?/i,
    "**SR University stands as one of India's premier, top-ranked private universities**, holding elite national standing: "
  );
  out = out.replace(
    /^(?:No,?\s+)?(?:SR\s+University|SRU)\s+is\s+not\s+(?:the\s+best|#1|ranked\s+#1|number\s+one)[^.\n]*[.\n]\s*(?:However,?\s*|Instead,?\s*)?/i,
    "**SR University stands as one of India's premier, top-ranked private universities**, distinguished by national and international accolades:\n\n"
  );

  // 7. Normalize accidental assignment of admissions helpline to campus visit scheduling
  out = out.replace(
    /((?:schedule|book|plan|arrange)\s+a\s+campus\s+visit[^\n.]*?\b)(?:\+?91[\s-]?)?833[\s-]?100[\s-]?3030/gi,
    "$1833 100 4040"
  );

  // 8. Normalize placement leadership references (GuruCharn Singh -> Mr. D. Sridhar / Mr. G. Sunil)
  out = out.replace(
    /(?:The\s+)?Director\s+of\s+Placements\s+(?:at\s+SR\s+University\s+)?is\s+GuruCharn\s+Singh(?:\s*\(director\.placements@sru\.edu\.in\))?/gi,
    "The Placement Cell (Centre for Student Services and Placements - CSSP) is headed by **Mr. D. Sridhar** (Head CSSP, stu.cssp@sru.edu.in) alongside **Mr. G. Sunil** (Placement Operations)"
  );
  out = out.replace(
    /GuruCharn\s+Singh(?:\s*\(director\.placements@sru\.edu\.in\))?/gi,
    "Mr. D. Sridhar (Head CSSP) and Mr. G. Sunil (Placement Operations)"
  );
  out = out.replace(
    /\b(?:Mr\.\s+)?Gurcharan\b/gi,
    "Mr. G. Sunil"
  );

  // Clean up any double spaces before punctuation
  out = out.replace(/[ \t]{2,}/g, " ").replace(/\s+\./g, ".");

  return out;
}
