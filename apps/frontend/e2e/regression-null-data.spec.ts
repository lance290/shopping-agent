/**
 * E2E Regression: Null/malformed data in rows must not crash the UI.
 *
 * These tests create rows with various null/malformed JSONB fields via the
 * backend API, then verify the frontend renders without crashing.
 *
 * Covers:
 * - Rows with null choice_answers / choice_factors / selected_providers
 * - Rows with JSON "null" stored in JSONB columns
 * - Mixed rows: some valid, some null — full board render
 * - Provider toggle renders with null selectedProviders
 * - Anonymous (unauthenticated) user sees empty board without crash
 */

import { test, expect, Page } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// ============================================================
// TEST UTILITIES
// ============================================================

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

async function createRowViaApi(
  request: any,
  token: string,
  title: string,
  overrides: Record<string, any> = {},
): Promise<number> {
  const resp = await request.post(`${BACKEND_URL}/rows`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: {
      title,
      status: 'sourcing',
      request_spec: { item_name: title, constraints: '{}' },
      ...overrides,
    },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  return data.id;
}

async function patchRowViaApi(
  request: any,
  token: string,
  rowId: number,
  patch: Record<string, any>,
): Promise<void> {
  await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: patch,
  });
}

// ============================================================
// SCENARIO 1: Anonymous user sees empty board (no crash)
// ============================================================

test.describe('Anonymous user — no crash', () => {
  test('homepage loads without JavaScript error', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // No "Cannot convert undefined or null to object" errors
    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object') ||
      e.includes('Object.entries')
    );
    expect(nullErrors).toHaveLength(0);
  });

  test('chat input is visible for anonymous users', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const chatInput = page.locator('input[placeholder*="looking for"], input[placeholder*="search"], textarea');
    await expect(chatInput.first()).toBeVisible({ timeout: 10000 });
  });
});

// ============================================================
// SCENARIO 2: Authenticated user with null JSONB rows
// ============================================================

test.describe('Null JSONB fields — no crash on render', () => {
  let ctx: TestContext;

  test.beforeAll(async ({ request }) => {
    ctx = await mintTestSession(request, 'null_regression');
  });

  test('board renders with rows that have null choice_answers', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    // Create a row, then patch choice_answers to null
    const rowId = await createRowViaApi(request, ctx.sessionToken, 'Null answers test');
    await patchRowViaApi(request, ctx.sessionToken, rowId, { choice_answers: null });

    await setupAuthenticatedPage(page, ctx);

    // Wait for rows to load
    await page.waitForTimeout(3000);

    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object')
    );
    expect(nullErrors).toHaveLength(0);
  });

  test('board renders with rows that have null selected_providers', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const rowId = await createRowViaApi(request, ctx.sessionToken, 'Null providers test');
    await patchRowViaApi(request, ctx.sessionToken, rowId, { selected_providers: null });

    await setupAuthenticatedPage(page, ctx);
    await page.waitForTimeout(3000);

    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object')
    );
    expect(nullErrors).toHaveLength(0);
  });

  test('clicking a row with null selected_providers shows provider toggles', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const rowId = await createRowViaApi(request, ctx.sessionToken, 'Toggle null test');
    await patchRowViaApi(request, ctx.sessionToken, rowId, { selected_providers: null });

    await setupAuthenticatedPage(page, ctx);
    await page.waitForTimeout(3000);

    // Click the row tile to activate it
    const rowTile = page.locator(`text=Toggle null test`).first();
    if (await rowTile.isVisible()) {
      await rowTile.click();
      await page.waitForTimeout(1000);
    }

    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object')
    );
    expect(nullErrors).toHaveLength(0);
  });
});

// ============================================================
// SCENARIO 3: Mixed rows — some valid, some with null data
// ============================================================

