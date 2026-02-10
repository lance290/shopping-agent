import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL, COOKIE_NAME } from '../constants';

export async function GET(request: NextRequest) {
  try {
    const sessionToken = request.cookies.get(COOKIE_NAME)?.value;
    
    if (!sessionToken) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }
    
    const response = await fetch(`${BFF_URL}/auth/me`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error in auth/me:', error);
    return NextResponse.json({ error: 'Failed to check auth' }, { status: 500 });
  }
}
