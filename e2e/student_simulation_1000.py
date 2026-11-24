"""SRU Buddy: 1,000 different students, each with their own mindset and wording (v4.14.0).

Builds on student_simulation.py (same API calls and per-reply checks) but generates the students: 18 mindsets
(anxious parent, topper, low scorer, budget-conscious, fun-seeker, skeptic, confused, impatient texter, Telugu-
English, Hindi-English, hostel-focused, sports person, safety-conscious, comparison shopper, rude, wanderer,
day scholar, outstation student), each asking 3-7 questions about SR University drawn from ~30 topics with several
wordings, typos and casual spellings, and follow-ups that depend on the earlier turn ("what about its fees?").

80% of the students only type. 20% also tap the quick-response buttons when the reply offers them; a reply to a
button is checked against the button's own words. Every reply is checked for: an error, an empty reply, a filler
ending, being welcomed again, a repeated answer to a different question, unverified rupee amounts, length, and
that it is about what was asked (expected words for the topic).

Replies the code cannot give itself go to the language model. Without a Gemini key the review server's stand-in
model answers them (it says so); those turns are counted separately as "needs the AI model" (not a failure of the
code, and not checked for content).

Usage: python e2e/student_simulation_1000.py <outdir> [--users 1000] [--concurrency 16] [--api http://127.0.0.1:8080]
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

PROGS = ["B.Tech CSE", "B.Tech AI & ML", "B.Tech ECE", "B.Tech Mechanical", "B.Tech Civil", "B.Tech Data Science",
         "BBA", "MBA", "B.Sc Agriculture", "BCA", "B.Des"]
SHORT = {"B.Tech CSE": "cse", "B.Tech AI & ML": "aiml", "B.Tech ECE": "ece", "B.Tech Mechanical": "mech",
         "B.Tech Civil": "civil", "B.Tech Data Science": "data science", "BBA": "bba", "MBA": "mba",
         "B.Sc Agriculture": "agriculture", "BCA": "bca", "B.Des": "b.des"}
FEE_WORDS = ["₹", "fee", "eligib", "marks", "scholarship", "board", "programme", "course", "which"]
MODEL_TEXT = re.compile(r"Review model: no Gemini key", re.I)

# topic -> (wordings, expectations). {p} programme, {s} its short name, {pct} a percentage.
TOPICS: dict[str, tuple[list[str], dict]] = {
    "fees": (["What is the fee for {p}?", "{s} fees?", "how much is {p} per year", "{s} fee structure pls",
              "fees for {p} at SRU", "total cost of {p} first year"], {"any": FEE_WORDS}),
    "scholarship": (["I got {pct}% in inter, how much scholarship?", "scholarship for {pct} percent",
                     "merit scholarship details", "what scholarships does SRU give", "any scholarship for toppers?"],
                    {"any": ["scholarship", "%", "merit", "marks", "board"]}),
    "eligibility": (["what is the eligibility for {p}", "can I join {s} with {pct}%?", "eligibility criteria for {s}",
                     "am I eligible for {p} with {pct} percent"],
                    {"any": ["eligib", "%", "Intermediate", "MPC", "qualif", "10+2", "marks", "board", "programme"]}),
    "placements": (["how are the placements?", "highest package at SRU", "which companies come for placements",
                    "average package for {s}", "placement record", "do students get jobs after {s}"],
                   {"any": ["placement", "LPA", "recruit", "package", "compan"]}),
    "hostel_fee": (["hostel fees", "what is the AC room fee", "how much is hostel per year"], {"any": ["₹", "hostel"]}),
    "hostel_life": (["how is hostel life", "is the hostel good?", "life in the hostel?", "hostel experience at sru"],
                    {"any": ["hostel"]}),
    "food": (["how is the food?", "mess timings", "is non veg available in mess?", "is there a canteen",
              "is the hostel food good", "what time is breakfast"],
             {"any": ["food", "mess", "dining", "meal", "breakfast", "cafeteria", "canteen"]}),
    "events": (["what events happen at sru?", "fests in sru?", "any cultural fest?", "tell me about college events",
                "what celebrations happen on campus"], {"any": ["event", "fest", "Sparkrill", "celebrat"]}),
    "event_one": (["what is lumina?", "when is sparkrill", "is there a hostel night?", "what is navadhara",
                   "freshers party?", "tell me about the project expo", "any hackathons?"],
                  {"any": ["Lumina", "Sparkrill", "Navadhara", "Swagatham", "PRAGATHI", "Hackathon", "Hostel Night"]}),
    "clubs": (["what clubs are there?", "is there a coding club", "dance club?", "is there a robotics club",
               "music club available?", "tech clubs at sru"], {"any": ["club"]}),
    "sports": (["what sports facilities are there", "is there a gym?", "is there a cricket ground",
                "sports at sru?"], {"any": ["sport", "gym", "cricket", "ground", "court"]}),
    "campus_life": (["how is campus life?", "is campus life boring?", "what do students do after classes",
                     "student life at sru"], {"any": ["campus", "event", "club"]}),
    "safety": (["is the campus safe for girls?", "is the hostel safe?", "security on campus?"],
               {"any": ["safe", "security", "CCTV", "warden", "surveillance"]}),
    "curfew": (["hostel in-time?", "what are the hostel timings", "hostel curfew"], {"any": ["PM", "curfew", "in-time",
                                                                                          "In-Time"]}),
    "apply": (["how do I apply?", "admission process", "how to get admission in sru", "application fee?"],
              {"any": ["apply", "application", "admission", "process", "verify", "counsellor"]}),
    "programmes": (["what courses are there?", "programmes offered at SRU", "do you have BBA?", "which branches in btech"],
                   {"any": ["B.Tech", "programme", "program", "BBA", "MBA", "course", "branch"]}),
    "why": (["why should I choose SRU?", "is SRU a good university?", "what is the ranking of SRU",
             "why sru over others"], {"any": ["NIRF", "THE", "rank", "research", "placement", "NBA", "ICAR"]}),
    "skeptic": (["Is SRU ranked number one in India?", "why is SRU bad?", "Is VIT better than SRU?",
                 "is sru fake university", "honestly is sru worth it?"], {"no_no": True}),
    "location": (["where is SRU located?", "where is the campus"], {"any": ["Warangal", "Hasanparthy", "Ananthasagar",
                                                                            "Telangana"]}),
    "connect": (["I want to talk to a human", "connect me to customer care", "can I speak to a real person",
                 "talk to counsellor please"], {"any": ["counsellor", "connect", "call", "admissions"]}),
    "small_talk": (["hi", "hello", "good morning", "thanks", "ok thank you", "bye"], {"short": True}),
    "off_topic": (["write a poem about rain", "who won the IPL this year?", "what is the capital of France"],
                  {"redirect": True}),
    "unpublished": (["what was the cutoff rank for CSE last year?", "what is the refund policy?",
                     "how many seats in cse?"], {"any": ["verify", "verified", "Admissions", "833", "confirm", "cut-off",
                                                         "cutoff", "counsellor"]}),
    "follow_fee": (["what about its fees?", "and the fee?", "fees for it?"], {"known_programme": True, "any": FEE_WORDS}),
    "follow_place": (["how are placements for it?", "placements there?"], {"any": ["placement", "LPA", "recruit"]}),
    "programme": (["tell me about {p}", "{p} details", "about {s} course"], {"any": ["{p_word}"]}),
    "concession": (["my brother studies at SRU, any discount?", "is there any concession for girls?",
                    "any fee concession for single parent?", "sports quota available?"],
                   {"any": ["concession", "discount", "sibling", "scholarship", "₹", "eligib", "quota", "special"]}),
}

TYPO = {"fees": "fess", "placements": "placments", "scholarship": "scholarshp", "hostel": "hostal",
        "eligibility": "eligiblity", "campus": "campas", "events": "evnts", "food": "fud"}
TENGLISH = {"how is": "ela undi", "is there": "undha", "what is": "enti", "?": " ah?"}
HINGLISH = {"how is": "kaisa hai", "is there": "hai kya", "what is": "kya hai", "?": " bhai?"}

# mindset -> (topic weights, style)
MINDSETS: dict[str, tuple[dict[str, int], str]] = {
    "anxious_parent": ({"safety": 3, "hostel_life": 2, "food": 2, "fees": 2, "curfew": 2, "placements": 1,
                        "programme": 1, "follow_fee": 1}, "formal"),
    "topper": ({"scholarship": 3, "placements": 3, "why": 2, "programme": 2, "follow_fee": 1, "eligibility": 1}, "plain"),
    "low_scorer": ({"eligibility": 4, "scholarship": 2, "fees": 2, "programmes": 1, "concession": 1}, "plain"),
    "budget": ({"fees": 3, "scholarship": 3, "concession": 3, "hostel_fee": 2, "follow_fee": 1}, "plain"),
    "fun_seeker": ({"events": 3, "event_one": 3, "clubs": 3, "sports": 2, "campus_life": 3, "hostel_life": 2,
                    "food": 1}, "casual"),
    "skeptic": ({"skeptic": 4, "why": 2, "placements": 2, "unpublished": 1}, "plain"),
    "confused": ({"programmes": 3, "programme": 2, "apply": 2, "small_talk": 1, "eligibility": 1, "follow_fee": 1},
                 "casual"),
    "impatient_texter": ({"fees": 2, "placements": 2, "hostel_fee": 1, "food": 1, "events": 1, "small_talk": 1},
                         "short"),
    "tenglish": ({"fees": 2, "hostel_life": 2, "food": 2, "placements": 2, "events": 1, "campus_life": 1}, "tenglish"),
    "hinglish": ({"fees": 2, "hostel_life": 2, "food": 1, "placements": 2, "clubs": 1, "sports": 1}, "hinglish"),
    "hostel_focused": ({"hostel_life": 3, "hostel_fee": 2, "food": 3, "curfew": 2, "safety": 2, "event_one": 1},
                       "plain"),
    "sports_person": ({"sports": 4, "clubs": 2, "events": 1, "concession": 1, "campus_life": 1}, "casual"),
    "safety_conscious": ({"safety": 4, "curfew": 2, "hostel_life": 2, "location": 1, "connect": 1}, "formal"),
    "comparison_shopper": ({"skeptic": 2, "why": 3, "placements": 2, "fees": 1, "location": 1}, "plain"),
    "rude": ({"skeptic": 3, "placements": 1, "fees": 1, "off_topic": 1, "connect": 1}, "short"),
    "wanderer": ({"off_topic": 2, "small_talk": 2, "events": 1, "clubs": 1, "why": 1, "food": 1}, "casual"),
    "day_scholar": ({"fees": 2, "location": 2, "food": 2, "campus_life": 2, "clubs": 1, "apply": 1}, "plain"),
    "outstation": ({"hostel_life": 2, "hostel_fee": 1, "location": 2, "food": 2, "safety": 1, "apply": 1, "unpublished": 1},
                   "formal"),
}
FOLLOW_UPS = {"follow_fee", "follow_place"}
NAMES = base.VARIANTS["names"] + ["Nikhil Sai", "Ananya Rao", "Vamshi Krishna", "Harika Reddy", "Zoya Khan",
                                  "Rohit Yadav", "Pooja Patel", "Srinivas Goud"]


def styled(text: str, style: str, rnd: random.Random) -> str:
    if style == "formal":
        return rnd.choice(["", "Good evening. ", "Hello sir, ", "Namaste. "]) + text[0].upper() + text[1:]
    if style == "short":
        text = re.sub(r"^(what is|how is|is there|what are|tell me about)\s+", "", text, flags=re.I)
        text = text.lower().rstrip("?.!")
        for k, v in TYPO.items():
            if k in text and rnd.random() < 0.5:
                text = text.replace(k, v)
        return text + rnd.choice(["", "?", " pls", " ??"])
    if style == "casual":
        return text.lower().replace("?", rnd.choice(["?", "??", " ?", ""])) + rnd.choice(["", " bro", " pls", ""])
    if style in ("tenglish", "hinglish"):
        table = TENGLISH if style == "tenglish" else HINGLISH
        low = text.lower()
        for k, v in table.items():
            if k in low and rnd.random() < 0.7:
                low = low.replace(k, v, 1)
        return low
    return text


def build(n: int, seed: int = 2026) -> list[dict]:
    rnd = random.Random(seed)
    names = list(MINDSETS)
    chip_ids = set(rnd.sample(range(n), k=n // 5))           # 20% also tap the quick-response buttons
    students = []
    for i in range(n):
        mind = names[i % len(names)]
        weights, style = MINDSETS[mind]
        prog = rnd.choice(PROGS)
        pct = rnd.choice([52, 61, 68, 74, 79, 83, 88, 91, 94, 97])
        turns, last = [], None
        for t in range(rnd.randint(3, 7)):
            topics = [k for k in weights if not (k in FOLLOW_UPS and last not in ("programme", "fees", "eligibility"))]
            topic = rnd.choices(topics, weights=[weights[k] for k in topics])[0]
            if t == 0 and rnd.random() < 0.25:
                topic = "small_talk"
            wordings, exp = TOPICS[topic]
            msg = rnd.choice(wordings).format(p=prog, s=SHORT[prog], pct=pct)
            exp = dict(exp)
            if topic == "programme":
                exp["any"] = [SHORT[prog].split()[0], prog.split()[-1]]
            if topic == "small_talk" and t == 0:
                exp = {}
            if not (style in ("short", "tenglish", "hinglish") and topic in ("skeptic", "off_topic", "unpublished")):
                msg = styled(msg, style, rnd)
            if style in ("short", "tenglish", "hinglish"):
                exp.pop("any", None) if topic in ("unpublished",) else None
            turns.append({"message": msg, "topic": topic, "exp": exp})
            last = topic
        students.append({"id": f"{i + 1:04d}-{mind}", "mindset": mind, "style": style, "taps_chips": i in chip_ids,
                         "name": NAMES[i % len(NAMES)], "phone": f"9{rnd.randint(100000000, 999999999)}",
                         "turns": turns, "seed": rnd.randint(0, 10**9)})
    return students


_CHIP_STOP = set("yes no the a an and or of to for my me show see at sru about more other all".split())


def chip_expectation(chip: str) -> dict:
    words = [w for w in re.findall(r"[a-z]+", chip.lower()) if len(w) > 3 and w not in _CHIP_STOP]
    stems = [w[:5] for w in words]
    return {"any": stems} if stems else {}


async def run(st: dict, api: str, client: httpx.AsyncClient, gate: asyncio.Semaphore, outdir: Path) -> dict:
    rnd = random.Random(st["seed"])
    async with gate:
        sid = "sim1k-" + uuid.uuid4().hex
        await client.put(f"{api}/api/v1/agent/profile", json={"session_id": sid, "name": st["name"], "phone": st["phone"]})
        conv, transcript = None, []
        queue = list(st["turns"])
        taps = 0
        while queue:
            turn = queue.pop(0)
            msg, exp = turn["message"], turn["exp"]
            try:
                reply = await base.ask(client, api, sid, conv, msg)
            except Exception as exc:
                reply = {"error": f"{type(exc).__name__}: {str(exc)[:80]}", "answer": "", "ms": 0}
            conv = reply.get("conversation_id") or conv
            earlier = [t for t in transcript if t.get("answer")]
            model_turn = bool(MODEL_TEXT.search(reply.get("answer") or ""))
            problems = [] if model_turn else base.check_turn(msg, exp, reply, earlier)
            transcript.append({"message": msg, "topic": turn["topic"], "chip": turn.get("chip", False),
                               "answer": reply.get("answer", ""), "cards": [c.get("type") for c in reply.get("cards") or []],
                               "suggestions": reply.get("suggestions") or [], "ms": reply.get("ms"),
                               "needs_model": model_turn, "problems": problems})
            chips = reply.get("suggestions") or []
            if st["taps_chips"] and chips and taps < 3 and rnd.random() < 0.6:
                chip = rnd.choice(chips)
                taps += 1
                queue.insert(0, {"message": chip, "topic": "chip", "exp": chip_expectation(chip), "chip": True})
        result = {k: st[k] for k in ("id", "mindset", "style", "taps_chips", "name")}
        result.update(transcript=transcript, problems=sum(len(t["problems"]) for t in transcript))
        (outdir / "transcripts").mkdir(parents=True, exist_ok=True)
        (outdir / "transcripts" / f"{st['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
        return result


def report(results: list[dict], outdir: Path, elapsed: float) -> str:
    turns = [t for r in results for t in r["transcript"]]
    checked = [t for t in turns if not t["needs_model"]]
    model = [t for t in turns if t["needs_model"]]
    ok = [t for t in checked if not t["problems"]]
    chips = [t for t in turns if t["chip"]]
    counts, examples, by_topic = {}, {}, {}
    for r in results:
        for t in r["transcript"]:
            b = by_topic.setdefault(t["topic"], [0, 0, 0])
            b[0] += 1
            b[1] += bool(t["problems"])
            b[2] += t["needs_model"]
            for p in t["problems"]:
                key = re.sub(r"\(.*", "", p).strip()
                counts[key] = counts.get(key, 0) + 1
                examples.setdefault(key, []).append((r["id"], t["message"], t["answer"][:240].replace("\n", " "), p))
    times = sorted(t["ms"] or 0 for t in turns)
    pct = lambda q: times[min(len(times) - 1, int(len(times) * q))] if times else 0  # noqa: E731
    lines = ["# 1,000-student simulation", "",
             f"- Students: {len(results)} ({sum(r['taps_chips'] for r in results)} also tap buttons, "
             f"{sum(not r['taps_chips'] for r in results)} only type) · mindsets: {len(MINDSETS)}",
             f"- Replies: {len(turns)} ({len(chips)} after a button tap)",
             f"- Answered by the code and checked: {len(checked)} · no problem: {len(ok)} "
             f"({100 * len(ok) / max(1, len(checked)):.1f}%)",
             f"- Needs the AI model (stand-in here, not checked): {len(model)} ({100 * len(model) / max(1, len(turns)):.1f}%)",
             f"- Reply time: median {pct(0.5)} ms, 90th percentile {pct(0.9)} ms · run {elapsed:.0f} s", "",
             "## By topic", "", "| Topic | Replies | With a problem | Needs the model |", "|---|---|---|---|"]
    lines += [f"| {k} | {v[0]} | {v[1]} | {v[2]} |" for k, v in sorted(by_topic.items(), key=lambda kv: -kv[1][0])]
    lines += ["", "## Problems", ""]
    if counts:
        lines += ["| Problem | Replies |", "|---|---|"] + [f"| {k} | {v} |" for k, v in
                                                          sorted(counts.items(), key=lambda kv: -kv[1])]
        lines += ["", "## Examples (up to 5 per problem)", ""]
        for k, ex in sorted(examples.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {k}")
            for sid, msg, ans, p in ex[:5]:
                lines.append(f"- **{sid}** · \"{msg}\" → {p}\n  > {ans}")
            lines.append("")
    else:
        lines.append("No problems found.")
    text = "\n".join(lines)
    (outdir / "report.md").write_text(text)
    (outdir / "results.json").write_text(json.dumps(results, ensure_ascii=False))
    return text


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--users", type=int, default=1000)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--api", default="http://127.0.0.1:8080")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    students = build(args.users)
    gate = asyncio.Semaphore(args.concurrency)
    t0 = time.monotonic()
    async with httpx.AsyncClient(trust_env=False, timeout=120) as client:
        results = await asyncio.gather(*(run(s, args.api, client, gate, outdir) for s in students))
    print(report(list(results), outdir, time.monotonic() - t0)[:4000])


if __name__ == "__main__":
    asyncio.run(main())
