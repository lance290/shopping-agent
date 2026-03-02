/**
 * Tests for the SDUI Demo Page schemas.
 *
 * Validates that all 9 sample schemas used in /sdui-demo are valid
 * and render correctly through validateUISchema.
 */

import { describe, test, expect } from 'vitest';
import { validateUISchema } from '../sdui/types';

const GROCERY_SCHEMA = {
  version: 1,
  layout: 'ROW_MEDIA_LEFT',
  value_vector: 'unit_price',
  blocks: [
    { type: 'ProductImage', url: 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=200', alt: 'Organic Eggs' },
    { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
    { type: 'BadgeList', tags: ['Organic', 'Kroger', 'Pop Swap'] },
    { type: 'FeatureList', features: ['Free Range', 'Non-GMO', 'USDA Organic'] },
    { type: 'ActionRow', actions: [
      { label: 'View Deal', intent: 'outbound_affiliate', bid_id: '100', url: 'https://kroger.com/eggs' },
      { label: 'Claim $1.00 Swap', intent: 'claim_swap' },
    ]},
  ],
};

const JET_CHARTER_SCHEMA = {
  version: 1,
  layout: 'ROW_TIMELINE',
  value_vector: 'safety',
  blocks: [
    { type: 'MarkdownText', content: '**Private Jet Charter — SAN to ASE**' },
    { type: 'DataGrid', items: [
      { key: 'Origin', value: 'San Diego (SAN)' },
      { key: 'Destination', value: 'Aspen (ASE)' },
      { key: 'Passengers', value: '4' },
      { key: 'Date', value: 'February 13, 2026' },
      { key: 'Aircraft', value: 'Light Jet' },
    ]},
    { type: 'BadgeList', tags: ['Wyvern Wingman Certified', 'IS-BAO Stage 3'], source_refs: ['safety_cert_44', 'safety_cert_45'] },
    { type: 'Timeline', steps: [
      { label: 'Sourcing', status: 'done' },
      { label: 'Comparing', status: 'active' },
      { label: 'Negotiating', status: 'pending' },
      { label: 'Funded', status: 'pending' },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Request Firm Quotes', intent: 'contact_vendor' },
      { label: 'Leave a Tip', intent: 'send_tip', amount: 100 },
    ]},
  ],
};

const ESCROW_SCHEMA = {
  version: 3,
  layout: 'ROW_TIMELINE',
  blocks: [
    { type: 'MarkdownText', content: '**Yacht Charter — Mediterranean**' },
    { type: 'PriceBlock', amount: 45000, currency: 'USD', label: 'Escrow Amount' },
    { type: 'EscrowStatus', deal_id: 'deal_789' },
    { type: 'Timeline', steps: [
      { label: 'Sourcing', status: 'done' },
      { label: 'Negotiating', status: 'done' },
      { label: 'Funded', status: 'active' },
      { label: 'In Transit', status: 'pending' },
      { label: 'Delivered', status: 'pending' },
    ]},
    { type: 'ActionRow', actions: [{ label: 'Leave a Tip', intent: 'send_tip', amount: 500 }] },
  ],
};

const SWAP_CLAIM_SCHEMA = {
  version: 2,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Eggs — Pop Swap Claimed!**' },
    { type: 'BadgeList', tags: ['Pop Swap', 'Pending Receipt'] },
    { type: 'ReceiptUploader', campaign_id: 'camp_eggs_spring26' },
    { type: 'ActionRow', actions: [{ label: 'Undo Claim', intent: 'claim_swap' }] },
  ],
};

const COMPACT_TEXT_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Running Shoes**' },
    { type: 'PriceBlock', amount: 89.99, currency: 'USD', label: 'From' },
    { type: 'BadgeList', tags: ['Amazon', 'Nike.com', 'eBay', 'Google Shopping'] },
    { type: 'ActionRow', actions: [
      { label: 'View on Amazon', intent: 'outbound_affiliate', bid_id: '200', url: 'https://amazon.com/shoes' },
      { label: 'View All (12)', intent: 'view_all_bids', count: 12 },
    ]},
  ],
};

