import { NextRequest, NextResponse } from 'next/server';
import { proxyGet, proxyPost } from '../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const rowId = request.nextUrl.searchParams.get('row_id');
  if (!rowId) {
    return NextResponse.json({ error: 'Missing row_id' }, { status: 400 });
  }
  return proxyGet(request, `/comments?row_id=${rowId}`, { allowAnonymous: true });
}

export async function POST(request: NextRequest) {
  return proxyPost(request, '/comments');
}
