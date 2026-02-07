import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const cookieToken = request.cookies.get('sa_session')?.value;
    const auth = cookieToken
      ? `Bearer ${cookieToken}`
      : (request.headers.get('authorization') || '');

    console.log(`[merchant-register] POST ${BACKEND_URL}/merchants/register auth=${auth ? 'present' : 'missing'}`);

    const response = await fetch(`${BACKEND_URL}/merchants/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: auth,
      },
      body: JSON.stringify(body),
    });

    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      console.error(`[merchant-register] Non-JSON response (${response.status}):`, text.slice(0, 500));
      return NextResponse.json({ detail: `Backend error (${response.status})` }, { status: 502 });
    }

    if (!response.ok) {
      console.error(`[merchant-register] Backend ${response.status}:`, data);
    }
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('[merchant-register] Proxy error:', error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : 'Failed to reach backend' },
      { status: 502 },
    );
  }
}
