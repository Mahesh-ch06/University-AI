import "./SemesterFeeTable.css";

/**
 * Semester-by-semester fee table, shared by every fee card in the chat.
 *
 * It only DISPLAYS what the backend's fee engine (app/sru_agent/fees.py) sent: one column per semester,
 * one row per fee head, the semester payable at the foot. No amount is added, split or computed here.
 * Accepts the engine's two shapes: {item, amount, kind} (calculate_fee) or {label, formatted, kind}.
 */
export interface SemesterBlock {
  semester: number;
  items: Array<{ item?: string; label?: string; amount?: string | number; formatted?: string; kind?: string }>;
  total?: string | number;
  formatted_total?: string;
}

function money(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    const sign = value < 0 ? "− " : "";
    return `${sign}₹${Math.abs(Math.round(value)).toLocaleString("en-IN")}`;
  }
  const text = String(value).trim();
  return text.startsWith("-") ? `− ${text.slice(1)}` : text;
}

const KIND_NOTE: Record<string, string> = { optional: "optional", concession: "if approved" };

export function SemesterFeeTable({
  semesters,
  caption,
  compact = false,
}: {
  semesters: SemesterBlock[] | undefined;
  caption?: string;
  compact?: boolean;
}) {
  const sems = (semesters || []).filter(Boolean);
  if (sems.length === 0) return null;
  const rows: { label: string; kind: string }[] = [];
  for (const s of sems) {
    for (const i of s.items || []) {
      const label = i.item || i.label || "";
      if (label && !rows.some((r) => r.label === label)) rows.push({ label, kind: i.kind || "" });
    }
  }
  const cell = (s: SemesterBlock, label: string) => {
    const it = (s.items || []).find((i) => (i.item || i.label) === label);
    return it ? money(it.formatted ?? it.amount) : "—";
  };
  return (
    <div className={`sft-wrap${compact ? " sft-compact" : ""}`}>
      <table className="sft-table">
        {caption && <caption className="sft-caption">{caption}</caption>}
        <thead>
          <tr>
            <th scope="col">Fee head</th>
            {sems.map((s) => (
              <th scope="col" className="sft-num" key={s.semester}>
                Sem {s.semester}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className={r.kind ? `sft-row--${r.kind}` : undefined}>
              <th scope="row">
                <span className="sft-label">{r.label}</span>
                {KIND_NOTE[r.kind] && <span className="sft-tag">{KIND_NOTE[r.kind]}</span>}
              </th>
              {sems.map((s) => {
                const v = cell(s, r.label);
                return (
                  <td key={s.semester} className={`sft-num${v === "—" ? " sft-empty" : ""}`}>
                    {v}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Payable</th>
            {sems.map((s) => (
              <td key={s.semester} className="sft-num">
                {money(s.formatted_total ?? s.total)}
              </td>
            ))}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
