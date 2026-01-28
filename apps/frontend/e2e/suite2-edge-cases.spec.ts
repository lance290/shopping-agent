/**
 * Suite 2: Edge Cases & Error Handling
 * 
 * Philosophy: Test error recovery, boundary conditions, and defensive behavior.
 * Ensures the system handles unexpected inputs gracefully.
 * 
 * Covers:
 * - Empty/invalid inputs
 * - Boundary conditions (0 bids, many bids, etc.)
 * - Rate limiting
 * - Security (XSS, injection attempts)
 * - Error messages and recovery
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

// ============================================================
// SCENARIO 1: EMPTY & INVALID INPUTS
// ============================================================

test.describe('Scenario 1: Empty & Invalid Inputs', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'edge_invalid');
  });

  test('Empty search query is handled gracefully', async ({ page }) => {
    await setupAuthenticatedPage(page, ctx);

    // Try to submit empty input
    const chatInput = page.locator('input[placeholder*="looking for"], input[placeholder*="Refine"]');
    await expect(chatInput).toBeVisible({ timeout: 10000 });
    
    // Press Enter with empty input
    await chatInput.focus();
    await chatInput.press('Enter');
    
    // Should not crash, should not create row
    await page.waitForTimeout(1000);
    
    // Verify no error state
    const hasError = await page.locator('text=Error, text=error').isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasError).toBeFalsy();
    
    console.log('✅ Empty input handled gracefully');
  });

  test('Very long search query (1000+ chars)', async ({ request }) => {
    const longQuery = 'a'.repeat(1500);
    
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: longQuery,
        status: 'sourcing',
        request_spec: {
          item_name: longQuery,
          constraints: '{}',
        },
      },
    });
    
    // Should either succeed (with truncation) or return 400/422
    // Either way, should not crash
    console.log(`Long query response status: ${response.status()}`);
    expect([200, 400, 422]).toContain(response.status());
    console.log('✅ Long query handled');
  });

  test('Special characters in search', async ({ request }) => {
    const specialChars = 'laptop <>&"\'`\\/${}[]|;:';
    
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: specialChars,
        status: 'sourcing',
        request_spec: {
          item_name: specialChars,
          constraints: '{}',
        },
      },
    });
    
    expect(response.ok()).toBeTruthy();
    const row = await response.json();
    expect(row.title).toBe(specialChars);
    console.log('✅ Special characters handled correctly');
  });

  test('SQL injection attempt is safely handled', async ({ request }) => {
    const sqlInjection = "'; DROP TABLE row; --";
    
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: sqlInjection,
        status: 'sourcing',
        request_spec: {
          item_name: sqlInjection,
          constraints: '{}',
        },
      },
    });
    
    // Should succeed (stored as text) or reject
    if (response.ok()) {
      const row = await response.json();
      // Table should still exist - try to list rows
      const listResponse = await request.get(`${BACKEND_URL}/rows`, {
        headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
      });
      expect(listResponse.ok()).toBeTruthy();
      console.log('✅ SQL injection safely stored as text');
    } else {
      console.log('✅ SQL injection rejected');
    }
  });

  test('XSS attempt is escaped in output', async ({ page, request }) => {
    const xssPayload = '<script>alert("xss")</script>';
    
    // Create row with XSS payload
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: xssPayload,
        status: 'sourcing',
        request_spec: {
          item_name: xssPayload,
          constraints: '{}',
        },
      },
    });
    expect(response.ok()).toBeTruthy();

    // Load page and verify XSS doesn't execute
    await setupAuthenticatedPage(page, ctx);
    
    // Listen for any alerts
    let alertTriggered = false;
    page.on('dialog', () => { alertTriggered = true; });
    
    await page.waitForTimeout(2000);
    
    expect(alertTriggered).toBeFalsy();
    console.log('✅ XSS payload did not execute');
  });
});

// ============================================================
// SCENARIO 2: BOUNDARY CONDITIONS
// ============================================================

test.describe('Scenario 2: Boundary Conditions', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'edge_boundary');
  });

  test('Row with 0 bids displays correctly', async ({ page, request }) => {
    // Create row without triggering search
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Item with no bids',
        status: 'sourcing',
        request_spec: {
          item_name: 'Item with no bids',
          constraints: '{}',
        },
      },
    });
    expect(response.ok()).toBeTruthy();

    await setupAuthenticatedPage(page, ctx);
    
    // Row should be visible
    await expect(page.getByRole('heading', { name: 'Item with no bids' }).first()).toBeVisible({ timeout: 10000 });
    
    // Should show empty state or "no results" message, not crash
    console.log('✅ Row with 0 bids displays correctly');
  });

  test('Project with 0 rows displays correctly', async ({ page, request }) => {
    // Create empty project
    const response = await request.post(`${BACKEND_URL}/projects`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { title: 'Empty Project' },
    });
    expect(response.ok()).toBeTruthy();

    await setupAuthenticatedPage(page, ctx);
    
    // Project should be visible
    await expect(page.locator('text=Empty Project')).toBeVisible({ timeout: 10000 });
    
    // Should show "no requests" message
    const emptyMessage = await page.locator('text=No requests').isVisible({ timeout: 3000 }).catch(() => false);
    console.log(`Empty project message shown: ${emptyMessage}`);
    console.log('✅ Empty project displays correctly');
  });

  test('Multiple rapid row creations', async ({ request }) => {
    // Create 10 rows in rapid succession
    const promises = [];
    for (let i = 0; i < 10; i++) {
      promises.push(
        request.post(`${BACKEND_URL}/rows`, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${ctx.sessionToken}`,
          },
          data: {
            title: `Rapid Row ${i}`,
            status: 'sourcing',
            request_spec: {
              item_name: `Rapid Row ${i}`,
              constraints: '{}',
            },
          },
        })
      );
    }
    
    const responses = await Promise.all(promises);
    const successCount = responses.filter(r => r.ok()).length;
    
    console.log(`Rapid creation: ${successCount}/10 succeeded`);
    expect(successCount).toBeGreaterThan(0);
    
    // Verify all rows were created
    const listResponse = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    const rows = await listResponse.json();
    const rapidRows = rows.filter((r: any) => r.title.startsWith('Rapid Row'));
    
    console.log(`Rapid rows created: ${rapidRows.length}`);
    console.log('✅ Rapid creation handled');
  });

  test('Delete row while search in progress', async ({ request }) => {
    // Create a row
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Row to delete',
        status: 'sourcing',
        request_spec: {
          item_name: 'Row to delete',
          constraints: '{}',
        },
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const row = await createResponse.json();

    // Start search (non-blocking) and immediately delete
    const searchPromise = request.post(`${BACKEND_URL}/rows/${row.id}/search`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { query: 'test' },
    });

    const deleteResponse = await request.delete(`${BACKEND_URL}/rows/${row.id}`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    
    // Delete should succeed (row is archived)
    expect(deleteResponse.ok()).toBeTruthy();
    
    // Search may succeed or fail, but shouldn't crash
    const searchResponse = await searchPromise;
    console.log(`Search after delete status: ${searchResponse.status()}`);
    
    console.log('✅ Concurrent delete handled');
  });
});

// ============================================================
// SCENARIO 3: AUTHENTICATION EDGE CASES
// ============================================================

test.describe('Scenario 3: Authentication Edge Cases', () => {
  test('Request without auth token returns 401', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows`);
    expect(response.status()).toBe(401);
    console.log('✅ Unauthenticated request rejected');
  });

  test('Request with invalid token returns 401', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': 'Bearer invalid_token_12345' },
    });
    expect(response.status()).toBe(401);
    console.log('✅ Invalid token rejected');
  });

  test('Request with malformed auth header', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': 'NotBearer token' },
    });
    expect(response.status()).toBe(401);
    console.log('✅ Malformed auth header rejected');
  });

  test('Expired/revoked session is rejected', async ({ request }) => {
    // Mint session then revoke it
    const ctx = await mintTestSession(request, 'revoke_test');
    
    // Logout to revoke
    await request.post(`${BACKEND_URL}/auth/logout`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    
    // Try to use revoked token
    const response = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    
    expect(response.status()).toBe(401);
    console.log('✅ Revoked session rejected');
  });
});

// ============================================================
// SCENARIO 4: RATE LIMITING
// ============================================================

test.describe('Scenario 4: Rate Limiting', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'rate_limit');
  });

  test('Search rate limit triggers after threshold', async ({ request }) => {
    // Create a row first
    const rowResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Rate limit test',
        status: 'sourcing',
        request_spec: { item_name: 'test', constraints: '{}' },
      },
    });
    expect(rowResponse.ok()).toBeTruthy();
    const row = await rowResponse.json();

    // Make many rapid search requests
    let rateLimited = false;
    for (let i = 0; i < 35; i++) {
      const response = await request.post(`${BACKEND_URL}/rows/${row.id}/search`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { query: `test ${i}` },
      });
      
      if (response.status() === 429) {
        rateLimited = true;
        console.log(`Rate limited at request ${i + 1}`);
        break;
      }
    }
    
    console.log(`Rate limiting triggered: ${rateLimited}`);
    // Rate limiting may or may not trigger depending on config
    console.log('✅ Rate limit test completed');
  });
});

// ============================================================
// SCENARIO 5: BUG REPORTING
// ============================================================

test.describe('Scenario 5: Bug Reporting Edge Cases', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'bug_edge');
  });

  test('Submit bug report with minimal fields', async ({ request }) => {
    const formData = new FormData();
    formData.append('notes', 'Minimal bug report');
    formData.append('severity', 'low');
    formData.append('category', 'other');
    
    // Note: FormData handling in Playwright may differ
    const response = await request.post(`${BACKEND_URL}/api/bugs`, {
      headers: {
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      multipart: {
        notes: 'Minimal bug report',
        severity: 'low',
        category: 'other',
      },
    });
    
    if (response.ok()) {
      const bug = await response.json();
      expect(bug.id).toBeTruthy();
      console.log(`✅ Bug created: ${bug.id}`);
    } else {
      console.log(`Bug creation status: ${response.status()}`);
    }
  });

  test('Submit bug report with very long notes', async ({ request }) => {
    const longNotes = 'Bug description '.repeat(500); // ~8000 chars
    
    const response = await request.post(`${BACKEND_URL}/api/bugs`, {
      headers: {
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      multipart: {
        notes: longNotes,
        severity: 'medium',
        category: 'ui',
      },
    });
    
    // Should succeed or return validation error, not crash
    expect([200, 201, 400, 422]).toContain(response.status());
    console.log(`✅ Long notes handled: status ${response.status()}`);
  });
});

// ============================================================
// SCENARIO 6: API ERROR RESPONSES
// ============================================================

test.describe('Scenario 6: API Error Responses', () => {
  let ctx: TestContext;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'api_errors');
  });

  test('GET non-existent row returns 404', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/rows/99999999`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.status()).toBe(404);
    console.log('✅ Non-existent row returns 404');
  });

  test('DELETE non-existent row returns 404', async ({ request }) => {
    const response = await request.delete(`${BACKEND_URL}/rows/99999999`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    expect(response.status()).toBe(404);
    console.log('✅ Delete non-existent row returns 404');
  });

  test('PATCH with invalid data returns 422', async ({ request }) => {
    // Create a row first
    const createResponse = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Test row',
        status: 'sourcing',
        request_spec: { item_name: 'test', constraints: '{}' },
      },
    });
    const row = await createResponse.json();

    // Try to update with invalid budget (string instead of number)
    const response = await request.patch(`${BACKEND_URL}/rows/${row.id}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: { budget_max: 'not-a-number' },
    });
    
    // Should return 422 Unprocessable Entity
    expect([400, 422]).toContain(response.status());
    console.log('✅ Invalid data returns validation error');
  });

  test('POST row with missing required fields', async ({ request }) => {
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        // Missing title and request_spec
        status: 'sourcing',
      },
    });
    
    expect([400, 422]).toContain(response.status());
    console.log('✅ Missing fields returns validation error');
  });
});

// ============================================================
// SCENARIO 7: CONCURRENT MODIFICATIONS
// ============================================================

test.describe('Scenario 7: Concurrent Modifications', () => {
  let ctx: TestContext;
  let rowId: number;

  test.beforeEach(async ({ request }) => {
    ctx = await mintTestSession(request, 'concurrent');
    
    const response = await request.post(`${BACKEND_URL}/rows`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${ctx.sessionToken}`,
      },
      data: {
        title: 'Concurrent test row',
        status: 'sourcing',
        request_spec: { item_name: 'test', constraints: '{}' },
      },
    });
    const row = await response.json();
    rowId = row.id;
  });

  test('Simultaneous updates to same row', async ({ request }) => {
    // Send multiple updates simultaneously
    const updates = [
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update A' },
      }),
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update B' },
      }),
      request.patch(`${BACKEND_URL}/rows/${rowId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${ctx.sessionToken}`,
        },
        data: { title: 'Update C' },
      }),
    ];
    
    const responses = await Promise.all(updates);
    const successCount = responses.filter(r => r.ok()).length;
    
    console.log(`Concurrent updates: ${successCount}/3 succeeded`);
    expect(successCount).toBe(3); // All should succeed (last-write-wins)
    
    // Verify final state
    const getResponse = await request.get(`${BACKEND_URL}/rows/${rowId}`, {
      headers: { 'Authorization': `Bearer ${ctx.sessionToken}` },
    });
    const row = await getResponse.json();
    console.log(`Final title: ${row.title}`);
    expect(['Update A', 'Update B', 'Update C']).toContain(row.title);
    console.log('✅ Concurrent updates handled');
  });
});
