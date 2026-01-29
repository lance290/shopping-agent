import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('Copy Search Link Feature', () => {
  test.setTimeout(60000);
  const email = `copy_link_${Date.now()}@test.com`;
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

  test('Copy search link button is visible and copies URL with query param', async ({ page, context }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find the chat input
    const chatInput = page.locator('input[placeholder="What are you looking for?"]');
    await expect(chatInput).toBeVisible({ timeout: 10000 });

    // Create a search
    const searchQuery = 'Nike running shoes';
    await chatInput.fill(searchQuery);
    await chatInput.press('Enter');

    // Wait for the row to appear
    await page.waitForSelector('[data-testid="row-strip"]', { timeout: 15000 });

    // Find the copy link button (Link2 icon button with title "Copy search link")
    const copyLinkButton = page.locator('button[title="Copy search link"]').first();
    await expect(copyLinkButton).toBeVisible({ timeout: 5000 });

    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    // Click the copy link button
    await copyLinkButton.click();

    // Wait for success toast
    await expect(page.locator('text=Search link copied to clipboard.')).toBeVisible({ timeout: 5000 });

    // Verify clipboard contains the correct URL
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toContain('?q=');
    expect(clipboardText).toContain(encodeURIComponent(searchQuery));
  });

  test('Shared search link creates row and runs search', async ({ page }) => {
    const sharedQuery = 'Adidas sneakers test';
    const encodedQuery = encodeURIComponent(sharedQuery);

    // Navigate with query parameter
    await page.goto(`/?q=${encodedQuery}`);
    await page.waitForLoadState('networkidle');

    // Wait for the row to be created and search to run
    await page.waitForSelector('[data-testid="row-strip"]', { timeout: 15000 });

    // Verify the row title matches the shared query
    const rowTitle = page.locator('h3.text-base.font-semibold').first();
    await expect(rowTitle).toHaveText(sharedQuery, { timeout: 10000 });

    // Verify search is running or has completed (check for offers or loading state)
    const hasOffers = await page.locator('[data-testid="offer-tile"]').count() > 0;
    const isLoading = await page.locator('text=Sourcing offers...').isVisible();

    expect(hasOffers || isLoading).toBeTruthy();
  });
});
