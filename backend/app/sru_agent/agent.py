"""The agent loop: the model decides, calls tools, reads results, then answers.

    student message
        -> quick checks the code can settle by itself (today's date, "don't call me",
           a callback / visit request that already has name + number)
        -> model (sees instructions + student profile + tools)
        -> wants a tool?  yes: run it, give the result back, ask again (max N rounds)
                          no : that text is the final answer
        -> honesty checks (never "saved" or "cancelled" unless a tool really did it)

Yields small event dicts so the API can stream progress to the browser:
    {"type": "start"} {"type": "tool", ...} {"type": "token", "delta": "..."} {"type": "done", ...}

Under load the agent (1) spreads students across every configured Gemini key, (2) moves to the
next key when one is rate limited, (3) waits and retries when Google is busy, (4) lets only
AGENT_MAX_CONCURRENCY model calls run at once, and (5) still answers fee questions from the fee
file if the model cannot be reached at all.
"""
import asyncio
import logging
import re
import time
import weakref
from datetime import date, datetime

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from . import affordability, config, faculty, fee_flow, fee_intake, fees, followups, intents, knowledge, memory, responses, tools
from . import fact_service, policy_engine, policy_models, policy_service, semantic_router, observability
from .prompt import build_system_prompt

log = logging.getLogger("sru_agent")
_client = None

FALLBACK_OPTIONS = [
    f"I'm having trouble right now. Please call the Admissions Office at {config.ADMISSIONS_PHONE} or try again in a moment.",
    f"I'm experiencing a temporary connection issue. Please try again in a moment, or reach Admissions directly at {config.ADMISSIONS_PHONE}.",
    f"I couldn't reach the service just now. Please try again in a moment, or call the Admissions Office at {config.ADMISSIONS_PHONE}.",
]
FALLBACK = FALLBACK_OPTIONS[0]


def get_fallback_text(seed_str: str = "") -> str:
    if not seed_str:
        return FALLBACK
    import hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return FALLBACK_OPTIONS[h % len(FALLBACK_OPTIONS)]
# Results of these tools are sent to the browser so it can draw a card.
CARD_TOOLS = {"calculate_fee", "check_eligibility", "request_counsellor_callback",
              "request_campus_visit_callback", "get_contact_and_apply_links", "get_university_videos",
              "find_faculty"}
# When one of these ran, the answer is about this student's own numbers, so the generic
# "B.Tech CSE fee" table from card_service must not be shown underneath it.
_FEE_TOOLS = {"calculate_fee", "compare_programs", "get_program_info", "get_special_concessions"}
_FALLBACK_MODELS = ("gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash")
# Campus visits: SRU Buddy never books or confirms one (admissions brief, Nov 2026). It points to the
# admissions team (sru.edu.in/visit-us) and can pass the student's number on as a callback request.
def _visit_guide(date_text: str | None = None) -> str:
    asked = f" for {date_text}" if date_text else ""
    return (f"Campus visits{asked} are arranged by the SR University admissions team. I can't book or confirm a "
            f"visit myself, but they will help you plan it:\n"
            f"- Call or WhatsApp: {config.CAMPUS_VISIT_PHONE}\n"
            f"- Campus: {config.CAMPUS_ADDRESS}\n\n"
            f"Please confirm the day and time with them before you travel. If you like, share your name and "
            f"10-digit mobile number and I will ask the admissions team to call you back about the visit.")


_CAMPUS_TOUR_CHOICE_CHIPS = ["🎥 Virtual Tour (Videos & Info)", "🏛️ In-Person Campus Visit"]
_CAMPUS_TOUR_CHOICE_TEXT = (
    "We offer two ways to explore our 170-acre campus:\n\n"
    "1. 🎥 **Virtual Tour** – Watch official video walkthroughs and explore our smart classrooms, central library, "
    "AI & robotics centers, and student life online.\n"
    "2. 🏛️ **In-Person Visit** – Visit our Warangal campus in person, meet faculty, and take a guided tour "
    "arranged by our admissions team.\n\n"
    "Which one would you prefer?"
)

_VIRTUAL_TOUR_CHIPS = ["🏛️ In-Person Campus Visit", "Hostel details", "Why choose SRU?"]
_VIRTUAL_TOUR_TEXT = (
    "Here is the virtual walkthrough of our 170-acre Warangal campus!\n\n"
    "• 🏛️ **Academic & Research**: Smart IoT classrooms, digital central library, and 11 specialized research centers.\n"
    "• 🚀 **SRiX Innovation Exchange**: On-campus incubator with 14+ maker spaces supporting 171+ student startups.\n"
    "• 🏠 **Campus Life**: Modern sports arenas, secure hostels, and a 4,000-seat dining hall.\n\n"
    f"Explore the videos below! For an in-person guided tour, call Admissions at {config.CAMPUS_VISIT_PHONE}."
)

_VISIT_CHIPS = ["Ask counsellor to call me", "How to reach the campus", "🎥 Virtual Tour (Videos & Info)"]
_VISIT_DETAIL = re.compile(r"\b(?:parents?|timings?|hours?|allowed|dress|bring|documents?|reach|directions?|route|"
                           r"bus|train|far|distance|weekends?|sundays?|holidays?|accompan\w*|stay|guest|lunch|"
                           r"free|cost|charge)\b", re.IGNORECASE)


# ------------------------------------------------------------ model access ----
class _KeyRing:
    """One Gemini client per configured API key, handed out in turn."""

    def __init__(self):
        self._pool = None
        self._clients = {}

    def _get_pool(self):
        if self._pool is None:
            keys = list(config.GEMINI_API_KEYS) or ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
            if not keys:
                return None
            from app.providers.key_pool import APIKeyPool
            self._pool = APIKeyPool(keys, default_cooldown=config.AGENT_KEY_COOLDOWN_SECONDS)
        return self._pool

    def next_key(self) -> str:
        pool = self._get_pool()
        return pool.get_next_key() if pool else ""

    def client(self, key: str):
        if key not in self._clients:
            self._clients[key] = genai.Client(api_key=key)
        return self._clients[key]

    def rate_limited(self, key: str, cooldown: float | None = None) -> str:
        """Rest this key for a while; returns the key to use next (may be the same one)."""
        pool = self._get_pool()
        return pool.mark_rate_limited(key, cooldown) if pool else key

    def all_resting(self) -> bool:
        """True when every key is waiting out a limit (no point calling the model right now)."""
        pool = self._get_pool()
        return bool(pool) and pool.active_keys_count == 0

    def worked(self, key: str):
        pool = self._get_pool()
        if pool:
            pool.mark_success(key)

    def size(self) -> int:
        pool = self._get_pool()
        return len(pool) if pool else 0


_ring = _KeyRing()
_gates = weakref.WeakKeyDictionary()


def get_client():
    """A Gemini client on the first configured key (kept for scripts and older code)."""
    global _client
    if _client is None:
        _client = _ring.client(_ring.next_key() or config.GEMINI_API_KEY)
    return _client


def _gate() -> asyncio.Semaphore:
    """At most AGENT_MAX_CONCURRENCY model calls at a time; the rest queue instead of failing."""
    loop = asyncio.get_running_loop()
    gate = _gates.get(loop)
    if gate is None:
        gate = _gates[loop] = asyncio.Semaphore(max(1, config.AGENT_MAX_CONCURRENCY))
    return gate


def _error_kind(exc: Exception) -> str:
    """'model' (try another model), 'rate' (try another key / wait), 'busy' (wait), 'config' (the
    model refused a setting such as the thinking level), or 'fatal'."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    text = str(exc).lower()
    if (code == 400 or "400" in text or "invalid_argument" in text) and "think" in text:
        return "config"
    if code == 404 or "not found" in text or "404" in text or "no longer available" in text:
        return "model"
    if code == 429 or "429" in text or "resource_exhausted" in text or "resource exhausted" in text \
            or "quota" in text or "rate limit" in text:
        return "rate"
    if isinstance(exc, (ConnectionError, OSError)) or "connecterror" in type(exc).__name__.lower() \
            or "connection" in text or "timed out" in text or "name resolution" in text:
        return "busy"  # the network or Google is unreachable: wait, then answer without the model
    if code in (500, 502, 503, 504) or isinstance(exc, (asyncio.TimeoutError, TimeoutError)) \
            or any(w in text for w in ("503", "unavailable", "overloaded", "deadline exceeded", "internal error")):
        return "busy"
    return "fatal"


class ModelUnavailable(Exception):
    """Every key has used up its quota: answer without the model instead of making students wait."""


def _remaining_budget(link: dict) -> float:
    deadline = link.get("deadline")
    if deadline is None:
        return config.AGENT_CALL_TIMEOUT
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ModelUnavailable("agent request time budget exhausted")
    return min(config.AGENT_CALL_TIMEOUT, remaining)


def _is_daily_limit(exc: Exception) -> bool:
    text = str(exc).lower().replace(" ", "").replace("_", "")
    return "perday" in text or "daily" in text or "requestsperday" in text


async def _handle_call_error(exc, link: dict, attempt: int, model: str) -> float | None:
    """Decide what to do after a failed model call: None = try the next model at once, a number =
    wait that long and retry; raises when there is nothing left to try."""
    kind = link["error_kind"] = _error_kind(exc)
    err_str = str(exc).lower()
    if "name resolution" in err_str or "clientconnectordnserror" in type(exc).__name__.lower():
        raise exc
    if kind == "model" and link["model_idx"] + 1 < len(link["models"]):
        log.warning("Agent model %s unavailable (%s), trying the next model", model, exc)
        link["model_idx"] += 1
        return None
    if kind == "config" and link.get("thinking"):
        log.warning("Model %s refused the thinking setting (%s); retrying without it", model, str(exc)[:120])
        link["thinking"] = False
        return None
    if kind in ("fatal", "model", "config") or attempt >= len(config.AGENT_RETRY_DELAYS):
        raise exc
    wait = config.AGENT_RETRY_DELAYS[attempt]
    if kind == "rate" and not link["fixed"]:
        # A per-day limit will not clear in a few seconds: rest that key for an hour.
        daily = _is_daily_limit(exc)
        new_key = _ring.rate_limited(link["key"], config.AGENT_DAILY_LIMIT_COOLDOWN if daily else None)
        if _ring.all_resting() and (daily or _ring.size() > 1):
            raise ModelUnavailable(str(exc)[:200]) from exc
        if new_key != link["key"]:
            link["key"], wait = new_key, 0.2  # a fresh key: go again almost at once
    log.warning("Model call %s (%s); retry %d in %.1fs", kind, str(exc)[:120], attempt + 1, wait)
    return wait


def _with_thinking(cfg, link: dict, model: str):
    """Ask for the least thinking the model allows (AGENT_THINKING_LEVEL), which is the biggest
    single speed setting on Gemini 3 models. Dropped automatically if a model refuses it."""
    level = (config.AGENT_THINKING_LEVEL or "").upper()
    if not link.get("thinking") or not level or level == "DEFAULT":
        return cfg
    if model.startswith("gemini-2"):
        thinking = types.ThinkingConfig(thinking_budget=0)
    else:
        if level == "MINIMAL" and not any(model.startswith(m) for m in _MINIMAL_OK):
            level = "LOW"
        thinking = types.ThinkingConfig(thinking_level=level)
    return cfg.model_copy(update={"thinking_config": thinking})


# Models that accept thinking_level MINIMAL (the others get LOW).
_MINIMAL_OK = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash",
               "gemini-3-flash")


async def _generate(contents, cfg, link: dict):
    """One model call that survives a retired model, a rate-limited key and a busy server.

    `link` carries the connection for this student message: a fixed client (tests) or the
    current key, plus the model that last worked. This function, _generate_stream and _KeyRing
    are the only code that talks to the AI provider: moving to a paid Gemini plan needs only new
    keys in the environment; another provider needs only a replacement for these functions.
    """
    attempt = 0
    if not link["fixed"] and _ring.all_resting():
        link["error_kind"] = "rate"
        raise ModelUnavailable("all Gemini keys are resting after a rate limit")
    while True:
        client = link["fixed"] or _ring.client(link["key"])
        model = link["models"][link["model_idx"]]
        try:
            timeout = _remaining_budget(link)
            async with _gate():
                resp = await asyncio.wait_for(
                    client.aio.models.generate_content(model=model, contents=contents,
                                                       config=_with_thinking(cfg, link, model)),
                    timeout=timeout)
            if not link["fixed"]:
                _ring.worked(link["key"])
            return resp
        except Exception as exc:
            wait = await _handle_call_error(exc, link, attempt, model)
            if wait is None:
                continue
            attempt += 1
            if link.get("deadline") is not None and time.monotonic() + wait >= link["deadline"]:
                raise ModelUnavailable("agent request time budget exhausted") from exc
            await asyncio.sleep(wait)


def _can_stream(link: dict) -> bool:
    client = link["fixed"] or (_ring.client(link["key"]) if link["key"] else None)
    return bool(config.AGENT_STREAM) and client is not None and \
        hasattr(getattr(getattr(client, "aio", None), "models", None), "generate_content_stream")


async def _generate_stream(contents, cfg, link: dict):
    """Like _generate, but hands over the answer while the model is still writing it.

    Yields ("text", piece) as words arrive, then ("done", response) with every part the model
    sent (function calls and their thought signatures included), so the agent loop treats it
    exactly like a normal response. Errors before the first piece are retried like _generate;
    an error in the middle of an answer is raised (the words already shown are replaced by the
    final reply or the error message)."""
    attempt = 0
    if not link["fixed"] and _ring.all_resting():
        link["error_kind"] = "rate"
        raise ModelUnavailable("all Gemini keys are resting after a rate limit")
    while True:
        client = link["fixed"] or _ring.client(link["key"])
        model = link["models"][link["model_idx"]]
        started = False
        try:
            timeout = _remaining_budget(link)
            async with _gate():
                stream = await asyncio.wait_for(
                    client.aio.models.generate_content_stream(model=model, contents=contents,
                                                              config=_with_thinking(cfg, link, model)),
                    timeout=timeout)
                parts, last = [], None
                iterator = stream.__aiter__()
                while True:
                    try:
                        chunk = await asyncio.wait_for(iterator.__anext__(), timeout=_remaining_budget(link))
                    except StopAsyncIteration:
                        break
                    last = chunk
                    cand = (chunk.candidates or [None])[0]
                    for part in ((cand.content.parts if cand and cand.content else None) or []):
                        parts.append(part)
                        if part.text and not getattr(part, "thought", False):
                            started = True
                            yield ("text", part.text)
            if not link["fixed"]:
                _ring.worked(link["key"])
            merged = types.GenerateContentResponse(candidates=[types.Candidate(
                content=types.Content(role="model", parts=parts),
                finish_reason=getattr((last.candidates or [None])[0], "finish_reason", None) if last else None)])
            yield ("done", merged)
            return
        except Exception as exc:
            if started:
                link["error_kind"] = _error_kind(exc)
                raise
            wait = await _handle_call_error(exc, link, attempt, model)
            if wait is None:
                continue
            attempt += 1
            if link.get("deadline") is not None and time.monotonic() + wait >= link["deadline"]:
                raise ModelUnavailable("agent request time budget exhausted") from exc
            await asyncio.sleep(wait)


def _tool_declarations():
    return types.Tool(function_declarations=[
        types.FunctionDeclaration(name=name, **decl) for name, (_fn, _label, decl) in tools.TOOLS.items()])


def _chunks(text: str, words_per_chunk: int = 6):
    words = re.findall(r"\S+\s*", text)
    for i in range(0, len(words), words_per_chunk):
        yield "".join(words[i:i + words_per_chunk])


# ------------------------------------------------------- small reply helpers ----
def _done(conversation_id, answer, used=(), cards=(), suggestions=(), telemetry=None):
    d = {"type": "done", "conversation_id": conversation_id, "answer": answer,
         "tools_used": list(used), "model": config.AGENT_MODEL,
         # kept so the existing frontend 'done' handler does not break
         "sources": [], "suggestions": list(suggestions), "cards": list(cards), "flow": None}
    if telemetry is not None:
        d["telemetry"] = telemetry
    return d


async def _say(text, message, session_id, conversation_id, used=(), cards=(), suggestions=(), telemetry=None):
    """Stream a reply the code wrote itself (no model call), remember it, and finish the turn."""
    from app.services.guardrail_service import normalize_positive_brand_advocacy
    text = normalize_positive_brand_advocacy(text)
    for c in cards:
        yield {"type": "card", "card": c}
    for piece in _chunks(text):
        yield {"type": "token", "delta": piece}
    await memory.append_history(session_id, message, text, conversation_id)
    yield _done(conversation_id, text, used, cards, suggestions, telemetry=telemetry)


async def _run_action(name: str, args: dict, ctx: dict, used: list, cards: list):
    """Run one tool on the student's behalf and record it exactly like a model-requested call."""
    result = await tools.run_tool(name, args, ctx)
    error = result.pop("_error", None)
    if error:
        log.error("tool %s failed: %s", name, error)
    log.info("tool=%s status=%s session=%s (direct)", name, result.get("status"), ctx.get("session_id"))
    used.append({"name": name, "status": result.get("status"), "is_action": name in tools.ACTION_TOOLS})
    if name in CARD_TOOLS and result.get("status") in ("calculated", "saved", "ok"):
        cards.append({"type": name, "data": result})
    return result


def _tool_events(name: str, result: dict):
    label = tools.TOOLS[name][1] if name in tools.TOOLS else "Working"
    card_ready = name in CARD_TOOLS and result.get("status") in ("calculated", "saved", "ok")
    return [{"type": "tool", "name": name, "status": "running", "label": label},
            {"type": "tool", "name": name, "status": "done", "result_status": result.get("status"),
             "result": result if card_ready else None}]


def _first_name(name: str) -> str:
    return (name or "").split()[0] if name else ""


def _cancel_text(result: dict) -> str:
    status, ref = result.get("status"), result.get("reference")
    label = "campus visit" if result.get("request_type") == "campus_visit" else "callback"
    if status == "cancelled":
        return (f"Done. I have cancelled your {label} request. The admissions team "
                f"will not contact you about it. If you change your mind, just tell me.")
    if status == "nothing_to_cancel":
        return ("There is no callback or visit request saved from this chat, so there is nothing to cancel "
                "and nobody will call you because of this chat. If you shared your number through another "
                f"form, please call the Admissions Office at {config.ADMISSIONS_PHONE} to have it removed.")
    return (f"I could not cancel your {label} request from here. Please call the "
            f"Admissions Office at {config.ADMISSIONS_PHONE}, and they will remove it.")


