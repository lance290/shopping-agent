import { NextRequest, NextResponse } from 'next/server';
import { BACKEND_URL, getAuthHeader } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const auth = getAuthHeader(request);

  if (!auth) {
    return NextResponse.json(
      { balance_cents: 0, transactions: [] },
      { status: 200 },
    );
  }

  const headers: Record<string, string> = { Authorization: auth };

  try {
    const response = await fetch(`${BACKEND_URL}/pop/wallet`, { headers });
    if (!response.ok) {
      return NextResponse.json({ balance_cents: 0, transactions: [] });
    }
    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ balance_cents: 0, transactions: [] });
  }
}
