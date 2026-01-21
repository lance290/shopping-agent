import { test, expect } from '@playwright/test';

test.describe('Bug Report Flow', () => {
  test('should allow user to submit a bug report via the UI', async ({ page }) => {
    // Navigate to the board view
    await page.goto('/');

    // 1. Verify "Report Bug" button exists in the header
    const reportBugBtn = page.getByRole('button', { name: 'Report a bug' });
    await expect(reportBugBtn).toBeVisible();

    // 2. Open the modal
    await reportBugBtn.click();
    const modal = page.getByRole('dialog', { name: 'Report a Bug' });
    await expect(modal).toBeVisible();

    // 3. Verify submit is disabled initially
    const submitBtn = modal.getByRole('button', { name: 'Submit' });
    await expect(submitBtn).toBeDisabled();

    // 4. Fill required fields (Notes)
    const notesInput = modal.getByLabel('What happened?');
    await notesInput.fill('This is a test bug report from Playwright E2E');

    // 5. Attach a mock screenshot (required)
    // We mock the file input
    const fileInput = modal.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'screenshot.png',
      mimeType: 'image/png',
      buffer: Buffer.from('mock-image-content'),
    });

    // 6. Verify submit is now enabled
    await expect(submitBtn).toBeEnabled();

    // 7. Submit the form
    await submitBtn.click();

    // 8. Verify success state (Receipt)
    // The mock API returns success with a mock ID
    await expect(modal.getByText('Bug Reported!')).toBeVisible();
    await expect(modal.getByText('MOCK-')).toBeVisible();

    // 9. Close the modal via "Done" button
    const doneBtn = modal.getByRole('button', { name: 'Done' });
    await doneBtn.click();

    // 10. Verify modal is closed
    await expect(modal).not.toBeVisible();
  });
});
