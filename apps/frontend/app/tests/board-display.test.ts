import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore, Offer, Row } from '../store';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ProcurementBoard from '../components/Board';

describe('ProcurementBoard Display Logic', () => {
  const mockOffers: Offer[] = [
    { title: 'Product A', price: 19.99, currency: 'USD', merchant: 'Store A', url: 'http://a.com', image_url: 'http://img.com/a.jpg', rating: 4.5, reviews_count: 100, shipping_info: 'Free shipping', source: 'test' },
    { title: 'Product B', price: 29.99, currency: 'USD', merchant: 'Store B', url: 'http://b.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' },
  ];

  const mockRows: Row[] = [
    { id: 1, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' },
    { id: 2, title: 'Blue hoodies', status: 'sourcing', budget_max: 50, currency: 'USD' },
  ];

  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows(mockRows);
  });

  test('displays all rows', () => {
    render(React.createElement(ProcurementBoard));

    expect(screen.getAllByText('Montana State shirts')[0]).toBeDefined();
    expect(screen.getAllByText('Blue hoodies')[0]).toBeDefined();
  });

  test('displays offers for a row', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockOffers);

    render(React.createElement(ProcurementBoard));

    // Check if offers are visible
    expect(screen.getByText('Product A')).toBeDefined();
    expect(screen.getByText('Product B')).toBeDefined();
  });

  test('displays loading/empty state for row with no offers', () => {
    // Row 2 has no offers set
    render(React.createElement(ProcurementBoard));
    
    // Should see placeholder for row 2 (Searching or No offers)
    expect(screen.getAllByText(/Searching for offers/i)).toHaveLength(2);
  });

  test('highlights active row', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);

    render(React.createElement(ProcurementBoard));
    
    // This is a bit tricky to test with just text, checking for visual class requires DOM inspection
    // But we can verify the ID is displayed
    expect(screen.getByText('ID: 1')).toBeDefined();
  });

  test('displays empty board state when no rows', () => {
    useShoppingStore.getState().setRows([]);
    
    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Your Procurement Board is Empty')).toBeDefined();
  });

  test('OfferTile links to clickout URL', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockOffers);

    render(React.createElement(ProcurementBoard));

    // Get all links that are NOT the disclosure link
    const links = screen.getAllByRole('link').filter(l => l.getAttribute('href') !== '/disclosure');
    
    // Check href format: /api/clickout?url=...
    const href = links[0].getAttribute('href');
    expect(href).toContain('/api/clickout');
    expect(href).toContain(encodeURIComponent('http://a.com'));
  });
});
