import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BACKEND_URL = normalizeBaseUrl(
  process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

function getDevSessionToken(): string | undefined {
  return process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
}

async function mintDevSessionToken(): Promise<string | undefined> {
  try {
    const devEmail =
      process.env.NEXT_PUBLIC_DEV_SESSION_EMAIL ||
      process.env.DEV_SESSION_EMAIL ||
      'test@example.com';
    const res = await fetch(`${BACKEND_URL}/test/mint-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: devEmail }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      console.error('[likes/counts] mint-session failed', res.status, text);
      return undefined;
    }
    let data: any;
    try {
      data = await res.json();
    } catch (err) {
      const text = await res.text().catch(() => '');
      console.error('[likes/counts] mint-session parse failed', err, text);
      return undefined;
    }
    const token = data?.session_token;
    if (!token) {
      console.error('[likes/counts] mint-session missing token', data);
    }
    return token || undefined;
  } catch {
    return undefined;
  }
}

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  // When Clerk is enabled, use Clerk token
  if (!disableClerk) {
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
  const devToken =
    request.cookies.get('sa_session')?.value ||
    getDevSessionToken();
  return devToken ? { Authorization: `Bearer ${devToken}` } : {};
}

async function ensureAuthHeader(
  request: NextRequest
): Promise<{ Authorization?: string }> {
  const existing = await getAuthHeader(request);
  if (existing.Authorization) return existing;

  if (disableClerk) {
    const mintedToken = await mintDevSessionToken();
    if (mintedToken) {
      return { Authorization: `Bearer ${mintedToken}` };
    }
  }
  return {};
}

export async function GET(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const rowId = request.nextUrl.searchParams.get('row_id');

    if (!rowId) {
      return NextResponse.json({ error: 'row_id is required' }, { status: 400 });
    }

    const response = await fetch(`${BACKEND_URL}/likes/counts?row_id=${rowId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
    });

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      console.error('Error parsing response:', parseError);
      return NextResponse.json(
        { error: 'Invalid response from server' },
        { status: response.status || 500 }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching like counts:', error);
    return NextResponse.json({}, { status: 500 });
  }
}
