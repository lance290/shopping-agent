import { NextRequest } from 'next/server';
import { proxyPost } from '../../../utils/api-proxy';

// Create a new outreach campaign
export async function POST(request: NextRequest) {
  return proxyPost(request, '/outreach/campaigns');
}
