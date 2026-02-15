import { NextRequest } from 'next/server';
import { proxyGet } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  return proxyGet(request, '/stripe-connect/earnings');
}
