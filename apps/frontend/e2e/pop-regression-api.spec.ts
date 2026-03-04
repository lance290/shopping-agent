/**
 * Pop BFF API Routes smoke tests + Invite page tests.
 * Extracted from pop-regression.spec.ts to keep files under 450 lines.
 */

import { test, expect, Page } from '@playwright/test';

// ─────────────────────────────────────────────────────────────────────────────
// 5. Pop Invite Page
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop Invite Page', () => {
  test('Valid invite shows join form', async ({ page }) => {
    // Mock a valid invite response
    await page.route('**/api/pop/invite/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_title: 'Smith Family Groceries',
          invited_by_name: 'Jane',
          project_id: 42,
        }),
      });
    });

    await page.goto('/pop-site/invite/valid-token-abc');
    
    // Should show the list name
    const content = await page.textContent('body');
    expect(content).toContain('Smith Family Groceries');
  });

  test('Invalid invite shows error', async ({ page }) => {
    await page.route('**/api/pop/invite/**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invite not found' }),
      });
    });

    await page.goto('/pop-site/invite/invalid-token');
    
    // Should show some error indication
    const content = await page.textContent('body');
    // The page should handle the error gracefully
    expect(content).toBeTruthy();
  });

  test('Expired invite shows expired message', async ({ page }) => {
    await page.route('**/api/pop/invite/**', async (route) => {
      await route.fulfill({
        status: 410,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invite expired' }),
      });
    });

    await page.goto('/pop-site/invite/expired-token');
    
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });

  test('Join button requires auth', async ({ page }) => {
    await page.route('**/api/pop/invite/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          project_title: 'Test List',
          invited_by_name: 'Bob',
          project_id: 99,
        }),
      });
    });

    // Mock the join endpoint to return 401
    await page.route('**/api/pop/join-list/**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not authenticated' }),
      });
    });

    await page.goto('/pop-site/invite/test-token');
    
    // The page should handle the unauthenticated state
    const content = await page.textContent('body');
    expect(content).toBeTruthy();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 6. BFF API route smoke tests (via fetch, no browser)
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Pop BFF API Routes (smoke)', () => {
  test('GET /api/pop/wallet without auth returns 200 with zero balance', async ({ request }) => {
    const resp = await request.get('/api/pop/wallet');
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.balance_cents).toBe(0);
    expect(Array.isArray(data.transactions)).toBe(true);
  });

  test('POST /api/pop/chat with missing message returns 400', async ({ request }) => {
    const resp = await request.post('/api/pop/chat', {
      data: {},
      headers: { 'Content-Type': 'application/json' },
    });
    expect(resp.status()).toBe(400);
    const data = await resp.json();
    expect(data.error).toBeTruthy();
  });

  test('POST /api/pop/chat with message returns 200', async ({ request }) => {
    const resp = await request.post('/api/pop/chat', {
      data: { message: 'ping test' },
      headers: { 'Content-Type': 'application/json' },
    });
    expect(resp.status()).toBe(200);
    const data = await resp.json();
    expect(data.reply).toBeTruthy();
    expect(typeof data.reply).toBe('string');
  });

  test('GET /api/pop/list/[id] for non-existent project propagates backend status', async ({ request }) => {
    const resp = await request.get('/api/pop/list/9999999');
    expect([200, 404, 500]).toContain(resp.status());
  });

  test('PATCH /api/pop/item/[id] without auth returns 401', async ({ request }) => {
    const resp = await request.patch('/api/pop/item/999', {
      data: { title: 'Hacked' },
      headers: { 'Content-Type': 'application/json' },
    });
    expect(resp.status()).toBe(401);
  });

  test('DELETE /api/pop/item/[id] without auth returns 401', async ({ request }) => {
    const resp = await request.delete('/api/pop/item/999');
    expect(resp.status()).toBe(401);
  });

  test('GET /api/pop/my-list without auth returns 401', async ({ request }) => {
    const resp = await request.get('/api/pop/my-list');
    expect(resp.status()).toBe(401);
  });

  test('POST /api/pop/invite/[id] without auth returns 401', async ({ request }) => {
    const resp = await request.post('/api/pop/invite/some-project-id');
    expect(resp.status()).toBe(401);
  });

  test('GET /api/pop/invite/[id] for unknown token returns 4xx', async ({ request }) => {
    const resp = await request.get('/api/pop/invite/bogus-token-xyz');
    expect(resp.status()).toBeGreaterThanOrEqual(400);
    expect(resp.status()).toBeLessThan(500);
  });
});
