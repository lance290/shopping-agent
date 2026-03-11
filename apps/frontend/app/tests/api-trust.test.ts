import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('../utils/anonymous-session', () => ({
  getAnonymousSessionId: vi.fn().mockReturnValue('anon-test-session'),
}));

import { AUTH_REQUIRED } from '../utils/api-core';
import { submitFeedback, submitOutcome, logEvent } from '../utils/api-trust';

describe('trust metrics API helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  test('submitFeedback posts to the feedback endpoint with auth and anon headers', async () => {
    window.localStorage.setItem('session_token', 'token-123');
    const fetchMock = vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ id: 5, status: 'ok' }), { status: 200 })
    );

    const result = await submitFeedback(42, { bid_id: 9, feedback_type: 'good_lead' });

    expect(result).toEqual({ id: 5, status: 'ok' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/rows/42/feedback',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
        headers: expect.objectContaining({
          Authorization: 'Bearer token-123',
          'Content-Type': 'application/json',
          'X-Anonymous-Session-Id': 'anon-test-session',
        }),
      })
    );
  });

  test('submitOutcome returns AUTH_REQUIRED on 401', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 401 }));

    const result = await submitOutcome(11, { outcome: 'solved' });

    expect(result).toBe(AUTH_REQUIRED);
  });

  test('logEvent returns null on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('oops', { status: 500 }));

    const result = await logEvent(7, { event_type: 'candidate_clicked', bid_id: 99 });

    expect(result).toBeNull();
  });
});
