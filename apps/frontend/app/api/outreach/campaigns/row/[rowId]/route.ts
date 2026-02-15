import { NextRequest } from 'next/server';
import { proxyGet } from '../../../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  const { rowId } = await params;
  return proxyGet(request, `/outreach/campaigns/row/${rowId}`);
}
