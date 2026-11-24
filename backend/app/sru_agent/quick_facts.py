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
        lead = "As a university, SRU is led by a Vice-Chancellor rather than a principal. "
    else:
        role = next((r for r, rx in (("Pro Vice-Chancellor", r"\bpro[- ]?vice[- ]?chancellor\b|\bpro[- ]?vc\b"),
                                      ("Vice-Chancellor", r"\bvice[- ]?chancellor\b|\bvc\b"),
                                      ("Pro-Chancellor", r"\bpro[- ]?chancellor\b"), ("Chancellor", r"\bchancellor\b"),
                                      ("Registrar", r"\bregistrar\b")) if re.search(rx, low)), None)
        line = next((p for p in people if role and p.startswith(f"**{role}:**")), None)
        if line:
            lead = f"The {role} of SR University is {line.split(':**', 1)[1].strip()}. "
    if lead:
        pass
    elif re.search(r"\bfound(?:er|ed)\b|\bstarted\b|\bowner\b|\bowns\b", low):
        lead = ("SR University's parent group, the **SR Educational group**, was founded in **1976** by "
                "**Sri A. Varada Reddy**, who is now the university's Chancellor. ")
    text = lead + "SR University's leadership (sru.edu.in/about):\n\n• " + "\n• ".join(people)
    return QuickAnswer(text, ["Why choose SRU?", "Rankings", "Programmes offered"])


def _history(message: str) -> QuickAnswer | None:
    facts = _section("11_official_website_facts_nov2026.md", "1. University identity")
    if not facts:
        return None
    text = ("SR University's story (sru.edu.in/about):\n\n• " + "\n• ".join(facts[:3]) +
            "\n\nThe group was founded by **Sri A. Varada Reddy**, now SR University's Chancellor.")
    return QuickAnswer(text, ["Why choose SRU?", "Rankings", "Leadership"])


def _international(message: str) -> QuickAnswer | None:
    facts = _section("12_strengths_faculty_and_visits_nov2026.md", "4. International partnerships")
    if not facts:
        return None
    text = ("For international students, SR University's website lists (sru.edu.in/international):\n\n• " +
            "\n• ".join(facts) + "\n\nThe 2027-28 fee card also has a special concession of **₹15,000 a year** for "
            "international students. The International Affairs office handles applications and visa questions; "
            f"the Admissions Office can connect you ({_phone()}, info@sru.edu.in).")
    return QuickAnswer(text, ["Study abroad pathways", "Special concessions", "Talk to a counsellor"])


def _lateral(message: str) -> QuickAnswer | None:
    if re.search(r"\b(?:concessions?|discounts?|apply|applied|fees?)\b", message or "", re.I):
        return None          # a concession or fee request: the fee flow answers (with the ₹15,000 concession)
    return QuickAnswer(
        "Yes. SR University has **B.Tech Lateral Entry**: **6 semesters (3 years)**, instead of 8 for the regular "
        "B.Tech (academic regulations). Lateral entry students pay the same tuition structure and get the same "
        "concessions as regular students, plus a special concession of **₹15,000 a year** (2027-28 fee card).\n\n"
        "The eligibility and admission process for lateral entry aren't printed in the official sources I use, so the "
        f"Admissions Office confirms them ({_phone()}, info@sru.edu.in).",
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
