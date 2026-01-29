import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { NextResponse, type NextFetchEvent, type NextRequest } from 'next/server';

const isPublicRoute = createRouteMatcher([
  '/login(.*)',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/clerk_(.*)',
  '/api(.*)',
  '/api/health(.*)',
]);

const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
const secretKey = process.env.CLERK_SECRET_KEY;
const signInUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL || '/login';
const signUpUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_UP_URL || '/sign-up';

const middleware = clerkMiddleware(
  async (auth, request) => {
    const pathname = request.nextUrl.pathname;
    const isApiRoute = pathname.startsWith('/api');
    if (!isApiRoute && !isPublicRoute(request)) {
      await auth.protect();
    }
  },
  {
    publishableKey,
    secretKey,
    signInUrl,
    signUpUrl,
    debug: true,
  }
);

export default function authMiddleware(request: NextRequest, event: NextFetchEvent) {
  if (disableClerk) {
    return NextResponse.next();
  }

  if (request.nextUrl.pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  console.log(
    `[clerk:middleware] pk_prefix=${publishableKey?.slice(0, 12) || 'missing'} pk_len=${publishableKey?.length || 0} sk_set=${Boolean(secretKey)}`
  );
  return middleware(request, event);
}

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
  ],
};
