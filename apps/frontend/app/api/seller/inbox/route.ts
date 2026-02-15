import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const page = request.nextUrl.searchParams.get('page') || '1';
  const perPage = request.nextUrl.searchParams.get('per_page') || '20';
  return proxyGet(request, `/seller/inbox?page=${page}&per_page=${perPage}`);
}
