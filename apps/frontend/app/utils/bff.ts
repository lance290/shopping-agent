/**
 * Shared BFF (Backend-for-Frontend) utility functions.
 * Used by Next.js API routes that proxy to the BFF service.
 */

export function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

export const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8081'
);
