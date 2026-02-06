import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL } from '../../utils/bff';

function getAuthHeader(request: NextRequest): string | null {
  const direct = request.cookies.get('sa_session')?.value;
  if (direct) return `Bearer ${direct}`;
  const authHeader = request.headers.get('Authorization');
  if (authHeader?.startsWith('Bearer ')) return authHeader;
  return null;
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = getAuthHeader(request);
    if (!authHeader) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const body = await request.json();

    const response = await fetch(`${BFF_URL}/api/shares`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authHeader,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating share link:', error);
    return NextResponse.json({ error: 'Failed to create share link' }, { status: 500 });
  }
}
