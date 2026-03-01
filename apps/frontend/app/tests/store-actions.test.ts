import { describe, test, expect, beforeEach, vi, afterEach } from 'vitest';
import { useShoppingStore } from '../store';
import type { Row, Offer } from '../store';

const mockRow = (overrides: Partial<Row> = {}): Row => ({
  id: 1, title: 'Test Row', status: 'sourcing', budget_max: null, currency: 'USD',
  ...overrides,
});

const mockOffer = (overrides: Partial<Offer> = {}): Offer => ({
  title: 'Product', price: 19.99, currency: 'USD', merchant: 'Store',
  url: 'https://example.com/p', image_url: null, rating: 4.5,
  reviews_count: 100, shipping_info: 'Free', source: 'test',
  ...overrides,
});

describe('Zustand Store - Project Management', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.setState({ projects: [] });
  });

  test('setProjects replaces all projects', () => {
    const store = useShoppingStore.getState();
    store.setProjects([
      { id: 1, title: 'Project A', created_at: '', updated_at: '' },
      { id: 2, title: 'Project B', created_at: '', updated_at: '' },
    ]);
    expect(useShoppingStore.getState().projects).toHaveLength(2);
  });

  test('addProject prepends to list', () => {
    const store = useShoppingStore.getState();
    store.setProjects([{ id: 1, title: 'Old', created_at: '', updated_at: '' }]);
    store.addProject({ id: 2, title: 'New', created_at: '', updated_at: '' });

    const projects = useShoppingStore.getState().projects;
    expect(projects).toHaveLength(2);
    expect(projects[0].id).toBe(2);
  });

  test('removeProject filters by id', () => {
    const store = useShoppingStore.getState();
    store.setProjects([
      { id: 1, title: 'A', created_at: '', updated_at: '' },
      { id: 2, title: 'B', created_at: '', updated_at: '' },
    ]);
    store.removeProject(1);

    const projects = useShoppingStore.getState().projects;
    expect(projects).toHaveLength(1);
    expect(projects[0].id).toBe(2);
  });
});

describe('Zustand Store - Target Project Filtering', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, title: 'Row in proj', project_id: 10 }),
      mockRow({ id: 2, title: 'Row outside proj', project_id: null }),
      mockRow({ id: 3, title: 'Another in proj', project_id: 10 }),
    ]);
  });

  test('selectOrCreateRow filters by targetProjectId when set', () => {
    const store = useShoppingStore.getState();
    store.setTargetProjectId(10);

    const match = store.selectOrCreateRow('Row in proj', store.rows);
    expect(match?.id).toBe(1);
  });

  test('selectOrCreateRow returns null when no match in target project', () => {
    const store = useShoppingStore.getState();
    store.setTargetProjectId(10);

    const match = store.selectOrCreateRow('Row outside proj', store.rows);
    expect(match).toBeNull();
  });

  test('selectOrCreateRow searches all rows when no target project', () => {
    const store = useShoppingStore.getState();
    store.setTargetProjectId(null);

    const match = store.selectOrCreateRow('Row outside proj', store.rows);
    expect(match?.id).toBe(2);
  });
});

describe('Zustand Store - Offer Sort Modes', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setRowOfferSort stores sort mode', () => {
    const store = useShoppingStore.getState();
    store.setRowOfferSort(1, 'price_asc');
    expect(useShoppingStore.getState().rowOfferSort[1]).toBe('price_asc');
  });

  test('setRowOfferSort price_desc', () => {
    const store = useShoppingStore.getState();
    store.setRowOfferSort(1, 'price_desc');
    expect(useShoppingStore.getState().rowOfferSort[1]).toBe('price_desc');
  });

  test('setRowOfferSort original removes the key', () => {
    const store = useShoppingStore.getState();
    store.setRowOfferSort(1, 'price_asc');
    expect(useShoppingStore.getState().rowOfferSort[1]).toBe('price_asc');

    store.setRowOfferSort(1, 'original');
    expect(useShoppingStore.getState().rowOfferSort[1]).toBeUndefined();
  });

  test('sort modes are independent per row', () => {
    const store = useShoppingStore.getState();
    store.setRowOfferSort(1, 'price_asc');
    store.setRowOfferSort(2, 'price_desc');

    const state = useShoppingStore.getState();
    expect(state.rowOfferSort[1]).toBe('price_asc');
    expect(state.rowOfferSort[2]).toBe('price_desc');
  });
});

