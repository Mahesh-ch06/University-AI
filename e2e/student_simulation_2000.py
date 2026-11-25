"""SRU Buddy: 2,000 simulated students, end to end, with every reply checked (v4.15.0).

What is different from the 1,000-student run: each student has a JOURNEY with an outcome that can be checked
exactly, not only "was the reply on topic":

  fee          the full evaluation: programme -> board -> stage -> marks (in the marks card's format) -> group ->
               concessions -> hostel -> bus -> final fee card. The student answers whatever is asked (adaptive),
               typing (80%) or tapping the card / quick-reply buttons (20%).
  correction   the same, with 1-3 marks corrections at random points ("No, my marks are 671 out of 1000",
               "actually it's 82%", Telugu / Hindi-English too). After each: the reply confirms the NEW marks,
               the profile on the server holds them, and the final card's scholarship is the slab for the LATEST
               marks (official slab table, checked independently of the fee engine for B.Tech).
  invalid      impossible marks first ("1200 out of 1000", "abc"): not accepted, asked again, then real marks.
  side         a side question in the middle of the steps ("is the hostel food good?"): answered, and the step
               continues (the next answer is accepted, the programme is never asked again).
  greeting     "hi" in the middle of the steps: does not reset anything.
  switch       a change of programme in the middle ("actually I want ECE"): the final card is for the new one.
  callback     "call me back" / "talk to a counsellor" (the 30-second connect, wait shortened for the run): the
               confirmation names the student, never "Unknown"; asking again never makes a second request.
  noname       no name on file: asked for it, the request then completes with the name given.
  fresh_cb     "Start fresh", then a callback: the name is still known (the original "Unknown" bug).
  return       a journey stopped half-way, then the student comes back: on the SAME server (minutes later), or on a
               SECOND server with the short-term memory (Redis) removed (days later: only the database is left).
               Recovery context: right name, latest marks, where they stopped. Continue: the next answer is
               accepted at the step where they stopped. Fresh: a clean chat, the name kept, nothing old applied.
  enquiry      3-7 questions on any topic (programmes, fees, placements, hostel, food, clubs, events, sports,
               safety, apply, rankings, skeptical, off-topic, small talk), with follow-ups.

Every reply also gets the general checks of student_simulation.check_turn (no error, no filler, no repeat, every
rupee amount verified, length, advocacy). Turns answered by the AI model are counted separately: without a Gemini
key the review server's stand-in model answers them and they are NOT judged as correct or wrong.

Usage: python e2e/student_simulation_2000.py <outdir> [--users 2000] [--concurrency 16]
          [--api http://127.0.0.1:8080] [--api2 http://127.0.0.1:8081]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import student_simulation as base  # noqa: E402
import student_simulation_1000 as k1  # noqa: E402

NOT_ELIGIBLE = re.compile(r"can't show you a fee", re.IGNORECASE)   # v4.15.1: marks below the programme minimum
MODEL_TEXT = re.compile(r"Review model: no Gemini key", re.I)
ADMIN_KEY = "change-me-in-production"
PLACEHOLDER = re.compile(r"\b(?:unknown|undefined|null|none|student|user)\b", re.I)

# ------------------------------------------------------------------ official slabs (independent of the fee engine)
# B.Tech merit scholarship on tuition, from the official 2027-28 fee card.
STATE_SLABS = [(98, 40), (92, 30), (80, 25), (70, 20), (65, 15), (60, 10)]
CBSE_SLABS = [(95, 40), (90, 30), (80, 25), (70, 20), (65, 15), (60, 10)]


def slab(pct: float, board: str) -> int:
    for low, s in (CBSE_SLABS if board == "cbse" else STATE_SLABS):
        if pct >= low:
            return s
    return 0


# ------------------------------------------------------------------ amounts the fee engine computes
# "Your academic scholarship is 15%: − ₹60,000" is 15% of the official tuition: computed, not invented. These are
# accepted when they equal pct x tuition (or the tuition after it) for some programme and an official slab.
def _computed_amounts() -> set[int]:
    sys.path.insert(0, str(base.BACKEND))
    from app.sru_agent import fees
    out = set()
    for p in fees.load_data()["programs"].values():
        t = int(p.get("tuition_per_year") or 0)
        for pct in (10, 15, 20, 25, 30, 40, 50):
            out.update({t * pct // 100, t - t * pct // 100})
    return out


_COMPUTED = _computed_amounts()


def computed_ok(problem: str) -> bool:
    nums = [int(x.replace(",", "")) for x in re.findall(r"₹\s?([\d,]+)", problem)]
    return bool(nums) and all(n in _COMPUTED for n in nums)


REPEAT = ("same opening line", "same answer as for a different question")


# ------------------------------------------------------------------ students
FIRST = ["Mahesh", "Asha", "Ravi", "Sneha", "Arjun", "Divya", "Karthik", "Lakshmi", "Nikhil", "Ananya", "Vamshi",
         "Harika", "Zoya", "Rohit", "Pooja", "Srinivas", "Sai", "Keerthi", "Imran", "Priya", "Teja", "Bhavana",
         "Rahul", "Meghana", "Akhil", "Swathi", "Venkat", "Fatima", "Charan", "Deepika", "Manoj", "Sravani"]
LAST = ["Kumar", "Reddy", "Rao", "Goud", "Sharma", "Khan", "Naidu", "Patel", "Yadav", "Varma", "Chary", "Singh"]
PERSONAS = ["anxious_parent", "strong_student", "low_marks", "confused", "budget", "scholarship_focused",
            "comparing", "placement_focused", "campus_life", "mind_changer", "corrector", "unrelated_followups",
            "skeptical", "impatient", "rude", "incomplete_info", "returning_hours", "returning_days",
            "short_answers", "long_messages"]
STYLES = ["english", "tenglish", "hinglish", "short", "typos", "informal", "long"]
# persona -> journeys (weights)
JOURNEYS = {
    "anxious_parent": {"enquiry": 3, "fee": 2, "callback": 2, "side": 1},
    "strong_student": {"fee": 3, "correction": 1, "enquiry": 2},
    "low_marks": {"fee": 3, "invalid": 1, "enquiry": 1},
    "confused": {"enquiry": 2, "fee": 2, "greeting": 1, "noname": 1},
    "budget": {"fee": 3, "side": 1, "enquiry": 1},
    "scholarship_focused": {"fee": 2, "correction": 2},
    "comparing": {"enquiry": 3, "switch": 1},
    "placement_focused": {"enquiry": 3, "fee": 1},
    "campus_life": {"enquiry": 4, "side": 1},
    "mind_changer": {"switch": 3, "correction": 1, "fresh_cb": 1},
    "corrector": {"correction": 4, "invalid": 1},
    "unrelated_followups": {"side": 3, "enquiry": 2, "greeting": 1},
    "skeptical": {"enquiry": 3, "callback": 1},
    "impatient": {"fee": 2, "callback": 2, "enquiry": 1},
    "rude": {"enquiry": 2, "callback": 1, "invalid": 1},
    "incomplete_info": {"noname": 2, "fee": 2, "invalid": 1},
    "returning_hours": {"return": 4},
    "returning_days": {"return": 4},
    "short_answers": {"fee": 2, "greeting": 1, "enquiry": 1},
    "long_messages": {"fee": 2, "enquiry": 2, "correction": 1},
}
# Programmes for the evaluation: (what the student types, what a button sends, key, B.Tech slabs apply)
FEE_PROGS = [("cse", "B.Tech Computer Science & Engineering (CSE)", "btech_cse", True),
             ("btech cse", "B.Tech Computer Science & Engineering (CSE)", "btech_cse", True),
             ("ece", "B.Tech ECE (AIML, VLSI, Robotics)", "btech_ece", True),
             ("mechanical", "B.Tech Mechanical / Civil / EEE", "btech_mech", True),
             ("ai and robotics", "B.Tech in Artificial Intelligence & Robotics", "btech_ai_robotics", True),
             ("bba", "BBA", "bba", False), ("agriculture", "B.Sc Agriculture", "bsc_agri", False)]
BOARDS = [("telangana", "Telangana Intermediate (TSBIE)", "state", 1000),
          ("ts board", "Telangana Intermediate (TSBIE)", "state", 1000),
          ("ap", "Andhra Pradesh Intermediate (BIEAP)", "state", 1000),
          ("andhra pradesh board", "Andhra Pradesh Intermediate (BIEAP)", "state", 1000),
          ("cbse", "CBSE", "cbse", 100)]
START = {"english": ["Calculate my fee", "What will my fee be for {p}?", "I want to know my scholarship",
                     "how much fee for {p} after scholarship"],
         "tenglish": ["naa fee entha avtundi?", "{p} fee entha?", "scholarship vastunda naaku?"],
         "hinglish": ["mera fee kitna hoga?", "{p} ki fees kitni hai bhai", "scholarship milega kya?"],
         "short": ["fee?", "{p} fees", "scholarship?"],
         "typos": ["calcualte my fess", "{p} fess", "scholarshp for me"],
         "informal": ["yo how much do i pay for {p}", "fee for {p} bro", "tell me my fees pls"],
         "long": ["Hello, I have just finished my Intermediate exams and I am planning to join {p} at SR University. "
                  "Could you please tell me how much fee I would need to pay and whether I get any scholarship?"]}
CORRECTIONS = {"english": ["No, these are not my marks. My actual marks are {v}.", "sorry I made a mistake, it's {v}",
                           "wait, my marks are {v}", "correction: I got {v}", "not that, I scored {v}"],
               "tenglish": ["kaadu, naa marks {v}", "sorry, naa actual marks {v}"],
               "hinglish": ["nahi, mere marks {v} hai", "galti ho gayi, mere marks {v}"],
               "short": ["no {v}", "marks {v}"], "typos": ["no my marsk are {v}", "sory my marks {v}"],
               "informal": ["oops my bad, marks are {v}", "nah i got {v}"],
               "long": ["I'm really sorry, I gave you the wrong marks earlier. My correct marks are {v}, please use "
                        "these instead."]}
SIDE_QS = [("is the hostel food good?", ["food", "mess", "dining", "meal"]),
           ("how are placements?", ["placement", "LPA", "recruit", "package"]),
           ("is the campus safe for girls?", ["safe", "security", "CCTV", "warden"]),
           ("what clubs are there?", ["club"]),
           ("where is the campus?", ["Warangal", "Hasanparthy", "Ananthasagar", "Telangana"])]
GREETINGS = ["hi", "hello", "hey", "hii", "namaste"]


def marks_value(board_kind: str, pct: float, rnd: random.Random, style: str) -> tuple[str, float, bool]:
    """(what the student types, the percentage it means, typed as raw marks out of 1000)."""
    if board_kind == "state" and rnd.random() < 0.75:
        raw = int(round(pct * 10))
        form = rnd.choice(["{r}", "{r} out of 1000", "I got {r}", "{r}/1000", "{r} marks"])
        if style == "tenglish":
            form = rnd.choice(["naaku {r} vachayi", "{r} marks vachayi", "{r}"])
        elif style == "hinglish":
            form = rnd.choice(["mere {r} marks hai", "{r} aaye", "{r}"])
        return form.format(r=raw), round(raw / 10, 2), True
    p = int(round(pct))
    form = rnd.choice(["{p}%", "{p} percent", "I got {p}%", "{p} percentage"])
    if style == "tenglish":
        form = rnd.choice(["{p}% vachindi", "{p} percent"])
    elif style == "hinglish":
        form = rnd.choice(["{p}% aaya", "{p} percent"])
    return form.format(p=p), float(p), False


_PHONES = random.SystemRandom()   # new numbers on every run (leads from an earlier run must not count as duplicates)


def build(n: int, seed: int = 2027) -> list[dict]:
    rnd = random.Random(seed)
    chip_ids = set(rnd.sample(range(n), k=n // 5))   # 20% also tap the buttons, 80% only type
    students = []
    for i in range(n):
        persona = PERSONAS[i % len(PERSONAS)]
        style = STYLES[(i // len(PERSONAS)) % len(STYLES)] if persona not in ("short_answers", "long_messages") else \
            ("short" if persona == "short_answers" else "long")
        jw = JOURNEYS[persona]
        journey = rnd.choices(list(jw), weights=list(jw.values()))[0]
        if persona == "returning_days":
            journey = "return"
        prog = rnd.choice(FEE_PROGS)
        board = rnd.choice(BOARDS)
        if persona == "strong_student":
            pct = rnd.choice([92.5, 94.0, 96.3, 98.2, 99.0])
        elif persona == "low_marks":
            pct = rnd.choice([48.0, 55.5, 58.0, 61.2, 63.0])
        else:
            pct = rnd.choice([60.5, 65.0, 67.1, 71.0, 76.4, 80.0, 84.0, 87.0, 90.5, 93.0, 95.5, 98.5])
        first = FIRST[i % len(FIRST)]
        students.append({
            "id": f"{i + 1:04d}-{persona}-{journey}", "persona": persona, "style": style, "journey": journey,
            "taps": i in chip_ids, "name": f"{first} {LAST[(i // len(FIRST)) % len(LAST)]}", "first": first,
            "phone": f"9{_PHONES.randint(100000000, 999999999)}", "prog": prog, "board": board, "pct": pct,
            "return_mode": ("days" if persona == "returning_days" else rnd.choice(["hours", "days"])),
            "return_choice": rnd.choice(["continue", "continue", "fresh"]),
            "seed": rnd.randint(0, 10**9)})
    return students


# ------------------------------------------------------------------ what is the bot asking?
def asked(reply: dict) -> str | None:
    types = [c.get("type") for c in reply.get("cards") or []]
    text = reply.get("answer") or ""
    low = text.lower()
    if "counsellor_program_selection" in types or re.search(r"which (programme|program|course)\b.*\?", low):
        return "program"
    if re.search(r"which b\.?tech branch", low):
        return "branch"
    if "counsellor_board_selection" in types or re.search(r"which board", low):
        return "board"
    if "counsellor_stage_selection" in types or re.search(r"where are you in intermediate|still studying", low):
        return "stage"
    if "counsellor_marks_input" in types or re.search(r"what (?:are|were) your (?:final )?marks|what percentage did you", low):
        return "marks"
    if re.search(r"which group|subjects? did you (take|study)", low) or ("counsellor_choice" in types and "group" in low):
        return "group"
    if re.search(r"eapcet rank or a jee main percentile\?", low):
        return "entrance"
    if "get_special_concessions" in types or re.search(r"pick the category that applies|special considerations? available", low):
        return "concession"
    if re.search(r"do you have the supporting document", low):
        return "proof"
    if re.search(r"hostel or day scholar|stay in the university hostel|add the hostel fee|stay in the hostel\?", low):
        return "hostel"
    if re.search(r"use the university bus", low):
        return "bus"
    if re.search(r"would you also like to check whether your", low):
        return "scholarship_q"
    return None


def card(reply: dict, kind: str) -> dict | None:
    return next((c for c in reply.get("cards") or [] if c.get("type") == kind), None)


class Student:
    def __init__(self, st: dict, api: str, client: httpx.AsyncClient, outdir: Path):
        self.st, self.api, self.client, self.outdir = st, api, client, outdir
        self.rnd = random.Random(st["seed"])
        self.sid = "sim2k-" + uuid.uuid4().hex
        self.conv: str | None = None
        self.transcript: list[dict] = []
        self.checks: list[dict] = []       # journey-level outcomes: {"metric", "pass", "detail"}
        self.expected_pct: float | None = None
        self.steps_seen: dict[str, int] = {}

    # -------------------------------------------------------------- plumbing
    def metric(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"metric": name, "pass": bool(ok), "detail": detail[:300]})

    async def say(self, msg: str, exp: dict | None = None, topic: str = "", chip: bool = False,
                  api: str | None = None) -> dict:
        try:
            reply = await base.ask(self.client, api or self.api, self.sid, self.conv, msg)
        except Exception as exc:
            reply = {"error": f"{type(exc).__name__}: {str(exc)[:80]}", "answer": "", "ms": 0}
        self.conv = reply.get("conversation_id") or self.conv
        model = bool(MODEL_TEXT.search(reply.get("answer") or ""))
        cut = max([i for i, t in enumerate(self.transcript) if t["message"].startswith(("[Start fresh", "[Returns"))
                   and "fresh" in t["message"]] or [-1])
        earlier = [t for t in self.transcript[cut + 1:] if t.get("answer") and not t["message"].startswith("[")]
        if chip and (asked(reply) or reply.get("cards") or msg.startswith(("↩️", "📋"))
                     or re.search(r"\bcontinue\b", msg, re.I)):
            exp = {k: v for k, v in (exp or {}).items() if k != "any"}   # a tap that opens the next step is on topic
        problems = [] if model else base.check_turn(msg, exp or {}, reply, earlier)
        problems = [p for p in problems if not (p.startswith("unverified amount") and computed_ok(p))]
        if reply.get("error"):
            problems = [f"error: {reply['error']}"]
        self.transcript.append({"message": msg, "topic": topic, "chip": chip, "answer": reply.get("answer", ""),
                                "cards": [c.get("type") for c in reply.get("cards") or []],
                                "suggestions": reply.get("suggestions") or [], "ms": reply.get("ms"),
                                "needs_model": model, "problems": problems})
        if chip and not model:   # a tap answered by the AI model is counted with the model turns, not judged here
            self.metric("quick_replies", not [p for p in problems if not p.startswith(REPEAT)]
                        and bool((reply.get("answer") or "").strip()),
                        f"{msg} -> {(reply.get('answer') or '')[:120]}")
        return reply

    async def profile(self, api: str | None = None) -> dict:
        r = await self.client.get(f"{api or self.api}/api/v1/agent/profile", params={"session_id": self.sid})
        return (r.json() or {}).get("profile") or {}

    def styled(self, text: str) -> str:
        if self.st["style"] == "short":
            return text.lower().rstrip("?.!")
        if self.st["style"] == "informal":
            return text.lower() + self.rnd.choice(["", " pls", " bro"])
        if self.st["style"] == "typos":
            return text.replace("ee", "e").replace("ar", "ra", 1) if self.rnd.random() < 0.3 else text.lower()
        return text

    # -------------------------------------------------------------- answering the fee steps
    def answer_for(self, step: str, reply: dict) -> tuple[str, bool]:
        """(message, is_a_button) for the step being asked."""
        st, tap = self.st, self.st["taps"] and self.rnd.random() < 0.7
        typed_prog, btn_prog, key, _ = st["prog"]
        if step == "program":
            c = card(reply, "counsellor_program_selection")
            if tap and c:
                hit = next((p["name"] for p in c.get("programs") or [] if p.get("key") == key), None)
                if hit:
                    return hit, True
            return self.styled(typed_prog), False
        if step == "branch":
            return ("CSE" if "cse" in typed_prog else typed_prog), False
        if step == "board":
            typed, label, _, _ = st["board"]
            return (label, True) if tap else (self.styled(typed), False)
        if step == "stage":
            if tap:
                return "Completed Intermediate / Class 12 (passed out)", True
            return self.rnd.choice({"tenglish": ["completed", "inter aipoyindi"], "hinglish": ["completed", "pass ho gaya"]}
                                   .get(st["style"], ["completed", "passed out", "I have completed inter", "finished"])), False
        if step == "marks":
            c = card(reply, "counsellor_marks_input") or {}
            mx = c.get("max_marks")
            if tap and mx:   # the marks card's own format: "870 out of 1000" or "87%"
                if float(mx) > 100:
                    raw = int(round(st["pct"] * float(mx) / 100))
                    self.expected_pct = round(raw / float(mx) * 100, 2)
                    return f"{raw} out of {int(mx)}", True
                self.expected_pct = float(int(round(st["pct"])))
                return f"{int(round(st['pct']))}%", True
            board_kind = st["board"][2] if not (mx and float(mx) <= 100 and st["board"][2] == "state") else "pct"
            text, pct, _ = marks_value(board_kind if board_kind != "pct" else "cbse", st["pct"], self.rnd, st["style"])
            self.expected_pct = pct
            return text, False
        if step == "group":
            if key == "bsc_agri":   # Agriculture needs BiPC
                return self.rnd.choice(["BiPC", "bipc", "biology physics chemistry"]), False
            if tap:
                return "MPC (Maths, Physics, Chemistry)", True
            return self.rnd.choice(["MPC", "mpc", "maths physics chemistry"]), False
        if step == "entrance":
            return ("No entrance exam", True) if tap else (self.rnd.choice(["no", "no entrance exam", "didn't write"]), False)
        if step == "concession":
            return ("None of these apply", True) if tap else (self.rnd.choice(["none of these apply", "none", "no"]), False)
        if step == "proof":
            return "Yes, I have it", True
        if step == "hostel":
            if tap:
                chips = reply.get("suggestions") or []
                pick = self.rnd.choice(chips) if chips else "No hostel, I'm a day scholar"
                return pick, True
            return self.rnd.choice(["no hostel, day scholar", "AC 4-sharing", "non ac 3 sharing", "day scholar"]), False
        if step == "bus":
            return ("No, I'll manage", True) if tap else (self.rnd.choice(["no", "yes", "no bus"]), False)
        if step == "scholarship_q":
            return "Yes, check my scholarship", True
        return "ok", False

    async def run_steps(self, reply: dict, max_turns: int = 14, hooks: dict | None = None) -> dict:
        """Answer whatever is asked until the final fee card (or the turn budget). hooks: step -> async fn(reply)
        called once, the first time that step is asked (side question, greeting, correction, switch...)."""
        hooks = dict(hooks or {})
        for _ in range(max_turns):
            if card(reply, "fee_summary") or NOT_ELIGIBLE.search(reply.get("answer") or ""):
                return reply        # the fee, or (v4.15.1) the honest "you can't join this programme" answer
            step = asked(reply)
            if step is None:
                if MODEL_TEXT.search(reply.get("answer") or ""):
                    self.metric("fee_flow_understood", False, f"step answer went to the model: "
                                f"{self.transcript[-1]['message']!r}")
                    return reply
                # a reply without a question (e.g. scholarship result with chips): ask for the final fee
                reply = await self.say("Show my final fee", {}, "fee_step", chip=True)
                continue
            self.steps_seen[step] = self.steps_seen.get(step, 0) + 1
            if self.steps_seen[step] >= 3:
                self.metric("no_repeated_step", False, f"'{step}' asked {self.steps_seen[step]} times")
                return reply
            hook = hooks.pop(step, None) or hooks.pop("*", None) if (step in hooks or "*" in hooks) else None
            if hook:
                reply = await hook(reply, step)
                if reply is None:
                    return {}
                continue
            msg, tap = self.answer_for(step, reply)
            reply = await self.say(msg, {}, f"fee:{step}", chip=tap)
        return reply

    async def check_final(self, reply: dict, prog_key: str, btech: bool, label: str = "fee") -> None:
        fs = card(reply, "fee_summary")
        # v4.15.1: marks below the programme's minimum must end in an honest "not eligible" answer and NO fee
        refused = bool(NOT_ELIGIBLE.search(reply.get("answer") or ""))
        below = self.expected_pct is not None and self.expected_pct < 50
        self.metric("fee_workflow_completion", (bool(fs) and not below) or (refused and below and not fs),
                    f"{label}: last reply {(reply.get('answer') or '')[:160]!r}")
        if refused:
            return
        prof = await self.profile()
        if self.expected_pct is not None:
            got = prof.get("percent")
            self.metric("marks_consistency", got is not None and abs(float(got) - self.expected_pct) < 0.06,
                        f"profile percent {got} vs latest given {self.expected_pct}")
        if fs and self.expected_pct is not None:
            data = fs.get("data") or fs
            sch = data.get("scholarship") or {}
            text = json.dumps(sch) + " " + (reply.get("answer") or "")
            m = re.search(r"(\d{1,2})%\s*(?:merit\s+)?scholarship|scholarship\s*\((\d{1,2})%\)", text, re.I)
            shown = int(m.group(1) or m.group(2)) if m else 0
            board = "cbse" if self.st["board"][2] == "cbse" else "state"
            if btech:
                want = slab(self.expected_pct, board)
            else:
                sys.path.insert(0, str(base.BACKEND))
                from app.sru_agent import fees
                want = int(fees.calculate_fee(prog_key, percent=self.expected_pct,
                                              board="cbse" if board == "cbse" else "state_board")
                           .get("scholarship_percent") or 0)
            self.metric("eligibility_correctness", shown == want,
                        f"{prog_key} {self.expected_pct}% ({board}): shown {shown}%, official slab {want}%")

    # -------------------------------------------------------------- journeys
    async def start_fee(self) -> dict:
        typed_prog = self.st["prog"][0]
        opener = self.rnd.choice(START[self.st["style"]]).format(p=typed_prog)
        return await self.say(opener, {}, "fee:start")

    async def j_fee(self) -> None:
        reply = await self.start_fee()
        reply = await self.run_steps(reply)
        await self.check_final(reply, self.st["prog"][2], self.st["prog"][3])

    async def j_correction(self) -> None:
        n = self.rnd.choice([1, 1, 2, 3])
        board_kind = self.st["board"][2]
        points = self.rnd.sample(["group", "concession", "hostel", "bus", "final"], k=min(n, 3))

        async def correct(reply, step):
            new = round(min(99.0, max(50.0, self.st["pct"] + self.rnd.choice([-22, -15, -8, 6, 9]))), 1)
            if board_kind == "state" and self.rnd.random() < 0.7:
                raw = int(round(new * 10))
                v, pct = self.rnd.choice([f"{raw} out of 1000", f"{raw}/1000", f"{raw} marks"]), round(raw / 10, 2)
            else:
                v, pct = f"{int(round(new))}%", float(int(round(new)))
            msg = self.rnd.choice(CORRECTIONS[self.st["style"]]).format(v=v)
            r = await self.say(msg, {}, "correction")
            self.expected_pct = pct
            ans = r.get("answer") or ""
            # acknowledged: "Updated: I'm now using your marks ..." or the reply itself is built on the new value
            first_num = re.search(r"\d+(?:\.\d+)?", v).group(0)
            num_ok = bool(re.search(rf"(?<![\d.]){re.escape(first_num)}(?![\d])", ans))
            self.metric("marks_correction_acknowledged", num_ok and not MODEL_TEXT.search(ans),
                        f"{msg!r} -> {ans[:160]!r}")
            prof = await self.profile()
            got = prof.get("percent")
            self.metric("marks_consistency", got is not None and abs(float(got) - pct) < 0.06,
                        f"after correction: profile {got} vs {pct}")
            return r

        hooks = {p: correct for p in points if p != "final"}
        reply = await self.start_fee()
        reply = await self.run_steps(reply, hooks=hooks)
        if "final" in points and card(reply, "fee_summary"):
            reply = await correct(reply, "final")
            self.metric("fee_recalculated_after_correction", bool(card(reply, "fee_summary")),
                        (reply.get("answer") or "")[:160])
        await self.check_final(reply, self.st["prog"][2], self.st["prog"][3], "after corrections")

    async def j_invalid(self) -> None:
        async def bad(reply, step):
            c = card(reply, "counsellor_marks_input") or {}
            mx = float(c.get("max_marks") or 1000)
            wrong = self.rnd.choice([f"{int(mx) + 200} out of {int(mx)}" if mx > 100 else "150%", "abc", "-5",
                                     "I don't know"])
            r = await self.say(wrong, {}, "invalid_marks")
            prof = await self.profile()
            p = prof.get("percent")
            self.metric("invalid_marks_rejected", (p is None or 0 < float(p) <= 100) and asked(r) == "marks",
                        f"{wrong!r} -> profile {p}, next asks {asked(r)}: {(r.get('answer') or '')[:120]!r}")
            return r
        reply = await self.start_fee()
        reply = await self.run_steps(reply, hooks={"marks": bad})
        await self.check_final(reply, self.st["prog"][2], self.st["prog"][3])

    async def j_side(self) -> None:
        q, words = self.rnd.choice(SIDE_QS)

        async def side(reply, step):
            r = await self.say(q, {"any": words}, "side_question")
            if not MODEL_TEXT.search(r.get("answer") or ""):
                self.metric("relevance", not [p for p in self.transcript[-1]["problems"] if not p.startswith(REPEAT)],
                            f"side {q!r}: {self.transcript[-1]['problems']}")
            back = asked(r) or asked(reply)
            self.metric("continuity", back == step or (r.get("suggestions") and any("continue" in s.lower() for s in
                                                                                    r["suggestions"])) or back is not None,
                        f"after side question at '{step}': next asks {asked(r)}")
            # answer the step that was open (the student goes back to it)
            msg, tap = self.answer_for(step, reply)
            return await self.say(msg, {}, f"fee:{step}", chip=tap)
        point = self.rnd.choice(["board", "stage", "marks", "concession", "hostel"])
        reply = await self.start_fee()
        reply = await self.run_steps(reply, hooks={point: side})
        await self.check_final(reply, self.st["prog"][2], self.st["prog"][3], "with a side question")

    async def j_greeting(self) -> None:
        async def greet(reply, step):
            r = await self.say(self.rnd.choice(GREETINGS), {"short": True}, "greeting_mid_chat")
            self.metric("continuity", "welcome to sr university" not in (r.get("answer") or "").lower()
                        and asked(r) in (step, None), f"greeting at '{step}' -> {(r.get('answer') or '')[:140]!r}")
            msg, tap = self.answer_for(step, reply)
            return await self.say(msg, {}, f"fee:{step}", chip=tap)
        point = self.rnd.choice(["board", "stage", "marks", "group"])
        reply = await self.start_fee()
        reply = await self.run_steps(reply, hooks={point: greet})
        await self.check_final(reply, self.st["prog"][2], self.st["prog"][3], "with a greeting")

    async def j_switch(self) -> None:
        new = self.rnd.choice([p for p in FEE_PROGS if p[2] != self.st["prog"][2] and p[2].startswith("btech")])

        done = []

        async def switch(reply, step):
            if done:      # switched already at an earlier step: answer this one normally
                msg, tap = self.answer_for(step, reply)
                return await self.say(msg, {}, f"fee:{step}", chip=tap)
            done.append(step)
            msg = self.rnd.choice(["actually I want {p}", "change to {p}", "no wait, {p} instead",
                                   "I changed my mind, {p}"]).format(p=new[0])
            self.st = {**self.st, "prog": new}
            return await self.say(msg, {}, "programme_change")
        point = self.rnd.choice(["stage", "marks", "concession"])
        reply = await self.start_fee()
        reply = await self.run_steps(reply, hooks={p: switch for p in dict.fromkeys([point, "marks", "concession",
                                                                                      "hostel", "bus"])})
        if not done:   # every step was skipped (all details known): switch after the final card
            reply = await switch(reply, "final")
            reply = await self.run_steps(reply)
        fs = card(reply, "fee_summary")
        prog_shown = json.dumps(fs or {})
        names = {"btech_cse": "CSE", "btech_ece": "ECE", "btech_mech": "Mech", "btech_ai_robotics": "Robotics"}
        self.metric("programme_change_applied", bool(fs) and names.get(new[2], "") in prog_shown,
                    f"switched to {new[2]}; final card mentions it: {names.get(new[2], '') in prog_shown}")
        await self.check_final(reply, new[2], new[3], "after programme change")

    async def poll_connect(self, reply: dict) -> None:
        c = card(reply, "counsellor_connect") or next((x for x in reply.get("cards") or [] if "request_id" in json.dumps(x)), None)
        text = reply.get("answer") or ""
        if not c:
            ok = self.st["first"] in text and not PLACEHOLDER.search(text.replace("Student", ""))
            self.metric("callback_identity", ok, text[:200])
            return
        rid = c.get("request_id") or (c.get("data") or {}).get("request_id")
        status = {}
        for _ in range(40):
            r = await self.client.get(f"{self.api}/api/v1/agent/connect/{rid}", params={"session_id": self.sid})
            status = r.json() if r.status_code == 200 else {}
            if status.get("status") not in (None, "waiting"):
                break
            await asyncio.sleep(1)
        fn = str(status.get("first_name") or "")
        self.metric("callback_identity", fn == self.st["first"], f"connect status {status.get('status')} first_name={fn!r}")

    async def j_callback(self) -> None:
        if self.rnd.random() < 0.5:
            await self.say(self.rnd.choice(["hi", "what is the fee for cse?", "how are placements?"]), {}, "warmup")
        msg = self.rnd.choice(["I want to talk to a counsellor", "please call me back", "call me", "can I speak to a person",
                               "counsellor tho matladali", "mujhe counsellor se baat karni hai", "callback please"])
        r = await self.say(msg, {}, "callback")
        await self.poll_connect(r)
        r2 = await self.say(self.rnd.choice(["call me back please", "I want a callback"]), {}, "callback_again")
        t2 = r2.get("answer") or ""
        self.metric("callback_identity", self.st["first"] in t2 and "Unknown" not in t2, f"again: {t2[:160]!r}")
        await self.check_one_lead()

    async def check_one_lead(self) -> None:
        r = await self.client.get(f"{self.api}/api/v1/admin/leads", params={"search": self.st["phone"]},
                                  headers={"X-Admin-Key": ADMIN_KEY})
        items = (r.json() or {}).get("items") or (r.json() or {}).get("leads") or []
        mine = [x for x in items if str(x.get("phone") or "").endswith(self.st["phone"][-10:])]
        names = {str(x.get("name") or x.get("student_name") or "") for x in mine}
        self.metric("no_duplicate_callbacks", len(mine) <= 1, f"{len(mine)} leads for this number")
        self.metric("callback_identity", bool(mine) and all(n and not PLACEHOLDER.fullmatch(n.strip()) for n in names),
                    f"lead names {names}")

    async def j_noname(self) -> None:
        r = await self.say(self.rnd.choice(["call me back please", "I want a callback", "please call me"]), {}, "callback")
        t = r.get("answer") or ""
        self.metric("asks_missing_name", "name" in t.lower() and "Unknown" not in t, t[:160])
        r = await self.say(self.st["name"], {}, "gives_name")
        t = r.get("answer") or ""
        self.metric("callback_identity", self.st["first"] in t and "Unknown" not in t and not MODEL_TEXT.search(t),
                    f"after giving the name: {t[:160]!r}")
        await self.check_one_lead()

    async def j_fresh_cb(self) -> None:
        await self.say(self.rnd.choice(["hi", "what is the fee for cse?"]), {}, "warmup")
        rr = await self.client.post(f"{self.api}/api/v1/agent/reset-session",
                                    json={"session_id": self.sid, "conversation_id": self.conv})
        self.conv = (rr.json() or {}).get("new_conversation_id")
        await self.client.put(f"{self.api}/api/v1/agent/profile", json={"session_id": self.sid, "fresh_start": True})
        self.transcript.append({"message": "[Start fresh]", "answer": "", "problems": [], "needs_model": False,
                                "topic": "fresh", "chip": True, "cards": [], "suggestions": [], "ms": 0})
        r = await self.say(self.rnd.choice(["I want to talk to a counsellor", "please call me back"]), {}, "callback")
        await self.poll_connect(r)
        await self.check_one_lead()

    async def j_return(self) -> None:
        # a journey stopped half-way
        stop_at = self.rnd.choice(["stage", "marks", "group", "concession"])

        left = []

        async def leave(reply, step):
            left.append(step)
            return None
        reply = await self.start_fee()
        done_reply = await self.run_steps(reply, hooks={stop_at: leave})
        if not left:   # the journey finished before that step was asked: returning, they ask for the fee again
            self.st = {**self.st, "return_choice": "continue_final"}
        old_conv = self.conv
        prof_before = await self.profile()
        api = self.api
        if self.st["return_mode"] == "days" and self.api2:
            api = self.api2
            await asyncio.sleep(1.0)
            # days later: the short-term memory has expired; only the database is left
            await redis_del(f"sru:state:{self.sid}:*", f"sru:history:{self.sid}:*")
        ctx = (await self.client.get(f"{api}/api/v1/agent/recovery-context", params={"session_id": self.sid})).json()
        self.metric("memory_restoration", ctx.get("has_resumable_conversation") and ctx.get("conversation_id") == old_conv,
                    f"{self.st['return_mode']}: resumable={ctx.get('has_resumable_conversation')} same conv="
                    f"{ctx.get('conversation_id') == old_conv}")
        nm = str(ctx.get("student_name") or "")
        self.metric("callback_identity", nm.split()[0:1] == [self.st["first"]] if nm else False,
                    f"recovery context name {nm!r}")
        if prof_before.get("percent") is not None:
            self.metric("marks_consistency", str(ctx.get("score_text") or "").find(str(prof_before["percent"]).rstrip("0").rstrip(".")) >= 0
                        or f"{float(prof_before['percent']):.1f}" in str(ctx.get("score_text") or ""),
                        f"recovery score {ctx.get('score_text')!r} vs profile {prof_before.get('percent')}")
        self.transcript.append({"message": f"[Returns after {self.st['return_mode']}: {self.st['return_choice']}]",
                                "answer": "", "problems": [], "needs_model": False, "topic": "return", "chip": True,
                                "cards": [], "suggestions": [], "ms": 0})
        if self.st["return_choice"] == "continue_final":
            self.api = api
            r = await self.say(self.rnd.choice(["Show my final fee", "what was my final fee?", "show my fee summary"]),
                               {}, "return:final")
            self.metric("continuity", bool(card(r, "fee_summary")), f"final fee after returning: {(r.get('answer') or '')[:140]!r}")
            await self.check_final(r, self.st["prog"][2], self.st["prog"][3], "after returning")
        elif self.st["return_choice"] == "continue":
            # the student says hi first (the UI then offers continue / fresh; they continue) and answers the step
            self.api = api
            step_reply = {"answer": self.transcript[-2]["answer"] if len(self.transcript) > 1 else "",
                          "cards": [{"type": t} for t in self.transcript[-2]["cards"]] if len(self.transcript) > 1 else []}
            step = asked(step_reply) or stop_at
            msg, tap = self.answer_for(step, step_reply)
            r = await self.say(msg, {}, f"return:{step}", chip=tap)
            nxt = asked(r)
            self.metric("continuity", not MODEL_TEXT.search(r.get("answer") or "") and nxt != "program"
                        and (nxt != step or step == "concession") and not re.search(r"which programme", r.get("answer") or "", re.I),
                        f"continued at '{step}' with {msg!r} -> asks {nxt}: {(r.get('answer') or '')[:140]!r}")
            r = await self.run_steps(r)
            await self.check_final(r, self.st["prog"][2], self.st["prog"][3], "after returning")
        else:
            rr = await self.client.post(f"{api}/api/v1/agent/reset-session",
                                        json={"session_id": self.sid, "conversation_id": old_conv})
            self.conv = (rr.json() or {}).get("new_conversation_id")
            await self.client.put(f"{api}/api/v1/agent/profile", json={"session_id": self.sid, "fresh_start": True})
            self.api = api
            r = await self.say(self.rnd.choice(["hi", "hello"]), {}, "fresh_hi")
            t = r.get("answer") or ""
            self.metric("memory_restoration", self.st["first"] in t and "Unknown" not in t and not asked(r),
                        f"fresh start greeting: {t[:140]!r}")
            r = await self.say("Calculate my fee", {}, "fresh_fee")
            self.metric("continuity", asked(r) == "program", f"fresh chat asks the programme again: {asked(r)}")
            prof = await self.profile()
            self.metric("callback_identity", (prof.get("name") or "").split()[:1] == [self.st["first"]],
                        f"name kept after fresh start: {prof.get('name')!r}")

    async def j_enquiry(self) -> None:
        weights, style = k1.MINDSETS[self.rnd.choice(list(k1.MINDSETS))]
        prog = self.rnd.choice(k1.PROGS)
        last = None
        for t in range(self.rnd.randint(3, 7)):
            topics = [k for k in weights if not (k in k1.FOLLOW_UPS and last not in ("programme", "fees", "eligibility"))]
            topic = self.rnd.choices(topics, weights=[weights[k] for k in topics])[0]
            wordings, exp = k1.TOPICS[topic]
            msg = self.rnd.choice(wordings).format(p=prog, s=k1.SHORT[prog], pct=self.rnd.choice([61, 74, 88, 94]))
            exp = dict(exp)
            if topic == "programme":
                exp["any"] = [k1.SHORT[prog].split()[0], prog.split()[-1]]
            if self.st["style"] in ("tenglish", "hinglish", "short") and topic not in ("skeptic", "off_topic", "unpublished"):
                msg = k1.styled(msg, {"tenglish": "tenglish", "hinglish": "hinglish", "short": "short"}[self.st["style"]],
                                self.rnd)
                exp.pop("any", None) if topic == "unpublished" else None
            r = await self.say(msg, exp, topic)
            if not self.transcript[-1]["needs_model"]:
                self.metric("relevance", not [p for p in self.transcript[-1]["problems"] if not p.startswith(REPEAT)],
                            f"{topic} {msg!r}: {self.transcript[-1]['problems']}")
            if self.st["taps"] and r.get("suggestions") and self.rnd.random() < 0.5:
                chip = self.rnd.choice(r["suggestions"])
                rr = await self.say(chip, k1.chip_expectation(chip), "chip", chip=True)
                if card(rr, "counsellor_program_selection") or asked(rr):
                    rr = await self.run_steps(rr, max_turns=10)
            last = topic

    async def run(self, gate: asyncio.Semaphore) -> dict:
        async with gate:
            body = {"session_id": self.sid, "phone": self.st["phone"]}
            if self.st["journey"] != "noname":
                body["name"] = self.st["name"]
            await self.client.put(f"{self.api}/api/v1/agent/profile", json=body)
            try:
                await getattr(self, f"j_{self.st['journey']}")()
                if self.st["journey"] not in ("enquiry",) and self.rnd.random() < 0.35:
                    self.st = {**self.st}
                    await self.say(self.rnd.choice(["thanks", "ok thank you", "bye"]), {"short": True}, "small_talk")
            except Exception as exc:  # a crash of the journey is a finding
                self.metric("journey_ran", False, f"{type(exc).__name__}: {exc}")
            turns = self.transcript
            for t in turns:
                if t["message"].startswith("["):
                    continue
                if not t["needs_model"]:
                    self.metric("intent_accuracy", not any(p.startswith(("topic not covered", "missing card",
                                                                         "asked again")) for p in t["problems"]),
                                t["message"])
                    self.metric("ui_failures", not any(p.startswith(("error", "empty reply")) for p in t["problems"]),
                                t["message"])
                    self.metric("factual_correctness", not any(p.startswith("unverified amount") for p in t["problems"]),
                                t["message"])
                    self.metric("no_repeated_answer", not any(p.startswith(REPEAT) for p in t["problems"]), t["message"])
            result = {k: self.st[k] for k in ("id", "persona", "style", "journey", "taps", "name")}
            result.update(transcript=turns, checks=self.checks,
                          problems=sum(len(t["problems"]) for t in turns) + sum(not c["pass"] for c in self.checks))
            (self.outdir / "transcripts").mkdir(parents=True, exist_ok=True)
            (self.outdir / "transcripts" / f"{self.st['id']}.json").write_text(json.dumps(result, ensure_ascii=False,
                                                                                         indent=1))
            return result


_redis = None


async def redis_del(*patterns: str) -> None:
    import redis.asyncio as aioredis
    global _redis
    _redis = _redis or aioredis.from_url("redis://127.0.0.1:6379/0")
    for pat in patterns:
        async for k in _redis.scan_iter(match=pat):
            await _redis.delete(k)


METRICS = ["intent_accuracy", "relevance", "factual_correctness", "continuity", "memory_restoration",
           "marks_consistency", "eligibility_correctness", "callback_identity", "fee_workflow_completion",
           "quick_replies", "ui_failures"]
EXTRA = ["no_repeated_answer", "marks_correction_acknowledged", "invalid_marks_rejected", "no_duplicate_callbacks", "asks_missing_name",
         "programme_change_applied", "fee_recalculated_after_correction", "no_repeated_step", "fee_flow_understood",
         "journey_ran"]


def report(results: list[dict], outdir: Path, elapsed: float, round_label: str) -> str:
    turns = [t for r in results for t in r["transcript"] if not t["message"].startswith("[")]
    model = [t for t in turns if t["needs_model"]]
    checked = [t for t in turns if not t["needs_model"]]
    clean = [t for t in checked if not t["problems"]]
    agg: dict[str, list[int]] = {}
    fails: dict[str, list] = {}
    for r in results:
        for c in r["checks"]:
            a = agg.setdefault(c["metric"], [0, 0])
            a[0] += 1
            a[1] += c["pass"]
            if not c["pass"]:
                fails.setdefault(c["metric"], []).append((r["id"], c["detail"]))
    ok_students = [r for r in results if not any(not c["pass"] for c in r["checks"])
                   and not any(t["problems"] for t in r["transcript"])]
    times = sorted(t["ms"] or 0 for t in turns)
    q = lambda p: times[min(len(times) - 1, int(len(times) * p))] if times else 0  # noqa: E731
    by = lambda key: {v: sum(1 for r in results if r[key] == v) for v in sorted({r[key] for r in results})}  # noqa: E731
    lines = [f"# 2,000-student simulation: {round_label}", "",
             f"- Students: {len(results)} · typing only: {sum(not r['taps'] for r in results)} · also buttons: "
             f"{sum(r['taps'] for r in results)}",
             f"- Personas: {len(by('persona'))} · styles: {by('style')}",
             f"- Journeys: {by('journey')}",
             f"- Replies: {len(turns)} · answered by the code and checked: {len(checked)} · by the AI model "
             f"(stand-in, not judged): {len(model)} ({100 * len(model) / max(1, len(turns)):.1f}%)",
             f"- Checked replies with no problem: {len(clean)}/{len(checked)} ({100 * len(clean) / max(1, len(checked)):.1f}%)",
             f"- Students with every check passed: {len(ok_students)}/{len(results)} "
             f"({100 * len(ok_students) / max(1, len(results)):.1f}%)",
             f"- Reply time: median {q(0.5)} ms · 90th percentile {q(0.9)} ms · run {elapsed:.0f} s", "",
             "## Metrics", "", "| Metric | Checks | Passed | Rate |", "|---|---|---|---|"]
    for m in METRICS + EXTRA:
        if m in agg:
            a = agg[m]
            lines.append(f"| {m} | {a[0]} | {a[1]} | {100 * a[1] / max(1, a[0]):.1f}% |")
    lines.append(f"| overall_success (students) | {len(results)} | {len(ok_students)} | "
                 f"{100 * len(ok_students) / max(1, len(results)):.1f}% |")
    counts: dict[str, int] = {}
    ex: dict[str, list] = {}
    for r in results:
        for t in r["transcript"]:
            for p in t["problems"]:
                key = re.sub(r"\(.*", "", p).strip()
                counts[key] = counts.get(key, 0) + 1
                ex.setdefault(key, []).append((r["id"], t["message"], t["answer"][:200].replace("\n", " ")))
    lines += ["", "## Reply problems", ""]
    lines += (["| Problem | Replies |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
              if counts else ["None."])
    lines += ["", "## Failed checks (up to 6 examples each)", ""]
    for m, items in sorted(fails.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"### {m} ({len(items)})")
        lines += [f"- {sid}: {d}" for sid, d in items[:6]]
        lines.append("")
    if counts:
        lines += ["## Reply problem examples", ""]
        for k, items in sorted(ex.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {k}")
            lines += [f"- {sid} · \"{m}\" → {a}" for sid, m, a in items[:4]]
            lines.append("")
    text = "\n".join(lines)
    (outdir / "report.md").write_text(text)
    (outdir / "results.json").write_text(json.dumps({"metrics": agg, "students": len(results), "ok": len(ok_students),
                                                     "turns": len(turns), "checked": len(checked), "model": len(model),
                                                     "clean": len(clean)}, indent=1))
    return text


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--users", type=int, default=2000)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--api", default="http://127.0.0.1:8080")
    ap.add_argument("--api2", default="http://127.0.0.1:8081")
    ap.add_argument("--seed", type=int, default=2027)
    ap.add_argument("--label", default="round")
    ap.add_argument("--only", default="", help="comma-separated journeys to run (debugging)")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    students = build(args.users, args.seed)
    if args.only:
        students = [s for s in students if s["journey"] in args.only.split(",")]
    gate = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(trust_env=False, timeout=120) as client:
        # the 30-second connect, shortened to the minimum for the run (always in office hours); restored after
        settings = (await client.get(f"{args.api}/api/v1/admin/settings", headers={"X-Admin-Key": ADMIN_KEY})).json()
        keep = {k: settings.get(k) for k in ("office_days", "office_hours_start", "office_hours_end",
                                              "connect_wait_seconds", "connect_enabled") if k in settings}
        await client.put(f"{args.api}/api/v1/admin/settings", headers={"X-Admin-Key": ADMIN_KEY},
                         json={"office_days": [0, 1, 2, 3, 4, 5, 6], "office_hours_start": "00:00",
                               "office_hours_end": "23:59", "connect_wait_seconds": 10, "connect_enabled": True})
        t0 = time.monotonic()
        try:
            runners = []
            for s in students:
                st = Student(s, args.api, client, outdir)
                st.api2 = args.api2
                runners.append(st.run(gate))
            results = await asyncio.gather(*runners)
        finally:
            if keep:
                await client.put(f"{args.api}/api/v1/admin/settings", headers={"X-Admin-Key": ADMIN_KEY}, json=keep)
    print(report(list(results), outdir, time.monotonic() - t0, args.label)[:6000])


if __name__ == "__main__":
    asyncio.run(main())