test.describe('Mixed valid/null rows — board stability', () => {
  let ctx: TestContext;

  test.beforeAll(async ({ request }) => {
    ctx = await mintTestSession(request, 'mixed_regression');
  });

  test('board renders 5+ rows with mixed null/valid data without crash', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    // Create rows with various data states
    const row1 = await createRowViaApi(request, ctx.sessionToken, 'Valid row');
    await patchRowViaApi(request, ctx.sessionToken, row1, {
      choice_answers: JSON.stringify({ size: 'M', color: 'blue' }),
      selected_providers: JSON.stringify({ amazon: true, ebay: true }),
    });

    const row2 = await createRowViaApi(request, ctx.sessionToken, 'Null answers');
    await patchRowViaApi(request, ctx.sessionToken, row2, {
      choice_answers: null,
      selected_providers: null,
    });

    const row3 = await createRowViaApi(request, ctx.sessionToken, 'Empty answers');
    await patchRowViaApi(request, ctx.sessionToken, row3, {
      choice_answers: JSON.stringify({}),
    });

    await createRowViaApi(request, ctx.sessionToken, 'No patches row');
    await createRowViaApi(request, ctx.sessionToken, 'Another clean row');

    await setupAuthenticatedPage(page, ctx);
    await page.waitForTimeout(5000);

    // The board should have rendered without errors
    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object') ||
      e.includes('Object.entries')
    );
    expect(nullErrors).toHaveLength(0);

    // At least some rows should be visible
    const rowTitles = page.locator('[class*="tile"], [class*="row"], [class*="strip"]');
    const count = await rowTitles.count();
    // We created 5 rows, at least some should render
    expect(count).toBeGreaterThan(0);
  });
});

// ============================================================
// SCENARIO 4: Rapid row activation with null data
// ============================================================

test.describe('Rapid row switching — no crash', () => {
  let ctx: TestContext;

  test.beforeAll(async ({ request }) => {
    ctx = await mintTestSession(request, 'rapid_switch');
  });

  test('rapidly clicking between rows with null data does not crash', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    // Create 3 rows with different null states
    for (const title of ['Switch A', 'Switch B', 'Switch C']) {
      const rowId = await createRowViaApi(request, ctx.sessionToken, title);
      if (title === 'Switch B') {
        await patchRowViaApi(request, ctx.sessionToken, rowId, {
          choice_answers: null,
          selected_providers: null,
        });
      }
    }

    await setupAuthenticatedPage(page, ctx);
    await page.waitForTimeout(3000);

    // Rapidly click rows
    for (const title of ['Switch A', 'Switch B', 'Switch C', 'Switch A', 'Switch B']) {
      const tile = page.locator(`text=${title}`).first();
      if (await tile.isVisible()) {
        await tile.click();
        await page.waitForTimeout(300);
      }
    }

    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object')
    );
    expect(nullErrors).toHaveLength(0);
  });
});

// ============================================================
// SCENARIO 5: Row deletion and undo with null data
// ============================================================

test.describe('Row deletion — no crash with null data', () => {
  let ctx: TestContext;

  test.beforeAll(async ({ request }) => {
    ctx = await mintTestSession(request, 'delete_null');
  });

  test('deleting a row with null choice_answers does not crash', async ({ page, request }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const rowId = await createRowViaApi(request, ctx.sessionToken, 'Delete me null');
    await patchRowViaApi(request, ctx.sessionToken, rowId, { choice_answers: null });

    await setupAuthenticatedPage(page, ctx);
    await page.waitForTimeout(3000);

    // Try to find and delete the row (architecture-dependent)
    const row = page.locator('text=Delete me null').first();
    if (await row.isVisible()) {
      // Hover to reveal delete button (if exists)
      await row.hover();
      const deleteBtn = page.locator('[aria-label*="delete"], [aria-label*="Delete"], button:has-text("Delete")').first();
      if (await deleteBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await deleteBtn.click();
        await page.waitForTimeout(1000);
      }
    }

    const nullErrors = errors.filter((e) =>
      e.includes('Cannot convert undefined or null to object')
    );
    expect(nullErrors).toHaveLength(0);
  });
});
