import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import RowStrip from '../components/RowStrip';
import { useShoppingStore, Row } from '../store';

// Mock dependencies
vi.mock('../utils/api', () => ({
  fetchSingleRowFromDb: vi.fn(),
  runSearchApiWithStatus: vi.fn().mockResolvedValue({
    results: [],
    providerStatuses: [],
    userMessage: null,
  }),
  selectOfferForRow: vi.fn(),
  toggleLikeApi: vi.fn(),
  fetchLikesApi: vi.fn(async () => []),
  createCommentApi: vi.fn(),
  fetchCommentsApi: vi.fn(async () => []),
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('displays error message from store', () => {
    const errorMessage = "Rate limit exceeded. Please try again later.";
    
    // Set up the store with an error
    useShoppingStore.setState({ rowSearchErrors: { 1: errorMessage } });

    render(React.createElement(RowStrip, {
      row: mockRow,
      offers: [],
      isActive: false,
      onSelect: () => {},
    }));

    // Verify error is displayed
    expect(screen.getByText(/Rate limit exceeded/i)).toBeDefined();
  });

  test('displays "No offers found" when no error and no results', () => {
    const store = useShoppingStore.getState();
    
    // Set up the store with NO error and NO results
    store.setRowResults(1, [], undefined, false, undefined);

    render(React.createElement(RowStrip, {
      row: mockRow,
      offers: [],
      isActive: false,
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
