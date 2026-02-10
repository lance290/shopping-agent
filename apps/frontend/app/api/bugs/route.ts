import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

import { BACKEND_URL } from '../../utils/bff';

function getAuthHeader(request: NextRequest): string | null {
  const direct = request.cookies.get('sa_session')?.value;
  if (direct) return `Bearer ${direct}`;
  
  const devToken = process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
  if (devToken) return `Bearer ${devToken}`;
  
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
    
    // Forward the raw body with original Content-Type to preserve multipart boundaries
    const contentType = request.headers.get('content-type');
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    
    const body = await request.arrayBuffer();
    
    const response = await fetch(`${BACKEND_URL}/api/bugs`, {
      method: 'POST',
      headers,
      body: Buffer.from(body),
    });
    
    if (!response.ok) {
        const text = await response.text();
        console.error(`[bugs] Backend /api/bugs failed: ${response.status}`, text);
        return NextResponse.json(
            { error: text || `Backend returned ${response.status}`, status: response.status }, 
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('[bugs] Error submitting bug report:', message);
    return NextResponse.json({ error: `Failed to submit bug report: ${message}` }, { status: 500 });
  }
}
