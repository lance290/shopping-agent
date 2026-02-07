import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { buildApp } from '../src/index';

/**
 * Integration tests for BFF proxy routes.
 * Verifies that requests are correctly forwarded to the backend,
 * auth headers are passed through, and error handling works.
 */

describe('BFF Proxy Routes', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.GOOGLE_GENERATIVE_AI_API_KEY;
    process.env.BACKEND_URL = 'http://backend.local';
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.restoreAllMocks();
  });

  // ── Health ──────────────────────────────────────────────────────────────

  describe('GET /health', () => {
    it('returns ok without hitting backend', async () => {
      const app = buildApp();
      await app.ready();

      const res = await app.inject({ method: 'GET', url: '/health' });
      expect(res.statusCode).toBe(200);
      expect(res.json()).toEqual({ status: 'ok' });
    });
  });

  describe('GET /', () => {
    it('returns hello message', async () => {
      const app = buildApp();
      await app.ready();

      const res = await app.inject({ method: 'GET', url: '/' });
      expect(res.statusCode).toBe(200);
      expect(res.json()).toHaveProperty('message');
    });
  });

  // ── Rows CRUD ──────────────────────────────────────────────────────────

  describe('GET /api/rows', () => {
    it('proxies to backend with auth header', async () => {
      let capturedAuth: string | undefined;
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/rows') && !u.includes('/rows/')) {
          capturedAuth = init?.headers?.Authorization;
          return new Response(JSON.stringify([{ id: 1, title: 'Test' }]), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/rows',
        headers: { authorization: 'Bearer tok123' },
      });

      expect(res.statusCode).toBe(200);
      expect(capturedAuth).toBe('Bearer tok123');
    });

    it('returns 401 when backend says unauthorized', async () => {
      const fetchMock = vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'Not authenticated' }), {
          status: 401, headers: { 'Content-Type': 'application/json' },
        })
      );
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({ method: 'GET', url: '/api/rows' });
      expect(res.statusCode).toBe(401);
    });

    it('returns 502 when backend is unreachable', async () => {
      const fetchMock = vi.fn(async () => { throw new Error('ECONNREFUSED'); });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({ method: 'GET', url: '/api/rows' });
      expect(res.statusCode).toBe(502);
    });
  });

  describe('POST /api/rows', () => {
    it('creates a row via backend', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        calls.push(`${init?.method || 'GET'} ${u}`);
        if (u.includes('/rows') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 99, title: 'New row' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/rows',
        payload: { title: 'New row', status: 'sourcing' },
        headers: { authorization: 'Bearer tok' },
      });

      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('POST') && c.includes('/rows'))).toBe(true);
    });
  });

  describe('GET /api/rows/:id', () => {
    it('returns single row', async () => {
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/rows/5')) {
          return new Response(JSON.stringify({ id: 5, title: 'Row 5' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({ method: 'GET', url: '/api/rows/5' });
      expect(res.statusCode).toBe(200);
    });

    it('returns 404 for missing row', async () => {
      const fetchMock = vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'Not found' }), {
          status: 404, headers: { 'Content-Type': 'application/json' },
        })
      );
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({ method: 'GET', url: '/api/rows/999' });
      expect(res.statusCode).toBe(404);
    });
  });

  describe('DELETE /api/rows/:id', () => {
    it('deletes row via backend', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        calls.push(`${init?.method || 'GET'} ${u}`);
        if (u.includes('/rows/3') && init?.method === 'DELETE') {
          return new Response(JSON.stringify({ status: 'deleted' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'DELETE', url: '/api/rows/3',
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('DELETE') && c.includes('/rows/3'))).toBe(true);
    });
  });

  // ── Projects CRUD ──────────────────────────────────────────────────────

  describe('GET /api/projects', () => {
    it('proxies project list', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        calls.push(u);
        if (u.includes('/projects')) {
          return new Response(JSON.stringify([{ id: 1, title: 'Proj' }]), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/projects',
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('/projects'))).toBe(true);
    });
  });

  describe('POST /api/projects', () => {
    it('creates project', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/projects') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 2, title: 'New Proj' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/projects',
        payload: { title: 'New Proj' },
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
      expect(fetchMock).toHaveBeenCalled();
    });
  });

  describe('DELETE /api/projects/:id', () => {
    it('deletes project', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/projects/7') && init?.method === 'DELETE') {
          return new Response(JSON.stringify({ status: 'deleted' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'DELETE', url: '/api/projects/7',
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
    });
  });

  // ── Auth Proxy ─────────────────────────────────────────────────────────

  describe('Auth proxy routes', () => {
    it('POST /api/auth/start forwards to backend', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        calls.push(u);
        if (u.includes('/auth/start')) {
          return new Response(JSON.stringify({ status: 'sent' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/auth/start',
        payload: { phone: '+11234567890' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('/auth/start'))).toBe(true);
    });

    it('POST /api/auth/verify forwards to backend', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        calls.push(u);
        if (u.includes('/auth/verify')) {
          return new Response(JSON.stringify({ status: 'ok', session_token: 'tok' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/auth/verify',
        payload: { phone: '+11234567890', code: '123456' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('/auth/verify'))).toBe(true);
    });

    it('GET /api/auth/me passes auth header', async () => {
      let capturedAuth: string | undefined;
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/auth/me')) {
          capturedAuth = init?.headers?.Authorization;
          return new Response(JSON.stringify({ authenticated: true, user_id: 1 }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/auth/me',
        headers: { authorization: 'Bearer mytoken' },
      });
      expect(res.statusCode).toBe(200);
      expect(capturedAuth).toBe('Bearer mytoken');
    });

    it('POST /api/auth/logout passes auth header', async () => {
      let capturedAuth: string | undefined;
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/auth/logout')) {
          capturedAuth = init?.headers?.Authorization;
          return new Response(JSON.stringify({ status: 'ok' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/auth/logout',
        headers: { authorization: 'Bearer mytoken' },
      });
      expect(res.statusCode).toBe(200);
      expect(capturedAuth).toBe('Bearer mytoken');
    });
  });

  // ── Likes/Comments proxy ───────────────────────────────────────────────

  describe('Likes proxy', () => {
    it('POST /api/likes forwards body + auth', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        calls.push(u);
        if (u.includes('/likes') && !u.includes('/counts') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 1, bid_id: 42 }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/likes',
        payload: { bid_id: 42 },
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('/likes'))).toBe(true);
    });

    it('GET /api/likes/counts proxies query params', async () => {
      let capturedUrl = '';
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/likes/counts')) {
          capturedUrl = u;
          return new Response(JSON.stringify([{ bid_id: 1, count: 3 }]), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/likes/counts?row_id=5',
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
      expect(capturedUrl).toContain('row_id=5');
    });
  });

  describe('Comments proxy', () => {
    it('POST /api/comments creates comment', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/comments') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 1 }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/comments',
        payload: { bid_id: 1, body: 'nice', row_id: 1 },
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
    });

    it('DELETE /api/comments/:id deletes comment', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/comments/5') && init?.method === 'DELETE') {
          return new Response(JSON.stringify({ status: 'deleted' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'DELETE', url: '/api/comments/5',
        headers: { authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
    });
  });

  // ── Merchants ──────────────────────────────────────────────────────────

  describe('POST /api/merchants/register', () => {
    it('forwards registration to backend', async () => {
      const calls: string[] = [];
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        calls.push(u);
        if (u.includes('/merchants/register') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 1, business_name: 'TestCo' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/merchants/register',
        payload: { business_name: 'TestCo', email: 'a@b.com' },
      });
      expect(res.statusCode).toBe(200);
      expect(calls.some(c => c.includes('/merchants/register'))).toBe(true);
    });

    it('returns 502 when backend fails', async () => {
      const fetchMock = vi.fn(async () => { throw new Error('Connection refused'); });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/merchants/register',
        payload: { business_name: 'TestCo' },
      });
      expect(res.statusCode).toBe(502);
    });
  });

  // ── Bugs ───────────────────────────────────────────────────────────────

  describe('POST /api/bugs', () => {
    it('forwards bug report to backend', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/api/bugs') && init?.method === 'POST') {
          return new Response(JSON.stringify({ id: 1, status: 'received' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/bugs',
        payload: { description: 'broken button' },
        headers: { 'content-type': 'application/json', authorization: 'Bearer tok' },
      });
      expect(res.statusCode).toBe(200);
    });
  });

  // ── Outreach / Vendors ─────────────────────────────────────────────────

  describe('Outreach proxy routes', () => {
    it('GET /api/outreach/vendors/:category returns vendor list', async () => {
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/outreach/vendors/private_aviation')) {
          return new Response(JSON.stringify({
            category: 'private_aviation',
            vendors: [{ title: 'JetCo' }],
          }), { status: 200, headers: { 'Content-Type': 'application/json' } });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/outreach/vendors/private_aviation',
      });
      expect(res.statusCode).toBe(200);
      expect(res.json().vendors).toHaveLength(1);
    });

    it('GET /api/outreach/check-service passes query param', async () => {
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/outreach/check-service')) {
          expect(u).toContain('query=private');
          return new Response(JSON.stringify({ is_service: true }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET', url: '/api/outreach/check-service?query=private+jet',
      });
      expect(res.statusCode).toBe(200);
    });
  });

  // ── Quotes ─────────────────────────────────────────────────────────────

  describe('Quotes proxy routes', () => {
    it('GET /api/quotes/form/:token fetches form', async () => {
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/quotes/form/abc123')) {
          return new Response(JSON.stringify({ token: 'abc123', fields: [] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({ method: 'GET', url: '/api/quotes/form/abc123' });
      expect(res.statusCode).toBe(200);
      expect(res.json().token).toBe('abc123');
    });

    it('POST /api/quotes/submit/:token submits quote', async () => {
      const fetchMock = vi.fn(async (url: any, init: any) => {
        const u = String(url);
        if (u.includes('/quotes/submit/abc123') && init?.method === 'POST') {
          return new Response(JSON.stringify({ status: 'submitted' }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({}), { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'POST', url: '/api/quotes/submit/abc123',
        payload: { price: 1000 },
      });
      expect(res.statusCode).toBe(200);
    });
  });

  // ── Clickout ───────────────────────────────────────────────────────────

  describe('GET /api/out', () => {
    it('returns redirect from backend', async () => {
      const fetchMock = vi.fn(async (url: any) => {
        const u = String(url);
        if (u.includes('/api/out')) {
          // Simulate a redirect response with a location header
          const resp = new Response('', { status: 302 });
          // Response constructor doesn't allow setting Location on 302,
          // so we use a Headers workaround
          Object.defineProperty(resp, 'headers', {
            value: new Headers({ location: 'https://amazon.com/product' }),
          });
          return resp;
        }
        return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
      });
      vi.stubGlobal('fetch', fetchMock as any);

      const app = buildApp();
      await app.ready();
      const res = await app.inject({
        method: 'GET',
        url: '/api/out?url=https%3A%2F%2Famazon.com%2Fproduct',
      });
      expect(res.statusCode).toBe(302);
      expect(res.headers.location).toBe('https://amazon.com/product');
    });
  });
});