def _saved_text(kind: str, result: dict, preferred_time: str | None = None) -> str:
    status = result.get("status")
    if status == "saved":
        first, ref, last4 = _first_name(result.get("name")), result.get("reference"), result.get("phone_last4")
        again = "is already saved" if result.get("already_saved") else "is saved"
        if kind == "campus_visit":
            wish = f" (you mentioned {result['preferred_date']})" if result.get("preferred_date") else ""
            return (f"Thank you, {first}. I have passed your wish to visit the campus{wish} to the admissions team. "
                    f"This is not a booking: the admissions team will call you on the "
                    f"number ending {last4} to arrange the visit and confirm the day and time. You can also reach "
                    f"them directly on {config.CAMPUS_VISIT_PHONE} (call or WhatsApp). To withdraw the request, "
                    f"just say \"cancel my visit request\".")
        when = f" (preferred time: {preferred_time})" if preferred_time else ""
        return (f"Thank you, {first}. Your callback request {again}. An admissions "
                f"counsellor will call you on the number ending {last4}{when}. "
                f"To cancel it, say \"cancel the callback\"; if the number is wrong, say \"change my number\".")
    if status == "invalid":
        return result.get("problem") or "Some details were not valid. Please check and send them again."
    return (f"Sorry, I could not save your request just now. Please call the Admissions Office at "
            f"{config.ADMISSIONS_PHONE} or try again in a minute.")


def _pending_from_history(history: list):
    """If the agent's last message asked for a phone number, what was it arranging?"""
    last = next((h.get("text", "") for h in reversed(history) if h.get("role") in ("model", "assistant")), "")
    if not re.search(r"mobile|phone\s*number|10-digit|contact\s*number|your\s+number", last, re.IGNORECASE):
        return None
    is_visit = re.search(r"\bvisit\b|\btour\b", last, re.IGNORECASE) and not re.search(
        r"call\s*-?\s*back|callback|counsell?or", last, re.IGNORECASE)
    return "campus_visit" if is_visit else "callback"


def _has_other_question(message: str, name: str | None) -> bool:
    """Does the message ask something besides giving name / number / date for the request?"""
    rest = re.sub(r"(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}", " ", message)
    if name:
        rest = re.sub(re.escape(name), " ", rest, flags=re.IGNORECASE)
    return "?" in rest and len(rest.split()) >= 4


_SAVED_VERB = re.compile(
    r"\b(?:i\s+have|i've|i|we\s+have)\s+(?:now\s+|just\s+|already\s+)?(?:requested|booked|scheduled|saved|"
    r"arranged|registered|submitted|noted|shared|forwarded|passed)\b"
    r"|\b(?:has\s+been|is\s+now)\s+(?:booked|scheduled|saved|arranged|registered|submitted|confirmed|"
    r"requested|noted)\b", re.IGNORECASE)
_CONTACT_WORDS = re.compile(
    r"\b(?:call\s*-?\s*back|callback|call\s+you|contact\s+you|campus\s+visit|visit\s+request|your\s+visit|"
    r"counsell?or|admissions\s+team|your\s+request|your\s+number)\b", re.IGNORECASE)
_CANCEL_CLAIM = re.compile(
    r"\b(?:callback|call\s*-?\s*back|visit|request|booking|appointment)\b[^.!?\n]{0,60}\b(?:cancel(?:l)?ed|removed|withdrawn)\b"
    r"|\b(?:cancel(?:l)?ed|removed|withdrawn)\b[^.!?\n]{0,60}\b(?:callback|call\s*-?\s*back|your\s+(?:visit|request|booking|number|details))\b"
    r"|\b(?:will\s+not|won'?t)\s+(?:be\s+)?(?:call|contact)(?:ed|ing)?\s+you\b"
    r"|\bno\s+one\s+will\s+(?:call|contact)\s+you\b", re.IGNORECASE)
_NEGATED = re.compile(r"\b(?:could\s*n[o']?t|cannot|can'?t|unable|not\s+able|nothing|not\s+been|was\s*n[o']?t|"
                      r"is\s*n[o']?t|no\s+(?:callback|request|visit))\b", re.IGNORECASE)
_CANCEL_ASK = re.compile(r"\b(?:cancel|remove|delete|stop|don'?t|dont|do\s+not|no\s+need|never)\b", re.IGNORECASE)
_NOT_ABOUT_CONTACT = re.compile(r"\b(?:admission|seat|course|fee|fees|refund|hostel|exam)\b", re.IGNORECASE)


def _claims_saved(text: str) -> bool:
    return any(_SAVED_VERB.search(s) and _CONTACT_WORDS.search(s) for s in re.split(r"(?<=[.!?\n])\s*", text))


def _claims_cancelled(text: str) -> bool:
    return any(_CANCEL_CLAIM.search(s) and not _NEGATED.search(s) for s in re.split(r"(?<=[.!?\n])\s*", text))


_FEE_WORDS = re.compile(r"\b(?:fee|fees|fess|feez|tuition|cost|schol\w*|waiver|how\s+much|per\s+sem)\b", re.IGNORECASE)


def _offline_fee_reply(message: str, ctx: dict, fee: dict | None = None):
    """A fee answer straight from the fee file, for when the model cannot be reached."""
    if fee and fee.get("status") == "ok":
        return _offline_fee_text(fee), fee
    if not _FEE_WORDS.search(message):
        return None
    profile = ctx.get("profile") or {}
    program = message if fees.find_program(message) else profile.get("program_interest")
    if not program:
        return None
    m = re.search(r"(?<!\d)(\d{2}(?:\.\d+)?)\s*(?:%|percent)", message, re.IGNORECASE)
    percent = float(m.group(1)) if m else profile.get("percent")
    m = re.search(r"\b(?:eapcet|eamcet)\D{0,20}(\d{1,6})\b|\brank\D{0,10}(\d{1,6})\b", message, re.IGNORECASE)
    rank = int(m.group(1) or m.group(2)) if m else profile.get("eapcet_rank")
    board = "cbse" if re.search(r"\b(?:cbse|icse)\b", message, re.IGNORECASE) else profile.get("board") or "state_board"
    fee = fees.calculate_fee(program=program, percent=percent, board=board, eapcet_rank=rank)
    if fee.get("status") != "ok":
        return None
    return _offline_fee_text(fee), fee


def _offline_fee_text(fee: dict) -> str:
    lines = [f"Here is the official {fee['academic_year']} fee for **{fee['program']}**, as per the Admissions Office:", ""]
    if fee.get("scholarship_percent"):
        lines.append(f"- Tuition: {fee['tuition_first_year']} per year. With your {fee['scholarship_percent']}% merit "
                     f"scholarship ({fee['scholarship_basis']}) it is **{fee['tuition_first_year_after_scholarship']}** per year.")
    else:
        lines.append(f"- Tuition: **{fee['tuition_first_year']}** per year.")
    lines += [f"- Semester 1 payable: **{fee['sem1_total_payable']}** (includes the one-time enrollment fee).",
              f"- Each regular semester: **{fee['total_per_semester']}**.", "",
              "Hostel is optional and charged separately."
              + (" The scholarship is subject to marksheet verification." if fee.get("scholarship_percent") else ""),
              f"Many students are chatting right now, so this is a quick answer from the fee table. For anything "
              f"else, please ask again in a minute or call {config.ADMISSIONS_PHONE}."]
    return "\n".join(lines)


def format_counsellor_assessment(fee_res: dict, details: dict) -> str:
    """Formats structured scholarship assessment and fee details following admission counsellor standards."""
    board_lbl = details.get("board_label") or details.get("board") or "10+2 / Intermediate"
    stage_lbl = details.get("stage_label") or ""
    qual_str = f"{board_lbl} ({stage_lbl})" if stage_lbl else board_lbl

    raw_m = details.get("raw_marks")
    max_m = details.get("max_marks")
    pct = details.get("percent")
    if raw_m and max_m and max_m > 100:
        score_str = f"{int(raw_m) if raw_m == int(raw_m) else raw_m}/{max_m} ({pct}%)"
    elif pct:
        score_str = f"{pct}%"
    elif details.get("ib_score"):
        score_str = f"{details['ib_score']} points (out of 45)"
    else:
        score_str = "Standard Eligibility"

    route_lbl = details.get("route_label") or "Direct Merit / 10+2 Marks"
    if details.get("eapcet_rank"):
        route_str = f"{route_lbl} (Rank: {details['eapcet_rank']:,})"
    elif details.get("jee_percentile"):
        route_str = f"{route_lbl} ({details['jee_percentile']}%ile)"
    else:
        route_str = route_lbl

    prog_key = fee_res.get("program_key") or details.get("program") or "btech_cse"
    prog_name = fees.clean_program_name(
        prog_key,
        specialization=details.get("specialization"),
        user_text=details.get("program_raw") or details.get("user_query") or fee_res.get("program") or details.get("program_name"),
    )

    pct_waiver = fee_res.get("scholarship_percent", 0)
    matching_cat = fee_res.get("scholarship_basis_text") or (
        f"{pct_waiver}% Merit Scholarship" if pct_waiver > 0 else "Standard Fee / Minimum Eligibility"
    )

    orig_tuition = fee_res.get("tuition_first_year", "₹3,40,000")
    num_match = re.search(r"[\d,]+", orig_tuition.replace("₹", ""))
    if num_match:
        orig_annual_int = int(num_match.group(0).replace(",", ""))
        orig_sem = f"₹{orig_annual_int // 2:,}"
    else:
        orig_sem = "₹1,70,000"

    savings = fee_res.get("saving_first_year", "₹0")
    net_tuition = fee_res.get("tuition_first_year_after_scholarship", orig_tuition)
    per_sem_net = fee_res.get("per_semester_after_scholarship", orig_sem)
    sem1_payable = fee_res.get("sem1_total_payable", per_sem_net)

    lines = []
    if details.get("re_query"):
        lines.append("Thanks! I already have your academic details. Let's continue with your scholarship assessment.\n")

    lines.append("### Your Scholarship Assessment")
    lines.append(f"• **Academic Qualification**: {qual_str}")
    lines.append(f"• **Academic Score**: {score_str}")
    lines.append(f"• **Admission Route**: {route_str}")
    lines.append(f"• **Selected Programme**: {prog_name}")
    lines.append(f"• **Matching Scholarship Category**: {matching_cat}\n")

    lines.append("### Your Fee Details")
    lines.append(f"• **Original Tuition Fee**: {orig_tuition} per year ({orig_sem} per semester)")
    if pct_waiver > 0:
        lines.append(f"• **Applicable Scholarship**: **{pct_waiver}% Tuition Waiver**")
        lines.append(f"• **Scholarship Savings**: **{savings} per year**")
    else:
        lines.append("• **Applicable Scholarship**: **0% (Standard Fee)**")
    lines.append(f"• **Remaining Annual Tuition**: **{net_tuition} per year** ({per_sem_net} per semester)")
    lines.append(f"• **First Semester Payable**: **{sem1_payable}**")

    if details.get("is_projected"):
        lines.append("\n> [!NOTE]\n"
                     f"> **Preliminary Projection**: Based on your {stage_lbl or 'first-year'} academic score, "
                     "this is an estimated scholarship. Final scholarship will be confirmed upon submission of "
                     "complete 10+2 academic transcripts and entrance scorecard.")

    lines.append(f"\nYou can also verify your scholarship on our official calculator: {fee_intake.FEE_PORTAL_URL}")
    return "\n".join(lines)


_SCORE_WORDS = r"(?:eapcet|eamcet|emcet|emact|eamect|eamcent)"
_FEE_KEYS = ("program", "academic_year", "scholarship_percent", "scholarship_basis_text", "scores_considered",
             "tuition_first_year", "tuition_first_year_after_scholarship", "per_semester_after_scholarship",
             "one_time_enrollment_fee", "other_yearly_fees", "hostel", "hostel_options_per_year",
             "sem1_total_payable", "total_per_semester", "first_year_total_payable", "yearly_increase",
             "next_scholarship_slab", "notes")


def _fee_args_from_message(message: str, profile: dict):
    """If the message is a plain fee / scholarship question the code can work out by itself,
    return the calculate_fee arguments; otherwise None (the model decides)."""
    low = message.lower()
    if not _FEE_WORDS.search(message) or re.search(r"\b(?:vs|versus|compare|difference|cheaper|concession)\b", low):
        return None
    in_message = fees.find_program(message)
    program = in_message or profile.get("program_interest")
    if not program or not fees.find_program(str(program)):
        return None
    args = {"program": in_message or str(program)}
    m = re.search(r"(?<![\d.])(\d{2}(?:\.\d+)?)\s*(?:%|percent)", low)
    marks = re.search(r"(?<!\d)(\d{3,4})\s*(?:marks|/\s*1000|out\s+of\s+1000)", low)
    if m and float(m.group(1)) <= 100:
        args["percent"] = float(m.group(1))
    elif marks and int(marks.group(1)) <= 1000:
        args["percent"] = round(int(marks.group(1)) / 10, 2)
    m = re.search(rf"\b{_SCORE_WORDS}\b\D{{0,25}}(\d[\d,]{{0,6}})\b|\brank\D{{0,12}}(\d[\d,]{{0,6}})\b"
                  rf"|(\d[\d,]{{0,6}})\s*(?:rank|in\s+{_SCORE_WORDS})\b", low)
    if m:
        args["eapcet_rank"] = int((m.group(1) or m.group(2) or m.group(3)).replace(",", ""))
    m = re.search(r"\bjee\D{0,25}(\d{1,2}(?:\.\d+)?)\b|(\d{1,2}(?:\.\d+)?)\s*(?:percentile|%ile)", low)
    if m:
        args["jee_percentile"] = float(m.group(1) or m.group(2))
    if re.search(r"\b(?:cbse|icse)\b", low):
        args["board"] = "cbse"
    if "hostel" in low:
        if re.search(r"\bnon[\s-]?ac\b", low):
            kind = "non_ac"
        elif re.search(r"\bac\b|a/c|air[\s-]?condition", low):
            kind = "ac"
        else:
            return None  # which hostel? let the model ask or explain the options
        sharing = "3" if re.search(r"(?<!\d)3[\s-]?(?:shar|bed|person|member)", low) else "4"
        args["hostel"] = f"{kind}_{sharing}"
    return args


def _has_word(text: str, *words: str) -> bool:
    for w in words:
        if re.search(r"\b" + re.escape(w) + r"\b", text):
            return True
    return False


def _contextual_query(
    message: str,
    history: list | None = None,
    active_topic: str | None = None,
    active_program: str | None = None,
) -> str:
    """Build a search query enriched with conversational context for follow-up questions."""
    low = (message or "").lower().strip()
    words = low.split()

    if len(words) > 7 and not re.search(r"\b(?:it|this|that|these|those)\b", low):
        return message

    additions = []
    topic = active_topic

    is_other_fee_inquiry = bool(re.search(
        r"\b(?:other\s+fees?|other\s+academic(?:\s*/\s*university|\s+university)?\s+charges?|other\s+charges?|annual\s+charges?|"
        r"university\s+charges?|additional\s+fees?|additional\s+charges?|enrolment\s+fee|enrollment\s+fee|application\s+form\s+fee|"
        r"specialisation\s+fee|specialization\s+fee|phd\s+fee|"
        r"fees?\s+(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee)|"
        r"(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee))\b",
        low,
    ))


    if is_other_fee_inquiry:
        additions.append("Other fees and charges enrolment fee application fee other academic university charges examination fee specialisation fee phd fee")
    elif topic == "hostel" or _has_word(low, "hostel", "mess", "curfew", "warden", "ac", "non-ac", "sharing", "double", "table", "bed", "in-time"):
        if not _has_word(low, "hostel", "hostels"):
            additions.append("hostel accommodation")
        if _has_word(low, "double", "table"):
            additions.append("rooms sharing 3-sharing 4-sharing categories")
        if _has_word(low, "mess", "food", "dining", "meal", "included"):
            additions.append("mess dining Mega Dining Hall food included fee")
        if _has_word(low, "ac", "non-ac", "air"):
            additions.append("AC Non-AC room amenities power backup")
        if _has_word(low, "fee", "cost", "annual", "charge", "rent"):
            additions.append("hostel fees per year caution deposit laundry")

    elif topic == "placements" or _has_word(low, "placement", "package", "guarantee", "guaranteed", "lpa", "jobs"):
        if not _has_word(low, "placement", "placements"):
            additions.append("placements assistance career")
        if _has_word(low, "guarantee", "guaranteed", "98%", "100%"):
            additions.append("100% placement assistance policy readiness CSSP")

    elif topic in ("btech", "programs") or _has_word(low, "btech", "b.tech", "branch", "branches", "stream", "engineering", "ai"):
        if not _has_word(low, "b.tech", "btech", "engineering"):
            additions.append("B.Tech engineering programs branches")
        if _has_word(low, "ai"):
            additions.append("Artificial Intelligence AI CSE AI Robotics")

    elif topic in ("fee", "scholarship") or _has_word(low, "fee", "fees", "scholarship", "scholarships", "waiver", "concession", "eligible", "eligibility", "60%", "85%", "90%"):
        if _has_word(low, "scholarship", "scholarships", "concession", "waiver", "discount"):
            additions.append("merit scholarships fee concessions slabs intermediate cbse jee eapcet")
        if active_program:
            additions.append(str(active_program))
        if _has_word(low, "eligible", "eligibility", "cutoff", "minimum"):
            additions.append("eligibility criteria minimum marks")

    if additions:
        return message + " " + " ".join(additions)
    return message



def _handbook_context(query: str) -> str:
    """Handbook passages for this query, found by keyword search (no AI call)."""
    try:
        found = knowledge.search(query, k=3, min_score=2.5)
    except Exception:
        return ""
    if not found:
        return ""
    top = found[0]["score"]
    parts = [f"[{f['title'].split(' > ')[-1]}]\n{f['text'][:750]}" for f in found if f["score"] >= 0.50 * top]
    return "\n\n".join(parts)


_shown_offline_titles: dict = {}


def _offline_knowledge_reply(message: str, session_id: str = ""):
    """The most relevant handbook passage, shown as it is, with rotation across turns for when the model cannot be reached."""
    try:
        found = knowledge.search(message, k=4, min_score=6.0)
    except Exception:
        found = []
    if not found:
        return None
    recent = _shown_offline_titles.setdefault(session_id, [])
    selected = found[0]
    for c in found:
        t = c.get("title", "")
        if t not in recent:
            selected = c
            break
    recent.append(selected.get("title", ""))
    if len(recent) > 10:
        recent.pop(0)

    text = re.sub(r"\[FACT-ID:[^\]]*\]\s*|\[STATUS:[^\]]*\]\s*|\[SOURCE:[^\]]*\]\s*", "", selected["text"]).strip()
    if len(text) > 900:
        text = text[:900].rsplit("\n", 1)[0] + "\n..."
    return (f"I cannot reach my AI model right now (the free limit for today has been used), so here is the "
            f"matching part of the SR University handbook, **{selected['title'].split(' > ')[-1]}**:\n\n{text}\n\n"
            f"I can still calculate fees and scholarships, find faculty profiles and arrange a callback. "
            f"For anything else, please call the Admissions Office at {config.ADMISSIONS_PHONE}.")


