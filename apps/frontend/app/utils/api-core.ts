/**
 * Shared API utilities — auth, fetch wrapper, constants.
 * All domain-specific API modules import from here.
 */

import { getAnonymousSessionId } from './anonymous-session';

export const AUTH_REQUIRED = 'auth_required' as const;

export function getAuthToken(): string {
  // Prefer cookie-based auth via same-origin requests, but keep legacy token
  // fallback for environments where only localStorage is populated.
  if (typeof window === 'undefined') return '';
  const storage = globalThis.localStorage;
  if (!storage || typeof storage.getItem !== 'function') return '';
  return storage.getItem('session_token') || '';
}

export async function fetchWithAuth(url: string, init: RequestInit = {}): Promise<Response> {
  const baseHeaders = init.headers ? { ...(init.headers as Record<string, string>) } : {};
  const token = getAuthToken();
  const headers: Record<string, string> = token ? { ...baseHeaders, Authorization: `Bearer ${token}` } : { ...baseHeaders };

  // Include anonymous session ID for scoping guest rows to browser session
  const anonId = getAnonymousSessionId();
  if (anonId) headers['X-Anonymous-Session-Id'] = anonId;

  const res = await fetch(url, { ...init, headers, credentials: 'same-origin' });
  
  // NOTE: Do NOT redirect to /login on 401 here.
  // The workspace page must be accessible to anonymous visitors (affiliate requirement).
  // Individual components should handle 401 gracefully (show empty state, prompt sign-in, etc.).
  
  return res;
}

export const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';

export async function readResponseBodySafe(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
}
