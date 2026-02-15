/**
 * Shared proxy utilities for Next.js API routes.
 * Single source of truth for BACKEND_URL and auth header extraction.
 *
 * PRD-00: Unify the Proxy Layer
 */
import { NextRequest, NextResponse } from 'next/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, '');
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

/**
 * Canonical backend URL.  Fallback order is compatible with Railway
 * (`BACKEND_URL`), legacy env aliases, and local dev.
 */
export const BACKEND_URL: string = normalizeBaseUrl(
  process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.BFF_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8000',
);

export const COOKIE_NAME = 'sa_session';

/**
 * Extract a Bearer token from the request.
 * Checks the `sa_session` cookie first (SSR path), then the Authorization header.
 */
export function getAuthHeader(request: NextRequest): string | null {
  const cookieToken = request.cookies.get(COOKIE_NAME)?.value;
  if (cookieToken) return `Bearer ${cookieToken}`;

  const authHeader = request.headers.get('Authorization');
  if (authHeader?.startsWith('Bearer ')) return authHeader;

  return null;
}

// ---------------------------------------------------------------------------
// Generic proxy helpers
// ---------------------------------------------------------------------------

interface ProxyOptions {
  /** If true, skip the auth check and allow unauthenticated requests. */
  allowAnonymous?: boolean;
}

async function proxyRequest(
  request: NextRequest,
  method: string,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  const auth = getAuthHeader(request);
  if (!auth && !opts?.allowAnonymous) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (auth) headers['Authorization'] = auth;

  const url = `${BACKEND_URL}${backendPath}`;

  try {
    const fetchOpts: RequestInit = { method, headers };

    if (method !== 'GET' && method !== 'HEAD') {
      try {
        const body = await request.json();
        fetchOpts.body = JSON.stringify(body);
      } catch {
        // No body or unparseable — proceed without body
      }
    }

    const res = await fetch(url, fetchOpts);

    // Attempt JSON response; fall back to text
    const contentType = res.headers.get('Content-Type') || '';
    if (contentType.includes('application/json')) {
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    }

    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { 'Content-Type': contentType || 'text/plain' },
    });
  } catch (error) {
    console.error(`[api-proxy] ${method} ${backendPath} failed:`, error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export function proxyGet(
  request: NextRequest,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  return proxyRequest(request, 'GET', backendPath, opts);
}

export function proxyPost(
  request: NextRequest,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  return proxyRequest(request, 'POST', backendPath, opts);
}

export function proxyPatch(
  request: NextRequest,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  return proxyRequest(request, 'PATCH', backendPath, opts);
}

export function proxyPut(
  request: NextRequest,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  return proxyRequest(request, 'PUT', backendPath, opts);
}

export function proxyDelete(
  request: NextRequest,
  backendPath: string,
  opts?: ProxyOptions,
): Promise<NextResponse> {
  return proxyRequest(request, 'DELETE', backendPath, opts);
}