_LIMIT_REPLY_OPTIONS = [
    (f"Many students are using SRU Buddy right now and the free AI limit has been reached, so I cannot "
     f"answer that question at the moment. I can still do these without it: calculate a fee or "
     f"scholarship (for example \"CSE fee with 85%\"), arrange a counsellor callback (\"call me\"), "
     f"find a faculty member, or plan a campus visit ({config.CAMPUS_VISIT_PHONE}). You can also call the Admissions Office at {config.ADMISSIONS_PHONE}."),
    (f"SRU Buddy is receiving high student traffic right now and the free AI limit has been reached momentarily. "
     f"However, our fee & scholarship calculator (e.g. \"CSE fee with 85%\"), counsellor callbacks (\"call me\"), "
     f"faculty search, and campus visit planning ({config.CAMPUS_VISIT_PHONE}) still work without it. You can also call Admissions at {config.ADMISSIONS_PHONE}."),
    (f"The free AI limit has been reached due to heavy traffic. I can still calculate your fees and scholarships, "
     f"arrange a counsellor callback (\"call me\"), or help plan a campus visit ({config.CAMPUS_VISIT_PHONE}). For admissions support, please call "
     f"the Admissions Office at {config.ADMISSIONS_PHONE}."),
]
_LIMIT_REPLY = _LIMIT_REPLY_OPTIONS[0]


def get_limit_reply(seed_str: str = "") -> str:
    if not seed_str:
        return _LIMIT_REPLY
    import hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return _LIMIT_REPLY_OPTIONS[h % len(_LIMIT_REPLY_OPTIONS)]

_GREETING_ASK_NAME = [
    "Hello! Welcome to SR University. Before we get started, may I know your name?",
    "Hello and welcome to SR University! Who do I have the pleasure of speaking with today?",
    "Hello there! Great to connect with you. Before we dive into SR University, may I know your name?",
    "Hello! Welcome to SR University! May I know your name so I know who I'm chatting with?",
    "Hello! Glad you reached out to SR University. What's your name before we get started?",
    "Hello! Welcome to SR University. What should I call you?",
]

_GREETING_WITH_NAME = [
    "Hello {name}! What would you like to explore about SR University today?",
    "Hey {name}! Great to see you. How can I help you with SR University today?",
    "Welcome back, {name}! What can I look up for you regarding SRU today?",
    "Hi {name}! What questions can I answer for you about SR University?",
    "Hey {name}! Glad to connect again. What's on your mind today regarding SRU?",
]

_NAME_GIVEN_REPLIES = [
    "Hi {name}! Great to connect with you. What would you like to explore about SR University?",
    "Nice to meet you, {name}! How can I assist you with SR University today?",
    "Welcome, {name}! Glad to have you here. What would you like to know about our programs or campus?",
    "Pleasure meeting you, {name}! What's on your mind regarding SR University?",
]

_QUESTION_ACK_FEE = [
    "Absolutely! I can help you with the B.Tech fee details. First, may I know your name?",
    "I'd be glad to walk you through the fee structure and scholarship slabs! Before we start, may I know your name?",
    "Happy to calculate your fee and scholarship details! First, what should I call you?",
]

_QUESTION_ACK_CAMPUS = [
    "I'd love to share all about the campus and facilities! Before we get into it, may I have your name?",
    "Happy to help with campus visit and hostel details! First, may I know your name?",
    "I can certainly tell you about campus life, hostels, and lab facilities. First, may I know your name?",
]

_QUESTION_ACK_SRU = [
    "I'd love to tell you all about SR University! Before we get started, may I know your name?",
    "Great to connect! I can share everything about SR University with you. First, who do I have the pleasure of speaking with?",
    "Happy to guide you through everything SR University has to offer! Before we begin, may I know your name?",
]

_QUESTION_ACK_GENERAL = [
    "I'd be happy to help you with that! Before we dive in, may I know your name?",
    "I can certainly guide you through that. First, may I know your name?",
    "Great question! I'd love to answer that for you. Before we get started, may I know your name?",
]

_SMALL_TALK_THANKS = [
    "You're welcome{name}! If you have more questions about SR University, just ask.",
    "Happy to help and you're always welcome{name}! Let me know if you'd like to explore anything else about courses, campus, or admissions.",
    "You're welcome{name}! I'm right here if you want to know more about SR University.",
    "You're welcome{name}! Glad I could help! Feel free to ask if there's anything else you're curious about.",
]

_SMALL_TALK_HOW_ARE_YOU = [
    "I'm doing well, thank you{name}! Ready to help you explore everything about SR University admissions. What would you like to know?",
    "I'm doing well and feeling great, thanks for asking{name}! Excited to assist you with SR University admissions and programs. What would you like to know?",
    "I'm doing well, thank you{name}! All good here and ready to answer any questions about SRU courses, fees, scholarships, or campus life. How can I help?",
]

_SMALL_TALK_BYE = [
    f"Goodbye{{name}}! Wishing you the very best in your academic journey. You can reach out here anytime or contact the Admissions Office on {config.ADMISSIONS_PHONE}.",
    "Take care{name}! Feel free to come back whenever you have questions. All the best for your future!",
    "Bye{name}! Have a wonderful day ahead. Don't hesitate to return if you need more info on SR University!",
]

_SMALL_TALK_WHO_ARE_YOU = [
    f"I'm SRU Buddy, the AI admissions assistant of SR University, Warangal. I can help you calculate fees and scholarships, check course eligibility, learn about faculty and campus life, and connect with our admissions counsellors. What would you like to know?",
    f"I'm SRU Buddy, the AI admissions assistant for SR University! Whether you need fee breakdowns, scholarship calculations, placement stats, or campus tour guidance, I'm here to help. What shall we explore?",
]


def _select_variation(options: list[str], seed_str: str) -> str:
    import hashlib
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return options[h % len(options)]


def _ack_question_for_name(question: str, seed: str) -> str:
    q = question.lower()
    if any(k in q for k in ("fee", "fees", "scholarship", "cost", "tuition", "waiver")):
        return _select_variation(_QUESTION_ACK_FEE, seed)
    if any(k in q for k in ("visit", "campus", "hostel", "room", "mess", "food", "tour")):
        return _select_variation(_QUESTION_ACK_CAMPUS, seed)
    if any(k in q for k in ("about sru", "about sr university", "tell me about sru", "tell me about sr university", "rank", "ranking", "placement", "nirf")):
        return _select_variation(_QUESTION_ACK_SRU, seed)
    return _select_variation(_QUESTION_ACK_GENERAL, seed)


def _is_first_interaction_name_query(message: str) -> bool:
    msg = (message or "").strip().lower()
    if any(k in msg for k in ("hostel", "mess", "food")):
        return False
    if any(k in msg for k in ("fee", "fees", "scholarship", "tuition", "cost", "waiver")):
        return True
    if any(k in msg for k in ("about sru", "about sr university", "tell me about sru", "tell me about sr university",
                              "what is sru", "what is sr university", "know about sru", "know about sr university")):
        return True
    if any(k in msg for k in ("how to apply", "how to join sru", "join sr university",
                              "courses in sru", "programs in sru", "b.tech in sru", "btech in sru")):
        return True
    return False


# Static response templates and catalogues are housed in responses.py
from .responses import (
    _SMALL_TALK_CHIPS,
    _PLACEMENT_ASSISTANCE_CHIPS,
    _PLACEMENT_ASSISTANCE_RESPONSES,
    _SPECIAL_CONCESSIONS_TEXT,
    _NEXT_GEN_TECH_TEXT,
    _FEE_TREE_TEXT,
    _BTECH_TREE_TEXT,
    _BTECH_CSE_FEE_TEXT,
    get_btech_cse_fee_text,
    _BTECH_AI_ROBOTICS_FEE_TEXT,
    _BTECH_ECE_FEE_TEXT,
    _BTECH_CORE_FEE_TEXT,
    _MANAGEMENT_FEE_TEXT,
    _AGRICULTURE_FEE_TEXT,
    _COMP_APP_FEE_TEXT,
    _DESIGN_FEE_TEXT,
    _ALL_PROGRAMS_TEXT,
    _HOSTEL_INFO_TEXT,
    _HOSTEL_INFO_CHIPS,
    _HOSTEL_MESS_TEXT,
    _HOSTEL_MESS_CHIPS,
    _HOSTEL_CURFEW_RULES_TEXT,
    _HOSTEL_CURFEW_CHIPS,
    _HOSTEL_SAFETY_TEXT,
    _HOSTEL_SAFETY_CHIPS,
    _HOSTEL_FEE_TEXT,
    _HOSTEL_FEE_CHIPS,
    _COMBINED_HOSTEL_FEE_TEXT,
    _COMBINED_HOSTEL_FEE_CHIPS,
    _CAMPUS_CANTEEN_TEXT,
    _CAMPUS_CANTEEN_CHIPS,
    _ACADEMIC_EVALUATION_TEXT,
    _ACADEMIC_EVALUATION_CHIPS,
    _LAB_FACILITIES_TEXT,
    _LAB_FACILITIES_CHIPS,
    _ADMISSION_GUARANTEE_TEXT,
    _ADMISSION_GUARANTEE_CHIPS,
    _FUTURE_YEAR_FEE_TEXT,
    _FUTURE_YEAR_FEE_CHIPS,
)

_PLACEMENT_ASSISTANCE_CHIPS = ["Top Recruiters & Packages", "Startup Incubator (SRiX)", "Placement Eligibility Rules", "Book a Campus Visit"]

_PLACEMENT_ASSISTANCE_RESPONSES = [
    """At **SR University**, we provide **100% placement assistance and career readiness support** to all eligible students across our undergraduate and postgraduate programs.

While no university can unconditionally guarantee job offers—as final placement selections depend entirely on an individual student's academic standing, technical competence, interview clearance, and recruiter hiring criteria—SRU provides an end-to-end launchpad to prepare you for industry success.

---

### 🌟 How SRU Empowers Your Career & Ambitions:
1. **💼 100% Placement & Career Support**:
   - Structured preparation via the **Center for Student Services and Placements (CSSP)** and **Career Guidance Cell (CGC)**: competitive coding, full-stack assessments, aptitude coaching, and mock technical interviews.
   - **3,500+ internships** completed with top stipends reaching up to ₹1.25 Lakh/month.
   - Dedicated on-campus recruitment drives featuring **150+ marquee companies** (including Microsoft, Amazon, ServiceNow, Salesforce, PayPal, Cisco, TCS, Cognizant, Accenture, and Capgemini).

2. **🚀 Explore Startups & Entrepreneurship (SRiX)**:
   - For students passionate about entrepreneurship or building their own ventures, SRU houses **SRiX (SR Innovation Exchange)**—a premier, DST-supported technology business incubator on campus.
   - Students gain access to **maker spaces, rapid prototyping labs, expert mentorship from venture leaders**, and **seed grant funding from a ₹76+ Crore startup ecosystem** with 171+ incubated startups.

3. **📊 Verified Placement Track Record**:
   - **1,300+ Total Job Offers** secured by students.
   - **Average Package**: ~**6 to 6.5 LPA** across graduating engineering cohorts.
   - **Top Milestone Packages**:
     - 💎 **₹51.00 LPA** — Microsoft (*Batch 2025*)
     - 💎 **₹49.30 LPA** — ServiceNow (*Batch 2027*)
     - 💎 **₹46.38 LPA** — Amazon (*Batch 2026*)
     - 💎 **₹44.00 LPA** — Salesforce & ServiceNow (*Batch 2025*)

> [!TIP]
> **Our Commitment**: We provide 100% institutional support, premium recruiters, and incubation backing—your dedication, skills, and preparation turn these opportunities into dream careers!""",

    """**SR University provides 100% placement assistance** and an end-to-end career launchpad for every eligible student.

Because final placement outcomes depend on individual student dedication, technical competence, academic consistency (CGPA and zero active backlogs), and company interview evaluations, placements cannot be unconditionally guaranteed by any institution. However, SRU equips every student with industry-grade skills, corporate drives, and entrepreneurial pathways.

---

### 💼 Comprehensive Career & Startup Ecosystem:
- **🎯 100% Placement Guidance**: Tailored career counselling, full-stack coding assessments, and intensive interview preparation conducted by the **Center for Student Services and Placements (CSSP)** with **150+ hiring partners**.
- **🚀 Passionate About Startups?**: If you want to pursue your own venture, SRU's on-campus incubator **SRiX (SR Innovation Exchange)**—recognized and supported by the Department of Science and Technology (DST)—provides seed funding, incubation labs, prototyping resources, and angel investor networking.
- **🛠️ Industry Internships**: Over **3,500+ internships** completed with monthly stipends reaching up to ₹1.25 Lakh/month.

### 📈 Verified Placement Benchmarks:
- **Average Package**: ~**6 LPA** (with university portals citing 6.5 LPA across engineering streams).
- **Highest Packages**: **₹51 LPA** at Microsoft, **₹49.30 LPA** at ServiceNow, and **₹46.38 LPA** at Amazon.
- **Over 1,300+ Placement Offers** spanning global IT giants, product companies, and core engineering firms.""",

    """At **SR University**, our core commitment is delivering **100% placement assistance, rigorous skill development, and diverse career pathways** for every student.

While final job offers naturally depend on each student's academic performance, technical skills, and interview success—meaning no higher education institution can give an unconditional job guarantee—SRU leaves no stone unturned in ensuring you are career-ready:

---

- 🎯 **100% Placement Assistance**: Rigorous coaching in data structures, system design, aptitude, and soft skills from the 2nd year onwards, connecting students directly to **150+ national and multinational recruiters**.
- 🚀 **Explore Startups & Innovation**: Have an entrepreneurial mindset? SRU’s **SRiX (SR Innovation Exchange)** incubator offers world-class maker spaces, seed capital, and mentorship to help students launch and scale their own startup ventures.
- 💼 **Proven Placement Record**: Over **1,300+ job offers** with an average package of **6 to 6.5 LPA**. Top offers include **₹51 LPA (Microsoft)**, **₹49.30 LPA (ServiceNow)**, and **₹46.38 LPA (Amazon)**.

Whether your aspiration is securing a dream role at a global technology leader or launching a disruptive startup, SR University provides the 100% mentorship, infrastructure, and opportunities to make it happen!""",

    """**SR University assures 100% placement assistance and career guidance** to help every graduate succeed in the professional world.

Rather than a passive "guarantee", SRU actively partners with you: final placement offers depend on your skills, consistency, and interview performance, while the university provides the entire launchpad—from industry certifications to campus drives.

---

### 🌟 What SRU Offers Every Student:
1. **100% Placement Assistance**: Dedicated recruitment drives with **150+ top companies** (Microsoft, Amazon, ServiceNow, Salesforce, Accenture, Cognizant, TCS), comprehensive mock interviews, and 3,500+ internships.
2. **Startup & Incubation Support (SRiX)**: Want to build your own company instead of a traditional corporate job? SRU's on-campus incubator **SRiX** offers seed funding, maker spaces, and startup mentoring to turn innovative ideas into commercial realities.
3. **Stellar Placement Records**: 
   - **Average Salary**: ~**6 – 6.5 LPA** across graduating engineering disciplines.
   - **Highest Packages**: **₹51 LPA** (Microsoft), **₹49.30 LPA** (ServiceNow), and **₹46.38 LPA** (Amazon).
   - **1,300+ Placement Offers** across global tech, fintech, core engineering, and consulting firms."""
]

_SPECIAL_CONCESSIONS_TEXT = """### 🎖️ Special Category Fee Concessions (2027–28)

At SR University, special category tuition fee concessions are offered annually to eligible students across 19 categories. These concessions are applied directly to your annual tuition fee upon verification of valid certificates by the Admissions Office:

| Category / Eligibility | Annual Concession |
| :--- | :--- |
| **Students who have lost both parents (Orphans)** | **₹50,000 / year** |
| **International-level sports achievers** | **₹50,000 / year** |
| **Children of regular SR University employees** | **₹50,000 / year** |
| **Students with 50% or above disability (Differently Abled)** | **₹20,000 / year** |
| **Children of Defence personnel, CRPF personnel & Martyrs** | **₹15,000 / year** |
| **Children of State Police personnel** | **₹15,000 / year** |
| **Only Girl Child from Telangana** | **₹15,000 / year** |
| **Girl students from states other than Telangana** | **₹15,000 / year** |
| **Students with a single living parent / Divorced parents** | **₹15,000 / year** |
| **Sibling enrolled at SR University (concurrent 2027–28)** | **₹15,000 / year** |
| **SRU Alumni, their children and siblings** | **₹15,000 / year** |
| **Students of SR Junior College** | **₹15,000 / year** |
| **NCC 'C' Certificate holders** | **₹15,000 / year** |
| **National-level sports achievers** | **₹15,000 / year** |
| **Children of Padma / Gallantry awardees & J&K migrant families** | **₹15,000 / year** |
| **Non-Local students (outside Telangana & Andhra Pradesh)** | **₹15,000 / year** |
| **Students from Andhra Pradesh** | **₹15,000 / year** |
| **Lateral Entry students** | **₹15,000 / year** |
| **International students** | **₹15,000 / year** |

> [!NOTE]
> - Concessions are applicable per academic year on tuition fees.
> - Required certificates and documentation must be submitted directly to the Admissions Office (833 100 3030 / info@sru.edu.in) during admission counselling."""

_NEXT_GEN_TECH_TEXT = """### 🚀 Next-Gen Technology Programs at SR University

SR University has pioneered futuristic, multidisciplinary undergraduate engineering programs designed to prepare students for the next industrial revolution:

---

#### 1. 🤖 B.Tech in Artificial Intelligence & Robotics
- **Focus**: Autonomous mobile robotics, ROS (Robot Operating System), computer vision, sensor fusion, cyber-physical systems, and robotic manipulation.
- **Key Labs**: Advanced Robotics Arena, Makerspace, and Embedded Systems Lab.
- **Tuition**: ₹4,00,000 / year (₹2,00,000 / semester) | Merit scholarships up to 40% available.

---

#### 2. 🌾 B.Tech CSE — AI & Precision Agriculture
- **Focus**: Integrating machine learning, computer vision, IoT sensing, and drone analytics with modern agricultural science to create high-yield, climate-smart farming solutions.
- **Unique Advantage**: Jointly offered with SRU’s **ICAR-accredited School of Agriculture** with hands-on learning on experiential research farms.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

#### 3. 🦾 B.Tech CSE — Robotics & Automation
- **Focus**: Industrial automation, PLC/SCADA programming, kinematics, machine kinematics, robotic arm control, and smart Industry 4.0 manufacturing.
- **Career Pathways**: Automation engineer, robotics software engineer, mechatronics specialist in automotive, aerospace, and defense sectors.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

#### 4. ⚛️ B.Tech CSE — Quantum AI
- **Focus**: Quantum computing algorithms, Qiskit framework, quantum neural networks, quantum annealing, and post-quantum cryptography.
- **Cutting Edge**: Equips students for future high-performance computing, drug discovery simulations, and next-generation cybersecurity.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

> [!TIP]
> All programs feature practical prototyping at **SRiX (DST-supported Technology Business Incubator)** with ₹76+ Cr in funding and 171+ startups.

*Would you like to see the fee breakdown, eligibility cutoffs, or calculate your scholarship for any of these programs?*"""

