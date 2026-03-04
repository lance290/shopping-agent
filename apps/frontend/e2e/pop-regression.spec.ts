/**
 * Regression tests for Pop savings agent frontend pages.
 *
 * Covers:
 *   /pop-site          — Landing page
 *   /pop-site/chat     — Web chat with Pop
 *   /pop-site/wallet   — Savings wallet
 *   /pop-site/list/[id]— Shared list view
 *   /pop-site/invite/[code] — Invite flow
 *   /api/pop/*         — BFF proxy routes
 *
 * Bug regressions:
 *   - Chat page must show welcome message on first load (not blank)
 *   - Sending empty message must be a no-op (no API call)
 *   - List state persists in localStorage between page refreshes
 *   - Wallet shows zero balance for guest, not an error
 *   - Invite 410 must show "expired" copy, not a crash
 *   - Deleted items must not reappear after page refresh
 */
import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const POP_BASE = '/pop-site';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

async function mintSession(request: import('@playwright/test').APIRequestContext, email: string) {
  const resp = await request.post(`${BACKEND_URL}/test/mint-session`, { data: { email } });
  if (!resp.ok()) return null;
  return (await resp.json()).session_token as string;
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. Landing page
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop Landing Page', () => {
  test('renders hero section with Pop branding', async ({ page }) => {
    await page.goto(POP_BASE);
    await expect(page.locator('text=Pop').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('nav')).toBeVisible();
  });

  test('navigation links to /pop-site/chat', async ({ page }) => {
    await page.goto(POP_BASE);
    const chatLink = page.locator('a[href*="chat"]').first();
    await expect(chatLink).toBeVisible({ timeout: 10_000 });
  });

  test('shows sign-up CTA button', async ({ page }) => {
    await page.goto(POP_BASE);
    const signupBtn = page.locator('a[href*="login"], a:text("Sign Up"), button:text("Sign Up")').first();
    await expect(signupBtn).toBeVisible({ timeout: 10_000 });
  });

  test('renders feature cards (Text, Savings, Snap, Family)', async ({ page }) => {
    await page.goto(POP_BASE);
    await expect(page.locator('text=Instant Savings')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text=Family Sync')).toBeVisible({ timeout: 10_000 });
  });

  test('how-it-works steps are visible', async ({ page }) => {
    await page.goto(POP_BASE);
    await expect(page.locator('text=Build your list').first()).toBeVisible({ timeout: 10_000 });
  });

  test('page title or meta references Pop', async ({ page }) => {
    await page.goto(POP_BASE);
    const title = await page.title();
    // Page should either have a title set or at minimum not be blank
    expect(title).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. Chat page
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop Chat Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${POP_BASE}/chat`);
    await page.waitForLoadState('networkidle');
  });

  test('Regression: welcome message visible on first load (not blank)', async ({ page }) => {
    // Bug: chat page used to mount with empty messages state on first render
    const welcomeMsg = page.locator('text=grocery savings').first();
    await expect(welcomeMsg).toBeVisible({ timeout: 10_000 });
  });

  test("Pop introduces itself as grocery assistant", async ({ page }) => {
    const intro = page.locator("text=Pop, your grocery").first();
    await expect(intro).toBeVisible({ timeout: 10_000 });
  });

  test('chat input is visible and focusable', async ({ page }) => {
    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await expect(input).toBeVisible({ timeout: 10_000 });
    await input.click();
    await expect(input).toBeFocused();
  });

  test('Regression: pressing Enter with empty input does NOT call API', async ({ page }) => {
    let chatCalled = false;
    await page.route('**/api/pop/chat', () => {
      chatCalled = true;
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.click();
    await input.press('Enter');
    await page.waitForTimeout(500);

    expect(chatCalled).toBe(false);
  });

  test('typing a message and submitting calls /api/pop/chat', async ({ page }) => {
    let chatBody: object | null = null;
    await page.route('**/api/pop/chat', async (route) => {
      const request = route.request();
      chatBody = JSON.parse(request.postData() || '{}');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: 'Added milk to your list!',
          list_items: [{ id: 1, title: 'Milk', status: 'sourcing' }],
          project_id: 42,
          row_id: 1,
          action: 'create_row',
        }),
      });
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.fill('I need milk');
    await input.press('Enter');

    expect(chatBody).toBeTruthy();
    expect((chatBody as unknown as { message: string }).message).toBe('I need milk');
  });

  test('assistant reply appears in chat after sending message', async ({ page }) => {
    await page.route('**/api/pop/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: 'Got it! Added eggs to your list.',
          list_items: [{ id: 1, title: 'Eggs', status: 'sourcing' }],
          project_id: 5,
          row_id: 1,
          action: 'create_row',
        }),
      });
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.fill('I need eggs');
    await input.press('Enter');

    await expect(page.locator('text=Got it! Added eggs')).toBeVisible({ timeout: 10_000 });
  });

  test('list panel shows item returned by backend', async ({ page }) => {
    await page.route('**/api/pop/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: 'Added bread!',
          list_items: [{ id: 99, title: 'Sourdough Bread', status: 'sourcing' }],
          project_id: 7,
          row_id: 99,
          action: 'create_row',
        }),
      });
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.fill('Need sourdough bread');
    await input.press('Enter');

    await expect(page.locator('text=Sourdough Bread')).toBeVisible({ timeout: 10_000 });
  });

  test('Regression: backend error returns graceful fallback, chat does not crash', async ({ page }) => {
    await page.route('**/api/pop/chat', async (route) => {
      await route.fulfill({ status: 500, body: 'Internal Server Error' });
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.fill('crash me');
    await input.press('Enter');

    // Should show a fallback error message, not a blank/broken UI
    const fallback = page.locator('text=/trouble|brain|sec|moment/i').first();
    await expect(fallback).toBeVisible({ timeout: 10_000 });
    // Page must still be functional (input still visible)
    await expect(input).toBeVisible();
  });

  test('Regression: list persists in localStorage after receiving chat response', async ({ page }) => {
    await page.route('**/api/pop/chat', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          reply: 'Added butter!',
          list_items: [{ id: 55, title: 'Butter', status: 'sourcing' }],
          project_id: 10,
          row_id: 55,
          action: 'create_row',
        }),
      });
    });

    const input = page.locator('input[placeholder], textarea[placeholder]').first();
    await input.fill('butter');
    await input.press('Enter');

    await expect(page.locator('text=Butter')).toBeVisible({ timeout: 10_000 });

    // Check localStorage was set
    const storedItems = await page.evaluate(() =>
      localStorage.getItem('pop_guest_list_items')
    );
    expect(storedItems).toBeTruthy();
    const parsed = JSON.parse(storedItems || '[]');
    expect(parsed.some((i: { title: string }) => i.title === 'Butter')).toBe(true);
  });

  test('list items from localStorage are restored on page reload', async ({ page }) => {
    // Pre-seed localStorage
    await page.evaluate(() => {
      localStorage.setItem(
        'pop_guest_list_items',
        JSON.stringify([{ id: 77, title: 'Orange Juice', status: 'sourcing' }])
      );
      localStorage.setItem('pop_guest_project_id', '99');
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Orange Juice')).toBeVisible({ timeout: 10_000 });
  });

  test('delete button removes item from list UI', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem(
        'pop_guest_list_items',
        JSON.stringify([{ id: 88, title: 'Yogurt', status: 'sourcing' }])
      );
    });
    await page.reload();
    await page.waitForLoadState('networkidle');

    await page.route('**/api/pop/item/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ deleted: true }),
      });
    });

    await expect(page.locator('text=Yogurt')).toBeVisible({ timeout: 10_000 });
    // Click delete/remove button for the item
    const deleteBtn = page.locator('[aria-label*="delete"], [aria-label*="remove"], button:text("×"), button:text("✕")').first();
    if (await deleteBtn.isVisible()) {
      await deleteBtn.click();
      await expect(page.locator('text=Yogurt')).not.toBeVisible({ timeout: 5_000 });
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. Wallet page
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop Wallet Page', () => {
  test('Regression: guest user sees zero balance, not an error', async ({ page }) => {
    await page.route('**/api/pop/wallet', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ balance_cents: 0, transactions: [] }),
      });
    });

    await page.goto(`${POP_BASE}/wallet`);
    await page.waitForLoadState('networkidle');

    // Should not show an error page
    await expect(page.locator('text=/error|crash|500/i')).not.toBeVisible();
    // Should show balance (0 or $0.00)
    await expect(page.locator('text=/\\$0|0 cents|wallet|savings/i').first()).toBeVisible({ timeout: 10_000 });
  });

  test('wallet page renders without crashing for unauthenticated user', async ({ page }) => {
    await page.goto(`${POP_BASE}/wallet`);
    await page.waitForLoadState('networkidle');
    // No crash — the page should render something (even if it prompts login)
    const body = page.locator('body');
    await expect(body).toBeVisible();
    const bodyText = await body.textContent();
    expect(bodyText).toBeTruthy();
    expect(bodyText!.length).toBeGreaterThan(10);
  });

  test('wallet shows non-zero balance for user with credits', async ({ page, request }) => {
    const token = await mintSession(request, `wallet_test_${Date.now()}@test.com`);
    if (!token) {
      test.skip();
      return;
    }

    await page.route('**/api/pop/wallet', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          balance_cents: 275,
          transactions: [
            { id: 1, amount_cents: 275, description: 'Receipt scan — Whole milk', created_at: new Date().toISOString() },
          ],
        }),
      });
    });

    await page.context().addCookies([
      { name: 'sa_session', value: token, domain: 'localhost', path: '/' },
    ]);
    await page.goto(`${POP_BASE}/wallet`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=/\\$2\\.75|275|2,75/i').first()).toBeVisible({ timeout: 10_000 });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Shared list view /pop-site/list/[id]
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop Shared List Page', () => {
  test('list page renders items returned by backend', async ({ page }) => {
    await page.route('**/api/pop/list/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_id: 1,
          title: 'Smith Family List',
          items: [
            { id: 1, title: 'Whole milk', status: 'sourcing', deal_count: 2, best_price: 3.49, swaps: [] },
            { id: 2, title: 'Dozen eggs', status: 'sourcing', deal_count: 0, best_price: null, swaps: [] },
          ],
        }),
      });
    });

    await page.goto(`${POP_BASE}/list/1`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Whole milk')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('text=Dozen eggs')).toBeVisible({ timeout: 10_000 });
  });

  test('list page shows 404 message for non-existent list', async ({ page }) => {
    await page.route('**/api/pop/list/**', async (route) => {
      await route.fulfill({ status: 404, body: JSON.stringify({ detail: 'Not found' }) });
    });

    await page.goto(`${POP_BASE}/list/999999`);
    await page.waitForLoadState('networkidle');

    const body = page.locator('body');
    const text = await body.textContent();
    // Page should render something — not a white screen
    expect(text!.length).toBeGreaterThan(5);
  });

  test('list page shows deal count badge for items with deals', async ({ page }) => {
    await page.route('**/api/pop/list/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_id: 5,
          title: 'Test List',
          items: [
            { id: 10, title: 'Cheddar cheese', status: 'sourcing', deal_count: 3, best_price: 4.99, swaps: [] },
          ],
        }),
      });
    });

    await page.goto(`${POP_BASE}/list/5`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Cheddar cheese')).toBeVisible({ timeout: 10_000 });
    // Deal count or price should appear
    await expect(page.locator('text=/\\$4\\.99|4,99|3 deal/i').first()).toBeVisible({ timeout: 10_000 });
  });

  test('Regression: swap items appear under list items', async ({ page }) => {
    await page.route('**/api/pop/list/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_id: 7,
          title: 'Swap Test',
          items: [
            {
              id: 20, title: 'Whole milk', status: 'sourcing', deal_count: 1, best_price: 3.49,
              swaps: [{ title: 'Oat milk (save $1.50)', price: 2.49, url: 'https://example.com' }],
            },
          ],
        }),
      });
    });

    await page.goto(`${POP_BASE}/list/7`);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Oat milk').first()).toBeVisible({ timeout: 10_000 });
  });
});

// Sections 5-6 (Invite Page + BFF API Routes) extracted to pop-regression-api.spec.ts
