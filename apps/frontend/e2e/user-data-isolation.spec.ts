import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

test.describe('User Data Isolation', () => {
  let tokenA: string;
  let tokenB: string;
  let rowIdA: number;

  test.beforeAll(async ({ request }) => {
    // 1. Mint sessions for User A and User B
    const sessionA = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email: 'user_a_isolation@test.com' }
    });
    expect(sessionA.ok()).toBeTruthy();
    tokenA = (await sessionA.json()).session_token;

    const sessionB = await request.post(`${BACKEND_URL}/test/mint-session`, {
      data: { email: 'user_b_isolation@test.com' }
    });
    expect(sessionB.ok()).toBeTruthy();
    tokenB = (await sessionB.json()).session_token;
  });

  test('User A can create and list their row', async ({ request }) => {
    // Create Row
    const createResp = await request.post(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${tokenA}` },
      data: {
        title: 'User A Secret Row',
        status: 'sourcing',
        currency: 'USD',
        request_spec: { item_name: 'Secret Item', constraints: '{}' }
      }
    });
    expect(createResp.ok()).toBeTruthy();
    const row = await createResp.json();
    rowIdA = row.id;
    expect(row.title).toBe('User A Secret Row');

    // List Rows
    const listResp = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${tokenA}` }
    });
    expect(listResp.ok()).toBeTruthy();
    const rows = await listResp.json();
    const found = rows.find((r: any) => r.id === rowIdA);
    expect(found).toBeDefined();
  });

  test('User B cannot see User A rows', async ({ request }) => {
    const listResp = await request.get(`${BACKEND_URL}/rows`, {
      headers: { 'Authorization': `Bearer ${tokenB}` }
    });
    expect(listResp.ok()).toBeTruthy();
    const rows = await listResp.json();
    const found = rows.find((r: any) => r.id === rowIdA);
    expect(found).toBeUndefined();
  });

  test('User B cannot access User A row by ID', async ({ request }) => {
    const getResp = await request.get(`${BACKEND_URL}/rows/${rowIdA}`, {
      headers: { 'Authorization': `Bearer ${tokenB}` }
    });
    expect(getResp.status()).toBe(404);
  });

  test('User B cannot update User A row', async ({ request }) => {
    const patchResp = await request.patch(`${BACKEND_URL}/rows/${rowIdA}`, {
      headers: { 'Authorization': `Bearer ${tokenB}` },
      data: { title: 'Hacked by B' }
    });
    expect(patchResp.status()).toBe(404);
  });

  test('User B cannot delete User A row', async ({ request }) => {
    const deleteResp = await request.delete(`${BACKEND_URL}/rows/${rowIdA}`, {
      headers: { 'Authorization': `Bearer ${tokenB}` }
    });
    expect(deleteResp.status()).toBe(404);
  });
});
