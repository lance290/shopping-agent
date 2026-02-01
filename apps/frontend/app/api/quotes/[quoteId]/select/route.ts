import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || process.env.NEXT_PUBLIC_BFF_URL || 'http://localhost:8080';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ quoteId: string }> }
) {
  try {
    const { quoteId } = await params;
    const body = await request.json();
    
    // Build query params for buyer info
    const queryParams = new URLSearchParams();
    if (body.buyer_name) queryParams.set('buyer_name', body.buyer_name);
    if (body.buyer_phone) queryParams.set('buyer_phone', body.buyer_phone);
    
    const url = `${BFF_URL}/api/quotes/${quoteId}/select${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    
    const res = await fetch(url, {
      method: 'POST',
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
    console.error('Quote select error:', error);
    return NextResponse.json(
      { detail: 'Failed to select quote' },
      { status: 500 }
    );
  }
}
