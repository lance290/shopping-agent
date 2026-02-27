import { NextRequest } from 'next/server';
import { proxyGet, proxyPost } from '../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const status = request.nextUrl.searchParams.get('status');
  const path = status ? `/deals?status=${status}` : '/deals';
  return proxyGet(request, path);
}

export async function POST(request: NextRequest) {
  return proxyPost(request, '/deals');
}
