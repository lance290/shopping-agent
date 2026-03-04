/**
 * SDUI block type shape tests + SSE event + scenario tests.
 * Extracted from sdui-types.test.ts to keep files under 450 lines.
 */
import { describe, test, expect } from 'vitest';
import type {
  UISchema,
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
  UISchemaUpdatedEvent,
} from '../sdui/types';
import { validateUISchema } from '../sdui/types';

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

  test('trigger can be any valid string', () => {
    const event: UISchemaUpdatedEvent = {
      entity_type: 'row',
      entity_id: 1,
      schema: { version: 1, layout: 'ROW_COMPACT', blocks: [] },
      version: 1,
      trigger: 'manual_rebuild',
    };
    expect(event.trigger).toBe('manual_rebuild');
  });
});
