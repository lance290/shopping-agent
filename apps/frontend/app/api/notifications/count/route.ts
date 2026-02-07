import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const cookieToken = request.cookies.get('sa_session')?.value;
    const auth = cookieToken ? `Bearer ${cookieToken}` : (request.headers.get('authorization') || '');

    const res = await fetch(`${BACKEND_URL}/notifications/count`, {
      headers: { Authorization: auth },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /notifications/count] Error:', error);
    return NextResponse.json({ error: 'Failed to fetch count' }, { status: 500 });
  }
}
