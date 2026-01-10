import { describe, test, expect, beforeEach } from 'vitest';
import { useShoppingStore } from '../store';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ProcurementBoard from '../components/Board';

describe('ProcurementBoard Display Logic', () => {
  const mockProducts = [
    { title: 'Product A', price: 19.99, currency: 'USD', merchant: 'Store A', url: 'http://a.com', image_url: 'http://img.com/a.jpg', rating: 4.5, reviews_count: 100, shipping_info: 'Free shipping', source: 'test' },
    { title: 'Product B', price: 29.99, currency: 'USD', merchant: 'Store B', url: 'http://b.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' },
  ];

  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      { id: 1, title: 'Montana State shirts', status: 'sourcing', budget_max: null, currency: 'USD' },
      { id: 2, title: 'Blue hoodies', status: 'sourcing', budget_max: 50, currency: 'USD' },
    ]);
  });

  test('displays rowResults when activeRowId is set', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Product A')).toBeDefined();
    expect(screen.getByText('Product B')).toBeDefined();
    expect(screen.getByText('2 products found')).toBeDefined();
  });

  test('displays row title in header when row is active', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Montana State shirts')).toBeDefined();
  });

  test('displays empty state when no results and no active row', () => {
    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Ask for something in the chat or select a request')).toBeDefined();
  });

  test('displays loading state when isSearching is true', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setCurrentQuery('test');
    store.setIsSearching(true);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Searching products...')).toBeDefined();
  });

  test('product cards link to product URL', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    const links = screen.getAllByRole('link');
    expect(links[0].getAttribute('href')).toBe('http://a.com');
  });

  test('product cards show price formatted correctly', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('$19.99')).toBeDefined();
    expect(screen.getByText('$29.99')).toBeDefined();
  });

  test('product cards show merchant name', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Store A')).toBeDefined();
    expect(screen.getByText('Store B')).toBeDefined();
  });

  test('product cards show rating when available', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('4.5 (100)')).toBeDefined();
  });

  test('product cards show shipping info when available', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);
    store.setRowResults(1, mockProducts);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Free shipping')).toBeDefined();
  });

  test('switching active row shows different results', () => {
    const store = useShoppingStore.getState();
    const productsRow1 = [{ title: 'Row 1 Product', price: 10, currency: 'USD', merchant: 'M1', url: 'http://1.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }];
    const productsRow2 = [{ title: 'Row 2 Product', price: 20, currency: 'USD', merchant: 'M2', url: 'http://2.com', image_url: null, rating: null, reviews_count: null, shipping_info: null, source: 'test' }];

    store.setRowResults(1, productsRow1);
    store.setRowResults(2, productsRow2);
    store.setActiveRowId(1);

    const { rerender } = render(React.createElement(ProcurementBoard));
    expect(screen.getByText('Row 1 Product')).toBeDefined();

    // Switch to row 2
    store.setActiveRowId(2);
    rerender(React.createElement(ProcurementBoard));
    expect(screen.getByText('Row 2 Product')).toBeDefined();
  });

  test('falls back to searchResults when no activeRowId', () => {
    const store = useShoppingStore.getState();
    store.setSearchResults(mockProducts);
    store.setCurrentQuery('test query');

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Product A')).toBeDefined();
    expect(screen.getByText('test query')).toBeDefined();
  });
});
