import { NextRequest } from 'next/server';
import { proxyGet } from '../../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ campaignId: string }> }
) {
  const { campaignId } = await params;
  return proxyGet(request, `/outreach/campaigns/${campaignId}`);
}
