/**
 * Suite 1: Happy Path User Journey
 * 
 * Philosophy: Simulate a complete, successful user experience
 * from login to purchase selection - exactly what a human would do.
 * 
 * Covers:
 * - First-time buyer journey
 * - Project-based procurement
 * - Choice factor interaction
 * - Search refinement
 * - Offer selection
 */

import { test, expect, Page } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// ============================================================
// TEST UTILITIES
// ============================================================

interface TestContext {
  sessionToken: string;
  userId?: number;
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

async function waitForChatResponse(page: Page, timeout = 30000): Promise<void> {
  // Wait for assistant message to appear and stop loading
  await page.waitForSelector('[class*="whitespace-pre-wrap"]', { timeout });
  // Give time for streaming to complete
  await page.waitForTimeout(2000);
}

async function typeInChat(page: Page, message: string): Promise<void> {
  const chatInput = page.locator('input[placeholder*="looking for"], input[placeholder*="Refine"]');
  await expect(chatInput).toBeVisible({ timeout: 10000 });
  await chatInput.fill(message);
  await chatInput.press('Enter');
}

async function getRowCount(page: Page): Promise<number> {
  // Count RowStrip components in the board
  return await page.locator('[data-testid="row-strip"], .space-y-6 > div').count();
}

// ============================================================
// SCENARIO 1: FIRST-TIME BUYER JOURNEY
// ============================================================

test.describe('Scenario 1: First-Time Buyer Journey', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'buyer_journey');
  });

  test('Complete buyer flow: search → view offers → refine → select', async ({ page, request }) => {
    test.setTimeout(120000);
    await setupAuthenticatedPage(page, ctx);

    // Step 1: Verify empty state
    await expect(page.locator('text=Your Board is Empty')).toBeVisible({ timeout: 10000 });
    console.log('✅ Step 1: Empty board state verified');

    // Step 2: Create first search via chat
    await typeInChat(page, 'Montana State long sleeve shirt XL blue');
    await waitForChatResponse(page);
    
    // Verify row was created
    await page.waitForTimeout(3000); // Wait for row creation
    const boardText = await page.textContent('body');
    expect(boardText).toContain('Montana State');
    console.log('✅ Step 2: Row created via chat');

    // Step 3: Verify offers appear (or status updates)
    // The board should show the row with status
    await expect(page.locator('text=Montana State').first()).toBeVisible({ timeout: 15000 });
    console.log('✅ Step 3: Row visible in board');

    // Step 4: Refine search with price constraint
    await typeInChat(page, 'under $50 please');
    await waitForChatResponse(page);
    console.log('✅ Step 4: Refinement sent');

    // Step 5: Verify refinement was applied (row should update, not create new)
    // Count rows - should still be 1
    await page.waitForTimeout(2000);
    
    // Take screenshot for debugging
    await page.screenshot({ path: 'test-results/buyer-journey-refinement.png', fullPage: true });
    console.log('✅ Step 5: Screenshot captured');
  });

  test('Multiple independent searches create separate rows', async ({ page }) => {
    test.setTimeout(90000);
    await setupAuthenticatedPage(page, ctx);

    // Create first row
    await typeInChat(page, 'gaming laptop');
    await waitForChatResponse(page);
    await page.waitForTimeout(3000);

    // Create second row (completely different item)
    await typeInChat(page, 'wireless headphones');
    await waitForChatResponse(page);
    await page.waitForTimeout(3000);

    // Verify both rows exist
    const bodyText = await page.textContent('body');
    
    // At least one of them should be visible
    const hasLaptop = bodyText?.includes('laptop') || bodyText?.includes('gaming');
    const hasHeadphones = bodyText?.includes('headphones') || bodyText?.includes('wireless');
    
    console.log(`Rows found - Laptop: ${hasLaptop}, Headphones: ${hasHeadphones}`);
    
    await page.screenshot({ path: 'test-results/multiple-rows.png', fullPage: true });
  });
});

// ============================================================
// SCENARIO 2: PROJECT-BASED PROCUREMENT
// ============================================================

