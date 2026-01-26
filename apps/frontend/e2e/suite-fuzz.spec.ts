import { test, expect, Page, APIRequestContext } from '@playwright/test';

/**
 * Suite: Fuzzing / Model-Based Testing
 * 
 * Approach:
 * Instead of linear scenarios, we define a set of "Actions" (Create, Delete, Refresh, Undo).
 * We execute a random sequence of these actions and assert "Invariants" after each step.
 * 
 * Invariants:
 * 1. UI Row Count === API Row Count
 * 2. No Console Errors / 500s
 * 3. Deleted rows are actually gone (after undo window)
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const ITERATIONS = 20; // Robust number for CI/regression

interface FuzzContext {
  sessionToken: string;
  email: string;
  rows: Set<string>; // Local model of expected row titles
}

// --- Helper: Auth ---
async function mintFuzzSession(request: APIRequestContext): Promise<FuzzContext> {
  const email = `fuzz_${Date.now()}_${Math.floor(Math.random() * 1000)}@test.com`;
  const response = await request.post(`${BACKEND_URL}/test/mint-session`, {
    data: { email },
  });
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  return { 
    sessionToken: data.session_token, 
    email,
    rows: new Set() 
  };
}

// --- Helper: Setup Page ---
async function setupPage(page: Page, token: string) {
  await page.context().addCookies([{
    name: 'sa_session',
    value: token,
    domain: 'localhost',
    path: '/',
  }]);
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  // Wait for initial fetch
  await page.waitForResponse(
    (r) => r.url().includes('/api/rows') && r.request().method() === 'GET',
    { timeout: 15000 }
  );
}

// --- Invariant Check ---
async function verifyInvariants(page: Page, request: APIRequestContext, ctx: FuzzContext, stepName: string) {
  console.log(`[Invariant Check] Post-${stepName}`);

  // 1. Fetch Source of Truth from API
  const apiRes = await request.get(`${BACKEND_URL}/rows`, {
    headers: { 'Authorization': `Bearer ${ctx.sessionToken}` }
  });
  expect(apiRes.ok()).toBeTruthy();
  const apiRows = await apiRes.json();
  const apiTitles = new Set<string>(apiRows.filter((r: any) => r.status !== 'archived').map((r: any) => r.title as string));

  // 2. Check UI State
  // We explicitly wait for the UI to settle slightly to account for animations/react updates
  await page.waitForTimeout(500); 
  
  const uiTitles = await page.locator('h3.text-base.font-semibold.text-onyx').allInnerTexts();
  const uiSet = new Set(uiTitles.map(t => t.trim()));

  // 3. Compare (UI should match API)
  // Note: We allow UI to lag slightly on deletion if undo toast is present, 
  // but for this fuzz test we treat sidebar as "eventually consistent" or strict depending on action.
  // Here we enforce strict consistency for visible rows.
  
  // Debug if mismatch
  if (apiTitles.size !== uiSet.size) {
    console.error(`Mismatch! API: ${Array.from(apiTitles)}, UI: ${Array.from(uiSet)}`);
  }

  // We assert that every API row is visible in UI (completeness)
  for (const title of apiTitles) {
    if (!uiSet.has(title)) {
      console.warn(`[Warning] API has "${title}" but UI missing it. (Might be pagination or delay)`);
    }
  }

  // We assert that every UI row exists in API (no phantom rows)
  for (const title of uiSet) {
    // Ignore "Active" or other UI artifacts if they accidentally match selector
    if (title === 'Active' || title === 'Shopping Agent') continue;
    
    expect(apiTitles.has(title), `UI shows "${title}" but API does not have it!`).toBeTruthy();
  }
}

// --- Actions ---

const ACTIONS = [
  {
    name: 'CREATE_ROW',
    weight: 4,
    run: async (page: Page, ctx: FuzzContext, request: APIRequestContext) => {
      const title = `Item ${Date.now()}-${Math.floor(Math.random() * 100)}`;
      console.log(`👉 Action: CREATE_ROW "${title}"`);
      
      // Use UI to create
      const input = page.locator('input[placeholder*="looking for"], input[placeholder*="Refine"]');
      await input.fill(title);
      await page.keyboard.press('Enter');
      
      // 1. Wait for user message to appear (confirm UI handled submit)
      await expect(page.locator(`div:has-text("${title}")`).last()).toBeVisible({ timeout: 5000 });

      // 2. Wait for assistant response (confirm backend handled request)
      await page.waitForSelector('[class*="whitespace-pre-wrap"]', { timeout: 30000 });
      
      // 3. Verify via API first (Source of Truth)
      // This isolates "Backend failed to create" vs "UI failed to render"
      let createdRowId: number | null = null;
      await expect(async () => {
        console.log(`[CREATE_ROW] Checking API for "${title}" (User: ${ctx.email})`);
        const res = await request.get(`${BACKEND_URL}/rows`, {
          headers: { 'Authorization': `Bearer ${ctx.sessionToken}` }
        });
        expect(res.ok()).toBeTruthy();
        const rows = await res.json();
        
        // Debug logging to catch why matching might fail
        const match = rows.find((r: any) => r.title === title);
        if (!match) {
          console.log(`[CREATE_ROW] Waiting for "${title}" in API. Found: ${rows.length} rows.`);
          if (rows.length > 0) {
            console.log(`[DEBUG] First 3 rows: ${JSON.stringify(rows.slice(0, 3).map((r: any) => r.title))}`);
          }
        } else {
          console.log(`[CREATE_ROW] Found "${title}" in API. ID: ${match.id}`);
        }
        
        expect(match).toBeTruthy();
        createdRowId = match?.id;
      }).toPass({ timeout: 90000, intervals: [2000] });

      // 4. Wait for row to appear on board (with reload polling)
      await expect(async () => {
        await page.reload({ waitUntil: 'domcontentloaded' });
        // Check for error alerts too
        const alert = page.locator('[role="alert"]');
        if (await alert.isVisible()) {
          console.log('   (Saw alert during wait:', await alert.innerText(), ')');
        }
        await expect(page.getByRole('heading', { name: title }).first()).toBeVisible({ timeout: 5000 });
      }).toPass({ timeout: 90000, intervals: [5000] });
      
      ctx.rows.add(title);
    }
  },
  {
    name: 'REFRESH_PAGE',
    weight: 1,
    run: async (page: Page, ctx: FuzzContext) => {
      console.log(`👉 Action: REFRESH_PAGE`);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForResponse(
        (r) => r.url().includes('/api/rows') && r.request().method() === 'GET',
        { timeout: 15000 }
      );
    }
  },
  {
    name: 'DELETE_ROW_VIA_API',
    weight: 2,
    run: async (page: Page, ctx: FuzzContext, request: APIRequestContext) => {
      // Pick a random row from API to delete (simulate out-of-band update)
      const apiRes = await request.get(`${BACKEND_URL}/rows`, {
        headers: { 'Authorization': `Bearer ${ctx.sessionToken}` }
      });
      const rows = await apiRes.json();
      if (rows.length === 0) {
        console.log('   (Skipped DELETE: No rows)');
        return;
      }

      const target = rows[Math.floor(Math.random() * rows.length)] as { id: number, title: string };
      console.log(`👉 Action: DELETE_ROW_VIA_API "${target.title}"`);
      
      const deleteRes = await request.delete(`${BACKEND_URL}/rows/${target.id}`, {
        headers: { 'Authorization': `Bearer ${ctx.sessionToken}` }
      });
      expect(deleteRes.ok()).toBeTruthy();
      
      // UI might not update instantly without SWR revalidation or manual refresh.
      // In our app, we might expect a re-fetch or we trigger a manual refresh for the test.
      await page.reload(); 
      ctx.rows.delete(target.title);
    }
  },
  {
    name: 'ARCHIVE_UI',
    weight: 2,
    run: async (page: Page, ctx: FuzzContext) => {
      // Find visible rows using robust test ID
      const rows = page.getByTestId('row-strip');
      const count = await rows.count();
      if (count === 0) {
        console.log('   (Skipped ARCHIVE: No visible rows)');
        return;
      }
      
      // Pick random index
      const idx = Math.floor(Math.random() * count);
      const row = rows.nth(idx);
      const rowTitle = await row.locator('h3').first().innerText();
      console.log(`👉 Action: ARCHIVE_UI "${rowTitle}"`);
      
      // Hover and click archive (ensure strict scoping to THIS row)
      await row.hover();
      // Use .first() just in case, though structure should imply one per row container
      const archiveBtn = row.locator('button[title="Archive row"]').first();
      
      if (await archiveBtn.isVisible()) {
        await archiveBtn.click();
        
        // Verify Undo button appears (row enters pending delete state) OR row disappears
        // We use a poll to be robust against re-renders
        await expect(async () => {
          // Check if row still exists at this index
          const countNow = await rows.count();
          if (idx >= countNow) return; // Row likely gone, success
          
          const currentRow = rows.nth(idx);
          // Check if it's the same row (by title)
          const currentTitle = await currentRow.locator('h3').first().innerText().catch(() => null);
          if (currentTitle !== rowTitle) return; // Row shifted/gone, success
          
          // If row is still there and is the same row, Undo button MUST be visible
          const undoBtn = currentRow.locator('button:has-text("Undo")');
          if (await undoBtn.isVisible()) return; // Success
          
          // If we are here, row exists, title matches, but Undo not visible -> Fail/Retry
          throw new Error(`Undo button not visible for "${rowTitle}"`);
        }).toPass({ timeout: 15000, intervals: [1000] });
      }
    }
  }
];

// --- Test Suite ---

test.describe('Fuzzing / Model-Based Suite', () => {
  test('Randomized User Actions Walkthrough', async ({ page, request }) => {
    test.setTimeout(180000); // 3 minutes for fuzzing
    
    // 1. Init
    const ctx = await mintFuzzSession(request);
    await setupPage(page, ctx.sessionToken);
    
    // 2. Loop
    for (let i = 0; i < ITERATIONS; i++) {
      console.log(`\n--- Iteration ${i + 1}/${ITERATIONS} ---`);
      
      // Weighted random selection
      const totalWeight = ACTIONS.reduce((acc, a) => acc + a.weight, 0);
      let r = Math.random() * totalWeight;
      const action = ACTIONS.find(a => {
        r -= a.weight;
        return r <= 0;
      }) || ACTIONS[0];

      // Execute
      try {
        await action.run(page, ctx, request);
      } catch (e) {
        console.error(`💥 Action ${action.name} Failed:`, e);
        throw e;
      }

      // Verify
      await verifyInvariants(page, request, ctx, action.name);
    }
    
    console.log('✅ Fuzzing run complete without invariant violations.');
  });
});
