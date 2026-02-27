import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ dealId: string }> }
) {
  const { dealId } = await params;
  return proxyPost(request, `/deals/${dealId}/release`);
}
