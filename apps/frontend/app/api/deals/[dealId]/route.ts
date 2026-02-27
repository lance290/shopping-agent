import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ dealId: string }> }
) {
  const { dealId } = await params;
  return proxyGet(request, `/deals/${dealId}`);
}
