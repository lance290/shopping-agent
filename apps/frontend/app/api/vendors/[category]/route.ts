import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ category: string }> }
) {
  const { category } = await params;
  const qs = request.nextUrl.searchParams.toString();
  const path = `/outreach/vendors/${category}${qs ? `?${qs}` : ''}`;
  return proxyGet(request, path, { allowAnonymous: true });
}
