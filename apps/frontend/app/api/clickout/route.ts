import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { COOKIE_NAME } from '../auth/constants';

export const dynamic = 'force-dynamic';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function GET(request: NextRequest) {
  try {
    // Get auth token if available (for tracking, not required)
    const cookieStore = await cookies();
    const token = cookieStore.get(COOKIE_NAME)?.value;
    
    // Forward all query params to BFF
    const { searchParams } = new URL(request.url);
    const params = searchParams.toString();
    
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
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
