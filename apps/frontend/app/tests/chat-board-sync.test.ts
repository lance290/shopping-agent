import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';

describe('Chat-Board Synchronization', () => {
  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearSearch();
    store.setRows([
      { id: 31, title: 'Montana State shirts under $50', status: 'sourcing', budget_max: 50, currency: 'USD' },
      { id: 32, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' }
    ]);
  });

  test('Clicking a card updates Zustand source of truth (Step 3a-3b)', () => {
    // Simulate clicking card #31
    useShoppingStore.getState().setCurrentQuery('Montana State shirts under $50');
    useShoppingStore.getState().setActiveRowId(31);

    // Get fresh state after mutations
    const state = useShoppingStore.getState();
    expect(state.currentQuery).toBe('Montana State shirts under $50');
    expect(state.activeRowId).toBe(31);
  });

  test('Card click sets cardClickQuery to trigger chat append (Step 3c)', () => {
    // Simulate card click flow from Board.tsx
    useShoppingStore.getState().setCurrentQuery('Montana State shirts under $50');
    useShoppingStore.getState().setActiveRowId(31);
    useShoppingStore.getState().setCardClickQuery('Montana State shirts under $50');

    const state = useShoppingStore.getState();
    expect(state.cardClickQuery).toBe('Montana State shirts under $50');
    
    // After Chat.tsx processes it, it should be cleared
    useShoppingStore.getState().setCardClickQuery(null);
    expect(useShoppingStore.getState().cardClickQuery).toBeNull();
  });

  test('selectOrCreateRow identifies existing row for extended query (Step 2)', () => {
    const store = useShoppingStore.getState();
    const rows = store.rows;
    
    // Case: User types "under $50" when "Montana State shirts" is active
    const match = store.selectOrCreateRow('Montana State shirts under $50', rows);
    
    expect(match).toBeDefined();
    expect(match?.id).toBe(31);
  });

  test('selectOrCreateRow prioritizes active row for significant word overlap (Step 2)', () => {
    const store = useShoppingStore.getState();
    
    // Simulate card #32 being active
    store.setActiveRowId(32);
    const rows = store.rows;
    
    // Case: User is on "Montana State shirts" (#32) and says "actually can you show the sweatshirts?"
    const match = store.selectOrCreateRow('Montana State sweatshirt', rows);
    
    expect(match).toBeDefined();
    expect(match?.id).toBe(32); // Should reuse the active card
  });
});
