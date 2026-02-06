import { NextRequest, NextResponse } from 'next/server';

const ALLOWED_PROXY_PATHS = new Set([
  'auth/start',
  'auth/verify',
  'auth/me',
  'auth/logout',
]);

function isAllowedPath(path: string): boolean {
  if (ALLOWED_PROXY_PATHS.has(path)) return true;
  if (path.includes('..') || path.includes('//')) return false;
  return false;
}

function getBackendUrl(): string {
  return process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const path = (await params).path.join('/');

  if (!isAllowedPath(path)) {
    return NextResponse.json({ error: 'Not Found' }, { status: 404 });
  }

  const url = `${getBackendUrl()}/${path}`;

  try {
    const body = await request.json();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Forward Authorization header if present
    const authHeader = request.headers.get('Authorization');
    const cookieToken = request.cookies.get('sa_session')?.value;
    if (authHeader) {
      headers['Authorization'] = authHeader;
    } else if (cookieToken) {
      headers['Authorization'] = `Bearer ${cookieToken}`;
    }

    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await res.json();
    
    // If it's the verify endpoint and success, set the cookie
    if (path === 'auth/verify' && res.ok && data.session_token) {
        const response = NextResponse.json(data, { status: res.status });
        response.cookies.set('sa_session', data.session_token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            path: '/',
            maxAge: 60 * 60 * 24 * 30, // 30 days
            sameSite: 'lax',
        });
        return response;
    }
    
    // If logout, clear cookie
    if (path === 'auth/logout' && res.ok) {
        const response = NextResponse.json(data, { status: res.status });
        response.cookies.delete('sa_session');
        return response;
    }

    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error(`Proxy error for ${path}:`, error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const path = (await params).path.join('/');

  if (!isAllowedPath(path)) {
    return NextResponse.json({ error: 'Not Found' }, { status: 404 });
  }

  const url = `${getBackendUrl()}/${path}`;

  try {
    const headers: Record<string, string> = {};
    
    // Forward Authorization header or cookie
    const authHeader = request.headers.get('Authorization');
    const cookieToken = request.cookies.get('sa_session')?.value;
    
    if (authHeader) {
      headers['Authorization'] = authHeader;
    } else if (cookieToken) {
        headers['Authorization'] = `Bearer ${cookieToken}`;
    }

    const res = await fetch(url, {
      method: 'GET',
      headers,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error(`Proxy error for ${path}:`, error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}
