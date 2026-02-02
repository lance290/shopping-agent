import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = [
  '/login',
  '/sign-in',
  '/sign-up',
  '/marketing',
  '/api/proxy/auth', // Allow auth endpoints
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  // Check if path is public
  const isPublic = PUBLIC_PATHS.some(path => pathname.startsWith(path));

  // Also allow all internal API routes (they should handle their own auth or be open)
  // But we want to protect / page and other UI pages.
  // Actually, let's keep it simple: protect everything except public paths and assets.
  
  if (
    pathname.startsWith('/_next') || 
    pathname.startsWith('/static') || 
    pathname.includes('.') // file extensions
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get('sa_session')?.value;

  // If trying to access protected route without token, redirect to login
  if (!isPublic && !token) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
