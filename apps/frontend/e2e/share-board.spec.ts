import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('Share Board Feature', () => {
  test.setTimeout(60000);
  const email = `share_board_${Date.now()}@test.com`;
  let sessionToken: string;

  test.beforeEach(async ({ page, request }) => {
    // Mint session via backend test endpoint
    const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
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

  test('Share Board button copies URL with multiple query params', async ({ page, context }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find the chat input
    const chatInput = page.locator('input[placeholder="What are you looking for?"]');
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Create multiple searches
    const searches = ['Nike shoes', 'Adidas sneakers', 'Running gear'];
    for (const search of searches) {
      await chatInput.fill(search);
      await chatInput.press('Enter');
      await page.waitForTimeout(1000); // Wait between searches
    }

    // Wait for rows to appear
    await page.waitForSelector('[data-testid="row-strip"]', { timeout: 15000 });

    // Find the Share Board button
    const shareBoardButton = page.locator('button:has-text("Share Board")').first();
    await expect(shareBoardButton).toBeVisible({ timeout: 5000 });

    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Click the Share Board button
    await shareBoardButton.click();

    // Wait for success toast
    await expect(page.locator('text=Board link copied!')).toBeVisible({ timeout: 5000 });

    // Verify clipboard contains the correct URL with multiple queries
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());

    // Should contain multiple q= parameters
    const qCount = (clipboardText.match(/q=/g) || []).length;
    expect(qCount).toBe(searches.length);

    // Each search should be in the URL
    for (const search of searches) {
      expect(clipboardText).toContain(encodeURIComponent(search));
    }
  });

  test('Shared board link creates multiple rows', async ({ page }) => {
    const searches = ['Test search 1', 'Test search 2', 'Test search 3'];

    // Build URL with multiple query parameters
    const params = searches.map(s => `q=${encodeURIComponent(s)}`).join('&');
    await page.goto(`/?${params}`);
    await page.waitForLoadState('networkidle');

    // Wait for rows to be created
    await page.waitForSelector('[data-testid="row-strip"]', { timeout: 15000 });

    // Count the number of rows created
    const rowCount = await page.locator('[data-testid="row-strip"]').count();
    expect(rowCount).toBe(searches.length);

    // Verify each search title appears
    for (const search of searches) {
      const rowTitle = page.locator(`h3.text-base.font-semibold:has-text("${search}")`);
      await expect(rowTitle).toBeVisible({ timeout: 10000 });
    }
  });

  test('Share Board button shows error when no requests exist', async ({ page, context }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find the Share Board button
    const shareBoardButton = page.locator('button:has-text("Share Board")').first();
    await expect(shareBoardButton).toBeVisible({ timeout: 10000 });

    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Click the Share Board button when board is empty
    await shareBoardButton.click();

    // Wait for error toast
    await expect(page.locator('text=No requests to share')).toBeVisible({ timeout: 5000 });
  });
});
