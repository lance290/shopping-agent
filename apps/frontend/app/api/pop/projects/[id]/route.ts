import { NextRequest } from 'next/server';
import { proxyPatch } from '../../../../utils/api-proxy';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  return proxyPatch(request, `/pop/projects/${id}`);
}
