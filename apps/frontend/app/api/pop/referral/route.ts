import { NextRequest } from 'next/server';
import { proxyGet, proxyPost } from '../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export function GET(request: NextRequest) {
  return proxyGet(request, '/pop/referral');
}

export function POST(request: NextRequest) {
  return proxyPost(request, '/pop/referral/signup');
}
