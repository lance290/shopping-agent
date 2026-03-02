import { NextRequest } from 'next/server';
import { proxyPost, proxyDelete } from '../../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyPost(request, `/pop/offer/${id}/claim`);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyDelete(request, `/pop/offer/${id}/claim`);
}
