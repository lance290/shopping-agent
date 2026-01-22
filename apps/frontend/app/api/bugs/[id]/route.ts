import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export const dynamic = 'force-dynamic';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

async function getAuthHeader(): Promise<{ Authorization?: string }> {
  const { getToken } = await auth();
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const authHeader = await getAuthHeader();
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { id } = await params;
    
    if (!id) {
        return NextResponse.json({ error: 'Missing bug ID' }, { status: 400 });
    }

    const response = await fetch(`${BFF_URL}/api/bugs/${id}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
    });
    
    if (!response.ok) {
        if (response.status === 404) {
            return NextResponse.json({ error: 'Bug report not found' }, { status: 404 });
        }
        return NextResponse.json(
            { error: `BFF failed with ${response.status}` }, 
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Error fetching bug report:', error);
    return NextResponse.json({ error: 'Failed to fetch bug report' }, { status: 500 });
  }
}
