import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';

describe('Zustand Store - Per-Row Results', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      { id: 1, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' },
      { id: 2, title: 'Blue hoodies', status: 'sourcing', budget_max: 50, currency: 'USD' },
      { id: 3, title: 'Red sneakers', status: 'closed', budget_max: 100, currency: 'USD' },
    ]);
  });

  const mockProducts = [
    { title: 'Product 1', price: 19.99, currency: 'USD', merchant: 'Store A', url: 'http://a.com', image_url: null, rating: 4.5, reviews_count: 100, shipping_info: 'Free', source: 'test' },
    { title: 'Product 2', price: 29.99, currency: 'USD', merchant: 'Store B', url: 'http://b.com', image_url: null, rating: 4.0, reviews_count: 50, shipping_info: null, source: 'test' },
  ];

  test('setRowResults stores results under specific row ID', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockProducts);

    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toHaveLength(2);
    expect(state.rowResults[1][0].title).toBe('Product 1');
    expect(state.rowResults[2]).toBeUndefined();
  });

  test('setRowResults for multiple rows keeps them separate', () => {
    const store = useShoppingStore.getState();
    const productsRow1 = [mockProducts[0]];
    const productsRow2 = [mockProducts[1]];

    store.setRowResults(1, productsRow1);
    store.setRowResults(2, productsRow2);

    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toHaveLength(1);
    expect(state.rowResults[1][0].title).toBe('Product 1');
    expect(state.rowResults[2]).toHaveLength(1);
    expect(state.rowResults[2][0].title).toBe('Product 2');
  });

  test('setRowResults clears isSearching flag', () => {
    const store = useShoppingStore.getState();
    store.setIsSearching(true);
    expect(useShoppingStore.getState().isSearching).toBe(true);

    store.setRowResults(1, mockProducts);
    expect(useShoppingStore.getState().isSearching).toBe(false);
  });

  test('clearRowResults removes results for specific row only', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockProducts);
    store.setRowResults(2, [mockProducts[0]]);

    store.clearRowResults(1);

    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toBeUndefined();
    expect(state.rowResults[2]).toHaveLength(1);
  });

  test('clearSearch resets all rowResults', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockProducts);
    store.setRowResults(2, [mockProducts[0]]);
    store.setActiveRowId(1);
    store.setCurrentQuery('test query');

    store.clearSearch();

    const state = useShoppingStore.getState();
    expect(state.rowResults).toEqual({});
    expect(state.searchResults).toEqual([]);
    expect(state.activeRowId).toBeNull();
    expect(state.currentQuery).toBe('');
  });

  test('removeRow clears activeRowId if deleted row was active', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    expect(useShoppingStore.getState().activeRowId).toBe(1);

    store.removeRow(1);

    const state = useShoppingStore.getState();
    expect(state.activeRowId).toBeNull();
    expect(state.rows.find(r => r.id === 1)).toBeUndefined();
  });

  test('removeRow keeps activeRowId if different row deleted', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);

    store.removeRow(2);

    const state = useShoppingStore.getState();
    expect(state.activeRowId).toBe(1);
    expect(state.rows).toHaveLength(2);
  });

  test('updateRow modifies row in place', () => {
    const store = useShoppingStore.getState();
    store.updateRow(1, { title: 'Montana State shirts under $50', budget_max: 50 });

    const state = useShoppingStore.getState();
    const row = state.rows.find(r => r.id === 1);
    expect(row?.title).toBe('Montana State shirts under $50');
    expect(row?.budget_max).toBe(50);
    expect(row?.status).toBe('sourcing'); // unchanged
  });

  test('addRow prepends to rows array (newest first)', () => {
    const store = useShoppingStore.getState();
    const newRow = { id: 4, title: 'New item', status: 'sourcing', budget_max: null, currency: 'USD' };

    store.addRow(newRow);

    const state = useShoppingStore.getState();
    expect(state.rows).toHaveLength(4);
    expect(state.rows[0].id).toBe(4); // New row should be first
    expect(state.rows[0].last_engaged_at).toBeDefined(); // Should have engagement timestamp
  });
});

describe('Zustand Store - selectOrCreateRow', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      { id: 1, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' },
      { id: 2, title: 'Blue hoodies under $50', status: 'sourcing', budget_max: 50, currency: 'USD' },
    ]);
  });

  test('returns exact match', () => {
    const store = useShoppingStore.getState();
    const match = store.selectOrCreateRow('Montana State shirts', store.rows);
    expect(match?.id).toBe(1);
  });

  test('returns null for completely new query', () => {
    const store = useShoppingStore.getState();
    const match = store.selectOrCreateRow('Red sneakers', store.rows);
    expect(match).toBeNull();
  });

  test('matches when query extends existing row title', () => {
    const store = useShoppingStore.getState();
    const match = store.selectOrCreateRow('Montana State shirts under $50', store.rows);
    expect(match?.id).toBe(1);
  });

  test('matches when query is subset of existing row title', () => {
    const store = useShoppingStore.getState();
    const match = store.selectOrCreateRow('Blue hoodies', store.rows);
    expect(match?.id).toBe(2);
  });

  test('prioritizes active row with word overlap', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    
    // "Montana sweatshirt" has word overlap with "Montana State shirts"
    const match = store.selectOrCreateRow('Montana State sweatshirt', store.rows);
    expect(match?.id).toBe(1);
  });

  test('returns null when active row has no overlap with query', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    
    // "Red sneakers" has no overlap with "Montana State shirts"
    const match = store.selectOrCreateRow('Red sneakers size 10', store.rows);
    expect(match).toBeNull();
  });
});

describe('Zustand Store - cardClickQuery', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setCardClickQuery sets the value', () => {
    const store = useShoppingStore.getState();
    store.setCardClickQuery('Test query');
    expect(useShoppingStore.getState().cardClickQuery).toBe('Test query');
  });

  test('setCardClickQuery can be set to null', () => {
    const store = useShoppingStore.getState();
    store.setCardClickQuery('Test query');
    store.setCardClickQuery(null);
    expect(useShoppingStore.getState().cardClickQuery).toBeNull();
  });

  test('clearSearch resets cardClickQuery', () => {
    const store = useShoppingStore.getState();
    store.setCardClickQuery('Test query');
    store.clearSearch();
    expect(useShoppingStore.getState().cardClickQuery).toBeNull();
  });
});
