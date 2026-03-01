import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL, COOKIE_NAME } from '../constants';

export async function POST(request: NextRequest) {
  try {
    const sessionToken = request.cookies.get(COOKIE_NAME)?.value;

    if (!sessionToken) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetch(`${BFF_URL}/auth/location`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error in auth/location:', error);
    return NextResponse.json({ error: 'Failed to set location' }, { status: 500 });
  }
}
