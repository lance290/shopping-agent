import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';
import { useShoppingStore, Offer, Row } from '../store';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ProcurementBoard from '../components/Board';
import RequestTile from '../components/RequestTile';

vi.mock('../utils/api', async () => {
  const actual = await vi.importActual<any>('../utils/api');
  return {
    ...actual,
    fetchRowsFromDb: vi.fn(async () => []),
  };
});

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

  afterEach(() => {
    vi.restoreAllMocks();
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

    // Should see placeholder for rows with no offers (status: "sourcing")
    expect(screen.getAllByText(/Sourcing offers/i)).toHaveLength(2);
  });

  test('highlights active row', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);

    render(React.createElement(ProcurementBoard));

    // Check that the row ID is displayed (format: "#1")
    expect(screen.getByText('#1')).toBeDefined();
  });

  test('displays empty board state when no rows', () => {
    useShoppingStore.getState().setRows([]);

    render(React.createElement(ProcurementBoard));

    expect(screen.getByText('Find anything')).toBeDefined();
  });

  test('OfferTile links to clickout URL', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, mockOffers);

    render(React.createElement(ProcurementBoard));

    // Get only clickout links (exclude disclosure, navigation, etc.)
    const links = screen.getAllByRole('link').filter(l => (l.getAttribute('href') || '').includes('/api/clickout'));

    // Check href format: /api/clickout?url=...
    const href = links[0].getAttribute('href');
    expect(href).toContain('/api/clickout');
    expect(href).toContain(encodeURIComponent('http://a.com'));
  });

  test('Options Refresh triggers regenerate_choice_factors PATCH when factors missing', async () => {
    const fetchSpy = vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal('fetch', fetchSpy as any);

    const row: Row = {
      id: 123,
      title: 'Nintendo Switch 2',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
      choice_factors: undefined,
      choice_answers: undefined,
    };

    render(React.createElement(RequestTile, { row }));

    expect(screen.getByText(/Analyzing request/i)).toBeDefined();

    const refresh = screen.getByTitle('Refresh options');
    fireEvent.click(refresh);

    type FetchCall = [any, any];
    const calls = fetchSpy.mock.calls as unknown as FetchCall[];
    const patchCall = calls.find((c) => String(c[0]).includes(`/api/rows?id=${row.id}`));
    expect(patchCall).toBeDefined();

    const init = patchCall?.[1] as RequestInit | undefined;
    expect(init?.method).toBe('PATCH');
    expect(String(init?.body)).toContain('regenerate_choice_factors');
  });

  test('Options Refresh triggers search after regenerating factors', async () => {
    const fetchSpy = vi.fn(async (url: string) => {
      if (url.includes('/api/rows')) {
        return new Response(JSON.stringify({}), { status: 200 });
      }
      if (url.includes('/api/search')) {
        return new Response(JSON.stringify({ results: [], providerStatuses: [] }), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });
    vi.stubGlobal('fetch', fetchSpy as any);

    const row: Row = {
      id: 456,
      title: 'Bianchi bicycle',
      status: 'sourcing',
      budget_max: 5000,
      currency: 'USD',
      choice_factors: JSON.stringify({ brand: { options: ['Bianchi'] } }),
      choice_answers: JSON.stringify({ brand: 'Bianchi', min_price: 500 }),
    };

    render(React.createElement(RequestTile, { row }));

    const refresh = screen.getByTitle('Refresh options');
    fireEvent.click(refresh);

    // Wait for async operations
    await vi.waitFor(() => {
      type FetchCall = [string, RequestInit?];
      const calls = fetchSpy.mock.calls as unknown as FetchCall[];
      const searchCall = calls.find((c) => String(c[0]).includes('/api/search'));
      expect(searchCall).toBeDefined();
    }, { timeout: 1000 });
  });

  test('Options card displays price range from choice_answers', () => {
    const row: Row = {
      id: 789,
      title: 'Road Bike',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
      choice_factors: JSON.stringify({
        min_price: { type: 'number', label: 'Min Price' },
        max_price: { type: 'number', label: 'Max Price' },
      }),
      choice_answers: JSON.stringify({ min_price: 500, max_price: 2000 }),
    };

    render(React.createElement(RequestTile, { row }));

    // Should display the price values
    expect(screen.getByDisplayValue('500')).toBeDefined();
  });

  test('Options card displays multiselect amenities', () => {
    const row: Row = {
      id: 890,
      title: 'Private jet charter',
      status: 'sourcing',
      budget_max: null,
      currency: 'USD',
      choice_factors: JSON.stringify([
        {
          name: 'required_amenities',
          label: 'Required Amenities',
          type: 'multiselect',
          options: ['WiFi', 'Catering', 'Entertainment System', 'Private Lavatory'],
          required: false,
        }
      ]),
      choice_answers: JSON.stringify({ required_amenities: ['WiFi', 'Catering'] }),
    };

    render(React.createElement(RequestTile, { row }));

    // Should display all amenity options as checkboxes
    expect(screen.getByText('WiFi')).toBeDefined();
    expect(screen.getByText('Catering')).toBeDefined();
    expect(screen.getByText('Entertainment System')).toBeDefined();
    expect(screen.getByText('Private Lavatory')).toBeDefined();

    // Check that WiFi and Catering checkboxes are checked
    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
    const wifiCheckbox = checkboxes.find((cb) => {
      const label = cb.parentElement?.textContent;
      return label?.includes('WiFi');
    });
    const cateringCheckbox = checkboxes.find((cb) => {
      const label = cb.parentElement?.textContent;
      return label?.includes('Catering');
    });

    expect(wifiCheckbox?.checked).toBe(true);
    expect(cateringCheckbox?.checked).toBe(true);
  });
});
