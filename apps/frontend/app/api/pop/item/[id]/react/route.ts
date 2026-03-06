import { NextRequest } from 'next/server';
import { proxyPost, proxyGet } from '../../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyPost(request, `/pop/item/${id}/react`));
}

export function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyGet(request, `/pop/item/${id}/reactions`));
}
