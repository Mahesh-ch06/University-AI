"""The fee evaluation agent (v4.11.0): from eligibility to a personalised final fee.

    eligibility result -> qualification confirmed -> special concessions offered -> special consideration
    (pending verification) -> academic scholarship (existing rules) -> hostel / transport -> final fee card

This is a planner, not a fixed script. The conversation state (conv_state["fee_eval"]) stores only the
student's SELECTIONS: programme, chosen concession and whether its proof is ready, whether they want the
scholarship checked, hostel and transport. Every amount is computed when it is shown, from the official fee
data (fees.calculate_fee) and the marks in the profile, so a change of marks, programme or hostel is reflected
at once and nothing stale or double-counted is carried.

Rules that never bend:
  * a special concession is never approved here: it is "pending verification" until the Admissions Office
    checks the proof, and it is kept out of the confirmed payable amount;
  * an academic scholarship comes only from the fee-card rules for the marks the student gave; marks that are
    a projection (exam not finished) make it an estimate, also kept out of the confirmed amount;
  * one concession at a time (choosing another replaces it), and the scholarship is deducted once;
  * the final card is shown only when the steps are done, or when the student asks for it (then the open
    steps are listed as such).

decide() is pure: it returns what to do; agent.py does the I/O (state, profile, scholarship steps, cards).
"""
from __future__ import annotations

import hashlib
import re

from . import config, fee_intake, fee_plan, fees

KEY = "fee_eval"

PROGRAM_CHIPS = ["B.Tech CSE", "B.Tech ECE", "B.Tech AI & Robotics", "BBA"]
NONE_APPLY = "None of these apply"
SHOW_FEE = "Show my final fee"
RESUME = "↩️ Continue my fee estimate"
HOSTEL_CHOICES = [  # (chip, key); amounts are added to the chip label from the fee data
    ("AC 4-sharing", "ac_4"), ("AC 3-sharing", "ac_3"),
    ("Non-AC 4-sharing", "non_ac_4"), ("Non-AC 3-sharing", "non_ac_3"),
]
NO_HOSTEL = "No hostel, I'm a day scholar"

_YES = re.compile(r"^\s*(?:yes|yeah|yep|yup|sure|ok(?:ay)?|please|go\s+ahead|of\s+course|haa?n?|avunu|y|ha|haan|ji|"
                  r"kavali)\b",
                  re.IGNORECASE)
_NO = re.compile(r"^\s*(?:no|nope|nah|none|not\s+(?:now|yet|interested|needed|required)|skip|later|n|ledu|vaddu|nahi|"
                 r"nahin)\b",
                 re.IGNORECASE)
# The "Special Consideration" tile (and the student asking for it). "What special category concessions are
# there?" is an information question, answered with the concessions table, not an evaluation.
_SPECIAL = re.compile(r"\bspecial\s+considerations?\b", re.IGNORECASE)
_FINAL = re.compile(
    r"\b(?:final\s+fee|fee\s+summary|fee\s+card|final\s+(?:amount|payable|card)|show\s+my\s+(?:final\s+)?fee|"
    r"how\s+much\s+(?:will|would|do|should|must)\s+i\s+(?:have\s+to\s+)?pay|what\s+(?:will|would)\s+i\s+pay|"
    r"total\s+(?:i\s+)?pay(?:able)?|my\s+total\s+fee|fee\s+chart|fee\s+plan|"
    r"(?:full|complete|whole|entire|total)\s+fee\s+(?:chart|plan|breakdown|details)|"
    r"prepare\s+(?:my|the|a)\s+(?:full\s+|complete\s+|whole\s+)?fee|give\s+(?:me\s+)?(?:the\s+)?final)\b",
    re.IGNORECASE)
_PAY_Q = re.compile(r"how\s+much\b.{0,30}\b(?:will|would|do|should|must|have\s+to)\s+(?:i\s+)?(?:have\s+to\s+)?pay|"
                    r"what\s+(?:will|would)\s+i\s+pay", re.IGNORECASE)
_EXPLICIT_FINAL = re.compile(r"\b(?:final|summary|chart|plan|breakdown|total)\b", re.IGNORECASE)
_WRAP_UP = re.compile(r"^\s*(?:ok(?:ay)?\s+)?(?:thanks?|thank\s+you|thx|ty|bye|goodbye|that'?s\s+all|done|"
                      r"ok(?:ay)?|cool|got\s+it|fine)\b[\s!.]*$", re.IGNORECASE)
_CHANGE_CONCESSION = re.compile(r"\b(?:change|different|another|other|switch)\b.{0,20}\b(?:concession|consideration|category)\b",
                                re.IGNORECASE)
_REMOVE_CONCESSION = re.compile(r"\b(?:remove|drop|cancel|without|no)\b.{0,12}\b(?:concession|consideration)\b",
                                re.IGNORECASE)
_REMOVE_HOSTEL = re.compile(r"\b(?:remove|drop|without|no)\s+(?:the\s+)?hostel\b|\bday\s*scholar\b", re.IGNORECASE)
_CHANGE_HOSTEL = re.compile(r"\b(?:change|add|include|switch)\b.{0,12}\bhostel\b", re.IGNORECASE)
# "Find me the lowest fee" (v4.12.0): the agent takes the goal, shows its plan and runs every check itself.
_LOWEST = re.compile(
    r"\b(?:lowest|cheapest|minimum|least|lower|reduce|less)\b.{0,30}\b(?:fee|fees|cost|tuition|pay|amount)\b"
    r"|\b(?:maximum|max|best|highest|biggest)\s+(?:possible\s+)?(?:scholarship|discount|concession|saving)s?\b"
    r"|\bhow\s+(?:can|do|to)\s+(?:i\s+)?(?:pay\s+less|save\s+(?:on|money)|reduce\s+(?:my\s+)?fee)",
    re.IGNORECASE)
ENTRANCE_CHIPS = ["Add my EAPCET rank", "Add my JEE Main percentile", "No entrance exam"]
_CONTINUE = re.compile(r"continue\s+my\s+fee|resume\s+my\s+fee|back\s+to\s+my\s+fee", re.IGNORECASE)


def _pick(options: list[str], seed: str) -> str:
    return options[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(options)]


def _clip(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:160]


