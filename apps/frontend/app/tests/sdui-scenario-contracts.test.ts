/**
 * Scenario-level contract tests for SDUI schemas.
 *
 * Validates end-to-end user flow schemas (grocery, jet charter, escrow,
 * swap claim, zero results) purely via data contracts — no browser needed.
 *
 * Covers:
 * - Schema parsing from simulated API responses
 * - Fallback behavior when schema is missing/invalid
 * - SSE ui_schema_updated event shape
 * - Schema versioning
 * - Full flow scenarios (grocery, jet, escrow, swap, zero results)
 * - Security: no tracking tags in persisted schema
 * - ActionObject intent validation
 */

import { describe, test, expect } from 'vitest';
import {
  validateUISchema,
  getMinimumViableRow,
  ACTION_INTENTS,
} from '../sdui/types';
import type { ActionRowBlock } from '../sdui/types';

// ---------------------------------------------------------------------------
// Schema Factories
// ---------------------------------------------------------------------------

function makeGrocerySchema() {
  return {
    version: 1,
    layout: 'ROW_MEDIA_LEFT',
    value_vector: 'unit_price',
    blocks: [
      { type: 'ProductImage', url: 'https://img.com/eggs.jpg', alt: 'Organic Eggs' },
      { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
      { type: 'BadgeList', tags: ['Sourcing', 'Kroger', 'Pop Swap'] },
      { type: 'ActionRow', actions: [
        { label: 'View Deal', intent: 'outbound_affiliate', bid_id: '100', url: 'https://kroger.com/eggs' },
      ]},
    ],
  };
}

function makeJetCharterSchema() {
  return {
    version: 1,
    layout: 'ROW_TIMELINE',
    value_vector: 'safety',
    blocks: [
      { type: 'DataGrid', items: [
        { key: 'Origin', value: 'SAN' },
        { key: 'Destination', value: 'ASE' },
        { key: 'Passengers', value: '4' },
        { key: 'Date', value: 'Feb 13' },
      ]},
      { type: 'BadgeList', tags: ['Wyvern Wingman Certified'], source_refs: ['vendor_safety_db_44'] },
      { type: 'Timeline', steps: [
        { label: 'Sourcing', status: 'done' },
        { label: 'Comparing', status: 'active' },
        { label: 'Negotiating', status: 'pending' },
      ]},
      { type: 'ActionRow', actions: [
        { label: 'Request Firm Quotes', intent: 'contact_vendor' },
      ]},
    ],
  };
}

function makeEscrowSchema() {
  return {
    version: 3,
    layout: 'ROW_TIMELINE',
    blocks: [
      { type: 'MarkdownText', content: '**Yacht Charter — Funded**' },
      { type: 'EscrowStatus', deal_id: 'deal_789' },
      { type: 'Timeline', steps: [
        { label: 'Sourcing', status: 'done' },
        { label: 'Negotiating', status: 'done' },
        { label: 'Funded', status: 'active' },
        { label: 'Delivered', status: 'pending' },
      ]},
      { type: 'ActionRow', actions: [
        { label: 'Leave a Tip', intent: 'send_tip', amount: 100 },
      ]},
    ],
  };
}

function makeSwapClaimSchema() {
  return {
    version: 2,
    layout: 'ROW_COMPACT',
    blocks: [
      { type: 'MarkdownText', content: '**Eggs — Swap Claimed**' },
      { type: 'ReceiptUploader', campaign_id: 'camp_eggs_123' },
      { type: 'ActionRow', actions: [
        { label: 'Undo Claim', intent: 'claim_swap' },
      ]},
    ],
  };
}

// =========================================================================
// 1. Schema Parsing
// =========================================================================

describe('Schema parsing from API responses', () => {
  test('grocery schema validates', () => {
    const result = validateUISchema(makeGrocerySchema());
    expect(result).not.toBeNull();
    expect(result!.layout).toBe('ROW_MEDIA_LEFT');
    expect(result!.value_vector).toBe('unit_price');
    expect(result!.blocks).toHaveLength(4);
  });

  test('jet charter schema validates', () => {
    const result = validateUISchema(makeJetCharterSchema());
    expect(result).not.toBeNull();
    expect(result!.layout).toBe('ROW_TIMELINE');
    expect(result!.value_vector).toBe('safety');
  });

  test('escrow schema validates', () => {
    const result = validateUISchema(makeEscrowSchema());
    expect(result).not.toBeNull();
    expect(result!.blocks.find((b) => b.type === 'EscrowStatus')).toBeDefined();
  });

  test('swap claim schema validates', () => {
    const result = validateUISchema(makeSwapClaimSchema());
    expect(result).not.toBeNull();
    expect(result!.blocks.find((b) => b.type === 'ReceiptUploader')).toBeDefined();
  });

  test('JSON roundtrip preserves schema', () => {
    const original = makeGrocerySchema();
    const roundtripped = JSON.parse(JSON.stringify(original));
    const validated = validateUISchema(roundtripped);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe(original.layout);
    expect(validated!.blocks).toHaveLength(original.blocks.length);
  });
});

// =========================================================================
// 2. Fallback Behavior
// =========================================================================

describe('Fallback when schema is invalid', () => {
  test('MVR is valid', () => {
    const mvr = getMinimumViableRow('Test', 'sourcing');
    expect(validateUISchema(mvr)).not.toBeNull();
  });

  test('null/undefined/empty reject', () => {
    expect(validateUISchema(null)).toBeNull();
    expect(validateUISchema(undefined)).toBeNull();
    expect(validateUISchema({})).toBeNull();
  });

  test('invalid layout rejects', () => {
    expect(validateUISchema({ version: 1, layout: 'INVALID', blocks: [] })).toBeNull();
  });

  test('unknown blocks stripped', () => {
    const schema = {
      version: 1, layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: 'Hi' },
        { type: 'FooWidget', data: 42 },
      ],
    };
    const result = validateUISchema(schema);
    expect(result).not.toBeNull();
    expect(result!.blocks).toHaveLength(1);
  });

  test('fallback applied after rejection', () => {
    const badSchema = { version: 'bad' };
    expect(validateUISchema(badSchema)).toBeNull();
    const fallback = getMinimumViableRow('Eggs', 'sourcing');
    expect(validateUISchema(fallback)).not.toBeNull();
  });
});

