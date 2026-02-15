import { NextRequest } from 'next/server';
import { proxyGet } from '../../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  return proxyGet(request, `/quotes/form/${token}`, { allowAnonymous: true });
}
