import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../utils/api-proxy';

export async function POST(request: NextRequest) {
  const auth = getAuthHeader(request);
  const body = await request.json();
  const { message, email } = body;

  if (!message) {
    return NextResponse.json({ error: 'Message is required' }, { status: 400 });
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (auth) headers['Authorization'] = auth;

  // Route through the Bob webhook endpoint which handles NLU + sourcing + reply
  // For web chat, we call process_bob_message via a dedicated endpoint
  const response = await fetch(`${BACKEND_URL}/bob/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      email: email || undefined,
      channel: 'web',
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    return NextResponse.json(
      { error: text || 'Backend error' },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
