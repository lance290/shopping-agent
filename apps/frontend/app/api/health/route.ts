import { NextResponse } from 'next/server';

export async function GET() {
  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || '';
  const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'nextjs-app',
    version: process.env.npm_package_version || '0.1.0',
    clerk: {
      disabled: disableClerk,
      publishable_key_prefix: pk ? pk.slice(0, 12) : null,
      publishable_key_len: pk ? pk.length : 0,
      publishable_key_ends_with_dollar: pk ? pk.endsWith('$') : false,
    },
  });
}
