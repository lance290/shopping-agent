import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';

describe('RequestsSidebar Logic', () => {
  beforeEach(() => {
    const store = useShoppingStore.getState();
    store.clearSearch();
    store.setRows([
      { id: 101, title: 'Italian bicycles', status: 'sourcing', budget_max: 4000, currency: 'USD' },
      { id: 102, title: 'Espresso machine', status: 'closed', budget_max: 500, currency: 'USD' }
    ]);
  });

  test('Sidebar card click triggers correct store updates', () => {
    const store = useShoppingStore.getState();
    const row = store.rows.find(r => r.id === 101)!;

    // Simulate handleCardClick logic from RequestsSidebar
    store.setCurrentQuery(row.title);
    store.setActiveRowId(row.id);
    store.setCardClickQuery(row.title);

    const updatedState = useShoppingStore.getState();
    
    // Verify 3b: Query and Active Row updated
    expect(updatedState.currentQuery).toBe('Italian bicycles');
    expect(updatedState.activeRowId).toBe(101);
    
    // Verify 3c: cardClickQuery set (triggers Chat append)
    expect(updatedState.cardClickQuery).toBe('Italian bicycles');
  });

  test('Sidebar delete row logic updates store', () => {
    const store = useShoppingStore.getState();
    
    // Simulate deleteRow logic
    store.removeRow(102);

    const updatedState = useShoppingStore.getState();
    expect(updatedState.rows).toHaveLength(1);
    expect(updatedState.rows.find(r => r.id === 102)).toBeUndefined();
  });
});
