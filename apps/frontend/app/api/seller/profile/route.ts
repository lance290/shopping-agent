import { NextRequest } from 'next/server';
import { proxyGet, proxyPatch } from '../../../utils/api-proxy';

export async function GET(request: NextRequest) {
  return proxyGet(request, '/seller/profile');
}

export async function PATCH(request: NextRequest) {
  return proxyPatch(request, '/seller/profile');
}
