import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  const { rowId } = await params;
  return proxyPost(request, `/outreach/rows/${rowId}/quote-link`);
}
