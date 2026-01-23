import { NextRequest } from 'next/server';
import { auth } from '@clerk/nextjs/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BFF_URL = normalizeBaseUrl(process.env.BFF_URL || 'http://localhost:8080');

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

export async function POST(request: NextRequest) {
  let token: string | null = null;
  if (disableClerk) {
    token = process.env.DEV_SESSION_TOKEN || null;
  } else {
    const { getToken } = await auth();
    token = await getToken();
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
      'Content-Type': response.headers.get('Content-Type') || 'text/plain',
    },
  });
}
