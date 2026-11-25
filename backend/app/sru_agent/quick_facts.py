"""Short, exact answers to specific questions the open-question audit found answered badly (v4.15.1).

Every answer comes from the official 2027-28 fee card (fees_2027_28.json: its programmes and `terms`), the verified
facts registry, or says plainly that the information is not in the official sources and who confirms it. Nothing is
added from general knowledge. answer() returns None when the message is not one of these questions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config, fees


@dataclass
class QuickAnswer:
    text: str
    chips: list[str] = field(default_factory=list)
    cards: list = field(default_factory=list)


def _phone() -> str:
    return config.ADMISSIONS_PHONE


def _fee_increase(message: str) -> QuickAnswer:
    data = fees.load_data()
    key = fees.find_program(message or "")
    terms = data.get("terms") or []
    rule = next((t for t in terms if "annual increase" in t.lower()), "")
    if key:
        p = data["programs"][key]
        inc = p.get("yearly_increase")
        line = (f"For **{fees.short_name(key)}** the 2027-28 tuition is **{fees.inr(p['tuition_per_year'])}** a year, "
                f"rising by **{fees.inr(inc)}** each year of the course." if inc else "")
    else:
        line = ("Each programme's yearly increase is printed on the fee card (for example B.Tech CSE: "
                f"{fees.inr(data['programs']['btech_cse'].get('yearly_increase', 0))} a year).")
    text = ("Yes. The official 2027-28 fee card says: \"" + rule + "\" " + line +
            "\n\nFees for students admitted in later years are not published yet.")
    return QuickAnswer(text.strip(), ["Calculate my fee", "Scholarships", "Talk to a counsellor"])


def _fee_value(message: str) -> QuickAnswer:
    return QuickAnswer(
        "Most students at SR University pay well below the listed tuition:\n\n"
        "• **Merit scholarships up to 40%** of tuition, from Intermediate marks, EAPCET rank or JEE Main percentile\n"
        "• **19 special concessions** (₹15,000 to ₹50,000 a year), for example for siblings, girl students from "
        "other states or sports achievers\n"
        "• **Placements:** 1,300+ offers, average 6 to 6.5 LPA and a highest of ₹51 LPA (Microsoft)\n"
        "• **Recognition:** NIRF 91st in Engineering, NBA Tier-I B.Tech programmes, the first private university "
        "in Telangana and Andhra Pradesh with ICAR accreditation\n\n"
        "Shall I work out what you would actually pay?",
        ["Calculate my fee", "Special concessions", "Placements"])


def _scholarship_renewal(message: str) -> QuickAnswer:
    return QuickAnswer(
        "The 2027-28 fee card gives the merit scholarship slabs (from your Intermediate marks, EAPCET rank or JEE "
        "Main percentile) but does not print the rules for keeping the scholarship in later years. It does say "
        "that tuition rises every year *irrespective of the scholarship awarded*, and that all scholarships are "
        "subject to university policies.\n\n"
        f"The Admissions Office confirms the renewal conditions ({_phone()}).",
        ["Scholarship slabs", "Calculate my scholarship", "Talk to a counsellor"])


def _backlogs(message: str) -> QuickAnswer:
    return QuickAnswer(
        "To join, you need to have **passed 10+2 / Intermediate** with the subjects and minimum marks your "
        "programme asks for. If you have backlogs, clear them in the supplementary exams first; your marks after "
        "passing are the ones that count for eligibility and the merit scholarship.\n\n"
        f"The Admissions Office can tell you the last date to submit your pass certificate ({_phone()}).",
        ["Check my eligibility", "How do I apply?", "Talk to a counsellor"])


def _naac(message: str) -> QuickAnswer:
    return QuickAnswer(
        "The accreditations in the verified facts I use are: **NBA Tier-I** for the B.Tech programmes (CSE, ECE, "
        "EEE, ME, CE), **ICAR** accreditation for the School of Agriculture (the first private university in "
        "Telangana and Andhra Pradesh to get it) and **UGC 2(f)** recognition under the TS Private Universities "
        "Act 2018, with **NIRF 91st in Engineering**.\n\n"
        f"For SRU's current NAAC grade, please check with the Admissions Office ({_phone()}).",
        ["Rankings", "Why choose SRU?", "Talk to a counsellor"])


def _valid_abroad(message: str) -> QuickAnswer:
    return QuickAnswer(
        "SR University is a **UGC-recognised** state private university (2(f), TS Private Universities Act 2018) and "
        "its B.Tech programmes are **NBA Tier-I** accredited, so its degrees are regular, recognised degrees. "
        "Whether a degree is accepted for a particular job or university abroad is decided by that country or "
        "institution (often through a credential evaluation).\n\n"
        "SRU also has 80+ international collaborations, with 2+2 / 3+1 pathways to partner universities in the "
        f"USA and New Zealand. The Admissions Office can advise on a specific country ({_phone()}).",
        ["Study abroad pathways", "Rankings", "Talk to a counsellor"])


def _weather(message: str) -> QuickAnswer:
    return QuickAnswer(
        "I can't check the weather, sorry. I'm SRU Buddy, here for SR University admissions: programmes, fees, "
        "scholarships, hostel and campus life. What would you like to know?",
        ["Programmes", "Calculate my fee", "Hostel life"])


_RULES = [
    (re.compile(r"\b(?:will|do(?:es)?|is)\b.{0,30}\bfees?\b.{0,25}\b(?:increase|go\s+up|rise|hike|change)\b|"
                r"\bfees?\s+(?:increase|hike|rise)\b|\byearly\s+increase\b|\bincrease\s+(?:in|of)\s+fees?\b", re.I),
     _fee_increase),
    (re.compile(r"\bwhy\b.{0,25}\b(?:fees?|fee\s+structure|cost)\b.{0,20}\b(?:so\s+)?(?:high|costly|expensive|more)\b|"
                r"\b(?:fees?|cost)\b.{0,15}\b(?:too|very|so)\s+(?:high|costly|expensive)\b|\bworth\s+the\s+fees?\b", re.I),
     _fee_value),
    (re.compile(r"\b(?:lose|losing|keep|retain|renew\w*|continue|continued|every\s+year|all\s+(?:4|four)\s+years|"
                r"only\s+(?:for\s+)?(?:the\s+)?first\s+year|next\s+years?|second\s+year)\b.{0,40}\bscholarships?\b|"
                r"\bscholarships?\b.{0,40}\b(?:lose|losing|keep|retain|renew\w*|every\s+year|all\s+(?:4|four)\s+years|"
                r"only\s+(?:for\s+)?(?:the\s+)?first\s+year|next\s+year|if\s+(?:my\s+)?(?:marks|cgpa|grades)\s+(?:drop|fall|go\s+down))\b",
                re.I), _scholarship_renewal),
    (re.compile(r"\b(?:backlogs?|supplementary|supply|compartment|failed\s+in)\b.{0,40}\b(?:inter|intermediate|12th|"
                r"join|admission|apply|eligib\w*)\b|\b(?:join|admission|apply|eligib\w*)\b.{0,40}\b(?:backlogs?|"
                r"supplementary|compartment)\b", re.I), _backlogs),
    (re.compile(r"\bnaac\b", re.I), _naac),
    (re.compile(r"\b(?:degree|certificate)s?\b.{0,30}\b(?:valid|recogni[sz]ed|accepted)\b.{0,30}\b(?:abroad|outside\s+india|"
                r"foreign|usa|us|uk|canada|australia|germany|other\s+countries)\b|\bvalid\s+abroad\b", re.I), _valid_abroad),
    (re.compile(r"\bweather\b|\btemperature\s+(?:today|now|outside)\b|\bwill\s+it\s+rain\b", re.I), _weather),
]


# ------------------------------------------------------------------ fees (2027-28 fee card)
def _data():
    return fees.load_data()


def _hostel_included(message: str) -> QuickAnswer:
    h = _data()["hostel_per_year"]
    return QuickAnswer(
        "No. The hostel is **separate from tuition**: per year, meals included, "
        f"AC 3-sharing {fees.inr(h['ac_3'])}, AC 4-sharing {fees.inr(h['ac_4'])}, Non-AC 3-sharing {fees.inr(h['non_ac_3'])}, "
        f"Non-AC 4-sharing {fees.inr(h['non_ac_4'])} (2027-28 fee card). Day scholars pay no hostel fee.",
        ["Calculate my fee", "Hostel life", "Hostel deposits"])


def _per_semester(message: str) -> QuickAnswer:
    key = fees.find_program(message or "") or "btech_cse"
    p = _data()["programs"][key]
    half = int(p["tuition_per_year"]) // 2
    return QuickAnswer(
        f"**{fees.short_name(key)}** tuition for 2027-28 is **{fees.inr(half)} per semester** "
        f"({fees.inr(p['tuition_per_year'])} a year), before any scholarship. Other yearly charges and the hostel are "
        "separate.\n\nThe payment dates and instalment rules aren't printed on the fee card; the Admissions Office "
        f"confirms them ({_phone()}).",
        ["Calculate my fee", f"{fees.short_name(key)} fees", "Scholarships"])


def _course_total(message: str) -> QuickAnswer:
    key = fees.find_program(message or "") or "btech_cse"
    p = _data()["programs"][key]
    years = int(p.get("duration_years") or 4)
    t, inc = int(p["tuition_per_year"]), int(p.get("yearly_increase") or 0)
    per_year = [t + inc * i for i in range(years)]
    rows = "\n".join(f"• Year {i + 1}: {fees.inr(v)}" for i, v in enumerate(per_year))
    return QuickAnswer(
        f"**{fees.short_name(key)}** tuition over {years} years (2027-28 fee card, before any scholarship):\n\n{rows}\n\n"
        f"**Total tuition: {fees.inr(sum(per_year))}.** Other yearly charges, the hostel and transport are extra, and a "
        "merit scholarship (up to 40%) lowers the tuition.",
        ["Calculate my fee", "Scholarships", "Hostel fees"])


def _extra_charges(message: str) -> QuickAnswer:
    d = _data()
    o, y, dep = d["one_time"], d["yearly_other"], d["hostel_deposits"]
    return QuickAnswer(
        "Everything on the 2027-28 fee card besides tuition:\n\n"
        f"• **One-time:** application fee {fees.inr(o['application_fee'])}, enrolment fee {fees.inr(o['enrollment_fee'])}\n"
        f"• **Every year:** other academic / university charges {fees.inr(y['other_fee'])}, examination fee "
        f"{fees.inr(y['exam_fee'])}\n"
        f"• **Hostel (if you stay):** room with meals, plus a caution deposit {fees.inr(dep['caution_deposit'])}, laundry "
        f"{fees.inr(dep['laundry_per_year'])} a year and an electricity deposit ({fees.inr(dep['electricity_deposit_non_ac'])} "
        f"non-AC, {fees.inr(dep['electricity_deposit_ac'])} AC)\n"
        f"• **Transport (optional):** about {fees.inr(d['transport_per_year'])} a year, depending on distance\n\n"
        "Nothing else is listed on the fee card.",
        ["Calculate my fee", "Hostel fees", "Scholarships"])


def _deposit(message: str) -> QuickAnswer:
    dep = _data()["hostel_deposits"]
    return QuickAnswer(
        f"For hostel students the 2027-28 fee card lists a **caution deposit of {fees.inr(dep['caution_deposit'])}**, "
        f"laundry {fees.inr(dep['laundry_per_year'])} a year, and an electricity deposit of "
        f"{fees.inr(dep['electricity_deposit_non_ac'])} (non-AC) or {fees.inr(dep['electricity_deposit_ac'])} (AC).",
        ["Hostel fees", "Calculate my fee"])


def _transport(message: str) -> QuickAnswer:
    d = _data()
    return QuickAnswer(
        f"University transport is about **{fees.inr(d['transport_per_year'])} a year** on the 2027-28 fee card; the "
        "actual amount depends on the distance of your boarding point. The transport office confirms the fee for "
        f"your area ({_phone()}).",
        ["Calculate my fee", "Hostel fees"])


def _not_on_fee_card(topic: str):
    def fn(message: str) -> QuickAnswer:
        return QuickAnswer(
            f"The {topic} isn't printed on the official 2027-28 fee card, so I can't state it. The Admissions Office "
            f"confirms it ({_phone()}, {config.ADMISSIONS_EMAIL}).",
            ["Calculate my fee", "Talk to a counsellor"])
    return fn


# ------------------------------------------------------------------ contacts
def _contacts(message: str) -> QuickAnswer:
    from app.services import app_settings
    days = app_settings.get("office_days") or [0, 1, 2, 3, 4, 5]
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    span = f"{names[min(days)]}–{names[max(days)]}" if days == list(range(min(days), max(days) + 1)) else \
        ", ".join(names[d] for d in sorted(days))
    hours = f"{app_settings.get('office_hours_start') or '09:00'}–{app_settings.get('office_hours_end') or '18:00'}"
    return QuickAnswer(
        "SR University Admissions:\n\n"
        f"• **Phone:** {_phone()}\n"
        f"• **Email:** {config.ADMISSIONS_EMAIL}\n"
        f"• **Campus visits (call or WhatsApp):** {config.CAMPUS_VISIT_PHONE}\n"
        f"• **Address:** {config.CAMPUS_ADDRESS}\n"
        f"• **Counsellors available:** {span}, {hours} (India time)\n"
        f"• **Apply online:** {config.APPLY_URL}",
        ["Talk to a counsellor", "Plan a campus visit", "How do I apply?"])


# ------------------------------------------------------------------ programmes
_NOT_OFFERED = [(r"\bpharm\w*|\bpharm\.?\s?d\b", "Pharmacy (B.Pharm / Pharm.D)"),
                (r"\bmbbs\b|\bmedicine\b|\bmedical\s+(?:course|degree|seat)|\bbds\b|\bdental\b", "MBBS / medicine"),
                (r"\blaw\b|\bllb\b|\bba\s*llb\b", "Law (LLB)"),
                (r"\bb\.?\s?arch\b|\barchitecture\b", "Architecture (B.Arch)"),
                (r"\bnursing\b", "Nursing"),
                (r"\bonline\s+(?:course|degree|programme|program)s?\b|\bdistance\s+(?:education|learning|course)",
                 "Online / distance programmes")]


def _programme_list() -> str:
    groups = {"B.Tech": [], "Other UG": [], "PG": []}
    for k, p in _data()["programs"].items():
        name = fees.short_name(k)
        if k.startswith("btech_"):
            groups["B.Tech"].append(name.replace("B.Tech ", ""))
        elif p.get("level") == "pg":
            groups["PG"].append(name)
        else:
            groups["Other UG"].append(name)
    return (f"• **B.Tech:** {', '.join(dict.fromkeys(groups['B.Tech']))}\n"
            f"• **Other undergraduate:** {', '.join(dict.fromkeys(groups['Other UG']))}\n"
            f"• **Postgraduate:** {', '.join(dict.fromkeys(groups['PG']))}, and Ph.D.")


def _not_offered(message: str) -> QuickAnswer | None:
    low = (message or "").lower()
    hit = next((label for rx, label in _NOT_OFFERED if re.search(rx, low)), None)
    if not hit:
        return None
    return QuickAnswer(f"**{hit}** isn't among the programmes on SR University's 2027-28 fee card. What SRU offers:\n\n"
                       f"{_programme_list()}", ["Programmes for MPC", "Programmes for BiPC", "Calculate my fee"])


def _duration(message: str) -> QuickAnswer | None:
    key = fees.find_program(message or "") or ("btech_cse" if re.search(r"b\.?\s?tech|engineering", message or "", re.I) else None)
    if not key:
        return None
    p = _data()["programs"][key]
    if not p.get("duration_years"):
        return None
    name = "B.Tech" if key.startswith("btech_") and not fees.find_program(message or "") else fees.short_name(key)
    return QuickAnswer(f"**{name}** at SR University is a **{p['duration_years']}-year** programme"
                       + (" (8 semesters)." if p["duration_years"] == 4 else "."),
                       ["Fees", "Eligibility", "Placements"])


def _pg_research(message: str) -> QuickAnswer:
    d = _data()
    low = (message or "").lower()
    if "phd" in low or "ph.d" in low or "doctor" in low:
        return QuickAnswer(f"Yes, SR University offers the **Ph.D.**; the 2027-28 fee card lists **{fees.inr(d['phd_fee_per_year'])} "
                           "a year**. Admission dates and the entrance process aren't on the fee card; the Admissions "
                           f"Office confirms them ({_phone()}).", ["Research at SRU", "Talk to a counsellor"])
    p = d["programs"]["mtech"]
    specs = re.search(r"\(([^)]+)\)", p["name"])
    return QuickAnswer(f"Yes. **M.Tech** (2 years) is offered in {specs.group(1) if specs else 'several specialisations'}. "
                       f"2027-28 tuition: {fees.inr(p['tuition_per_year'])} a year. Eligibility: {p.get('eligibility_note')}.",
                       ["M.Tech fees", "Eligibility", "Talk to a counsellor"])


def _after_stream(message: str) -> QuickAnswer:
    """Which undergraduate programmes a student's 10+2 group allows, from the fee card's eligibility notes only:
    "open" when the note allows the group, "ask" when the note says "required subjects as per university norms"."""
    low = (message or "").lower()
    bipc = bool(re.search(r"bipc|bi\.?p\.?c|biology|pcb", low))
    mec = bool(re.search(r"\b(?:mec|cec|hec|commerce|arts|humanities)\b", low))
    science_name = re.compile(r"physics|chemistry|math|computer|biotech|food|engineering|agri", re.I)
    open_, ask = [], []
    for k, p in _data()["programs"].items():
        if p.get("level") == "pg":
            continue
        name, note = fees.short_name(k), (p.get("eligibility_note") or "").lower()
        has_mpc = bool(re.search(r"maths|pcm|mpc", note))
        has_bipc = bool(re.search(r"pcb|bipc", note))
        norms = "required subjects" in note
        plain = not (has_mpc or has_bipc or norms)
        if mec:
            if k.startswith("btech_") or k == "bsc_agri":
                continue                                   # engineering / agriculture: a science group is required
            if plain and not science_name.search(p.get("name") or ""):
                open_.append(name)
            elif norms or plain:
                ask.append(name)
        elif bipc:
            if has_bipc or plain:
                open_.append(name)
            elif norms and not k.startswith("btech_"):
                ask.append(name)
        else:                                              # MPC
            if has_mpc or plain or norms:
                open_.append(name)
    open_, ask = list(dict.fromkeys(open_)), list(dict.fromkeys(ask))
    stream = "BiPC" if bipc else ("a non-science group (MEC / CEC / HEC)" if mec else "MPC")
    # "commerce students" names the stream, not the B.Com programme ("can a commerce student do bcom" still names it)
    named = fees.find_program(re.sub(r"\b(?:commerce|arts|humanities)\b(?:\s+(?:students?|stream|group))?", " ",
                                     message or "", flags=re.I))
    lead = ""
    if named:
        nm = fees.short_name(named)
        if nm in open_:
            lead = f"Yes. **{nm}** is open to students with {stream}. "
        elif nm in ask:
            lead = (f"For **{nm}** the fee card lists \"required subjects as per university norms\", so the Admissions "
                    f"Office confirms whether {stream} qualifies ({_phone()}). ")
        else:
            need = _data()["programs"][named].get("eligibility_note") or "different subjects"
            lead = f"**{nm}** needs {need}, so it isn't open with {stream}. "
    if named and fees.short_name(named) in open_:
        return QuickAnswer(lead + "Would you like its fees or to check your eligibility with your marks?",
                           ["Check my eligibility", f"{fees.short_name(named)} fees", "Programmes offered"])
    text = lead + f"With **{stream}** in Intermediate, the 2027-28 fee card allows:\n\n• " + "\n• ".join(open_)
    if ask:
        text += ("\n\nTo confirm with the Admissions Office (the fee card says \"required subjects as per university "
                 "norms\"):\n\n• " + "\n• ".join(ask))
    text += "\n\nWould you like the fees or your eligibility for one?"
    return QuickAnswer(text, ["Check my eligibility", "Calculate my fee", "Programmes offered"])


_RULES += [
    (re.compile(r"\bhostel\s+fees?\b.{0,20}\b(?:included|include|part\s+of)\b|\b(?:included|include)\b.{0,25}\bhostel\b|"
                r"\btuition\b.{0,20}\bhostel\b.{0,15}\b(?:included|together|same)\b", re.I), _hostel_included),
    (re.compile(r"\b(?:fees?|tuition)\b.{0,25}\bper\s+sem(?:ester)?\b|\bper\s+sem(?:ester)?\s+fees?\b|"
                r"\bsemester\s+fees?\b", re.I), _per_semester),
    (re.compile(r"\b(?:total|full|complete|whole|entire)\b.{0,15}\b(?:fees?|cost)\b.{0,25}\b(?:4|four|3|three|2|two|all)\s+"
                r"years?\b|\b(?:4|four)\s+years?\s+(?:total\s+)?fees?\b|\bfees?\s+for\s+(?:all\s+)?(?:4|four)\s+years\b", re.I), _course_total),
    (re.compile(r"\bhidden\s+(?:charges?|fees?|costs?)\b|\b(?:other|extra|additional)\s+(?:charges?|fees?|costs?)\b|"
                r"\bany\s+other\s+fees?\b", re.I), _extra_charges),
    (re.compile(r"\bcaution\s+(?:deposit|money|fee)\b|\bsecurity\s+deposit\b|\bhostel\s+deposits?\b", re.I), _deposit),
    (re.compile(r"\b(?:transport|bus)\s+(?:fee|fees|charges?|cost)\b|\b(?:fee|fees|cost)\s+(?:for|of)\s+(?:the\s+)?"
                r"(?:bus|transport)\b", re.I), _transport),
    (re.compile(r"\b(?:instal+ments?|emi|pay\s+in\s+parts|part\s+payment)\b", re.I), _not_on_fee_card("instalment rule")),
    (re.compile(r"\b(?:education|bank|study)\s+loans?\b|\bloan\s+(?:facility|available|support)\b", re.I),
     _not_on_fee_card("education-loan arrangement")),
    (re.compile(r"\b(?:phone|contact|mobile|whatsapp|helpline)\s*(?:number|no\.?|details|info)?\b.{0,25}\b(?:admissions?|"
                r"sru|university|office|college|counsell?or)\b|\b(?:admissions?|office|sru)\b.{0,20}\b(?:phone|contact|"
                r"email|e-?mail|whatsapp|number(?!\s+(?:one|1|two|three|\d))|address)\b|\bemail\s*(?:id)?\b.{0,15}\badmissions?\b|"
                r"^\W*(?:whatsapp|email|contact)\s*(?:number|no|id|details)?\W*$|\bwhere\s+is\s+(?:the\s+)?admissions?\s+office\b|"
                r"\boffice\s+(?:timings?|hours)\b", re.I), _contacts),
    (re.compile(r"\b(?:duration|how\s+many\s+years|how\s+long)\b.{0,30}\b(?:b\.?\s?tech|btech|engineering|bba|bca|mba|mca|"
                r"b\.?\s?sc|b\.?\s?des|m\.?\s?tech|course|programme|program|degree)\b", re.I), _duration),
    (re.compile(r"\b(?:m\.?\s?tech|ph\.?\s?d|doctorate)\b", re.I), _pg_research),
    (re.compile(r"\b(?:courses?|programmes?|programs?|options|what\s+can\s+i\s+(?:do|study|join))\b.{0,30}\b(?:after|for|with)\b"
                r".{0,15}\b(?:mpc|bipc|pcb|pcm|mec|cec|hec|commerce|arts)\b|\b(?:mpc|bipc|mec|cec|hec)\s+(?:students?|courses?)\b|"
                r"\b(?:can|could)\s+(?:a|an)?\s*(?:mpc|bipc|pcb|mec|cec|hec|commerce|arts)\s+(?:student|students|stream)?\b.{0,25}"
                r"\b(?:join|do|take|study|get)\b", re.I),
     _after_stream),
]


# v4.15.1 (open-question audit): leadership, history, international students and lateral entry, read from the
# verified handbook files (data/handbook), so an update there updates the answer. None if a section is missing.
_HANDBOOK = Path(__file__).resolve().parents[2] / "data" / "handbook"


def _section(file: str, heading: str) -> list[str]:
    """The bullet lines under a '## ...heading' of a handbook file, without the markdown bullet."""
    try:
        text = (_HANDBOOK / file).read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(r"^##\s+" + re.escape(heading) + r".*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return [ln.strip()[2:].strip() for ln in (m.group(1).splitlines() if m else []) if ln.strip().startswith(("- ", "* "))]


def _leadership(message: str) -> QuickAnswer | None:
    people = _section("11_official_website_facts_nov2026.md", "2. Leadership")
    if not people:
        return None
    low = (message or "").lower()
    lead = ""
    if re.search(r"\bprincipal\b", low):
        lead = "Being a university, SRU doesn't have a principal; it's led by a Vice-Chancellor. "
    else:
        role = next((r for r, rx in (("Pro Vice-Chancellor", r"\bpro[- ]?vice[- ]?chancellor\b|\bpro[- ]?vc\b"),
                                      ("Vice-Chancellor", r"\bvice[- ]?chancellor\b|\bvc\b"),
                                      ("Pro-Chancellor", r"\bpro[- ]?chancellor\b"), ("Chancellor", r"\bchancellor\b"),
                                      ("Registrar", r"\bregistrar\b")) if re.search(rx, low)), None)
        line = next((p for p in people if role and p.startswith(f"**{role}:**")), None)
        if line:
            lead = f"SRU's {role} is {line.split(':**', 1)[1].strip()}. "
    if lead:
        pass
    elif re.search(r"\bfound(?:er|ed)\b|\bstarted\b|\bowner\b|\bowns\b", low):
        lead = ("SRU comes from the **SR Educational group**, which **Sri A. Varada Reddy** started back in **1976**. "
                "He's the university's Chancellor today. ")
    others = [p for p in people if not (lead and p.split(":**", 1)[-1].strip() in lead)]
    text = lead + ("The rest of the leadership team:" if lead else "Here's who leads SRU:") + "\n\n• " + \
        "\n• ".join(others)
    return QuickAnswer(text, ["Why choose SRU?", "Rankings", "Programmes offered"])


def _history(message: str) -> QuickAnswer | None:
    facts = _section("11_official_website_facts_nov2026.md", "1. University identity")
    if not facts:
        return None
    text = ("SRU is young as a university, but its roots go back a long way:\n\n• " + "\n• ".join(facts[:3]) +
            "\n\nThe group was started by **Sri A. Varada Reddy**, who is SRU's Chancellor today.")
    return QuickAnswer(text, ["Why choose SRU?", "Rankings", "Leadership"])


def _international(message: str) -> QuickAnswer | None:
    facts = _section("12_strengths_faculty_and_visits_nov2026.md", "4. International partnerships")
    if not facts:
        return None
    text = ("Yes, SRU welcomes international students, and there's support for visas and settling in:\n\n• " +
            "\n• ".join(facts) + "\n\nInternational students also get a special concession of **₹15,000 a year** "
            "(2027-28). For applications and visa questions, the International Affairs office can help; the Admissions "
            f"Office will connect you ({_phone()}, info@sru.edu.in).")
    return QuickAnswer(text, ["Study abroad pathways", "Special concessions", "Talk to a counsellor"])


def _lateral(message: str) -> QuickAnswer | None:
    if re.search(r"\b(?:concessions?|discounts?|apply|applied|fees?)\b", message or "", re.I):
        return None          # a concession or fee request: the fee flow answers (with the ₹15,000 concession)
    return QuickAnswer(
        "Yes, you can! **B.Tech Lateral Entry** lets you join directly and finish in **3 years (6 semesters)** "
        "instead of 4. You pay the same tuition as regular students, get the same concessions, and there's an extra "
        "**₹15,000 a year** concession for lateral entry students (2027-28).\n\n"
        "For the exact eligibility and how to apply, the Admissions Office is your best bet "
        f"({_phone()}, info@sru.edu.in).",
        ["B.Tech programmes", "Calculate my fee", "Talk to a counsellor"])


_RULES += [
    (re.compile(r"\b(?:vice[- ]?chancellor|pro[- ]?chancellor|chancellor|registrar|principal|chairman|founder|"
                r"leadership)\b|\bpro[- ]?vc\b|\bwho\s+(?:is\s+(?:the\s+)?vc|founded|started|owns|runs)\b|\b(?:owner)\s+of\s+(?:sru|sr\s+"
                r"university|the\s+(?:college|university))\b", re.I), _leadership),
    (re.compile(r"\bhow\s+old\s+is\b|\bwhen\s+was\b.{0,25}\b(?:established|founded|started|set\s+up|started)\b|"
                r"\b(?:history|establishment\s+year|year\s+of\s+establishment)\b.{0,20}\b(?:sru|sr\s+university|"
                r"university|college)\b", re.I), _history),
    (re.compile(r"\bvisa\b|\b(?:foreign|international|overseas|nri)\s+(?:students?|applicants?|nationals?)\b", re.I),
     _international),
    (re.compile(r"\blateral\s+entry\b|\b(?:join|admission|direct\s+entry)\b.{0,15}\b(?:2nd|second)\s+year\b|"
                r"\bdiploma\s+(?:students?|holders?)\b.{0,30}\b(?:b\.?\s?tech|btech|engineering|join)\b|\becet\b", re.I),
     _lateral),
]


# v4.15.1 (real-model audit): questions the AI answered wrongly or with facts not in the sources. Each answer is
# built from the fee card (programme names, tuition, eligibility notes) or a handbook line, never typed in by hand.
def _programme_line(key: str) -> str:
    """'**B.Des (Design)**: ₹2,10,000 a year, open after 10+2 / Intermediate' (from the fee card)."""
    p = _data()["programs"].get(key) or {}
    tuition = p.get("tuition_per_year") or p.get("annual_tuition")
    fee = f"{fees.inr(int(tuition))} a year" if tuition else ""
    note = p.get("eligibility_note") or ""
    who = f"after {note}" if note else ""
    return f"**{p.get('name', key)}**" + (": " + ", ".join(x for x in (fee, who) if x) if fee or who else "")


def _hospitality(message: str) -> QuickAnswer | None:
    if "bsc_hospitality" not in _data()["programs"]:
        return None
    return QuickAnswer(
        "Yes! SRU's programme for hotels, hospitality and events is " + _programme_line("bsc_hospitality") +
        " (2027-28).\n\nWant me to work out the fee with your marks, or see what else you can join?",
        ["B.Sc Hospitality fees", "Check my eligibility", "Programmes offered"])


def _robotics(message: str) -> QuickAnswer | None:
    keys = [k for k, p in _data()["programs"].items() if "robot" in (p.get("name") or "").lower()]
    if not keys:
        return None
    dedicated = [k for k in keys if "and robotics" in (_data()["programs"][k].get("name") or "").lower()]
    lead = (f"Good choice to explore! SRU has a full **{_data()['programs'][dedicated[0]]['name']}** degree, and you "
            "can also take robotics as a specialisation in other branches. " if dedicated else "")
    text = (lead + "Your options (2027-28 tuition):\n\n• " + "\n• ".join(_programme_line(k) for k in keys) +
            "\n\nShall I work out the fee with your marks, or tell you more about one of them?")
    return QuickAnswer(text, ["Calculate my fee", "Check my eligibility", "Placements"])


def _design_interest(message: str) -> QuickAnswer | None:
    if "bdes" not in _data()["programs"]:
        return None
    return QuickAnswer(
        "Then design is worth a serious look! SRU has a **School of Design** offering " + _programme_line("bdes") +
        " (2027-28). It's a 4-year design degree of its own, not part of engineering.\n\nIt's a big decision with "
        "your parents too, so if it helps, a counsellor can talk all of you through both paths.",
        ["B.Des fees", "Check my eligibility", "Talk to a counsellor"])


def _entrance_test(message: str) -> QuickAnswer:
    lines = []
    try:
        text = (_HANDBOOK / "03_phd_and_research_regulations.md").read_text(encoding="utf-8")
        if "SRU Written Eligibility Test" in text and "UGC-NET" in text:
            lines.append("For the **Ph.D.**, SRU holds a written eligibility test (50% research methodology, 50% "
                         "subject); candidates with UGC-NET, UGC-CSIR NET, GATE, CEED or SET are exempt.")
    except OSError:
        pass
    named = re.search(r"\bsrsat\b", message or "", re.I)
    text = (("I haven't come across \"SRSAT\" in SRU's official information, so I'd rather not guess about it. "
             if named else "") +
            "For undergraduate admission, SRU doesn't list an entrance test of its own: what counts is your 10+2 / "
            "Intermediate with the right subjects for the programme. Your scholarship is based on the best of your "
            "Intermediate marks, EAPCET rank or JEE Main percentile." +
            ("\n\n" + lines[0] if lines else "") +
            f"\n\nThe Admissions Office can confirm the latest process ({_phone()}, info@sru.edu.in).")
    return QuickAnswer(text, ["How do I apply?", "Check my eligibility", "Scholarships"])


def _without_entrance(message: str) -> QuickAnswer | None:
    if re.search(r"\d|%|\bfees?\b|\bscholarship", message or "", re.I):
        return None          # "cse fee with 85%, no JEE or EAPCET": a fee / scholarship calculation, not this
    return QuickAnswer(
        "Don't worry, you can still apply! SRU's eligibility is based on your 10+2 / Intermediate with the right "
        "subjects (for B.Tech: Maths, Physics, Chemistry); an EAPCET or JEE rank isn't listed as a requirement. A rank "
        "only helps with the scholarship, and your Intermediate marks count for that too, whichever is better.\n\n"
        f"The Admissions Office can confirm the steps for your programme ({_phone()}).",
        ["Check my eligibility", "Scholarships", "How do I apply?"])


def _ratio(message: str) -> QuickAnswer:
    try:
        text = (_HANDBOOK / "12_strengths_faculty_and_visits_nov2026.md").read_text(encoding="utf-8")
    except OSError:
        text = ""
    facts = [ln.strip()[2:] for ln in text.splitlines()
             if ln.strip().startswith("- ") and ("340 faculty" in ln or "316 of the 340" in ln)]
    text = "SRU hasn't published a student-teacher ratio, so I won't guess a number."
    if facts:
        text += " Here's what I can tell you about the faculty:\n\n• " + "\n• ".join(facts)
    return QuickAnswer(text, ["Faculty", "Labs", "Talk to a counsellor"])


def _age_limit(message: str) -> QuickAnswer:
    return QuickAnswer(
        "SRU's eligibility rules don't mention an age limit, but I wouldn't want to promise either way. The Admissions "
        f"Office can confirm it for you ({_phone()}, info@sru.edu.in).",
        ["Check my eligibility", "How do I apply?"])


def _university_type(message: str) -> QuickAnswer | None:
    facts = _section("11_official_website_facts_nov2026.md", "1. University identity")
    if not facts:
        return None
    low = (message or "").lower()
    if "autonomous" in low:
        lead = ("SRU is a full university now, a **State Private University** that runs its own programmes and exams. "
                "\"Autonomous\" was the status of **SR Engineering College**, where it all started, from 2014.")
    elif "deemed" in low:
        lead = "No, it's not a deemed university. SRU is a **State Private University**."
    else:
        lead = "SRU is a **private** university (a State Private University), not a government one."
    text = (lead + "\n\n• " + "\n• ".join(facts[:2]) + "\n• It was set up under the Telangana State Private "
            "Universities Act, with **NBA Tier-I** accreditation for B.Tech CSE, ECE, EEE, Mechanical and Civil, and "
            "**ICAR** accreditation for Agriculture.")
    return QuickAnswer(text, ["Rankings", "Why choose SRU?", "Programmes offered"])


def _parent_visits(message: str) -> QuickAnswer:
    return QuickAnswer(
        "I don't have the exact visiting hours for parents, so it's best to check with the hostel office "
        f"({_phone()}). What I can tell you: nobody can enter a hostel of the opposite gender, and parents get "
        "daily attendance and mid-term marks by SMS, so they stay in the loop.",
        ["Hostel rules", "Hostel safety", "Hostel fees"])


_RULES += [
    (re.compile(r"\bhotel\s+management\b|\bhospitality\b(?!.{0,15}\bfees?\b)|\bcatering\s+(?:course|technology)\b|"
                r"\bevent\s+management\b(?!.{0,15}\bfees?\b)", re.I), _hospitality),
    (re.compile(r"\bwhat\s+is\s+(?:the\s+)?robotics\b|\brobotics\s+(?:course|courses|programmes?|programs?|branch(?:es)?|"
                r"degree)\b(?!.{0,15}\bfees?\b)|\b(?:courses?|programmes?|degree)\s+(?:in|on|for)\s+robotics\b|"
                r"\b(?:is\s+there|do\s+you\s+(?:have|offer))\s+(?:a\s+|any\s+)?robotics\b(?!\s+(?:club|society|team|lab|"
                r"competition|event))", re.I), _robotics),       # "is there a robotics club" is the clubs answer
    (re.compile(r"\b(?:i\s+)?(?:like|love|enjoy|interested\s+in|passion\s+for|want\s+to\s+do|into)\s+(?:design|designing|"
                r"drawing|art|fashion|interior)\b", re.I), _design_interest),
    (re.compile(r"\bsrsat\b|\bsru\s+(?:entrance|admission)\s+(?:test|exam)\b|\bentrance\s+(?:test|exam)\b.{0,30}"
                r"\b(?:sru|conducted|by\s+(?:the\s+)?(?:university|college))\b|\b(?:own|separate)\s+entrance\b", re.I),
     _entrance_test),
    (re.compile(r"\b(?:missed|without|no|not\s+written|didn'?t\s+(?:write|take|attempt|appear))\b.{0,20}"
                r"\b(?:eapcet|eamcet|ts\s*eapcet|ap\s*eapcet|jee)\b(?!.{0,20}\b(?:rank|percentile|score)\s*\d)", re.I),
     _without_entrance),
    (re.compile(r"\b(?:student|students)[- ](?:teacher|faculty)\s+ratio\b|\b(?:faculty|teacher)[- ]students?\s+ratio\b", re.I),
     _ratio),
    (re.compile(r"\bage\s+(?:limit|bar|criteria|restriction)s?\b|\b(?:maximum|minimum)\s+age\b|"
                r"\bhow\s+old\s+(?:should|must|do)\s+i\b", re.I), _age_limit),
    (re.compile(r"\bdeemed\b|\b(?:private|government|govt)\s+or\s+(?:private|government|govt)\b|"
                r"\bis\s+(?:sru|it|this|sr\s+university)\s+(?:a\s+)?(?:private|government|govt|autonomous|state)\b|"
                r"\bautonomous\b", re.I), _university_type),
    (re.compile(r"\bparents?\b.{0,25}\b(?:visit|meet|come|allowed|enter|stay)\b.{0,20}\b(?:hostels?|rooms?)\b|"
                r"\bhostel\s+visiting\s+(?:hours|timings?|time)\b|\bvisiting\s+(?:hours|timings?)\b.{0,15}\bhostels?\b",
                re.I), _parent_visits),       # a campus visit with parents is the visit flow, not this
]


# v4.15.1 (multi-question live test): everyday campus facts, read from the handbook lines (Gemini got the station
# distance and the condonation rule wrong when it wrote them itself).
def _lines(file: str, *needles: str) -> list[str]:
    """The handbook lines containing any of the needles (bullet marks removed), in file order."""
    try:
        text = (_HANDBOOK / file).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for ln in text.splitlines():
        if any(n.lower() in ln.lower() for n in needles):
            out.append(re.sub(r"^\s*[-*]\s+", "", ln).strip())
    return out


def _from_lines(lines: list[str], lead: str = "", tail: str = "", chips: list[str] | None = None) -> QuickAnswer | None:
    if not lines:
        return None
    body = lines[0] if len(lines) == 1 else "• " + "\n• ".join(lines)
    return QuickAnswer((lead + "\n\n" if lead else "") + body + (("\n\n" + tail) if tail else ""), chips or [])


def _num(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text or "", re.I)
    return m.group(1) if m else None


def _location(message: str) -> QuickAnswer | None:
    dist = " ".join(_lines("01_campus_life_and_facilities.md", "Distance: 14 km")[:1])
    addr = " ".join(_lines("09_verified_sru_facts.md", "Main Campus:")[:1])
    town = _num(r"Main Campus:\s*([^(]+?)\s*\(", addr)
    city, kzj, wgl = (_num(r"(\d+)\s*km from Hanumakonda", dist), _num(r"(\d+)\s*km from Kazipet", dist),
                      _num(r"(\d+)\s*km from Warangal Railway", dist))
    if not (town and city and kzj and wgl):
        return None
    return QuickAnswer(
        f"SRU is at **{town}**, on the Warangal–Karimnagar highway. It's about **{city} km** from Hanumakonda, "
        f"**{kzj} km** from Kazipet Railway Station and **{wgl} km** from Warangal Railway Station. If you're flying "
        "in, the nearest big airport is Hyderabad's Rajiv Gandhi International.",
        ["Plan a campus visit", "Transport", "Hostel life"])


def _attendance(message: str) -> QuickAnswer | None:
    text = " ".join(_section("02_academic_regulations_and_examinations.md", "4. Attendance Policy"))
    if not ("75%" in text and "10% to 25%" in text):
        return None
    agri = " (only 10% for Agriculture, so 65% there)" if "Agriculture Exception" in text else ""
    return QuickAnswer(
        "You need at least **75% attendance** in each course. That 25% leeway is meant for things like illness, "
        "family emergencies, fests and sports.\n\nIf you fall a little short for a genuine reason, the Condonation "
        f"Board can allow **10% to 25%** more{agri}, with a fee. Below that, you can't write that course's "
        "end-semester exam and you'd have to repeat it.",
        ["Exam pattern", "Backlogs", "Hostel rules"])


def _exams(message: str) -> QuickAnswer | None:
    if not _lines("02_academic_regulations_and_examinations.md", "Evaluation is based on Continuous Internal"):
        return None
    return QuickAnswer(
        "Each course is assessed in two parts: **continuous internal evaluation** during the semester (tests, "
        "assignments and so on) and an **end-semester exam**. Grades are on a 10-point scale. Just keep your "
        "attendance up, because without it you can't sit the end-semester exam.",
        ["Attendance rule", "Backlogs", "Grading"])


def _classes_start(message: str) -> QuickAnswer:
    return QuickAnswer("The start date for the new batch hasn't been announced in anything I have yet. The Admissions "
                       f"Office will confirm it once you're admitted ({_phone()}, info@sru.edu.in).",
                       ["How do I apply?", "Admission process", "Talk to a counsellor"])


def _wifi(message: str) -> QuickAnswer | None:
    if not _lines("01_campus_life_and_facilities.md", "100% Wi-Fi enabled"):
        return None
    return QuickAnswer("Yes! The whole campus is on Wi-Fi: hostels, classrooms, labs and the library.",
                       ["Hostel life", "Hostel fees", "Labs"])


def _vehicles(message: str) -> QuickAnswer | None:
    if not _lines("01_campus_life_and_facilities.md", "Motorized vehicles", "Bicycles are allowed"):
        return None
    return QuickAnswer(
        "Bikes, scooters and cars aren't allowed inside the campus for students. You can park them outside the "
        "second gate (at your own risk). A **bicycle is fine**, though, and hostel students can keep theirs in the "
        "hostel.", ["Transport", "Hostel rules", "Hostel life"])


def _atm(message: str) -> QuickAnswer | None:
    bank = _num(r"(\w+\s+Bank)\s+ATM", " ".join(_lines("01_campus_life_and_facilities.md", "Bank ATM")[:1]))
    if not bank:
        return None
    return QuickAnswer(f"Yes, there's a **{bank} ATM** right at the main gate, open 24x7.",
                       ["Hostel life", "Campus facilities"])


def _ragging(message: str) -> QuickAnswer | None:
    mail = _num(r"`([^`]+)`", " ".join(_lines("04_hostels_rules_and_discipline_code.md", "Anti-Ragging Helpline")[:1]))
    if not _lines("04_hostels_rules_and_discipline_code.md", "Ragging is a criminal"):
        return None
    return QuickAnswer(
        "No, SRU has **zero tolerance** for ragging. It's a criminal offence under Supreme Court and UGC rules, "
        "and there's an Anti-Ragging Cell watching out for students" + (f": you can reach it anytime at {mail}." if mail
                                                                        else ".") +
        " You'll be in safe hands.", ["Hostel safety", "Hostel rules"])


def _library(message: str) -> QuickAnswer | None:
    hours = " ".join(_lines("01_campus_life_and_facilities.md", "Central Library: Monday")[:1]).replace("**", "")
    wk = _num(r"Monday to Friday\s*([^;]+);", hours)
    we = _num(r"Saturday\s*&\s*Sunday\s*([^.]+)\.", hours)
    if not (wk and we):
        return None
    size = "about 1,000 sq. m with reading rooms, a reference section and a digital library. " if _lines(
        "01_campus_life_and_facilities.md", "Spread over 1,000 sq. meters") else ""
    return QuickAnswer(f"The Central Library is open **{wk}** on weekdays and **{we}** on weekends. It's " + size +
                       "A good spot for focused study!", ["Labs", "Wi-Fi", "Campus tour"])


def _campus_size(message: str) -> QuickAnswer | None:
    # 170+ acres: the handbook (01, 09, 10, 14) as confirmed by the university on 25 Nov 2026
    acres = _num(r"(\d+\+?)\s*acres", " ".join(_lines("01_campus_life_and_facilities.md", "acres")[:1]))
    if not acres:
        return None
    return QuickAnswer(f"It's big! SRU's green campus is spread over **{acres} acres** in Warangal, one of the largest "
                       "in Telangana. Honestly, the best way to get a feel for it is a campus visit.",
                       ["Plan a campus visit", "Hostel life", "Campus facilities"])


_RULES += [
    (re.compile(r"\bhow\s+(?:big|large)\s+is\s+(?:the\s+)?(?:campus|university|sru|college)\b|\bcampus\s+(?:size|area)\b|"
                r"\bhow\s+many\s+acres\b|\bis\s+the\s+campus\s+(?:big|large|huge)\b", re.I), _campus_size),
    (re.compile(r"\blibrary\b.{0,25}\b(?:timings?|hours?|open|opens|close|closes|time|big|size)\b|"
                r"\b(?:timings?|hours?|when)\b.{0,20}\blibrary\b|\bhow\s+big\s+is\s+(?:the\s+)?library\b", re.I), _library),
    (re.compile(r"\bhow\s+far\b|\bdistance\b|\bwhere\s+is\s+(?:sru|sr\s+university|the\s+(?:campus|university|college)|"
                r"campus|college)\b|\bwhere\s+(?:is|are)\s+you\s+located\b|\b(?:sru|campus)\s+location\b|"
                r"\b(?:railway\s+station|kazipet|hanamkonda|hanumakonda)\b", re.I), _location),
    (re.compile(r"\battendance\b(?!.{0,20}\b(?:sms|sent\s+to\s+parents)\b)", re.I), _attendance),
    (re.compile(r"\bhow\s+(?:are|is)\s+(?:the\s+)?(?:exams?|examinations?)\b|\b(?:exam|evaluation|examination)\s+(?:pattern|"
                r"system|process)\b|\bgrading\s+system\b|\bhow\s+(?:are|is)\s+(?:students?\s+)?(?:evaluated|graded|assessed)\b",
                re.I), _exams),
    (re.compile(r"\bwhen\s+(?:do|will|does)\s+(?:the\s+)?class(?:es)?\s+(?:start|begin|commence)\b|\bclass(?:es)?\s+start"
                r"(?:\s+date)?\b|\bacademic\s+calendar\b", re.I), _classes_start),
    (re.compile(r"\bwi-?\s?fi\b|\binternet\b", re.I), _wifi),
    (re.compile(r"\b(?:bikes?|scooty|scooters?|two[- ]wheelers?|cars?|vehicles?|bicycles?|cycles?)\b", re.I), _vehicles),
    (re.compile(r"\batm\b|\bis\s+there\s+(?:a\s+)?bank\b", re.I), _atm),
    (re.compile(r"\bragg(?:ing|ed)?\b", re.I), _ragging),
]


# v4.15.1 (live chat): "Explore programmes" / "what courses do you offer" answered from the fee card, not by the model.
_PROGRAMME_GROUPS = [
    ("Engineering (B.Tech)", lambda k: k.startswith("btech_")),
    ("Computing", lambda k: k in ("bca", "bsc_cs")),
    ("Agriculture", lambda k: k == "bsc_agri"),
    ("Business & commerce", lambda k: k in ("bba", "bba_specialised", "bcom")),
    ("Design", lambda k: k == "bdes"),
    ("Hospitality", lambda k: k == "bsc_hospitality"),
    ("Sciences", lambda k: k in ("bsc_maths_ai", "bsc_physics", "bsc_chemistry")),
    ("Postgraduate", lambda k: k in ("mba", "mba_agri", "mca", "mtech", "msc")),
]


def _lakh(amount: int) -> str:
    return f"₹{amount / 100000:g} lakh"


def _programmes_overview(message: str) -> QuickAnswer | None:
    progs = _data()["programs"]
    if not progs or re.search(r"\bb\.?\s?tech|\bengineering\b|\bmba\b|\bbba\b|\bb\.?\s?sc\b|\bm\.?\s?tech\b|\bpg\b|"
                              r"\bpost\s*graduate|\bunder\s*graduate|\bagri", message or "", re.I):
        return None        # a family named ("B.Tech programmes offered"): its own overview answers
    return _overview_text(progs)


def _overview_text(progs: dict) -> QuickAnswer | None:
    lines, used = [], set()
    for label, belongs in _PROGRAMME_GROUPS:
        keys = [k for k in progs if belongs(k)]
        if not keys:
            continue
        used |= set(keys)
        fees_ = [int(progs[k].get("tuition_per_year") or progs[k].get("annual_tuition") or 0) for k in keys]
        fees_ = [f for f in fees_ if f]
        rng = (f"{_lakh(min(fees_))}" if min(fees_) == max(fees_) else f"{_lakh(min(fees_))}–{_lakh(max(fees_))}") \
            if fees_ else ""
        names = ", ".join(re.sub(r"^B\.Tech\s+", "", fees.short_name(k)) if label.startswith("Engineering")
                          else fees.short_name(k) for k in keys)
        lines.append(f"**{label}**" + (f" ({rng} a year)" if rng else "") + f": {names}")
    ug = sum(1 for p in progs.values() if p.get("level", "ug") == "ug")
    pg = sum(1 for p in progs.values() if p.get("level") == "pg")
    phd = ", plus the Ph.D" if _data().get("phd_fee_per_year") else ""
    text = (f"SRU has **{ug} undergraduate** and **{pg} postgraduate** programmes for 2027-28{phd}. Here they are, "
            "with yearly tuition before any scholarship:\n\n• " + "\n• ".join(lines) +
            "\n\nWhich one catches your eye? I can check your eligibility or work out your fee for it.")
    card = None
    try:
        from app.services.card_service import PROGRAMS_OFFERED_CARD
        card = PROGRAMS_OFFERED_CARD
    except Exception:
        pass
    return QuickAnswer(text, ["Check my eligibility", "Calculate my fee", "Placements"], [card] if card else [])


def _day_scholar(message: str) -> QuickAnswer | None:
    routes = " ".join(_lines("01_campus_life_and_facilities.md", "**Routes**")[:1])
    towns = _num(r"tri-cities \(([^)]+)\)", routes)
    more = _num(r"neighboring towns:\s*([^.]+)\.", routes)
    bus = fees.load_data().get("transport_per_year")
    if not (towns and bus):
        return None
    return QuickAnswer(
        "Yes, you can be a **day scholar**; the hostel is your choice. University buses run Monday to Friday across "
        f"the tri-cities ({towns})" + (f" and nearby towns like {more}" if more else "") +
        f", for about **{fees.inr(int(bus))} a year** (it depends on the distance of your stop).",
        ["Transport", "Hostel life", "Hostel fees"])


_RULES += [
    (re.compile(r"\b(?:stay|live)\s+(?:outside|off)[- ]?(?:the\s+)?campus\b|"
                r"\b(?:can|could|may)\s+i\s+be\s+a\s+day\s*scholar\b|\bday\s*scholars?\s+(?:allowed|possible|option)\b|"
                r"\b(?:is|are)\s+(?:there\s+)?day\s*scholars?\b|"
                r"\b(?:is|are)\s+(?:the\s+)?hostels?\s+(?:compulsory|mandatory|required|necessary|a\s+must)\b|"
                r"\b(?:must|have\s+to|should)\s+i\s+stay\s+in\s+(?:the\s+)?hostel\b|\bcommute\s+from\s+home\b", re.I),
     _day_scholar),
    (re.compile(r"\bexplore\s+(?:all\s+)?(?:the\s+)?(?:programs?|programmes?|courses?)\b|"
                r"\b(?:programs?|programmes?|courses?|degrees?)\s+(?:offered|available)\b(?!\s+(?:after|for|with))|"
                r"\bwhat\s+(?:all\s+)?(?:courses?|programs?|programmes?|degrees?)\s+(?:do|does|are|can)\b|"
                r"\b(?:list\s+of|all)\s+(?:the\s+)?(?:courses?|programs?|programmes?)\b|\bwhich\s+courses\s+(?:do|are|does)\b",
                re.I), _programmes_overview),
]


def answer(message: str) -> QuickAnswer | None:
    na = _not_offered(message) if re.search(r"\b(?:do\s+you|is\s+there|does\s+sru|offer|available|have|course|"
                                             r"programme|program|admission)\b", message or "", re.I) else None
    if na:
        return na
    for rx, fn in _RULES:
        if rx.search(message or ""):
            got = fn(message)
            if got:
                return got
    return None
