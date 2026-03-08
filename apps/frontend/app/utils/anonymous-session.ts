/**
 * Anonymous session ID — scopes guest user rows to a single browser session.
 *
 * Generates a random UUID stored in localStorage so each browser tab/session
 * only sees its own anonymous search results, not all guest rows globally.
 */

const STORAGE_KEY = 'ba_anonymous_session_id';

export function getAnonymousSessionId(): string {
  if (typeof window === 'undefined' || !window.localStorage) return '';

  let sessionId: string | null = null;
  try {
    sessionId = localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    console.warn('[AnonymousSession] Failed to read from localStorage:', e);
  }

  if (!sessionId) {
    sessionId = crypto.randomUUID();
    try {
      localStorage.setItem(STORAGE_KEY, sessionId);
    } catch (e) {
      console.warn('[AnonymousSession] Failed to write to localStorage:', e);
    }
  }
  return sessionId;
}

export function clearAnonymousSessionId(): void {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.warn('[AnonymousSession] Failed to remove from localStorage:', e);
    }
  }
}
