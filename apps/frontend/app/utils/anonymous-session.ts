/**
 * Anonymous session ID — scopes guest user rows to a single browser session.
 *
 * Generates a random UUID stored in localStorage so each browser tab/session
 * only sees its own anonymous search results, not all guest rows globally.
 */

const STORAGE_KEY = 'ba_anonymous_session_id';

export function getAnonymousSessionId(): string {
  if (typeof window === 'undefined') return '';

  let sessionId = localStorage.getItem(STORAGE_KEY);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, sessionId);
  }
  return sessionId;
}

export function clearAnonymousSessionId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(STORAGE_KEY);
  }
}
