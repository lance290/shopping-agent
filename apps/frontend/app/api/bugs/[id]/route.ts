import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const BFF_URL = process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8080';

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  const cookieToken = request.cookies.get('sa_session')?.value;
  const token = cookieToken || process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
  
  // Also check Authorization header
  const authHeader = request.headers.get('Authorization');
  if (authHeader?.startsWith('Bearer ')) {
      return { Authorization: authHeader };
  }

  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    
    if (!id) {
        return NextResponse.json({ error: 'Missing bug ID' }, { status: 400 });
    }

    const response = await fetch(`${BFF_URL}/api/bugs/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
    });
    
    if (!response.ok) {
        if (response.status === 404) {
            return NextResponse.json({ error: 'Bug report not found' }, { status: 404 });
        }
        return NextResponse.json(
            { error: `BFF failed with ${response.status}` }, 
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Error fetching bug report:', error);
    return NextResponse.json({ error: 'Failed to fetch bug report' }, { status: 500 });
  }
}
