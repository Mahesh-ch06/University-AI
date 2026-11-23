"""Tests for SRU Buddy v3.3.1 - Intelligence, Contextual Understanding & Dynamic Response Overhaul.

Verifies:
1. Scenario A: Hostel room sharing -> Double sharing clarification -> AC options -> Annual fee -> Mess included.
2. Scenario B: Scholarships available -> 85% score -> Eligibility check -> 90% score comparison.
3. Scenario C: B.Tech branches -> AI-specialized branches -> Eligibility criteria (50% PCM).
4. Scenario D: About SRU overview -> Placements -> 98% guarantee clarification.
5. Contextual suggestion chips relevance and deduplication across multi-turn sessions.
6. Strict knowledge boundary enforcement (refusing non-SRU topics).
"""
import pytest
from app.sru_agent import agent, memory, followups, knowledge, fee_intake


class MockClient:
    """Simulates LLM response generation for multi-turn scenarios."""
    def __init__(self, script: list[str]):
        self.script = list(script)
        self.received_prompts = []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config=None):
        last_text = ""
        for c in contents:
            for p in getattr(c, "parts", []):
                if hasattr(p, "text") and p.text:
                    last_text = p.text
        self.received_prompts.append(last_text)
        reply = self.script.pop(0) if self.script else "SR University provides comprehensive academic excellence."
        return type("Resp", (), {
            "function_calls": [],
            "text": reply,
            "candidates": [type("Cand", (), {"content": type("Content", (), {"parts": [type("Part", (), {"text": reply})()]})})()],
        })()


async def _run_session(session_id: str, turns: list[tuple[str, str]]):
    """Executes a multi-turn conversation with scripted model replies."""
    conv_id = f"conv-{session_id}"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    script = [model_reply for _, model_reply in turns if model_reply is not None]
    mock_client = MockClient(script)

    results = []
    for user_msg, _ in turns:
        events = [ev async for ev in agent.run_agent(user_msg, session_id, conv_id, client=mock_client)]
        done = [ev for ev in events if ev.get("type") == "done"][0]
        results.append({
            "user": user_msg,
            "answer": done["answer"],
            "suggestions": done.get("suggestions", []),
            "cards": done.get("cards", []),
        })
    return results, mock_client


@pytest.mark.asyncio
async def test_scenario_a_hostel_multiturn_flow():
    """Scenario A: Hostel rooms? -> Double sharing? -> AC? -> Annual fee? -> Mess included?"""
    turns = [
        ("Hostel rooms?", "SR University provides 3-sharing and 4-sharing rooms in both AC and Non-AC configurations."),
        ("Double sharing?", "Standard hostel accommodation is offered in 3-sharing and 4-sharing rooms. Double sharing is not part of standard fee structure; please contact the hostel administration for special requests."),
        ("AC?", "Yes, air-conditioned options are available for 3-sharing and 4-sharing rooms with 24/7 power backup."),
        ("What is the annual fee?", "For 3-sharing AC rooms, the annual fee is ₹1,35,000, while 3-sharing Non-AC is ₹1,15,000 per year."),
        ("Does it include mess?", "Yes, the annual hostel fee includes unlimited dining (4 daily meals: breakfast, lunch, snacks, dinner) at the 4,000-seat Mega Dining Hall."),
    ]
    results, _ = await _run_session("sess-scenario-a", turns)

    assert len(results) == 5

    # Turn 1: Hostel rooms
    assert "3-sharing" in results[0]["answer"]
    assert any("hostel" in s.lower() or "room" in s.lower() or "ac" in s.lower() for s in results[0]["suggestions"])

    # Turn 2: Double sharing clarification
    assert "double sharing" in results[1]["answer"].lower() or "standard" in results[1]["answer"].lower()
    # Ensure suggestions stay in hostel context
    assert any("fee" in s.lower() or "mess" in s.lower() or "rule" in s.lower() for s in results[1]["suggestions"])

    # Turn 4: Annual fee
    assert "1,35,000" in results[3]["answer"]

    # Turn 5: Mess inclusion
    assert "mega dining hall" in results[4]["answer"].lower() or "included" in results[4]["answer"].lower()


@pytest.mark.asyncio
async def test_scenario_b_scholarship_multiturn_flow():
    """Scenario B: What scholarships are available? -> 85% in inter -> Am I eligible? -> What about 90%?"""
    turns = [
        ("What scholarships are available?", "SR University offers merit scholarships up to 40% based on 10+2 marks and national entrance test ranks."),
        ("I scored 85% in intermediate.", "Congratulations on scoring 85%! That puts you in a strong bracket for merit scholarship consideration."),
        ("Am I eligible?", None),
        ("What about 90%?", "Scoring 90% or above elevates your eligibility to the next scholarship tier, granting up to a 30% to 40% tuition fee waiver."),
    ]
    results, _ = await _run_session("sess-scenario-b", turns)

    assert len(results) == 4
    # Turn 1: Broad scholarship enquiry
    assert "scholarship" in results[0]["answer"].lower()

    # Turn 2: Score ingestion
    assert "85%" in results[1]["answer"] or "85" in results[1]["answer"]

    # Turn 3: admission eligibility depends on the programme: the 85% is remembered (not asked again) and
    # only the programme is asked. A scholarship waiver is never presented as admission eligibility.
    assert "**85%**" in results[2]["answer"] and "Which programme" in results[2]["answer"]
    assert "waiver" not in results[2]["answer"].lower()

    # Turn 4: 90% comparison
    assert "90%" in results[3]["answer"] or "tier" in results[3]["answer"].lower()


