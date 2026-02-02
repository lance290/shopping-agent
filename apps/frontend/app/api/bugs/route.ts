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

export async function POST(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    const headers: Record<string, string> = {};
    
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }
    
    // We expect FormData because of file attachments
    const formData = await request.formData();
    
    // Forward to BFF
    const response = await fetch(`${BFF_URL}/api/bugs`, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    if (!response.ok) {
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
