import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const includeProvenance = request.nextUrl.searchParams.get('include_provenance');
  const path = includeProvenance
    ? `/bids/${id}?include_provenance=true`
    : `/bids/${id}`;
  return proxyGet(request, path);
}
