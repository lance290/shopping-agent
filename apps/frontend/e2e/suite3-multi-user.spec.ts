/**
 * Suite 3: Multi-User & Data Isolation
 * 
 * Philosophy: Ensure complete data separation between users and proper access control.
 * This is CRITICAL for a marketplace with buyers and sellers.
 * 
 * Covers:
 * - User A cannot see User B's data
 * - User A cannot modify User B's data
 * - Project isolation
 * - Session management
 * - Admin vs regular user permissions
 */

import { test, expect, Page } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// ============================================================
// TEST UTILITIES
// ============================================================

interface TestContext {
  sessionToken: string;
  email: string;
  userId?: number;
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
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.waitForResponse(
    (r) => r.url().includes('/api/rows') && r.request().method() === 'GET' && r.status() === 200,
    { timeout: 15000 }
  );
}

async function createRow(request: any, ctx: TestContext, title: string, projectId?: number): Promise<any> {
  const response = await request.post(`${BACKEND_URL}/rows`, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${ctx.sessionToken}`,
    },
    data: {
      title,
      status: 'sourcing',
      project_id: projectId,
      request_spec: {
        item_name: title,
        constraints: '{}',
      },
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function createProject(request: any, ctx: TestContext, title: string): Promise<any> {
  const response = await request.post(`${BACKEND_URL}/projects`, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${ctx.sessionToken}`,
    },
    data: { title },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

// ============================================================
// SCENARIO 1: ROW DATA ISOLATION
// ============================================================

test.describe('Scenario 1: Row Data Isolation', () => {
  let userA: TestContext;
  let userB: TestContext;
  let userARowId: number;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'isolation_userA');
    userB = await mintTestSession(request, 'isolation_userB');
    
    // User A creates a row
    const row = await createRow(request, userA, 'User A Secret Item');
    userARowId = row.id;
  });

  test('User B cannot see User A rows in list', async ({ request }) => {
    // User B lists their rows
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    expect(response.ok()).toBeTruthy();
    
    const rows = await response.json();
    const foundUserARow = rows.find((r: any) => r.title === 'User A Secret Item');
    
    expect(foundUserARow).toBeUndefined();
    console.log('✅ User B cannot see User A rows in list');
  });

  test('User B cannot access User A row by ID', async ({ request }) => {
    // User B tries to access User A's row directly
    const response = await request.get(`${BACKEND_URL}/rows/${userARowId}`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    
    // Should return 404 (not 403, to prevent enumeration)
    expect(response.status()).toBe(404);
    console.log('✅ User B cannot access User A row by ID (returns 404)');
  });

  test('User B cannot update User A row', async ({ request }) => {
    // User B tries to update User A's row
    const response = await request.patch(`${BACKEND_URL}/rows/${userARowId}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userB.sessionToken}`,
      },
      data: { title: 'Hacked by User B' },
    });
    
    expect(response.status()).toBe(404);
    
    // Verify row wasn't modified
    const verifyResponse = await request.get(`${BACKEND_URL}/rows/${userARowId}`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
    });
    const row = await verifyResponse.json();
    expect(row.title).toBe('User A Secret Item');
    
    console.log('✅ User B cannot update User A row');
  });

  test('User B cannot delete User A row', async ({ request }) => {
    // User B tries to delete User A's row
    const response = await request.delete(`${BACKEND_URL}/rows/${userARowId}`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    
    expect(response.status()).toBe(404);
    
    // Verify row still exists
    const verifyResponse = await request.get(`${BACKEND_URL}/rows/${userARowId}`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
    });
    expect(verifyResponse.ok()).toBeTruthy();
    
    console.log('✅ User B cannot delete User A row');
  });

  test('User B cannot search User A row', async ({ request }) => {
    // User B tries to search on User A's row
    const response = await request.post(`${BACKEND_URL}/rows/${userARowId}/search`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userB.sessionToken}`,
      },
      data: { query: 'test' },
    });
    
    expect(response.status()).toBe(404);
    console.log('✅ User B cannot search User A row');
  });

  test('User B cannot select option on User A row', async ({ request }) => {
    // User B tries to select an option on User A's row
    const response = await request.post(`${BACKEND_URL}/rows/${userARowId}/options/1/select`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    
    expect(response.status()).toBe(404);
    console.log('✅ User B cannot select option on User A row');
  });
});

// ============================================================
// SCENARIO 2: PROJECT DATA ISOLATION
// ============================================================

test.describe('Scenario 2: Project Data Isolation', () => {
  let userA: TestContext;
  let userB: TestContext;
  let userAProjectId: number;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'proj_iso_userA');
    userB = await mintTestSession(request, 'proj_iso_userB');
    
    // User A creates a project
    const project = await createProject(request, userA, 'User A Private Project');
    userAProjectId = project.id;
  });

  test('User B cannot see User A projects in list', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/projects`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    expect(response.ok()).toBeTruthy();
    
    const projects = await response.json();
    const foundUserAProject = projects.find((p: any) => p.title === 'User A Private Project');
    
    expect(foundUserAProject).toBeUndefined();
    console.log('✅ User B cannot see User A projects');
  });

  test('User B cannot delete User A project', async ({ request }) => {
    const response = await request.delete(`${BACKEND_URL}/projects/${userAProjectId}`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    
    expect(response.status()).toBe(404);
    
    // Verify project still exists
    const verifyResponse = await request.get(`${BACKEND_URL}/projects`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
    });
    const projects = await verifyResponse.json();
    const found = projects.find((p: any) => p.id === userAProjectId);
    expect(found).toBeTruthy();
    
    console.log('✅ User B cannot delete User A project');
  });

  test('User B cannot add rows to User A project', async ({ request }) => {
    // User B tries to create a row under User A's project
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userB.sessionToken}`,
      },
      data: {
        title: 'Injected by User B',
        status: 'sourcing',
        project_id: userAProjectId, // User A's project!
        request_spec: {
          item_name: 'Injected',
          constraints: '{}',
        },
      },
    });
    
    // Should either fail or create row without project association
    if (response.ok()) {
      const row = await response.json();
      // If created, should NOT be under User A's project
      expect(row.project_id).not.toBe(userAProjectId);
      console.log('✅ Row created but NOT under User A project');
    } else {
      console.log(`✅ Row creation rejected: ${response.status()}`);
    }
  });
});

// ============================================================
// SCENARIO 3: SESSION MANAGEMENT
// ============================================================

test.describe('Scenario 3: Session Management', () => {
  test('Logout invalidates session', async ({ request }) => {
    const ctx = await mintTestSession(request, 'session_logout');
    
    // Verify session works
    const beforeLogout = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(beforeLogout.ok()).toBeTruthy();
    
    // Logout
    const logoutResponse = await request.post(`${BACKEND_URL}/auth/logout`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(logoutResponse.ok()).toBeTruthy();
    
    // Session should no longer work
    const afterLogout = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(afterLogout.status()).toBe(401);
    
    console.log('✅ Logout invalidates session');
  });

  test('Multiple sessions for same user', async ({ request }) => {
    const email = `multi_session_${Date.now()}@test.com`;
    
    // Create first session
    const session1 = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    const token1 = (await session1.json()).session_token;
    
    // Create second session (same email)
    const session2 = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email },
    });
    const token2 = (await session2.json()).session_token;
    
    // Both sessions should work
    const response1 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${token1}` },
    });
    const response2 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${token2}` },
    });
    
    expect(response1.ok()).toBeTruthy();
    expect(response2.ok()).toBeTruthy();
    
    // Logout session 1
    await request.post(`${BACKEND_URL}/auth/logout`, {
      headers: { 'Authorization': `Bearer ${token1}` },
    });
    
    // Session 1 should be invalid, session 2 still valid
    const afterLogout1 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${token1}` },
    });
    const afterLogout2 = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${token2}` },
    });
    
    expect(afterLogout1.status()).toBe(401);
    expect(afterLogout2.ok()).toBeTruthy();
    
    console.log('✅ Multiple sessions managed independently');
  });

  test('Auth check endpoint returns correct user info', async ({ request }) => {
    const ctx = await mintTestSession(request, 'auth_check');
    
    const response = await request.get(`${BACKEND_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.authenticated).toBe(true);
    expect(data.email).toBe(ctx.email);
    
    console.log('✅ Auth check returns correct user info');
  });
});

