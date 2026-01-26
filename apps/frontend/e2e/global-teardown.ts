import type { FullConfig } from '@playwright/test';

async function globalTeardown(_config: FullConfig) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  try {
    const res = await fetch(`${backendUrl}/test/reset-db`, { method: 'POST' });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      // eslint-disable-next-line no-console
      console.warn(`[e2e] DB reset failed: ${res.status} ${text}`);
      return;
    }
    // eslint-disable-next-line no-console
    console.log('[e2e] DB reset complete');
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[e2e] DB reset error', err);
  }
}

export default globalTeardown;
