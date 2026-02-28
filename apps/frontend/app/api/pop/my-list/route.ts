import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export function GET(request: NextRequest) {
  return proxyGet(request, '/pop/my-list');
}
