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
  isValidBlockType,
  isValidActionIntent,
  isValidValueVector,
  validateUISchema,
  getMinimumViableRow,
} from '../sdui/types';
import type {
  UISchema,
  UISchemaUpdatedEvent,
  ProductImageBlock,
  PriceBlockData,
  DataGridBlock,
  FeatureListBlock,
  BadgeListBlock,
  MarkdownTextBlock,
  TimelineBlock,
  MessageListBlock,
  ChoiceFactorFormBlock,
  ActionRowBlock,
  ReceiptUploaderBlock,
  WalletLedgerBlock,
  EscrowStatusBlock,
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

  test('BLOCK_TYPES has 13 types', () => {
    expect(BLOCK_TYPES).toHaveLength(13);
  });

  test('ACTION_INTENTS has 8 intents', () => {
    expect(ACTION_INTENTS).toHaveLength(8);
    expect(ACTION_INTENTS).toContain('outbound_affiliate');
    expect(ACTION_INTENTS).toContain('claim_swap');
    expect(ACTION_INTENTS).toContain('fund_escrow');
    expect(ACTION_INTENTS).toContain('send_tip');
    expect(ACTION_INTENTS).toContain('contact_vendor');
    expect(ACTION_INTENTS).toContain('view_all_bids');
    expect(ACTION_INTENTS).toContain('view_raw');
    expect(ACTION_INTENTS).toContain('edit_request');
  });

  test('VALUE_VECTORS has 5 vectors', () => {
    expect(VALUE_VECTORS).toHaveLength(5);
    expect(VALUE_VECTORS).toContain('unit_price');
    expect(VALUE_VECTORS).toContain('safety');
    expect(VALUE_VECTORS).toContain('speed');
    expect(VALUE_VECTORS).toContain('reliability');
    expect(VALUE_VECTORS).toContain('durability');
  });

  test('STATE_DRIVEN_BLOCKS has 3 types', () => {
    expect(STATE_DRIVEN_BLOCKS).toHaveLength(3);
    expect(STATE_DRIVEN_BLOCKS).toContain('ReceiptUploader');
    expect(STATE_DRIVEN_BLOCKS).toContain('WalletLedger');
    expect(STATE_DRIVEN_BLOCKS).toContain('EscrowStatus');
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
  test('accepts all 8 intents', () => {
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

// =========================================================================
// Block Type Shapes
// =========================================================================

describe('Block Type Shapes', () => {
  test('ProductImage shape', () => {
    const block: ProductImageBlock = { type: 'ProductImage', url: 'https://img.com/a.jpg', alt: 'Eggs' };
    expect(block.type).toBe('ProductImage');
    expect(block.url).toBe('https://img.com/a.jpg');
  });

  test('PriceBlock with null amount (quote-based)', () => {
    const block: PriceBlockData = { type: 'PriceBlock', amount: null, currency: 'USD', label: 'Request Quote' };
    expect(block.amount).toBeNull();
  });

  test('PriceBlock with zero amount (free)', () => {
    const block: PriceBlockData = { type: 'PriceBlock', amount: 0, currency: 'USD', label: 'Free' };
    expect(block.amount).toBe(0);
  });

  test('DataGrid with items', () => {
    const block: DataGridBlock = {
      type: 'DataGrid',
      items: [{ key: 'Origin', value: 'SAN' }, { key: 'Dest', value: 'ASE' }],
    };
    expect(block.items).toHaveLength(2);
  });

  test('FeatureList with features', () => {
    const block: FeatureListBlock = { type: 'FeatureList', features: ['Organic', 'Non-GMO'] };
    expect(block.features).toContain('Organic');
  });

  test('BadgeList with source_refs (provenance)', () => {
    const block: BadgeListBlock = {
      type: 'BadgeList',
      tags: ['Safest Jet'],
      source_refs: ['safety_cert_123'],
    };
    expect(block.source_refs).toEqual(['safety_cert_123']);
  });

  test('MarkdownText with content', () => {
    const block: MarkdownTextBlock = { type: 'MarkdownText', content: '**Bold text**' };
    expect(block.content).toContain('Bold');
  });

  test('Timeline with steps', () => {
    const block: TimelineBlock = {
      type: 'Timeline',
      steps: [
        { label: 'Sourcing', status: 'done' },
        { label: 'Comparing', status: 'active' },
        { label: 'Funded', status: 'pending' },
      ],
    };
    expect(block.steps).toHaveLength(3);
    expect(block.steps[1].status).toBe('active');
  });

  test('MessageList with messages', () => {
    const block: MessageListBlock = {
      type: 'MessageList',
      messages: [
        { sender: 'user', text: 'I need eggs' },
        { sender: 'assistant', text: 'Found some options!' },
      ],
    };
    expect(block.messages).toHaveLength(2);
  });

  test('ChoiceFactorForm with factors', () => {
    const block: ChoiceFactorFormBlock = {
      type: 'ChoiceFactorForm',
      factors: [{ name: 'brand', label: 'Brand', type: 'text' }],
    };
    expect(block.factors).toHaveLength(1);
  });

  test('ActionRow with actions', () => {
    const block: ActionRowBlock = {
      type: 'ActionRow',
      actions: [
        { label: 'Buy on Amazon', intent: 'outbound_affiliate', bid_id: '123', url: 'https://amazon.com/p' },
        { label: 'Leave a Tip', intent: 'send_tip', amount: 5 },
      ],
    };
    expect(block.actions).toHaveLength(2);
    expect(block.actions[0].bid_id).toBe('123');
    expect(block.actions[1].amount).toBe(5);
  });

  test('ReceiptUploader with campaign_id', () => {
    const block: ReceiptUploaderBlock = { type: 'ReceiptUploader', campaign_id: 'camp_123' };
    expect(block.campaign_id).toBe('camp_123');
  });

  test('WalletLedger (no fields)', () => {
    const block: WalletLedgerBlock = { type: 'WalletLedger' };
    expect(block.type).toBe('WalletLedger');
  });

  test('EscrowStatus with deal_id', () => {
    const block: EscrowStatusBlock = { type: 'EscrowStatus', deal_id: 'deal_456' };
    expect(block.deal_id).toBe('deal_456');
  });
});

// =========================================================================
// SSE Event Shape
// =========================================================================

describe('UISchemaUpdatedEvent', () => {
  test('conforms to spec shape', () => {
    const schema: UISchema = {
      version: 2,
      layout: 'ROW_COMPACT',
      blocks: [{ type: 'MarkdownText', content: '**Updated**' }],
    };
    const event: UISchemaUpdatedEvent = {
      entity_type: 'row',
      entity_id: 42,
      schema,
      version: 2,
      trigger: 'search_complete',
    };
    expect(event.entity_type).toBe('row');
    expect(event.entity_id).toBe(42);
    expect(event.schema.version).toBe(2);
    expect(event.trigger).toBe('search_complete');
  });

  test('project entity type', () => {
    const event: UISchemaUpdatedEvent = {
      entity_type: 'project',
      entity_id: 1,
      schema: getMinimumViableRow(),
      version: 1,
      trigger: 'first_item_added',
    };
    expect(event.entity_type).toBe('project');
  });
});

// =========================================================================
// Scenario-Level Validation
// =========================================================================

describe('Schema Scenarios', () => {
  test('grocery comparison schema roundtrip', () => {
    const raw = {
      version: 1,
      layout: 'ROW_MEDIA_LEFT',
      value_vector: 'unit_price',
      blocks: [
        { type: 'ProductImage', url: 'https://img.com/eggs.jpg', alt: 'Eggs' },
        { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
        { type: 'BadgeList', tags: ['Sourcing', 'Kroger', 'Pop Swap'] },
        { type: 'ActionRow', actions: [{ label: 'View Deal', intent: 'outbound_affiliate', bid_id: '100' }] },
      ],
    };
    const parsed = validateUISchema(JSON.parse(JSON.stringify(raw)));
    expect(parsed).not.toBeNull();
    expect(parsed!.layout).toBe('ROW_MEDIA_LEFT');
    expect(parsed!.value_vector).toBe('unit_price');
    expect(parsed!.blocks).toHaveLength(4);
  });

  test('jet charter timeline schema roundtrip', () => {
    const raw = {
      version: 1,
      layout: 'ROW_TIMELINE',
      value_vector: 'safety',
      blocks: [
        { type: 'DataGrid', items: [{ key: 'Origin', value: 'SAN' }, { key: 'Dest', value: 'ASE' }, { key: 'Pax', value: '4' }] },
        { type: 'BadgeList', tags: ['Wyvern Wingman Certified'], source_refs: ['vendor_safety_db_44'] },
        { type: 'Timeline', steps: [{ label: 'Sourcing', status: 'done' }, { label: 'Comparing', status: 'active' }] },
        { type: 'ActionRow', actions: [{ label: 'Request Firm Quotes', intent: 'contact_vendor' }] },
      ],
    };
    const parsed = validateUISchema(JSON.parse(JSON.stringify(raw)));
    expect(parsed).not.toBeNull();
    expect(parsed!.layout).toBe('ROW_TIMELINE');
    expect(parsed!.value_vector).toBe('safety');
  });

  test('escrow + tip flow schema', () => {
    const raw = {
      version: 3,
      layout: 'ROW_TIMELINE',
      blocks: [
        { type: 'MarkdownText', content: '**Yacht Charter — Funded**' },
        { type: 'EscrowStatus', deal_id: 'deal_789' },
        { type: 'Timeline', steps: [{ label: 'Funded', status: 'active' }, { label: 'Delivered', status: 'pending' }] },
        { type: 'ActionRow', actions: [{ label: 'Leave a Tip', intent: 'send_tip', amount: 100 }] },
      ],
    };
    const parsed = validateUISchema(raw);
    expect(parsed).not.toBeNull();
    expect(parsed!.version).toBe(3);
    expect(parsed!.blocks.find((b) => b.type === 'EscrowStatus')).toBeDefined();
  });

  test('swap claim + receipt uploader schema', () => {
    const raw = {
      version: 2,
      layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: '**Eggs — Swap Claimed**' },
        { type: 'ReceiptUploader', campaign_id: 'camp_eggs' },
        { type: 'ActionRow', actions: [{ label: 'Undo Claim', intent: 'claim_swap' }] },
      ],
    };
    const parsed = validateUISchema(raw);
    expect(parsed).not.toBeNull();
    expect(parsed!.blocks.find((b) => b.type === 'ReceiptUploader')).toBeDefined();
  });

  test('zero results schema', () => {
    const raw = {
      version: 1,
      layout: 'ROW_COMPACT',
      blocks: [
        { type: 'MarkdownText', content: 'No options found for **Unobtainium**' },
        { type: 'ActionRow', actions: [{ label: 'Edit Request', intent: 'edit_request' }] },
      ],
    };
    const parsed = validateUISchema(raw);
    expect(parsed).not.toBeNull();
    expect(parsed!.blocks).toHaveLength(2);
  });

  test('schema survives JSON.stringify/parse roundtrip', () => {
    const original = getMinimumViableRow('Test Item', 'sourcing');
    const serialized = JSON.stringify(original);
    const deserialized = JSON.parse(serialized);
    const validated = validateUISchema(deserialized);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe(original.layout);
    expect(validated!.blocks).toHaveLength(original.blocks.length);
  });
});