# ------------------------------------------------------------------------------------------ state
def new_state(program: str | None = None, origin: str = "fee", scholarship: str | None = None,
              hostel: str | None = None, transport: bool | None = None) -> dict:
    return {"active": True, "origin": origin, "program": program, "concession": None, "concession_decided": False,
            "proof": None, "scholarship": scholarship, "hostel": hostel, "transport": transport,
            "awaiting": None, "asked_text": None, "final_shown": False, "goal": None, "entrance": None}


def program_label(key: str | None, text: str | None = None, specialization: str | None = None) -> str | None:
    """The programme as the student chose it: "B.Tech CSE (Artificial Intelligence & Machine Learning)" when they
    named a specialisation, otherwise the programme alone, never the fee card's whole group of specialisations."""
    if not key:
        return None
    return fees.clean_program_name(key, specialization=specialization, user_text=text)


def _set_program(st: dict, key: str, text: str | None = None) -> None:
    """Record the programme and the name to show; a new choice replaces the old name."""
    if st.get("program") != key or text:
        st["program_label"] = program_label(key, text)
    st["program"] = key


def has_marks(profile: dict) -> bool:
    p = profile or {}
    return any(p.get(k) not in (None, "") for k in ("percent", "eapcet_rank", "jee_percentile", "ib_score"))


def _hostel_chips() -> list[str]:
    per_year = fees.load_data().get("hostel_per_year", {})
    return [f"{label} ({fees.inr(per_year[key])})" for label, key in HOSTEL_CHOICES if key in per_year]


def _read_hostel(message: str) -> str | None:
    low = (message or "").lower()
    if _REMOVE_HOSTEL.search(low) or re.search(r"\b(?:no\s+hostel|not\s+interested|day\s*scholar|stay\s+at\s+home|"
                                               r"local)\b", low):
        return "none"
    kind = "non_ac" if re.search(r"\bnon[\s-]?ac\b", low) else ("ac" if re.search(r"\bac\b|a/c", low) else None)
    if not kind:
        return None
    share = "3" if re.search(r"(?<!\d)3\s*[- ]?(?:shar|bed|person|member|sea)", low) else "4"
    return f"{kind}_{share}"


def _cheapest_room() -> tuple[str, int]:
    per_year = fees.load_data().get("hostel_per_year", {})
    key = min(per_year, key=lambda k: (per_year[k], k))
    return fees.HOSTEL_LABELS.get(key, key), int(per_year[key])


def _read_entrance(message: str, awaiting: str | None) -> dict:
    """{'eapcet_rank': 18500} / {'jee_percentile': 96.5} from what the student typed (or {})."""
    low = (message or "").lower().replace(",", "")
    out = {}
    m = re.search(r"\b(?:eapcet|eamcet|emcet|ts\s*eapcet|ap\s*eapcet)\b\D{0,20}(\d{1,6})\b", low) \
        or re.search(r"\brank\D{0,10}(\d{1,6})\b|\b(\d{1,6})\s*(?:th\s+)?rank\b", low)
    if m:
        out["eapcet_rank"] = int(next(g for g in m.groups() if g))
    m = re.search(r"\bjee\b\D{0,20}(\d{1,2}(?:\.\d+)?)\b|(\d{1,2}(?:\.\d+)?)\s*(?:percentile|%ile)", low)
    if m and "eapcet_rank" not in out:
        out["jee_percentile"] = float(next(g for g in m.groups() if g))
    if not out and awaiting in ("eapcet_value", "jee_value"):
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", low)
        if m:
            value = float(m.group(1))
            if awaiting == "eapcet_value" and value >= 1 and value == int(value):
                out["eapcet_rank"] = int(value)
            elif awaiting == "jee_value" and 0 < value <= 100:
                out["jee_percentile"] = value
    if out.get("jee_percentile") is not None and not (0 < out["jee_percentile"] <= 100):
        out.pop("jee_percentile")
    if out.get("eapcet_rank") is not None and not (1 <= out["eapcet_rank"] <= 400000):
        out.pop("eapcet_rank")
    return out


def plan_card(state: dict, profile: dict) -> dict:
    """The agent's visible plan for the lowest-fee goal: each step done / now / to do, with what it found."""
    program = state.get("program")
    key = fees.find_program(program) if program else None
    fee = None
    if key and has_marks(profile):
        merit = _merit(profile)
        fee = fees.calculate_fee(key, **{k: v for k, v in merit.items() if k != "board"},
                                 board=merit.get("board") or "state_board")
    aw = state.get("awaiting")
    steps = []

    def add(title, done, detail=None, now=False):
        steps.append({"title": title, "status": "done" if done else "now" if now else "todo", "detail": detail})

    add("Programme", bool(key), fees.short_name(key) if key else None, now=aw == "program")
    marks_done = has_marks(profile)
    add("Your marks and eligibility", marks_done,
        (fee or {}).get("scholarship_basis_text") if marks_done else None, now=aw == "scholarship_steps")
    routes_done = marks_done and (state.get("entrance") is not None or not (key and fee_intake._uses_entrance(key))
                                  or bool((profile or {}).get("eapcet_rank") or (profile or {}).get("jee_percentile")))
    best = None
    if fee and fee.get("status") == "ok":
        best = f"{fee.get('scholarship_percent', 0)}% from {fee.get('scholarship_basis_text') or 'your marks'}"
    add("Compare scholarship routes (board, EAPCET, JEE)", routes_done, best if routes_done else None,
        now=aw in ("entrance", "eapcet_value", "jee_value"))
    conc = state.get("concession")
    add("Special concessions", bool(state.get("concession_decided")),
        (f"{conc['label']} (pending proof)" if conc else "none apply") if state.get("concession_decided") else None,
        now=aw in ("concession", "proof"))
    hostel = state.get("hostel")
    add("Hostel or day scholar", hostel is not None and (hostel != "none" or state.get("transport") is not None),
        (fees.HOSTEL_LABELS.get(hostel, "") if hostel not in (None, "none") else
         ("day scholar" + (" + bus" if state.get("transport") else "")) if hostel == "none" else None),
        now=aw in ("hostel", "transport"))
    add("Your lowest fee", bool(state.get("final_shown")))
    if state.get("final_shown"):   # the student asked for the result early: open steps were skipped, not pending
        for step in steps:
            if step["status"] != "done":
                step.update(status="skipped", detail=step.get("detail") or "skipped: you can add it any time")
    return {"type": "agent_plan", "data": {"title": "Finding your lowest fee", "steps": steps}}


