import { NextRequest, NextResponse } from 'next/server';
import { proxyGet } from '../../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  const bidIds = request.nextUrl.searchParams.get('bid_ids') || '';
  if (!bidIds) {
    return NextResponse.json({}, { status: 200 });
  }
  return proxyGet(request, `/bids/social/batch?bid_ids=${encodeURIComponent(bidIds)}`);
}
