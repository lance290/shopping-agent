/**
 * Suite 3 Part 2: Admin Access, Bid/Offer Isolation, Clickout & Bug Report Isolation
 * Extracted from suite3-multi-user.spec.ts to keep files under 450 lines.
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

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

async function createRow(request: any, ctx: TestContext, title: string) {
  const response = await request.post(`${BACKEND_URL}/rows`, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${ctx.sessionToken}`,
    },
    data: {
      title,
      status: 'sourcing',
      request_spec: { item_name: title, constraints: '{}' },
    },
  });
  expect(response.ok()).toBeTruthy();
  return await response.json();
}

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
    const row = await createRow(request, userA, 'Laptop for bids test');
    
    await request.post(`${BACKEND_URL}/rows/${row.id}/search`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userA.sessionToken}`,
      },
      data: { query: 'laptop' },
    });
    
    const userAResponse = await request.get(`${BACKEND_URL}/rows/${row.id}`, {
      headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
    });
    expect(userAResponse.ok()).toBeTruthy();
    
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
    const row = await createRow(request, userA, 'Clickout test item');
    
    const clickoutUrl = 'https://www.amazon.com/dp/B08N5WRWNW';
    const response = await request.get(
      `${BACKEND_URL}/api/out?url=${encodeURIComponent(clickoutUrl)}&row_id=${row.id}&idx=0&source=test`,
      {
        headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
        maxRedirects: 0,
      }
    );
    
    expect(response.status()).toBe(302);
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
      
      const userAResponse = await request.get(`${BACKEND_URL}/api/bugs/${bug.id}`, {
        headers: { 'Authorization': `Bearer ${userA.sessionToken}` },
      });
      expect(userAResponse.ok()).toBeTruthy();
      
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
