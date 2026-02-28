import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../utils/api-proxy';

export async function POST(request: NextRequest) {
  const auth = getAuthHeader(request);

  if (!auth) {
    return NextResponse.json(
      { error: 'Authentication required to scan receipts' },
      { status: 401 },
    );
  }

  const body = await request.json();

  try {
    const response = await fetch(`${BACKEND_URL}/bob/receipt/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: auth,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      return NextResponse.json(
        { error: text || 'Receipt scan failed' },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: 'Failed to process receipt' },
      { status: 500 },
    );
  }
}
