"""Shared test setup."""
import pytest


@pytest.fixture(autouse=True)
def _chat_settings_are_the_defaults():
    """The admin panel's chat settings live in the database; tests use the defaults unless they set others."""
    from app.services import app_settings

    # Defaults, and no database reload during the test. "Answers written by the AI" is off here so the older
    # tests keep checking the verified texts themselves (they are the facts and the fallback since v4.13.0);
    # tests of the model-written replies turn it on (tests/test_v413_dynamic_replies.py).
    # Likewise "suggestion_chips" is 'always' here (the older tests check the chips themselves); the default
    # 'questions_only' is covered by tests/test_v413_chips_and_tiles.py.
    # and "fee_questions" is 'fee_card' (the standard fee at once, as those tests expect); the default
    # 'evaluate_first' is covered by tests/test_v413_fee_questions.py.
    app_settings.set_for_tests(ai_answers=False, suggestion_chips="always", fee_questions="fee_card")
    yield
    app_settings.reset_for_tests()
    app_settings.set_for_tests(ai_answers=False, suggestion_chips="always", fee_questions="fee_card")


@pytest.fixture(autouse=True)
def _agent_memory_stays_in_the_test():
    """The live app keeps student profiles and chat context in PostgreSQL (app/main.py wires the
    hooks). Unit tests use fixed session names, so with a real database one run would find the
    profiles left by the previous run. Tests therefore run with the agent's memory in-process
    only; tests that check the lasting storage set the hooks themselves."""
    from app.sru_agent import memory

    before = (memory._profile_loader, memory._profile_saver, memory._history_loader)
    state_before = (memory._state_loader, memory._state_saver)
    memory.set_profile_store(None, None)
    memory.set_history_loader(None)
    memory.set_state_store(None, None)          # the conversation-state store too (v4.15.0)
    memory._state_saved.clear()
    memory._local.clear()
    memory._hot.clear()
    memory._pending_writes.clear()
    r = memory._client()
    if r:
        try:
            import asyncio
            asyncio.run(r.flushdb())
        except Exception:
            pass
    yield
    memory._local.clear()
    memory._hot.clear()
    memory._pending_writes.clear()
    r = memory._client()
    if r:
        try:
            import asyncio
            asyncio.run(r.flushdb())
        except Exception:
            pass
    memory._profile_loader, memory._profile_saver, memory._history_loader = before
    memory.set_state_store(*state_before)