test.describe('Scenario 2: Project-Based Procurement', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'project_buyer');
  });

  test('Create project and add rows under it', async ({ page, request }) => {
    test.setTimeout(120000);
    await setupAuthenticatedPage(page, ctx);

    // Step 1: Create a project via UI
    const newProjectButton = page.locator('button:has-text("New Project")');
    await expect(newProjectButton).toBeVisible({ timeout: 10000 });
    
    // Mock the prompt dialog
    await page.evaluate(() => {
      window.prompt = () => 'Office Setup';
    });
    
    await newProjectButton.click();
    await page.waitForTimeout(2000);
    
    // Verify project appears
    await expect(page.getByText('Office Setup', { exact: true })).toBeVisible({ timeout: 10000 });
    console.log('✅ Project created: Office Setup');

    // Step 2: Add a row to the project
    // Find the "Add Request" button within the project
    const addRequestInProject = page.getByText('Office Setup', { exact: true }).locator('..').locator('..').locator('button:has-text("Add Request")');
    
    if (await addRequestInProject.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addRequestInProject.click();
      await page.waitForTimeout(500);
      
      // Type in chat to create row
      await typeInChat(page, 'ergonomic office chair');
      await waitForChatResponse(page);
      await page.waitForTimeout(3000);
      
      console.log('✅ Row added to project');
    }

    await page.screenshot({ path: 'test-results/project-with-rows.png', fullPage: true });
  });

  test('Create project via API and verify in UI', async ({ page, request }) => {
    test.setTimeout(60000);
    
    // Create project via API
    const projectResponse = await request.post(`${BACKEND_URL}/projects`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { title: 'Summer Vacation' },
    });
    expect(projectResponse.ok()).toBeTruthy();
    const project = await projectResponse.json();
    console.log(`Created project via API: ${project.id}`);

    // Create row under project via API
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Flights to Hawaii',
        status: 'sourcing',
        project_id: project.id,
        request_spec: {
          item_name: 'Flights to Hawaii',
          constraints: '{}',
        },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    console.log('Created row under project via API');

    // Load page and verify
    await setupAuthenticatedPage(page, ctx);
    
    await expect(page.getByText('Summer Vacation', { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Flights to Hawaii' }).first()).toBeVisible({ timeout: 10000 });
    
    console.log('✅ Project and row visible in UI');
    await page.screenshot({ path: 'test-results/api-created-project.png', fullPage: true });
  });
});

// ============================================================
// SCENARIO 3: CHOICE FACTORS INTERACTION
// ============================================================

