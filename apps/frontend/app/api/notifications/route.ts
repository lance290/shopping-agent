import { NextRequest } from 'next/server';
import { proxyGet } from '../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const unread = request.nextUrl.searchParams.get('unread_only') || 'false';
  return proxyGet(request, `/notifications?unread_only=${unread}`);
}
