import { NextRequest, NextResponse } from 'next/server';
import { proxyGet, proxyPost, proxyDelete } from '../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  return proxyGet(request, '/projects');
}

export async function POST(request: NextRequest) {
  return proxyPost(request, '/projects');
}

export async function DELETE(request: NextRequest) {
  const id = request.nextUrl.searchParams.get('id');
  if (!id) {
    return NextResponse.json({ error: 'Missing project ID' }, { status: 400 });
  }
  return proxyDelete(request, `/projects/${id}`);
}
