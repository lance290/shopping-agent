import { NextRequest } from 'next/server';
import { proxyGet, proxyPost } from '../../../utils/api-proxy';

// Trigger outreach
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  const { rowId } = await params;
  return proxyPost(request, `/outreach/rows/${rowId}/trigger`, { allowAnonymous: true });
}

// Get outreach status
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  const { rowId } = await params;
  return proxyGet(request, `/outreach/rows/${rowId}/status`, { allowAnonymous: true });
}