def _lowest_explanation(state: dict, profile: dict, data: dict) -> tuple[str, list[str]]:
    """What made the fee lowest, and the one change that would lower it further (if any)."""
    key = data["program_key"]
    merit = _merit(profile)
    fee = fees.calculate_fee(key, **{k: v for k, v in merit.items() if k != "board"},
                             board=merit.get("board") or "state_board")
    lines, chips = [], []
    considered = fee.get("scores_considered") or []
    if len(considered) > 1:
        routes = ", ".join(f"{c['score']} → {c['scholarship_percent']}%" for c in considered)
        lines.append(f"• **Scholarship:** I compared {routes}, and used the best: "
                     f"**{fee.get('scholarship_percent', 0)}%**.")
    elif fee.get("scholarship_percent"):
        lines.append(f"• **Scholarship:** {fee['scholarship_percent']}% from {fee.get('scholarship_basis_text')}.")
    if state.get("concession"):
        c = state["concession"]
        lines.append(f"• **Concession:** {c['label']} (− {fees.inr(c['amount'])}/year) once your proof is verified.")
    hostel = state.get("hostel")
    if hostel not in (None, "none"):
        per_year = fees.load_data().get("hostel_per_year", {})
        cheapest_label, cheapest = _cheapest_room()
        if per_year.get(hostel, cheapest) > cheapest:
            lines.append(f"• 💡 A {cheapest_label} room would save **{fees.inr(per_year[hostel] - cheapest)}** a year.")
            chips.append(f"Switch to {cheapest_label.replace(', ', ' ')}")
    nxt = fee.get("next_scholarship_slab")
    if nxt and (profile or {}).get("is_projected"):
        lines.append(f"• 🎯 {nxt['requires']} in your final exam would give {nxt['scholarship_percent']}% "
                     f"({nxt['extra_saving_first_year']} less in the first year).")
    return "\n".join(lines), chips


# ------------------------------------------------------------------------------------------ amounts
_SWITCH = re.compile(r"\b(?:actually|instead|change(?:d)?\s+(?:it\s+)?(?:to|my\s+mind)|switch(?:ed)?\s+(?:it\s+)?to|"
                     r"i\s+(?:want|prefer|would\s+like)|no\s+wait|rather|make\s+it|not\s+\w+(?:\s+\w+)?,?\s+(?:but|i\s+want))\b",
                     re.IGNORECASE)


def _switched_program(message: str, current: str | None) -> str | None:
    """The programme the student switches to in this message, or None."""
    if not _SWITCH.search(message or "") or fee_intake.parse_details(message).get("qualifying_degree"):
        return None
    key = fee_intake.parse_details(message).get("program") or fees.find_program(message or "")
    key = fees.find_program(str(key)) if key else None
    if not key or key == fees.find_program(str(current or "")):
        return None
    return key


def marks_update_text(state: dict, profile: dict) -> str:
    """One line: what the student's (new) marks mean for the scholarship on the programme being evaluated."""
    key = fees.find_program(str(state.get("program") or ""))
    if not key or state.get("scholarship") == "no" or not has_marks(profile):
        return ""
    merit = _merit(profile)
    fee = fees.calculate_fee(key, **{k: v for k, v in merit.items() if k != "board"},
                             board=merit.get("board") or "state_board")
    if fee.get("status") != "ok":
        return ""
    short = fees.short_name(key)
    pct = int(fee.get("scholarship_percent") or 0)
    if pct <= 0:
        return (f"With your marks there's no merit scholarship slab on **{short}**, so the standard tuition "
                f"of **{fee.get('tuition_first_year')}/year** applies.")
    return (f"With your marks, your scholarship on **{short}** is **{pct}%**: tuition comes to "
            f"**{fee.get('tuition_first_year_after_scholarship') or fee.get('tuition_first_year')}/year**.")


def _merit(profile: dict) -> dict:
    return fee_plan._merit_args(profile or {})


