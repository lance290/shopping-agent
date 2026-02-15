import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ messageId: string }> }
) {
  const { messageId } = await params;
  return proxyPost(request, `/outreach/campaigns/messages/${messageId}/approve`);
}
