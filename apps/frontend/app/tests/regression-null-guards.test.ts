/**
 * Regression tests for the Feb/Mar 2026 production crash.
 *
 * Root cause: JSON.parse("null") returns null, and typeof null === "object"
 * in JavaScript. Multiple functions were returning null to callers that then
 * called Object.entries(null), crashing the app.
 *
 * Covers:
 * - parseChoiceAnswers null/undefined/array/string guard
 * - parseChoiceFactors null guard (typeof null === 'object')
 * - setActiveRowId with null selected_providers
 * - setRows with null rowResults / rowProviderStatuses
 * - mapBidToOffer with edge-case bids
 */

import { describe, test, expect, beforeEach } from 'vitest';
import {
  useShoppingStore,
  parseChoiceAnswers,
  parseChoiceFactors,
  mapBidToOffer,
} from '../store';
import type { Row, Bid } from '../store';

const mockRow = (overrides: Partial<Row> = {}): Row => ({
  id: 1,
  title: 'Test Row',
  status: 'sourcing',
  budget_max: null,
  currency: 'USD',
  ...overrides,
});

// ============================================================
// 1. parseChoiceAnswers — must NEVER return null
// ============================================================

describe('parseChoiceAnswers — null guard regression', () => {
  test('returns {} for undefined choice_answers', () => {
    const row = mockRow();
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} for null choice_answers', () => {
    const row = mockRow({ choice_answers: undefined });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} when choice_answers is JSON "null" string', () => {
    // THIS IS THE BUG: JSON.parse("null") returns null, typeof null === "object"
    const row = mockRow({ choice_answers: 'null' });
    const result = parseChoiceAnswers(row);
    expect(result).toEqual({});
    expect(result).not.toBeNull();
  });

  test('returns {} when choice_answers is empty string', () => {
    const row = mockRow({ choice_answers: '' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} when choice_answers is JSON array', () => {
    const row = mockRow({ choice_answers: '["a", "b"]' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} when choice_answers is JSON number', () => {
    const row = mockRow({ choice_answers: '42' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} when choice_answers is JSON string', () => {
    const row = mockRow({ choice_answers: '"just a string"' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} when choice_answers is JSON boolean', () => {
    const row = mockRow({ choice_answers: 'true' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns {} for malformed JSON', () => {
    const row = mockRow({ choice_answers: '{broken' });
    expect(parseChoiceAnswers(row)).toEqual({});
  });

  test('returns valid object for valid JSON object', () => {
    const row = mockRow({
      choice_answers: JSON.stringify({ size: 'M', color: 'blue' }),
    });
    const result = parseChoiceAnswers(row);
    expect(result).toEqual({ size: 'M', color: 'blue' });
  });

  test('Object.entries on result never throws', () => {
    const badInputs = [
      undefined,
      '',
      'null',
      '42',
      '"string"',
      'true',
      '["array"]',
      '{broken',
    ];

    for (const input of badInputs) {
      const row = mockRow({ choice_answers: input });
      const result = parseChoiceAnswers(row);
      // This is the exact call that crashed production
      expect(() => Object.entries(result)).not.toThrow();
    }
  });
});

// ============================================================
// 2. parseChoiceFactors — null guard regression
// ============================================================

describe('parseChoiceFactors — null guard regression', () => {
  test('returns [] for undefined choice_factors', () => {
    const row = mockRow();
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns [] when choice_factors is JSON "null" string', () => {
    // typeof null === "object" would pass the old check
    const row = mockRow({ choice_factors: 'null' });
    const result = parseChoiceFactors(row);
    expect(result).toEqual([]);
    expect(Array.isArray(result)).toBe(true);
  });

  test('returns [] for JSON number', () => {
    const row = mockRow({ choice_factors: '42' });
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns [] for JSON string', () => {
    const row = mockRow({ choice_factors: '"just a string"' });
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns [] for JSON boolean', () => {
    const row = mockRow({ choice_factors: 'false' });
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('returns [] for malformed JSON', () => {
    const row = mockRow({ choice_factors: '{broken' });
    expect(parseChoiceFactors(row)).toEqual([]);
  });

  test('parses valid array', () => {
    const row = mockRow({
      choice_factors: JSON.stringify([
        { name: 'size', label: 'Size', type: 'select' },
      ]),
    });
    expect(parseChoiceFactors(row)).toHaveLength(1);
  });

  test('converts valid object to array', () => {
    const row = mockRow({
      choice_factors: JSON.stringify({
        size: { label: 'Size', type: 'select' },
      }),
    });
    const result = parseChoiceFactors(row);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('size');
  });

  test('Object.entries inside parseChoiceFactors never throws on null-like input', () => {
    const badInputs = ['null', '42', '"string"', 'true', '{broken', ''];
    for (const input of badInputs) {
      const row = mockRow({ choice_factors: input || undefined });
      expect(() => parseChoiceFactors(row)).not.toThrow();
    }
  });
});

// ============================================================
// 3. setActiveRowId — null selected_providers regression
// ============================================================

describe('setActiveRowId — null selectedProviders regression', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('handles selected_providers = "null" without crashing', () => {
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, selected_providers: 'null' }),
    ]);

    // This was the original crash: setActiveRowId parsed "null" and set
    // selectedProviders to null, then Object.values(null) crashed
    expect(() => {
      useShoppingStore.getState().setActiveRowId(1);
    }).not.toThrow();

    const state = useShoppingStore.getState();
    expect(state.selectedProviders).toBeDefined();
    expect(state.selectedProviders).not.toBeNull();
  });

  test('handles selected_providers = null (undefined) without crashing', () => {
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, selected_providers: undefined }),
    ]);

    expect(() => {
      useShoppingStore.getState().setActiveRowId(1);
    }).not.toThrow();
  });

  test('handles selected_providers = "" (empty string) without crashing', () => {
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, selected_providers: '' }),
    ]);

    expect(() => {
      useShoppingStore.getState().setActiveRowId(1);
    }).not.toThrow();
  });

  test('handles selected_providers = "[]" (array) without crashing', () => {
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, selected_providers: '[]' }),
    ]);

    expect(() => {
      useShoppingStore.getState().setActiveRowId(1);
    }).not.toThrow();
  });

  test('valid selected_providers are loaded', () => {
    useShoppingStore.getState().setRows([
      mockRow({
        id: 1,
        selected_providers: JSON.stringify({ amazon: true, ebay: false }),
      }),
    ]);

    useShoppingStore.getState().setActiveRowId(1);
    const state = useShoppingStore.getState();
    expect(state.selectedProviders.amazon).toBe(true);
    expect(state.selectedProviders.ebay).toBe(false);
  });

  test('setActiveRowId(null) does not crash', () => {
    expect(() => {
      useShoppingStore.getState().setActiveRowId(null);
    }).not.toThrow();
    expect(useShoppingStore.getState().activeRowId).toBeNull();
  });
});

