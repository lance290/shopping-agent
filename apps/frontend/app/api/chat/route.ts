import { NextRequest } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  const { getToken } = await auth();
  const token = await getToken();
  
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
