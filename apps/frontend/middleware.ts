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
  '/app',
];

const POP_DOMAINS = ['popsavings.com', 'www.popsavings.com'];

function isPopDomain(hostname: string): boolean {
  return POP_DOMAINS.includes(hostname) || hostname.endsWith('.popsavings.com');
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hostname = request.headers.get('host')?.split(':')[0] ?? '';

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

  // ---------------------------------------------------------------------------
  // Pop domain routing: popsavings.com → /(pop)/ route group
  // In dev, use ?brand=pop query param to simulate
  // ---------------------------------------------------------------------------
  const isPop = isPopDomain(hostname) || request.nextUrl.searchParams.get('brand') === 'pop';

  if (isPop && !pathname.startsWith('/pop-site')) {
    // Rewrite / → /pop-site, /chat → /pop-site/chat, etc.
    // Skip paths that are BuyAnything-specific
    const buyAnythingPrefixes = ['/admin', '/seller', '/merchants', '/bugs', '/app', '/login', '/guides', '/disclosure', '/share', '/quote'];
    const isBuyAnythingRoute = buyAnythingPrefixes.some(p => pathname.startsWith(p));

    if (!isBuyAnythingRoute) {
      const popPath = pathname === '/' ? '/pop-site' : `/pop-site${pathname}`;
      const url = request.nextUrl.clone();
      url.pathname = popPath;
      const response = NextResponse.rewrite(url);
      response.headers.set('x-brand', 'pop');
      return response;
    }
  }

  // Set brand header for BuyAnything routes
  const response = NextResponse.next();
  if (isPop) {
    response.headers.set('x-brand', 'pop');
  }

  // Check if this is a protected route
  const isProtected = PROTECTED_PREFIXES.some(prefix => pathname.startsWith(prefix));

  if (!isProtected) {
    return response;
  }

  // Protected route — require auth
  const token = request.cookies.get('sa_session')?.value;
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    return NextResponse.redirect(loginUrl);
  }

  return response;
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