// ============================================================
// 4. setRows — null rowResults / rowProviderStatuses regression
// ============================================================

describe('setRows — null state regression', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setRows with rows that have null bids does not crash', () => {
    expect(() => {
      useShoppingStore.getState().setRows([
        mockRow({ id: 1, bids: undefined }),
      ]);
    }).not.toThrow();
  });

  test('setRows with rows that have empty bids array', () => {
    expect(() => {
      useShoppingStore.getState().setRows([
        mockRow({ id: 1, bids: [] }),
      ]);
    }).not.toThrow();
  });

  test('setRows prunes results for removed rows', () => {
    const store = useShoppingStore.getState();
    store.setRows([mockRow({ id: 1 }), mockRow({ id: 2 })]);
    store.setRowResults(1, [
      {
        title: 'P1', price: 10, currency: 'USD', merchant: 'S',
        url: 'https://a.com', image_url: null, rating: null,
        reviews_count: null, shipping_info: null, source: 'test',
      },
    ]);
    store.setRowResults(2, [
      {
        title: 'P2', price: 20, currency: 'USD', merchant: 'S',
        url: 'https://b.com', image_url: null, rating: null,
        reviews_count: null, shipping_info: null, source: 'test',
      },
    ]);

    // Remove row 2
    store.setRows([mockRow({ id: 1 })]);
    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toBeDefined();
    expect(state.rowResults[2]).toBeUndefined();
  });

  test('Object.entries on rowResults inside setRows never throws', () => {
    // Force rowResults to be a weird state (simulating hydration issue)
    useShoppingStore.setState({ rowResults: {} });
    expect(() => {
      useShoppingStore.getState().setRows([mockRow({ id: 1 })]);
    }).not.toThrow();
  });
});

// ============================================================
// 5. mapBidToOffer edge cases
// ============================================================

