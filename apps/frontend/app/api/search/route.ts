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
  // Always check for dev session token first (cookie or env)
  const devToken =
    request.cookies.get('sa_session')?.value ||
    process.env.DEV_SESSION_TOKEN ||
    process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
  
  if (devToken) {
    return { Authorization: `Bearer ${devToken}` };
  }

  // Fall back to Clerk if no dev token
  if (!disableClerk) {
    try {
      const { getToken } = await auth();
      const token = await getToken();
      if (token) {
        return { Authorization: `Bearer ${token}` };
      }
    } catch (e) {
      console.error('[search] Clerk auth error:', e);
    }
  }

  return {};
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const authHeader = await getAuthHeader(request);
    console.log('[search route] authHeader:', authHeader.Authorization ? 'Bearer ***' + authHeader.Authorization.slice(-10) : 'NONE');
    if (!authHeader.Authorization) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BFF_URL}/api/search`, {
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
    console.error('Error searching:', error);
    return NextResponse.json({ results: [] }, { status: 500 });
  }
}