describe('Zustand Store - appendRowResults', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('appends new results to existing', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [mockOffer({ url: 'https://a.com' })]);
    store.appendRowResults(1, [mockOffer({ url: 'https://b.com', title: 'Product B' })]);

    const results = useShoppingStore.getState().rowResults[1];
    expect(results).toHaveLength(2);
    expect(results[1].title).toBe('Product B');
  });

  test('deduplicates by URL', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [mockOffer({ url: 'https://a.com' })]);
    store.appendRowResults(1, [mockOffer({ url: 'https://a.com', title: 'Dup' })]);

    const results = useShoppingStore.getState().rowResults[1];
    expect(results).toHaveLength(1);
  });

  test('appends to empty row', () => {
    const store = useShoppingStore.getState();
    store.appendRowResults(5, [mockOffer({ url: 'https://c.com' })]);

    const results = useShoppingStore.getState().rowResults[5];
    expect(results).toHaveLength(1);
  });

  test('tracks moreResultsIncoming', () => {
    const store = useShoppingStore.getState();
    store.appendRowResults(1, [mockOffer()], undefined, true);
    expect(useShoppingStore.getState().moreResultsIncoming[1]).toBe(true);

    store.appendRowResults(1, [], undefined, false);
    expect(useShoppingStore.getState().moreResultsIncoming[1]).toBe(false);
  });

  test('stores provider statuses', () => {
    const store = useShoppingStore.getState();
    const status = { provider_id: 'amazon', status: 'ok' as const, result_count: 5 };
    store.appendRowResults(1, [], [status]);

    expect(useShoppingStore.getState().rowProviderStatuses[1]).toHaveLength(1);
    expect(useShoppingStore.getState().rowProviderStatuses[1][0].provider_id).toBe('amazon');
  });

  test('accumulates provider statuses across appends', () => {
    const store = useShoppingStore.getState();
    store.appendRowResults(1, [], [{ provider_id: 'a', status: 'ok' as const, result_count: 3 }]);
    store.appendRowResults(1, [], [{ provider_id: 'b', status: 'ok' as const, result_count: 2 }]);

    expect(useShoppingStore.getState().rowProviderStatuses[1]).toHaveLength(2);
  });

  test('sets userMessage in rowSearchErrors', () => {
    const store = useShoppingStore.getState();
    store.appendRowResults(1, [], undefined, false, 'No results found for this query');
    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe('No results found for this query');
  });
});

describe('Zustand Store - setRowResults merge logic', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('preserves like state when merging results', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [
      mockOffer({ bid_id: 10, is_liked: true, liked_at: '2026-01-01' }),
    ]);

    // New results come in with explicit is_liked: false
    store.setRowResults(1, [
      mockOffer({ bid_id: 10, is_liked: false }),
    ]);

    const results = useShoppingStore.getState().rowResults[1];
    expect(results[0].is_liked).toBe(false); // new data takes precedence when is_liked is explicitly provided
  });

  test('preserves service providers when incoming has none', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [
      mockOffer({ is_service_provider: true, title: 'JetCo', url: 'mailto:jet@co.com' }),
    ]);

    store.setRowResults(1, [
      mockOffer({ title: 'Widget', url: 'https://shop.com' }),
    ]);

    const results = useShoppingStore.getState().rowResults[1];
    expect(results).toHaveLength(2);
    expect(results[0].is_service_provider).toBe(true);
  });

  test('replaces service providers when incoming has them', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [
      mockOffer({ is_service_provider: true, title: 'OldVendor', url: 'mailto:old@v.com' }),
    ]);

    store.setRowResults(1, [
      mockOffer({ is_service_provider: true, title: 'NewVendor', url: 'mailto:new@v.com' }),
    ]);

    const results = useShoppingStore.getState().rowResults[1];
    const serviceProviders = results.filter(r => r.is_service_provider);
    expect(serviceProviders).toHaveLength(1);
    expect(serviceProviders[0].title).toBe('NewVendor');
  });
});

