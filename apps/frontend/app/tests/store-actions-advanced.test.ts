/**
 * Zustand Store advanced tests — setRows hydration, bid merge, engagement tracking.
 * Extracted from store-actions.test.ts to keep files under 450 lines.
 */
import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';

function mockRow(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    title: 'Test Row',
    status: 'sourcing',
    budget_max: null,
    currency: 'USD',
    ...overrides,
  };
}

function mockBid(overrides: Record<string, unknown> = {}) {
  return {
    id: 100,
    price: 29.99,
    currency: 'USD',
    item_title: 'Product A',
    item_url: 'https://example.com/a',
    image_url: null,
    source: 'rainforest',
    is_selected: false,
    ...overrides,
  };
}

describe('Zustand Store - setRows preserves engagement and hydrates bids', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('preserves existing last_engaged_at timestamps', () => {
    const store = useShoppingStore.getState();
    store.setRows([mockRow({ id: 1 })]);
    store.setActiveRowId(1);

    const engagedAt = useShoppingStore.getState().rows[0].last_engaged_at;
    expect(engagedAt).toBeDefined();

    store.setRows([mockRow({ id: 1 })]);
    expect(useShoppingStore.getState().rows[0].last_engaged_at).toBe(engagedAt);
  });

  test('hydrates rowResults from bids when rows have bids', () => {
    const store = useShoppingStore.getState();
    const bids = [mockBid({ id: 200 }), mockBid({ id: 201 })];
    store.setRows([mockRow({ id: 5, bids })]);

    const results = useShoppingStore.getState().rowResults[5];
    expect(results).toBeDefined();
    expect(results.length).toBeGreaterThanOrEqual(2);
  });

  test('prunes rowResults for removed rows', () => {
    const store = useShoppingStore.getState();
    store.setRows([mockRow({ id: 1 }), mockRow({ id: 2 })]);
    store.setRowResults(1, [{ title: 'A', price: 10, currency: 'USD', merchant: 'X', url: '#', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }]);
    store.setRowResults(2, [{ title: 'B', price: 20, currency: 'USD', merchant: 'Y', url: '#', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }]);

    store.setRows([mockRow({ id: 1 })]);
    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toBeDefined();
    expect(state.rowResults[2]).toBeUndefined();
  });

  test('merges bid results with existing search results by bid_id', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(10, [
      { title: 'Search A', price: 5, currency: 'USD', merchant: 'M', url: '#', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test', bid_id: 300 },
    ]);

    const bids = [mockBid({ id: 300, price: 7.99 }), mockBid({ id: 301, price: 9.99 })];
    store.setRows([mockRow({ id: 10, bids })]);

    const results = useShoppingStore.getState().rowResults[10];
    expect(results).toBeDefined();
    const bidIds = results.filter(r => r.bid_id).map(r => r.bid_id);
    expect(bidIds).toContain(300);
    expect(bidIds).toContain(301);
  });
});
