import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BACKEND_URL = normalizeBaseUrl(
  process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  if (disableClerk) {
    const token = request.cookies.get('sa_session')?.value || process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  try {
    const { getToken } = await auth();
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

export async function GET(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    const rowId = request.nextUrl.searchParams.get('row_id');
    
    const url = rowId ? `${BACKEND_URL}/likes?row_id=${rowId}` : `${BACKEND_URL}/likes`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
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
    const authHeader = await getAuthHeader(request);
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/likes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
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
    const authHeader = await getAuthHeader(request);
    const params = request.nextUrl.searchParams.toString();

    const response = await fetch(`${BACKEND_URL}/likes?${params}`, {
      method: 'DELETE',
      headers: {
        ...authHeader,
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
