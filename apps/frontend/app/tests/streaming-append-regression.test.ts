/**
 * REGRESSION TESTS: Streaming Append & Replace-on-New-Search
 *
 * These tests codify the two core invariants of the search UX:
 *
 * 1. APPEND: As results arrive from each provider, they are APPENDED to the
 *    existing list. The UI must show partial results immediately — never wait
 *    for all providers to finish.
 *
 * 2. REPLACE: When the user changes requirements (new search), old results are
 *    REPLACED — but liked/selected bids are preserved.
 *
 * If you break these invariants the user will see:
 *   - Empty tiles for 5-10s while waiting for slow providers (violates APPEND)
 *   - Stale results from a previous search mixed with new ones (violates REPLACE)
 *
 * DO NOT WEAKEN OR DELETE THESE TESTS.
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';
import type { Offer, ProviderStatusSnapshot, ProviderStatusType } from '../store-types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let urlCounter = 0;
const makeOffer = (overrides: Partial<Offer> = {}): Offer => ({
  title: 'Test Product',
  price: 99.99,
  currency: 'USD',
  merchant: 'TestMerchant',
  url: `https://example.com/product-${++urlCounter}`,
  image_url: null,
  rating: null,
  reviews_count: null,
  shipping_info: null,
  source: 'test',
  ...overrides,
});

const makeStatus = (id: string, status: ProviderStatusType = 'ok'): ProviderStatusSnapshot => ({
  provider_id: id,
  status,
  result_count: 1,
  latency_ms: 100,
});

const ROW_ID = 100;

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  urlCounter = 0;
  const store = useShoppingStore.getState();
  store.clearSearch();
  store.clearRowResults(ROW_ID);
  store.setStreamingLock(ROW_ID, false);
  store.setIsSearching(false);
  store.setMoreResultsIncoming(ROW_ID, false);
});

// ===========================================================================
// INVARIANT 1: Results append as each provider completes
// ===========================================================================

describe('INVARIANT: Results append incrementally per provider', () => {
  test('first provider batch is immediately visible (not waiting for others)', () => {
    const store = useShoppingStore.getState();
    const amazonResult = makeOffer({ title: 'Amazon Widget', source: 'rainforest_amazon', bid_id: 1 });

    // Simulate: streaming lock acquired, first SSE event arrives from Amazon
    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [amazonResult], [makeStatus('amazon')], true);

    const state = useShoppingStore.getState();
    // Result must be visible NOW — not after all providers finish
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('Amazon Widget');
    expect(state.moreResultsIncoming[ROW_ID]).toBe(true);
  });

  test('second provider batch appends to first (not replaces)', () => {
    const store = useShoppingStore.getState();
    const amazonResult = makeOffer({ title: 'Amazon Widget', source: 'rainforest_amazon', bid_id: 1 });
    const vendorResult = makeOffer({ title: 'HELM Yacht Charters', source: 'vendor_directory', bid_id: 2 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [amazonResult], [makeStatus('amazon')], true);
    store.appendRowResults(ROW_ID, [vendorResult], [makeStatus('vendor_directory')], true);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    expect(state.rowResults[ROW_ID].map(o => o.title)).toEqual([
      'Amazon Widget',
      'HELM Yacht Charters',
    ]);
  });

  test('third provider (last) sets more_incoming=false', () => {
    const store = useShoppingStore.getState();
    const r1 = makeOffer({ title: 'Result 1', bid_id: 1 });
    const r2 = makeOffer({ title: 'Result 2', bid_id: 2 });
    const r3 = makeOffer({ title: 'Result 3', bid_id: 3 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [r1], [makeStatus('a')], true);   // 2 remaining
    store.appendRowResults(ROW_ID, [r2], [makeStatus('b')], true);   // 1 remaining
    store.appendRowResults(ROW_ID, [r3], [makeStatus('c')], false);  // 0 remaining (last)

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(3);
    expect(state.moreResultsIncoming[ROW_ID]).toBe(false);
  });

  test('empty provider batch (0 results) does not clear existing results', () => {
    const store = useShoppingStore.getState();
    const existing = makeOffer({ title: 'Existing', bid_id: 1 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [existing], [makeStatus('amazon')], true);

    // SerpAPI returns 0 results — must NOT wipe existing Amazon results
    store.appendRowResults(ROW_ID, [], [makeStatus('serpapi', 'ok')], true);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('Existing');
  });

  test('provider statuses accumulate across batches', () => {
    const store = useShoppingStore.getState();

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [makeOffer({ bid_id: 1 })], [makeStatus('amazon')], true);
    store.appendRowResults(ROW_ID, [makeOffer({ bid_id: 2 })], [makeStatus('vendor_directory')], false);

    const state = useShoppingStore.getState();
    const statuses = state.rowProviderStatuses[ROW_ID];
    expect(statuses).toHaveLength(2);
    expect(statuses.map(s => s.provider_id)).toContain('amazon');
    expect(statuses.map(s => s.provider_id)).toContain('vendor_directory');
  });

  test('failed provider does not block subsequent providers', () => {
    const store = useShoppingStore.getState();
    const goodResult = makeOffer({ title: 'Good Result', bid_id: 1 });

    store.setStreamingLock(ROW_ID, true);
    // Provider A fails — but we still get an event for it
    store.appendRowResults(ROW_ID, [], [makeStatus('serpapi', 'error')], true);
    // Provider B succeeds
    store.appendRowResults(ROW_ID, [goodResult], [makeStatus('amazon')], false);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('Good Result');

    const statuses = state.rowProviderStatuses[ROW_ID];
    expect(statuses.find(s => s.provider_id === 'serpapi')?.status).toBe('error');
    expect(statuses.find(s => s.provider_id === 'amazon')?.status).toBe('ok');
  });
});

// ===========================================================================
// INVARIANT 2: New search replaces old results (via setRowResults after done)
// ===========================================================================

describe('INVARIANT: New search replaces old results', () => {
  test('setRowResults replaces all results when streaming lock is released', () => {
    const store = useShoppingStore.getState();
    const oldResult = makeOffer({ title: 'Old Search Result', bid_id: 1 });
    const newResult = makeOffer({ title: 'New Search Result', bid_id: 2 });

    // Old search completed
    store.appendRowResults(ROW_ID, [oldResult]);

    // New search: authoritative DB re-fetch replaces everything
    store.setRowResults(ROW_ID, [newResult]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('New Search Result');
  });

  test('setRowResults preserves service providers when new results do not include them', () => {
    const store = useShoppingStore.getState();
    const vendorOffer = makeOffer({
      title: 'HELM Yacht Charters',
      source: 'vendor',
      is_service_provider: true,
      bid_id: 10,
    });
    const productOffer = makeOffer({ title: 'Amazon Book', source: 'amazon', bid_id: 11 });

    // First: vendor results arrive
    store.appendRowResults(ROW_ID, [vendorOffer]);

    // Then: setRowResults from DB re-fetch (which only has product bids)
    store.setRowResults(ROW_ID, [productOffer]);

    const state = useShoppingStore.getState();
    // Service provider should be preserved since incoming results don't include them
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    expect(state.rowResults[ROW_ID].find(o => o.is_service_provider)?.title).toBe('HELM Yacht Charters');
    expect(state.rowResults[ROW_ID].find(o => !o.is_service_provider)?.title).toBe('Amazon Book');
  });

  test('setRowResults replaces service providers when new results include them', () => {
    const store = useShoppingStore.getState();
    const oldVendor = makeOffer({ title: 'Old Vendor', is_service_provider: true, bid_id: 20 });
    const newVendor = makeOffer({ title: 'New Vendor', is_service_provider: true, bid_id: 21 });
    const product = makeOffer({ title: 'Product', source: 'amazon', bid_id: 22 });

    store.appendRowResults(ROW_ID, [oldVendor]);
    store.setRowResults(ROW_ID, [newVendor, product]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    expect(state.rowResults[ROW_ID].find(o => o.is_service_provider)?.title).toBe('New Vendor');
  });

  test('clearRowResults removes all results for a row', () => {
    const store = useShoppingStore.getState();
    store.appendRowResults(ROW_ID, [makeOffer({ bid_id: 1 }), makeOffer({ bid_id: 2 })]);

    store.clearRowResults(ROW_ID);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toBeUndefined();
  });
});

// ===========================================================================
// INVARIANT 3: Streaming lock protects in-flight SSE results
// ===========================================================================

describe('INVARIANT: Streaming lock prevents data loss during SSE', () => {
  test('setRowResults is blocked while SSE is streaming', () => {
    const store = useShoppingStore.getState();
    const sseResult = makeOffer({ title: 'SSE Result', bid_id: 1 });
    const staleResult = makeOffer({ title: 'Stale Auto-Load', bid_id: 2 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [sseResult], undefined, true);

    // Auto-load or comment-merge tries to replace — should be blocked
    store.setRowResults(ROW_ID, [staleResult]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('SSE Result');
  });

  test('appendRowResults is NEVER blocked by streaming lock', () => {
    const store = useShoppingStore.getState();

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'Batch 1', bid_id: 1 })], undefined, true);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'Batch 2', bid_id: 2 })], undefined, true);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'Batch 3', bid_id: 3 })], undefined, false);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(3);
  });

  test('full SSE lifecycle: lock → append → append → unlock → replace', () => {
    const store = useShoppingStore.getState();

    // 1. SSE starts
    store.setStreamingLock(ROW_ID, true);
    store.setIsSearching(true);

    // 2. Provider A returns (append)
    store.appendRowResults(
      ROW_ID,
      [makeOffer({ title: 'Provider A', bid_id: 1 })],
      [makeStatus('amazon')],
      true,
    );
    expect(useShoppingStore.getState().rowResults[ROW_ID]).toHaveLength(1);

    // 3. Provider B returns (append)
    store.appendRowResults(
      ROW_ID,
      [makeOffer({ title: 'Provider B', bid_id: 2 })],
      [makeStatus('vendor_directory')],
      false,
    );
    expect(useShoppingStore.getState().rowResults[ROW_ID]).toHaveLength(2);

    // 4. SSE done event → release lock
    store.setStreamingLock(ROW_ID, false);
    store.setIsSearching(false);

    // 5. Authoritative DB re-fetch replaces (this is the final truth)
    store.setRowResults(
      ROW_ID,
      [
        makeOffer({ title: 'DB Result 1', bid_id: 10 }),
        makeOffer({ title: 'DB Result 2', bid_id: 11 }),
        makeOffer({ title: 'DB Result 3', bid_id: 12 }),
      ],
    );

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(3);
    expect(state.rowResults[ROW_ID][0].title).toBe('DB Result 1');
    expect(state.isSearching).toBe(false);
    expect(state.streamingRowIds[ROW_ID]).toBe(false);
  });
});

// ===========================================================================
// INVARIANT 4: Deduplication across provider batches
// ===========================================================================

describe('INVARIANT: Deduplication prevents duplicate tiles', () => {
  test('same bid_id across batches is deduplicated', () => {
    const store = useShoppingStore.getState();

    store.appendRowResults(ROW_ID, [makeOffer({ title: 'First', bid_id: 42 })]);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'Dupe', bid_id: 42 })]);

    expect(useShoppingStore.getState().rowResults[ROW_ID]).toHaveLength(1);
    expect(useShoppingStore.getState().rowResults[ROW_ID][0].title).toBe('First');
  });

  test('same URL across batches is deduplicated (when no bid_id)', () => {
    const store = useShoppingStore.getState();
    const sharedUrl = 'https://example.com/same-product';

    store.appendRowResults(ROW_ID, [makeOffer({ title: 'First', url: sharedUrl })]);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'Dupe', url: sharedUrl })]);

    expect(useShoppingStore.getState().rowResults[ROW_ID]).toHaveLength(1);
  });

  test('different URLs are NOT deduplicated', () => {
    const store = useShoppingStore.getState();

    store.appendRowResults(ROW_ID, [makeOffer({ title: 'A', url: 'https://a.com/1', bid_id: 1 })]);
    store.appendRowResults(ROW_ID, [makeOffer({ title: 'B', url: 'https://b.com/2', bid_id: 2 })]);

    expect(useShoppingStore.getState().rowResults[ROW_ID]).toHaveLength(2);
  });
});

// ===========================================================================
// INVARIANT 5: Vendor directory results are treated as first-class results
// ===========================================================================

describe('INVARIANT: Vendor directory results are first-class', () => {
  test('vendor_directory results append alongside marketplace results', () => {
    const store = useShoppingStore.getState();
    const amazonResult = makeOffer({ title: 'Amazon Book', source: 'rainforest_amazon', bid_id: 1 });
    const vendorResult = makeOffer({ title: 'HELM Yacht Charters', source: 'vendor_directory', bid_id: 2 });

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(ROW_ID, [amazonResult], [makeStatus('amazon')], true);
    store.appendRowResults(ROW_ID, [vendorResult], [makeStatus('vendor_directory')], false);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(2);
    const sources = state.rowResults[ROW_ID].map(o => o.source);
    expect(sources).toContain('rainforest_amazon');
    expect(sources).toContain('vendor_directory');
  });

  test('vendor_directory results survive when other providers return empty', () => {
    const store = useShoppingStore.getState();
    const vendorResult = makeOffer({ title: 'CharterWorld', source: 'vendor_directory', bid_id: 1 });

    store.setStreamingLock(ROW_ID, true);
    // All web providers fail
    store.appendRowResults(ROW_ID, [], [makeStatus('serpapi', 'error')], true);
    store.appendRowResults(ROW_ID, [], [makeStatus('searchapi', 'error')], true);
    store.appendRowResults(ROW_ID, [], [makeStatus('amazon', 'timeout')], true);
    // Vendor directory succeeds
    store.appendRowResults(ROW_ID, [vendorResult], [makeStatus('vendor_directory')], false);

    const state = useShoppingStore.getState();
    expect(state.rowResults[ROW_ID]).toHaveLength(1);
    expect(state.rowResults[ROW_ID][0].title).toBe('CharterWorld');
  });
});
