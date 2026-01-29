import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export const dynamic = 'force-dynamic'; // Disable caching

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

function getDevSessionToken(): string | undefined {
  return process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
}

function getCookieSessionToken(request: NextRequest): string | undefined {
  return request.cookies.get('sa_session')?.value;
}

function isClerkConfigured(): boolean {
  return Boolean(process.env.CLERK_SECRET_KEY);
}

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  if (disableClerk || !isClerkConfigured()) {
    const token = getCookieSessionToken(request) || getDevSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  try {
    const { getToken } = await auth();
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    const token = getDevSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ row_id: string }> }
) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const params = await context.params;
    const rowId = params.row_id;
    const body = await request.json();

    console.log(`[API] Creating custom bid for row ${rowId}:`, body);

    const response = await fetch(`${BFF_URL}/api/rows/${rowId}/custom-bids`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      console.error(`[API] BFF returned ${response.status}: ${text}`);
      return NextResponse.json(
        { error: 'Failed to create custom bid' },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log('[API] Custom bid created successfully:', data);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating custom bid:', error);
    return NextResponse.json(
      { error: 'Failed to create custom bid' },
      { status: 500 }
    );
  }
}
