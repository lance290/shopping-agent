import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8081';

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
    
    // Forward all query params to BFF
    const { searchParams } = new URL(request.url);
    const params = searchParams.toString();
    
    const headers: Record<string, string> = {};
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }
    
    // Fetch from BFF, don't follow redirects
    const response = await fetch(`${BFF_URL}/api/out?${params}`, {
      headers,
      redirect: 'manual',
    });
    
    // Get the redirect location from BFF
    const location = response.headers.get('location');
    
    if (location) {
      // Redirect to the affiliate URL
      return NextResponse.redirect(location, 302);
    } else {
      // If no redirect, pass through the response
      const text = await response.text();
      return new NextResponse(text, { status: response.status });
    }
  } catch (error) {
    console.error('Error in clickout:', error);
    // Fallback: redirect to the original URL if BFF fails
    const url = request.nextUrl.searchParams.get('url');
    if (url) {
      return NextResponse.redirect(url, 302);
    }
    return NextResponse.json({ error: 'Clickout failed' }, { status: 500 });
  }
}
