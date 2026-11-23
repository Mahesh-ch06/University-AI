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

## One admission journey (v4.6.0)
- **Fees**: a fee question with no programme asks which programme (and branch for B.Tech) before any figure; only
  that programme's fees are shown, for the year on the fee card. Inside a hostel / transport conversation, "what is
  the fee?" means that fee. Later years: "not published yet", plus the named programme's 2027-28 figure.
- **Unfinished messages** ("I want to...", "Can you explain", "What about the"): ask what the student means, using
  the topic being discussed; the pending question is kept. Short complete questions ("Hostel fees?") are answered.
- **Academic details** (board, status, marks, 10+2 group, optional entrance score) belong to the conversation
  (`sru_agent/journey.py`). Eligibility, scholarship and fee answers all reuse them; only missing fields are asked:
  two or more missing -> one `academic_details_form` card (pre-filled); one missing -> only that field; typed
  answers after the form continue field by field.
- A **new conversation** starts with a clean form; details from the previous chat are offered as
  "Use my saved details (...)" and used only if the student taps it.
- A **programme change** midway keeps the marks and redoes the check for the new programme.
- **Name**: used where it reads naturally (journey start, results received, scholarship start), never in two
  consecutive replies, never invented.
- **Neutral guidance**: the agent describes options and asks about interests; it never calls a course "the best for
  you". Admission eligibility and scholarships are evaluated and shown separately.
