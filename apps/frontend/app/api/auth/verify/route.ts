import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL, COOKIE_NAME } from '../constants';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    
    if (response.ok && data.session_token) {
      const res = NextResponse.json({ status: 'ok' }, { status: 200 });
      
      res.cookies.set(COOKIE_NAME, data.session_token, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
      });
      
      return res;
    }
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error in auth/verify:', error);
    return NextResponse.json({ error: 'Failed to verify auth' }, { status: 500 });
  }
}