def evaluate(state: dict, profile: dict) -> dict | None:
    """Everything the final card shows, computed now from the official fee data. None: unknown programme."""
    program = state.get("program")
    if not program or not fees.find_program(program):
        return None
    hostel = state.get("hostel") if state.get("hostel") not in (None, "none") else "none"
    transport = bool(state.get("transport"))
    merit = _merit(profile) if state.get("scholarship") != "no" else {}
    with_merit = fees.calculate_fee(program, hostel=hostel, transport=transport,
                                    **{k: v for k, v in merit.items() if k != "board"},
                                    board=merit.get("board") or "state_board")
    base = fees.calculate_fee(program, hostel=hostel, transport=transport)
    if with_merit.get("status") != "ok" or base.get("status") != "ok":
        return None
    num = fee_plan._num
    tuition = num(base["tuition_first_year"])
    pct = int(with_merit.get("scholarship_percent") or 0)
    merit_amount = num(with_merit.get("saving_first_year")) if pct else 0
    projected = bool((profile or {}).get("is_projected"))

    # Academic scholarship: from the fee-card rules for the marks given.
    if state.get("scholarship") == "no":
        sch = {"status": "not_requested", "label": "Not checked (you chose to skip it)", "amount": None}
    elif not has_marks(profile):
        sch = {"status": "not_evaluated", "label": "Not evaluated yet (marks not given)", "amount": None}
    elif pct <= 0:
        sch = {"status": "not_eligible", "label": "No merit slab for the marks given", "amount": None}
    elif projected:
        sch = {"status": "estimated", "label": f"{pct}% — estimate from your current marks; confirmed with the "
                                              f"final marksheet", "amount": fees.inr(merit_amount)}
    else:
        sch = {"status": "applied", "label": f"{pct}% merit scholarship (fee-card rules; checked against your "
                                            f"marksheet at admission)", "amount": fees.inr(merit_amount)}

    # Special consideration: never approved here.
    conc = state.get("concession")
    if conc:
        proof = state.get("proof")
        cons = {"status": "pending", "category": conc["label"], "amount": fees.inr(int(conc["amount"])),
                "label": ("Pending verification — proof ready to submit" if proof == "ready" else
                          "Pending verification — proof to be submitted")}
    elif state.get("concession_decided"):
        cons = {"status": "none", "category": None, "amount": None, "label": "None selected"}
    else:
        cons = {"status": "not_explored", "category": None, "amount": None, "label": "Not explored yet"}

    total_base = num(base["first_year_total_payable"])
    applied = merit_amount if sch["status"] == "applied" else 0
    pending_merit = merit_amount if sch["status"] == "estimated" else 0
    pending_conc = int(conc["amount"]) if conc else 0
    confirmed = total_base - applied
    estimated = confirmed - pending_merit - pending_conc

    rows = [{"item": "Tuition fee (first year)", "amount": fees.inr(tuition), "kind": "fee"}]
    if sch["amount"]:
        rows.append({"item": f"Academic scholarship ({pct}%)", "amount": "− " + sch["amount"],
                     "kind": "discount" if sch["status"] == "applied" else "pending", "status": sch["status"]})
    if conc:
        rows.append({"item": f"Special consideration: {conc['label']}", "amount": "− " + cons["amount"],
                     "kind": "pending", "status": "pending"})
    rows.append({"item": "Other academic / university fees", "amount": base["other_yearly_fees"], "kind": "fee",
                 "note": "per year"})
    rows.append({"item": "Enrollment fee", "amount": base["one_time_enrollment_fee"], "kind": "fee",
                 "note": "one time"})
    h = base.get("hostel") or {}
    if base.get("has_hostel") and h.get("per_year"):
        rows.append({"item": f"Hostel ({h.get('type')})", "amount": h["per_year"], "kind": "fee",
                     "note": "includes meals"})
    if base.get("transport_per_year"):
        rows.append({"item": "Transport (university bus)", "amount": base["transport_per_year"], "kind": "fee",
                     "note": "varies by distance"})

    pending = []
    if sch["status"] == "estimated":
        pending.append(f"Academic scholarship {pct}%: confirmed with your final marksheet")
    if conc:
        pending.append(f"{conc['label']} ({cons['amount']}/year): verified by the Admissions Office after you "
                       "submit proof")
    if cons["status"] == "not_explored":
        pending.append("Special concessions: not explored yet")
    if sch["status"] == "not_evaluated":
        pending.append("Academic scholarship: share your marks to check it")
    if state.get("hostel") is None:
        pending.append("Hostel: not chosen yet")

    if sch["status"] in ("applied", "estimated"):
        category = f"Merit — {with_merit.get('scholarship_basis_text') or 'your marks'}, {pct}% slab"
    elif has_marks(profile) and state.get("scholarship") != "no":
        category = f"Standard fee — {with_merit.get('scholarship_basis_text') or 'your marks'}"
    else:
        category = "Standard fee"
    data = {
        "academic_year": base.get("academic_year") or config.ADMISSION_YEAR,
        "program_key": base.get("program_key"),
        "program": fees.short_name(base["program_key"]),
        "course": state.get("program_label") or program_label(base["program_key"]),
        "category": category,
        "rows": rows,
        "original_tuition": fees.inr(tuition),
        "scholarship": sch,
        "special_consideration": cons,
        "total_approved_concessions": fees.inr(applied),
        "payable_confirmed": fees.inr(confirmed),
        "payable_after_approval": fees.inr(estimated) if estimated != confirmed else None,
        "pending": pending,
        "application_fee": base.get("one_time_application_fee"),
        "combine_note": (fee_plan.COMBINE_NOTE.format(phone=config.ADMISSIONS_PHONE)
                         if conc and sch["status"] in ("applied", "estimated") else None),
        "source": base.get("source"),
    }
    data["share_text"] = share_text(data)
    return data


def share_text(d: dict) -> str:
    lines = [f"SR University {d['academic_year']} fee summary: {d['course']}", f"Category: {d['category']}"]
    for r in d["rows"]:
        tag = " (pending)" if r.get("kind") == "pending" else ""
        lines.append(f"- {r['item']}: {r['amount']}{tag}")
    lines.append(f"Payable now (confirmed): {d['payable_confirmed']}")
    if d.get("payable_after_approval"):
        lines.append(f"After pending approvals (estimate): {d['payable_after_approval']}")
    lines.append(f"Confirm with the Admissions Office: {config.ADMISSIONS_PHONE}.")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------ the planner
def _ask(state: dict, awaiting: str, text: str, chips: list[str], cards: list | None = None) -> dict:
    state["awaiting"] = awaiting
    state["asked_text"] = _clip(text.split("\n")[-1])
    return {"kind": "reply", "text": text, "chips": chips, "cards": cards or [], "state": state}


def _concession_card(program: str | None) -> dict:
    return fee_plan.concession_card(program, in_evaluation=True)


def _concession_chips() -> list[str]:
    """The grouped card has its own "None of these apply" button; the full table needs the chip."""
    from app.services import app_settings
    return [SHOW_FEE] if app_settings.get("concession_picker") == "grouped" else [NONE_APPLY, SHOW_FEE]


def next_step(state: dict, profile: dict, lead: str = "", seed: str = "") -> dict:
    """What to do next for this student: the first open step, or the final card."""
    lead = (lead.strip() + "\n\n") if lead.strip() else ""
    program = state.get("program")
    # Special consideration: the categories come first (the programme is needed only for the amounts).
    consideration_first = state.get("origin") == "special_consideration" and not state.get("concession_decided")
    if not program and not consideration_first:
        return _ask(state, "program", lead + "Which programme should I work out the fee for?", PROGRAM_CHIPS)
    if state.get("goal") == "lowest" and program:
        if not has_marks(profile):
            state["scholarship"] = "yes"
            state["awaiting"] = "scholarship_steps"
            state["asked_text"] = None
            return {"kind": "scholarship_steps", "lead": lead, "state": state}
        if state.get("entrance") is None and fee_intake._uses_entrance(fees.find_program(program)) \
                and not (profile or {}).get("eapcet_rank") and not (profile or {}).get("jee_percentile"):
            return _ask(state, "entrance",
                        lead + "Do you have an EAPCET rank or a JEE Main percentile? Sometimes it gives a bigger "
                               "scholarship than board marks, and I'll use whichever is better.",
                        ENTRANCE_CHIPS)
    if not state.get("concession_decided"):
        if state.get("origin") == "eligibility":
            ask = ("Before we finalise your fee, there may be additional concessions or special considerations "
                   "available. Would you like to explore them? Select one that applies to see your potential "
                   "final fee.")
        else:
            ask = ("Pick the category that applies to you, and I'll check what it means for your fee. Only "
                   "choose one you can prove with a document.")
        return _ask(state, "concession", lead + ask, _concession_chips(), [_concession_card(program)])
    if not program:
        return _ask(state, "program", lead + "Which programme should I work out the fee for?", PROGRAM_CHIPS)
    conc = state.get("concession")
    if conc and state.get("proof") is None:
        return _ask(state, "proof",
                    lead + f"Do you have the supporting document for **{conc['label']}** (a certificate or ID that "
                           "proves it)? The Admissions Office checks it before the concession is approved.",
                    ["Yes, I have it", "Not yet"])
    if state.get("scholarship") is None:
        if has_marks(profile):
            state["scholarship"] = "yes"          # already evaluated from the marks given: reuse, never re-ask
        else:
            return _ask(state, "scholarship",
                        lead + "Would you also like to check whether your 10+2 / Intermediate marks give you an "
                               "academic scholarship (up to 40% on tuition)?",
                        ["Yes, check my scholarship", "No, skip it"])
    if state.get("scholarship") == "yes" and not has_marks(profile):
        state["awaiting"] = "scholarship_steps"
        state["asked_text"] = None
        return {"kind": "scholarship_steps", "lead": lead, "state": state}
    if state.get("hostel") is None:
        return hostel_step(state, lead, seed)
    if state.get("hostel") == "none" and state.get("transport") is None:
        bus = fees.inr(fees.load_data().get("transport_per_year", 0))
        return _ask(state, "transport",
                    lead + f"Will you use the university bus? It's about **{bus}/year** (varies by distance).",
                    ["Yes, add the bus", "No, I'll manage"])
    return final(state, profile, lead)


