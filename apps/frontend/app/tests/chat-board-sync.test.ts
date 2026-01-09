import { renderHook, act } from '@testing-library/react';
import { useShoppingStore } from '../store';

// Mock fetch for the persistence calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ success: true }),
  })
) as jest.Mock;

describe('Chat-Board Synchronization Regression Test', () => {
  beforeEach(() => {
    const { result } = renderHook(() => useShoppingStore());
    act(() => {
      result.current.clearSearch();
      result.current.setRows([
        { id: 31, title: 'Montana State shirts under $50', status: 'sourcing', budget_max: 50, currency: 'USD' },
        { id: 32, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' }
      ]);
    });
    (global.fetch as jest.Mock).mockClear();
  });

  test('Clicking a card updates Zustand source of truth (Step 3a-3b)', () => {
    const { result } = renderHook(() => useShoppingStore());
    
    act(() => {
      // Simulate clicking card #31
      result.current.setCurrentQuery('Montana State shirts under $50');
      result.current.setActiveRowId(31);
    });

    expect(result.current.currentQuery).toBe('Montana State shirts under $50');
    expect(result.current.activeRowId).toBe(31);
  });

  test('selectOrCreateRow identifies existing row for extended query (Step 2)', () => {
    const { result } = renderHook(() => useShoppingStore());
    
    const rows = result.current.rows;
    
    // Case: User types "under $50" when "Montana State shirts" is active
    // The store should find the most relevant existing row instead of creating a new one
    const match = result.current.selectOrCreateRow('Montana State shirts under $50', rows);
    
    expect(match).toBeDefined();
    expect(match?.id).toBe(31);
  });

  test('selectOrCreateRow prioritizes active row for significant word overlap (Step 2)', () => {
    const { result } = renderHook(() => useShoppingStore());
    
    act(() => {
      // Simulate card #32 being active
      result.current.setActiveRowId(32);
    });

    const rows = result.current.rows;
    
    // Case from user: User is on "Montana State shirts" (#32) and says "actually can you show the sweatshirts?"
    // The query becomes "Montana State sweatshirt"
    const match = result.current.selectOrCreateRow('Montana State sweatshirt', rows);
    
    expect(match).toBeDefined();
    expect(match?.id).toBe(32); // Should reuse the active card instead of creating #33
  });
});
