import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  const { rowId } = await params;
  return proxyPost(request, `/rows/${rowId}/events`);
}
