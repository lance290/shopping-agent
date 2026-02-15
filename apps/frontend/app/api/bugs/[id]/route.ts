import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyGet(request, `/api/bugs/${id}`);
}