def hostel_step(state: dict, lead: str = "", seed: str = "") -> dict:
    """The hostel question (asked in order, or straight away when the student asks to add / change the hostel)."""
    if state.get("goal") == "lowest":
        cheapest = _cheapest_room()
        text = (f"Will you stay in the hostel? The lowest-cost room is **{cheapest[0]}** "
                f"({fees.inr(cheapest[1])} a year, meals included).")
    else:
        text = _pick(["Will you stay in the university hostel? Pick a room type to add it to your fee.",
                      "Do you want to add the hostel fee? Choose a room type (meals included).",
                      "Hostel or day scholar? Pick a room to include it."], seed)
    return _ask(state, "hostel", lead + text, _hostel_chips() + [NO_HOSTEL])


def final(state: dict, profile: dict, lead: str = "") -> dict:
    data = evaluate(state, profile)
    if not data:
        state["program"] = None
        return _ask(state, "program", "I couldn't match that programme. Which one should I use?", PROGRAM_CHIPS)
    updated = bool(state.get("final_shown"))
    state["final_shown"] = True
    state["awaiting"] = None
    state["asked_text"] = None
    sch = data["scholarship"]
    pct_txt = sch["label"].split(" ")[0]
    if sch["status"] == "applied":
        with_sch = f"With your {pct_txt} scholarship (− {sch['amount']}), "
    elif sch["status"] == "estimated":
        with_sch = (f"Your {pct_txt} scholarship is an estimate until your final marksheet, so ")
    else:
        with_sch = ""
    if data.get("payable_after_approval"):
        summary = (f"{with_sch}you'd pay **{data['payable_confirmed']}** in the first year as things stand, and "
                   f"**{data['payable_after_approval']}** if the pending items are approved.")
    else:
        summary = f"{with_sch}your first-year total comes to **{data['payable_confirmed']}**."
    summary = summary[0].upper() + summary[1:]
    chips = []
    if data["special_consideration"]["status"] == "not_explored":
        chips.append("Explore special concessions")
    if state.get("hostel") in (None, "none"):
        chips.append("Add hostel to my fee")
    else:
        chips.append("Change hostel")
    chips += ["Documents needed for the concession" if state.get("concession") else "How do I apply for 2027-28?",
              "Talk to a counsellor"]
    head = "Here's your updated fee summary." if updated else "Here's your personalised fee summary."
    if state.get("goal") == "lowest":
        head = "✓ Done. Here's your lowest first-year fee."
        how, extra_chips = _lowest_explanation(state, profile, data)
        if how:
            summary = summary + "\n\n" + how
        chips = (extra_chips + chips)[:4]
    text = (lead.strip() + "\n\n" if lead.strip() else "") + head + " " + summary
    return {"kind": "final", "text": text, "chips": chips[:4],
            "cards": [{"type": "fee_summary", "data": data}], "state": state}


def _answering(state: dict, history_last: str | None) -> bool:
    """Is the student answering the question we asked last (not a question asked by something else since)?"""
    asked = state.get("asked_text")
    return bool(asked) and bool(history_last) and asked in re.sub(r"\s+", " ", history_last)


def resolve_program(*candidates) -> str | None:
    for c in candidates:
        key = fees.find_program(str(c)) if c else None
        if key:
            return key
    return None


def decide(message: str, state: dict | None, profile: dict, ctx: dict) -> dict | None:
    """What the fee agent does with this message, or None. Adds the visible plan for the lowest-fee goal."""
    result = _decide(message, state, profile, ctx)
    return with_plan(result, {**(profile or {}), **((result or {}).get("profile_updates") or {})})


def with_plan(result: dict | None, profile: dict) -> dict | None:
    """The lowest-fee goal shows the agent's plan above every step (one plan card, replaced each time)."""
    if not result or (result.get("state") or {}).get("goal") != "lowest":
        return result
    cards = [c for c in result.get("cards") or [] if c.get("type") != "agent_plan"]
    result["cards"] = [plan_card(result["state"], profile)] + cards
    return result


