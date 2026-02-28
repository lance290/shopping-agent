import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = getAuthHeader(request);
  if (!auth) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });

  const body = await request.json();
  const response = await fetch(`${BACKEND_URL}/pop/item/${id}`, {
    method: 'PATCH',
    headers: { Authorization: auth, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    return NextResponse.json({ error: 'Failed to update item' }, { status: response.status });
  }
  return NextResponse.json(await response.json());
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = getAuthHeader(request);
  if (!auth) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });

  const response = await fetch(`${BACKEND_URL}/pop/item/${id}`, {
    method: 'DELETE',
    headers: { Authorization: auth },
  });

  if (!response.ok) {
    return NextResponse.json({ error: 'Failed to delete item' }, { status: response.status });
  }
  return NextResponse.json(await response.json());
}
