# 36. Understanding the student, not matching keywords (standing priority)

> Agreed with the project owner (23 Nov 2026): **this is the main motive of SRU Buddy as an agent.** The agent must
> understand what the student means *in the context of the conversation*, and answer that. It must not react
> blindly to a keyword. Work on it continues feature by feature. Do not drop it.

## The rules (every change must keep them)

1. **Context first.** Before routing a message, ask: is this about something the student already has in this chat
   (a fee evaluation, a selected concession, a programme, a pending request)? If yes, answer from that state.
   - Example: "Documents needed for the concession" after selecting *Students of SR Junior College* gets: "You've
     selected Students of SR Junior College (₹15,000 a year)… once approved: ₹2,80,000 → ₹2,65,000".
   - It must never get the scholarship steps ("I already have your details…").
2. **Answer what was asked, then continue.** A question in the middle of a flow is answered, and then the open step
   is asked again ("Now, back to your fee:"). Progress is never lost.
3. **Do what the button says.**
   - **Same request, same step:** "Add hostel to my fee" goes to the hostel question, even when other steps are
     still open.
   - **Contract:** every button the agent offers must lead to an answer about that button. It is checked by
     `test_every_button_the_fee_agent_offers_gets_a_relevant_answer`.
4. **Use the student's own choices.**
   - **Programme name:** shown as chosen ("B.Tech CSE", or "B.Tech CSE (Artificial Intelligence & Machine
     Learning)" when a specialisation was named). Never the fee card's whole group of specialisations.
   - **Category:** the concession category the student selected, and their own fee effect.
5. **Statements are not questions.** "Yes, I have the proof" records the proof. It is not a question about
   documents.
6. **Never invent to fill a gap.**
   - **Documents:** where the official data has no detail (for example, the exact document for each concession
     category), say what has to be proved and that the Admissions Office confirms the exact document.

## Done so far

| Version | What |
|---|---|
| 4.11.0 | Fee evaluation agent: remembers selections, answers side questions, offers to continue |
| 4.12.0 | Lowest-fee agent with a visible plan; "talk to a counsellor"; self-check of AI-written numbers |
| 4.12.1 | Questions about the student's own evaluation (documents, "is it approved?", "my scholarship"), answered from their selections; the programme shown as chosen; "Add hostel" goes to the hostel step; the button-contract test |
| 4.13.0 | Multi-question messages (Nikhil's decomposition) split only when safe: never a message with an action or the student's own data, a button label, a single question or another programme's fees; a pending question's answer is still read as the answer (`sru_agent/compound.py`, docs/37) |
| 4.13.0 | Replies written by the model from verified facts with the conversation state (docs/38); a family-link discount question gets the named concession; cut-off questions answered as unpublished; "what is the eligibility?" gives the programme's rule; marks read with the board's total; typos recognised; the student simulation (`e2e/student_simulation.py`) for replaying many students |

## Next (in order)

1. **Button contract for every chip, not only the fee agent's.**
   - **Scope:** the topic chips in `followups._chips` (placements, hostel, programmes, faculty, visit, apply…).
   - **Test:** click each chip in a realistic state and check the reply answers it.
   - **Fix the routing:** any chip that lands in an unrelated flow.
2. **Keyword routers that capture the wrong messages.** Audit every regex router for messages meant for something
   else:
   - the scholarship-calculation pattern in `agent.py` (`is_scholarship_calc_q`, which matches "concession");
   - `dialogue._pick`;
   - the intent classifier.
   For each: a test with the misrouted message, then a context check before the keyword.
3. **State-aware answers in the other journeys** (admission steps, campus visit, callbacks): "what's the status of
   my request?", "what did I select?", "change my programme" answered from the conversation's state.
4. **Replay real chats.** Take anonymised conversations from the admin panel where the student repeated or
   rephrased a question (a sign the first answer missed), and turn each into a test.

Each item ships with tests and a browser check, like the fee agent.