def _decide(message: str, state: dict | None, profile: dict, ctx: dict) -> dict | None:
    """What the fee agent does with this message, or None (not about the fee evaluation).

    ctx: program (the programme in this conversation), hostel / transport (last fee asked about),
    last_reply (the last assistant message), selected_concession, seed.
    """
    msg = message or ""
    seed = ctx.get("seed", "") + msg
    st = dict(state) if state else None
    active = bool(st and st.get("active"))
    aw0 = (st or {}).get("awaiting") if active else None
    picked = fee_plan.find_concession(msg) or ctx.get("fuzzy_concession")

    # ---- entry points (work whether or not an evaluation is running) ---------------------------------------
    if _SPECIAL.search(msg) and not picked:
        st = st if active else new_state(resolve_program(ctx.get("program")), "special_consideration")
        st.update(concession_decided=False)
        lead = ("Your special consideration can be evaluated for an additional fee concession. Let's collect the "
                "relevant details before working out your final payable fee.")
        return next_step(st, profile, lead, seed)

    if _LOWEST.search(msg) and not picked and not re.search(r"\b(?:hostel|mess|bus|transport)\b", msg, re.IGNORECASE):
        if not active:
            st = new_state(None, "lowest_fee", scholarship="yes")
            key = resolve_program(msg, ctx.get("program"))
            if key:
                _set_program(st, key, msg if fees.find_program(msg) else ctx.get("program_text"))
        elif fees.find_program(msg):
            _set_program(st, fees.find_program(msg), msg)
        st.update(goal="lowest", final_shown=False)
        lead = "Sure! I'll work out the lowest fee you can get. Here's my plan, and I'll run each check myself."
        return next_step(st, profile, lead, seed)

    if picked and (aw0 == "concession"
                   or re.search(r"\b(?:apply|add|concession|consideration|select|choose|use)\b", msg, re.IGNORECASE)):
        if not active:
            st = new_state(resolve_program(ctx.get("program")), "concession")
        named_text = re.sub(r'"[^"]*"', " ", msg)
        named = fees.find_program(named_text)   # "... to my B.Tech CSE fee" (not the label)
        if named:
            _set_program(st, named, named_text)
        old = st.get("concession")
        if old and old["label"] == picked["label"]:
            lead = f"**{picked['label']}** is already in your evaluation; it's counted once."
        else:
            st.update(concession=picked, concession_decided=True, proof=None)
            replaced = f" (it replaces {old['label']})" if old else ""
            lead = (f"Noted: **{picked['label']}** — {fees.inr(picked['amount'])} a year{replaced}. This isn't "
                    "applied yet: it's a special consideration that the Admissions Office evaluates once you "
                    "submit proof, so I'll show it separately from your confirmed fee.")
        return next_step(st, profile, lead, seed)

    wants_final = bool(_FINAL.search(msg)) and not (
        not active and re.search(r"\b(?:hostel|mess|bus|transport|exam|application)\b", msg, re.IGNORECASE))
    if wants_final and not active and ctx.get("evaluate_first") and not has_marks(profile) \
            and _PAY_Q.search(msg) and not _EXPLICIT_FINAL.search(msg):
        # v4.15.0: "how much do I pay for AI & Robotics?" from a student with no marks yet is a fee question: the
        # evaluation (marks -> scholarship -> concessions -> hostel) runs first, as for "AI & Robotics fees?".
        wants_final = False
        return None
    if not active and ctx.get("offer") == "fee_chart" and _YES.match(msg):
        wants_final = True          # "yes" to "shall I prepare your complete fee chart?"
    if wants_final:
        if active and st.get("awaiting") == "concession":
            st["concession_decided"] = True     # "show my final fee" instead of picking a category
        if not active:
            program = resolve_program(msg, ctx.get("program"))
            st = new_state(program, "final_request", scholarship="yes" if has_marks(profile) else None,
                           hostel=ctx.get("hostel"), transport=ctx.get("transport"))
            if ctx.get("selected_concession"):
                st.update(concession=ctx["selected_concession"], concession_decided=True, proof="needed")
        elif fees.find_program(msg):
            _set_program(st, fees.find_program(msg), msg)
        if not st.get("program"):
            st["want_final"] = True
            return _ask(st, "program", "Sure! Which programme should the fee summary be for?", PROGRAM_CHIPS)
        return final(st, profile)

    about = _about_my_evaluation(msg, st if active else None, profile, ctx, seed)
    if about:
        return about

    if not active:
        return None

    # ---- while an evaluation is running ----------------------------------------------------------------------
    answering = _answering(st, ctx.get("last_reply"))
    aw = st.get("awaiting")

    # v4.15.0: a change of programme in the middle ("actually I want ECE", "change to AI and Robotics"): the
    # evaluation continues for the new programme (same marks, same selections), with what that changes.
    new_key = _switched_program(msg, st.get("program"))
    if new_key:
        _set_program(st, new_key, msg)
        lead = f"Sure, switching to **{fees.short_name(new_key)}**. " + marks_update_text(st, profile)
        if st.get("final_shown") and not aw:
            return final(st, profile, lead)
        return next_step(st, profile, lead, seed)

    # v4.15.0: the student corrected their marks ("No, my marks are 671 out of 1000"). The new marks are already
    # the only marks on file (agent._sync_marks); say what they change, then ask the open step again. The "No"
    # in the correction is NOT an answer to the open step (it used to be read as "no concession").
    if ctx.get("marks_corrected") and aw != "scholarship_steps":
        lead = marks_update_text(st, profile)
        if st.get("final_shown") and not aw:
            return final(st, profile, lead)
        return next_step(st, profile, lead, seed)

    if _CONTINUE.search(msg):
        if st.get("final_shown") and not aw:
            return final(st, profile)
        return next_step(st, profile, "Picking up where we left off.", seed)
    if _REMOVE_CONCESSION.search(msg) and st.get("concession"):
        old = st["concession"]["label"]
        st.update(concession=None, concession_decided=True, proof=None)
        return next_step(st, profile, f"Removed **{old}** from your evaluation.", seed)
    if _CHANGE_CONCESSION.search(msg) or re.search(r"\b(?:explore|show|see|check)\s+(?:the\s+)?(?:special\s+)?"
                                                   r"concessions?\b", msg, re.IGNORECASE):
        st.update(concession_decided=False, proof=None)
        return next_step(st, profile, "", seed)
    if _CHANGE_HOSTEL.search(msg) and not _read_hostel(msg):
        st.update(hostel=None, transport=None)
        return hostel_step(st, "", seed)     # what they asked for, not the next open step
    hostel_now = _read_hostel(msg)
    if hostel_now and (aw == "hostel" or re.search(r"\bhostel\b|\broom\b|\bsharing\b", msg, re.IGNORECASE)):
        st["hostel"] = hostel_now
        if hostel_now != "none":
            st["transport"] = False
        lead = ("Okay, no hostel." if hostel_now == "none" else
                f"Added the {fees.HOSTEL_LABELS[hostel_now]} hostel room.")
        return next_step(st, profile, lead, seed)

    if aw in ("entrance", "eapcet_value", "jee_value"):
        found = _read_entrance(msg, aw)
        if found:
            st["entrance"] = "given"
            merged = {**(profile or {}), **found}
            key = fees.find_program(st.get("program") or "")
            lead = "Got it."
            if key:
                merit = _merit(merged)
                fee = fees.calculate_fee(key, **{k: v for k, v in merit.items() if k != "board"},
                                         board=merit.get("board") or "state_board")
                routes = fee.get("scores_considered") or []
                if len(routes) > 1:
                    lead = ("I compared " + ", ".join(f"{r['score']} → {r['scholarship_percent']}%" for r in routes)
                            + f". The best is **{fee.get('scholarship_percent', 0)}%**, so I'll use that.")
            step = next_step(st, merged, lead, seed)
            step["profile_updates"] = found
            return step
        if re.search(r"add\s+my\s+eapcet|eapcet|eamcet", msg, re.IGNORECASE):
            return _ask(st, "eapcet_value", "Type your EAPCET rank (just the number).", [])
        if re.search(r"add\s+my\s+jee|\bjee\b", msg, re.IGNORECASE):
            return _ask(st, "jee_value", "Type your JEE Main percentile (for example 92.5).", [])
        if aw == "entrance" and (_NO.match(msg) or re.search(r"no\s+entrance|didn'?t\s+write|not\s+written|none",
                                                            msg, re.IGNORECASE)):
            st["entrance"] = "none"
            return next_step(st, profile, "Okay, board marks it is.", seed)
    if aw == "program":
        key = fees.find_program(msg)
        if key:
            _set_program(st, key, msg)
            if st.pop("want_final", False):
                return final(st, profile)            # they asked for the final fee: give it now
            return next_step(st, profile, f"Got it, **{fees.short_name(key)}**.", seed)
    elif aw == "concession" and (answering or re.search(r"none\s+of\s+(?:these|them)|doesn'?t\s+apply|"
                                                         r"don'?t\s+(?:have|qualify)", msg, re.IGNORECASE)):
        if re.search(r"none\s+of|doesn'?t\s+apply|don'?t\s+(?:have|qualify)|^\s*(?:no|none|nothing|nope|nah|na|"
                     r"ledu|kuch\s+nahi|nahi)\b|skip|not\s+applicable",
                     msg, re.IGNORECASE):
            st.update(concession=None, concession_decided=True, proof=None)
            return next_step(st, profile, "No problem, no special concession then.", seed)
        if re.search(SHOW_FEE, msg, re.IGNORECASE):
            st.update(concession_decided=True)
            return final(st, profile)
    elif aw == "proof" and answering:
        if _YES.match(msg):
            st["proof"] = "ready"
            return next_step(st, profile, "Great — keep it ready for the Admissions Office.", seed)
        if _NO.match(msg):
            st["proof"] = "needed"
            return next_step(st, profile, "That's fine; you can submit it during admission. It stays pending "
                                          "until then.", seed)
    elif aw == "scholarship" and answering:
        if _YES.match(msg) or re.search(r"check\s+my\s+scholarship", msg, re.IGNORECASE):
            st["scholarship"] = "yes"
            return next_step(st, profile, "", seed)
        if _NO.match(msg):
            st["scholarship"] = "no"
            return next_step(st, profile, "Okay, I'll leave the scholarship out.", seed)
    elif aw == "transport" and answering:
        if _YES.match(msg):
            st["transport"] = True
            return next_step(st, profile, "Added the university bus.", seed)
        if _NO.match(msg):
            st["transport"] = False
            return next_step(st, profile, "", seed)

    # The conversation is winding down with the fee unfinished: offer to finish it (one tap).
    if _WRAP_UP.match(msg) and not st.get("final_shown") and aw and aw != "scholarship_steps":
        step = next_step(dict(st), profile, "", seed)
        if step["kind"] == "reply":
            step["text"] = ("You're welcome! Before you go — your fee estimate is almost ready.\n\n"
                            + step["text"])
            if SHOW_FEE not in step["chips"]:
                step["chips"] = step["chips"] + [SHOW_FEE]
            return step
    return None


