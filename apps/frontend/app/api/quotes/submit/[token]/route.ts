import { NextRequest } from 'next/server';
import { proxyPost } from '../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  return proxyPost(request, `/quotes/submit/${token}`, { allowAnonymous: true });
}
