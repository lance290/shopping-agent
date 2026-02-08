import { NextRequest, NextResponse } from 'next/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BACKEND_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

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
    
    const url = rowId ? `${BACKEND_URL}/likes?row_id=${rowId}` : `${BACKEND_URL}/likes`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching likes:', error);
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

    const response = await fetch(`${BACKEND_URL}/likes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify(body),
    });

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      console.error('Error parsing response:', parseError);
      return NextResponse.json(
        { error: 'Invalid response from server' },
        { status: response.status || 500 }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating like:', error);
    return NextResponse.json({ error: 'Failed to create like' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const params = request.nextUrl.searchParams.toString();

    const response = await fetch(`${BACKEND_URL}/likes?${params}`, {
      method: 'DELETE',
      headers: {
        Authorization: authHeader,
      },
    });

    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      console.error('Error parsing response:', parseError);
      return NextResponse.json(
        { error: 'Invalid response from server' },
        { status: response.status || 500 }
      );
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error deleting like:', error);
    return NextResponse.json({ error: 'Failed to delete like' }, { status: 500 });
  }
}
