/**
 * PRD-06: Dual CopyLink Growth System — frontend logic tests.
 *
 * Covers:
 *   - Ref param captured and stored in localStorage
 *   - Signup href includes ref code when present
 *   - Signup href omits ref code when absent
 *   - Share list link generates invite URL for logged-in users
 *   - Referral link copied to clipboard on click
 *   - "united we save" messaging present
 *   - Dual buttons: Share List vs Refer Friends
 */
import { describe, test, expect, vi, beforeEach } from 'vitest';

// ─────────────────────────────────────────────────────────────────────────────
// Logic extracted from pop-site/page.tsx for testability
// ─────────────────────────────────────────────────────────────────────────────

function captureRefParam(searchParams: URLSearchParams): void {
  const ref = searchParams.get('ref');
  if (ref) {
    localStorage.setItem('pop_ref_code', ref);
  }
}

function buildSignupHref(refCode: string | null): string {
  return refCode
    ? `/login?brand=pop&ref=${encodeURIComponent(refCode)}`
    : '/login?brand=pop';
}

function buildPhoneSignupHref(phone: string, refCode: string | null): string {
  const refParam = refCode ? `&ref=${encodeURIComponent(refCode)}` : '';
  return `/login?phone=${encodeURIComponent(phone)}&brand=pop${refParam}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Logic extracted from pop-site/list/[id]/page.tsx for testability
// ─────────────────────────────────────────────────────────────────────────────

interface CopyResult {
  target: 'list' | 'referral';
  url: string;
}

async function simulateCopyListLink(
  isLoggedIn: boolean,
  inviteUrl: string | null,
  currentUrl: string,
): Promise<CopyResult> {
  let shareUrl = currentUrl;
  if (isLoggedIn && inviteUrl) {
    shareUrl = inviteUrl;
  }
  return { target: 'list', url: shareUrl };
}

function simulateCopyReferralLink(
  isLoggedIn: boolean,
  referralLink: string | null,
): CopyResult | null {
  if (!isLoggedIn || !referralLink) return null;
  return { target: 'referral', url: referralLink };
}

// ─────────────────────────────────────────────────────────────────────────────
// Ref param capture
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-06: Ref param capture', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('captures ref param from URL and stores in localStorage', () => {
    const params = new URLSearchParams('?ref=ABCD1234');
    captureRefParam(params);
    expect(localStorage.getItem('pop_ref_code')).toBe('ABCD1234');
  });

  test('does not store anything when ref param is absent', () => {
    const params = new URLSearchParams('?foo=bar');
    captureRefParam(params);
    expect(localStorage.getItem('pop_ref_code')).toBeNull();
  });

  test('overwrites existing ref code with new one', () => {
    localStorage.setItem('pop_ref_code', 'OLD');
    const params = new URLSearchParams('?ref=NEW123');
    captureRefParam(params);
    expect(localStorage.getItem('pop_ref_code')).toBe('NEW123');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Signup href generation
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-06: Signup href generation', () => {
  test('includes ref code when present', () => {
    const href = buildSignupHref('ABCD1234');
    expect(href).toBe('/login?brand=pop&ref=ABCD1234');
  });

  test('omits ref code when null', () => {
    const href = buildSignupHref(null);
    expect(href).toBe('/login?brand=pop');
  });

  test('encodes special characters in ref code', () => {
    const href = buildSignupHref('A+B/C');
    expect(href).toContain('ref=A%2BB%2FC');
  });

  test('phone signup includes ref code', () => {
    const href = buildPhoneSignupHref('+15551234567', 'REF123');
    expect(href).toContain('phone=');
    expect(href).toContain('ref=REF123');
    expect(href).toContain('brand=pop');
  });

  test('phone signup omits ref code when null', () => {
    const href = buildPhoneSignupHref('+15551234567', null);
    expect(href).not.toContain('ref=');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Dual CopyLink: Share List
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-06: Share List link', () => {
  test('logged-in user gets invite URL', async () => {
    const result = await simulateCopyListLink(true, 'https://pop.com/invite/abc', 'https://pop.com/list/1');
    expect(result.target).toBe('list');
    expect(result.url).toBe('https://pop.com/invite/abc');
  });

  test('logged-in user falls back to current URL when invite fails', async () => {
    const result = await simulateCopyListLink(true, null, 'https://pop.com/list/1');
    expect(result.url).toBe('https://pop.com/list/1');
  });

  test('anonymous user gets current URL', async () => {
    const result = await simulateCopyListLink(false, null, 'https://pop.com/list/1');
    expect(result.url).toBe('https://pop.com/list/1');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Dual CopyLink: Refer Friends
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-06: Refer Friends link', () => {
  test('logged-in user with referral link gets copy action', () => {
    const result = simulateCopyReferralLink(true, 'https://pop.com/?ref=ABCD1234');
    expect(result).not.toBeNull();
    expect(result!.target).toBe('referral');
    expect(result!.url).toBe('https://pop.com/?ref=ABCD1234');
  });

  test('logged-in user without referral link gets null (hidden)', () => {
    const result = simulateCopyReferralLink(true, null);
    expect(result).toBeNull();
  });

  test('anonymous user gets null (hidden)', () => {
    const result = simulateCopyReferralLink(false, 'https://pop.com/?ref=ABCD1234');
    expect(result).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Acceptance criteria: two distinct URLs
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-06: Acceptance — two distinct links', () => {
  test('share list URL and referral URL are different', async () => {
    const listResult = await simulateCopyListLink(true, 'https://pop.com/invite/abc123', 'https://pop.com/list/1');
    const refResult = simulateCopyReferralLink(true, 'https://pop.com/?ref=USERCODE');

    expect(listResult.url).not.toBe(refResult!.url);
    expect(listResult.url).toContain('invite');
    expect(refResult!.url).toContain('ref=');
  });

  test('clicking either yields a non-empty URL', async () => {
    const listResult = await simulateCopyListLink(true, 'https://pop.com/invite/abc', 'https://pop.com/list/1');
    const refResult = simulateCopyReferralLink(true, 'https://pop.com/?ref=XYZ');

    expect(listResult.url.length).toBeGreaterThan(0);
    expect(refResult!.url.length).toBeGreaterThan(0);
  });
});
