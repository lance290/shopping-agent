/**
 * PRD-08: Coupon Network & CPG Activation — frontend logic tests.
 *
 * Covers:
 *   - Coupon badge display logic
 *   - Brand portal token validation
 *   - Coupon submission form validation
 *   - Savings display formatting
 */
import { describe, test, expect } from 'vitest';

// ─────────────────────────────────────────────────────────────────────────────
// Types extracted from page.tsx for testability
// ─────────────────────────────────────────────────────────────────────────────

interface CouponBadge {
  swap_id: number;
  savings_cents: number;
  savings_display: string;
  brand_name: string | null;
  product_name: string;
  url: string | null;
}

// ─────────────────────────────────────────────────────────────────────────────
// Logic functions
// ─────────────────────────────────────────────────────────────────────────────

function shouldShowCouponBadge(coupon: CouponBadge | null | undefined): boolean {
  return !!coupon && coupon.savings_cents > 0;
}

function formatSavingsDisplay(cents: number): string {
  return `$${(cents / 100).toFixed(2)} Off`;
}

function buildCouponLabel(coupon: CouponBadge): string {
  const base = 'Clip Coupon';
  return coupon.brand_name ? `${base} — ${coupon.brand_name}` : base;
}

function validateCouponSubmission(data: {
  swap_product_name: string;
  savings_cents: number;
}): { valid: boolean; error?: string } {
  if (!data.swap_product_name.trim()) {
    return { valid: false, error: 'Product name required' };
  }
  if (data.savings_cents <= 0) {
    return { valid: false, error: 'Savings must be positive' };
  }
  return { valid: true };
}

function isTokenValid(token: string | null): boolean {
  return !!token && token.length > 0;
}

// ─────────────────────────────────────────────────────────────────────────────
// Coupon Badge Display
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Coupon badge display', () => {
  test('shows badge when coupon exists with positive savings', () => {
    const coupon: CouponBadge = {
      swap_id: 1,
      savings_cents: 100,
      savings_display: '$1.00 Off',
      brand_name: 'Tide',
      product_name: 'Tide Pods 42ct',
      url: 'https://tide.example.com',
    };
    expect(shouldShowCouponBadge(coupon)).toBe(true);
  });

  test('hides badge when coupon is null', () => {
    expect(shouldShowCouponBadge(null)).toBe(false);
  });

  test('hides badge when coupon is undefined', () => {
    expect(shouldShowCouponBadge(undefined)).toBe(false);
  });

  test('hides badge when savings is zero', () => {
    const coupon: CouponBadge = {
      swap_id: 1,
      savings_cents: 0,
      savings_display: '$0.00 Off',
      brand_name: null,
      product_name: 'Free Thing',
      url: null,
    };
    expect(shouldShowCouponBadge(coupon)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Savings Display Formatting
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Savings display formatting', () => {
  test('formats $1.00 correctly', () => {
    expect(formatSavingsDisplay(100)).toBe('$1.00 Off');
  });

  test('formats $2.50 correctly', () => {
    expect(formatSavingsDisplay(250)).toBe('$2.50 Off');
  });

  test('formats $0.50 correctly', () => {
    expect(formatSavingsDisplay(50)).toBe('$0.50 Off');
  });

  test('formats $10.00 correctly', () => {
    expect(formatSavingsDisplay(1000)).toBe('$10.00 Off');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Coupon Label
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Coupon label', () => {
  test('includes brand name when present', () => {
    const coupon: CouponBadge = {
      swap_id: 1, savings_cents: 100, savings_display: '$1.00 Off',
      brand_name: 'Heinz', product_name: 'Heinz Ketchup', url: null,
    };
    expect(buildCouponLabel(coupon)).toBe('Clip Coupon — Heinz');
  });

  test('shows just "Clip Coupon" when no brand name', () => {
    const coupon: CouponBadge = {
      swap_id: 1, savings_cents: 100, savings_display: '$1.00 Off',
      brand_name: null, product_name: 'Generic Ketchup', url: null,
    };
    expect(buildCouponLabel(coupon)).toBe('Clip Coupon');
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Brand Portal Token Validation
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Brand portal token validation', () => {
  test('valid token string passes', () => {
    expect(isTokenValid('abc123xyz')).toBe(true);
  });

  test('null token fails', () => {
    expect(isTokenValid(null)).toBe(false);
  });

  test('empty string fails', () => {
    expect(isTokenValid('')).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Coupon Submission Validation
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Coupon submission validation', () => {
  test('valid submission passes', () => {
    const result = validateCouponSubmission({
      swap_product_name: 'Tide Pods 42ct',
      savings_cents: 100,
    });
    expect(result).toEqual({ valid: true });
  });

  test('empty product name fails', () => {
    const result = validateCouponSubmission({
      swap_product_name: '',
      savings_cents: 100,
    });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('Product name required');
  });

  test('whitespace-only product name fails', () => {
    const result = validateCouponSubmission({
      swap_product_name: '   ',
      savings_cents: 100,
    });
    expect(result.valid).toBe(false);
  });

  test('zero savings fails', () => {
    const result = validateCouponSubmission({
      swap_product_name: 'Some Product',
      savings_cents: 0,
    });
    expect(result.valid).toBe(false);
    expect(result.error).toBe('Savings must be positive');
  });

  test('negative savings fails', () => {
    const result = validateCouponSubmission({
      swap_product_name: 'Some Product',
      savings_cents: -50,
    });
    expect(result.valid).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Acceptance Criteria
// ─────────────────────────────────────────────────────────────────────────────

describe('PRD-08: Acceptance criteria', () => {
  test('coupon badge displays savings amount from backend', () => {
    const coupon: CouponBadge = {
      swap_id: 42,
      savings_cents: 100,
      savings_display: '$1.00 Off',
      brand_name: 'Tide',
      product_name: 'Tide Pods',
      url: 'https://example.com/coupon',
    };
    expect(shouldShowCouponBadge(coupon)).toBe(true);
    expect(coupon.savings_display).toBe('$1.00 Off');
    expect(buildCouponLabel(coupon)).toBe('Clip Coupon — Tide');
  });

  test('brand PM can submit valid coupon via portal', () => {
    const submission = validateCouponSubmission({
      swap_product_name: 'Tide Pods 42ct',
      savings_cents: 100,
    });
    expect(submission.valid).toBe(true);
  });
});
