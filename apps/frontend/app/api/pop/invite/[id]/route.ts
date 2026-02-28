import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../../utils/api-proxy';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const response = await fetch(`${BACKEND_URL}/pop/invite/${id}`);

  if (!response.ok) {
    return NextResponse.json(
      { error: 'Invite not found or expired' },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = getAuthHeader(request);

  if (!auth) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const response = await fetch(`${BACKEND_URL}/pop/list/${id}/invite`, {
    method: 'POST',
    headers: { Authorization: auth },
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: 'Failed to create invite' },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
