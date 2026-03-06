import { NextRequest } from 'next/server';
import { proxyGet, proxyPost } from '../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get('token') || '';
  return proxyGet(request, `/pop/brands/claim?token=${encodeURIComponent(token)}`, { allowAnonymous: true });
}

export function POST(request: NextRequest) {
  return proxyPost(request, '/pop/brands/claim', { allowAnonymous: true });
}
