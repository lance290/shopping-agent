import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

import { BACKEND_URL } from '../../utils/bff';

export async function POST(request: NextRequest) {
  try {
    // Match chat route's auth handling exactly
    let token: string | null = null;
    const cookie = request.cookies.get('sa_session')?.value;
    if (cookie) {
      token = cookie;
    } else {
      const authHeader = request.headers.get('Authorization');
      if (authHeader?.startsWith('Bearer ')) {
        token = authHeader.substring(7);
      }
    }
    
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    
    const response = await fetch(`${BACKEND_URL}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error searching:', error);
    return NextResponse.json({ results: [] }, { status: 500 });
  }
}
