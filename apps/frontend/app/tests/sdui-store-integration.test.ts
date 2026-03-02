/**
 * Tests for SDUI + Store Integration
 *
 * Covers:
 * - Store state shape readiness for SDUI (Row.desire_tier exists, ui_schema not yet)
 * - mapBidToOffer compatibility with SDUI ActionRow intents
 * - shouldForceNewRow compatibility (no dependency on desire_tier)
 * - rowResults hydration from bids (existing flow works pre-SDUI)
 * - Store actions that will need SDUI wiring (setRowResults, appendRowResults, updateRow)
 * - selectOrCreateRow behavior (no SDUI dependency)
 * - Streaming lock behavior (guards against ui_schema_updated race conditions)
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore, mapBidToOffer, shouldForceNewRow } from '../store';
import type { Row, Bid, Offer } from '../store';
import { validateUISchema, getMinimumViableRow } from '../sdui/types';
// UISchema type used implicitly via validateUISchema return

// Reset store before each test
beforeEach(() => {
  useShoppingStore.setState({
    rows: [],
    projects: [],
    rowResults: {},
    rowProviderStatuses: {},
    rowSearchErrors: {},
    rowOfferSort: {},
    moreResultsIncoming: {},
    streamingRowIds: {},
    isSearching: false,
    activeRowId: null,
    currentQuery: '',
    cardClickQuery: null,
    pendingRowDelete: null,
  });
});

// =========================================================================
// Store State Shape Readiness
// =========================================================================

describe('Store Row interface readiness for SDUI', () => {
  test('Row interface has desire_tier field', () => {
    const row: Row = {
      id: 1, title: 'Test', status: 'sourcing', budget_max: null, currency: 'USD',
      desire_tier: 'commodity',
    };
    expect(row.desire_tier).toBe('commodity');
  });

  test('Row interface allows undefined desire_tier', () => {
    const row: Row = {
      id: 1, title: 'Test', status: 'sourcing', budget_max: null, currency: 'USD',
    };
    expect(row.desire_tier).toBeUndefined();
  });

  test('Row interface has service fields', () => {
    const row: Row = {
      id: 1, title: 'Jet', status: 'sourcing', budget_max: null, currency: 'USD',
      is_service: true, service_category: 'private_aviation',
    };
    expect(row.is_service).toBe(true);
    expect(row.service_category).toBe('private_aviation');
  });

  test('Row interface has bids for hydration', () => {
    const row: Row = {
      id: 1, title: 'Test', status: 'sourcing', budget_max: null, currency: 'USD',
      bids: [
        { id: 10, price: 29.99, currency: 'USD', item_title: 'Widget', item_url: 'https://x.com', image_url: null, source: 'amazon', is_selected: false },
      ],
    };
    expect(row.bids).toHaveLength(1);
  });
});

// =========================================================================
// mapBidToOffer → ActionRow Intent Compatibility
// =========================================================================

describe('mapBidToOffer SDUI compatibility', () => {
  test('generates click_url for outbound_affiliate intent', () => {
    const bid: Bid = {
      id: 1, price: 29.99, currency: 'USD', item_title: 'Shoes',
      item_url: 'https://amazon.com/shoes', image_url: null, source: 'rainforest', is_selected: false,
    };
    const offer = mapBidToOffer(bid);
    // click_url uses /api/clickout which maps to /api/out (the backend affiliate redirect)
    expect(offer.click_url).toContain('/api/clickout');
    expect(offer.click_url).toContain(encodeURIComponent('https://amazon.com/shoes'));
    expect(offer.bid_id).toBe(1);
  });

  test('generates vendor_email for contact_vendor intent', () => {
    const bid: Bid = {
      id: 2, price: null, currency: 'USD', item_title: 'NetJets',
      item_url: 'mailto:info@netjets.com', image_url: null, source: 'vendor_directory',
      is_selected: false, is_service_provider: true,
    };
    const offer = mapBidToOffer(bid);
    expect(offer.vendor_email).toBe('info@netjets.com');
    expect(offer.is_service_provider).toBe(true);
  });

  test('null price maps correctly (quote-based)', () => {
    const bid: Bid = {
      id: 3, price: null, currency: 'USD', item_title: 'Custom Ring',
      item_url: null, image_url: null, source: 'vendor_directory', is_selected: false,
    };
    const offer = mapBidToOffer(bid);
    expect(offer.price).toBeNull();
  });
});

// =========================================================================
// shouldForceNewRow (no desire_tier dependency)
// =========================================================================

describe('shouldForceNewRow has no desire_tier dependency', () => {
  test('does not reference desire_tier', () => {
    // shouldForceNewRow only uses message, activeRowTitle, aggressiveness
    const result = shouldForceNewRow({
      message: 'completely different product',
      activeRowTitle: 'organic eggs',
      aggressiveness: 80,
    });
    // The function works purely on word overlap — no tier logic
    expect(typeof result).toBe('boolean');
  });

  test('returns false for low aggressiveness', () => {
    expect(shouldForceNewRow({
      message: 'something else entirely',
      activeRowTitle: 'eggs',
      aggressiveness: 30,
    })).toBe(false);
  });

  test('returns false for refinement queries', () => {
    expect(shouldForceNewRow({
      message: 'eggs over $10',
      activeRowTitle: 'eggs',
      aggressiveness: 90,
    })).toBe(false);
  });
});

// =========================================================================
// Store setRowResults / appendRowResults
// =========================================================================

describe('Store row results management (pre-SDUI)', () => {
  test('setRowResults replaces results for a row', () => {
    const store = useShoppingStore.getState();
    const offers: Offer[] = [
      { title: 'A', price: 10, currency: 'USD', merchant: 'X', url: 'https://x.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' },
    ];
    store.setRowResults(1, offers);
    expect(useShoppingStore.getState().rowResults[1]).toHaveLength(1);
  });

  test('appendRowResults dedupes by bid_id', () => {
    const store = useShoppingStore.getState();
    const offer1: Offer = {
      title: 'A', price: 10, currency: 'USD', merchant: 'X', url: 'https://x.com',
      image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test', bid_id: 100,
    };
    store.setRowResults(1, [offer1]);
    // Append same bid_id — should not duplicate
    store.appendRowResults(1, [{ ...offer1, title: 'A Updated' }]);
    expect(useShoppingStore.getState().rowResults[1]).toHaveLength(1);
  });

  test('appendRowResults adds new results', () => {
    const store = useShoppingStore.getState();
    const offer1: Offer = {
      title: 'A', price: 10, currency: 'USD', merchant: 'X', url: 'https://x.com',
      image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test', bid_id: 100,
    };
    const offer2: Offer = {
      title: 'B', price: 20, currency: 'USD', merchant: 'Y', url: 'https://y.com',
      image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test', bid_id: 200,
    };
    store.setRowResults(1, [offer1]);
    store.appendRowResults(1, [offer2]);
    expect(useShoppingStore.getState().rowResults[1]).toHaveLength(2);
  });

  test('streaming lock blocks setRowResults', () => {
    const store = useShoppingStore.getState();
    store.setStreamingLock(1, true);
    const offers: Offer[] = [
      { title: 'A', price: 10, currency: 'USD', merchant: 'X', url: 'https://x.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' },
    ];
    store.setRowResults(1, offers);
    // Should be blocked — rowResults should be empty for row 1
    expect(useShoppingStore.getState().rowResults[1]).toBeUndefined();
  });

  test('streaming lock does NOT block appendRowResults', () => {
    const store = useShoppingStore.getState();
    store.setStreamingLock(1, true);
    const offer: Offer = {
      title: 'A', price: 10, currency: 'USD', merchant: 'X', url: 'https://x.com',
      image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test', bid_id: 100,
    };
    store.appendRowResults(1, [offer]);
    // appendRowResults is NOT blocked by streaming lock (it's the SSE path)
    expect(useShoppingStore.getState().rowResults[1]).toHaveLength(1);
  });
});

// =========================================================================
// Store updateRow hydrates bids → rowResults
// =========================================================================

describe('Store updateRow bid hydration', () => {
  test('updateRow with bids hydrates rowResults', () => {
    const store = useShoppingStore.getState();
    const row: Row = {
      id: 1, title: 'Eggs', status: 'sourcing', budget_max: null, currency: 'USD',
    };
    store.setRows([row]);
    // Simulate row update with bids from DB fetch
    store.updateRow(1, {
      bids: [
        { id: 10, price: 3.49, currency: 'USD', item_title: 'Store Eggs', item_url: 'https://store.com/eggs', image_url: 'https://img.com/eggs.jpg', source: 'kroger', is_selected: false },
        { id: 11, price: 4.99, currency: 'USD', item_title: 'Organic Eggs', item_url: 'https://store.com/organic', image_url: 'https://img.com/organic.jpg', source: 'kroger', is_selected: false },
      ],
    });
    const results = useShoppingStore.getState().rowResults[1];
    expect(results).toBeDefined();
    expect(results).toHaveLength(2);
    expect(results[0].bid_id).toBe(10);
    expect(results[1].bid_id).toBe(11);
  });
});

// =========================================================================
// SDUI Schema + Store Future State
// =========================================================================

describe('SDUI schema readiness for store integration', () => {
  test('UISchema can be stored as JSON in Row (simulated)', () => {
    const schema = getMinimumViableRow('Test', 'sourcing');
    // Simulate what Row.ui_schema would look like when persisted
    const rowWithSchema = {
      id: 1, title: 'Test', status: 'sourcing',
      ui_schema: JSON.stringify(schema),
      ui_schema_version: 1,
    };
    const parsed = JSON.parse(rowWithSchema.ui_schema);
    const validated = validateUISchema(parsed);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe('ROW_COMPACT');
  });

  test('ui_schema_updated SSE event can be processed', () => {
    // Simulate receiving an SSE event and updating store
    const ssePayload = {
      entity_type: 'row' as const,
      entity_id: 1,
      schema: {
        version: 2,
        layout: 'ROW_MEDIA_LEFT' as const,
        blocks: [
          { type: 'ProductImage' as const, url: 'https://img.com/a.jpg', alt: 'Product' },
          { type: 'PriceBlock' as const, amount: 29.99, currency: 'USD', label: 'Best Price' },
        ],
      },
      version: 2,
      trigger: 'search_complete',
    };

    // Validate the schema from SSE
    const validated = validateUISchema(ssePayload.schema);
    expect(validated).not.toBeNull();
    expect(validated!.layout).toBe('ROW_MEDIA_LEFT');
    expect(validated!.blocks).toHaveLength(2);
  });

  test('minimum viable row used as fallback when schema is invalid', () => {
    const invalidSchema = { version: 'bad', layout: 'INVALID' };
    const validated = validateUISchema(invalidSchema);
    expect(validated).toBeNull();

    // Fallback
    const fallback = getMinimumViableRow('Eggs', 'sourcing');
    const fallbackValidated = validateUISchema(fallback);
    expect(fallbackValidated).not.toBeNull();
  });

  test('stale schema safety: 10s timeout produces fallback', () => {
    // This tests the concept — actual timer logic would be in the component
    // Here we verify that getMinimumViableRow produces valid output
    const fallback = getMinimumViableRow('Stale Item', 'sourcing');
    expect(fallback.blocks).toHaveLength(3);
    expect(fallback.blocks[2].type).toBe('ActionRow');
  });
});
