import { NextRequest } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../utils/api-proxy';

export async function POST(request: NextRequest) {
  const auth = getAuthHeader(request);

  const body = await request.json();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (auth) headers['Authorization'] = auth;

  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  // Stream the response back (SSE — cannot use generic proxy)
  return new Response(response.body, {
    status: response.status,
    headers: {
      'Content-Type': response.headers.get('Content-Type') || 'text/event-stream; charset=utf-8',
      'Cache-Control': response.headers.get('Cache-Control') || 'no-cache, no-transform',
    },
  });
}
