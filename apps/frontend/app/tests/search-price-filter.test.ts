import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';
import { useShoppingStore, Row, Offer, ProviderStatusSnapshot } from '../store';

describe('Search Price Filter Integration', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('row choice_answers stores min_price correctly as JSON string', () => {
    const choiceAnswers = { min_price: 500, max_price: 5000 };
    const row: Row = {
      id: 1,
      title: 'Bianchi bicycle',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
      choice_answers: JSON.stringify(choiceAnswers),
    };

    useShoppingStore.getState().setRows([row]);
    const storedRow = useShoppingStore.getState().rows.find(r => r.id === 1);

    const parsed = JSON.parse(storedRow?.choice_answers || '{}');
    expect(parsed.min_price).toBe(500);
    expect(parsed.max_price).toBe(5000);
  });

  test('updateRow preserves choice_answers JSON', () => {
    const initialRow: Row = {
      id: 3,
      title: 'Test Item',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
      choice_answers: JSON.stringify({ min_price: 100 }),
    };

    useShoppingStore.getState().setRows([initialRow]);
    
    // Update with new data that also has choice_answers
    useShoppingStore.getState().updateRow(3, {
      ...initialRow,
      choice_answers: JSON.stringify({ min_price: 200, brand: 'Test' }),
    });

    const updatedRow = useShoppingStore.getState().rows.find(r => r.id === 3);
    const parsed = JSON.parse(updatedRow?.choice_answers || '{}');
    expect(parsed.min_price).toBe(200);
    expect(parsed.brand).toBe('Test');
  });

  test('setRowResults stores results with price data', () => {
    const row: Row = {
      id: 4,
      title: 'Test',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
    };

    useShoppingStore.getState().setRows([row]);

    const offers: Offer[] = [
      { title: 'Item 1', price: 500, currency: 'USD', merchant: 'Shop A', url: 'http://a.com', source: 'google_shopping', image_url: null, rating: null, reviews_count: null, shipping_info: null },
      { title: 'Item 2', price: 750, currency: 'USD', merchant: 'Shop B', url: 'http://b.com', source: 'rainforest', image_url: null, rating: null, reviews_count: null, shipping_info: null },
    ];

    useShoppingStore.getState().setRowResults(4, offers);

    const results = useShoppingStore.getState().rowResults[4];
    expect(results).toHaveLength(2);
    expect(results[0].price).toBe(500);
    expect(results[1].price).toBe(750);
  });

  test('provider statuses track google_shopping provider', () => {
    const row: Row = {
      id: 5,
      title: 'Test',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
    };

    useShoppingStore.getState().setRows([row]);

    const providerStatuses: ProviderStatusSnapshot[] = [
      { provider_id: 'rainforest', status: 'ok', result_count: 5, latency_ms: 2000 },
      { provider_id: 'google_shopping', status: 'ok', result_count: 40, latency_ms: 8000 },
      { provider_id: 'serpapi', status: 'rate_limited', result_count: 0, latency_ms: 300 },
    ];

    useShoppingStore.getState().setRowResults(5, [], providerStatuses);

    const statuses = useShoppingStore.getState().rowProviderStatuses[5];
    expect(statuses).toHaveLength(3);
    
    const googleShopping = statuses.find((s: ProviderStatusSnapshot) => s.provider_id === 'google_shopping');
    expect(googleShopping?.status).toBe('ok');
    expect(googleShopping?.result_count).toBe(40);
  });

  test('results include source field for filtering', () => {
    const row: Row = {
      id: 6,
      title: 'Test',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
    };

    useShoppingStore.getState().setRows([row]);

    const offers: Offer[] = [
      { title: 'Amazon Item', price: 100, currency: 'USD', merchant: 'Amazon', url: 'http://amazon.com', source: 'rainforest', image_url: null, rating: null, reviews_count: null, shipping_info: null },
      { title: 'Google Item', price: 200, currency: 'USD', merchant: 'Best Buy', url: 'http://bestbuy.com', source: 'google_shopping', image_url: null, rating: null, reviews_count: null, shipping_info: null },
      { title: 'CSE Item', price: 0, currency: 'USD', merchant: 'Blog', url: 'http://blog.com', source: 'google_cse', image_url: null, rating: null, reviews_count: null, shipping_info: null },
    ];

    useShoppingStore.getState().setRowResults(6, offers);

    const results = useShoppingStore.getState().rowResults[6];
    
    const rainforestResults = results.filter(r => r.source === 'rainforest');
    const googleShoppingResults = results.filter(r => r.source === 'google_shopping');
    const cseResults = results.filter(r => r.source === 'google_cse');

    expect(rainforestResults).toHaveLength(1);
    expect(googleShoppingResults).toHaveLength(1);
    expect(cseResults).toHaveLength(1);
  });
});

describe('Search API Request Building', () => {
  test('search request includes row_id', async () => {
    const fetchSpy = vi.fn(async () => 
      new Response(JSON.stringify({ results: [], providerStatuses: [] }), { status: 200 })
    );
    vi.stubGlobal('fetch', fetchSpy);

    // Import after mocking
    const { runSearchApiWithStatus } = await import('../utils/api');
    
    await runSearchApiWithStatus(null, 123);

    expect(fetchSpy).toHaveBeenCalled();
    const calls = fetchSpy.mock.calls as unknown as [string, RequestInit?][];
    const url = calls[0][0];
    expect(url).toContain('/api/search');
    expect(url).toContain('row_id=123');
  });

  test('search request can specify providers', async () => {
    const fetchSpy = vi.fn(async () => 
      new Response(JSON.stringify({ results: [], providerStatuses: [] }), { status: 200 })
    );
    vi.stubGlobal('fetch', fetchSpy);

    const { runSearchApiWithStatus } = await import('../utils/api');
    
    await runSearchApiWithStatus(null, 456, { providers: ['rainforest'] });

    expect(fetchSpy).toHaveBeenCalled();
    const calls = fetchSpy.mock.calls as unknown as [string, RequestInit?][];
    const url = calls[0][0];
    expect(url).toContain('providers=rainforest');
  });
});
