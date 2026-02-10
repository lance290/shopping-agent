import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL, COOKIE_NAME } from '../constants';

export async function POST(request: NextRequest) {
  const sessionToken = request.cookies.get(COOKIE_NAME)?.value;
  let backendLogoutSuccess = true;
  
  if (sessionToken) {
    try {
      const response = await fetch(`${BFF_URL}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${sessionToken}` },
      });
      backendLogoutSuccess = response.ok;
    } catch (error) {
      console.error('Error calling backend logout:', error);
      backendLogoutSuccess = false;
    }
  }
  
  const res = NextResponse.json(
    { status: 'ok', backend_logout: backendLogoutSuccess },
    { status: 200 }
  );
  
  res.cookies.set(COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  
  return res;
}
