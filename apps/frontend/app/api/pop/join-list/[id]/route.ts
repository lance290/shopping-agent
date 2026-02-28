import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../../utils/api-proxy';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = getAuthHeader(request);

  if (!auth) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const response = await fetch(`${BACKEND_URL}/pop/join-list/${id}`, {
    method: 'POST',
    headers: { Authorization: auth },
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: 'Failed to join list' },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
