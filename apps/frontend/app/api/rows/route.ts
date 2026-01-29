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

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8080'
);

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

const BACKEND_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

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
  if (disableClerk || !isClerkConfigured()) {
    const token = getCookieSessionToken(request) || getDevSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  try {
    const { getToken } = await auth();
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    const token = getDevSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
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
    if (!res.ok) return undefined;
    const data = await res.json();
    const token = data?.session_token;
    return token || undefined;
  } catch {
    return undefined;
  }
}

async function ensureAuthHeader(
  request: NextRequest
): Promise<{ Authorization?: string; mintedToken?: string }> {
  const authHeader = await getAuthHeader(request);
  if (authHeader.Authorization) {
    return { Authorization: authHeader.Authorization };
  }

  if (!disableClerk || isClerkConfigured()) {
    return {};
  }

  const mintedToken = await mintDevSessionToken();
  if (!mintedToken) {
    return {};
  }

  return { Authorization: `Bearer ${mintedToken}`, mintedToken };
}

export async function GET(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const hadToken = Boolean(getCookieSessionToken(request) || getDevSessionToken());

    let response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
    });

    if (response.status === 401 && !hadToken) {
      const mintedToken = await mintDevSessionToken();
      if (mintedToken) {
        response = await fetch(`${BFF_URL}/api/rows`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${mintedToken}`,
          },
        });
        const data = await response.json();
        const out = NextResponse.json(data, { status: response.status });
        out.cookies.set('sa_session', mintedToken, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          path: '/',
        });
        return out;
      }
    }
    
    const data = await response.json();
    const out = NextResponse.json(data, { status: response.status });
    if (authHeader.mintedToken) {
      out.cookies.set('sa_session', authHeader.mintedToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      });
    }
    return out;
  } catch (error) {
    console.error('Error fetching rows:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const hadToken = Boolean(getCookieSessionToken(request) || getDevSessionToken());

    const body = await request.json();
    
    let response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
      body: JSON.stringify(body),
    });

    if (response.status === 401 && !hadToken) {
      const mintedToken = await mintDevSessionToken();
      if (mintedToken) {
        response = await fetch(`${BFF_URL}/api/rows`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${mintedToken}`,
          },
          body: JSON.stringify(body),
        });

        if (response.ok) {
          const data = await response.json();
          const out = NextResponse.json(data, { status: response.status });
          out.cookies.set('sa_session', mintedToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
          });
          return out;
        }
      }
    }
    
    const data = await response.json();
    const out = NextResponse.json(data, { status: response.status });
    if (authHeader.mintedToken) {
      out.cookies.set('sa_session', authHeader.mintedToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      });
    }
    return out;
  } catch (error) {
    console.error('Error creating row:', error);
    return NextResponse.json({ error: 'Failed to create row' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const hadToken = Boolean(getCookieSessionToken(request) || getDevSessionToken());

    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    let response = await fetch(`${BFF_URL}/api/rows/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: authHeader.Authorization,
      }
    });

    if (response.status === 401 && !hadToken) {
      const mintedToken = await mintDevSessionToken();
      if (mintedToken) {
        response = await fetch(`${BFF_URL}/api/rows/${id}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${mintedToken}`,
          },
        });
        const data = await response.json();
        const out = NextResponse.json(data, { status: response.status });
        out.cookies.set('sa_session', mintedToken, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          path: '/',
        });
        return out;
      }
    }
    
    const data = await response.json();
    const out = NextResponse.json(data, { status: response.status });
    if (authHeader.mintedToken) {
      out.cookies.set('sa_session', authHeader.mintedToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      });
    }
    return out;
  } catch (error) {
    console.error('Error deleting row:', error);
    return NextResponse.json({ error: 'Failed to delete row' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const authHeader = await ensureAuthHeader(request);
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const hadToken = Boolean(getCookieSessionToken(request) || getDevSessionToken());

    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    const body = await request.json();
    
    console.log(`[API] PATCH /api/rows?id=${id}`, body);

    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    const bffUrl = `${BFF_URL}/api/rows/${id}`;
    console.log(`[API] Forwarding to BFF: ${bffUrl}`);

    let response = await fetch(bffUrl, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader.Authorization,
      },
      body: JSON.stringify(body),
    });

    if (response.status === 401 && !hadToken) {
      const mintedToken = await mintDevSessionToken();
      if (mintedToken) {
        response = await fetch(bffUrl, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${mintedToken}`,
          },
          body: JSON.stringify(body),
        });
        const data = await response.json();
        const out = NextResponse.json(data, { status: response.status });
        out.cookies.set('sa_session', mintedToken, {
          httpOnly: true,
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'lax',
          path: '/',
        });
        return out;
      }
    }
    
    if (!response.ok) {
      console.error(`[API] BFF returned ${response.status} ${response.statusText}`);
      const text = await response.text();
      console.error(`[API] BFF response body: ${text}`);
      return NextResponse.json({ error: 'BFF failed' }, { status: response.status });
    }

    const data = await response.json();
    console.log(`[API] BFF success:`, data);
    const out = NextResponse.json(data, { status: response.status });
    if (authHeader.mintedToken) {
      out.cookies.set('sa_session', authHeader.mintedToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      });
    }
    return out;
  } catch (error) {
    console.error('Error updating row:', error);
    return NextResponse.json({ error: 'Failed to update row' }, { status: 500 });
  }
}
