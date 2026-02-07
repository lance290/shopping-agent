import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

// Bug reports go directly to backend (skip BFF) — consistent with POST route
const BACKEND_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://127.0.0.1:8000'
);

function getAuthHeader(request: NextRequest): string | null {
  const direct = request.cookies.get('sa_session')?.value;
  if (direct) return `Bearer ${direct}`;

  const devToken = process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
  if (devToken) return `Bearer ${devToken}`;

  const authHeader = request.headers.get('Authorization');
  if (authHeader?.startsWith('Bearer ')) return authHeader;

  return null;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;

    if (!id) {
        return NextResponse.json({ error: 'Missing bug ID' }, { status: 400 });
    }

    const response = await fetch(`${BACKEND_URL}/api/bugs/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
    });

    if (!response.ok) {
        if (response.status === 404) {
            return NextResponse.json({ error: 'Bug report not found' }, { status: 404 });
        }
        const text = await response.text();
        console.error(`[bugs] Backend /api/bugs/${id} failed: ${response.status}`, text);
        return NextResponse.json(
            { error: text || `Backend returned ${response.status}` },
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[bugs] Error fetching bug report:', message);
    return NextResponse.json({ error: `Failed to fetch bug report: ${message}` }, { status: 500 });
  }
}
