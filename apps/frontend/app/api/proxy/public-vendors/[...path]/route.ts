import { NextRequest } from 'next/server';
import { proxyGet } from '../../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const path = url.pathname.replace('/api/proxy/public-vendors', '/api/public/vendors');
  const search = url.search;
  return proxyGet(request, `${path}${search}`, { allowAnonymous: true });
}
