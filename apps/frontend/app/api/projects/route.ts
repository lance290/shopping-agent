import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export const dynamic = 'force-dynamic';

function normalizeBaseUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  return `http://${trimmed}`;
}

const BFF_URL = normalizeBaseUrl(
  process.env.NEXT_PUBLIC_BFF_URL || process.env.BFF_URL || 'http://127.0.0.1:8080'
);
const disableClerk = process.env.NEXT_PUBLIC_DISABLE_CLERK === '1';

function getDevSessionToken(): string | undefined {
  return process.env.DEV_SESSION_TOKEN || process.env.NEXT_PUBLIC_DEV_SESSION_TOKEN;
}

function getCookieSessionToken(request: NextRequest): string | undefined {
  return request.cookies.get('sa_session')?.value;
}

function isClerkConfigured(): boolean {
  return Boolean(process.env.CLERK_SECRET_KEY);
}

async function getAuthHeader(request: NextRequest): Promise<{ Authorization?: string }> {
  if (disableClerk || !isClerkConfigured()) {
    const token = getCookieSessionToken(request) || getDevSessionToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  const { getToken } = await auth();
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function GET(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BFF_URL}/api/projects`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching projects:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    console.log(`[API] Creating project with title: ${body.title} via BFF: ${BFF_URL}`);
    
    const response = await fetch(`${BFF_URL}/api/projects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader,
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const text = await response.text();
      console.error(`[API] BFF project creation failed: ${response.status}`, text);
      return NextResponse.json({ error: 'BFF failed' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating project:', error);
    return NextResponse.json({ error: 'Failed to create project' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const authHeader = await getAuthHeader(request);
    if (!authHeader['Authorization']) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Missing project ID' }, { status: 400 });
    }
    
    const response = await fetch(`${BFF_URL}/api/projects/${id}`, {
      method: 'DELETE',
      headers: {
        ...authHeader,
      }
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error deleting project:', error);
    return NextResponse.json({ error: 'Failed to delete project' }, { status: 500 });
  }
}
