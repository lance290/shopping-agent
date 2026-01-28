import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export const dynamic = 'force-dynamic';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8080'
);

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  if (disableClerk) {
    const cookieToken = request.cookies.get('sa_session')?.value;
    const token = cookieToken || process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  const { getToken } = await auth();
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    // Note: We might want to allow anonymous reporting if auth not present, 
    // but typically we want at least the auth header if available.
    // The plan mentioned "Open access (for now)" but code structure usually benefits from passing auth if we have it.
    
    // We expect FormData because of file attachments
    const formData = await request.formData();
    
    // Forward to BFF
    // When sending FormData with fetch, do NOT set Content-Type header manually; 
    // fetch will set it with the boundary.
    const response = await fetch(`${BFF_URL}/api/bugs`, {
      method: 'POST',
      headers: {
        // 'Content-Type': 'multipart/form-data', // DO NOT SET THIS
        ...authHeader,
      },
      body: formData,
    });
    
    if (!response.ok) {
        // Try to parse error as text or json
        const text = await response.text();
        console.error(`[API] BFF /api/bugs failed: ${response.status}`, text);
        return NextResponse.json(
            { error: `BFF failed with ${response.status}` }, 
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error('Error submitting bug report:', error);
    return NextResponse.json({ error: 'Failed to submit bug report' }, { status: 500 });
  }
}
