import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('Per-Row Results Isolation', () => {
  let sessionToken: string;
  let row1Id: number;
  let row2Id: number;

  test.beforeEach(async ({ request }) => {
    // Mint a fresh session
    const email = `isolation_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Create two rows with different titles
    const row1Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Montana State shirts',
        status: 'sourcing',
        request_spec: { item_name: 'Montana State shirts', constraints: '{}' },
      },
    });
    expect(row1Response.ok()).toBeTruthy();
    const row1 = await row1Response.json();
    row1Id = row1.id;

    const row2Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue hoodies under $50',
        status: 'sourcing',
        request_spec: { item_name: 'Blue hoodies', constraints: '{"max_price":"50"}' },
      },
    });
    expect(row2Response.ok()).toBeTruthy();
    const row2 = await row2Response.json();
    row2Id = row2.id;
  });

  test('clicking different cards shows different results', async ({ page }) => {
    // Set auth cookie
    await page.context().addCookies([{
      name: 'sa_session',
      value: sessionToken,
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Wait until the board has fetched rows
    await page.waitForResponse(
      (r) => r.url().includes('/api/rows') && r.request().method() === 'GET' && r.status() === 200,
      { timeout: 15000 }
    );

    // Wait until rows are rendered
    const row1Heading = page.getByRole('heading', { name: 'Montana State shirts' }).first();
    const row2Heading = page.getByRole('heading', { name: 'Blue hoodies under $50' }).first();
    await expect(row1Heading).toBeVisible({ timeout: 15000 });
    await expect(row2Heading).toBeVisible({ timeout: 15000 });

    // Click first row
    await row1Heading.click();
    await expect(page.getByText('Focused on: Montana State shirts')).toBeVisible({ timeout: 10000 });

    // Click second row
    await row2Heading.click();
    await expect(page.getByText('Focused on: Blue hoodies under $50')).toBeVisible({ timeout: 10000 });
  });

  test('row titles persist after page reload', async ({ page }) => {
    await page.context().addCookies([{
      name: 'sa_session',
      value: sessionToken,
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Verify rows exist
    const row1Heading = page.getByRole('heading', { name: 'Montana State shirts' }).first();
    const row2Heading = page.getByRole('heading', { name: 'Blue hoodies under $50' }).first();
    await expect(row1Heading).toBeVisible({ timeout: 15000 });
    await expect(row2Heading).toBeVisible({ timeout: 15000 });

    // Reload page
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    await page.waitForResponse(
      (r) => r.url().includes('/api/rows') && r.request().method() === 'GET' && r.status() === 200,
      { timeout: 15000 }
    );

    // Rows should still be there
    await expect(page.getByRole('heading', { name: 'Montana State shirts' }).first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Blue hoodies under $50' }).first()).toBeVisible({ timeout: 15000 });
  });

  test('deleting a row removes it from sidebar', async ({ page }) => {
    await page.context().addCookies([{
      name: 'sa_session',
      value: sessionToken,
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Both rows visible
    const row1Heading = page.getByRole('heading', { name: 'Montana State shirts' }).first();
    const row2Heading = page.getByRole('heading', { name: 'Blue hoodies under $50' }).first();
    await expect(row1Heading).toBeVisible({ timeout: 15000 });
    await expect(row2Heading).toBeVisible({ timeout: 15000 });

    // Archive the first row via the archive icon button
    const firstRowCard = row1Heading.locator('..').locator('..');
    const archiveButton = firstRowCard.locator('button[title="Archive row"]');
    await archiveButton.click();

    // UI supports undo; row is removed after the undo window elapses
    await page.waitForTimeout(8000);

    // First row should be gone, second should remain
    await expect(page.getByRole('heading', { name: 'Montana State shirts' })).toHaveCount(0, { timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Blue hoodies under $50' }).first()).toBeVisible({ timeout: 15000 });
  });
});

test.describe('Row Update via API', () => {
  let sessionToken: string;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    const email = `update_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Create a row
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Original title',
        status: 'sourcing',
        request_spec: { item_name: 'Original title', constraints: '{}' },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();
    rowId = row.id;
  });

  test('PATCH /rows/:id updates title', async ({ request }) => {
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Updated title with constraints' },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify update
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(getResponse.ok()).toBeTruthy();
    const row = await getResponse.json();
    expect(row.title).toBe('Updated title with constraints');
  });

  test('PATCH /rows/:id updates request_spec', async ({ request }) => {
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue shirts under $50',
        request_spec: {
          item_name: 'Blue shirts',
          constraints: '{"color":"blue","max_price":"50"}',
        },
      },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify update
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(getResponse.ok()).toBeTruthy();
    const row = await getResponse.json();
    expect(row.title).toBe('Blue shirts under $50');
  });

  test('PATCH /rows/:id fails for wrong user', async ({ request }) => {
    // Create another user
    const email2 = `other_${Date.now()}@example.com`;
    const response2 = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email: email2 },
    });
    const data2 = await response2.json();
    const otherToken = data2.session_token;

    // Try to update with wrong user's token
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${otherToken}` },
      data: { title: 'Hacked title' },
    });
    expect(updateResponse.status()).toBe(404); // Row not found for this user
  });
});

test.describe('Row Search Endpoint', () => {
  let sessionToken: string;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    const email = `search_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Create a row with constraints
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue Montana shirts under $50',
        status: 'sourcing',
        request_spec: {
          item_name: 'Montana shirts',
          constraints: '{"color":"blue","max_price":"50"}',
        },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();
    rowId = row.id;
  });

  test('POST /rows/:id/search returns results', async ({ request }) => {
    const searchResponse = await request.post(`${BACKEND_URL}/rows/${rowId}/search`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { query: 'Montana shirts' },
    });
    expect(searchResponse.ok()).toBeTruthy();
    const data = await searchResponse.json();
    expect(data).toHaveProperty('results');
    expect(Array.isArray(data.results)).toBe(true);
  });

  test('POST /rows/:id/search fails for wrong user', async ({ request }) => {
    // Create another user
    const email2 = `other_search_${Date.now()}@example.com`;
    const response2 = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email: email2 },
    });
    const data2 = await response2.json();
    const otherToken = data2.session_token;

    // Try to search with wrong user's token
    const searchResponse = await request.post(`${BACKEND_URL}/rows/${rowId}/search`, {
      headers: { Authorization: `Bearer ${otherToken}` },
      data: { query: 'Montana shirts' },
    });
    expect(searchResponse.status()).toBe(404); // Row not found for this user
  });

  test('POST /rows/:id/search fails without auth', async ({ request }) => {
    const searchResponse = await request.post(`${BACKEND_URL}/rows/${rowId}/search`, {
      data: { query: 'Montana shirts' },
    });
    expect(searchResponse.status()).toBe(401);
  });
});
