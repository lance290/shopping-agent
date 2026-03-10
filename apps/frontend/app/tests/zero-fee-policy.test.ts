/**
 * ###########################################################################
 * #                                                                         #
 * #   ZERO FEE POLICY — FRONTEND REGRESSION TESTS                          #
 * #                                                                         #
 * #   BuyAnything launches FREE. No commissions. No service fees.           #
 * #   No escrow. The ONLY revenue is AFFILIATE MARKETING (clickouts).      #
 * #                                                                         #
 * #   DO NOT REMOVE OR WEAKEN THESE TESTS.                                 #
 * #   DO NOT add .skip() or .todo().                                       #
 * #                                                                         #
 * #   If you need to introduce fees later:                                 #
 * #     1. Get explicit founder approval                                   #
 * #     2. Update Terms, Disclosure, and these tests together              #
 * #     3. Ship as a deliberate, documented product decision               #
 * #                                                                         #
 * #   These tests exist because AI assistants kept sneaking 5% fees into   #
 * #   the codebase. Never again.                                           #
 * #                                                                         #
 * ###########################################################################
 */

import { describe, test, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const APP_ROOT = path.resolve(__dirname, '..');

function readFileIfExists(relativePath: string): string {
  const fullPath = path.join(APP_ROOT, relativePath);
  if (fs.existsSync(fullPath)) {
    return fs.readFileSync(fullPath, 'utf-8');
  }
  return '';
}

// ###########################################################################
//
//  SECTION 1: MERCHANT REGISTRATION — NO FEE LANGUAGE
//
//  Vendors register on /merchants/register. If that page says we charge
//  a "5% platform fee", vendors will either (a) not register, or
//  (b) rightfully expect us to provide escrow services we don't offer.
//
// ###########################################################################

describe('ZERO FEE POLICY: Merchant Registration Page', () => {
  const source = readFileIfExists('merchants/register/page.tsx');

  test('page exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! CRITICAL: The merchant registration page MUST NOT mention a    !
   * ! "5% platform fee" or "Platform Fee Notice". We are FREE.      !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('does NOT mention "5% platform fee"', () => {
    expect(source.toLowerCase()).not.toContain('5% platform fee');
  });

  test('does NOT have a "Platform Fee Notice" heading', () => {
    expect(source.toLowerCase()).not.toContain('platform fee notice');
  });

  test('does NOT mention "commission" as a charge to vendors', () => {
    // "commission" in the context of charging vendors is forbidden.
    // "affiliate commissions" in disclosures is fine (that's our revenue).
    const lines = source.split('\n');
    const suspiciousLines = lines.filter(
      (line) =>
        line.toLowerCase().includes('commission') &&
        !line.toLowerCase().includes('affiliate commission')
    );
    // Allow at most a generic disclosure mentioning commissions on marketplace offers
    for (const line of suspiciousLines) {
      expect(line.toLowerCase()).not.toMatch(/charges?\s+.*commission/);
    }
  });
});

// ###########################################################################
//
//  SECTION 2: DISCLOSURE PAGE — NO TRANSACTION FEES
//
//  The /disclosure page tells users how we make money. The ONLY answer
//  right now is: affiliate links. If this page says "5% of transaction
//  total" or "Standard Rate: 5%", that's a lie AND a legal liability.
//
// ###########################################################################

describe('ZERO FEE POLICY: Disclosure Page', () => {
  const source = readFileIfExists('disclosure/page.tsx');

  test('page exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! FATAL if this fails: the disclosure page is telling users we   !
   * ! charge 5% on transactions. We do NOT.                         !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('does NOT claim "Standard Rate: 5%"', () => {
    expect(source.toLowerCase()).not.toContain('standard rate: 5%');
  });

  test('does NOT claim "5% of transaction total"', () => {
    expect(source.toLowerCase()).not.toContain('5% of transaction');
  });

  test('does NOT claim "5% platform fee"', () => {
    expect(source.toLowerCase()).not.toContain('5% platform fee');
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! The disclosure MUST mention "Zero Platform Fees" or similar    !
   * ! language confirming we don't charge vendors.                   !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('mentions zero fees for vendors', () => {
    expect(source.toLowerCase()).toContain('zero platform fee');
  });
});

// ###########################################################################
//
//  SECTION 3: TERMS OF SERVICE — INTRODUCTION PLATFORM
//
//  Our Terms MUST say we are an "introduction" platform. This is our
//  legal shield against being classified as a payment processor,
//  financial intermediary, or escrow agent.
//
// ###########################################################################

describe('ZERO FEE POLICY: Terms of Service', () => {
  const source = readFileIfExists('(public)/terms/page.tsx');

  test('page exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! CRITICAL: Terms MUST identify us as an "introduction" platform !
   * ! This is the single most important legal sentence on the site. !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('identifies as "introduction" platform', () => {
    expect(source.toLowerCase()).toContain('introduction');
  });

  test('explicitly disclaims escrow agent role', () => {
    // Must say we do NOT act as escrow
    expect(source.toLowerCase()).toContain('do not act as an escrow');
  });

  test('explicitly disclaims financial intermediary role', () => {
    expect(source.toLowerCase()).toContain('financial intermediary');
  });
});

// ###########################################################################
//
//  SECTION 4: ESCROW STATUS COMPONENT — NO "FUNDS IN ESCROW"
//
//  The EscrowStatus.tsx component renders in the deal timeline. It MUST
//  NOT claim we hold funds or protect buyers. We don't.
//
// ###########################################################################

describe('ZERO FEE POLICY: EscrowStatus Component', () => {
  const source = readFileIfExists('components/sdui/EscrowStatus.tsx');

  test('component exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! "Funds in Escrow" is a legal claim. If we say it, we must     !
   * ! actually hold funds in escrow. We don't. So don't say it.    !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('does NOT say "Funds in Escrow"', () => {
    expect(source).not.toContain('Funds in Escrow');
  });

  test('does NOT say "Protected until delivery"', () => {
    expect(source).not.toContain('Protected until delivery');
  });
});

// ###########################################################################
//
//  SECTION 5: HERO / LANDING PAGE — NO CHECKOUT / ESCROW LANGUAGE
//
//  The landing page hero slides are the first thing users see. They MUST
//  reflect the "AI Chief of Staff / Introduction" positioning, NOT
//  "Zero-Friction Checkout" or "Fund service deals into secure escrow".
//
// ###########################################################################

describe('ZERO FEE POLICY: Landing Page Hero Content', () => {
  const source = readFileIfExists('components/sdui/AppView.tsx');

  test('AppView exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! The hero slide that used to say "Zero-Friction Checkout" and  !
   * ! "Fund service deals into secure escrow with one click" was a  !
   * ! massive legal liability. It MUST be gone.                     !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('hero does NOT say "Fund service deals into secure escrow"', () => {
    expect(source).not.toContain('Fund service deals into secure escrow');
  });

  test('hero does NOT say "Zero-Friction Checkout"', () => {
    expect(source).not.toContain('Zero-Friction Checkout');
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! The hero MUST contain "Zero Platform Fees" — this is our key  !
   * ! differentiator vs. Angi/Houzz/Thumbtack who all charge.     !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('hero contains "Zero Platform Fees" slide', () => {
    expect(source).toContain('Zero Platform Fees');
  });
});

// ###########################################################################
//
//  SECTION 6: SHARE PAGE — NO "FUND ESCROW" BUTTON
//
//  When someone receives a shared link, the page must NOT have a
//  "Fund Escrow" button. We are not an escrow service.
//
// ###########################################################################

describe('ZERO FEE POLICY: Share Page', () => {
  const source = readFileIfExists('share/[token]/page.tsx');

  test('share page exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  test('does NOT have a "Fund Escrow" button', () => {
    expect(source).not.toContain('Fund Escrow');
  });

  test('does NOT say "Start Shopping" (consumer language)', () => {
    expect(source).not.toContain('Start Shopping');
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! The share page CTA should reflect B2B/procurement positioning. !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('CTA says "Start a Project"', () => {
    expect(source).toContain('Start a Project');
  });
});

// ###########################################################################
//
//  SECTION 7: CHAT WELCOME — "AI CHIEF OF STAFF" POSITIONING
//
//  The first thing a new user sees in chat must identify us as a B2B
//  procurement intelligence tool, not a consumer shopping assistant.
//
// ###########################################################################

describe('ZERO FEE POLICY: Chat Welcome Message', () => {
  const source = readFileIfExists('components/ChatMessages.tsx');

  test('ChatMessages exists', () => {
    expect(source.length).toBeGreaterThan(0);
  });

  /**
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   * ! "Hi, I'm Annie! I'm your AI shopping assistant" is the OLD    !
   * ! consumer positioning. The new positioning is B2B procurement. !
   * !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   */
  test('does NOT use old "Annie" consumer branding', () => {
    expect(source).not.toContain("Hi, I'm Annie");
    expect(source).not.toContain("Hi, I&apos;m Annie");
  });

  test('does NOT say "AI shopping assistant" (consumer language)', () => {
    expect(source).not.toContain('AI shopping assistant');
  });

  test('uses "Chief of Staff" or "procurement" positioning', () => {
    const lower = source.toLowerCase();
    const hasProcurement = lower.includes('procurement');
    const hasChiefOfStaff = lower.includes('chief of staff');
    expect(hasProcurement || hasChiefOfStaff).toBe(true);
  });
});
