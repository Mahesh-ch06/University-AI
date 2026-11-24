"""v4.13.0: every way students ask for a person reaches the 30-second connect ("customer care", "human please"...)."""
import pytest

from app.sru_agent import intents


@pytest.mark.parametrize("message", [
    "I want to connect to the customer care", "connect me to a human", "customer care number", "customer care",
    "connect to customer support", "transfer me to an agent", "human please", "I need help from a person",
    "I want to talk to a human", "connect with the helpdesk", "I need a human", "talk to a counsellor",
    "can I speak to a real person", "connect me to admissions team",
])
def test_asking_for_a_person_connects(message):
    assert intents.is_connect_request(message)


@pytest.mark.parametrize("message", [
    "what is the customer care of the hostel like", "don't connect me", "no need to talk to a counsellor",
    "how good are the counsellors at SRU", "human resources course", "is there customer care for hostel complaints",
])
def test_questions_about_people_are_not_a_connect_request(message):
    assert not intents.is_connect_request(message)
