import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8080'
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
    
    if (!rowId) {
      return NextResponse.json({ error: 'Missing row_id' }, { status: 400 });
    }

    const response = await fetch(`${BFF_URL}/api/comments?row_id=${rowId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching comments:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/api/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating comment:', error);
    return NextResponse.json({ error: 'Failed to create comment' }, { status: 500 });
  }
}
