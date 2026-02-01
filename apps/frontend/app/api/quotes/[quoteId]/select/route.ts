import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function POST(
  request: NextRequest,
  { params }: { params: { quoteId: string } }
) {
  try {
    const { quoteId } = params;
    const body = await request.json();
    
    // Build query params for buyer info
    const queryParams = new URLSearchParams();
    if (body.buyer_name) queryParams.set('buyer_name', body.buyer_name);
    if (body.buyer_phone) queryParams.set('buyer_phone', body.buyer_phone);
    
    const url = `${BACKEND_URL}/quotes/${quoteId}/select${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    
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
