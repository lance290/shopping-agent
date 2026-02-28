import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../utils/api-proxy';

export async function POST(request: NextRequest) {
  try {
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

    const url = `${BACKEND_URL}/bob/chat`;
    console.log(`[pop/chat] POST ${url}`);

    const response = await fetch(url, {
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
      console.error(`[pop/chat] Backend returned ${response.status}: ${text.slice(0, 200)}`);
      return NextResponse.json(
        { reply: 'Hmm, I had trouble processing that. Try again in a moment!' },
        { status: 200 },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[pop/chat] Proxy error:', error);
    return NextResponse.json(
      { reply: 'Oops, I couldn\'t reach my brain. Check back in a sec!', list_items: [], project_id: null },
      { status: 200 },
    );
  }
}
