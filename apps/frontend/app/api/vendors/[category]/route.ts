import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ category: string }> }
) {
  const { category } = await params;
  return proxyGet(request, `/outreach/vendors/${category}`, { allowAnonymous: true });
}