# Questions ABOUT the student's own evaluation ("what documents do I need for it?", "is my concession approved?",
# "how much is my scholarship?"). Answered from what the student selected, then the open step is asked again,
# so a question never derails the evaluation and never sends the student to an unrelated flow.
_DOCS_Q = re.compile(r"\b(?:documents?|docs?|proofs?|certificates?|papers?)\b", re.IGNORECASE)
_CONCESSION_WORD = re.compile(r"\b(?:concessions?|considerations?|claim|categor(?:y|ies)|it|this|that)\b", re.IGNORECASE)
_APPROVED_Q = re.compile(r"\b(?:approved?|confirmed?|sanctioned|granted|guaranteed|sure)\b.{0,30}\b(?:concession|consideration|it)\b"
                         r"|\b(?:concession|consideration)\b.{0,30}\b(?:approved?|confirmed?|sanctioned|granted|guaranteed)\b"
                         r"|\bwill\s+i\s+(?:get|receive)\s+(?:the\s+|my\s+|this\s+)?(?:concession|consideration|discount)\b",
                         re.IGNORECASE)
_SCHOLARSHIP_Q = re.compile(r"\b(?:how\s+much|what(?:'s|\s+is)?)\b.{0,25}\b(?:my\s+)?scholarship\b|\bmy\s+scholarship\b",
                            re.IGNORECASE)


def _concession_effect(st: dict, profile: dict) -> str | None:
    """'₹2,80,000 → ₹2,65,000' for the student's current selections, or None."""
    data = evaluate(st, profile) if st.get("program") else None
    if data and data.get("payable_after_approval"):
        return f"**{data['payable_confirmed']} → {data['payable_after_approval']}** in the first year"
    return None


def _continue_or_close(st: dict, profile: dict, answer: str, chips: list[str], seed: str) -> dict:
    """After answering, carry on with the open step (or, when the summary is done, offer what fits)."""
    if st.get("awaiting") and st["awaiting"] != "scholarship_steps" and not st.get("final_shown"):
        step = next_step(st, profile, answer + "\n\nNow, back to your fee:", seed)
        return step
    st["asked_text"] = None
    return {"kind": "reply", "text": answer, "chips": chips, "cards": [], "state": st}