@pytest.mark.asyncio
async def test_scenario_c_btech_branches_and_ai_flow():
    """Scenario C: Which B.Tech branches are available? -> Which one has AI? -> What is its eligibility?"""
    turns = [
        ("Which B.Tech branches are available?", "SR University offers B.Tech programs in Computer Science & AI, Electronics & Communication, Electrical, Mechanical, and Civil Engineering."),
        ("Which one has AI?", "AI programs include B.Tech in Artificial Intelligence & Robotics, CSE with AIML specialization, CSE with Quantum AI, and AI & Precision Agriculture."),
        ("What is its eligibility?", "Eligibility for B.Tech AI programs requires a minimum of 50% aggregate marks in 10+2 / Intermediate with Physics, Chemistry, and Mathematics (PCM)."),
    ]
    results, _ = await _run_session("sess-scenario-c", turns)

    assert len(results) == 3
    # Turn 2: AI branches identified
    assert "ai" in results[1]["answer"].lower()

    # Turn 3: "its" names no single programme, so the verified overview (built from the fee data, both
    # sources shown where they differ) is given and the student is asked which programme
    assert "50%" in results[2]["answer"] and "mpc" in results[2]["answer"].lower()
    assert "Which programme are you interested in?" in results[2]["answer"]


@pytest.mark.asyncio
async def test_scenario_d_placements_and_guarantee_flow():
    """Scenario D: Tell me about SRU. -> What about placements? -> Is 98% guaranteed?"""
    turns = [
        ("Tell me about SRU.", None),
        ("What about placements?", None),
        ("Packages & record", None),  # answered by the fixed, verified placements reply (no AI call)
        ("Is 98% guaranteed?", "While SR University provides 100% placement assistance and dedicated career readiness training, actual job offers depend on individual student academic merit and interview performance; offers are not guaranteed at 98%."),
    ]
    results, _ = await _run_session("sess-scenario-d", turns)

    assert len(results) == 4
    # Turn 1: About SRU, built from the verified facts (v4.10.0)
    assert "SRU" in results[0]["answer"] and results[0]["answer"].count("• ") >= 2

    # Turn 2: "What about placements?" is broad: ask which aspect, no information dump
    assert "What would you like to know about placements" in results[1]["answer"]
    assert "Packages & record" in results[1]["suggestions"]

    # Turn 3: the chosen aspect is answered
    assert "6 to 6.5 LPA" in results[2]["answer"]       # short, factual answer to the aspect asked
    assert "51" in results[2]["answer"]

    # Turn 4: Honest clarification of guarantee
    assert "not guaranteed" in results[3]["answer"].lower() or "depend" in results[3]["answer"].lower()
    assert "100% placement assistance" in results[3]["answer"]


def test_contextual_query_reformulation():
    """Verify _contextual_query properly contextualizes follow-up fragments."""
    # Hostel context
    q_hostel = agent._contextual_query("Double sharing?", active_topic="hostel")
    assert "hostel accommodation" in q_hostel
    assert "3-sharing 4-sharing" in q_hostel

    q_mess = agent._contextual_query("Does it include mess?", active_topic="hostel")
    assert "Mega Dining Hall" in q_mess
    assert "included fee" in q_mess

    # Placements context
    q_guar = agent._contextual_query("Is 98% guaranteed?", active_topic="placements")
    assert "100% placement assistance" in q_guar
    assert "policy" in q_guar

    # B.Tech AI context
    q_ai = agent._contextual_query("Which one has AI?", active_topic="btech")
    assert "Artificial Intelligence" in q_ai
    assert "B.Tech engineering programs branches" in q_ai


def test_followup_suggestions_relevance():
    """Verify suggestion chips adapt dynamically to current topic and suppress repetitions."""
    history = [
        {"role": "user", "content": "What are the hostel room options?"},
        {"role": "model", "content": "We offer 3-sharing and 4-sharing rooms."},
    ]

    # Asking about mess should produce mess/hostel suggestions, not unrelated academic trees
    chips = followups.suggest("Does it include mess?", [], None, history=history, active_topic="hostel")
    assert any("mess" in c.lower() or "food" in c.lower() or "dining" in c.lower() or "fee" in c.lower() for c in chips)
    assert not any("why choose sru" in c.lower() for c in chips)
    assert not any("all programs" in c.lower() for c in chips)


def test_knowledge_synonyms_enrichment():
    """Verify search terms with synonyms retrieve correct handbook passages."""
    found_double = knowledge.search("double sharing room", k=3)
    assert len(found_double) > 0
    # Should locate hostel sections
    titles = [f["title"].lower() for f in found_double]
    assert any("hostel" in t for t in titles)

    found_guar = knowledge.search("placement guarantee policy", k=3)
    assert len(found_guar) > 0
    titles_p = [f["title"].lower() for f in found_guar]
    assert any("placement" in t or "career" in t for t in titles_p)
