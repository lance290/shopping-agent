import { describe, test, expect, beforeEach, vi } from 'vitest';
import { useShoppingStore } from '../store';

describe('Search Flow Logic', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      { id: 1, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' },
      { id: 2, title: 'Blue hoodies under $50', status: 'sourcing', budget_max: 50, currency: 'USD' },
    ]);
  });

  test('setIsSearching sets loading state', () => {
    const store = useShoppingStore.getState();
    expect(store.isSearching).toBe(false);

    store.setIsSearching(true);
    expect(useShoppingStore.getState().isSearching).toBe(true);

    store.setIsSearching(false);
    expect(useShoppingStore.getState().isSearching).toBe(false);
  });

  test('setSearchResults clears isSearching', () => {
    const store = useShoppingStore.getState();
    store.setIsSearching(true);
    
    store.setSearchResults([{ title: 'Test', price: 10, currency: 'USD', merchant: 'M', url: 'http://x.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }]);
    
    expect(useShoppingStore.getState().isSearching).toBe(false);
    expect(useShoppingStore.getState().searchResults).toHaveLength(1);
  });

  test('setRowResults clears isSearching', () => {
    const store = useShoppingStore.getState();
    store.setIsSearching(true);
    
    store.setRowResults(1, [{ title: 'Test', price: 10, currency: 'USD', merchant: 'M', url: 'http://x.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }]);
    
    expect(useShoppingStore.getState().isSearching).toBe(false);
    expect(useShoppingStore.getState().rowResults[1]).toHaveLength(1);
  });

  test('search flow: set query, set active row, run search, store results', () => {
    const store = useShoppingStore.getState();
    
    // Step 1: Set query
    store.setCurrentQuery('Montana State shirts');
    expect(useShoppingStore.getState().currentQuery).toBe('Montana State shirts');
    
    // Step 2: Set active row
    store.setActiveRowId(1);
    expect(useShoppingStore.getState().activeRowId).toBe(1);
    
    // Step 3: Start search
    store.setIsSearching(true);
    expect(useShoppingStore.getState().isSearching).toBe(true);
    
    // Step 4: Store results
    const results = [{ title: 'Montana Shirt', price: 25, currency: 'USD', merchant: 'Store', url: 'http://x.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }];
    store.setRowResults(1, results);
    
    // Verify final state
    const finalState = useShoppingStore.getState();
    expect(finalState.isSearching).toBe(false);
    expect(finalState.rowResults[1]).toHaveLength(1);
    expect(finalState.activeRowId).toBe(1);
  });

  test('card click flow: set query, active row, and cardClickQuery', () => {
    const store = useShoppingStore.getState();
    const row = store.rows[0];
    
    // Simulate card click
    store.setCurrentQuery(row.title);
    store.setActiveRowId(row.id);
    store.setCardClickQuery(row.title);
    
    const state = useShoppingStore.getState();
    expect(state.currentQuery).toBe('Montana State shirts');
    expect(state.activeRowId).toBe(1);
    expect(state.cardClickQuery).toBe('Montana State shirts');
  });

  test('refinement flow: update row title, keep same activeRowId', () => {
    const store = useShoppingStore.getState();
    
    // Initial state
    store.setActiveRowId(1);
    store.setCurrentQuery('Montana State shirts');
    
    // User refines: "under $50"
    store.updateRow(1, { title: 'Montana State shirts under $50' });
    store.setCurrentQuery('Montana State shirts under $50');
    
    const state = useShoppingStore.getState();
    expect(state.activeRowId).toBe(1); // Same row
    expect(state.rows.find(r => r.id === 1)?.title).toBe('Montana State shirts under $50');
    expect(state.currentQuery).toBe('Montana State shirts under $50');
  });
});

describe('Row Selection Logic', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setActiveRowId updates activeRowId', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(5);
    expect(useShoppingStore.getState().activeRowId).toBe(5);
  });

  test('setActiveRowId can be set to null', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(5);
    store.setActiveRowId(null);
    expect(useShoppingStore.getState().activeRowId).toBeNull();
  });

  test('clearSearch resets activeRowId to null', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(5);
    store.clearSearch();
    expect(useShoppingStore.getState().activeRowId).toBeNull();
  });
});

describe('Query State Management', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setCurrentQuery updates currentQuery', () => {
    const store = useShoppingStore.getState();
    store.setCurrentQuery('test query');
    expect(useShoppingStore.getState().currentQuery).toBe('test query');
  });

  test('setCurrentQuery can be empty string', () => {
    const store = useShoppingStore.getState();
    store.setCurrentQuery('test');
    store.setCurrentQuery('');
    expect(useShoppingStore.getState().currentQuery).toBe('');
  });

  test('clearSearch resets currentQuery', () => {
    const store = useShoppingStore.getState();
    store.setCurrentQuery('test query');
    store.clearSearch();
    expect(useShoppingStore.getState().currentQuery).toBe('');
  });
});
