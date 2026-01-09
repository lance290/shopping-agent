import { NextRequest, NextResponse } from 'next/server';

const BFF_URL = process.env.BFF_URL || 'http://localhost:8080';

export async function GET() {
  try {
    const response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error fetching rows:', error);
    return NextResponse.json([], { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BFF_URL}/api/rows`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error creating row:', error);
    return NextResponse.json({ error: 'Failed to create row' }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    
    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    const response = await fetch(`${BFF_URL}/api/rows/${id}`, {
      method: 'DELETE',
    });
    
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error deleting row:', error);
    return NextResponse.json({ error: 'Failed to delete row' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const url = new URL(request.url);
    const id = url.searchParams.get('id');
    const body = await request.json();
    
    console.log(`[API] PATCH /api/rows?id=${id}`, body);

    if (!id) {
      return NextResponse.json({ error: 'Missing row ID' }, { status: 400 });
    }
    
    const bffUrl = `${BFF_URL}/api/rows/${id}`;
    console.log(`[API] Forwarding to BFF: ${bffUrl}`);

    const response = await fetch(bffUrl, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      console.error(`[API] BFF returned ${response.status} ${response.statusText}`);
      const text = await response.text();
      console.error(`[API] BFF response body: ${text}`);
      return NextResponse.json({ error: 'BFF failed' }, { status: response.status });
    }

    const data = await response.json();
    console.log(`[API] BFF success:`, data);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Error updating row:', error);
    return NextResponse.json({ error: 'Failed to update row' }, { status: 500 });
  }
}
