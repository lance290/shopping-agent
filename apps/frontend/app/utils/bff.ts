/**
 * Shared backend utility functions.
 * Used by Next.js API routes that proxy to the backend service.
 * (Formerly proxied to a BFF layer — removed in PRD-02.)
 */

export function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

export const BACKEND_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

/** @deprecated Use BACKEND_URL instead. Alias kept for backward compatibility during migration. */
export const BFF_URL = BACKEND_URL;
