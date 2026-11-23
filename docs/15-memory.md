# Conversation Memory

## Short-term memory
Store enough recent conversation history to resolve references and maintain continuity.

## Long-term memory
Only store explicitly permitted, useful, non-sensitive preferences or profile data.
Define retention and deletion behavior before production.

## Memory safety
- Never use memory as authorization.
- Never infer sensitive personal attributes.
- User-specific university data must come from authorized systems.
- Allow users to clear conversation history according to the product's privacy design.

## Context strategy
Use a bounded recent-message window plus optional summaries rather than sending an
unbounded conversation to the LLM.

## Smart Conversation Recovery (v4.0.0)
- Preserves conversation journey and counsellor intake state between sessions and reloads.
- Differentiates active ongoing conversations from genuine returns via strict trigger rules (page reload, fresh session, or 30+ minutes of inactivity).
- Provides personalized greetings contextually mapped to scholarship outcomes (40%, 30%, 25%, unmatched, incomplete, or general inquiry).
- Offers two explicit actions: Continue (restores exact message history and state without asking duplicate questions) or Start Fresh (resets active conversation state while isolating history and preserving verified lead identity).

### v4.8.0: when the choice appears, and what each choice does (docs/32)
- **One threshold, on the server:** `RECOVERY_RESUME_AFTER_MINUTES` (30, the value the app already used).
  `/recovery-context` measures the time since the last *message* of the most recently active conversation and
  returns `offer_choice`.
- **When the student returns:**
  - **Before the threshold** (a refresh, a short break, reopening within 30 minutes): the conversation simply
    continues. No question is asked.
  - **After the threshold:** the welcome-back panel asks whether to continue or start a new chat. Nothing is
    restored or started until the student chooses. A question typed meanwhile is answered after the choice.
  - **A tab left open:** the same choice is offered once at the end of the conversation.
- **Continue:** the saved messages are shown, and the agent reloads that conversation's history (from PostgreSQL
  when the cache has expired). It also reloads that conversation's academic details, including after a day.
- **Start a new chat** keeps the old conversation and its state intact. Its academic details are filed with it
  (offered for one-tap reuse, never applied automatically). The programme is not carried over. The student's
  name and mobile number are kept; "Not <name>?" forgets them on a shared computer.
- **Cards already shown** are remembered per conversation, so a new chat can show them again.

