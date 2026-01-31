import { NextRequest } from 'next/server';
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

export async function POST(request: NextRequest) {
  let token: string | null = null;

  // When Clerk is enabled, use Clerk token first
  if (!disableClerk) {
    try {
      const { getToken } = await auth();
      token = await getToken();
    } catch {
      // Fall through to dev token
    }
  }

  // Fallback: dev session token
  if (!token) {
    token =
      request.cookies.get('sa_session')?.value ||
      process.env.DEV_SESSION_TOKEN ||
      process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN ||
      null;
  }
  
  if (!token) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const body = await request.json();
  
  const response = await fetch(`${BFF_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  // Stream the response back
  return new Response(response.body, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'text/event-stream; charset=utf-8',
      'Cache-Control': response.headers.get('Cache-Control') || 'no-cache, no-transform',
    },
  });
}
