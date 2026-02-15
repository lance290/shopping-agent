import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader, proxyGet, proxyDelete } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  return proxyGet(request, '/seller/bookmarks');
}

export async function POST(request: NextRequest) {
  const auth = getAuthHeader(request);
  if (!auth) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  try {
    const body = await request.json();
    const { row_id } = body;
    if (!row_id) return NextResponse.json({ error: 'row_id required' }, { status: 400 });

    const res = await fetch(`${BACKEND_URL}/seller/bookmarks/${row_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: auth },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /seller/bookmarks POST] Error:', error);
    return NextResponse.json({ error: 'Failed to add bookmark' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  const rowId = request.nextUrl.searchParams.get('row_id');
  if (!rowId) return NextResponse.json({ error: 'row_id required' }, { status: 400 });
  return proxyDelete(request, `/seller/bookmarks/${rowId}`);
}
