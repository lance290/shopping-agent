import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8081'
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
    const res = await fetch(`${BFF_URL}/api/test/mint-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: devEmail }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      console.error('[comments] mint-session failed', res.status, text);
      return undefined;
    }
    let data: any;
    try {
      data = await res.json();
    } catch (err) {
      const text = await res.text().catch(() => '');
      console.error('[comments] mint-session parse failed', err, text);
      return undefined;
    }
    const token = data?.session_token;
    if (!token) {
      console.error('[comments] mint-session missing token', data);
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
      return NextResponse.json({ error: 'Missing row_id' }, { status: 400 });
    }

    const response = await fetch(`${BFF_URL}/api/comments?row_id=${rowId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching comments:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/api/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating comment:', error);
    return NextResponse.json({ error: 'Failed to create comment' }, { status: 500 });
  }
}
