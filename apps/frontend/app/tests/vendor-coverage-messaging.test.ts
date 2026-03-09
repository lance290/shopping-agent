/**
 * VENDOR COVERAGE MESSAGING: Chat SSE user_message promotion
 *
 * When vendor coverage is thin, the backend sends a user_message via
 * search_results SSE events. If the assistant has not yet produced any
 * text content, this message should become the visible assistant reply
 * instead of falling through to the generic empty-response fallback.
 *
 * These tests validate the logic extracted from Chat.tsx SSE handling.
 */

import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';
import type { Offer, ProviderStatusSnapshot, ProviderStatusType } from '../store-types';

// ---------------------------------------------------------------------------
// Helpers — mirrors Chat.tsx SSE handler logic
// ---------------------------------------------------------------------------

/**
 * Simulates the Chat.tsx SSE handler logic for search_results events.
 * Returns what assistantContent would be after processing the event.
 */
function processSearchResultsEvent(
  currentAssistantContent: string,
  payload: {
    row_id?: number;
    results?: unknown[];
    provider_statuses?: unknown[];
    more_incoming?: boolean;
    user_message?: string;
  },
): string {
  let assistantContent = currentAssistantContent;
  const userMessage =
    typeof payload.user_message === 'string' ? payload.user_message : undefined;

  // This is the exact logic added in Chat.tsx
  if (userMessage && !assistantContent.trim()) {
    assistantContent = userMessage;
  }

  return assistantContent;
}

/**
 * Simulates the empty-response fallback at the end of the SSE stream.
 */
function applyEmptyResponseFallback(assistantContent: string): string {
  if (!assistantContent.trim()) {
    return 'Sorry, the assistant returned an empty response. Please try again.';
  }
  return assistantContent;
}

const ROW_ID = 200;

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

const makeStatus = (
  id: string,
  status: ProviderStatusType = 'ok',
): ProviderStatusSnapshot => ({
  provider_id: id,
  status,
  result_count: 0,
  latency_ms: 100,
});

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
// Vendor coverage user_message → assistant content promotion
// ===========================================================================

describe('Vendor coverage messaging: user_message promotes to assistant content', () => {
  test('user_message becomes assistant content when assistant is empty', () => {
    const coverageMsg =
      "I'm not seeing strong vendor coverage for this request yet, so I've flagged it internally and we'll expand the vendor set as quickly as we can.";
    const result = processSearchResultsEvent('', {
      row_id: ROW_ID,
      results: [],
      user_message: coverageMsg,
    });

    expect(result).toBe(coverageMsg);
  });

  test('user_message becomes assistant content when assistant is only whitespace', () => {
    const coverageMsg = 'Vendor coverage is thin for this request.';
    const result = processSearchResultsEvent('   ', {
      row_id: ROW_ID,
      results: [],
      user_message: coverageMsg,
    });

    expect(result).toBe(coverageMsg);
  });

  test('user_message does NOT override existing assistant content', () => {
    const existingContent = 'I found several options for private jet charters.';
    const coverageMsg = 'Vendor coverage is thin.';
    const result = processSearchResultsEvent(existingContent, {
      row_id: ROW_ID,
      results: [],
      user_message: coverageMsg,
    });

    expect(result).toBe(existingContent);
  });

  test('no user_message leaves assistant content unchanged', () => {
    const result = processSearchResultsEvent('', {
      row_id: ROW_ID,
      results: [],
    });

    expect(result).toBe('');
  });

  test('empty-response fallback does NOT fire when coverage message was promoted', () => {
    const coverageMsg =
      "I'm not seeing strong vendor coverage for this request yet.";
    const afterSSE = processSearchResultsEvent('', {
      row_id: ROW_ID,
      results: [],
      user_message: coverageMsg,
    });
    const afterFallback = applyEmptyResponseFallback(afterSSE);

    expect(afterFallback).toBe(coverageMsg);
    expect(afterFallback).not.toContain('empty response');
  });

  test('empty-response fallback fires when NO coverage message was sent', () => {
    const afterSSE = processSearchResultsEvent('', {
      row_id: ROW_ID,
      results: [],
    });
    const afterFallback = applyEmptyResponseFallback(afterSSE);

    expect(afterFallback).toContain('empty response');
  });
});

// ===========================================================================
// Store-level: user_message flows through appendRowResults
// ===========================================================================

describe('Store: vendor coverage user_message persists in rowSearchErrors', () => {
  test('appendRowResults stores coverage message', () => {
    const store = useShoppingStore.getState();
    const coverageMsg =
      "I'm not seeing strong vendor coverage for this request yet.";

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(
      ROW_ID,
      [],
      [makeStatus('vendor_directory')],
      false,
      coverageMsg,
    );

    const state = useShoppingStore.getState();
    expect(state.rowSearchErrors[ROW_ID]).toBe(coverageMsg);
  });

  test('coverage message survives subsequent append without message', () => {
    const store = useShoppingStore.getState();
    const coverageMsg = 'Vendor coverage is thin.';

    store.setStreamingLock(ROW_ID, true);
    store.appendRowResults(
      ROW_ID,
      [],
      [makeStatus('vendor_directory')],
      true,
      coverageMsg,
    );
    store.appendRowResults(
      ROW_ID,
      [makeOffer({ title: 'Late result', bid_id: 1 })],
      [makeStatus('amazon')],
      false,
    );

    const state = useShoppingStore.getState();
    expect(state.rowSearchErrors[ROW_ID]).toBe(coverageMsg);
  });
});
