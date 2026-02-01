import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || process.env.NEXT_PUBLIC_BFF_URL || 'http://localhost:8080';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  try {
    const { token } = await params;
    
    const res = await fetch(`${BFF_URL}/api/quotes/form/${token}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await res.json();
    
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Quote form fetch error:', error);
    return NextResponse.json(
      { detail: 'Failed to load quote form' },
      { status: 500 }
    );
  }
}
