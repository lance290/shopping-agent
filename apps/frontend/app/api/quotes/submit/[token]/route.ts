import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || process.env.NEXT_PUBLIC_BFF_URL || 'http://localhost:8080';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  try {
    const { token } = await params;
    const body = await request.json();
    
    const res = await fetch(`${BFF_URL}/api/quotes/submit/${token}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Quote submit error:', error);
    return NextResponse.json(
      { detail: 'Failed to submit quote' },
      { status: 500 }
    );
  }
}
