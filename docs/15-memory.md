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

