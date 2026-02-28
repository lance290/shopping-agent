import { NextRequest } from 'next/server';
import { proxyPatch, proxyDelete } from '../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyPatch(request, `/pop/item/${id}`);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxyDelete(request, `/pop/item/${id}`);
}
