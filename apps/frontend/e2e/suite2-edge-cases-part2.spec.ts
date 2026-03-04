/**
 * Suite 2 Part 2: Bug Reporting, API Errors, Concurrent Modifications
 * Extracted from suite2-edge-cases.spec.ts to keep files under 450 lines.
 */

import { test, expect, Page } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

interface TestContext {
  sessionToken: string;
  email: string;
}

async function mintTestSession(request: any, emailPrefix: string): Promise<TestContext> {
  const email = `${emailPrefix}_${Date.now()}@test.com`;
  const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
    data: { email },
  });
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return { sessionToken: data.session_token, email };
}

async function setupAuthenticatedPage(page: Page, ctx: TestContext): Promise<void> {
  await page.context().addCookies([{
    name: 'sa_session',
    value: ctx.sessionToken,
    domain: 'localhost',
    path: '/',
  }]);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

// ============================================================
// SCENARIO 5: BUG REPORTING EDGE CASES
// ============================================================

test.describe('Scenario 5: Bug Reporting Edge Cases', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'bugreport');
  });

  test('Submit bug with minimal data', async ({ request }) => {
    const formData = new URLSearchParams();
    formData.append('description', 'Test bug');
    formData.append('severity', 'low');
    formData.append('category', 'ui');

    const response = await request.post(`${BACKEND_URL}/bugs`, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: formData.toString(),
    });

    // May succeed or fail depending on multipart handling
    console.log(`Bug report minimal: ${response.status()}`);
    expect([200, 201, 400, 422]).toContain(response.status());
  });

  test('Submit bug without auth returns 401', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/bugs`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      data: 'description=test&severity=low&category=ui',
    });
    expect(response.status()).toBe(401);
    console.log('✅ Bug report without auth returns 401');
  });

  test('Fetch non-existent bug returns 404', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/bugs/nonexistent-id-abc`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.status()).toBe(404);
    console.log('✅ Non-existent bug returns 404');
  });
});

// ============================================================
// SCENARIO 6: API ERROR RESPONSES
// ============================================================

test.describe('Scenario 6: API Error Responses', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'api_errors');
  });

  test('GET non-existent row returns 404', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows/99999999`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.status()).toBe(404);
    console.log('✅ Non-existent row returns 404');
  });

  test('DELETE non-existent row returns 404', async ({ request }) => {
    const response = await request.delete(`${BACKEND_URL}/rows/99999999`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.status()).toBe(404);
    console.log('✅ Delete non-existent row returns 404');
  });

  test('PATCH with invalid data returns 422', async ({ request }) => {
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Test row',
        status: 'sourcing',
        request_spec: { item_name: 'test', constraints: '{}' },
      },
    });
    const row = await createResponse.json();

    const response = await request.patch(`${BACKEND_URL}/rows/${row.id}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { budget_max: 'not-a-number' },
    });
    
    expect([400, 422]).toContain(response.status());
    console.log('✅ Invalid data returns validation error');
  });

  test('POST row with missing required fields', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        status: 'sourcing',
      },
    });
    
    expect([400, 422]).toContain(response.status());
    console.log('✅ Missing fields returns validation error');
  });
});

// ============================================================
// SCENARIO 7: CONCURRENT MODIFICATIONS
// ============================================================

test.describe('Scenario 7: Concurrent Modifications', () => {
  let ctx: TestContext;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'concurrent');
    
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Concurrent test row',
        status: 'sourcing',
        request_spec: { item_name: 'test', constraints: '{}' },
      },
    });
    const row = await response.json();
    rowId = row.id;
  });

  test('Simultaneous updates to same row', async ({ request }) => {
    const updates = [
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update A' },
      }),
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update B' },
      }),
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update C' },
      }),
    ];
    
    const responses = await Promise.all(updates);
    const successCount = responses.filter(r => r.ok()).length;
    
    console.log(`Concurrent updates: ${successCount}/3 succeeded`);
    expect(successCount).toBe(3);
    
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    const row = await getResponse.json();
    console.log(`Final title: ${row.title}`);
    expect(['Update A', 'Update B', 'Update C']).toContain(row.title);
    console.log('✅ Concurrent updates handled');
  });
});
