import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8081'
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

    // Support fetching a single row by ID
    const url = new URL(request.url);
    const rowId = url.searchParams.get('id');
    const bffUrl = rowId ? `${BFF_URL}/api/rows/${rowId}` : `${BFF_URL}/api/rows`;

    const response = await fetch(bffUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching rows:', error);
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
    
    const response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating row:', error);
    return NextResponse.json({ error: 'Failed to create row' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    const response = await fetch(`${BFF_URL}/api/rows/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: authHeader,
      }
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error deleting row:', error);
    return NextResponse.json({ error: 'Failed to delete row' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    const body = await request.json();
    
    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    const bffUrl = `${BFF_URL}/api/rows/${id}`;

    const response = await fetch(bffUrl, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      console.error(`[API] BFF returned ${response.status} ${response.statusText}`);
      const text = await response.text();
      console.error(`[API] BFF response body: ${text}`);
      return NextResponse.json({ error: 'BFF failed' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error updating row:', error);
    return NextResponse.json({ error: 'Failed to update row' }, { status: 500 });
  }
}