_FEE_TREE_TEXT = """### 💰 SR University Fee Structure (2027–28)

Here is the **Program Category Directory**. Select an academic school below or tap a category to explore its branch fees and scholarship slabs:

• **📘 B.Tech Engineering** — CSE & Allied, AI & Robotics, ECE, Core Engineering
• **🏢 Management & Commerce** — BBA (General & Analytics), MBA (Finance, Marketing, HR, Analytics)
• **🌾 Agriculture (ICAR-Accredited)** — B.Sc. (Hons) Agriculture
• **💻 Computer Applications & IT** — BCA (Hons), B.Sc Computer Science, MCA
• **🎨 Design** — B.Des (Interior & Fashion Design)
• **🔬 Postgraduate & Sciences** — M.Tech, M.Sc (Computer Science / Agriculture)

👉 **Which program category would you like to see the fee structure for?** Tap an option below or type your branch:"""

_BTECH_TREE_TEXT = """### 📘 B.Tech Fee Structure (2027–28)

For **B.Tech (Bachelor of Technology)**, SR University offers several engineering streams. Which branch would you like to view the detailed fee structure for?

• **1. B.Tech CSE & Allied** (AIML, Data Science, Cyber, Quantum AI) — **₹3,40,000 / yr** (₹1,70,000 / sem)
• **2. B.Tech AI & Robotics** — **₹4,00,000 / yr** (₹2,00,000 / sem)
• **3. B.Tech ECE** (VLSI & Embedded) — **₹2,70,000 / yr** (₹1,35,000 / sem)
• **4. B.Tech Core** (Biotech, Civil, EEE, Mech, Food Tech) — **₹2,00,000 / yr** (₹1,00,000 / sem)

*All B.Tech programs offer **10% to 40% Merit Scholarships** based on your 10+2 marks or EAPCET rank.*

👉 **Select a branch below to see the complete semester breakdown:**"""

_BTECH_CSE_FEE_TEXT = """### 💻 B.Tech CSE & Allied Streams — Fee Structure (2027–28)

Official fee schedule for **B.Tech Computer Science & Engineering** and its specialized streams (AIML, Data Science, Cyber Security, Quantum AI, Precision Agriculture):

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,70,000** | **₹3,40,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | ₹15,000 other + ₹5,000 exam |
| **Semester 1 Total (Day-Scholar)** | **₹1,85,000** | — | Includes enrollment + exam/other |
| **Regular Semester Total** | **₹1,80,000** | **₹3,60,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Inter ≥ 98% / CBSE ≥ 95% / EAPCET 1–2000 → **₹2,04,000 / yr** (Save ₹1,36,000)
- **30% Waiver**: Inter 92–97.9% / CBSE 90–94.9% / EAPCET 2001–8000 → **₹2,38,000 / yr** (Save ₹1,02,000)
- **25% Waiver**: Inter 80–91.9% / CBSE 80–89.9% / EAPCET 8001–20000 → **₹2,55,000 / yr** (Save ₹85,000)
- **20% Waiver**: Inter 70–79.9% → **₹2,72,000 / yr** (Save ₹68,000)
- **10%–15% Waiver**: Inter 60–69.9% → **₹2,89,000 – ₹3,06,000 / yr**

> [!NOTE]
> - Annual tuition escalation: ₹9,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year (includes 4 meals daily, AC/Non-AC options, Wi-Fi & laundry)."""

_BTECH_AI_ROBOTICS_FEE_TEXT = """### 🤖 B.Tech in Artificial Intelligence & Robotics — Fee Structure (2027–28)

Official fee schedule for the specialized **B.Tech in Artificial Intelligence & Robotics**:

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹2,00,000** | **₹4,00,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹2,15,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹2,10,000** | **₹4,20,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹2,40,000 / yr** (Save ₹1,60,000/yr)
- **30% Waiver**: Net Tuition **₹2,80,000 / yr** (Save ₹1,20,000/yr)
- **25% Waiver**: Net Tuition **₹3,00,000 / yr** (Save ₹1,00,000/yr)
- **20% Waiver**: Net Tuition **₹3,20,000 / yr** (Save ₹80,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹12,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_BTECH_ECE_FEE_TEXT = """### ⚡ B.Tech Electronics & Communication (ECE) — Fee Structure (2027–28)

