import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('Bug Report Flow', () => {
  test('should allow user to submit a bug report via the UI', async ({ page }) => {
    // Mint session so dev-mode endpoints that rely on sa_session cookie are authenticated
    const email = `bug_report_${Date.now()}@example.com`;
    const mint = await page.request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    expect(mint.ok()).toBeTruthy();
    const { session_token } = await mint.json();
    await page.context().addCookies([
      {
        name: 'sa_session',
        value: session_token,
        domain: 'localhost',
        path: '/',
      },
    ]);

    // Navigate to the board view
    await page.goto('/');

    // 1. Verify "Report Bug" button exists in the header
    const reportBugBtn = page.getByRole('button', { name: 'Report Bug' });
    await expect(reportBugBtn).toBeVisible();

    // 2. Open the modal
    await reportBugBtn.click();
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();

    await expect(modal.getByText('Report a Bug')).toBeVisible();

    // 3. Verify submit is disabled initially
    const submitBtn = modal.getByRole('button', { name: 'Submit' });
    await expect(submitBtn).toBeDisabled();

    // 4. Fill required fields (Notes)
    const notesInput = modal.locator('textarea').first();
    await notesInput.fill('This is a test bug report from Playwright E2E');

    // 6. Verify submit is now enabled
    await expect(submitBtn).toBeEnabled();

    // 7. Submit the form
    const submitResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/bugs') && r.request().method() === 'POST' && r.status() >= 200 && r.status() < 400,
      { timeout: 30000 }
    );
    await submitBtn.click();
    await submitResponsePromise;

    // 8. Verify success state (Receipt)
    await expect(page.getByRole('heading', { name: 'Bug Reported!' })).toBeVisible({ timeout: 30000 });
    // Should show some report id
    await expect(page.locator('strong')).toBeVisible();

    // 9. Close the modal via "Done" button
    const doneBtn = page.getByRole('button', { name: 'Done' });
    await doneBtn.click();

    // 10. Verify modal is closed
    await expect(modal).not.toBeVisible();
  });
});
