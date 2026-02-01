import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export const dynamic = 'force-dynamic'; // Disable caching

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BACKEND_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

function getDevSessionToken(): string | undefined {
  return process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
}

function getCookieSessionToken(request: NextRequest): string | undefined {
  const direct = request.cookies.get('sa_session')?.value;
  if (direct) return direct;
  const raw = request.headers.get('cookie') || '';
  const parts = raw.split(';').map((p) => p.trim());
  const match = parts.find((p) => p.startsWith('sa_session='));
  if (!match) return undefined;
  const value = match.slice('sa_session='.length);
  return value ? decodeURIComponent(value) : undefined;
}

function isClerkConfigured(): boolean {
  return Boolean(process.env.CLERK_SECRET_KEY);
}

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  // When Clerk is enabled, use Clerk token first
  if (!disableClerk && isClerkConfigured()) {
    try {
      const { getToken } = await auth();
      const token = await getToken();
      if (token) {
        return { Authorization: `Bearer ${token}` };
      }
    } catch {
      // Fall through to dev token
    }
  }

  // Fallback: dev session token
  const devToken = getCookieSessionToken(request) || getDevSessionToken();
  return devToken ? { Authorization: `Bearer ${devToken}` } : {};
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    const url = new URL(request.url);
    const includeProvenance = url.searchParams.get('include_provenance');

    const backendUrl = includeProvenance
      ? `${BACKEND_URL}/bids/${id}?include_provenance=true`
      : `${BACKEND_URL}/bids/${id}`;

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching bid:', error);
    return NextResponse.json({ error: 'Failed to fetch bid' }, { status: 500 });
  }
}
