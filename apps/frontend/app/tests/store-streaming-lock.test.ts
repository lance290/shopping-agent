import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore, Offer } from '../store';

const makeOffer = (overrides: Partial<Offer> = {}): Offer => ({
  title: 'Test Product',
  price: 99.99,
  currency: 'USD',
  merchant: 'TestMerchant',
  url: `https://example.com/${Math.random()}`,
  image_url: null,
  rating: null,
  reviews_count: null,
  shipping_info: null,
  source: 'serpapi',
  ...overrides,
});

describe('Streaming Lock — prevents setRowResults from wiping SSE results', () => {
  const ROW_ID = 42;

  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearRowResults(ROW_ID);
    store.setStreamingLock(ROW_ID, false);
    store.setIsSearching(false);
    store.setMoreResultsIncoming(ROW_ID, false);
  });

  test('setRowResults is blocked while streaming lock is active', () => {
    const store = useShoppingStore.getState();
    const sseOffer = makeOffer({ title: 'SSE Result', bid_id: 1 });
    const replaceOffer = makeOffer({ title: 'Replace Result', bid_id: 2 });

    // Simulate SSE: acquire lock, append results
    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [sseOffer], undefined, true);

    // Attempt to replace results while lock is held (e.g. from auto-load or comment merge)
    store.setRowResults(ROW_ID, [replaceOffer]);

    // SSE results should survive — replace should be blocked
    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('SSE Result');
  });

  test('setRowResults works after streaming lock is released', () => {
    const store = useShoppingStore.getState();
    const sseOffer = makeOffer({ title: 'SSE Result', bid_id: 1 });
    const freshOffer = makeOffer({ title: 'Fresh DB Result', bid_id: 3 });

    // Simulate full SSE cycle
    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [sseOffer], undefined, false);
    store.setStreamingLock(ROW_ID, false);

    // Now setRowResults should work (authoritative re-fetch after done event)
    store.setRowResults(ROW_ID, [freshOffer]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('Fresh DB Result');
  });

  test('appendRowResults is NOT blocked by streaming lock', () => {
    const store = useShoppingStore.getState();
    const offer1 = makeOffer({ title: 'Batch 1', bid_id: 10 });
    const offer2 = makeOffer({ title: 'Batch 2', bid_id: 11 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [offer1], undefined, true);
    store.appendRowResults(ROW_ID, [offer2], undefined, false);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    expect(state.rowResults[ROW_ID].map((o) => o.title)).toEqual(['Batch 1', 'Batch 2']);
  });
});

describe('updateRowOffer — targeted mutations safe during streaming', () => {
  const ROW_ID = 43;

  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearRowResults(ROW_ID);
    store.setStreamingLock(ROW_ID, false);
  });

  test('updateRowOffer mutates matching offers without replacing array', () => {
    const store = useShoppingStore.getState();
    const offer1 = makeOffer({ title: 'A', bid_id: 100, is_liked: false });
    const offer2 = makeOffer({ title: 'B', bid_id: 101, is_liked: false });

    store.appendRowResults(ROW_ID, [offer1, offer2]);

    // Like offer 1 via targeted mutation
    store.updateRowOffer(ROW_ID, (o) => o.bid_id === 100, { is_liked: true });

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    expect(state.rowResults[ROW_ID][0].is_liked).toBe(true);
    expect(state.rowResults[ROW_ID][1].is_liked).toBe(false);
  });

  test('updateRowOffer works while streaming lock is active', () => {
    const store = useShoppingStore.getState();
    const offer = makeOffer({ title: 'Streamable', bid_id: 200, is_liked: false });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [offer], undefined, true);

    // User likes an offer while SSE is still streaming
    store.updateRowOffer(ROW_ID, (o) => o.bid_id === 200, { is_liked: true });

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID][0].is_liked).toBe(true);
  });

  test('updateRowOffer handles select/unselect correctly', () => {
    const store = useShoppingStore.getState();
    const offer1 = makeOffer({ title: 'A', bid_id: 300, is_selected: false });
    const offer2 = makeOffer({ title: 'B', bid_id: 301, is_selected: false });

    store.appendRowResults(ROW_ID, [offer1, offer2]);

    // Select offer 1: first unselect all, then select the target
    store.updateRowOffer(ROW_ID, () => true, { is_selected: false });
    store.updateRowOffer(ROW_ID, (o) => o.bid_id === 300, { is_selected: true });

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID][0].is_selected).toBe(true);
    expect(state.rowResults[ROW_ID][1].is_selected).toBe(false);
  });

  test('updateRowOffer comment preview mutation', () => {
    const store = useShoppingStore.getState();
    const offer = makeOffer({ title: 'Commentable', bid_id: 400 });

    store.appendRowResults(ROW_ID, [offer]);

    store.updateRowOffer(ROW_ID, (o) => o.bid_id === 400, { comment_preview: 'Great deal!' });

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID][0].comment_preview).toBe('Great deal!');
  });

  test('updateRowOffer returns empty object for non-existent row', () => {
    const store = useShoppingStore.getState();
    // Should not throw
    store.updateRowOffer(999, () => true, { is_liked: true });
    const state = useShoppingStore.getState();
    expect(state.rowResults[999]).toBeUndefined();
  });
});

describe('appendRowResults deduplication', () => {
  const ROW_ID = 44;

  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearRowResults(ROW_ID);
  });

  test('deduplicates by bid_id', () => {
    const store = useShoppingStore.getState();
    const offer = makeOffer({ title: 'Original', bid_id: 500 });
    const dupe = makeOffer({ title: 'Duplicate', bid_id: 500 });

    store.appendRowResults(ROW_ID, [offer]);
    store.appendRowResults(ROW_ID, [dupe]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('Original');
  });

  test('deduplicates by URL when no bid_id', () => {
    const store = useShoppingStore.getState();
    const url = 'https://example.com/product-123';
    const offer = makeOffer({ title: 'First', url });
    const dupe = makeOffer({ title: 'Second', url });

    store.appendRowResults(ROW_ID, [offer]);
    store.appendRowResults(ROW_ID, [dupe]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('First');
  });
});
