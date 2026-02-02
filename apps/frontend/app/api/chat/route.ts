import { NextRequest } from 'next/server';

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

export async function POST(request: NextRequest) {
  let token: string | null = null;

  // Use sa_session cookie or Authorization header
  const cookie = request.cookies.get('sa_session')?.value;
  if (cookie) {
    token = cookie;
  } else {
    const authHeader = request.headers.get('Authorization');
    if (authHeader?.startsWith('Bearer ')) {
      token = authHeader.substring(7);
    }
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