const CHOICE_FACTOR_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Custom Engagement Ring**' },
    { type: 'ChoiceFactorForm', factors: [
      { name: 'budget', label: 'Budget Range', type: 'select', options: ['$5k-$10k', '$10k-$25k'], required: true },
    ]},
    { type: 'ActionRow', actions: [{ label: 'Find Options', intent: 'edit_request' }] },
  ],
};

const ZERO_RESULTS_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: 'No options found for **Unobtainium**' },
    { type: 'ActionRow', actions: [{ label: 'Edit Request', intent: 'edit_request' }] },
  ],
};

const WALLET_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Your Savings Dashboard**' },
    { type: 'WalletLedger' },
    { type: 'BadgeList', tags: ['3 Swaps Claimed'] },
    { type: 'ActionRow', actions: [{ label: 'Share & Earn 30%', intent: 'edit_request' }] },
  ],
};

const MESSAGE_HISTORY_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Vendor Conversation — NetJets**' },
    { type: 'MessageList', messages: [
      { sender: 'You', text: 'Looking for a light jet SAN to ASE' },
      { sender: 'NetJets', text: 'We can offer a Citation CJ3+ for $18,500' },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Accept Quote', intent: 'fund_escrow', amount: 18500 },
      { label: 'Counter Offer', intent: 'contact_vendor' },
    ]},
  ],
};

describe('SDUI Demo Page Schemas', () => {
  const schemas = [
    { name: 'Grocery', schema: GROCERY_SCHEMA },
    { name: 'Jet Charter', schema: JET_CHARTER_SCHEMA },
    { name: 'Escrow', schema: ESCROW_SCHEMA },
    { name: 'Swap Claim', schema: SWAP_CLAIM_SCHEMA },
    { name: 'Compact Text', schema: COMPACT_TEXT_SCHEMA },
    { name: 'Choice Factors', schema: CHOICE_FACTOR_SCHEMA },
    { name: 'Zero Results', schema: ZERO_RESULTS_SCHEMA },
    { name: 'Wallet', schema: WALLET_SCHEMA },
    { name: 'Message History', schema: MESSAGE_HISTORY_SCHEMA },
  ];

  for (const { name, schema } of schemas) {
    test(`${name} schema validates`, () => {
      const result = validateUISchema(schema);
      expect(result).not.toBeNull();
      expect(result!.version).toBeGreaterThanOrEqual(1);
      expect(result!.blocks.length).toBeGreaterThan(0);
    });

    test(`${name} schema survives JSON roundtrip`, () => {
      const json = JSON.stringify(schema);
      const parsed = JSON.parse(json);
      const result = validateUISchema(parsed);
      expect(result).not.toBeNull();
    });
  }

  test('all 9 schemas use valid layout tokens', () => {
    for (const { schema } of schemas) {
      expect(['ROW_COMPACT', 'ROW_MEDIA_LEFT', 'ROW_TIMELINE']).toContain(schema.layout);
    }
  });

  test('every schema has at least one ActionRow', () => {
    for (const { name, schema } of schemas) {
      const hasActionRow = schema.blocks.some((b: any) => b.type === 'ActionRow');
      expect(hasActionRow).toBe(true);
    }
  });

  test('all 13 block types are represented across demos', () => {
    const allTypes = new Set<string>();
    for (const { schema } of schemas) {
      for (const block of schema.blocks) {
        allTypes.add((block as any).type);
      }
    }
    expect(allTypes).toContain('ProductImage');
    expect(allTypes).toContain('PriceBlock');
    expect(allTypes).toContain('DataGrid');
    expect(allTypes).toContain('FeatureList');
    expect(allTypes).toContain('BadgeList');
    expect(allTypes).toContain('MarkdownText');
    expect(allTypes).toContain('Timeline');
    expect(allTypes).toContain('MessageList');
    expect(allTypes).toContain('ChoiceFactorForm');
    expect(allTypes).toContain('ActionRow');
    expect(allTypes).toContain('ReceiptUploader');
    expect(allTypes).toContain('WalletLedger');
    expect(allTypes).toContain('EscrowStatus');
  });
});
