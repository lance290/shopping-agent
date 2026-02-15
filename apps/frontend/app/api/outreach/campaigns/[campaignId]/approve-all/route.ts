import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ campaignId: string }> }
) {
  const { campaignId } = await params;
  return proxyPost(request, `/outreach/campaigns/${campaignId}/approve-all`);
}
