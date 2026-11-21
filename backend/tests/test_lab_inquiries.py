import pytest
from app.sru_agent import intents, knowledge, agent


def test_lab_intent_classification():
    assert intents.classify_agent_intent("how many labs are there in the university") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("how many labs") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("how many laboratories are there") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("what labs are available") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("tell me about lab facilities") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("what are the research centers") == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("list of laboratories") == "LAB_FACILITIES_QUERY"


def test_lab_fee_not_hijacked_by_lab_intent():
    # A fee query mentioning lab should not be classified as general lab inquiry
    assert intents.classify_agent_intent("cse lab fee") != "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("what is the laboratory fee") != "LAB_FACILITIES_QUERY"


def test_campus_visit_state_does_not_hijack_lab_query():
    state = {"active_topic": "campus_visit"}
    assert intents.classify_agent_intent("how many labs are there in the university", state) == "LAB_FACILITIES_QUERY"
    assert intents.classify_agent_intent("what labs are available at sru", state) == "LAB_FACILITIES_QUERY"


def test_knowledge_search_for_labs():
    knowledge.reload()
    results = knowledge.search("how many labs are there in the university", k=5)
    assert len(results) > 0
    top_sources = [r["source"] for r in results]
    assert "13_laboratories_and_research_centers.md" in top_sources or "09_verified_sru_facts.md" in top_sources
    top_text = " ".join(r["text"] for r in results)
    assert "11" in top_text
    assert "Creative Cognition" in top_text or "AI & Deep Learning" in top_text


@pytest.mark.asyncio
async def test_run_agent_lab_query_response():
    events = []
    async for ev in agent.run_agent("how many labs are there in the university", "test_session_labs_1"):
        events.append(ev)
    
    # Collect streamed response
    tokens = [e["delta"] for e in events if e.get("type") == "token"]
    full_text = "".join(tokens)
    
    # Verify core grounded facts are present
    assert "11" in full_text
    assert "Center for AI & Deep Learning" in full_text
    assert "Creative Cognition" in full_text
    assert "SR Innovation Exchange" in full_text or "SRiX" in full_text
    assert "14+" in full_text or "maker spaces" in full_text.lower()
    
    # Verify no unsolicited tour / callback pivot
    assert "virtual campus tour" not in full_text.lower()
    assert "callback from our admissions team" not in full_text.lower()
    
    # Verify chips
    done_events = [e for e in events if e.get("type") == "done"]
    assert len(done_events) == 1
    suggestions = done_events[0].get("suggestions", [])
    assert "AI & Computer Science Labs" in suggestions or "Robotics & IoT Labs" in suggestions
