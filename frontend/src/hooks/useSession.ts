/**
 * Session hook — generates and persists an anonymous session ID in localStorage.
 * No login required.
 *
 * "Start afresh" rotates the ID (startFreshSession): the new session has no messages, profile, marks,
 * programme, pending steps or cached answers on the server, because all of those are stored per session.
 * The previous session's data is not deleted; it is simply no longer used by this browser.
 */

const SESSION_KEY = "university_ai_session_id";
// Sessions started with "Start afresh": the contact details saved in this browser (used only for the
// contact gate) are NOT copied into them, so the assistant does not greet or address the student by name.
const FRESH_KEY = "sru_fresh_sessions";

function generateUUID(): string {
  return crypto.randomUUID();
}

export function getSessionId(): string {
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = generateUUID();
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

function readFresh(): string[] {
  try {
    const list = JSON.parse(localStorage.getItem(FRESH_KEY) || "[]");
    return Array.isArray(list) ? list.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

/** True for a session started with "Start afresh" (its identity is not filled in from this browser). */
export function isFreshSession(sessionId: string): boolean {
  return readFresh().includes(sessionId);
}

/** Start a completely new session and return its ID. */
export function startFreshSession(): string {
  const sessionId = generateUUID();
  try {
    localStorage.setItem(SESSION_KEY, sessionId);
    localStorage.setItem(FRESH_KEY, JSON.stringify([...readFresh().slice(-9), sessionId]));
  } catch {
    /* private mode: the ID still lives in React state for this page */
  }
  return sessionId;
}
