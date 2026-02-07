import { NextRequest, NextResponse } from 'next/server';

function getBackendUrl(): string {
  return process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const cookieToken = request.cookies.get('sa_session')?.value;
    const auth = cookieToken
      ? `Bearer ${cookieToken}`
      : (request.headers.get('authorization') || '');

    const response = await fetch(`${getBackendUrl()}/merchants/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: auth,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error registering merchant:', error);
    return NextResponse.json({ error: 'Failed to register merchant' }, { status: 500 });
  }
}
