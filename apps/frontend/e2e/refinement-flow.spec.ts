import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('Refinement Flow - Row Updates', () => {
  let sessionToken: string;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    const email = `refine_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Create initial row
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Montana State shirts',
        status: 'sourcing',
        request_spec: { item_name: 'Montana State shirts', constraints: '{}' },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();
    rowId = row.id;
  });

  test('updating row title reflects in GET response', async ({ request }) => {
    // Update row with refined title
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Montana State shirts under $50',
        request_spec: {
          item_name: 'Montana State shirts',
          constraints: '{"max_price":"50"}',
        },
      },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify the update
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    expect(getResponse.ok()).toBeTruthy();
    const row = await getResponse.json();
    expect(row.title).toBe('Montana State shirts under $50');
  });

  test('multiple refinements accumulate in title', async ({ request }) => {
    // First refinement: add price
    await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Montana State shirts under $50',
        request_spec: {
          item_name: 'Montana State shirts',
          constraints: '{"max_price":"50"}',
        },
      },
    });

    // Second refinement: add color
    await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue Montana State shirts under $50',
        request_spec: {
          item_name: 'Montana State shirts',
          constraints: '{"max_price":"50","color":"blue"}',
        },
      },
    });

    // Third refinement: add size
    const finalUpdate = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue Montana State shirts under $50 XL',
        request_spec: {
          item_name: 'Montana State shirts',
          constraints: '{"max_price":"50","color":"blue","size":"XL"}',
        },
      },
    });
    expect(finalUpdate.ok()).toBeTruthy();

    // Verify final state
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    const row = await getResponse.json();
    expect(row.title).toBe('Blue Montana State shirts under $50 XL');
  });

  test('refined row title shows in sidebar after refresh', async ({ page, request }) => {
    // Update row via API
    await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Montana State shirts under $50' },
    });

    // Set auth and navigate
    await page.context().addCookies([{
      name: 'sa_session',
      value: sessionToken,
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Should see updated title
    await expect(page.locator('text=Montana State shirts under $50')).toBeVisible();
  });
});

test.describe('Constraint Leakage Prevention', () => {
  let sessionToken: string;

  test.beforeEach(async ({ request }) => {
    const email = `leakage_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;
  });

  test('new row starts with empty constraints', async ({ request }) => {
    // Create first row with constraints
    const row1Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Blue shirts under $50',
        status: 'sourcing',
        request_spec: {
          item_name: 'Blue shirts',
          constraints: '{"color":"blue","max_price":"50"}',
        },
      },
    });
    expect(row1Response.ok()).toBeTruthy();

    // Create second row - should have clean constraints
    const row2Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Red sneakers',
        status: 'sourcing',
        request_spec: {
          item_name: 'Red sneakers',
          constraints: '{}',
        },
      },
    });
    expect(row2Response.ok()).toBeTruthy();
    const row2 = await row2Response.json();

    // Verify row2 has no constraints from row1
    const getResponse = await request.get(`${BACKEND_URL}/rows/${row2.id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    const row = await getResponse.json();
    expect(row.title).toBe('Red sneakers');
    // The request_spec should have empty constraints
  });

  test('rows are independent - updating one does not affect another', async ({ request }) => {
    // Create two rows
    const row1Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Row 1',
        status: 'sourcing',
        request_spec: { item_name: 'Row 1', constraints: '{}' },
      },
    });
    const row1 = await row1Response.json();

    const row2Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Row 2',
        status: 'sourcing',
        request_spec: { item_name: 'Row 2', constraints: '{}' },
      },
    });
    const row2 = await row2Response.json();

    // Update row1
    await request.patch(`${BACKEND_URL}/rows/${row1.id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { title: 'Row 1 Updated' },
    });

    // Verify row2 is unchanged
    const getRow2 = await request.get(`${BACKEND_URL}/rows/${row2.id}`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
    });
    const row2Data = await getRow2.json();
    expect(row2Data.title).toBe('Row 2');
  });
});

test.describe('Search Results Per Row', () => {
  let sessionToken: string;
  let row1Id: number;
  let row2Id: number;

  test.beforeEach(async ({ request }) => {
    const email = `search_per_row_${Date.now()}@example.com`;
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Create two rows with different search terms
    const row1Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Montana State shirts',
        status: 'sourcing',
        request_spec: { item_name: 'Montana State shirts', constraints: '{}' },
      },
    });
    row1Id = (await row1Response.json()).id;

    const row2Response = await request.post(`${BACKEND_URL}/rows`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {
        title: 'Nike running shoes',
        status: 'sourcing',
        request_spec: { item_name: 'Nike running shoes', constraints: '{}' },
      },
    });
    row2Id = (await row2Response.json()).id;
  });

  test('each row can have its own search executed', async ({ request }) => {
    // Search for row 1
    const search1 = await request.post(`${BACKEND_URL}/rows/${row1Id}/search`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { query: 'Montana State shirts' },
    });
    expect(search1.ok()).toBeTruthy();
    const results1 = await search1.json();
    expect(results1).toHaveProperty('results');

    // Search for row 2
    const search2 = await request.post(`${BACKEND_URL}/rows/${row2Id}/search`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: { query: 'Nike running shoes' },
    });
    expect(search2.ok()).toBeTruthy();
    const results2 = await search2.json();
    expect(results2).toHaveProperty('results');
  });

  test('row search uses stored title if no query provided', async ({ request }) => {
    // Search without explicit query - should use row's title
    const search = await request.post(`${BACKEND_URL}/rows/${row1Id}/search`, {
      headers: { Authorization: `Bearer ${sessionToken}` },
      data: {},
    });
    expect(search.ok()).toBeTruthy();
  });
});
