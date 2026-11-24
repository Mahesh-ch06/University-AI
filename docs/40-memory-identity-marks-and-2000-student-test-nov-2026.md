# 40. Memory, identity, marks, admin UI and the 2,000-student test (v4.15.0, 24 Nov 2026)

## 1. Returning students (memory)

| Before | Now |
| --- | --- |
| The "continue or start fresh?" panel appeared as soon as the chat opened, before the student typed anything; an idle popup also appeared | Nothing is shown on opening. After the student's **first message** a chat reply asks: "Hey Mahesh! Welcome back. Would you like to continue our previous conversation or start a fresh chat?" with **Continue previous chat** / **Start fresh**, and a preview of the old chat |
| Under 30 minutes the old chat was silently restored | Restored silently only when it is the same browser tab's own conversation (a refresh); otherwise the student chooses |
| The conversation's workflow state (fee steps, marks, selections) lived only in Redis for 24 hours | Also saved in the database (`user_memories`, rows `cstate.<conversation id>`, chunked; no schema change). A student returning days later continues at the exact step |
| Background state saves could finish out of order (an older state overwrote a newer one) | One writer per conversation, always writing the latest state (`memory._flush_state`) |
| "hi" in the middle of the fee steps gave "What would you like to know next?" and lost the step | A short hello and the same step again, with its card |
| Start fresh hid the student's name | The name stays (only "Not Mahesh?" forgets it) |

No previous conversation: nothing is offered and the chat starts fresh. A conversation is never invented.

## 2. Identity and callbacks

* "Unknown", "Undefined", "Null", "Student", "User" are never used as a name (`tools.is_placeholder_name`); the
  profile name is used, and when there is none the student is asked for it. The request they made ("call me back")
  is then carried out with the name they give (`gate_pending`).
* Confirmation: "Your callback request has been successfully submitted, Mahesh. Our admissions counsellor will
  contact you on the number ending 1234." The 30-second "talk to a counsellor" flow is unchanged.
* No duplicates: in the chat (same request again) and in the database: a callback / visit request from the same
  mobile number that is still **new** and less than 7 days old updates that lead (`repeat_requests` counted) instead
  of creating a second one (`lead_service.create_lead`).
* Telugu / Hindi requests are understood: "counsellor tho matladali", "mujhe counsellor se baat karni hai".

## 3. Marks

* A marks card everywhere the marks are asked: "Marks obtained" + "Maximum marks" (fixed for boards with a known
  total), or a percentage, with validation and a Continue button.
* The latest marks win, everywhere: profile, fee steps, every calculation (`agent._sync_marks`). A correction at
  any point ("No, these are not my marks. My actual marks are 671 out of 1000", "galti ho gayi, mere marks 74%")
  says "Updated: I'm now using your marks **671/1000 (67.1%)**", states the new scholarship and asks the open step
  again. The "No" in it is not read as an answer to that step. An earlier fee card is marked "Outdated estimate".
* Impossible marks are never used or saved: "1200 out of 1000", "-5", "abc", "150%", "20" at a 1000 step, marks
  above the total, a raw number at a percentage-only step. The same question again, with what was wrong.
* "92%" at a marks-out-of-1000 step is 92%, and "87" there is 87% (it used to be 87 marks = 8.7%). One number in a
  sentence counts ("naaku 985 vachayi"). "Completed Intermediate / Class 12" is completed, not 2nd year.
* "I did BCom" in the MBA flow is the qualifying degree, not a change of programme to B.Com.

## 4. Conversation

* Programme change in the middle ("actually I want ECE"): the evaluation continues for the new programme.
* "Tell me about B.Tech CSE / AI & ML / MBA": a short overview from the official fee card (specialisations,
  duration, eligibility, tuition, specialisation fee, scholarship range), then what to explore next.
* "Can I join SRU?": "Yes, you can!" and the choice of eligibility or how to apply. "How to get admission?" gives
  the process. "How much do I pay for X?" starts the evaluation. "Any concession for girls / sports quota?" lists
  every matching official category. "My brother studies at SRU, any discount?" names the sibling concession.
  "How many seats?" says the figure isn't published and who confirms it.
* Short answers and typos: "telangana", "ap pls", "andhra pradesh borad", "inter aipoyindi", "pass ho gaya",
  "maths physics chemistry", "hostal", "fess", "placment", "admision".
* A long answer already given word for word in the last replies is not repeated in full: the key points and a
  pointer to the full answer above.
* With the AI model on, the hello in the middle of the steps and the concession list are worded by the model; the
  step questions, amounts and percentages stay exact.

## 5. Admin

* Sign-in page: brand panel and form, "Admin access key" with show / hide, the key checked with the server before
  the dashboard opens, clear errors (wrong key / server unreachable), loading state, responsive. Authentication is
  unchanged (same key, same header, kept in the browser tab only).
* Dashboard: a sidebar with icons and counts on laptops, a top bar with the page title, "Open student chat" and
  Sign out, tabs on tablets and phones; tables scroll inside their card.

## 6. The 2,000-student test (e2e/student_simulation_2000.py)

2,000 students, 20 personas, 7 writing styles, 1,600 typing only and 400 also tapping buttons; 11 journeys with
checked outcomes (see `e2e/README.md`). Review server with the stand-in model (no Gemini key in this environment):
replies the AI model would write are counted separately and **not judged** (4.9% of replies in the final round).

| Metric | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 (final) |
| --- | --- | --- | --- | --- | --- |
| Students with every check passed | 80.6% | 85.6% | 89.3% | 92.2% | **92.7%** |
| Checked replies with no problem | 96.7% | 97.3% | 98.0% | 98.5% | **98.6%** |
| Intent accuracy | 99.7% | 99.8% | 99.9% | 100.0% | 100.0% (13,469 / 13,470) |
| Relevance | 88.8%* | 99.3% | 99.3% | 99.9% | 100.0% (2,481 / 2,482) |
| Factual correctness (amounts) | 99.9% | 100% | 100% | 100% | 100% |
| Continuity | 95.8% | 98.3% | 100% | 100% | 100% (360) |
| Memory restoration | 100% | 100% | 100% | 100% | 100% (270) |
| Marks consistency | 98.2% | 99.6% | 99.9% | 100% | 100% (1,548) |
| Eligibility / scholarship slab | 100% | 100% | 100% | 100% | 100% (1,129) |
| Callback identity | 96.0% | 100% | 100% | 100% | 100% (782) |
| Fee workflow completion | 94.0% | 99.4% | 99.9% | 100% | 100% (1,129) |
| Quick replies | 97.0% | 99.7% | 99.8% | 100% | 100% (1,390) |
| UI failures (errors, empty replies) | 0 | 0 | 0 | 0 | 0 |
| No repeated answer | – | 97.5% | 98.2% | 98.6% | 98.6% |

\* Round 1 counted repeats inside relevance; from round 2 they are a metric of their own. Rounds 1-4 found and fixed
the problems in sections 1-4. What is left: repeated answers (185 replies, mostly the same message sent twice by
the simulated student) and 1 reply off topic. Reply time: median 122 ms, 90th percentile 219 ms (code answers).

Not covered here, and to be run with the real Gemini model (key added to the environment): the 4.9% of replies the
model writes, hallucination and SRU-only checks on them, and the model's use of the conversation history.
