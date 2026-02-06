import { NextRequest, NextResponse } from 'next/server';
import { BFF_URL } from '../../../utils/bff';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  try {
    const response = await fetch(`${BFF_URL}/api/shares/${token}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error resolving share link:', error);
    return NextResponse.json({ error: 'Failed to resolve share link' }, { status: 500 });
  }
}