def _about_my_evaluation(msg: str, st: dict | None, profile: dict, ctx: dict, seed: str) -> dict | None:
    conc = (st or {}).get("concession") or ctx.get("selected_concession")
    # "Yes, I have the proof" is a statement about their concession, not a question about documents.
    if st and conc and st.get("concession") and re.search(
            r"\b(?:i\s+(?:have|got)|yes,?\s+i\s+have)\s+(?:the\s+|my\s+|a\s+)?(?:proof|documents?|certificate)",
            msg, re.IGNORECASE):
        st["proof"] = "ready"
        lead = f"Great, noted: your proof for **{conc['label']}** is ready."
        if st.get("final_shown"):
            return final(st, profile, lead)
        return next_step(st, profile, lead, seed)
    if _DOCS_Q.search(msg) and (_CONCESSION_WORD.search(msg) or conc) and not re.search(
            r"\b(?:admission|apply|application|join(?:ing)?\s+documents)\b", msg, re.IGNORECASE):
        if conc:
            amount = fees.inr(int(conc["amount"]))
            lines = [f"Yes. You've selected **{conc['label']}** ({amount} a year). To claim it, submit a "
                     "supporting document that proves this category to the Admissions Office when you join. "
                     "They verify it before the concession is approved."]
            effect = _concession_effect(st, profile) if st else None
            if effect:
                lines.append(f"Once it's approved, {amount} comes off your fee: {effect}.")
            else:
                lines.append(f"Once it's approved, {amount} comes off your tuition every year.")
            if (st or {}).get("proof") == "ready":
                lines.append("You said your proof is ready 👍. Keep it with your admission documents.")
            lines.append(f"The Admissions Office ({config.ADMISSIONS_PHONE}) confirms the exact document for "
                         "this category.")
            chips = (["Yes, I have the proof"] if (st or {}).get("proof") != "ready" else []) + \
                    ["Talk to a counsellor", SHOW_FEE]
            text = lines[0] + "\n\n" + "\n".join(lines[1:])
            if st:
                return _continue_or_close(st, profile, text, chips, seed)
            return {"kind": "info", "text": text, "chips": [c for c in chips if c != "Yes, I have the proof"],
                    "cards": []}
        text = ("Documents are needed only for a special concession: each one needs proof of its category, which "
                "the Admissions Office verifies before approving it. You haven't selected one yet. Want to check "
                "whether one applies to you?")
        chips = ["Explore special concessions", "Talk to a counsellor"]
        if st:
            return _continue_or_close(st, profile, text, chips, seed)
        return {"kind": "info", "text": text, "chips": chips, "cards": []}
    if not st:
        return None
    if _APPROVED_Q.search(msg) and conc:
        text = (f"Not yet: **{conc['label']}** is pending verification. It's approved by the Admissions Office "
                "after they check your proof, so I show it separately from your confirmed fee.")
        effect = _concession_effect(st, profile)
        if effect:
            text += f" If it's approved: {effect}."
        return _continue_or_close(st, profile, text, ["Documents needed for the concession", SHOW_FEE], seed)
    if _SCHOLARSHIP_Q.search(msg) and not _FINAL.search(msg) and st.get("program") and has_marks(profile):
        data = evaluate(st, profile)
        sch = (data or {}).get("scholarship") or {}
        if sch.get("amount"):
            text = f"Your academic scholarship is **{sch['label'].split(' ')[0]}**: − {sch['amount']} on the first-year tuition."
            if sch["status"] == "estimated":
                text += " It's an estimate until your final marksheet."
        else:
            text = f"No merit scholarship applies to the marks you gave ({sch.get('label', '').lower() or 'no slab'})."
        return _continue_or_close(st, profile, text, [SHOW_FEE, "Talk to a counsellor"], seed)
    return None


def resume_chip(state: dict | None) -> str | None:
    """The chip that brings the student back to an unfinished evaluation after a side question."""
    if state and state.get("active") and not state.get("final_shown") and state.get("awaiting") \
            and state.get("awaiting") != "scholarship_steps":
        return RESUME
    return None


def after_scholarship(state: dict, profile: dict, assessment_text: str, eligible, seed: str = "",
                      specialization: str | None = None) -> dict:
    """See _after_scholarship; adds the visible plan for the lowest-fee goal, and keeps the specialisation the
    student chose in the scholarship steps (e.g. CSE with AI & ML) for the fee summary."""
    result = _after_scholarship(state, profile, assessment_text, eligible, seed)
    st = result.get("state") or {}
    if specialization and st.get("program"):
        st["program_label"] = program_label(st["program"], specialization=specialization)
        for c in result.get("cards") or []:
            if c.get("type") == "fee_summary":
                c["data"]["course"] = st["program_label"]
                c["data"]["share_text"] = share_text(c["data"])
    return with_plan(result, profile)


def _after_scholarship(state: dict, profile: dict, assessment_text: str, eligible, seed: str = "") -> dict:
    """The scholarship / eligibility result is in (the existing step-by-step flow finished).

    First time (the student came for the scholarship): confirm the qualification and introduce the special
    concessions before any fee card. Inside an evaluation: use the result and go on to the next open step.
    """
    st = dict(state or {})
    if st.get("goal") == "lowest":   # the agent asks about entrance scores itself, as a step
        assessment_text = re.sub(r"\s*Have an EAPCET rank or JEE Main percentile\? Share it and I'll check if it "
                                 r"gives more\.", "", assessment_text).strip()
    if st.get("active"):
        st["scholarship"] = "yes"
        if st.get("final_shown"):
            return final(st, profile, assessment_text)
        return next_step(st, profile, assessment_text, seed)
    program = resolve_program(st.get("program"), (profile or {}).get("program_interest"))
    st = new_state(program, "eligibility", scholarship="yes")
    st["program_label"] = (state or {}).get("program_label")
    return _after_first_result(st, profile, assessment_text, eligible, seed)


def _after_first_result(st, profile, assessment_text, eligible, seed):
    if eligible is True:
        intro = _pick(["Congratulations! Based on your academic details, you qualify for this programme.",
                       "Congratulations! Your academic details meet the requirements for this programme.",
                       "You're eligible for this programme based on the details you shared. Congratulations!"], seed)
        assessment_text = assessment_text.replace("\n\nYou also meet the minimum marks for it.", "")
    else:
        intro = "Here's your result."
    return next_step(st, profile, f"{intro}\n\n{assessment_text}", seed)
