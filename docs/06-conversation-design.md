# Conversation Design

## Personality
Friendly, respectful, student-oriented, concise, patient and transparent.

## Examples

User: Hi
Bot: Hey! 👋 How can I help you today?

User: How are you?
Bot: I'm doing well! I'm here to help with university questions or just have a conversation.

User: When is the exam?
Bot: Sure — which exam or subject are you asking about?

User: I'm stressed about exams.
Bot: That sounds stressful. If you want, we can break your preparation into a simple plan.

## Grounding behavior
For university facts:
- Prefer retrieved official sources.
- Mention the relevant source/date when useful.
- If evidence is insufficient, say so.
- Never make up deadlines, fees, regulations or schedules.

## Conversation continuity
Use recent messages to resolve references such as:
"that exam", "the second one", "what about next week?"

## Broad versus specific questions (v4.4.0, `backend/app/sru_agent/dialogue.py`)
Every message passes through the conversation manager before any other route (no AI call):
- **Broad topic** ("Tell me about the hostel", "placements", "transport", "faculty"...): ask which aspect, with
  up to 4 chips. The reply ("Hostel fees.") becomes the specific question ("What are the hostel fees?") and only
  that is answered.
- **Broad programme** ("Tell me about CSE", "B.Tech"): ask the branch if needed, then the aspect (eligibility,
  fees, curriculum, placements, faculty, labs, careers). The chosen aspect is asked about that programme only.
- **Admission intent / vague interest** ("I want to join", "I'm interested", "I want to join B.Tech CSE"):
  programme -> branch -> goal (eligibility / process / fees) -> marks -> 10+2 subjects -> verdict. One question at
  a time; what the student already said (in the chat or saved profile) is never asked again.
- **Short follow-ups** ("fees", "placements", "this branch") are about the programme being discussed. Right
  after a fee answer, "what about hostel?" means hostel fees.
- **Specific questions** ("What are the hostel fees?", "CSE fee with 85%") are answered directly.
- A message that does not answer the pending question drops it and is treated as a new question. "skip" ends it.
- The programme being discussed is stored as `active_program` and given to the AI as a CURRENT FOCUS line, so
  AI-written answers stay on that programme.
