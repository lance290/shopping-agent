import { NextRequest } from 'next/server';
import { proxyPost } from '../../../utils/api-proxy';

export async function POST(request: NextRequest) {
  return proxyPost(request, '/api/public/quote-intent', { allowAnonymous: true });
}
