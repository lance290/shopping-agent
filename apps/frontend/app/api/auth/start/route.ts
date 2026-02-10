import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL } from '../constants';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/auth/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error in auth/start:', error);
    return NextResponse.json({ error: 'Failed to start auth' }, { status: 500 });
  }
}
