import { NextRequest, NextResponse } from 'next/server';
import { proxyGet, proxyPost, proxyPatch, proxyDelete } from '../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const rowId = request.nextUrl.searchParams.get('id');
  const path = rowId ? `/rows/${rowId}` : '/rows';
  return proxyGet(request, path, { allowAnonymous: true });
}

export async function POST(request: NextRequest) {
  return proxyPost(request, '/rows');
}

export async function DELETE(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  if (!id) {
    return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
  }
  return proxyDelete(request, `/rows/${id}`);
}

export async function PATCH(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  if (!id) {
    return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
  }
  return proxyPatch(request, `/rows/${id}`);
}
