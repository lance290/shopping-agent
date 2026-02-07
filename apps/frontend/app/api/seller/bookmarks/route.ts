import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';

    const res = await fetch(`${BACKEND_URL}/seller/bookmarks`, {
      headers: { Authorization: auth },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /seller/bookmarks] Error:', error);
    return NextResponse.json({ error: 'Failed to fetch bookmarks' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';
    const body = await request.json();
    const { row_id } = body;

    if (!row_id) {
      return NextResponse.json({ error: 'row_id required' }, { status: 400 });
    }

    const res = await fetch(`${BACKEND_URL}/seller/bookmarks/${row_id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: auth,
      },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /seller/bookmarks POST] Error:', error);
    return NextResponse.json({ error: 'Failed to add bookmark' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization') || '';
    const { searchParams } = new URL(request.url);
    const rowId = searchParams.get('row_id');

    if (!rowId) {
      return NextResponse.json({ error: 'row_id required' }, { status: 400 });
    }

    const res = await fetch(`${BACKEND_URL}/seller/bookmarks/${rowId}`, {
      method: 'DELETE',
      headers: { Authorization: auth },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error('[API /seller/bookmarks DELETE] Error:', error);
    return NextResponse.json({ error: 'Failed to remove bookmark' }, { status: 500 });
  }
}
