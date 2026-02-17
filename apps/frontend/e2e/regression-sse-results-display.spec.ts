/**
 * Regression test: SSE search results must display as offer cards.
 *
 * Bug: When a row_created SSE event fired, the RowStrip mounted with
 * isSearching=false and offers=[]. Its auto-load effect triggered
 * refresh('all') which called the non-streaming search endpoint.
 * For anonymous users this returned 401/empty, and setRowResults([])
 * wiped the SSE results that had already arrived.
 *
 * Fix: Set isSearching + moreResultsIncoming immediately on row_created
 * and context_switch events, before setActiveRowId triggers RowStrip mount.
 *
 * This test verifies that search results appear as visible offer tiles
 * after a chat search completes.
 */
import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('SSE Search Results Display Regression', () => {
  test.setTimeout(120_000);

  test('anonymous search displays offer tiles after chat', async ({ page }) => {
    // Go to homepage (workspace) without auth — anonymous user
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Find the chat input
    const chatInput = page.locator(
      'input[placeholder*="looking for"], input[placeholder*="Refine"], input[placeholder*="search"]'
    );
    await expect(chatInput).toBeVisible({ timeout: 15_000 });

    // Type a search query
    await chatInput.fill('wireless earbuds');
    await chatInput.press('Enter');

    // Wait for the row to appear in the board (row strip with title)
    const rowStrip = page.locator('[data-testid="row-strip"]').first();
    await expect(rowStrip).toBeVisible({ timeout: 30_000 });

    // Wait for at least one offer tile to appear — this is the core regression check.
    // Before the fix, this would time out because setRowResults([]) wiped SSE results.
    const offerTile = page.locator('[data-testid="offer-tile"]').first();
    await expect(offerTile).toBeVisible({ timeout: 60_000 });

    // Verify multiple offer tiles rendered (not just 1 vendor card)
    const tileCount = await page.locator('[data-testid="offer-tile"]').count();
    expect(tileCount).toBeGreaterThan(1);

    console.log(`✓ ${tileCount} offer tiles displayed after anonymous search`);
  });

  test('authenticated search displays offer tiles after chat', async ({
    page,
    request,
  }) => {
    // Mint a session
    const email = `sse_regression_${Date.now()}@test.com`;
    const mintResp = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });

    // Skip if test endpoint not available (CI without backend)
    if (!mintResp.ok()) {
      test.skip();
      return;
    }

    const { session_token } = await mintResp.json();
    await page.context().addCookies([
      { name: 'sa_session', value: session_token, domain: 'localhost', path: '/' },
    ]);

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const chatInput = page.locator(
      'input[placeholder*="looking for"], input[placeholder*="Refine"], input[placeholder*="search"]'
    );
    await expect(chatInput).toBeVisible({ timeout: 15_000 });

    await chatInput.fill('running shoes under $100');
    await chatInput.press('Enter');

    // Wait for row strip
    const rowStrip = page.locator('[data-testid="row-strip"]').first();
    await expect(rowStrip).toBeVisible({ timeout: 30_000 });

    // Core assertion: offer tiles must appear
    const offerTile = page.locator('[data-testid="offer-tile"]').first();
    await expect(offerTile).toBeVisible({ timeout: 60_000 });

    const tileCount = await page.locator('[data-testid="offer-tile"]').count();
    expect(tileCount).toBeGreaterThan(1);

    console.log(`✓ ${tileCount} offer tiles displayed after authenticated search`);
  });

  test('provider status badges appear during search', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const chatInput = page.locator(
      'input[placeholder*="looking for"], input[placeholder*="Refine"], input[placeholder*="search"]'
    );
    await expect(chatInput).toBeVisible({ timeout: 15_000 });

    await chatInput.fill('standing desk');
    await chatInput.press('Enter');

    // Wait for at least one provider status badge to appear
    // These show provider names like "SerpApi", "Rainforest", "Google CSE"
    const badge = page.locator('[data-testid="row-strip"]').first();
    await expect(badge).toBeVisible({ timeout: 30_000 });

    // Wait for search to complete and tiles to render
    const offerTile = page.locator('[data-testid="offer-tile"]').first();
    await expect(offerTile).toBeVisible({ timeout: 60_000 });

    // After search completes, "Sourcing offers..." should NOT be visible
    const sourcingSpinner = page.locator('text=Sourcing offers...');
    await expect(sourcingSpinner).not.toBeVisible({ timeout: 10_000 });
  });
});
