import { NextRequest } from 'next/server';
import { proxyPost } from '../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  return proxyPost(request, '/api/search');
}
