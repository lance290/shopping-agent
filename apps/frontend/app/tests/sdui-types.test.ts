/**
 * Tests for SDUI Type Definitions and Validation (app/sdui/types.ts)
 *
 * Covers:
 * - Type guard functions (isValidLayoutToken, isValidBlockType, etc.)
 * - validateUISchema() — valid/invalid/edge cases
 * - getMinimumViableRow() fallback
 * - Constants consistency (LAYOUT_TOKENS, BLOCK_TYPES, ACTION_INTENTS, LIMITS)
 * - Schema validation with all 13 block types
 * - Unknown block stripping
 * - Block limit enforcement
 * - SSE event type compatibility
 */

import { describe, test, expect } from 'vitest';
import {
  LAYOUT_TOKENS,
  BLOCK_TYPES,
  ACTION_INTENTS,
  VALUE_VECTORS,
  STATE_DRIVEN_BLOCKS,
  LIMITS,
  isValidLayoutToken,
  validateUISchema,
  getMinimumViableRow,
  isValidBlockType,
  isValidActionIntent,
  isValidValueVector,
} from '../sdui/types';
import type {
  MarkdownTextBlock,
  BadgeListBlock,
  ActionRowBlock,
} from '../sdui/types';

// =========================================================================
// Constants
// =========================================================================

describe('SDUI Constants', () => {
  test('LAYOUT_TOKENS has 3 tokens', () => {
    expect(LAYOUT_TOKENS).toHaveLength(3);
    expect(LAYOUT_TOKENS).toContain('ROW_COMPACT');
    expect(LAYOUT_TOKENS).toContain('ROW_MEDIA_LEFT');
    expect(LAYOUT_TOKENS).toContain('ROW_TIMELINE');
  });

  test('BLOCK_TYPES has 12 types', () => {
    expect(BLOCK_TYPES).toHaveLength(12);
  });

  test('ACTION_INTENTS has 10 intents', () => {
    expect(ACTION_INTENTS).toHaveLength(10);
    expect(ACTION_INTENTS).toContain('outbound_affiliate');
    expect(ACTION_INTENTS).toContain('claim_swap');
    expect(ACTION_INTENTS).toContain('send_tip');
    expect(ACTION_INTENTS).toContain('contact_vendor');
    expect(ACTION_INTENTS).toContain('view_all_bids');
    expect(ACTION_INTENTS).toContain('view_raw');
    expect(ACTION_INTENTS).toContain('edit_request');
    expect(ACTION_INTENTS).toContain('mark_terms_agreed');
    expect(ACTION_INTENTS).toContain('continue_negotiation');
    expect(ACTION_INTENTS).toContain('invite_vendor_connect');
  });

  test('VALUE_VECTORS has 5 vectors', () => {
    expect(VALUE_VECTORS).toHaveLength(5);
    expect(VALUE_VECTORS).toContain('unit_price');
    expect(VALUE_VECTORS).toContain('safety');
    expect(VALUE_VECTORS).toContain('speed');
    expect(VALUE_VECTORS).toContain('reliability');
    expect(VALUE_VECTORS).toContain('durability');
  });

  test('STATE_DRIVEN_BLOCKS has 2 types', () => {
    expect(STATE_DRIVEN_BLOCKS).toHaveLength(2);
    expect(STATE_DRIVEN_BLOCKS).toContain('ReceiptUploader');
    expect(STATE_DRIVEN_BLOCKS).toContain('WalletLedger');
    expect(STATE_DRIVEN_BLOCKS).not.toContain('EscrowStatus');
  });

  test('LIMITS match spec', () => {
    expect(LIMITS.MAX_BLOCKS_PER_ROW).toBe(8);
    expect(LIMITS.MAX_MARKDOWN_LENGTH).toBe(500);
    expect(LIMITS.MAX_DATAGRID_ITEMS).toBe(12);
    expect(LIMITS.MAX_ACTION_ROW_ACTIONS).toBe(3);
    expect(LIMITS.GROCERY_BID_CAP).toBe(5);
    expect(LIMITS.RETAIL_BID_CAP).toBe(30);
  });
});

// =========================================================================
// Type Guards
// =========================================================================

describe('isValidLayoutToken', () => {
  test('accepts valid tokens', () => {
    expect(isValidLayoutToken('ROW_COMPACT')).toBe(true);
    expect(isValidLayoutToken('ROW_MEDIA_LEFT')).toBe(true);
    expect(isValidLayoutToken('ROW_TIMELINE')).toBe(true);
  });

  test('rejects invalid tokens', () => {
    expect(isValidLayoutToken('INVALID')).toBe(false);
    expect(isValidLayoutToken('')).toBe(false);
    expect(isValidLayoutToken('row_compact')).toBe(false); // case sensitive
  });
});

describe('isValidBlockType', () => {
  test('accepts all 13 block types', () => {
    for (const bt of BLOCK_TYPES) {
      expect(isValidBlockType(bt)).toBe(true);
    }
  });

  test('rejects unknown types', () => {
    expect(isValidBlockType('FooWidget')).toBe(false);
    expect(isValidBlockType('')).toBe(false);
    expect(isValidBlockType('productimage')).toBe(false); // case sensitive
  });
});

describe('isValidActionIntent', () => {
  test('accepts all 11 intents', () => {
    for (const ai of ACTION_INTENTS) {
      expect(isValidActionIntent(ai)).toBe(true);
    }
  });

  test('rejects unknown intents', () => {
    expect(isValidActionIntent('buy_now')).toBe(false);
    expect(isValidActionIntent('')).toBe(false);
  });
});

