import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function GET() {
  try {
    const response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching rows:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating row:', error);
    return NextResponse.json({ error: 'Failed to create row' }, { status: 500 });
  }
}
