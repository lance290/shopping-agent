import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';
    const { searchParams } = new URL(request.url);
    const bidIds = searchParams.get('bid_ids') || '';

    if (!bidIds) {
      return NextResponse.json({}, { status: 200 });
    }

    const res = await fetch(
      `${BACKEND_URL}/bids/social/batch?bid_ids=${encodeURIComponent(bidIds)}`,
      {
        headers: { Authorization: auth },
      }
    );

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /bids/social/batch] Error:', error);
    return NextResponse.json({ error: 'Failed to fetch social data' }, { status: 500 });
  }
}
