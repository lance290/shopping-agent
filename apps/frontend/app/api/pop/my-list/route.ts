import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../utils/api-proxy';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const auth = getAuthHeader(request);
  if (!auth) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });

  const headers: Record<string, string> = { Authorization: auth };
  const response = await fetch(`${BACKEND_URL}/pop/my-list`, { headers });

  if (!response.ok) {
    return NextResponse.json({ error: 'Failed to fetch list' }, { status: response.status });
  }
  return NextResponse.json(await response.json());
}