Official fee schedule for **B.Tech ECE** (Specializations in VLSI, Embedded Systems, and Robotics):

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,35,000** | **₹2,70,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹1,50,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹1,45,000** | **₹2,90,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹1,62,000 / yr** (Save ₹1,08,000/yr)
- **30% Waiver**: Net Tuition **₹1,89,000 / yr** (Save ₹81,000/yr)
- **25% Waiver**: Net Tuition **₹2,02,500 / yr** (Save ₹67,500/yr)
- **20% Waiver**: Net Tuition **₹2,16,000 / yr** (Save ₹54,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹8,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_BTECH_CORE_FEE_TEXT = """### ⚙️ B.Tech Core Engineering — Fee Structure (2027–28)

Official fee schedule for **B.Tech Core Programs** (Mechanical, Civil, Electrical & Electronics, Biotechnology, Food Technology):

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,00,000** | **₹2,00,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹1,15,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹1,10,000** | **₹2,20,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹1,20,000 / yr** (Save ₹80,000/yr)
- **30% Waiver**: Net Tuition **₹1,40,000 / yr** (Save ₹60,000/yr)
- **25% Waiver**: Net Tuition **₹1,50,000 / yr** (Save ₹50,000/yr)
- **20% Waiver**: Net Tuition **₹1,60,000 / yr** (Save ₹40,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹6,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_MANAGEMENT_FEE_TEXT = """### 🏢 Astra School of Business — Fee Structure (2027–28)

Official fee schedule for Management & Commerce programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **BBA (General)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **BBA (Business Analytics / Specialized)** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **B.Com** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |
| **MBA (Finance, Marketing, HR, Analytics)** | **₹3,00,000** | ₹1,50,000 | +₹9,000 / yr |
| **MBA in Agri-Business Management** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers based on qualifying exam scores; eligible PG students receive an additional 10% scholarship."""

_AGRICULTURE_FEE_TEXT = """### 🌾 School of Agriculture — Fee Structure (2027–28)

Official fee schedule for the **ICAR-Accredited** Agricultural programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **B.Sc. (Hons) Agriculture** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **B.Tech Food Technology** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **M.Sc Agriculture (All Disciplines)** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |

- **Accreditation**: First private university in the Telugu States with ICAR accreditation.
- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers based on 10+2 BiPC marks or EAPCET rank."""

_COMP_APP_FEE_TEXT = """### 💻 Computer Applications & IT — Fee Structure (2027–28)

Official fee schedule for Computer Applications:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **BCA (Hons)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **B.Sc Computer Science (Hons)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **MCA** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **M.Sc Computer Science** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers."""

_DESIGN_FEE_TEXT = """### 🎨 School of Design — Fee Structure (2027–28)

Official fee schedule for Design programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **B.Des Interior Design** | **₹2,10,000** | ₹1,05,000 | +₹6,000 / yr |
| **B.Des Fashion Design** | **₹2,10,000** | ₹1,05,000 | +₹6,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers."""

_ALL_PROGRAMS_TEXT = """### 🎓 Programs Offered at SR University (2027–28)

SR University offers multidisciplinary UG, PG, and Ph.D. programs across **6 specialized schools**:

1. **School of Computer Science & Artificial Intelligence**: B.Tech CSE (Core, AIML, Data Science, Cyber Security, Quantum AI, Robotics), BCA, MCA, M.Tech, Ph.D.
2. **School of Engineering**: B.Tech in ECE, EEE, Mechanical, Civil & 2+2 International Engineering Program (IEP); M.Tech, Ph.D.
3. **Astra School of Business**: BBA (General & Specializations in Analytics, Finance, Marketing, HR), B.Com, MBA, Ph.D.
4. **School of Agriculture (ICAR-Accredited)**: B.Sc. (Hons) Agriculture, B.Tech Food Technology, M.Sc. Agriculture, Ph.D.
5. **School of Design**: B.Des in Interior Design & Fashion Design.
6. **School of Sciences & Humanities**: B.Tech Biotechnology (with AI), B.Sc, M.Sc, M.A. English.
7. **Doctoral Studies & Research (Ph.D.)**: Full-Time & Part-Time Ph.D. across all disciplines.

👉 **Which school or program would you like details on (eligibility, fees, or syllabus)?**"""

_ABOUT_SRU_TEXT = """### 🎓 About SR University (SRU)

SR University is a multidisciplinary, research-driven institution in Warangal, Telangana, dedicated to innovation, academic excellence, and global readiness:

• **Top Private University of Telangana & AP**: SR University stands among the premier private universities in the Telugu States, and is the first private university in Telangana and AP to receive prestigious **ICAR accreditation** for agricultural programs.
• **Prestigious Rankings & Accreditations**: Ranked **91st in NIRF Engineering** (top 100 for 4 consecutive years), **Tier-1 NBA accreditation** across all eligible B.Tech programs, **NAAC 'A' Grade**, and ranked **7th among private universities in India** (6th in Research Quality) by Times Higher Education (THE).
• **Record Placements & Industry Readiness**: Exceptional career outcomes with packages reaching **₹51 LPA (Microsoft)**, **₹49.3 LPA (ServiceNow)**, and **₹46.38 LPA (Amazon)**, an average package of ₹6 LPA, over 1,300 job offers, and **100% placement readiness assistance** with 250+ marquee recruiters.
• **Global Collaborations**: Active tie-ups with **80+ top global universities** across the US, UK, Australia, and Europe for student exchange, semester abroad, and 2+2 dual-degree international pathways.
• **Next-Gen Living & Learning Campus**: A vibrant **170-acre green campus** featuring 15+ advanced research centers, DST-backed **SRiX Technology Business Incubator** (171+ startups, ₹76+ Cr funding), a 4,000-seat mega central dining complex, and modern 24/7 secured hostels."""

_WHY_CHOOSE_SRU_TEXT = """### 🌟 Why Choose SR University?

SR University delivers a distinctive education blending academic prestige, practical innovation, and high-impact career outcomes:

• **Top Private University of Telangana & AP**: The premier and fastest-growing private university in Telangana with recognized national and global standing, plus first-in-region ICAR accreditation.
• **Elite Rankings & Global Recognition**: **NIRF 91st in Engineering** (consistently in Top 100 for 4 consecutive years), **Tier-1 NBA** accredited B.Tech branches, **NAAC 'A' grade**, and ranked **7th among private Indian universities** by Times Higher Education.
• **Marquee Placements & High Packages**: Dream career packages of **₹51 LPA (Microsoft)**, **₹49.3 LPA (ServiceNow)**, and **₹46.38 LPA (Amazon)**, with 100% placement readiness assistance and 3,500+ internships.
• **Global Collaborations**: Strategic tie-ups with **80+ international universities** allowing students to study abroad, pursue joint research, or complete international engineering dual degrees.
• **Next-Gen Living & Learning Campus**: A state-of-the-art **170-acre campus** with modern AC/Non-AC hostels, 4,000-seat central dining hall, DST-funded **SRiX Startup Incubator** (₹76+ Cr raised), and flexible choice-based credit learning (FFCS)."""

_ABOUT_SRU_CHIPS = ["B.Tech CSE fees", "Calculate my scholarship", "Placement record", "Plan a campus visit"]

_HOSTEL_INFO_TEXT = """### 🏢 Residential Campus Living at SR University

SR University offers a secure, vibrant, and disciplined residential experience with **dedicated separate hostel blocks** for Boys and Girls on campus:

• **Hostel Blocks**:
  - **Boys Hostels**: Dr. Sarvepalli Radhakrishnan Bhavan & APJ Abdul Kalam Bhavan
  - **Girls Hostels**: Kalpana Chawla Bhavan & Sarojini Naidu Bhavan
• **Room Options & Furnishings**:
  - **Air-Conditioned (AC)**: 3-Sharing & 4-Sharing
  - **Non-AC**: 3-Sharing & 4-Sharing
  - Every resident receives a dedicated bed, comfortable mattress, individual study desk, ergonomic chair, personal wardrobe, and 24/7 Wi-Fi.
• **Mega Dining Hall**:
  - 4,000 seating capacity serving 4 fresh, hygienic, unlimited meals daily (Breakfast, Lunch, Evening Snacks, Dinner) with balanced vegetarian and non-vegetarian menus.
• **Key Amenities & Utilities**:
  - 24/7 power backup and commercial RO-purified water dispensers on every floor.
  - Solar hot water supply (7:00–9:00 AM & 7:00–9:00 PM).
  - Modern gymnasium with fitness trainers, indoor sports (table tennis, carroms, chess, shuttle badminton) and recreation lounges.
  - On-campus health clinic, resident nurses, 24/7 stationed ambulance, and institutional tie-up with Aaditya Hospital.
• **Safety & Security**:
  - 100% CCTV surveillance, biometric access checkpoints, dedicated security personnel at all gates, and resident wardens in every block.

*Hostel accommodation is optional. Would you like to check the room fee breakdown, dining timings, or curfew rules?*"""

_HOSTEL_MESS_TEXT = """### 🍽️ Dining & Mess Facilities at SR University

The university features a state-of-the-art **4,000-seat Mega Dining Hall** providing nutritious, wholesome meals in an ultra-hygienic environment:

• **4 Wholesome Meals Daily Schedule**:
  - 🍳 **Breakfast (7:30 AM – 8:30 AM)**: Nutritious South & North Indian breakfast items (idli, dosa, puri, upma, poha), boiled eggs/sprouts, tea, coffee, and fresh milk.
  - 🍛 **Lunch (12:00 PM – 2:00 PM)**: Complete balanced meal — steamed rice, roti/chapati, seasonal vegetable curries, dal/sambar, rasam, fresh curd/buttermilk, and papad.
  - ☕ **Evening Snacks (5:00 PM – 6:00 PM)**: Freshly made evening refreshments (samosas, cutlets, pakoras, or bajji) with hot tea and coffee.
  - 🍲 **Dinner (7:30 PM – 8:30 PM)**: Wholesome dinner with vegetarian dishes and non-vegetarian curries served on designated days, followed by desserts or seasonal fruits.
• **Dining Features**:
  - **Unlimited Self-Service**: Students enjoy unlimited servings during meal timings.
  - **Hygiene & Safety**: Steam-cooking boilers, commercial RO water for cooking and drinking, and regular health checkups of catering staff.
  - **Sick Diet**: Special light diet (khichdi, clear soup, boiled milk/eggs) provided upon resident doctor or hostel nurse recommendation.
  - **Festive Dinners**: Special grand feasts organized on major festivals and institutional celebrations.

*Would you like to know more about hostel room options, rules, or fees?*"""

_HOSTEL_CURFEW_RULES_TEXT = """### ⏰ Hostel Curfew, Timings & Discipline Regulations

SR University maintains a secure and disciplined campus environment with strict curfew and movement policies:

• **Hostel In-Time (Night Curfew)**:
  - **Weekdays (Monday to Friday)**: Students must be inside the hostel premises by **9:00 PM**.
  - **Weekends & Holidays (Saturday & Sunday)**: Students must be inside by **9:30 PM**.
  - **Biometric Roll Call**: Mandatory nightly biometric attendance between **9:00 PM and 9:30 PM** (weekdays) / before **10:00 PM** (weekends).
  - **Morning Exit**: Students can leave the hostel in the morning after **5:30 AM** by signing the movement register.
• **Curfew Extensions**:
  - Extensions up to **11:00 PM** are granted for hackathons, club activities, festival preparations, or library study.
  - Requests must be submitted via the online **Sruniv portal** before 4:00 PM on the day and approved by the Warden.
• **Digital Out-Pass System**:
  - Resident students wishing to leave campus must apply via the online **Sruniv portal**.
  - Automated SMS notifications are sent to parents/guardians for approval before gate clearance is issued.
• **Silence Hours & Code of Conduct**:
  - **Silence Hours**: **10:00 PM to 7:00 AM** daily (strictly enforced for quiet study and rest).
  - **Cross-Gender Entry Policy**: Strictly prohibited. Male students/visitors cannot enter female blocks, and female students/visitors cannot enter male blocks.
  - **Prohibited Appliances**: Electric stoves, induction cooktops, immersion heaters, and electric irons are strictly forbidden in rooms.
  - **Substance Policy**: 100% zero-tolerance policy against ragging, bullying, alcohol, smoking, or unauthorized absences.

*Would you like to review safety and warden details, mess food, or room fees?*"""

_HOSTEL_SAFETY_TEXT = """### 🛡️ Campus Safety, Security & Hostel Wardens

The safety and well-being of residential students are our highest priorities:

• **Round-the-Clock Security**:
  - Gated campus with 24/7 professional uniformed security personnel at all hostel and campus gates.
  - Comprehensive CCTV surveillance covering all hostel corridors, staircases, common lounges, and perimeter grounds.
  - Biometric checkpoints for entry and roll call.
• **Dedicated Residential Wardens**:
  - **Girls Hostels Warden**: Ms. Anitha GP (📞 **+91 9599042878** | ✉️ `stu.girlshostel@sru.edu.in`)
  - **Boys Hostels Wardens**: Dr. Rupesh Mishra (📞 **+91 9716935695**) & Dr. Anshu Kumar (📞 **+91 6394355001**)
• **Student Counsellors**:
  - **Boys Counsellor**: Mr. Benson (📞 **+91 7893525257**)
  - **Girls Counsellor**: Ms. Swapna (📞 **+91 7207672300**)
• **Medical & Emergency Infrastructure**:
  - On-campus Health Centre with qualified resident nurse and visiting physicians.
  - Stationed 24/7 emergency ambulance on campus.
  - Direct tie-up with **Aaditya Hospital** for tertiary and emergency healthcare.
• **Zero-Tolerance Anti-Ragging**:
  - Fully compliant with Supreme Court & UGC Anti-Ragging Regulations 2009.
  - Active Anti-Ragging Committee and flying squads (`stu.antiraggingcell@sru.edu.in`).

*Would you like details on hostel living facilities, mess food, or room fees?*"""

_HOSTEL_FEE_TEXT = """### 💰 SR University Residential Hostel Fee Structure (2027–28)

Hostel accommodation is optional. Annual fees cover both **room accommodation and all 4 daily meals** in the 4,000-seat mega dining hall:

| Room Type | Sharing | Annual Fee (Room + Mess) | Notes |
| :--- | :--- | :--- | :--- |
| **Non-AC** | **4-Sharing** | **₹1,15,000 / year** | 4 meals/day, Wi-Fi, study desk, power backup |
| **Non-AC** | **3-Sharing** | **₹1,25,000 / year** | 4 meals/day, Wi-Fi, study desk, power backup |
| **Air-Conditioned (AC)** | **4-Sharing** | **₹1,25,000 / year** | AC room, 4 meals/day, Wi-Fi, study desk |
| **Air-Conditioned (AC)** | **3-Sharing** | **₹1,35,000 / year** | AC room, 4 meals/day, Wi-Fi, study desk |

#### 📋 Additional Deposits & Charges:
• **Caution Deposit**: **₹5,000** (one-time, refundable at end of degree)
• **Laundry Services**: **₹5,000 / year** (in-house mechanized laundry)
• **Electricity Deposit (AC Rooms)**: **₹10,000 / year** (Non-AC: **₹5,000 / year**)

> [!NOTE]
> - Hostel fees are billed annually at the beginning of each academic year.
> - Separate hostel blocks are provided for Boys and Girls on campus."""

_HOSTEL_INFO_CHIPS = ["Mess Food & Timings", "Hostel Rules & Curfew", "Safety & Wardens", "Hostel Fee Breakdown"]
_HOSTEL_MESS_CHIPS = ["Hostel Facilities & Rooms", "Curfew & In-Time Rules", "Hostel Room Fees", "Safety & Security"]
_HOSTEL_CURFEW_CHIPS = ["Mess & Dining timings", "Hostel Facilities & Rooms", "Hostel Wardens & Contacts", "Hostel Fees"]
_HOSTEL_SAFETY_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Hostel Fees"]
_HOSTEL_FEE_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Calculate B.Tech Fee"]

_COMBINED_HOSTEL_FEE_TEXT = """### 🎓 B.Tech CSE Fee + Hostel Combined Breakdown (Academic Year 2027–28)

Here is the complete combined fee breakdown for **B.Tech Computer Science & Engineering (Core)** including **Residential Hostel & Mess (AC 4-Sharing)**:

#### 📅 Per-Semester Breakdown (Regular):
• **Tuition Fee**: **₹1,70,000 / sem** (Annual base ₹3,40,000; up to 40% merit scholarship applies)
• **Hostel & Dining (AC 4-Sharing)**: **₹62,500 / sem** (Annual ₹1,25,000; includes 4 daily meals, Wi-Fi & laundry)
• **Academic & Exam Fee**: **₹10,000 / sem** (Annual ₹20,000)
👉 **Combined Regular Semester Fee**: **₹2,42,500 / semester**

#### 📋 First-Year Total Outlay:
• **Year 1 Combined Total**: **₹4,91,100** (Tuition ₹3.40L + Hostel ₹1.25L + Academic ₹20k + One-time admission/enrolment ₹6,100)
*(With Non-AC 4-Sharing, the combined total is **₹4,81,100 / year** or **₹2,37,500 / semester**).*

> [!NOTE]
> Merit scholarships (up to 40% waiver based on 10+2 marks or entrance ranks) directly reduce the tuition portion!"""

_COMBINED_HOSTEL_FEE_CHIPS = ["Calculate scholarship for my marks", "Hostel room options", "Placement records for this course", "Hostel Rules & Curfew"]

_CAMPUS_CANTEEN_TEXT = """### ☕ Campus Cafeteria, Food Stalls & Dining Options at SR University

SR University offers vibrant on-campus dining and snacking spots for students, faculty, and visitors across its 170-acre campus:

#### 1. 🍽️ Central Cafeteria
• **Timings**: **8:30 AM to 6:00 PM** (Monday to Saturday)
• **Offerings**: Fresh breakfast, hot South & North Indian lunch platters, fresh juices, teas, coffees, and wholesome snacks in a spacious indoor seating setting.

#### 2. 🥪 Campus Food Kiosks & Stalls
Open **9:00 AM to 7:00 PM** across campus plazas:
• **Tasty Treat**: Quick bites, grilled sandwiches, rolls, patties, and cool beverages.
• **Meet and Eat**: Fast-food varieties, noodles, wraps, and quick evening snacks.
• **Bharat Foods**: Traditional snacks, chaat, samosas, and refreshing hot drinks.

#### 3. 🍱 4,000-Seat Mega Dining Hall (Residential Mess)
• Four nutritious, hygienic daily meals (Breakfast, Lunch, Evening Snacks, Dinner) for hostel residents with rotating South & North Indian multi-cuisine menus.

> [!TIP]
> All food kiosks and the central cafeteria accept digital payments (UPI/cards). The Canara Bank 24/7 ATM is conveniently located at the Main Gate."""

_CAMPUS_CANTEEN_CHIPS = ["Hostel Mess & Dining", "Hostel Facilities & Rooms", "Campus Tour & Visit", "B.Tech CSE Fees"]

_ACADEMIC_EVALUATION_TEXT = """### 📊 Academic Regulations & Examination Evaluation at SR University (R22/R23)

SR University follows a comprehensive Credit-Based Semester System (CBSS) governed by the Academic Council:

#### 📝 Evaluation Structure
• **Continuous Internal Evaluation (CIE)**: Conducted during the semester through mid-term examinations, quizzes, assignments, and laboratory assessments.
• **End Semester Examination (ESE)**: Comprehensive university examinations conducted at the conclusion of each semester.

#### 🎯 10-Point Letter Grading Scale
| Letter Grade | Performance | Grade Point | Remarks |
| :--- | :--- | :--- | :--- |
| **O** | Outstanding | **10** | Exceptional performance |
| **A** | Excellent | **10** | Pass grade |
| **B** | Very Good | **8** | Pass grade |
| **C** | Good | **6** | Pass grade |
| **D** | Average | **4** | **Minimum Pass Grade (40% aggregate for UG)** |
| **F** | Fail | **0** | Backlog course; must appear in supplementary |
| **R** | Detained | **0** | Attendance < 75%; must re-register in Summer/Winter |

#### 📈 Percentage Conversion & Progression
• **Percentage Formula**: $\\text{Percentage of Marks} = 10 \\times \\text{CGPA}$
• **Attendance Requirement**: Minimum **75% aggregate** in each course (condonation board waiver up to 10–25% for verified medical emergencies).
• **Progression Criteria**: To promote to 2nd year: CGPA $\\ge 3.50$ (or 40% of 1st-year credits); to 3rd & 4th year: CGPA $\\ge 4.00$ (or 50% credits)."""

_ACADEMIC_EVALUATION_CHIPS = ["Attendance & Condonation Rules", "Honours & Minor Degrees", "B.Tech CSE Fees", "Placement Records"]

_LAB_FACILITIES_TEXT = """### 🔬 Laboratories & Research Infrastructure at SR University

SR University does not operate with a single combined count for all labs because facilities are organized across three distinct levels of advanced infrastructure:

#### 1. 🏢 11 Interdisciplinary Specialized Research Centers
Dedicated high-tech centers conducting cutting-edge research, patent creation, and industry projects:
• **Center for AI & Deep Learning (CAIDL)**: High-performance GPU computing clusters, neural network training environments, and computer vision systems.
• **Center for Creative Cognition (CCC)**: Houses 6 advanced labs (*Ideation Lab, Eye-tracking Lab, EEG Lab, Computational Neuroscience Lab, Driving Simulator Lab, Psychometric Testing Lab*).
• **Center for Embedded Systems & IoT (EIoT)**: Raspberry Pi platforms, ARM Cortex M4 development kits, and wireless sensor nodes.
• **Center for Emerging Energy Technologies (CEET)**: LabVIEW Advanced Simulation Lab, Energy Lab, and Electric Drives / EV Powertrain Lab.
• **Center for Materials & Manufacturing (CMM)**: Product Design Studio, CAD/CAM Lab, CNC Makers Space, and Additive Manufacturing (3D Printing).
• **Center for Construction Methods & Materials**: Concrete Technology, Triaxial Testing, Digital Consolidation, and Automatic Asphalt Compactor setups.
• **Centre for Nanomaterials**: Nanomaterial synthesis and high-resolution characterization microscopy.
• **Additional Centers**: *Center for Informetrics & Statistics*, *Center for Experiential Learning*, *Collaboratory for Social Innovation*, and *Center for Design*.

#### 2. 🚀 SR Innovation Exchange (SRiX) & Prototyping Studios
• **14+ Maker Spaces** and open innovation project studios.
• **IoT & ESDM Lab** (Electronic System Design & Manufacturing).
• **3D Rapid Prototyping Facility** & **Design Thinking Studio** supporting student startups from idea to scale (171+ startups incubated, ₹76+ Cr funding).

#### 3. 🖥️ Departmental Academic Laboratories Across 6 Schools
Every department maintains multiple specialized curriculum labs:
• **School of Computer Science & AI**: AI/ML, Big Data Analytics, Cloud Computing/DevOps, Cybersecurity, and Software Engineering Labs.
• **School of Engineering**: ECE (VLSI Design, DSP, Microprocessors, Microwave), EEE (Electric Machines, Power Electronics), Mechanical (Robotics & Automation, CAD/CAM, Metallurgy, Fluid Mechanics), and Civil (Surveying Total Station, Geotechnical, Environmental).
• **School of Agriculture (ICAR Accredited)**: 50+ acre experimental farm, polyhouses, Soil & Water Testing, Agronomy, and Plant Pathology labs.
• **Basic Sciences & Design**: Engineering Physics, Chemistry, AECS Multimedia English Lab, and Visual Design/Ergonomics Studios.

Which department or domain of laboratories would you like to explore in detail?"""

_LAB_FACILITIES_CHIPS = ["AI & Computer Science Labs", "SRiX Startup Maker Spaces", "Robotics & IoT Labs", "B.Tech CSE Curriculum"]


def _cache_key(message: str) -> str:
    import hashlib
    norm = re.sub(r"[^a-z0-9 ]+", " ", message.lower())
    return "sru:answer:" + hashlib.sha1(" ".join(norm.split()).encode()).hexdigest()


# -------------------------------------------------------------------- the agent ----
def _is_mock_or_test_client(cl) -> bool:
    return cl is not None and type(cl).__name__ in (
        "DummyClient", "Recorder", "MockClient", "MockAgentClient", "ScriptedClient",
        "FakeClient", "StreamingClient", "FallbackClient", "KeyClient", "QuotaClient"
    )


async def run_agent(
    message: str,
    session_id: str,
    conversation_id=None,
    client=None,
    require_contact_details: bool = False,
):
    """Async generator of events for one student message."""
    started = time.perf_counter()
    message = (message or "").strip()[:config.AGENT_MAX_MESSAGE_CHARS]
    yield {"type": "start", "conversation_id": conversation_id}
    if not message:
        yield {"type": "error", "detail": "Please type a question."}
        return

    # OWASP LLM01 / LLM06: Prompt injection and adversarial guardrail pre-screening
    refusal = intents.check_adversarial_guardrail(message)
    if refusal:
        async for ev in _say(refusal, message, session_id, conversation_id):
            yield ev
        return

    # Three independent reads, done together (each one may need a trip to Redis or the database).
    profile, history, conv_state = await asyncio.gather(
        memory.get_profile(session_id), memory.get_history(session_id, conversation_id),
        memory.get_conversation_state(session_id, conversation_id))
    ctx = {"session_id": session_id, "conversation_id": conversation_id, "profile": profile}

    if require_contact_details:
        existing_phone = tools.clean_phone(profile.get("phone") or "")
        extracted_phone = tools.find_phone(message)
        extracted_name = intents.extract_name(message, bare_ok=not profile.get("name"))
        if extracted_name and not profile.get("name"):
            profile = await memory.update_profile(session_id, name=extracted_name)
        if extracted_phone and not existing_phone:
            profile = await memory.update_profile(session_id, phone=extracted_phone)
        existing_name = str(profile.get("name") or "").strip()
        existing_phone = tools.clean_phone(profile.get("phone") or "")

        if not (existing_name and existing_phone):
            if not existing_name and not existing_phone:
                reply = "Before I can help, please provide your full name and 10-digit mobile number."
            elif not existing_name:
                reply = "Please provide your full name before I answer your question."
            else:
                reply = "Please provide your 10-digit mobile number before I answer your question."
            async for ev in _say(reply, message, session_id, conversation_id):
                yield ev
            return

    # ---- Semantic Routing & Approved Answer Policy Matching ----
    t0_routing = time.perf_counter()
    routing_decision = semantic_router.route_message(message, history, conv_state)
    routing_latency_ms = round((time.perf_counter() - t0_routing) * 1000, 2)

    # State preservation: detect interruptions to active admission dialogue
    is_admission_in_progress = bool(
        (conv_state.get("fee_intake") or {}).get("waiting_for")
        or conv_state.get("admission_stage")
    )
    paused_intent = conv_state.get("paused_intent")
    if is_admission_in_progress and routing_decision.intent_id not in ("ADMISSION_DATA_INPUT", "ADMISSION_COUNSELLING"):
        paused_intent = conv_state.get("current_intent") or "ADMISSION_COUNSELLING"

    # Map semantic policy intent to agent execution intent
    _SEMANTIC_TO_AGENT_INTENT = {
        "ABOUT_SRU": "ABOUT_SRU_QUERY",
        "WHY_CHOOSE_SRU": "WHY_CHOOSE_SRU_QUERY",
        "PLACEMENT_GUARANTEE": "PLACEMENT_GUARANTEE_QUERY",
        "ADMISSION_GUARANTEE": "ADMISSION_GUARANTEE_QUERY",
        "HOSTEL_CURFEW": "HOSTEL_CURFEW_RULES_QUERY",
        "HOSTEL_INFO": "HOSTEL_INFO_QUERY",
        "FUTURE_YEAR_FEE": "FUTURE_YEAR_FEE_QUERY",
        "SPECIAL_CONCESSIONS": "SPECIAL_CONCESSIONS_QUERY",
        "DATE_QUERY": "DATE_QUERY",
        "LAB_FACILITIES": "LAB_FACILITIES_QUERY",
    }
    legacy_intent = intents.classify_agent_intent(message, conv_state)
    _SPECIFIC_FLOW_INTENTS = {
        "FEE_TREE_QUERY", "BTECH_TREE_QUERY", "BTECH_CSE_FEE_QUERY", "BTECH_AI_ROBOTICS_FEE_QUERY",
        "BTECH_ECE_FEE_QUERY", "BTECH_CORE_FEE_QUERY", "MANAGEMENT_FEE_QUERY", "AGRICULTURE_FEE_QUERY",
        "COMP_APP_FEE_QUERY", "DESIGN_FEE_QUERY", "CAMPUS_TOUR_DISPATCH", "CAMPUS_TOUR_VIRTUAL",
        "CAMPUS_VISIT_BOOKING_WITH_DATE", "CAMPUS_VISIT_BOOKING", "CAMPUS_VISIT_INFO", "JOIN_SRU_QUERY",
        "CONFUSION_QUERY", "NEXT_GEN_TECH_QUERY", "ALL_PROGRAMS_QUERY", "OTHER_FEES_QUERY",
        "HOSTEL_FEE_QUERY", "HOSTEL_MESS_QUERY", "HOSTEL_SAFETY_QUERY", "COMBINED_FEE_HOSTEL_QUERY",
        "CAMPUS_CANTEEN_QUERY", "ACADEMIC_EVALUATION_QUERY", "ABOUT_SRU_QUERY",
    }
    if legacy_intent in _SPECIFIC_FLOW_INTENTS:
        intent = legacy_intent
    elif routing_decision.policy_id and not routing_decision.is_fallback:
        mapped_intent = _SEMANTIC_TO_AGENT_INTENT.get(routing_decision.intent_id)
        intent = mapped_intent if mapped_intent else legacy_intent
    else:
        intent = legacy_intent

    used, cards = [], []

    async def set_state(**fields):
        conv_state.update(fields)
        await memory.update_conversation_state(session_id, conversation_id, **fields)

    # Persist preserved state variables
    await set_state(
        current_intent=routing_decision.intent_id,
        paused_intent=paused_intent,
        collected_data=profile or {},
        pending_question=conv_state.get("pending_user_question"),
    )

    turn_telemetry = observability.PolicyTurnTelemetry(
        session_id=session_id,
        conversation_id=conversation_id,
        message=message,
        detected_intent=routing_decision.intent_id,
        selected_policy_id=routing_decision.policy_id,
        policy_version=routing_decision.policy_version,
        response_mode=routing_decision.response_mode.value if hasattr(routing_decision.response_mode, "value") else str(routing_decision.response_mode),
        retrieved_evidence_ids=routing_decision.evidence_ids,
        routing_confidence=routing_decision.confidence,
        fallback_decision=routing_decision.is_fallback,
        fallback_reason=routing_decision.fallback_reason,
        routing_latency_ms=routing_latency_ms,
    )

    async def clear_pending():
        await set_state(pending_action=None, pending_phone=None, pending_name=None, pending_turns=0)

    # Track conversational topic and program across turns
    active_topic = conv_state.get("active_topic")
    active_program = conv_state.get("active_program")

    current_topic = followups.topic_of(message, used, active_topic=active_topic)
    if current_topic:
        active_topic = current_topic
        await set_state(active_topic=active_topic)

    # Track conversational program and course changes across turns
    explicit_msg_prog = fees.find_program(message)
    previous_active_prog = conv_state.get("active_program") or (profile.get("program_interest") if profile else None)

    if explicit_msg_prog:
        active_program = explicit_msg_prog
        if profile is not None:
            profile["program_interest"] = explicit_msg_prog
        await memory.update_profile(session_id, program_interest=explicit_msg_prog)

        # Handle course switch
        if previous_active_prog and previous_active_prog != explicit_msg_prog:
            data = fees.load_data()
            old_level = data.get("programs", {}).get(previous_active_prog, {}).get("level", "ug")
            new_level = data.get("programs", {}).get(explicit_msg_prog, {}).get("level", "ug")
            current_intake = dict(conv_state.get("fee_intake") or {})
            if current_intake:
                current_intake["program"] = explicit_msg_prog
                if old_level != new_level:
                    for k_clr in (
                        "board", "board_label", "board_key", "academic_stage", "stage_label",
                        "raw_marks", "max_marks", "percent", "is_projected", "admission_route",
                        "route_label", "eapcet_rank", "jee_percentile", "ib_score"
                    ):
                        current_intake.pop(k_clr, None)
                        if profile is not None:
                            profile.pop(k_clr, None)
            await set_state(
                active_program=explicit_msg_prog,
                fee_flow_prog=explicit_msg_prog,
                fee_tree_step=None,
                fee_intake=current_intake if current_intake.get("waiting_for") else None,
            )
        else:
            current_intake = dict(conv_state.get("fee_intake") or {})
            if current_intake.get("waiting_for"):
                current_intake["program"] = explicit_msg_prog
                await set_state(
                    active_program=active_program,
                    fee_flow_prog=active_program,
                    fee_intake=current_intake,
                )
            else:
                await set_state(
                    active_program=active_program,
                    fee_flow_prog=active_program,
                )
    else:
        active_program = (
            conv_state.get("active_program")
            or (profile.get("program_interest") if profile else None)
            or ((conv_state.get("fee_intake") or {}).get("program"))
        )
        if active_program:
            await set_state(active_program=active_program)
            if profile is not None and not profile.get("program_interest"):
                profile["program_interest"] = active_program
                await memory.update_profile(session_id, program_interest=active_program)

    # Early extract academic facts (board, stage, marks, rank) so they are preserved across turns
    early_details = fee_intake.parse_details(message)
    academic_updates = {}
    for k in (
        "board", "board_label", "board_key", "academic_stage", "stage_label",
        "raw_marks", "max_marks", "percent", "is_projected", "admission_route",
        "route_label", "eapcet_rank", "jee_percentile", "ib_score"
    ):
        if early_details.get(k) is not None:
            if profile is not None:
                profile[k] = early_details[k]
            academic_updates[k] = early_details[k]
    if early_details.get("generic_btech") and not (profile or {}).get("degree_interest") and not (profile or {}).get("program_interest"):
        academic_updates["degree_interest"] = "btech"
        academic_updates["generic_btech"] = True
        if profile is not None:
            profile["degree_interest"] = "btech"
            profile["generic_btech"] = True
    if academic_updates:
        await memory.update_profile(session_id, **academic_updates)
        current_intake = dict(conv_state.get("fee_intake") or {})
        if current_intake.get("waiting_for"):
            current_intake.update(academic_updates)
            await set_state(fee_intake=current_intake)

    # Detect user persona and style
    persona = intents.detect_user_persona(message, history, profile)
    if persona == "parent" and not profile.get("is_parent"):
        profile["is_parent"] = True
        await memory.update_profile(session_id, is_parent=True)

    # Extract name if user provided one
    awaiting_name = bool(conv_state.get("awaiting_name"))
    extracted_name = intents.extract_name(message, bare_ok=awaiting_name)
    if extracted_name and not profile.get("name"):
        profile["name"] = extracted_name
        await memory.update_profile(session_id, name=extracted_name)
        await set_state(name_asked=True, awaiting_name=False)

    # ---- Handle Turn 2 after name was requested ----
    if awaiting_name:
        if extracted_name:
            await set_state(awaiting_name=False)
            pending_q = conv_state.get("pending_user_question")
            if pending_q:
                # Answer the question asked in Turn 1 immediately
                await set_state(pending_user_question=None)
                message = pending_q
                intent = intents.classify_agent_intent(message, conv_state)
            else:
                # User had only sent a greeting in Turn 1
                reply = _select_variation(_NAME_GIVEN_REPLIES, session_id).format(name=_first_name(extracted_name))
                async for ev in _say(reply, message, session_id, conversation_id, suggestions=_SMALL_TALK_CHIPS):
                    yield ev
                return
        else:
            # User declined, skipped, or asked another question
            await set_state(awaiting_name=False)
            pending_q = conv_state.get("pending_user_question")
            if pending_q and intents.is_refusal_or_skip(message):
                await set_state(pending_user_question=None)
                message = pending_q
                intent = intents.classify_agent_intent(message, conv_state)
            elif pending_q:
                await set_state(pending_user_question=None)

    # ---- 1. Things the code can answer by itself ------------------------------------------
    if intent == "DATE_QUERY":
        async for ev in _say(f"Today is {date.today():%B %d, %Y}.", message, session_id, conversation_id,
                             suggestions=["Plan a campus visit", "What are the B.Tech CSE fees?",
                                          "Hostel rules & curfew"]):
            yield ev
        return

    if intent == "CONFUSION_QUERY":
        async for ev in _say("Sorry for the confusion! I'm here to help clarify. Could you share what specific details you're looking for? "
                             "I can help with B.Tech & PG programs, fee structure, scholarships, placements, or visiting the campus.",
                             message, session_id, conversation_id,
                             suggestions=["B.Tech CSE fees", "Scholarship slabs", "Placements at SRU", "Plan a campus visit"]):
            yield ev
        return

    if intent == "JOIN_SRU_QUERY":
        flow_card = fee_flow.build_school_selection_card()
        async for ev in _say(
            "That's great! Which course or degree are you interested in pursuing at SR University?\n\n"
            "We offer diverse undergraduate and postgraduate programs across Engineering, Management, "
            "Agriculture, Computer Applications, and Sciences. Choose an academic area below or tell me your preferred course:",
            message,
            session_id,
            conversation_id,
            cards=[flow_card],
            suggestions=["B.Tech Engineering", "MBA", "BBA", "B.Sc (Hons) Agriculture", "Explore all programs"]
        ):
            yield ev
        return

    # Greetings and small talk
    chat = intents.small_talk(message) if intent not in ("DATE_CONFIRMATION_YES", "DATE_CONFIRMATION_NO") else None
    if chat:
        first_name = _first_name(profile["name"]) if profile.get("name") else ""
        last_assistant_text = next(
            (h.get("text", "") for h in reversed(history) if h.get("role") in ("model", "assistant")),
            ""
        )
        name_used_recently = bool(
            first_name and re.search(rf"\b{re.escape(first_name)}\b", last_assistant_text, re.IGNORECASE)
        )
        name_bit = f", {first_name}" if (first_name and not name_used_recently) else ""
        if chat == "greeting":
            if profile.get("name"):
                if not name_used_recently:
                    text = _select_variation(_GREETING_WITH_NAME, session_id + str(len(history))).format(name=first_name)
                else:
                    text = f"Hello again! What would you like to explore about SR University today?"
            else:
                await set_state(awaiting_name=True, name_asked=True)
                text = _select_variation(_GREETING_ASK_NAME, session_id + str(len(history)))
        elif chat == "how_are_you":
            text = _select_variation(_SMALL_TALK_HOW_ARE_YOU, session_id + str(len(history))).format(name=name_bit)
        elif chat == "thanks":
            text = _select_variation(_SMALL_TALK_THANKS, session_id + str(len(history))).format(name=name_bit)
        elif chat == "bye":
            text = _select_variation(_SMALL_TALK_BYE, session_id + str(len(history))).format(name=name_bit)
        elif chat == "who_are_you":
            text = _select_variation(_SMALL_TALK_WHO_ARE_YOU, session_id + str(len(history)))
        else:
            text = f"Hello{name_bit}! What would you like to explore about SR University today?"

        async for ev in _say(text, message, session_id, conversation_id, suggestions=_SMALL_TALK_CHIPS):
            yield ev
        return

    # ---- 1b. Deterministic quick responses (placement assistance, special concessions, next-gen tech, fee tree, all programs) ----
    if intent == "PLACEMENT_GUARANTEE_QUERY":
        from app.services.card_service import PLACEMENT_EXCELLENCE_CARD, get_session_shown_cards, record_session_card
        reply = _select_variation(_PLACEMENT_ASSISTANCE_RESPONSES, session_id + str(len(history)))
        cards_to_show = []
        if "placement_highlights" not in get_session_shown_cards(session_id):
            cards_to_show = [PLACEMENT_EXCELLENCE_CARD]
            record_session_card(session_id, "placement_highlights")
        async for ev in _say(reply, message, session_id, conversation_id,
                             cards=cards_to_show,
                             suggestions=_PLACEMENT_ASSISTANCE_CHIPS):
            yield ev
        return

    if intent == "ADMISSION_GUARANTEE_QUERY":
        await set_state(fee_intake=None)
        async for ev in _say(_ADMISSION_GUARANTEE_TEXT, message, session_id, conversation_id,
                             suggestions=_ADMISSION_GUARANTEE_CHIPS):
            yield ev
        return

    if intent == "FUTURE_YEAR_FEE_QUERY":
        await set_state(fee_intake=None)
        async for ev in _say(_FUTURE_YEAR_FEE_TEXT, message, session_id, conversation_id,
                             suggestions=_FUTURE_YEAR_FEE_CHIPS):
            yield ev
        return

    if intent == "SPECIAL_CONCESSIONS_QUERY":
        from app.services.card_service import get_session_shown_cards, record_session_card
        cards_to_show = []
        if "get_special_concessions" not in get_session_shown_cards(session_id):
            cards_to_show = [{"type": "get_special_concessions", "data": fees.special_concessions()}]
            record_session_card(session_id, "get_special_concessions")
        async for ev in _say(_SPECIAL_CONCESSIONS_TEXT, message, session_id, conversation_id,
                             used=[{"name": "get_special_concessions", "status": "ok", "is_action": False}],
                             cards=cards_to_show,
                             suggestions=["Calculate my fee with scholarship", "Documents for concession",
                                          "Fee Structure 2027-28", "Talk to a counsellor"]):
            yield ev
        return

    if intent == "NEXT_GEN_TECH_QUERY":
        async for ev in _say(_NEXT_GEN_TECH_TEXT, message, session_id, conversation_id,
                             suggestions=["Fee for AI & Robotics", "B.Tech CSE fee structure",
                                          "Calculate my scholarship", "How do I apply?"]):
            yield ev
        return

    if intent == "ALL_PROGRAMS_QUERY":
        async for ev in _say(_ALL_PROGRAMS_TEXT, message, session_id, conversation_id,
                             suggestions=["Fee Structure 2027-28", "Next-Gen Tech Programs",
                                          "Special Concessions", "Calculate my scholarship"]):
            yield ev
        return

    if intent == "OTHER_FEES_QUERY" and (_is_mock_or_test_client(client) or client is None):
        from app.services.card_service import OTHER_FEES_CARD, get_session_shown_cards, record_session_card
        cards_to_show = []
        if "fee_breakdown" not in get_session_shown_cards(session_id):
            cards_to_show = [OTHER_FEES_CARD]
            record_session_card(session_id, "fee_breakdown")
        async for ev in _say(responses._OTHER_FEES_TEXT, message, session_id, conversation_id,
                             cards=cards_to_show,
                             suggestions=responses._OTHER_FEES_CHIPS):
            yield ev
        return

    if bool(tools.find_phone(message) or intents.is_callback_request(message)):
        canned_intents = (
            "FEE_TREE_QUERY", "BTECH_TREE_QUERY", "BTECH_CSE_FEE_QUERY", "BTECH_AI_ROBOTICS_FEE_QUERY",
            "BTECH_ECE_FEE_QUERY", "BTECH_CORE_FEE_QUERY", "MANAGEMENT_FEE_QUERY", "AGRICULTURE_FEE_QUERY",
            "COMP_APP_FEE_QUERY", "DESIGN_FEE_QUERY", "HOSTEL_INFO_QUERY", "HOSTEL_MESS_QUERY",
            "HOSTEL_CURFEW_RULES_QUERY", "HOSTEL_SAFETY_QUERY", "HOSTEL_FEE_QUERY", "COMBINED_FEE_HOSTEL_QUERY",
            "CAMPUS_CANTEEN_QUERY", "ACADEMIC_EVALUATION_QUERY", "ALL_PROGRAMS_QUERY", "OTHER_FEES_QUERY",
            "LAB_FACILITIES_QUERY", "WHY_CHOOSE_SRU_QUERY", "ABOUT_SRU_QUERY", "ADMISSION_GUARANTEE_QUERY",
            "FUTURE_YEAR_FEE_QUERY",
        )
        if intent in canned_intents:
            intent = "GENERAL"

    _SPECIFIC_SUBTOPIC_KEYWORDS = (
        "cyber", "cybersecurity", "security", "cloud", "data science",
        "robotics", "ece", "vlsi", "eee", "civil", "mechanical", "biotech", "agriculture",
        "bba", "mba", "bca", "mca", "b.des", "design", "fee", "fees", "cost", "price",
        "scholarship", "eligibility", "hostel", "cutoff", "sports",
        "library", "canteen", "mess", "curfew", "timing", "bus", "transport", "syllabus",
        "curriculum", "available", "offered", "how to apply",
    )
    if intent in ("WHY_CHOOSE_SRU_QUERY", "ABOUT_SRU_QUERY") and any(k in (message or "").lower() for k in _SPECIFIC_SUBTOPIC_KEYWORDS):
        intent = "GENERAL"

    if intent in ("WHY_CHOOSE_SRU_QUERY", "ABOUT_SRU_QUERY"):
        from app.services.video_service import get_relevant_videos, get_keyword_videos, create_video_card
        vids = get_relevant_videos(message, limit=2)
        if not vids:
            vids = get_keyword_videos(message, limit=2, prefer_campus=True)
        vid_card = create_video_card(vids) if vids else None
        cards_to_show = [vid_card] if vid_card else []
        text_to_say = _WHY_CHOOSE_SRU_TEXT if intent == "WHY_CHOOSE_SRU_QUERY" else _ABOUT_SRU_TEXT
        async for ev in _say(text_to_say, message, session_id, conversation_id,
                             cards=cards_to_show,
                             suggestions=_ABOUT_SRU_CHIPS):
            yield ev
        return

    if intent == "BRANCH_GUIDANCE_QUERY" or intents.is_branch_guidance_query(message):
        await set_state(active_topic="career_guidance")
        if client is None or _is_mock_or_test_client(client):
            raw_marks = early_details.get("raw_marks") or (profile.get("raw_marks") if profile else None)
            bg_text = responses.get_branch_guidance_text(raw_marks, session_id=session_id)
            async for ev in _say(bg_text, message, session_id, conversation_id,
                                 suggestions=responses._BRANCH_GUIDANCE_CHIPS):
                yield ev
            return

    if intent == "FEE_TREE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step="category")
            flow_card = fee_flow.build_school_selection_card()
            async for ev in _say(_FEE_TREE_TEXT, message, session_id, conversation_id,
                                 cards=[flow_card],
                                 suggestions=["B.Tech Engineering", "Management (BBA / MBA)",
                                              "B.Sc (Hons) Agriculture", "Computer Applications (BCA / MCA)"]):
                yield ev
            return

    if intent == "BTECH_TREE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step="btech_branch")
            flow_card = fee_flow.build_course_selection_card(fee_flow.SCHOOLS_DATA[0], level="ug")
            async for ev in _say(_BTECH_TREE_TEXT, message, session_id, conversation_id,
                                 cards=[flow_card],
                                 suggestions=["B.Tech CSE & Allied", "B.Tech AI & Robotics",
                                              "B.Tech ECE", "B.Tech Core Engineering"]):
                yield ev
            return

    if intent == "BTECH_CSE_FEE_QUERY":
        if profile is not None:
            profile["program_interest"] = "btech_cse"
        await memory.update_profile(session_id, program_interest="btech_cse")
        await set_state(fee_tree_step=None, active_program="btech_cse", fee_flow_prog="btech_cse")
        if client is None or _is_mock_or_test_client(client):
            cse_prog = fee_flow.SCHOOLS_DATA[0]["programs"]["ug"][0]
            spec = fee_flow.detect_specialization(message, cse_prog)
            fee_card = fee_flow.build_detailed_fee_card(cse_prog, fee_flow.SCHOOLS_DATA[0], "2027-28", spec=spec, user_text=message)
            fee_text = get_btech_cse_fee_text(specialization=spec, user_msg=message)
            async for ev in _say(fee_text, message, session_id, conversation_id,
                                 cards=[fee_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "BTECH_AI_ROBOTICS_FEE_QUERY":
        if profile is not None:
            profile["program_interest"] = "btech_ai_robotics"
        await memory.update_profile(session_id, program_interest="btech_ai_robotics")
        await set_state(fee_tree_step=None, active_program="btech_ai_robotics", fee_flow_prog="btech_ai_robotics")
        if client is None or _is_mock_or_test_client(client):
            fee_card = fee_flow.build_detailed_fee_card(fee_flow.SCHOOLS_DATA[0]["programs"]["ug"][1], fee_flow.SCHOOLS_DATA[0], "2027-28")
            async for ev in _say(_BTECH_AI_ROBOTICS_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[fee_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "BTECH_ECE_FEE_QUERY":
        if profile is not None:
            profile["program_interest"] = "btech_ece"
        await memory.update_profile(session_id, program_interest="btech_ece")
        await set_state(fee_tree_step=None, active_program="btech_ece", fee_flow_prog="btech_ece")
        if client is None or _is_mock_or_test_client(client):
            fee_card = fee_flow.build_detailed_fee_card(fee_flow.SCHOOLS_DATA[1]["programs"]["ug"][0], fee_flow.SCHOOLS_DATA[1], "2027-28")
            async for ev in _say(_BTECH_ECE_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[fee_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "BTECH_CORE_FEE_QUERY":
        if profile is not None:
            profile["program_interest"] = "btech_mech"
        await memory.update_profile(session_id, program_interest="btech_mech")
        await set_state(fee_tree_step=None, active_program="btech_mech", fee_flow_prog="btech_mech")
        if client is None or _is_mock_or_test_client(client):
            fee_card = fee_flow.build_detailed_fee_card(fee_flow.SCHOOLS_DATA[1]["programs"]["ug"][1], fee_flow.SCHOOLS_DATA[1], "2027-28")
            async for ev in _say(_BTECH_CORE_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[fee_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "MANAGEMENT_FEE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step=None)
            lvl = "ug" if "bba" in message.lower() else ("pg" if "mba" in message.lower() else None)
            course_card = fee_flow.build_course_selection_card(fee_flow.SCHOOLS_DATA[3], level=lvl)
            async for ev in _say(_MANAGEMENT_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[course_card],
                                 suggestions=["Calculate my fee with scholarship", "MBA specializations",
                                              "Hostel details", "How do I apply?"]):
                yield ev
            return

    if intent == "AGRICULTURE_FEE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step=None)
            lvl = "ug" if ("bsc" in message.lower() or "b.sc" in message.lower() or "agri" in message.lower()) else ("pg" if "msc" in message.lower() else None)
            course_card = fee_flow.build_course_selection_card(fee_flow.SCHOOLS_DATA[2], level=lvl)
            async for ev in _say(_AGRICULTURE_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[course_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "COMP_APP_FEE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step=None)
            lvl = "ug" if "bca" in message.lower() else ("pg" if "mca" in message.lower() else None)
            course_card = fee_flow.build_course_selection_card(fee_flow.SCHOOLS_DATA[0], level=lvl)
            async for ev in _say(_COMP_APP_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[course_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "DESIGN_FEE_QUERY":
        if client is None or _is_mock_or_test_client(client):
            await set_state(fee_tree_step=None)
            course_card = fee_flow.build_course_selection_card(fee_flow.SCHOOLS_DATA[5], level="ug")
            async for ev in _say(_DESIGN_FEE_TEXT, message, session_id, conversation_id,
                                 cards=[course_card],
                                 suggestions=["Calculate my scholarship", "Hostel details",
                                              "Special category concessions", "How do I apply?"]):
                yield ev
            return

    if intent == "HOSTEL_INFO_QUERY":
        from app.services.card_service import HOSTEL_FACILITIES_CARD
        if HOSTEL_FACILITIES_CARD not in cards:
            cards.append(HOSTEL_FACILITIES_CARD)

    elif intent == "HOSTEL_FEE_QUERY":
        from app.services.card_service import HOSTEL_FEE_CARD
        if HOSTEL_FEE_CARD not in cards:
            cards.append(HOSTEL_FEE_CARD)

    elif intent == "COMBINED_FEE_HOSTEL_QUERY":
        from app.services.card_service import BTECH_CSE_WITH_HOSTEL_FEE_CARD
        if BTECH_CSE_WITH_HOSTEL_FEE_CARD not in cards:
            cards.append(BTECH_CSE_WITH_HOSTEL_FEE_CARD)

    if intent == "CAMPUS_CANTEEN_QUERY":
        if client is None:
            async for ev in _say(_CAMPUS_CANTEEN_TEXT, message, session_id, conversation_id,
                                 suggestions=_CAMPUS_CANTEEN_CHIPS):
                yield ev
            return

    if intent == "ACADEMIC_EVALUATION_QUERY":
        if client is None:
            async for ev in _say(_ACADEMIC_EVALUATION_TEXT, message, session_id, conversation_id,
                                 suggestions=_ACADEMIC_EVALUATION_CHIPS):
                yield ev
            return

    if intent == "LAB_FACILITIES_QUERY":
        if client is None:
            async for ev in _say(_LAB_FACILITIES_TEXT, message, session_id, conversation_id,
                                 suggestions=_LAB_FACILITIES_CHIPS):
                yield ev
            return

    # First interaction direct question name collection:
    has_replied = any(h.get("role") in ("model", "assistant") for h in history)
    if not has_replied and client is None and not profile.get("name") and not conv_state.get("name_asked"):
        if extracted_name:
            await set_state(name_asked=True, awaiting_name=False)
        elif _is_first_interaction_name_query(message) and not intents.is_cancel_contact(message) and not intents.is_number_update(message) and not intents.is_visit_request(message) and intent != "CAMPUS_VISIT_INFO":
            await set_state(pending_user_question=message, awaiting_name=True, name_asked=True)
            ack_text = _ack_question_for_name(message, session_id)
            async for ev in _say(ack_text, message, session_id, conversation_id, suggestions=_SMALL_TALK_CHIPS):
                yield ev
            return

    # ---- 2. "Don't call me" / "cancel my visit": run the cancel tool, report what really happened
    pending = conv_state.get("pending_action")
    has_open_request = bool(profile.get("last_lead_id"))
    if intent not in ("DATE_CONFIRMATION_YES", "DATE_CONFIRMATION_NO") and \
            intents.is_cancel_contact(message, has_open_request or bool(pending)):
        result = await _run_action("cancel_contact_request", {"reason": message[:200]}, ctx, used, cards)
        for ev in _tool_events("cancel_contact_request", result):
            yield ev
        if pending and result.get("status") == "nothing_to_cancel":
            text = ("No problem, I will not arrange it. Nothing was saved, so nobody will call you. "
                    "Is there anything else about SR University I can help you with?")
        else:
            text = _cancel_text(result)
        await clear_pending()
        await set_state(awaiting_date_confirmation=False, pending_visit_date=None)
        async for ev in _say(text, message, session_id, conversation_id, used, cards,
                             ["B.Tech CSE fees", "Scholarship slabs", "Hostel details"]):
            yield ev
        return

    # ---- 2b. "Change my number" / "my number is ...": one place for the number, everywhere ------
    phone = tools.find_phone(message)
    asked_for_call = intents.is_callback_request(message)
    wants_update = intents.is_number_update(message) or (pending == "update_number" and bool(phone))
    if wants_update and not asked_for_call and intent not in ("DATE_CONFIRMATION_YES", "DATE_CONFIRMATION_NO"):
        if phone:
            result = await _run_action("update_contact_details", {"phone": phone}, ctx, used, cards)
            for ev in _tool_events("update_contact_details", result):
                yield ev
            await clear_pending()
            last4 = result.get("phone_last4")
            if result.get("status") == "updated":
                text = f"Done. Your mobile number is now the one ending {last4}."
                if result.get("saved_request_updated"):
                    text += " Your saved request has the new number too."
                text += " You can see or change it any time from the menu under My details."
            elif result.get("status") == "unchanged":
                text = f"That is already the number I have for you (ending {last4}). Nothing needed to change."
            else:
                text = (f"Sorry, I could not update your number just now. Please try again in a minute or call "
                        f"the Admissions Office at {config.ADMISSIONS_PHONE}.")
        else:
            wrong = tools.find_bad_phone(message, min_digits=5)
            await set_state(pending_action="update_number", pending_turns=0)
            text = (f"\"{wrong}\" does not look like a valid 10-digit mobile number. Please type the correct one."
                    if wrong else
                    "Sure. Please type your new 10-digit mobile number here and I will update it. You can also "
                    "change it yourself from the menu under My details.")
        async for ev in _say(text, message, session_id, conversation_id, used, cards,
                             ["B.Tech CSE fees", "Scholarship slabs", "Hostel details"]):
            yield ev
        return
    if phone and intents.is_number_statement(message) and not asked_for_call:
        # "my mobile number is ...": remember it (and fix a saved request) before answering
        await _run_action("update_contact_details", {"phone": phone}, ctx, used, cards)
        profile = ctx["profile"]

    # ---- 3. Callback / campus visit requests: save them as soon as name + number are known ----
    bad_phone = None if phone else tools.find_bad_phone(message, min_digits=5 if asked_for_call else 8)
    # A bare "Ravi Kumar" counts as a name only when the agent has just asked for one.
    last_reply = next((h.get("text", "") for h in reversed(history) if h.get("role") in ("model", "assistant")), "")
    name_known = bool(profile.get("name") or conv_state.get("pending_name"))
    awaiting_name = bool(pending and not name_known and (
        conv_state.get("pending_phone") or re.search(r"\bname\b", last_reply, re.IGNORECASE)))
    name = intents.extract_name(message, bare_ok=awaiting_name)
    visit_words = intent in ("CAMPUS_VISIT_BOOKING", "CAMPUS_VISIT_BOOKING_WITH_DATE") or intents.is_visit_request(message)

    action = None
    if pending == "campus_visit" and not visit_words and not phone and not bad_phone and not asked_for_call:
        await set_state(pending_action=None, active_topic=None)
        pending = None

    if asked_for_call:
        # "Ask counsellor to call me" / "Ask admissions to call me" right after visit guidance is a visit callback.
        action = "campus_visit" if (pending == "campus_visit" or visit_words) else "callback"
    elif visit_words and (phone or bad_phone or pending == "campus_visit"):
        action = "campus_visit"
    elif pending in ("callback", "campus_visit") and intent not in ("DATE_CONFIRMATION_YES", "DATE_CONFIRMATION_NO") and \
            (phone or bad_phone or name or (pending == "campus_visit" and intent == "CAMPUS_VISIT_BOOKING_WITH_DATE")):
        action = pending
    elif phone:
        action = _pending_from_history(history)  # the agent had asked for the number

    action_note = None
    if action:
        # A number the student gave earlier (in the chat or in My details) is used as it is: they
        # are not asked for it again. The reply names its last four digits so a wrong one is noticed.
        use_phone = phone or conv_state.get("pending_phone") or tools.clean_phone(profile.get("phone") or "")
        use_name = name or profile.get("name") or conv_state.get("pending_name")
        visit = tools.resolve_campus_visit_date(message, today=date.today()) if action == "campus_visit" else None
        what = "campus visit callback" if action == "campus_visit" else "callback"
        await set_state(pending_action=action, pending_phone=use_phone, pending_name=use_name, pending_turns=0)
        if action == "campus_visit":
            await set_state(active_topic="campus_visit")

        text = None
        if bad_phone and not use_phone:
            text = (f"\"{bad_phone}\" does not look like a valid 10-digit mobile number. Please send the correct "
                    f"number and I will arrange the {what}.")
        elif use_phone and not use_name:
            text = "Thank you. May I have your full name, so the admissions team knows whom to ask for?"
        elif action == "campus_visit" and asked_for_call and not use_phone and not use_name and not bad_phone:
            text = (f"Sure. Please share your full name and 10-digit mobile number, and I will ask the admissions "
                    f"team to call you{' about visiting the campus' if action == 'campus_visit' else ''}.")
        elif name and not use_phone and len(message.split()) <= 6:
            text = (f"Thank you, {_first_name(name)}. Please send your 10-digit mobile number so the "
                    f"admissions team can reach you about the {what}.")
        elif use_phone and use_name:
            if action == "campus_visit":
                args = {"name": use_name, "phone": use_phone, "consent": True,
                        "preferred_date": (visit or {}).get("human") if (visit or {}).get("date") and
                                          not (visit or {}).get("is_past") else "",
                        "visitors": intents.extract_visitors(message) or 1}
                tool_name = "request_campus_visit_callback"
            else:
                args = {"name": use_name, "phone": use_phone, "consent": True,
                        "preferred_time": intents.extract_preferred_time(message)}
                tool_name = "request_counsellor_callback"
            result = await _run_action(tool_name, args, ctx, used, cards)
            for ev in _tool_events(tool_name, result):
                yield ev
            text = _saved_text(action, result, args.get("preferred_time"))
            if result.get("status") == "saved":
                await clear_pending()
                await set_state(awaiting_date_confirmation=False, pending_visit_date=None, confirmed_visit_date=None, active_topic=None)
                if _has_other_question(message, name):
                    # The request is saved; let the model answer the rest of the message too.
                    action_note = (f"The system has ALREADY saved this student's {what} request in this turn: "
                                   f"name {result.get('name')}, phone ending "
                                   f"{result.get('phone_last4')}. Confirm that in one line, then "
                                   f"answer their other question. Do not call the {tool_name} tool again.")
        if text and not action_note:
            async for ev in _say(text, message, session_id, conversation_id, used, cards,
                                 ["How to reach the campus", "B.Tech CSE fees", "Hostel details"]
                                 if action == "campus_visit" else
                                 ["B.Tech CSE fees", "Scholarship slabs", "Hostel details"]):
                yield ev
            return
        canned_action_text = text
        if not text:
            action = None  # nothing to do yet: the guided visit flow / the model takes it from here
    else:
        canned_action_text = None

    # ---- 4. Campus tour dispatch & in-person visit guidance -----------------
    if conv_state.get("awaiting_date_confirmation") or conv_state.get("pending_visit_date"):
        await set_state(awaiting_date_confirmation=False, pending_visit_date=None, confirmed_visit_date=None)

    # 4a. Ambiguous / General Campus Tour -> Directly offer the two options
    if intent == "CAMPUS_TOUR_DISPATCH" and not action:
        await set_state(active_topic="campus_tour")
        async for ev in _say(_CAMPUS_TOUR_CHOICE_TEXT, message, session_id, conversation_id,
                             used, cards, _CAMPUS_TOUR_CHOICE_CHIPS):
            yield ev
        return

    # 4b. Explicit Virtual Tour / Videos & Info
    if intent == "CAMPUS_TOUR_VIRTUAL" and not action:
        await set_state(active_topic="campus_tour_virtual")
        video_result = await _run_action("get_university_videos", {"topic": "campus tour"}, ctx, used, cards)
        for ev in _tool_events("get_university_videos", video_result):
            yield ev
        async for ev in _say(_VIRTUAL_TOUR_TEXT, message, session_id, conversation_id,
                             used, cards, _VIRTUAL_TOUR_CHIPS):
            yield ev
        return

    # 4c. In-Person Campus Visit
    asks_to_visit = intents.is_visit_request(message)
    visit = (tools.resolve_campus_visit_date(message, today=date.today())
             if intent.startswith("CAMPUS_VISIT") or asks_to_visit else {})
    detail_question = bool(_VISIT_DETAIL.search(message))
    wants_visit = not detail_question and (
        intent == "CAMPUS_VISIT_BOOKING" or asks_to_visit
        or (intent == "CAMPUS_VISIT_BOOKING_WITH_DATE" and visit.get("date"))
        or (intent == "CAMPUS_VISIT_INFO" and len(message.split()) <= 4))
    if wants_visit and not action:
        await set_state(active_topic="campus_visit", pending_action="campus_visit", pending_turns=0)
        contact = await _run_action("get_contact_and_apply_links", {"topic": "campus visit"}, ctx, used, cards)
        for ev in _tool_events("get_contact_and_apply_links", contact):
            yield ev
        async for ev in _say(_visit_guide(visit.get("human") if visit.get("date") else None), message,
                             session_id, conversation_id, used, cards, _VISIT_CHIPS):
            yield ev
        return
    if intent in ("DATE_CONFIRMATION_YES", "DATE_CONFIRMATION_NO"):
        intent = "GENERAL"  # an old chat that was waiting for a visit date: answer normally

    # ---- 4b. Course Selection & Fee Enquiry Flow ----------------
    intake_decision = None
    if not action_note and not action and conv_state.get("pending_action") not in ("callback", "campus_visit") \
            and intent not in ("CAMPUS_VISIT_BOOKING", "CAMPUS_VISIT_BOOKING_WITH_DATE", "DATE_CONFIRMATION_YES",
                               "DATE_CONFIRMATION_NO"):
        intake_state = dict(conv_state.get("fee_intake") or {})
        if not intake_state.get("program"):
            candidate_p = conv_state.get("fee_flow_prog") or conv_state.get("active_program") or (profile.get("program_interest") if profile else None)
            if candidate_p:
                intake_state["program"] = candidate_p

        async def _apply_intake_updates(state_dict: dict):
            await set_state(fee_intake=state_dict)
            for k in ("program", "board", "board_label", "board_key", "academic_stage", "stage_label",
                      "raw_marks", "max_marks", "percent", "admission_route", "route_label",
                      "eapcet_rank", "jee_percentile"):
                val = state_dict.get(k)
                if val is not None:
                    if k == "program":
                        if profile is not None:
                            profile["program_interest"] = val
                        await memory.update_profile(session_id, program_interest=val)
                        await set_state(active_program=val, fee_flow_prog=val)
                    else:
                        if profile is not None:
                            profile[k] = val
                        await memory.update_profile(session_id, **{k: val})

        # 0. Check affordability and concession multi-step flow
        if conv_state.get("affordability_flow") or affordability.is_affordability_query(message):
            afford_res = affordability.process_affordability_flow(message, profile, conv_state)
            if afford_res is not None:
                await set_state(**afford_res["new_state"])
                async for ev in _say(afford_res["text"], message, session_id, conversation_id,
                                     cards=afford_res.get("cards", []),
                                     suggestions=afford_res.get("suggestions", [])):
                    yield ev
                return

        # 1. If fee intake is active, or user asks specifically about scholarship/calculation, prioritize fee intake
        low_msg = (message or "").lower()
        is_other_fee_inquiry = bool(re.search(
            r"\b(?:other\s+fees?|other\s+academic(?:\s*/\s*university|\s+university)?\s+charges?|other\s+charges?|annual\s+charges?|"
            r"university\s+charges?|additional\s+fees?|additional\s+charges?|enrolment\s+fee|enrollment\s+fee|application\s+form\s+fee|"
            r"specialisation\s+fee|specialization\s+fee|phd\s+fee|"
            r"fees?\s+(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee)|"
            r"(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee))\b",
            low_msg,
        ))

        is_scholarship_calc_q = not is_other_fee_inquiry and bool(re.search(
            r"\b(?:schol\w*|waiver|concession|discount|fee\s+assessment|scholarship\s+assessment|assessment\s+form|"
            r"calculate\s+(?:[\w\s]+\s+)?(?:fee|tuition|scholarship)|fee\s+calculation|my\s+fee|expected\s+scholarship|"
            r"scholarship\s+counsell?or|fee\s+counsell?or)\b",
            low_msg,
        ))
        if bool(re.search(
            r"\b(?:what\s+scholarships|which\s+scholarships|scholarships\s+available|scholarship\s+options|list\s+of\s+scholarships)\b",
            low_msg,
        )):
            is_scholarship_calc_q = False
        if is_other_fee_inquiry and conv_state.get("fee_intake"):
            await set_state(fee_intake=None)
            intake_state = {}
        is_bare_score_msg = bool(re.match(
            r"^\s*(?:i\s+(?:got|scored|have|secured|obtained)\s+)?\d{2,4}(?:\.\d+)?\s*(?:marks?|%|percent)?\s*$",
            low_msg,
        )) or bool(re.fullmatch(r"\s*\d{2,4}(?:\.\d+)?\s*%?\s*", low_msg))
        is_branch_guidance = (intent == "BRANCH_GUIDANCE_QUERY") or intents.is_branch_guidance_query(message)
        is_seat_guarantee = (intent == "ADMISSION_GUARANTEE_QUERY") or bool(intents._ADMISSION_GUARANTEE_PATTERN.search(message))
        is_future_year = (intent == "FUTURE_YEAR_FEE_QUERY") or bool(intents._FUTURE_YEAR_FEE_PATTERN.search(message))
        if is_seat_guarantee or is_future_year:
            is_scholarship_calc_q = False
            if conv_state.get("fee_intake"):
                await set_state(fee_intake=None)
                intake_state = {}

        intake_in_progress = bool((conv_state.get("fee_intake") or {}).get("waiting_for"))
        if not is_other_fee_inquiry and not is_branch_guidance and not is_seat_guarantee and not is_future_year and (intake_in_progress or is_scholarship_calc_q or (is_bare_score_msg and client is None)):
            intake_decision = fee_intake.decide(message, profile, intake_state)
            if intake_decision and intake_decision["action"] == "ask":
                await _apply_intake_updates(intake_decision["state"])
                async for ev in _say(intake_decision["text"], message, session_id, conversation_id,
                                     cards=intake_decision.get("cards", []),
                                     suggestions=intake_decision["chips"]):
                    yield ev
                return
            elif intake_decision and intake_decision["action"] == "calculate" and intake_decision.get("counsellor") and not _is_mock_or_test_client(client):
                await _apply_intake_updates(intake_decision["state"])
                fee_args = dict(intake_decision["args"])
                fee_result = await tools.run_tool("calculate_fee", fee_args, ctx)
                if fee_result.get("status") == "ok":
                    c_text = format_counsellor_assessment(fee_result, intake_decision.get("counsellor_details", {}))
                    chips = ["Hostel fee details", "Campus visit", "Talk to an admission counsellor", "Explore other branches"]
                    for ev in _tool_events("calculate_fee", fee_result):
                        yield ev
                    async for ev in _say(c_text, message, session_id, conversation_id,
                                         used=[{"name": "calculate_fee", "status": "ok", "is_action": False}],
                                         cards=[{"type": "calculate_fee", "data": fee_result}],
                                         suggestions=chips):
                        yield ev
                    return

        # 2. Check exploratory school & course browsing flow ONLY when user is actively in selection or asked to explore schools
        in_selection_flow = conv_state.get("fee_flow_state") in ("awaiting_school_selection", "awaiting_course_selection")
        wants_course_explore = any(k in low_msg for k in ("explore programs", "explore schools", "browse courses", "browse schools", "change school", "different course", "change programme"))
        if not is_branch_guidance and (in_selection_flow or wants_course_explore or _is_mock_or_test_client(client)):
            flow_result = fee_flow.process_fee_flow(message, session_id, profile, conv_state)
            if flow_result is not None:
                await set_state(**flow_result["new_state"])
                async for ev in _say(flow_result["text"], message, session_id, conversation_id,
                                     cards=flow_result.get("cards", []),
                                     suggestions=flow_result.get("suggestions", [])):
                    yield ev
                return

        # 3. Fallback check for fee intake ONLY if user wants to calculate fee
        if not is_other_fee_inquiry and not is_branch_guidance and not is_seat_guarantee and not is_future_year and (is_scholarship_calc_q or intake_in_progress):
            if not intake_decision:
                intake_decision = fee_intake.decide(message, profile, intake_state)
            if intake_decision and intake_decision["action"] == "ask":
                await _apply_intake_updates(intake_decision["state"])
                async for ev in _say(intake_decision["text"], message, session_id, conversation_id,
                                     cards=intake_decision.get("cards", []),
                                     suggestions=intake_decision["chips"]):
                    yield ev
                return
            elif intake_decision and intake_decision["action"] == "calculate" and intake_decision.get("counsellor") and not _is_mock_or_test_client(client):
                await _apply_intake_updates(intake_decision["state"])
                fee_args = dict(intake_decision["args"])
                fee_result = await tools.run_tool("calculate_fee", fee_args, ctx)
                if fee_result.get("status") == "ok":
                    c_text = format_counsellor_assessment(fee_result, intake_decision.get("counsellor_details", {}))
                    chips = ["Hostel fee details", "Campus visit", "Talk to an admission counsellor", "Explore other branches"]
                    for ev in _tool_events("calculate_fee", fee_result):
                        yield ev
                    async for ev in _say(c_text, message, session_id, conversation_id,
                                         used=[{"name": "calculate_fee", "status": "ok", "is_action": False}],
                                         cards=[{"type": "calculate_fee", "data": fee_result}],
                                         suggestions=chips):
                        yield ev
                    return

        if intake_decision and not intake_decision.get("counsellor"):
            await set_state(fee_intake=None)

    # ---- 5. Everything else: the model, with tools --------------------------------------------
    contents = [types.Content(role=h["role"], parts=[types.Part.from_text(text=h["text"])])
                for h in history]
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=message)]))

    # First lines of earlier replies, so the model does not start every answer the same way.
    assistant_openings = []
    for h in history:
        if h.get("role") in ("model", "assistant"):
            for line in h.get("text", "").split("\n"):
                line = line.strip()
                if line and not line.startswith(("#", ">", "|", "```", "•", "-", "*")):
                    assistant_openings.append(line)
                    break
    variant_id = (len(assistant_openings) % 6) + 1
    from app.services.rag_service import determine_about_sru_angle, is_about_sru_query
    about_sru_angle = (
        determine_about_sru_angle("\n".join(f"{h.get('role')}: {h.get('text', '')}" for h in history), message)
        if is_about_sru_query(message) else 1)

    pending = conv_state.get("pending_action")
    if pending and not action:
        turns = int(conv_state.get("pending_turns") or 0) + 1
        if turns > 3:  # the student moved on; stop nudging
            await clear_pending()
            pending = None
        else:
            await set_state(pending_turns=turns)

    # The same first question (often a suggestion button) from a student we know nothing about
    # gets the saved answer instead of a new model call.
    personal = any(profile.get(k) not in (None, "") for k in memory.PUBLIC_PROFILE_KEYS)
    cacheable = (client is None and config.AGENT_ANSWER_CACHE_SECONDS > 0 and not history and not personal
                 and not pending and not action_note and not tools.find_phone(message))
    if cacheable:
        saved = await memory.get_cached_answer(_cache_key(message), config.AGENT_ANSWER_CACHE_SECONDS)
        if saved:
            async for ev in _say(saved["answer"], message, session_id, conversation_id,
                                 saved.get("used", []), saved.get("cards", []), saved.get("suggestions", [])):
                yield ev
            return

    if is_about_sru_query(message):
        from app.services.card_service import generate_cards
        why_cards = generate_cards(message, "", session_id=session_id)
        for wc in why_cards:
            if wc not in cards:
                cards.append(wc)

    # Do the look-ups the code can do for free, so the model can usually answer in ONE call:
    # the fee calculation for a plain fee question, and the handbook passages for everything else.
    prefetched_fee = None
    if intake_decision and intake_decision["action"] == "calculate":
        fee_args = dict(intake_decision["args"])
        hostel_args = _fee_args_from_message(message, profile) or {}
        if hostel_args.get("hostel"):
            fee_args["hostel"] = hostel_args["hostel"]
    else:
        fee_args = _fee_args_from_message(message, profile) if not action_note else None
    if fee_args:
        fee_result = await tools.run_tool("calculate_fee", fee_args, ctx)
        if fee_result.get("status") == "ok":
            prefetched_fee = fee_result
    fee_note = None
    if prefetched_fee:
        import json as _json
        fee_note = _json.dumps({k: prefetched_fee[k] for k in _FEE_KEYS if prefetched_fee.get(k) is not None},
                               ensure_ascii=False)
        details = (intake_decision or {}).get("details") or {}
        if details.get("board"):
            fee_note += f"\nBoard given by the student: {details.get('board_label') or details['board']}."
        if details.get("no_entrance"):
            fee_note += "\nThe student has no JEE Main / EAPCET score."
        fee_note += (f"\nOfficial fee & scholarship calculator to mention: {fee_intake.FEE_PORTAL_URL}")
    prefetched_faculty = None
    if not prefetched_fee and not action_note and faculty.is_faculty_question(message):
        fac = await tools.run_tool("find_faculty", {"query": message}, ctx)
        if fac.get("status") == "ok":
            prefetched_faculty = fac
    faculty_note = None
    if prefetched_faculty:
        import json as _json
        faculty_note = _json.dumps({k: v for k, v in prefetched_faculty.items() if k != "status"},
                                   ensure_ascii=False)[:3500]
    search_q = _contextual_query(message, history, active_topic=active_topic, active_program=active_program)
    passages = "" if (prefetched_fee or prefetched_faculty) else _handbook_context(search_q)

    models = []
    for m in (config.AGENT_MODEL, *_FALLBACK_MODELS):
        if m and m not in models:
            models.append(m)
    tool_decl = _tool_declarations()
    final = ""
    link = {"fixed": client, "key": None, "models": models, "model_idx": 0, "error_kind": None,
            "thinking": True, "deadline": time.monotonic() + max(1.0, config.AGENT_TOTAL_TIMEOUT)}
    # Words are shown while Gemini writes them, except when the reply is about a callback / visit
    # request or a cancellation: those are checked for honesty first and only then shown.
    live_ok = not (pending or action_note or _CANCEL_ASK.search(message) or intents.is_callback_request(message))
    streamed = ""
    try:
        link["key"] = None if client else _ring.next_key()
        if link["fixed"] is None and not link["key"]:
            link["fixed"] = get_client()
        last_assistant_text = next(
            (h.get("text", "") for h in reversed(history) if h.get("role") in ("model", "assistant")),
            ""
        )
        student_name = ctx["profile"].get("name") or ""
        first_name = _first_name(student_name)
        name_used_recently = bool(
            first_name and re.search(rf"\b{re.escape(first_name)}\b", last_assistant_text, re.IGNORECASE)
        )

        for round_no in range(config.AGENT_MAX_TOOL_ROUNDS + 1):
            last_round = round_no == config.AGENT_MAX_TOOL_ROUNDS
            cfg = types.GenerateContentConfig(
                system_instruction=build_system_prompt(
                    ctx["profile"], variant_id=variant_id, used_openings=assistant_openings,
                    about_sru_angle=about_sru_angle, pending_action=pending, action_note=action_note,
                    handbook_passages=passages, fee_result=fee_note, faculty_result=faculty_note,
                    persona=persona, name_used_recently=name_used_recently),
                tools=[tool_decl],
                temperature=0.2,
                max_output_tokens=900,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                # On the last round the model must answer in words, not call more tools.
                tool_config=types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
                    mode="NONE" if last_round else "AUTO")),
            )
            if live_ok and _can_stream(link):
                resp, round_text = None, ""
                async for kind, value in _generate_stream(contents, cfg, link):
                    if kind == "text":
                        round_text += value
                        streamed += value
                        yield {"type": "token", "delta": value}
                    else:
                        resp = value
            else:
                resp = await _generate(contents, cfg, link)
            if resp is None:
                link["error_kind"] = "busy"
                raise RuntimeError("Model stream produced no response")
            calls = resp.function_calls or []
            if not calls:
                final = (resp.text or "").strip()
                if not final and not last_round and round_no == 0:
                    # An empty reply (the model sometimes returns nothing): ask once more, plainly.
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(
                        text="(Please answer the student's last message in a few clear sentences.)")]))
                    continue
                break

            contents.append(resp.candidates[0].content)  # keep the model's turn exactly as returned
            result_parts = []
            for call in calls:
                label = tools.TOOLS[call.name][1] if call.name in tools.TOOLS else "Working"
                yield {"type": "tool", "name": call.name, "status": "running", "label": label}
                result = await tools.run_tool(call.name, dict(call.args or {}), ctx)
                error = result.pop("_error", None)
                if error:
                    log.error("tool %s failed: %s", call.name, error)
                log.info("tool=%s status=%s session=%s", call.name, result.get("status"), session_id)
                used.append({"name": call.name, "status": result.get("status"),
                             "is_action": call.name in tools.ACTION_TOOLS})
                is_card_ready = call.name in CARD_TOOLS and result.get("status") in ("calculated", "saved", "ok")
                if call.name == "calculate_fee":
                    prefetched_fee = None  # the model asked for its own calculation: show that one
                    cards[:] = [c for c in cards if c.get("type") != "calculate_fee"]
                if call.name == "find_faculty":
                    prefetched_faculty = None
                    cards[:] = [c for c in cards if c.get("type") != "find_faculty"]
                if is_card_ready:
                    cards.append({"type": call.name, "data": result})
                yield {"type": "tool", "name": call.name, "status": "done",
                       "result_status": result.get("status"),
                       "result": result if is_card_ready else None}
                result_parts.append(types.Part(function_response=types.FunctionResponse(
                    name=call.name, response=result, id=getattr(call, "id", None))))
            contents.append(types.Content(role="user", parts=result_parts))
    except Exception as exc:
        if link.get("error_kind") in ("rate", "busy"):
            # expected on the free tier: one line in the log, not a stack trace
            log.warning("model unavailable (%s) for session %s: %s", link["error_kind"], session_id, str(exc)[:160])
        else:
            log.exception("agent failed for session %s", session_id)
        if canned_action_text:  # the request itself was saved; say so even though the model failed
            async for ev in _say(canned_action_text, message, session_id, conversation_id, used, cards):
                yield ev
            return
        if not used:
            if intent == "PLACEMENT_GUARANTEE_QUERY":
                from app.services.card_service import PLACEMENT_EXCELLENCE_CARD
                reply = _select_variation(_PLACEMENT_ASSISTANCE_RESPONSES, session_id + str(len(history)))
                async for ev in _say(reply, message, session_id, conversation_id,
                                     cards=[PLACEMENT_EXCELLENCE_CARD],
                                     suggestions=_PLACEMENT_ASSISTANCE_CHIPS):
                    yield ev
                return
            if intent == "HOSTEL_INFO_QUERY":
                from app.services.card_service import HOSTEL_FACILITIES_CARD
                hostel_text = responses.get_hostel_info_text(session_id, message)
                async for ev in _say(hostel_text, message, session_id, conversation_id,
                                     cards=[HOSTEL_FACILITIES_CARD],
                                     suggestions=_HOSTEL_INFO_CHIPS):
                    yield ev
                return
            if intent == "HOSTEL_MESS_QUERY":
                async for ev in _say(_HOSTEL_MESS_TEXT, message, session_id, conversation_id,
                                     suggestions=_HOSTEL_MESS_CHIPS):
                    yield ev
                return
            if intent == "HOSTEL_CURFEW_RULES_QUERY":
                async for ev in _say(_HOSTEL_CURFEW_RULES_TEXT, message, session_id, conversation_id,
                                     suggestions=_HOSTEL_CURFEW_CHIPS):
                    yield ev
                return
            if intent == "HOSTEL_SAFETY_QUERY":
                async for ev in _say(responses._HOSTEL_SAFETY_TEXT, message, session_id, conversation_id,
                                     suggestions=_HOSTEL_SAFETY_CHIPS):
                    yield ev
                return
            if intent == "HOSTEL_FEE_QUERY":
                from app.services.card_service import HOSTEL_FEE_CARD
                async for ev in _say(_HOSTEL_FEE_TEXT, message, session_id, conversation_id,
                                     cards=[HOSTEL_FEE_CARD],
                                     suggestions=_HOSTEL_FEE_CHIPS):
                    yield ev
                return
            if intent == "COMBINED_FEE_HOSTEL_QUERY":
                from app.services.card_service import BTECH_CSE_WITH_HOSTEL_FEE_CARD
                async for ev in _say(_COMBINED_HOSTEL_FEE_TEXT, message, session_id, conversation_id,
                                     cards=[BTECH_CSE_WITH_HOSTEL_FEE_CARD],
                                     suggestions=_COMBINED_HOSTEL_FEE_CHIPS):
                    yield ev
                return
            if is_other_fee_inquiry:
                from app.services.card_service import OTHER_FEES_CARD
                async for ev in _say(responses._OTHER_FEES_TEXT, message, session_id, conversation_id,
                                     cards=[OTHER_FEES_CARD],
                                     suggestions=responses._OTHER_FEES_CHIPS):
                    yield ev
                return
            if is_about_sru_query(message):
                from app.services.card_service import generate_cards
                why_text = responses.get_why_choose_sru_text(variant_id=variant_id, session_id=session_id)
                why_cards = generate_cards(message, why_text, session_id=session_id)
                async for ev in _say(why_text, message, session_id, conversation_id,
                                     cards=why_cards,
                                     suggestions=responses._WHY_CHOOSE_SRU_CHIPS):
                    yield ev
            if intent == "BRANCH_GUIDANCE_QUERY" or intents.is_branch_guidance_query(message):
                raw_marks = profile.get("raw_marks") or early_details.get("raw_marks")
                bg_text = responses.get_branch_guidance_text(raw_marks, session_id=session_id)
                async for ev in _say(bg_text, message, session_id, conversation_id,
                                     suggestions=responses._BRANCH_GUIDANCE_CHIPS):
                    yield ev
                return

            offline = _offline_fee_reply(message, ctx, prefetched_fee)
            if offline:
                text, fee = offline
                for ev in _tool_events("calculate_fee", fee):
                    yield ev
                async for ev in _say(text, message, session_id, conversation_id,
                                     [{"name": "calculate_fee", "status": "ok", "is_action": False}],
                                     [{"type": "calculate_fee", "data": fee}]):
                    yield ev
                return

        if link.get("error_kind") in ("rate", "busy"):
            # When model is unavailable (quota, rate limit, or sandbox network): give handbook passage if one fits, else say what still works.
            text = (None if used else (_offline_knowledge_reply(search_q, session_id) or _offline_knowledge_reply(message, session_id))) or get_limit_reply(session_id)
            async for ev in _say(text, message, session_id, conversation_id, used, cards,
                                 ["CSE fee with 85%", "Call me", "Plan a campus visit"]):
                yield ev
            return
        yield {"type": "error", "detail": get_fallback_text(session_id)}
        return

    if prefetched_fee:  # the model answered from the calculation the code had already done
        used.append({"name": "calculate_fee", "status": "ok", "is_action": False})
        cards.append({"type": "calculate_fee", "data": prefetched_fee})
        for ev in _tool_events("calculate_fee", prefetched_fee):
            yield ev

    if prefetched_faculty:  # the model answered from the faculty profiles the code had found
        used.append({"name": "find_faculty", "status": "ok", "is_action": False})
        cards.append({"type": "find_faculty", "data": prefetched_faculty})
        for ev in _tool_events("find_faculty", prefetched_faculty):
            yield ev

    # ---- 6. Honesty checks: the words must match what the tools actually did ------------------
    statuses = {(t["name"], t["status"]) for t in used}
    saved_now = any(t["is_action"] and t["status"] == "saved" for t in used)
    if any(name_ == "cancel_contact_request" for name_, _ in statuses) or (
            final and _claims_cancelled(final) and _CANCEL_ASK.search(message)
            and not _NOT_ABOUT_CONTACT.search(message)):
        if ("cancel_contact_request", "cancelled") not in statuses:
            ran = next((t for t in used if t["name"] == "cancel_contact_request"), None)
            if ran is None:
                result = await _run_action("cancel_contact_request", {"reason": message[:200]}, ctx, used, cards)
                for ev in _tool_events("cancel_contact_request", result):
                    yield ev
                final = _cancel_text(result)
            elif _claims_cancelled(final):
                final = _cancel_text({"status": ran["status"], "reference": str(profile.get("last_lead_id", ""))[:8],
                                      "request_type": profile.get("last_lead_type")})
    elif final and _claims_saved(final) and not saved_now and not (ctx.get("profile") or {}).get("last_lead_id"):
        is_visit = bool(re.search(r"\bvisit\b|\btour\b", final + " " + message, re.IGNORECASE))
        await set_state(pending_action="campus_visit" if is_visit else "callback", pending_turns=0)
        final = ("I have not saved anything yet. To ask the admissions team to call you about a "
                 + ("campus visit, please send your full name and 10-digit mobile number. I can't book or confirm "
                    "a visit myself."
                    if is_visit else "callback, please send your full name and 10-digit mobile number."))
    if saved_now:
        await clear_pending()

    final = final or canned_action_text or get_fallback_text(session_id)
    from app.services.guardrail_service import normalize_positive_brand_advocacy
    final = normalize_positive_brand_advocacy(final)
    if not streamed:
        for piece in _chunks(final):
            yield {"type": "token", "delta": piece}
    # (when the words were streamed live, the 'done' event carries the final text, which the
    # browser shows in place of what it streamed)
    await memory.append_history(session_id, message, final, conversation_id)

    # ---- 7. Cards and follow-up suggestions ---------------------------------------------------
    try:
        from app.services.card_service import generate_cards

        # Videos are matched on their own titles and keywords (video_service.get_keyword_videos),
        # so no embedding call is spent here.
        query_embedding = None

        seen_card_types = set()
        for h in history:
            for c in h.get("cards") or []:
                if isinstance(c, dict) and c.get("type"):
                    seen_card_types.add(c["type"])
        for c in cards:
            if isinstance(c, dict) and c.get("type"):
                seen_card_types.add(c["type"])

        contextual_cards = generate_cards(
            user_message=message, answer=final, profile=ctx.get("profile"),
            session_id=session_id, seen_card_types=seen_card_types,
            query_embedding=query_embedding, keyword_videos=True)
        personalised = any(t["name"] in _FEE_TOOLS for t in used)
        has_video_card = any(c.get("type") in ("get_university_videos", "video_recommendations") for c in cards)
        for c in contextual_cards:
            if personalised and c.get("type") == "fee_breakdown":
                continue  # the student already has their own numbers; no generic table underneath
            if has_video_card and c.get("type") in ("get_university_videos", "video_recommendations"):
                continue  # tool already provided video card; do not duplicate
            if c not in cards:
                cards.append(c)
    except Exception as card_err:
        log.warning("Could not generate contextual cards for agent: %s", card_err)

    suggestions = []
    try:
        department = None
        fac = next((c["data"] for c in cards if c.get("type") == "find_faculty"), None)
        if fac:
            department = fac.get("department") or next(
                (p.get("department") for p in fac.get("faculty") or [] if p.get("department")), None)
        suggestions = followups.suggest(message, used, ctx.get("profile"), department, history=history, active_topic=active_topic)
    except Exception as sugg_err:
        log.warning("Could not generate suggestions for agent: %s", sugg_err)

    if cacheable and final != FALLBACK and not any(t["is_action"] for t in used):
        await memory.set_cached_answer(_cache_key(message), {
            "answer": final, "used": used, "cards": cards, "suggestions": suggestions})
    turn_telemetry.total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    observability.record_policy_telemetry(turn_telemetry)
    yield _done(conversation_id, final, used, cards, suggestions, telemetry=turn_telemetry.to_dict())