describe('Zustand Store - moreResultsIncoming', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setMoreResultsIncoming updates per-row flag', () => {
    const store = useShoppingStore.getState();
    store.setMoreResultsIncoming(1, true);
    expect(useShoppingStore.getState().moreResultsIncoming[1]).toBe(true);

    store.setMoreResultsIncoming(1, false);
    expect(useShoppingStore.getState().moreResultsIncoming[1]).toBe(false);
  });

  test('setRowResults with moreIncoming=true keeps isSearching', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [mockOffer()], undefined, true);
    expect(useShoppingStore.getState().isSearching).toBe(true);
  });

  test('setRowResults with moreIncoming=false clears isSearching', () => {
    const store = useShoppingStore.getState();
    store.setIsSearching(true);
    store.setRowResults(1, [mockOffer()], undefined, false);
    expect(useShoppingStore.getState().isSearching).toBe(false);
  });
});

describe('Zustand Store - setActiveRowId engagement tracking', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      mockRow({ id: 1 }),
      mockRow({ id: 2 }),
    ]);
  });

  test('sets last_engaged_at on the activated row', () => {
    const before = Date.now();
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);

    const row = useShoppingStore.getState().rows.find(r => r.id === 1);
    expect(row?.last_engaged_at).toBeDefined();
    expect(row!.last_engaged_at!).toBeGreaterThanOrEqual(before);
  });

  test('does not change other rows engagement', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(1);

    const row2 = useShoppingStore.getState().rows.find(r => r.id === 2);
    expect(row2?.last_engaged_at).toBeUndefined();
  });

  test('setActiveRowId(null) does not crash', () => {
    const store = useShoppingStore.getState();
    store.setActiveRowId(null);
    expect(useShoppingStore.getState().activeRowId).toBeNull();
  });
});

describe('Zustand Store - newRowAggressiveness', () => {
  test('clamps to 0-100 range', () => {
    const store = useShoppingStore.getState();
    store.setNewRowAggressiveness(-10);
    expect(useShoppingStore.getState().newRowAggressiveness).toBe(0);

    store.setNewRowAggressiveness(150);
    expect(useShoppingStore.getState().newRowAggressiveness).toBe(100);
  });

  test('rounds to integer', () => {
    const store = useShoppingStore.getState();
    store.setNewRowAggressiveness(55.7);
    expect(useShoppingStore.getState().newRowAggressiveness).toBe(56);
  });
});

describe('Zustand Store - sidebar and bug modal', () => {
  test('toggleSidebar flips state', () => {
    const store = useShoppingStore.getState();
    expect(store.isSidebarOpen).toBe(false);

    store.toggleSidebar();
    expect(useShoppingStore.getState().isSidebarOpen).toBe(true);

    store.toggleSidebar();
    expect(useShoppingStore.getState().isSidebarOpen).toBe(false);
  });

  test('setSidebarOpen sets directly', () => {
    const store = useShoppingStore.getState();
    store.setSidebarOpen(true);
    expect(useShoppingStore.getState().isSidebarOpen).toBe(true);
  });

  test('setReportBugModalOpen', () => {
    const store = useShoppingStore.getState();
    expect(store.isReportBugModalOpen).toBe(false);

    store.setReportBugModalOpen(true);
    expect(useShoppingStore.getState().isReportBugModalOpen).toBe(true);
  });
});

describe('Zustand Store - setRows preserves engagement and hydrates bids', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('preserves existing last_engaged_at timestamps', () => {
    const store = useShoppingStore.getState();
    store.setRows([mockRow({ id: 1 })]);
    store.setActiveRowId(1); // sets last_engaged_at

    const engagedAt = useShoppingStore.getState().rows.find(r => r.id === 1)!.last_engaged_at;

    // Simulate re-fetch from server (no last_engaged_at)
    store.setRows([mockRow({ id: 1 })]);

    const preserved = useShoppingStore.getState().rows.find(r => r.id === 1)!.last_engaged_at;
    expect(preserved).toBe(engagedAt);
  });

  test('hydrates rowResults from bids', () => {
    const store = useShoppingStore.getState();
    store.setRows([
      mockRow({
        id: 1,
        bids: [{
          id: 100, price: 25, currency: 'USD',
          item_title: 'Bid Item', item_url: 'https://bid.com',
          image_url: null, source: 'amazon', is_selected: false,
        }],
      }),
    ]);

    const results = useShoppingStore.getState().rowResults[1];
    expect(results).toBeDefined();
    expect(results).toHaveLength(1);
    expect(results[0].bid_id).toBe(100);
    expect(results[0].title).toBe('Bid Item');
  });

  test('prunes rowResults for removed rows', () => {
    const store = useShoppingStore.getState();
    store.setRows([mockRow({ id: 1 }), mockRow({ id: 2 })]);
    store.setRowResults(1, [mockOffer()]);
    store.setRowResults(2, [mockOffer()]);

    // Re-set with only row 1
    store.setRows([mockRow({ id: 1 })]);

    const state = useShoppingStore.getState();
    expect(state.rowResults[1]).toBeDefined();
    expect(state.rowResults[2]).toBeUndefined();
  });
});

