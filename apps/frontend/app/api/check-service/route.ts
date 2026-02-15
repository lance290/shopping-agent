import { NextRequest } from 'next/server';
import { proxyGet } from '../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get('query') || '';
  return proxyGet(request, `/outreach/check-service?query=${encodeURIComponent(query)}`, { allowAnonymous: true });
}