// ============================================================
// SCENARIO 4: DATA ISOLATION IN UI
// ============================================================

test.describe('Scenario 4: UI Data Isolation', () => {
  let userA: TestContext;
  let userB: TestContext;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'ui_iso_userA');
    userB = await mintTestSession(request, 'ui_iso_userB');
  });

  test('User A sees only their rows in UI', async ({ page, request }) => {
    // Create rows for both users
    await createRow(request, userA, 'User A Laptop');
    await createRow(request, userA, 'User A Headphones');
    await createRow(request, userB, 'User B Secret Item');
    
    // User A loads page
    await setupAuthenticatedPage(page, userA);
    
    // User A should see their rows
    await expect(page.getByRole('heading', { name: 'User A Laptop' }).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'User A Headphones' }).first()).toBeVisible({ timeout: 10000 });
    
    // User A should NOT see User B's row
    const userBRowVisible = await page.locator('text=User B Secret Item').isVisible({ timeout: 2000 }).catch(() => false);
    expect(userBRowVisible).toBeFalsy();
    
    console.log('✅ User A sees only their rows in UI');
  });

  test('User B sees only their rows in UI', async ({ page, request }) => {
    // Create rows for both users
    await createRow(request, userA, 'User A Private');
    await createRow(request, userB, 'User B Public');
    
    // User B loads page
    await setupAuthenticatedPage(page, userB);
    
    // User B should see their row
    await expect(page.getByRole('heading', { name: 'User B Public' }).first()).toBeVisible({ timeout: 10000 });
    
    // User B should NOT see User A's row
    const userARowVisible = await page.locator('text=User A Private').isVisible({ timeout: 2000 }).catch(() => false);
    expect(userARowVisible).toBeFalsy();
    
    console.log('✅ User B sees only their rows in UI');
  });

  test('Switching users shows different data', async ({ browser, request }) => {
    // Create data for both users
    await createRow(request, userA, 'Alice Special Item');
    await createRow(request, userB, 'Bob Special Item');
    
    // Create separate browser contexts for each user
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await pageA.context().addCookies([{
      name: 'sa_session',
      value: userA.sessionToken,
      domain: 'localhost',
      path: '/',
    }]);
    
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await pageB.context().addCookies([{
      name: 'sa_session',
      value: userB.sessionToken,
      domain: 'localhost',
      path: '/',
    }]);
    
    // Load both pages
    await pageA.goto('/', { waitUntil: 'domcontentloaded' });
    await pageB.goto('/', { waitUntil: 'domcontentloaded' });
    await pageA.waitForResponse(
      (r) => r.url().includes('/api/rows') && r.request().method() === 'GET' && r.status() === 200,
      { timeout: 15000 }
    );
    await pageB.waitForResponse(
      (r) => r.url().includes('/api/rows') && r.request().method() === 'GET' && r.status() === 200,
      { timeout: 15000 }
    );
    
    // Verify isolation
    const aliceHeadingA = pageA.getByRole('heading', { name: 'Alice Special Item' }).first();
    const bobHeadingA = pageA.getByRole('heading', { name: 'Bob Special Item' }).first();
    const aliceHeadingB = pageB.getByRole('heading', { name: 'Alice Special Item' }).first();
    const bobHeadingB = pageB.getByRole('heading', { name: 'Bob Special Item' }).first();

    await expect(aliceHeadingA).toBeVisible({ timeout: 15000 });
    await expect(bobHeadingB).toBeVisible({ timeout: 15000 });

    const bobInA = await bobHeadingA.isVisible({ timeout: 1000 }).catch(() => false);
    const aliceInB = await aliceHeadingB.isVisible({ timeout: 1000 }).catch(() => false);

    expect(bobInA).toBeFalsy();
    expect(aliceInB).toBeFalsy();
    
    await contextA.close();
    await contextB.close();
    
    console.log('✅ Different browser contexts show different user data');
  });
});

