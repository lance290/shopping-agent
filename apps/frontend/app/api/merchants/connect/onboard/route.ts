import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';

    const res = await fetch(`${BACKEND_URL}/merchants/connect/onboard`, {
      method: 'POST',
      headers: { Authorization: auth, 'Content-Type': 'application/json' },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /merchants/connect/onboard] Error:', error);
    return NextResponse.json({ error: 'Failed to start onboarding' }, { status: 500 });
  }
}
