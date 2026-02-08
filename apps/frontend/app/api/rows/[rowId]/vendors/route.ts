import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ rowId: string }> }
) {
  try {
    const { rowId } = await params;
    const body = await request.json();

    const res = await fetch(`${BACKEND_URL}/outreach/rows/${rowId}/vendors`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(request.headers.get('authorization')
          ? { Authorization: request.headers.get('authorization')! }
          : {}),
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Persist vendors error:', error);
    return NextResponse.json(
      { detail: 'Failed to persist vendors' },
      { status: 500 }
    );
  }
}
