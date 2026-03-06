import { NextRequest } from 'next/server';
import { proxyGet, proxyPost } from '../../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyGet(request, `/pop/item/${id}/comments`));
}

export function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  return params.then(({ id }) => proxyPost(request, `/pop/item/${id}/comments`));
}
