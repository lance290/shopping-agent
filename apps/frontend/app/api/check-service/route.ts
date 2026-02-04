import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.get('query') || '';
    
    const res = await fetch(`${BACKEND_URL}/outreach/check-service?query=${encodeURIComponent(query)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await res.json();
    
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Check service error:', error);
    return NextResponse.json(
      { detail: 'Failed to check service' },
      { status: 500 }
    );
  }
}