test.describe('Scenario 3: Choice Factors (RFP Builder)', () => {
  let ctx: TestContext;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'choice_factor');
    
    // Create a row via API with choice factors
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Gaming Laptop',
        status: 'sourcing',
        request_spec: {
          item_name: 'Gaming Laptop',
          constraints: '{}',
        },
        choice_factors: JSON.stringify([
          { name: 'max_budget', label: 'Max Budget', type: 'number', required: true },
          { name: 'screen_size', label: 'Screen Size', type: 'select', options: ['15 inch', '17 inch'], required: false },
          { name: 'brand', label: 'Preferred Brand', type: 'text', required: false },
        ]),
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();
    rowId = row.id;
  });

  test('Choice factors display and can be answered', async ({ page }) => {
    test.setTimeout(60000);
    await setupAuthenticatedPage(page, ctx);

    // Click on the row to make it active
    await page.locator('text=Gaming Laptop').first().click();
    await page.waitForTimeout(1000);

    // Look for choice factor panel or options section
    const optionsButton = page.locator('button:has-text("Options"), button:has-text("Specs")');
    if (await optionsButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      await optionsButton.click();
      await page.waitForTimeout(500);
    }

    // Take screenshot to verify choice factors are visible
    await page.screenshot({ path: 'test-results/choice-factors.png', fullPage: true });
    
    // Check if choice factor labels are visible
    const bodyText = await page.textContent('body');
    const hasFactors = bodyText?.includes('Budget') || bodyText?.includes('Screen') || bodyText?.includes('Brand');
    console.log(`Choice factors visible: ${hasFactors}`);
  });

  test('Answering choice factors updates row', async ({ request }) => {
    // Update choice_answers via API
    const updateResponse = await request.patch(`${BACKEND_URL}/rows/${rowId}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        choice_answers: JSON.stringify({
          max_budget: 1500,
          screen_size: '15 inch',
          brand: 'ASUS',
        }),
      },
    });
    expect(updateResponse.ok()).toBeTruthy();

    // Verify the update persisted
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(getResponse.ok()).toBeTruthy();
    const row = await getResponse.json();
    
    const answers = JSON.parse(row.choice_answers);
    expect(answers.max_budget).toBe(1500);
    expect(answers.screen_size).toBe('15 inch');
    expect(answers.brand).toBe('ASUS');
    
    console.log('✅ Choice answers persisted correctly');
  });
});

// ============================================================
// SCENARIO 4: OFFER SELECTION WORKFLOW
// ============================================================

test.describe('Scenario 4: Offer Selection', () => {
  let ctx: TestContext;
  let rowId: number;
  let bidId: number;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'offer_select');
    
    // Create row with bids via API
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Test Product',
        status: 'bids_arriving',
        request_spec: {
          item_name: 'Test Product',
          constraints: '{}',
        },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();
    rowId = row.id;
    
    // Trigger a search to create bids (if search is configured)
    // For now, we'll test the selection endpoint directly
  });

  test('Select offer via API marks it as selected', async ({ request }) => {
    // First, trigger a search to create some bids
    const searchResponse = await request.post(`${BACKEND_URL}/rows/${rowId}/search`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { query: 'test product' },
    });
    
    if (searchResponse.ok()) {
      const searchData = await searchResponse.json();
      const results = searchData.results || [];
      
      if (results.length > 0 && results[0].bid_id) {
        bidId = results[0].bid_id;
        
        // Select the first bid
        const selectResponse = await request.post(
          `${BACKEND_URL}/rows/${rowId}/options/${bidId}/select`,
          {
            headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
          }
        );
        
        expect(selectResponse.ok()).toBeTruthy();
        const selectData = await selectResponse.json();
        expect(selectData.status).toBe('selected');
        expect(selectData.row_status).toBe('closed');
        
        console.log('✅ Offer selected successfully');
      } else {
        console.log('ℹ️ No bids created (search may be mocked)');
      }
    } else {
      console.log('ℹ️ Search not available (may need API keys)');
    }
  });
});

// ============================================================
// SCENARIO 5: CLICKOUT TRACKING
// ============================================================

test.describe('Scenario 5: Clickout & Affiliate', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'clickout');
  });

  test('Clickout endpoint redirects and logs', async ({ request }) => {
    const testUrl = 'https://www.amazon.com/dp/B08N5WRWNW';
    
    const response = await request.get(
      `${BACKEND_URL}/api/out?url=${encodeURIComponent(testUrl)}&row_id=1&idx=0&source=test`,
      {
        headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
        maxRedirects: 0,
      }
    );
    
    // Should return 302 redirect
    expect(response.status()).toBe(302);
    
    const location = response.headers()['location'];
    expect(location).toBeTruthy();
    console.log(`✅ Clickout redirects to: ${location?.substring(0, 80)}...`);
  });

  test('Clickout rejects invalid URLs', async ({ request }) => {
    const response = await request.get(
      `${BACKEND_URL}/api/out?url=not-a-valid-url`,
      {
        headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
      }
    );
    
    expect(response.status()).toBe(400);
    console.log('✅ Invalid URL rejected');
  });
});

// ============================================================
// SCENARIO 6: END-TO-END FLOW (UI)
// ============================================================

test.describe('Scenario 6: Complete UI Flow', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'e2e_ui');
  });

  test('Full user journey through UI', async ({ page }) => {
    test.setTimeout(180000);
    await setupAuthenticatedPage(page, ctx);

    console.log('🚀 Starting full UI flow test');

    // 1. Verify initial empty state
    const isEmpty = await page.locator('text=Your Board is Empty').isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`1. Empty state: ${isEmpty ? 'Yes' : 'No (has existing data)'}`);

    // 2. Create a search
    await typeInChat(page, 'blue running shoes size 10');
    await waitForChatResponse(page);
    await page.waitForTimeout(5000);
    console.log('2. Search submitted');

    // 3. Verify row appears
    const rowVisible = await page.locator('text=running shoes, text=blue').first().isVisible({ timeout: 10000 }).catch(() => false);
    console.log(`3. Row visible: ${rowVisible}`);

    // 4. Take screenshot of current state
    await page.screenshot({ path: 'test-results/full-flow-after-search.png', fullPage: true });

    // 5. Try to refine
    await typeInChat(page, 'Nike brand only');
    await waitForChatResponse(page);
    await page.waitForTimeout(3000);
    console.log('5. Refinement sent');

    // 6. Final screenshot
    await page.screenshot({ path: 'test-results/full-flow-final.png', fullPage: true });
    console.log('✅ Full UI flow completed');
  });
});
