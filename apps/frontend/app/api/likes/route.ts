import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader, proxyGet } from '../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const rowId = request.nextUrl.searchParams.get('row_id');
  const path = rowId ? `/likes?row_id=${rowId}` : '/likes';
  return proxyGet(request, path);
}

export async function POST(request: NextRequest) {
  const auth = getAuthHeader(request);
  if (!auth) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  try {
    const body = await request.json();
    const bidId = body?.bid_id;
    if (!bidId) {
      return NextResponse.json({ error: 'bid_id required' }, { status: 400 });
    }

    // ONE endpoint: toggle like on/off
    const response = await fetch(`${BACKEND_URL}/likes/${bidId}/toggle`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: auth,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error toggling like:', error);
    return NextResponse.json({ error: 'Failed to toggle like' }, { status: 500 });
  }
}
