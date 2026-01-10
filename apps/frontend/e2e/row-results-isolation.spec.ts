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
    await page.waitForLoadState('networkidle');

    // Both rows should be visible in sidebar
    await expect(page.locator('text=Montana State shirts')).toBeVisible();
    await expect(page.locator('text=Blue hoodies under $50')).toBeVisible();

    // Click first row
    await page.locator('text=Montana State shirts').first().click();
    await page.waitForTimeout(500);

    // The product panel should show the row title
    const panelTitle = page.locator('h1');
    await expect(panelTitle).toContainText('Montana State shirts');

    // Click second row
    await page.locator('text=Blue hoodies under $50').first().click();
    await page.waitForTimeout(500);

    // Panel should now show second row's title
    await expect(panelTitle).toContainText('Blue hoodies under $50');
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
    await expect(page.locator('text=Montana State shirts')).toBeVisible();
    await expect(page.locator('text=Blue hoodies under $50')).toBeVisible();

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Rows should still be there
    await expect(page.locator('text=Montana State shirts')).toBeVisible();
    await expect(page.locator('text=Blue hoodies under $50')).toBeVisible();
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
    await expect(page.locator('text=Montana State shirts')).toBeVisible();
    await expect(page.locator('text=Blue hoodies under $50')).toBeVisible();

    // Find and click delete button on first row
    const firstRowCard = page.locator('text=Montana State shirts').first().locator('..');
    const deleteButton = firstRowCard.locator('button').first();
    await deleteButton.click();

    // Wait for deletion
    await page.waitForTimeout(500);

    // First row should be gone, second should remain
    await expect(page.locator('text=Montana State shirts')).not.toBeVisible();
    await expect(page.locator('text=Blue hoodies under $50')).toBeVisible();
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
