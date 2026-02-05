import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import RowStrip from '../components/RowStrip';
import { useShoppingStore, Row } from '../store';

// Mock dependencies
vi.mock('../utils/api', () => ({
  fetchSingleRowFromDb: vi.fn().mockResolvedValue(null),
  runSearchApiWithStatus: vi.fn(() => Promise.resolve({
    results: [],
    providerStatuses: [],
    userMessage: null,
  })),
  selectOfferForRow: vi.fn().mockResolvedValue(true),
  toggleLikeApi: vi.fn().mockResolvedValue(true),
  fetchLikesApi: vi.fn(() => Promise.resolve([])),
  createCommentApi: vi.fn().mockResolvedValue(true),
  fetchCommentsApi: vi.fn(() => Promise.resolve([])),
}));

describe('RowStrip Error Display', () => {
  const mockRow: Row = {
    id: 1,
    title: 'Test Product',
    status: 'complete',
    budget_max: null,
    currency: 'USD',
  };

  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([mockRow]);
    // Ensure no previous state leaks
    useShoppingStore.getState().clearRowResults(1);
    useShoppingStore.getState().setMoreResultsIncoming(1, false);
    // Prevent auto-refresh by marking as already loaded
    useShoppingStore.getState().setIsSearching(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('displays error message from store', () => {
    const errorMessage = "Rate limit exceeded. Please try again later.";

    // Use a row with status other than 'sourcing' to show error message
    const rowWithOpenStatus = { ...mockRow, status: 'open' as const };

    // First render with isActive=false to prevent auto-refresh
    const { rerender } = render(React.createElement(RowStrip, {
      row: rowWithOpenStatus,
      offers: [],
      isActive: false,
      onSelect: () => {},
    }));

    // Set up the store with an error after initial render
    useShoppingStore.setState({ rowSearchErrors: { 1: errorMessage } });

    // Now make it active to show the error
    rerender(React.createElement(RowStrip, {
      row: rowWithOpenStatus,
      offers: [],
      isActive: true,
      onSelect: () => {},
    }));

    // Verify error is displayed
    expect(screen.getByText(/Rate limit exceeded/i)).toBeDefined();
  });

  test('displays "No offers found" when no error and no results', () => {
    const store = useShoppingStore.getState();

    // Use a row with status 'open' instead of 'sourcing' to see "No offers found"
    const rowWithOpenStatus = { ...mockRow, status: 'open' as const };

    // First render with isActive=false to prevent auto-refresh
    const { rerender } = render(React.createElement(RowStrip, {
      row: rowWithOpenStatus,
      offers: [],
      isActive: false,
      onSelect: () => {},
    }));

    // Set up the store with NO error and NO results
    store.setRowResults(1, [], undefined, false, undefined);

    // Now make it active
    rerender(React.createElement(RowStrip, {
      row: rowWithOpenStatus,
      offers: [],
      isActive: true,
      onSelect: () => {},
    }));

    // Verify default empty state
    expect(screen.getByText(/No offers found/i)).toBeDefined();
    // Ensure no error message
    expect(screen.queryByText(/Rate limit/i)).toBeNull();
  });

  test('displays "Sourcing offers..." when loading', () => {
    const store = useShoppingStore.getState();
    
    // Set up store in loading state (moreIncoming=true)
    store.setMoreResultsIncoming(1, true);

    render(React.createElement(RowStrip, {
      row: mockRow,
      offers: [],
      isActive: false,
      onSelect: () => {},
    }));

    expect(screen.getByText(/Sourcing offers/i)).toBeDefined();
  });
});
