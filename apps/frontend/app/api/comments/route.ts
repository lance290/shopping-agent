import { NextRequest, NextResponse } from 'next/server';

import { BACKEND_URL } from '../../utils/bff';

function getAuthHeader(request: NextRequest): string | null {
  const direct = request.cookies.get('sa_session')?.value;
  if (direct) return `Bearer ${direct}`;
  
  const authHeader = request.headers.get('Authorization');
  if (authHeader?.startsWith('Bearer ')) return authHeader;
  
  return null;
}

export async function GET(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const rowId = request.nextUrl.searchParams.get('row_id');
    
    if (!rowId) {
      return NextResponse.json({ error: 'Missing row_id' }, { status: 400 });
    }

    const response = await fetch(`${BACKEND_URL}/comments?row_id=${rowId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
    });

    if (response.status === 404) {
      return NextResponse.json([], { status: 200 });
    }

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      return NextResponse.json({ error: text || 'Failed to fetch comments' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Error fetching comments:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const body = await request.json();
    
    const response = await fetch(`${BACKEND_URL}/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify(body),
    });

    if (response.status === 404) {
      return NextResponse.json({ error: 'Comments not implemented' }, { status: 501 });
    }

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      return NextResponse.json({ error: text || 'Failed to create comment' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Error creating comment:', error);
    return NextResponse.json({ error: 'Failed to create comment' }, { status: 500 });
  }
}
