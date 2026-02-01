import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Trigger outreach
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  try {
    const { rowId } = await params;
    const body = await request.json();
    
    const res = await fetch(`${BACKEND_URL}/outreach/rows/${rowId}/trigger`, {
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
    console.error('Outreach trigger error:', error);
    return NextResponse.json(
      { detail: 'Failed to trigger outreach' },
      { status: 500 }
    );
  }
}

// Get outreach status
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  try {
    const { rowId } = await params;
    
    const res = await fetch(`${BACKEND_URL}/outreach/rows/${rowId}/status`, {
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
    console.error('Outreach status error:', error);
    return NextResponse.json(
      { detail: 'Failed to get outreach status' },
      { status: 500 }
    );
  }
}
