import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';

// Mock the store creation to get a fresh instance for each test if needed,
// but zustand stores are singletons. We'll rely on beforeEach to reset.

describe('ShoppingStore Search Errors', () => {
  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearRowResults(1);
    store.setIsSearching(false);
  });

  test('setRowResults sets userMessage in rowSearchErrors', () => {
    const store = useShoppingStore.getState();
    const mockResults: any[] = [];
    const message = "Search failed due to rate limiting";

    store.setRowResults(1, mockResults, undefined, false, message);

    const state = useShoppingStore.getState();
    expect(state.rowSearchErrors[1]).toBe(message);
    expect(state.rowResults[1]).toEqual([]);
    expect(state.isSearching).toBe(false);
  });

  test('setRowResults clears previous error if new message is null/undefined', () => {
    const store = useShoppingStore.getState();
    const message = "Initial error";
    store.setRowResults(1, [], undefined, false, message);
    
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe(message);

    // Now set with no message (undefined implicitly)
    store.setRowResults(1, [], undefined, false);
    
    // It should effectively remain or clear depending on implementation? 
    // Looking at implementation: 
    // rowSearchErrors: { ...state.rowSearchErrors, [rowId]: userMessage || null },
    // So undefined userMessage becomes null.
    
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBeNull();
  });

  test('appendRowResults sets userMessage', () => {
    const store = useShoppingStore.getState();
    const message = "Streaming error";
    
    store.appendRowResults(1, [], undefined, true, message);
    
    const state = useShoppingStore.getState();
    expect(state.rowSearchErrors[1]).toBe(message);
    expect(state.isSearching).toBe(true); // moreIncoming=true
  });

  test('appendRowResults does not overwrite error with undefined if not provided', () => {
    const store = useShoppingStore.getState();
    const message = "Initial error";
    
    // Set initial error
    store.appendRowResults(1, [], undefined, true, message);
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe(message);

    // Append more results without error message
    // Implementation: 
    // rowSearchErrors: userMessage !== undefined ? { ...state.rowSearchErrors, [rowId]: userMessage } : state.rowSearchErrors
    store.appendRowResults(1, [], undefined, true);

    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe(message);
  });

  test('clearRowResults clears errors', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [], undefined, false, "Some error");
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe("Some error");

    store.clearRowResults(1);
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBeUndefined();
  });
});
