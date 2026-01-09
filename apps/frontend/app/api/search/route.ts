import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
