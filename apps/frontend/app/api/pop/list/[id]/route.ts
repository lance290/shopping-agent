import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../../utils/api-proxy';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const auth = getAuthHeader(request);

  const headers: Record<string, string> = {};
  if (auth) headers['Authorization'] = auth;

  const response = await fetch(`${BACKEND_URL}/pop/list/${id}`, { headers });

  if (!response.ok) {
    return NextResponse.json(
      { error: 'Failed to fetch list' },
      { status: response.status },
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
