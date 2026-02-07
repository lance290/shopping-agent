import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { buildApp } from '../src/index';

/**
 * Tests for buildBasicChoiceFactors via the PATCH /api/rows/:id endpoint
 * with regenerate_choice_factors=true (no Gemini key → uses buildBasicChoiceFactors).
 *
 * Also tests the pure category-detection regex logic directly.
 */

// ── Regex unit tests (mirrors the regex in buildBasicChoiceFactors) ──────────

const bikeRegex = /(\bbikes?\b|\bbicycles?\b|mtb|mountain bike|road bike|gravel bike|e-bike|ebike)/i;
const racquetRegex = /(racquet|racket)/i;
const socksRegex = /\bsocks?\b/i;
const shoesRegex = /(shoe|shoes|sneaker|sneakers|cleat|cleats)/i;

describe('Category detection regex', () => {
  describe('bikes', () => {
    it.each([
      'bike', 'bikes', 'bicycle', 'bicycles',
      'mtb', 'mountain bike', 'road bike', 'gravel bike',
      'e-bike', 'ebike', 'Bianchi Bicycle',
    ])('matches "%s"', (input) => {
      expect(bikeRegex.test(input)).toBe(true);
    });

    it.each(['toaster', 'running shoes', 'mike'])('does NOT match "%s"', (input) => {
      expect(bikeRegex.test(input)).toBe(false);
    });
  });

  describe('racquets', () => {
    it.each(['racquet', 'racket', 'tennis racquet', 'badminton racket'])(
      'matches "%s"', (input) => {
        expect(racquetRegex.test(input)).toBe(true);
      }
    );
  });

  describe('socks', () => {
    it.each(['sock', 'socks', 'wool socks', 'running socks'])(
      'matches "%s"', (input) => {
        expect(socksRegex.test(input)).toBe(true);
      }
    );

    it('does NOT match "socket"', () => {
      expect(socksRegex.test('socket')).toBe(false);
    });
  });

  describe('shoes', () => {
    it.each(['shoe', 'shoes', 'sneaker', 'sneakers', 'cleat', 'cleats', 'running shoes'])(
      'matches "%s"', (input) => {
        expect(shoesRegex.test(input)).toBe(true);
      }
    );
  });
});

// ── Integration: regenerate_choice_factors via BFF PATCH ────────────────────

describe('buildBasicChoiceFactors via PATCH regenerate', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.GOOGLE_GENERATIVE_AI_API_KEY; // force fallback path
    process.env.BACKEND_URL = 'http://backend.local';
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.restoreAllMocks();
  });

  it('returns bike-specific factors for a bicycle row', async () => {
    let savedFactors: any = null;

    // The handler does: 1) fetch GET row, 2) fetchJsonWithTimeout PATCH (which wraps fetch),
    // 3) fetch GET row again for updated data. We need to track the PATCH body.
    const fetchMock = vi.fn(async (url: any, init: any) => {
      const u = String(url);
      const method = init?.method || 'GET';

      if (u.includes('/rows/10') && method === 'PATCH') {
        const body = JSON.parse(init.body);
        if (body.choice_factors) {
          savedFactors = JSON.parse(body.choice_factors);
        }
        return new Response(JSON.stringify({ ok: true }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }

      if (u.includes('/rows/10')) {
        return new Response(JSON.stringify({
          id: 10, title: 'mountain bikes', is_service: false,
          service_category: null, choice_answers: null, request_spec: null,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      return new Response(JSON.stringify({ ok: true }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    });

    vi.stubGlobal('fetch', fetchMock as any);

    const app = buildApp();
    await app.ready();

    const res = await app.inject({
      method: 'PATCH',
      url: '/api/rows/10',
      payload: { regenerate_choice_factors: true },
      headers: { authorization: 'Bearer test-token' },
    });

    expect(res.statusCode).toBe(200);
    expect(savedFactors).not.toBeNull();

    const factorNames = savedFactors.map((f: any) => f.name);
    expect(factorNames).toContain('bike_size');
    expect(factorNames).toContain('frame_material');
    expect(factorNames).toContain('max_budget');
  });

  it('returns generic factors for a toaster row', async () => {
    let savedFactors: any = null;

    const fetchMock = vi.fn(async (url: any, init: any) => {
      const u = String(url);
      const method = init?.method || 'GET';

      if (u.includes('/rows/11') && method === 'PATCH') {
        const body = JSON.parse(init.body);
        if (body.choice_factors) savedFactors = JSON.parse(body.choice_factors);
        return new Response(JSON.stringify({ ok: true }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }

      if (u.includes('/rows/11')) {
        return new Response(JSON.stringify({
          id: 11, title: 'toaster', is_service: false,
          service_category: null, choice_answers: null, request_spec: null,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      return new Response(JSON.stringify({ ok: true }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    });

    vi.stubGlobal('fetch', fetchMock as any);

    const app = buildApp();
    await app.ready();

    await app.inject({
      method: 'PATCH',
      url: '/api/rows/11',
      payload: { regenerate_choice_factors: true },
      headers: { authorization: 'Bearer test-token' },
    });

    expect(savedFactors).not.toBeNull();
    const factorNames = savedFactors.map((f: any) => f.name);
    expect(factorNames).not.toContain('bike_size');
    expect(factorNames).toContain('max_budget');
    expect(factorNames).toContain('condition');
    expect(factorNames).toContain('shipping_speed');
  });

  it('returns shoe factors for sneakers', async () => {
    let savedFactors: any = null;

    const fetchMock = vi.fn(async (url: any, init: any) => {
      const u = String(url);
      const method = init?.method || 'GET';

      if (u.includes('/rows/12') && method === 'PATCH') {
        const body = JSON.parse(init.body);
        if (body.choice_factors) savedFactors = JSON.parse(body.choice_factors);
        return new Response(JSON.stringify({ ok: true }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }

      if (u.includes('/rows/12')) {
        return new Response(JSON.stringify({
          id: 12, title: 'running sneakers', is_service: false,
          service_category: null, choice_answers: null, request_spec: null,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }

      return new Response(JSON.stringify({ ok: true }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    });

    vi.stubGlobal('fetch', fetchMock as any);

    const app = buildApp();
    await app.ready();

    await app.inject({
      method: 'PATCH',
      url: '/api/rows/12',
      payload: { regenerate_choice_factors: true },
      headers: { authorization: 'Bearer test-token' },
    });

    expect(savedFactors).not.toBeNull();
    const factorNames = savedFactors.map((f: any) => f.name);
    expect(factorNames).toContain('shoe_size');
    expect(factorNames).toContain('shoe_material');
  });
});