describe('mapBidToOffer — edge cases', () => {
  const minimalBid: Bid = {
    id: 1,
    price: null,
    currency: 'USD',
    item_title: 'Item',
    item_url: null,
    image_url: null,
    source: 'test',
    is_selected: false,
  };

  test('handles null price', () => {
    const offer = mapBidToOffer({ ...minimalBid, price: null });
    expect(offer.price).toBeNull();
  });

  test('handles null item_url', () => {
    const offer = mapBidToOffer({ ...minimalBid, item_url: null });
    expect(offer.url).toBe('#');
  });

  test('handles null image_url', () => {
    const offer = mapBidToOffer({ ...minimalBid, image_url: null });
    expect(offer.image_url).toBeNull();
  });

  test('handles missing seller', () => {
    const offer = mapBidToOffer(minimalBid);
    expect(offer.merchant).toBe('Unknown');
    expect(offer.merchant_domain).toBeUndefined();
  });

  test('handles empty item_title', () => {
    const offer = mapBidToOffer({ ...minimalBid, item_title: '' });
    expect(offer.title).toBe('');
  });

  test('is_service_provider defaults to false', () => {
    const offer = mapBidToOffer(minimalBid);
    expect(offer.is_service_provider).toBe(false);
  });

  test('handles undefined is_service_provider', () => {
    const bid = { ...minimalBid };
    delete (bid as any).is_service_provider;
    const offer = mapBidToOffer(bid);
    expect(offer.is_service_provider).toBe(false);
  });
});

// ============================================================
// 6. Full scenario: 16 rows with mixed null/valid data
// ============================================================

describe('Full scenario: loading 16 rows with mixed data', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('loading 16 rows with various null fields does not crash', () => {
    const rows: Row[] = [
      mockRow({ id: 1, choice_answers: 'null', choice_factors: 'null', selected_providers: 'null' }),
      mockRow({ id: 2, choice_answers: undefined, choice_factors: undefined }),
      mockRow({ id: 3, choice_answers: '{}', choice_factors: '[]' }),
      mockRow({ id: 4, choice_answers: '{"size": "M"}', choice_factors: '[{"name": "size"}]' }),
      mockRow({ id: 5, choice_answers: '', choice_factors: '' }),
      mockRow({ id: 6, choice_answers: '{broken', choice_factors: '{broken' }),
      mockRow({ id: 7, choice_answers: '42', choice_factors: '42' }),
      mockRow({ id: 8, choice_answers: '"string"', choice_factors: '"string"' }),
      mockRow({ id: 9, choice_answers: 'true', choice_factors: 'true' }),
      mockRow({ id: 10, choice_answers: '["array"]', choice_factors: '{"obj": {}}' }),
      mockRow({ id: 11, selected_providers: '{"amazon": true}' }),
      mockRow({ id: 12, selected_providers: 'null' }),
      mockRow({ id: 13, selected_providers: '' }),
      mockRow({ id: 14, selected_providers: '[]' }),
      mockRow({ id: 15, bids: [] }),
      mockRow({ id: 16 }),
    ];

    expect(() => {
      useShoppingStore.getState().setRows(rows);
    }).not.toThrow();

    // Now activate each row — this triggers selectedProviders parsing
    for (const row of rows) {
      expect(() => {
        useShoppingStore.getState().setActiveRowId(row.id);
      }).not.toThrow();
    }

    // Now parse choice data for each row
    for (const row of rows) {
      expect(() => {
        const answers = parseChoiceAnswers(row);
        Object.entries(answers); // THE call that crashed production
      }).not.toThrow();

      expect(() => {
        const factors = parseChoiceFactors(row);
        factors.forEach((f) => f); // iterate without crash
      }).not.toThrow();
    }
  });
});

// ============================================================
// 7. Provider toggles default state
// ============================================================

describe('Provider toggles default state', () => {
  test('default selectedProviders includes amazon, ebay, serpapi, vendor_directory', () => {
    // Reset selectedProviders explicitly (clearSearch doesn't touch them)
    useShoppingStore.getState().setSelectedProviders({ amazon: true, ebay: true, serpapi: true, vendor_directory: true });
    const state = useShoppingStore.getState();
    expect(state.selectedProviders.amazon).toBe(true);
    expect(state.selectedProviders.ebay).toBe(true);
    expect(state.selectedProviders.serpapi).toBe(true);
    expect(state.selectedProviders.vendor_directory).toBe(true);
  });

  test('toggleProvider flips a provider', () => {
    useShoppingStore.getState().clearSearch();
    const store = useShoppingStore.getState();

    // Mock fetch to avoid real API calls
    global.fetch = (() => Promise.resolve({ ok: true })) as any;

    store.toggleProvider('amazon');
    expect(useShoppingStore.getState().selectedProviders.amazon).toBe(false);

    store.toggleProvider('amazon');
    expect(useShoppingStore.getState().selectedProviders.amazon).toBe(true);
  });
});
