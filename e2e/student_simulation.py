"""SRU Buddy: many students chatting the way real students do, with every reply checked (v4.13.0).

Runs against the real API (e2e/review_server.py on :8080; REVIEW_MODEL=live for the real Gemini model):
the widget's lead form first (name + mobile), then each student's own conversation, several at a time.

Students: short texters, typos, parents, Telugu / Hindi mixed with English, repeated greetings, follow-ups with
"it / that / there", topic switches and returns, the admission and scholarship journeys, concessions, callbacks,
skeptics, off-topic asks, facts that aren't published, multi-questions, Start Afresh, odd inputs.

Checks on every reply: no error, not empty, no filler ending ("How can I assist you today?"), not welcomed
again mid-chat, no repeated self-introduction, no repeated opening line, no identical answer to a different
question, every rupee amount verified (official fee data or this turn's cards), not over-long, the disclaimer
not inside the answer, plus each turn's own expectations (topic covered, known details not asked again, the
right card, positive advocacy, scope).

Usage: python e2e/student_simulation.py <outdir> [--users 60] [--concurrency 4] [--api http://127.0.0.1:8080]
Writes <outdir>/report.md, <outdir>/results.json and every transcript.
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
from difflib import SequenceMatcher
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
from app.sru_agent import answer_check  # noqa: E402  (verified amounts: official fee data + this turn's sources)

FILLER_END = re.compile(r"(how (can|may) i (assist|help) you( today)?|feel free to ask|let me know if you have any "
                        r"(other|more) questions|anything else i can help)[\s.!?]*$", re.I)
WELCOME = re.compile(r"^\W*(hi|hello|hey|welcome)\b[^.!?\n]{0,60}\b(welcome to|sr university|sru)\b", re.I)
SELF_INTRO = re.compile(r"\bI(?:'m| am) SRU Buddy\b", re.I)
ERRORS = re.compile(r"couldn't reach|something went wrong|try again later|service is unavailable|Review model", re.I)
ASKS_PROGRAMME = re.compile(r"\bwhich (programme|program|course|branch|degree)\b[^?]*\?", re.I)
DISCLAIMER = "May contain inaccuracies"
FOUR_YEAR_CHIP = re.compile(r"4[- ]?year|four[- ]year|full course|total course", re.I)

# ------------------------------------------------------------------ the students
# Each turn: (message, expectations). Expectations: any=[...] one of these words in the reply (case-insensitive),
# none=[...] none of these, known_programme=True (must not ask which programme), card="type" (a card of that
# type), no_no=True (must not open with a blunt "No"), short=True (at most 80 words), redirect=True (off-topic:
# brought back to SRU admissions).
BASE = [
    ("greeter", [("hi", {}), ("hi again", {"short": True}), ("hello", {"short": True}), ("hey", {"short": True}),
                 ("good morning", {"short": True})]),
    ("short_texter", [("hi", {}), ("fees?", {"any": ["programme", "course", "which", "fee"]}),
                      ("cse", {"any": ["CSE", "Computer"]}), ("hostel?", {"any": ["hostel"]}),
                      ("ok thanks", {"short": True})]),
    ("typos", [("fess for cse", {"any": ["CSE", "fee", "₹"]}), ("scholership for 90 percent",
                                                                  {"any": ["scholarship", "%"]}),
               ("placment record", {"any": ["placement", "LPA", "recruit"]})]),
    ("parent", [("Good morning. My son has completed Intermediate MPC. We are looking at B.Tech CSE at your university.",
                 {"any": ["CSE", "B.Tech"]}),
                ("Is the campus safe for students staying in the hostel?", {"any": ["safe", "security", "CCTV", "warden"]}),
                ("What is the total fee for the first year?", {"known_programme": True, "any": ["₹", "fee"]}),
                ("Thank you for the information.", {"short": True})]),
    ("tenglish", [("cse fees entha?", {"any": ["CSE", "₹", "fee"]}), ("hostel undha?", {"any": ["hostel"]}),
                  ("placements ela unnai?", {"any": ["placement", "LPA", "recruit"]})]),
    ("hinglish", [("placement kaisa hai SRU me?", {"any": ["placement", "LPA", "recruit"]}),
                  ("hostel fees kitni hai?", {"any": ["hostel", "₹"]}), ("thik hai, dhanyavad", {"short": True})]),
    ("follow_up_pronouns", [("Tell me about B.Tech CSE", {"any": ["CSE", "Computer"]}),
                            ("what about its fees?", {"known_programme": True, "any": ["₹", "fee"]}),
                            ("and the eligibility for it?", {"known_programme": True,
                                                             "any": ["eligib", "Intermediate", "MPC", "%"]}),
                            ("how are placements there?", {"any": ["placement", "LPA", "recruit"]})]),
    ("topic_switch_return", [("hostel facilities", {"any": ["hostel"]}), ("placements?", {"any": ["placement", "LPA"]}),
                             ("going back to the hostel, is it safe for girls?", {"any": ["safe", "security", "girls",
                                                                                          "warden", "CCTV"]})]),
    ("admission_journey", [("I want to join SR University", {"any": ["course", "programme", "program"]}),
                           ("B.Tech", {"any": ["branch", "specialisation", "specialization", "CSE", "B.Tech"]}),
                           ("CSE", {"any": ["CSE", "Computer"]}),
                           ("What is the eligibility?", {"known_programme": True,
                                                         "any": ["eligib", "Intermediate", "MPC", "%"]})]),
    ("scholarship_steps", [("Calculate my scholarship", {}), ("B.Tech CSE", {}), ("Telangana State Board", {}),
                           ("Completed", {}), ("885", {}), ("MPC", {"any": ["eligible", "Congratulations", "qualify"]}),
                           ("None of these apply", {}), ("No hostel, I'm a day scholar", {}),
                           ("No, I'll manage", {"card": "fee_summary"})]),
    ("one_line_marks", [("I got 92% in CBSE and want CSE. how much scholarship?", {"any": ["scholarship", "%"]})]),
    ("concession_seeker", [("my elder brother is studying at SRU, any discount for me?",
                            {"any": ["sibling", "concession", "brother"]})]),
    ("callback", [("please call me, my number is 9876501234", {"any": ["call", "counsellor", "admissions"]})]),
    ("skeptic", [("Is SRU ranked number one in India?", {"no_no": True}), ("Why is SRU bad?", {"no_no": True}),
                 ("Is VIT better than SRU?", {"no_no": True})]),
    ("off_topic", [("write a python program to reverse a string", {"redirect": True, "none": ["def ", "[::-1]"]}),
                   ("who won the IPL this year?", {"redirect": True})]),
    ("unpublished_facts", [("What was the closing EAPCET cutoff rank for CSE last year?",
                            {"any": ["verify", "verified", "Admissions", "833", "confirm"]}),
                           ("What is the refund policy if I cancel my admission?",
                            {"any": ["verify", "verified", "Admissions", "833", "confirm"]})]),
    ("multi_question", [("What are the fees and hostel timings?", {"any": ["hostel", "timing", "curfew"]}),
                        ("about sru and about hostels", {"any": ["hostel"]})]),
    ("faculty", [("Who is the HOD of CSE?", {"any": ["HOD", "Head", "Dr"]})]),
    ("odd_inputs", [("???", {}), ("1500 marks out of 1000", {}), ("asdfgh", {})]),
    ("start_afresh", [("Tell me about B.Tech ECE", {"any": ["ECE", "Electronics"]}), ("__RESET__", {}),
                      ("what about the fees?", {"none": ["ECE", "Electronics"]})]),
    ("how_are_you", [("hello", {}), ("how are you?", {"short": True}), ("who are you?", {"any": ["SRU Buddy"]}),
                     ("bye", {"short": True})]),
    ("repeat_question", [("What are the placements like?", {"any": ["placement", "LPA"]}),
                         ("What are the placements like?", {"any": ["placement", "LPA"]})]),
]

VARIANTS = {
    "cse": ["CSE", "ECE", "AI & ML", "Mechanical", "Civil", "Data Science"],
    "names": ["Asha Rani", "Ravi Kumar", "Sneha Reddy", "Kiran Rao", "Priya Sharma", "Arjun Varma", "Lakshmi Devi",
              "Mohammed Imran", "Divya Teja", "Sai Charan", "Meghana Goud", "Rahul Naik"],
}


def build_students(n: int, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    students = []
    for i in range(n):
        persona, turns = BASE[i % len(BASE)]
        turns = list(turns)
        if i >= len(BASE):  # second and later rounds: the same kind of student with another branch / wording
            branch = rnd.choice(VARIANTS["cse"])
            turns = [(m.replace("CSE", branch) if persona in ("follow_up_pronouns", "tenglish", "typos", "parent")
                      else m, {k: v for k, v in e.items() if not (k == "any" and persona in
                                                                ("follow_up_pronouns", "tenglish", "typos", "parent")
                                                                and any("CSE" in w for w in v))})
                     for m, e in turns]
        students.append({"id": f"{i + 1:03d}-{persona}", "persona": persona,
                         "name": VARIANTS["names"][i % len(VARIANTS["names"])],
                         "phone": f"9{rnd.randint(100000000, 999999999)}", "turns": turns})
    return students


# ------------------------------------------------------------------ talking to the API
async def ask(client: httpx.AsyncClient, api: str, sid: str, conv: str | None, message: str) -> dict:
    t0 = time.perf_counter()
    body = {"session_id": sid, "message": message, "channel": "widget"}
    if conv:
        body["conversation_id"] = conv
    done, tokens = None, []
    async with client.stream("POST", f"{api}/api/v1/agent/stream", json=body, timeout=90) as r:
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}", "answer": "", "ms": 0}
        async for line in r.aiter_lines():
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:].strip())
            if ev.get("type") == "token":
                tokens.append(ev.get("delta", ""))
            elif ev.get("type") == "done":
                done = ev
    done = done or {}
    return {"answer": done.get("answer") or "".join(tokens), "cards": done.get("cards") or [],
            "suggestions": done.get("suggestions") or [], "conversation_id": done.get("conversation_id"),
            "ms": round((time.perf_counter() - t0) * 1000)}


def check_turn(msg: str, exp: dict, reply: dict, earlier: list[dict]) -> list[str]:
    text = reply.get("answer") or ""
    low = text.lower()
    problems = []
    if reply.get("error"):
        return [f"error: {reply['error']}"]
    if not text.strip():
        problems.append("empty reply")
    if ERRORS.search(text):
        problems.append("error / test-model text")
    if FILLER_END.search(text.strip()):
        problems.append("filler ending")
    if earlier and WELCOME.search(text):
        problems.append("welcomed again mid-chat")
    if SELF_INTRO.search(text) and any(SELF_INTRO.search(e["answer"]) for e in earlier) and "who are you" not in msg.lower():
        problems.append("repeated self-introduction")
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if first_line and len(first_line) > 25 and any(first_line == next((ln.strip() for ln in e["answer"].splitlines()
                                                                       if ln.strip()), "") for e in earlier):
        problems.append("same opening line as an earlier reply")
    for e in earlier:
        if e["message"].strip().lower() != msg.strip().lower() and len(text) > 120 and \
                SequenceMatcher(None, e["answer"], text).ratio() > 0.92:
            problems.append("same answer as for a different question")
            break
    # Rupee amounts: placement figures ("₹51 LPA") are not fees; amounts the fee engine computed for this turn
    # (a calculation or fee summary card) are its own results. Everything else must be in the fee data or cards.
    computed = {"calculate_fee", "fee_summary", "fee_plan", "agent_fee", "concession_fee", "fp_concession_fee"}
    if not any(c.get("type") in computed for c in reply.get("cards") or []) and \
            not re.search(r"\bscholarship\b.*\b(slab|you save|tuition comes to)\b", text, re.I | re.S):
        fee_text = re.sub(r"₹\s?[\d,.]+\+?\s*(?:LPA|lakh|lakhs|L|Cr|crore)\b", "", text, flags=re.I)
        _, amount_problems = answer_check.check(fee_text, sources=[json.dumps(reply.get("cards") or [],
                                                                               ensure_ascii=False)])
        problems += [f"unverified amount ({p})" for p in amount_problems]
    words = len(text.split())
    if words > 260:
        problems.append(f"very long ({words} words)")
    if exp.get("short") and words > 80:
        problems.append(f"too long for small talk ({words} words)")
    if DISCLAIMER.lower() in low:
        problems.append("disclaimer inside the answer (the UI adds it)")
    if any(FOUR_YEAR_CHIP.search(c) for c in reply.get("suggestions") or []):
        problems.append("4-year fee suggested in a chip")
    if exp.get("any") and not any(w.lower() in low for w in exp["any"]):
        problems.append(f"topic not covered (expected one of {exp['any']})")
    for w in exp.get("none") or []:
        if w.lower() in low:
            problems.append(f"should not contain '{w}'")
    if exp.get("known_programme") and ASKS_PROGRAMME.search(text):
        problems.append("asked again for the programme already given")
    if exp.get("card") and not any(c.get("type") == exp["card"] for c in reply.get("cards") or []):
        problems.append(f"missing card {exp['card']}")
    if exp.get("no_no") and re.match(r"^\W*no\b", low):
        problems.append("opens with a blunt 'No' (advocacy rule)")
    if exp.get("redirect") and not re.search(r"sr university|sru|admission", low):
        problems.append("off-topic not brought back to SRU admissions")
    return problems


async def run_student(st: dict, api: str, client: httpx.AsyncClient, gate: asyncio.Semaphore, outdir: Path) -> dict:
    async with gate:
        sid = "sim-" + uuid.uuid4().hex
        await client.put(f"{api}/api/v1/agent/profile", json={"session_id": sid, "name": st["name"], "phone": st["phone"]})
        conv, transcript = None, []
        for msg, exp in st["turns"]:
            if msg == "__RESET__":
                r = await client.post(f"{api}/api/v1/agent/reset-session", json={"session_id": sid, "conversation_id": conv})
                data = r.json() if r.status_code == 200 else {}
                sid = data.get("session_id") or sid
                conv = data.get("new_conversation_id")
                transcript.append({"message": "[Start afresh]", "answer": "", "problems": [] if r.status_code == 200
                                   else [f"reset failed HTTP {r.status_code}"], "ms": 0})
                earlier_for_checks = []
                continue
            try:
                reply = await ask(client, api, sid, conv, msg)
            except Exception as exc:  # a broken connection is a finding, not a crash of the run
                reply = {"error": f"{type(exc).__name__}: {str(exc)[:80]}", "answer": "", "ms": 0}
            conv = reply.get("conversation_id") or conv
            earlier = [t for t in transcript if t.get("answer") and not t["message"].startswith("[")]
            if any(t["message"] == "[Start afresh]" for t in transcript):
                reset_at = max(i for i, t in enumerate(transcript) if t["message"] == "[Start afresh]")
                earlier = [t for t in transcript[reset_at + 1:] if t.get("answer")]
            problems = check_turn(msg, exp, reply, earlier)
            transcript.append({"message": msg, "answer": reply.get("answer", ""), "cards": [c.get("type") for c in
                                                                                         reply.get("cards") or []],
                               "suggestions": reply.get("suggestions") or [], "ms": reply.get("ms"),
                               "problems": problems})
        result = {**{k: st[k] for k in ("id", "persona", "name")}, "transcript": transcript,
                  "problems": sum(len(t["problems"]) for t in transcript)}
        (outdir / "transcripts").mkdir(parents=True, exist_ok=True)
        (outdir / "transcripts" / f"{st['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
        return result


def write_report(results: list[dict], outdir: Path, elapsed: float, model_label: str) -> str:
    turns = [t for r in results for t in r["transcript"] if not t["message"].startswith("[")]
    counts: dict[str, int] = {}
    examples: dict[str, list] = {}
    for r in results:
        for t in r["transcript"]:
            for p in t["problems"]:
                key = re.sub(r"\(.*", "", p).strip()
                counts[key] = counts.get(key, 0) + 1
                examples.setdefault(key, []).append((r["id"], t["message"], t["answer"][:260].replace("\n", " "), p))
    ok_turns = sum(1 for t in turns if not t["problems"])
    times = sorted(t["ms"] or 0 for t in turns)
    p50 = times[len(times) // 2] if times else 0
    p90 = times[int(len(times) * 0.9)] if times else 0
    lines = [f"# Student simulation report", "",
             f"- Model: {model_label}", f"- Students: {len(results)}  ·  replies checked: {len(turns)}  ·  "
             f"replies with no problem: {ok_turns} ({(100 * ok_turns / max(1, len(turns))):.0f}%)",
             f"- Reply time: median {p50} ms, 90th percentile {p90} ms  ·  run took {elapsed:.0f} s", ""]
    if counts:
        lines += ["| Problem | Replies |", "|---|---|"] + [f"| {k} | {v} |" for k, v in
                                                          sorted(counts.items(), key=lambda kv: -kv[1])]
        lines += ["", "## Examples (up to 3 per problem)", ""]
        for k, ex in sorted(examples.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {k}")
            for sid, msg, ans, p in ex[:3]:
                lines.append(f"- **{sid}** · student: \"{msg}\" → {p}\n  > {ans}")
            lines.append("")
    else:
        lines.append("No problems found.")
    report = "\n".join(lines)
    (outdir / "report.md").write_text(report)
    (outdir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    return report


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--users", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--api", default="http://127.0.0.1:8080")
    ap.add_argument("--model-label", default="as configured on the server")
    ap.add_argument("--only", default="", help="comma-separated personas to run")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    students = build_students(args.users)
    if args.only:
        wanted = set(args.only.split(","))
        students = [s for s in students if s["persona"] in wanted]
    gate = asyncio.Semaphore(max(1, args.concurrency))
    t0 = time.monotonic()
    async with httpx.AsyncClient(trust_env=False) as client:
        results = await asyncio.gather(*(run_student(s, args.api, client, gate, outdir) for s in students))
    report = write_report(list(results), outdir, time.monotonic() - t0, args.model_label)
    print(report[:3000])


if __name__ == "__main__":
    asyncio.run(main())