describe('Zustand Store - rowSearchErrors', () => {
  beforeEach(() => {
    useShoppingStore.getState().clearSearch();
  });

  test('setRowResults stores userMessage as error', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [], undefined, false, 'Rate limited');

    expect(useShoppingStore.getState().rowSearchErrors[1]).toBe('Rate limited');
  });

  test('setRowResults clears error when no message', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [], undefined, false, 'Error');
    store.setRowResults(1, [mockOffer()]);

    expect(useShoppingStore.getState().rowSearchErrors[1]).toBeNull();
  });

  test('clearRowResults removes error', () => {
    const store = useShoppingStore.getState();
    store.setRowResults(1, [], undefined, false, 'Error');
    store.clearRowResults(1);

    expect(useShoppingStore.getState().rowSearchErrors[1]).toBeUndefined();
  });
});

describe('Zustand Store - requestDeleteRow (bug #130: immediate deletion)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    global.fetch = vi.fn().mockResolvedValue({ ok: true }) as unknown as typeof fetch;
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, status: 'sourcing' }),
      mockRow({ id: 2, status: 'sourcing' }),
    ]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test('immediately removes the row from local state', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    const rows = useShoppingStore.getState().rows;
    expect(rows.find(r => r.id === 1)).toBeUndefined();
    expect(rows).toHaveLength(1);
  });

  test('immediately calls DELETE API without waiting for undo window', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    expect(global.fetch).toHaveBeenCalledWith('/api/rows?id=1', { method: 'DELETE' });
  });

  test('sets pendingRowDelete with row data for undo', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    const pending = useShoppingStore.getState().pendingRowDelete;
    expect(pending).not.toBeNull();
    expect(pending?.row.id).toBe(1);
  });

  test('clears pendingRowDelete after undo window expires', () => {
    useShoppingStore.getState().requestDeleteRow(1, 100);
    expect(useShoppingStore.getState().pendingRowDelete).not.toBeNull();

    vi.advanceTimersByTime(100);
    expect(useShoppingStore.getState().pendingRowDelete).toBeNull();
  });
});

describe('Zustand Store - undoDeleteRow (bug #130: restore via PATCH)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    global.fetch = vi.fn().mockResolvedValue({ ok: true }) as unknown as typeof fetch;
    useShoppingStore.getState().clearSearch();
    useShoppingStore.getState().setRows([
      mockRow({ id: 1, status: 'sourcing' }),
      mockRow({ id: 2, status: 'sourcing' }),
    ]);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test('restores the row back into the rows array', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    expect(useShoppingStore.getState().rows).toHaveLength(1);

    useShoppingStore.getState().undoDeleteRow();
    expect(useShoppingStore.getState().rows).toHaveLength(2);
    expect(useShoppingStore.getState().rows.find(r => r.id === 1)).toBeDefined();
  });

  test('calls PATCH to restore row status in the backend', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    vi.mocked(global.fetch).mockClear();

    useShoppingStore.getState().undoDeleteRow();

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/rows?id=1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'sourcing' }),
      }),
    );
  });

  test('clears pendingRowDelete after undo', () => {
    useShoppingStore.getState().requestDeleteRow(1);
    useShoppingStore.getState().undoDeleteRow();
    expect(useShoppingStore.getState().pendingRowDelete).toBeNull();
  });

  test('no-op when there is no pending delete', () => {
    expect(() => useShoppingStore.getState().undoDeleteRow()).not.toThrow();
    expect(global.fetch).not.toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ method: 'PATCH' }));
  });
});
