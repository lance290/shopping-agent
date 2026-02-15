import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const days = request.nextUrl.searchParams.get('days') || '30';
  return proxyGet(request, `/admin/metrics?days=${days}`);
}
