import { test, expect } from '@playwright/test';

test.describe('Row Persistence Regression', () => {
  // Use a unique email for isolation
  const email = `regression_${Date.now()}@example.com`;
  let sessionToken: string;

  test.beforeEach(async ({ page, request }) => {
    // Mint session via backend test endpoint
    const response = await request.post('http://localhost:8000/test/mint-session', {
      data: { email },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    sessionToken = data.session_token;

    // Set cookie
    await page.context().addCookies([{
      name: 'sa_session',
      value: sessionToken,
      domain: 'localhost',
      path: '/',
    }]);
  });

  test('should persist row title after creation via API', async ({ page, request }) => {
    const query = 'Regression Test Item ' + Date.now();
    
    // Create row directly via API (bypassing LLM which may not be available in tests)
    const createResponse = await request.post('http://localhost:8000/rows', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`,
      },
      data: {
        title: query,
        status: 'sourcing',
        request_spec: {
          item_name: query,
          constraints: '{}',
        },
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const createdRow = await createResponse.json();
    expect(createdRow.title).toBe(query);
    expect(createdRow.id).toBeDefined();

    // Now load the page and verify the row appears
    await page.goto('/');
    await expect(page.getByRole('heading', { name: query }).first()).toBeVisible({ timeout: 10000 });

    // Reload page to verify persistence
    await page.reload();
    await expect(page.getByRole('heading', { name: query }).first()).toBeVisible({ timeout: 10000 });
  });

  test('should allow logging out', async ({ page }) => {
    await page.goto('/');
    
    // Ensure logout button is visible (it's at the bottom of sidebar)
    await expect(page.getByText('Sign Out')).toBeVisible();
    
    // Click logout
    await page.getByText('Sign Out').click();
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('service vendor tiles persist after reload', async ({ page, request }) => {
    const query = `Private Jet Charter ${Date.now()}`;

    const createResponse = await request.post('http://localhost:8000/rows', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`,
      },
      data: {
        title: query,
        status: 'sourcing',
        is_service: true,
        service_category: 'private_aviation',
        request_spec: {
          item_name: query,
          constraints: '{}',
        },
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const createdRow = await createResponse.json();
    const rowId = createdRow.id;

    const vendorPayload = {
      category: 'private_aviation',
      vendors: [
        {
          title: 'JetRight E2E',
          vendor_company: 'JetRight E2E',
          vendor_name: 'Alexis',
          vendor_email: 'team@jetright-e2e.com',
          contact_phone: '+16505550199',
          source: 'wattdata',
        },
      ],
    };

    const persistResponse = await request.post(`http://localhost:8000/outreach/rows/${rowId}/vendors`, {
      data: vendorPayload,
    });
    expect(persistResponse.ok()).toBeTruthy();

    await page.goto('/');
    await expect(page.getByText('JetRight E2E').first()).toBeVisible({ timeout: 10000 });

    await page.reload();
    await expect(page.getByText('JetRight E2E').first()).toBeVisible({ timeout: 10000 });
  });
});