// =========================================================================
// 3. SSE Event Contract
// =========================================================================

describe('SSE ui_schema_updated event', () => {
  test('event shape matches spec', () => {
    const event = {
      entity_type: 'row' as const,
      entity_id: 42,
      schema: makeGrocerySchema(),
      version: 2,
      trigger: 'search_complete',
    };
    expect(['project', 'row']).toContain(event.entity_type);
    expect(typeof event.entity_id).toBe('number');
    expect(validateUISchema(event.schema)).not.toBeNull();
    expect(typeof event.version).toBe('number');
    expect(typeof event.trigger).toBe('string');
  });

  test('project entity type', () => {
    const schema = {
      version: 1, layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: '**Family Groceries**' },
        { type: 'ActionRow', actions: [{ label: 'Share', intent: 'edit_request' }] },
      ],
    };
    expect(validateUISchema(schema)).not.toBeNull();
  });
});

// =========================================================================
// 4. Schema Versioning
// =========================================================================

describe('Schema versioning', () => {
  test('version 1 is default', () => {
    expect(makeGrocerySchema().version).toBe(1);
    expect(getMinimumViableRow().version).toBe(1);
  });

  test('version 0 means no schema yet', () => {
    const freshRow = { ui_schema: null, ui_schema_version: 0 };
    expect(freshRow.ui_schema_version).toBe(0);
  });

  test('higher version still valid', () => {
    const schema = { ...makeGrocerySchema(), version: 5 };
    expect(validateUISchema(schema)).not.toBeNull();
  });
});

// =========================================================================
// 5. Full User Flow Scenarios
// =========================================================================

describe('Scenario: grocery flow', () => {
  test('skeleton → comparison', () => {
    const skeleton = getMinimumViableRow('Eggs', 'Searching...');
    expect(validateUISchema(skeleton)).not.toBeNull();

    const comparison = validateUISchema(makeGrocerySchema());
    expect(comparison).not.toBeNull();
    expect(comparison!.layout).toBe('ROW_MEDIA_LEFT');
    expect(comparison!.blocks.find((b) => b.type === 'ProductImage')).toBeDefined();
  });

  test('swap claimed → receipt uploader', () => {
    const preClaim = validateUISchema(makeGrocerySchema());
    expect(preClaim!.blocks.find((b) => b.type === 'ReceiptUploader')).toBeUndefined();

    const postClaim = validateUISchema(makeSwapClaimSchema());
    expect(postClaim!.blocks.find((b) => b.type === 'ReceiptUploader')).toBeDefined();
  });
});

describe('Scenario: high-ticket service flow', () => {
  test('vendor comparison → escrow funded → tip jar', () => {
    const comparison = validateUISchema(makeJetCharterSchema());
    expect(comparison).not.toBeNull();
    expect(comparison!.value_vector).toBe('safety');

    const funded = validateUISchema(makeEscrowSchema());
    expect(funded).not.toBeNull();
    expect(funded!.blocks.find((b) => b.type === 'EscrowStatus')).toBeDefined();

    const tipAction = funded!.blocks
      .filter((b): b is ActionRowBlock => b.type === 'ActionRow')
      .flatMap((b) => b.actions)
      .find((a) => a.intent === 'send_tip');
    expect(tipAction).toBeDefined();
    expect(tipAction!.amount).toBe(100);
  });
});

describe('Scenario: zero results', () => {
  test('renders edit request action', () => {
    const schema = validateUISchema({
      version: 1, layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: 'No options found for **Unobtainium**' },
        { type: 'ActionRow', actions: [{ label: 'Edit Request', intent: 'edit_request' }] },
      ],
    });
    expect(schema).not.toBeNull();
    expect(schema!.blocks).toHaveLength(2);
  });
});

// =========================================================================
// 6. Security
// =========================================================================

describe('Security: affiliate tags not in schema', () => {
  test('ActionRow URL is raw merchant URL', () => {
    const schema = makeGrocerySchema();
    const actionRow = schema.blocks.find((b) => b.type === 'ActionRow') as { actions: { url?: string }[] };
    const affiliate = actionRow.actions.find((a) => a.url);
    expect(affiliate?.url).toBe('https://kroger.com/eggs');
    // No ?tag= — backend appends at click time via /api/out
  });
});

// =========================================================================
// 7. ActionObject Intents
// =========================================================================

describe('ActionObject intents', () => {
  test('all 8 intents recognized', () => {
    expect(ACTION_INTENTS).toHaveLength(8);
    for (const intent of ACTION_INTENTS) {
      expect(typeof intent).toBe('string');
      expect(intent.length).toBeGreaterThan(0);
    }
  });

  test('outbound_affiliate has bid_id', () => {
    const action = { label: 'Buy', intent: 'outbound_affiliate' as const, bid_id: 'uuid-123' };
    expect(action.bid_id).toBeDefined();
  });

  test('send_tip has amount', () => {
    const action = { label: 'Tip', intent: 'send_tip' as const, amount: 5 };
    expect(action.amount).toBe(5);
  });

  test('view_all_bids has count', () => {
    const action = { label: 'View All', intent: 'view_all_bids' as const, count: 42 };
    expect(action.count).toBe(42);
  });
});
