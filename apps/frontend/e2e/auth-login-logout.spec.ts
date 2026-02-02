import { test, expect } from '@playwright/test';

test.describe('Auth: Login and Logout', () => {
  test.beforeEach(async ({ context }) => {
    // Clear cookies before each test
    await context.clearCookies();
  });

  test('unauthenticated user is redirected from / to /login', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  test('login page shows email input initially', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Send verification code');
  });

  test('can enter email and request verification code', async ({ page }) => {
    test.skip(!process.env.E2E_ALLOWED_EMAIL, 'Set E2E_ALLOWED_EMAIL to an allowlisted email to run OTP e2e');
    await page.goto('/login');
    
    await page.fill('input[type="email"]', process.env.E2E_ALLOWED_EMAIL as string);
    await page.click('button[type="submit"]');
    
    // After sending code, should show code input
    await expect(page.locator('input[id="code"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=We sent a verification code')).toBeVisible();
  });

  test('authenticated user can still access /login', async ({ page, context }) => {
    // Set a fake session cookie to simulate authenticated state
    await context.addCookies([
      {
        name: 'sa_session',
        value: 'fake-session-token',
        domain: 'localhost',
        path: '/',
      },
    ]);
    
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);
  });

  test('logout clears session and redirects to login', async ({ page, context }) => {
    // Set a fake session cookie
    await context.addCookies([
      {
        name: 'sa_session',
        value: 'fake-session-token',
        domain: 'localhost',
        path: '/',
      },
    ]);
    
    // Go to home (should work with cookie)
    await page.goto('/');
    await expect(page).toHaveURL('/');
    
    // Call logout API directly
    const response = await page.request.post('/api/auth/logout');
    expect(response.ok()).toBeTruthy();
    
    // After logout, visiting / should redirect to /login
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });
});
