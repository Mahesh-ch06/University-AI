"""Full-stack review server: the real FastAPI app (PostgreSQL, Redis, agent, cards). By default only the Gemini
model is replaced (no API key needed); REVIEW_MODEL=live keeps the real model. The replacement says plainly that it is a test model and reports
how many earlier turns of THIS conversation it received and what the agent knows, so restored context is visible."""
import os, re, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from google.genai import types
from app.sru_agent import agent

class ContextEchoModel:
    def __init__(self):
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        prompt = str(getattr(config, "system_instruction", "") or "")
        m = re.search(r"WHAT YOU ALREADY KNOW ABOUT THIS STUDENT: (.*)", prompt)
        earlier = max(0, (len(contents) - 1) // 2)
        items = [i.strip() for i in (m.group(1) if m else "").split(",")]
        known = ", ".join(i for i in items if i and not i.startswith(("phone", "name", "pass "))) or "nothing yet"
        known = known[:160]
        last = "".join(p.text or "" for p in contents[-1].parts)[:80]
        text = (f"(Review model: no Gemini key in this environment.) I received {earlier} earlier turn(s) of this "
                f"conversation. Your question: \"{last}\". Known about you: {known}")
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=text)]))])

# REVIEW_MODEL=live: keep the real Gemini client (keys from GEMINI_API_KEYS / GEMINI_API_KEY; in the review sandbox a
# placeholder key, the network proxy adds the real one). Default: the test model above, no key needed.
if os.environ.get("REVIEW_MODEL") != "live":
    agent.get_client = lambda *a, **k: ContextEchoModel()
import app.main as main
import uvicorn
uvicorn.run(main.app, host="127.0.0.1", port=int(os.environ.get("PORT", "8080")), log_level="warning")