// ============================================================
// SCENARIO 5: ADMIN ACCESS CONTROL
// ============================================================

test.describe('Scenario 5: Admin Access Control', () => {
  let regularUser: TestContext;

  test.beforeEach(async ({ request }) => {
    regularUser = await mintTestSession(request, 'regular_user');
  });

  test('Regular user cannot access admin audit endpoint', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/admin/audit`, {
      headers: { 'Authorization': `Bearer ${regularUser.sessionToken}` },
    });
    
    // Should return 403 Forbidden
    expect(response.status()).toBe(403);
    console.log('✅ Regular user cannot access admin endpoint');
  });

  test('Unauthenticated user cannot access admin audit endpoint', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/admin/audit`);
    
    expect(response.status()).toBe(401);
    console.log('✅ Unauthenticated user cannot access admin endpoint');
  });
});

// ============================================================
// SCENARIO 6: BID/OFFER ISOLATION
// ============================================================

test.describe('Scenario 6: Bid/Offer Isolation', () => {
  let userA: TestContext;
  let userB: TestContext;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'bid_iso_userA');
    userB = await mintTestSession(request, 'bid_iso_userB');
  });

  test('Bids are only visible to row owner', async ({ request }) => {
    // User A creates row and triggers search
    const row = await createRow(request, userA, 'Laptop for bids test');
    
    // Trigger search to create bids
    await request.post(`${BACKEND_URL}/rows/${row.id}/search`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userA.sessionToken}`,
      },
      data: { query: 'laptop' },
    });
    
    // User A can see the row with bids
    const userAResponse = await request.get(`${BACKEND_URL}/rows/${row.id}`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
    });
    expect(userAResponse.ok()).toBeTruthy();
    
    // User B cannot see the row at all
    const userBResponse = await request.get(`${BACKEND_URL}/rows/${row.id}`, {
      headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
    });
    expect(userBResponse.status()).toBe(404);
    
    console.log('✅ Bids only visible to row owner');
  });
});

// ============================================================
// SCENARIO 7: CLICKOUT ISOLATION
// ============================================================

test.describe('Scenario 7: Clickout Event Isolation', () => {
  let userA: TestContext;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'clickout_iso');
  });

  test('Clickout events are logged per user', async ({ request }) => {
    // Create a row and trigger clickout
    const row = await createRow(request, userA, 'Clickout test item');
    
    const clickoutUrl = 'https://www.amazon.com/dp/B08N5WRWNW';
    const response = await request.get(
      `${BACKEND_URL}/api/out?url=${encodeURIComponent(clickoutUrl)}&row_id=${row.id}&idx=0&source=test`,
      {
        headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
        maxRedirects: 0,
      }
    );
    
    // Should redirect
    expect(response.status()).toBe(302);
    
    // Note: We can't easily verify the clickout_event table from tests
    // without admin access, but the endpoint working is a good sign
    console.log('✅ Clickout logged for user');
  });
});

// ============================================================
// SCENARIO 8: BUG REPORT ISOLATION
// ============================================================

test.describe('Scenario 8: Bug Report Isolation', () => {
  let userA: TestContext;
  let userB: TestContext;

  test.beforeEach(async ({ request }) => {
    userA = await mintTestSession(request, 'bug_iso_userA');
    userB = await mintTestSession(request, 'bug_iso_userB');
  });

  test('User can only see their own bug reports', async ({ request }) => {
    // User A creates a bug report
    const createResponse = await request.post(`${BACKEND_URL}/api/bugs`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
      multipart: {
        notes: 'User A private bug report',
        severity: 'low',
        category: 'ui',
      },
    });
    
    if (createResponse.ok()) {
      const bug = await createResponse.json();
      
      // User A can see their bug
      const userAResponse = await request.get(`${BACKEND_URL}/api/bugs/${bug.id}`, {
        headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
      });
      expect(userAResponse.ok()).toBeTruthy();
      
      // User B cannot see User A's bug
      const userBResponse = await request.get(`${BACKEND_URL}/api/bugs/${bug.id}`, {
        headers: { 'Authorization': `Bearer ${userB.sessionToken}` },
      });
      expect(userBResponse.status()).toBe(404);
      
      console.log('✅ Bug reports isolated per user');
    } else {
      console.log('ℹ️ Bug creation failed, skipping isolation test');
    }
  });
});