describe('isValidValueVector', () => {
  test('accepts all 5 vectors', () => {
    for (const vv of VALUE_VECTORS) {
      expect(isValidValueVector(vv)).toBe(true);
    }
  });

  test('rejects unknown vectors', () => {
    expect(isValidValueVector('price')).toBe(false);
    expect(isValidValueVector('')).toBe(false);
  });
});

// =========================================================================
// validateUISchema
// =========================================================================

describe('validateUISchema', () => {
  test('validates minimal valid schema', () => {
    const data = { version: 1, layout: 'ROW_COMPACT', blocks: [] };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.version).toBe(1);
    expect(result!.layout).toBe('ROW_COMPACT');
    expect(result!.blocks).toEqual([]);
  });

  test('validates schema with blocks', () => {
    const data = {
      version: 1,
      layout: 'ROW_MEDIA_LEFT',
      value_vector: 'unit_price',
      blocks: [
        { type: 'ProductImage', url: 'https://img.com/a.jpg', alt: 'Eggs' },
        { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
        { type: 'BadgeList', tags: ['Organic', 'Pop Swap'] },
        { type: 'ActionRow', actions: [{ label: 'Buy', intent: 'outbound_affiliate' }] },
      ],
    };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.blocks).toHaveLength(4);
    expect(result!.value_vector).toBe('unit_price');
  });

  test('rejects null', () => {
    expect(validateUISchema(null)).toBeNull();
  });

  test('rejects undefined', () => {
    expect(validateUISchema(undefined)).toBeNull();
  });

  test('rejects non-object', () => {
    expect(validateUISchema('string')).toBeNull();
    expect(validateUISchema(42)).toBeNull();
    expect(validateUISchema(true)).toBeNull();
  });

  test('rejects missing version', () => {
    expect(validateUISchema({ layout: 'ROW_COMPACT', blocks: [] })).toBeNull();
  });

  test('rejects non-number version', () => {
    expect(validateUISchema({ version: 'one', layout: 'ROW_COMPACT', blocks: [] })).toBeNull();
  });

  test('rejects missing layout', () => {
    expect(validateUISchema({ version: 1, blocks: [] })).toBeNull();
  });

  test('rejects invalid layout', () => {
    expect(validateUISchema({ version: 1, layout: 'INVALID', blocks: [] })).toBeNull();
  });

  test('rejects missing blocks', () => {
    expect(validateUISchema({ version: 1, layout: 'ROW_COMPACT' })).toBeNull();
  });

  test('strips unknown block types', () => {
    const data = {
      version: 1,
      layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: 'Hello' },
        { type: 'FooWidget', data: 42 },
        { type: 'ActionRow', actions: [] },
      ],
    };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.blocks).toHaveLength(2);
    expect(result!.blocks[0].type).toBe('MarkdownText');
    expect(result!.blocks[1].type).toBe('ActionRow');
  });

  test('enforces max blocks limit', () => {
    const blocks = Array.from({ length: 12 }, (_, i) => ({
      type: 'MarkdownText',
      content: `Block ${i}`,
    }));
    const data = { version: 1, layout: 'ROW_COMPACT', blocks };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.blocks.length).toBeLessThanOrEqual(LIMITS.MAX_BLOCKS_PER_ROW);
  });

  test('sets invalid value_vector to null', () => {
    const data = {
      version: 1,
      layout: 'ROW_COMPACT',
      value_vector: 'nonexistent',
      blocks: [],
    };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.value_vector).toBeNull();
  });

  test('preserves valid value_vector', () => {
    const data = {
      version: 1,
      layout: 'ROW_COMPACT',
      value_vector: 'safety',
      blocks: [],
    };
    const result = validateUISchema(data);
    expect(result!.value_vector).toBe('safety');
  });

  test('preserves value_rationale_refs', () => {
    const data = {
      version: 1,
      layout: 'ROW_COMPACT',
      value_rationale_refs: ['ref_1', 'ref_2'],
      blocks: [],
    };
    const result = validateUISchema(data);
    expect(result!.value_rationale_refs).toEqual(['ref_1', 'ref_2']);
  });

  test('handles blocks with null entries', () => {
    const data = {
      version: 1,
      layout: 'ROW_COMPACT',
      blocks: [null, { type: 'MarkdownText', content: 'Hi' }, undefined],
    };
    const result = validateUISchema(data);
    expect(result).not.toBeNull();
    expect(result!.blocks).toHaveLength(1);
  });
});

// =========================================================================
// getMinimumViableRow
// =========================================================================

describe('getMinimumViableRow', () => {
  test('returns valid schema with defaults', () => {
    const mvr = getMinimumViableRow();
    expect(mvr.version).toBe(1);
    expect(mvr.layout).toBe('ROW_COMPACT');
    expect(mvr.blocks).toHaveLength(3);
    expect(mvr.blocks[0].type).toBe('MarkdownText');
    expect((mvr.blocks[0] as MarkdownTextBlock).content).toContain('Untitled');
  });

  test('uses custom title and status', () => {
    const mvr = getMinimumViableRow('Organic Eggs', 'searching');
    expect((mvr.blocks[0] as MarkdownTextBlock).content).toContain('Organic Eggs');
    expect((mvr.blocks[1] as BadgeListBlock).tags).toContain('searching');
  });

  test('always has ActionRow with view_raw', () => {
    const mvr = getMinimumViableRow();
    const actionRow = mvr.blocks.find((b) => b.type === 'ActionRow') as ActionRowBlock;
    expect(actionRow).toBeDefined();
    expect(actionRow.actions[0].intent).toBe('view_raw');
  });

  test('validates via validateUISchema', () => {
    const mvr = getMinimumViableRow('Test', 'sourcing');
    const validated = validateUISchema(mvr);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe('ROW_COMPACT');
  });
});

// Block Type Shapes + UISchemaUpdatedEvent + Schema Scenarios extracted to sdui-types-blocks.test.ts
