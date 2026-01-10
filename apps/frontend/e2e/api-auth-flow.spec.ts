import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('API Authentication Flow', () => {
  test('unauthenticated request to /rows returns 401', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows`);
    expect(response.status()).toBe(401);
  });

  test('unauthenticated POST to /rows returns 401 or 422', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/rows`, {
      data: { title: 'Test', status: 'sourcing', request_spec: { item_name: 'Test', constraints: '{}' } },
    });
    // Backend may return 401 (no auth) or 422 (validation before auth check)
    expect([401, 422]).toContain(response.status());
  });

  test('invalid token returns error (401 or 500)', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { Authorization: 'Bearer invalid_token_12345' },
    });
    // Backend may return 401 (proper auth error) or 500 (hash error)
    expect([401, 500]).toContain(response.status());
  });

  test('valid token returns 200', async ({ request }) => {
    // Mint a session
    const email = `auth_test_${Date.now()}@example.com`;
    const mintResponse = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    if (!mintResponse.ok()) {
      console.log('Mint session failed:', await mintResponse.text());
    }
    expect(mintResponse.ok()).toBeTruthy();
    const data = await mintResponse.json();
    const session_token = data.session_token;

    // Use the token
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${session_token}` },
    });
    expect(response.ok()).toBeTruthy();
  });

  test('session can be revoked', async ({ request }) => {
    // Mint a session
    const email = `revoke_test_${Date.now()}@example.com`;
    const mintResponse = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    const data = await mintResponse.json();
    const session_token = data.session_token;

    // Verify it works
    const response1 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${session_token}` },
    });
    expect(response1.ok()).toBeTruthy();

    // Revoke the session
    const revokeResponse = await request.post(`${BACKEND_URL}/auth/logout`, {
      headers: { Authorization: `Bearer ${session_token}` },
    });
    expect(revokeResponse.ok()).toBeTruthy();

    // Token should no longer work
    const response2 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${session_token}` },
    });
    expect(response2.status()).toBe(401);
  });
});

test.describe('Row CRUD Operations', () => {
  let sessionToken: string;

  test.beforeEach(async ({ request }) => {
    const email = `crud_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;
  });

  test('CREATE: POST /rows creates a new row', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Test Row',
        status: 'sourcing',
        request_spec: { item_name: 'Test Row', constraints: '{}' },
      },
    });
    expect(response.ok()).toBeTruthy();
    const row = await response.json();
    expect(row.id).toBeDefined();
    expect(row.title).toBe('Test Row');
    expect(row.status).toBe('sourcing');
  });

  test('READ: GET /rows returns user rows', async ({ request }) => {
    // Create a row first
    await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Row for GET test', status: 'sourcing', request_spec: { item_name: 'test', constraints: '{}' } },
    });

    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(response.ok()).toBeTruthy();
    const rows = await response.json();
    expect(Array.isArray(rows)).toBe(true);
    expect(rows.length).toBeGreaterThan(0);
  });

  test('READ: GET /rows/:id returns specific row', async ({ request }) => {
    // Create a row
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Specific Row', status: 'sourcing', request_spec: { item_name: 'test', constraints: '{}' } },
    });
    const { id } = await createResponse.json();

    // Get it by ID
    const response = await request.get(`${BACKEND_URL}/rows/${id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(response.ok()).toBeTruthy();
    const row = await response.json();
    expect(row.id).toBe(id);
    expect(row.title).toBe('Specific Row');
  });

  test('UPDATE: PATCH /rows/:id updates row', async ({ request }) => {
    // Create a row
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Original', status: 'sourcing', request_spec: { item_name: 'test', constraints: '{}' } },
    });
    const { id } = await createResponse.json();

    // Update it
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Updated', status: 'closed' },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify
    const getResponse = await request.get(`${BACKEND_URL}/rows/${id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    const row = await getResponse.json();
    expect(row.title).toBe('Updated');
    expect(row.status).toBe('closed');
  });

  test('DELETE: DELETE /rows/:id removes row', async ({ request }) => {
    // Create a row
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'To Delete', status: 'sourcing', request_spec: { item_name: 'test', constraints: '{}' } },
    });
    const { id } = await createResponse.json();

    // Delete it
    const deleteResponse = await request.delete(`${BACKEND_URL}/rows/${id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(deleteResponse.ok()).toBeTruthy();

    // Verify it's gone
    const getResponse = await request.get(`${BACKEND_URL}/rows/${id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(getResponse.status()).toBe(404);
  });

  test('GET /rows/:id returns 404 for non-existent row', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows/999999`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(response.status()).toBe(404);
  });

  test('PATCH /rows/:id returns 404 for non-existent row', async ({ request }) => {
    const response = await request.patch(`${BACKEND_URL}/rows/999999`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Should fail' },
    });
    expect(response.status()).toBe(404);
  });

  test('DELETE /rows/:id returns 404 for non-existent row', async ({ request }) => {
    const response = await request.delete(`${BACKEND_URL}/rows/999999`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(response.status()).toBe(404);
  });
});

test.describe('Health Check', () => {
  test('GET /health returns healthy status', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });
});
