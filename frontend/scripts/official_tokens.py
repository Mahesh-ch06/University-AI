"""Put the chat's off-brand colours behind `--o-*` tokens (v4.13.0, official widget look).

Each listed hex colour in the chat's stylesheets becomes `var(--o-<token>, <the same hex>)`:
- the full website defines no `--o-*` token, so it keeps exactly its current colours;
- the widget (`html[data-surface="widget"]`, src/styles/official-widget.css) defines them with the
  sru.edu.in palette, so every card, chip and form inside the widget follows the official look.

Idempotent: colours already inside `var(--o-…, …)` are left alone. Run from frontend/:
    python3 scripts/official_tokens.py            # rewrite the stylesheets
    python3 scripts/official_tokens.py --css      # print the token block for official-widget.css
"""
import re
import sys
from pathlib import Path

# token -> (official value on sru.edu.in, colours it replaces)
TOKENS = {
    "brand":        ("#194F90", "#0055a4 #004488 #004482 #0b3d75"),
    "brand-dark":   ("#123C6E", "#004382 #003e7a #003e7e #1e40af #1e3a8a"),
    "action":       ("#297DE5", "#2979e2 #2563eb #3b82f6 #1d4ed8 #0284c7 #0ea5e9 #6366f1 #4f46e5 "
                                "#7e22ce #8b5cf6 #a855f7 #9333ea #7c3aed #0f766e"),
    "action-dark":  ("#1F6BCB", "#1c66c9 #0369a1 #4338ca #6d28d9 #5b21b6"),
    "action-light": ("#8DBBF0", "#38bdf8 #818cf8 #60a5fa #93c5fd #a5b4fc #c084fc #c4b5fd #7dd3fc"),
    "tint":         ("#EFF8FF", "#e0f2fe #e0e7ff #eef2ff #f3e8ff #f5f3ff #dbeafe #e8f1fb #eff6ff #f0f9ff "
                                "#ede9fe #f0f7ff #cfe0ff #ccfbf1"),
    "tint-border":  ("#C1E3FC", "#bae6fd #c7d2fe #bfdbfe #e9d5ff #ddd6fe"),
    "ok":           ("#194F90", "#10b981 #15803d #16a34a #047857 #166534 #059669 #065f46"),
    "ok-light":     ("#8DBBF0", "#34d399 #4ade80"),
    "ok-tint":      ("#EFF8FF", "#dcfce7 #d1fae5 #ecfdf5 #ecfdf3 #f0fdf4 #e9f9ef #d6f5e1"),
    "ok-border":    ("#C1E3FC", "#bbf7d0 #b7ebc9 #86efac #a7f3d0"),
    "text":         ("#0F0F11", "#0f172a #1e293b #0a1b3a #111827"),
    "text-2":       ("#3A3B45", "#334155 #475569 #1f2937"),
    "muted":        ("#5D5E6C", "#64748b"),
    "faint":        ("#8B8C97", "#94a3b8 #93a4bf"),
    "line-strong":  ("#CFD3DA", "#cbd5e1"),
    "line":         ("#E4E6EB", "#e2e8f0"),
    "surface-2":    ("#F2F3F6", "#f1f5f9"),
    "surface":      ("#F7F8FA", "#f8fafc #f6f8fc"),
}
FILES = sorted(
    [p for p in Path("src/components").glob("*.css")]
    + [Path("src/pages/ChatPage.css"), Path("src/styles/polish.css")]
)
LOOKUP = {hexv: tok for tok, (_, olds) in TOKENS.items() for hexv in olds.split()}
HEX = re.compile(r"(var\(--o-[a-z0-9-]+,\s*)?(#[0-9a-fA-F]{6})\b")


def rewrite(text: str) -> tuple[str, int]:
    count = 0

    def sub(m: re.Match) -> str:
        nonlocal count
        if m.group(1):  # already tokenised
            return m.group(0)
        tok = LOOKUP.get(m.group(2).lower())
        if not tok:
            return m.group(0)
        count += 1
        return f"var(--o-{tok}, {m.group(2)})"

    return HEX.sub(sub, text), count


def css_block() -> str:
    return "\n".join(f"  --o-{tok}: {val};" for tok, (val, _) in TOKENS.items())


if __name__ == "__main__":
    if "--css" in sys.argv:
        print(css_block())
        sys.exit(0)
    total = 0
    for f in FILES:
        new, n = rewrite(f.read_text())
        if n:
            f.write_text(new)
        total += n
        print(f"{f}: {n}")
    print("total", total)
