import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Protected route prefixes — these require a valid sa_session cookie.
 * Everything else is public (homepage, search, guides, vendors, share, quote, etc.).
 *
 * This is intentionally a SHORT list that rarely changes. New public pages
 * work automatically without touching middleware.
 */
const PROTECTED_PREFIXES = [
  '/admin',
  '/seller',
  '/merchants',
  '/bugs',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // API routes handle their own auth
  if (pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  // Static assets — always pass through
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/static') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check if this is a protected route
  const isProtected = PROTECTED_PREFIXES.some(prefix => pathname.startsWith(prefix));

  if (!isProtected) {
    // Public route — allow anonymous access
    return NextResponse.next();
  }

  // Protected route — require auth
  const token = request.cookies.get('sa_session')?.value;
  if (!token) {
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
