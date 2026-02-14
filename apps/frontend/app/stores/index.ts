/**
 * Combined store exports - provides backward-compatible API
 * while organizing code into modular stores
 */

import { create } from 'zustand';
import { useRowStore } from './rows';
import { useSearchStore } from './search';
import { useUIStore } from './ui';
import { mapBidToOffer } from './utils';
import { Row, Offer } from './types';

// Re-export types
export * from './types';
export * from './utils';

// Re-export individual stores
export { useRowStore, useSearchStore, useUIStore };

/**
 * Combined store hook that provides the unified API from the original store.ts
 * This maintains backward compatibility while the codebase transitions to modular stores.
 */
export const useShoppingStore = create<any>((set, get) => ({
  // Proxy getters to individual stores
  get currentQuery() { return useSearchStore.getState().currentQuery; },
  get activeRowId() { return useRowStore.getState().activeRowId; },
  get targetProjectId() { return useRowStore.getState().targetProjectId; },
  get newRowAggressiveness() { return useRowStore.getState().newRowAggressiveness; },
  get rows() { return useRowStore.getState().rows; },
  get projects() { return useRowStore.getState().projects; },
  get searchResults() { return useSearchStore.getState().searchResults; },
  get rowResults() {
    const searchState = useSearchStore.getState();
    const rowState = useRowStore.getState();

    // Hydrate rowResults from persisted bids when rows are loaded
    const hydratedResults: Record<number, Offer[]> = { ...searchState.rowResults };

    rowState.rows.forEach(row => {
      if (row.bids && row.bids.length > 0 && !hydratedResults[row.id]) {
        hydratedResults[row.id] = row.bids.map(mapBidToOffer);
      }
    });

    return hydratedResults;
  },
  get rowProviderStatuses() { return useSearchStore.getState().rowProviderStatuses; },
  get rowSearchErrors() { return useSearchStore.getState().rowSearchErrors; },
  get rowOfferSort() { return useSearchStore.getState().rowOfferSort; },
  get moreResultsIncoming() { return useSearchStore.getState().moreResultsIncoming; },
  get isSearching() { return useSearchStore.getState().isSearching; },
  get cardClickQuery() { return useSearchStore.getState().cardClickQuery; },
  get isSidebarOpen() { return useUIStore.getState().isSidebarOpen; },
  get isReportBugModalOpen() { return useUIStore.getState().isReportBugModalOpen; },
  get pendingRowDelete() { return useRowStore.getState().pendingRowDelete; },

  // Proxy setters to individual stores
  setCurrentQuery: (query: string) => useSearchStore.getState().setCurrentQuery(query),
  setActiveRowId: (id: number | null) => useRowStore.getState().setActiveRowId(id),
  setTargetProjectId: (id: number | null) => useRowStore.getState().setTargetProjectId(id),
  setNewRowAggressiveness: (value: number) => useRowStore.getState().setNewRowAggressiveness(value),
  setRows: (rows: Row[]) => {
    const rowState = useRowStore.getState();
    const searchState = useSearchStore.getState();

    // Update row store
    rowState.setRows(rows);

    // Hydrate search results from bids
    const rowIds = new Set(rows.map(r => r.id));
    const prunedRowResults = Object.fromEntries(
      Object.entries(searchState.rowResults).filter(([id]) => rowIds.has(Number(id)))
    );
    const prunedProviderStatuses = Object.fromEntries(
      Object.entries(searchState.rowProviderStatuses).filter(([id]) => rowIds.has(Number(id)))
    );

    // Merge bids with existing results
    rows.forEach(row => {
      if (row.bids && row.bids.length > 0) {
        const bidsAsOffers = row.bids.map(mapBidToOffer);
        const existingResults = prunedRowResults[row.id] || [];

        const existingByBidId = new Map<number, Offer>();
        const existingWithoutBidId: Offer[] = [];

        existingResults.forEach(offer => {
          if (offer.bid_id) {
            existingByBidId.set(offer.bid_id, offer);
          } else {
            existingWithoutBidId.push(offer);
          }
        });

        bidsAsOffers.forEach(bidOffer => {
          if (bidOffer.bid_id) {
            existingByBidId.set(bidOffer.bid_id, bidOffer);
          }
        });

        prunedRowResults[row.id] = [
          ...Array.from(existingByBidId.values()),
          ...existingWithoutBidId
        ];
      }
    });

    // Update search store with merged results
    Object.entries(prunedRowResults).forEach(([rowId, results]) => {
      searchState.setRowResults(Number(rowId), results, prunedProviderStatuses[Number(rowId)]);
    });
  },
  setProjects: (projects: any) => useRowStore.getState().setProjects(projects),
  addProject: (project: any) => useRowStore.getState().addProject(project),
  removeProject: (id: number) => useRowStore.getState().removeProject(id),
  addRow: (row: Row) => useRowStore.getState().addRow(row),
  updateRow: (id: number, updates: Partial<Row>) => useRowStore.getState().updateRow(id, updates),
  removeRow: (id: number) => useRowStore.getState().removeRow(id),
  setSearchResults: (results: Offer[]) => useSearchStore.getState().setSearchResults(results),
  setRowResults: (rowId: number, results: Offer[], providerStatuses?: any, moreIncoming?: boolean, userMessage?: string) =>
    useSearchStore.getState().setRowResults(rowId, results, providerStatuses, moreIncoming, userMessage),
  appendRowResults: (rowId: number, results: Offer[], providerStatuses?: any, moreIncoming?: boolean, userMessage?: string) =>
    useSearchStore.getState().appendRowResults(rowId, results, providerStatuses, moreIncoming, userMessage),
  clearRowResults: (rowId: number) => useSearchStore.getState().clearRowResults(rowId),
  setRowOfferSort: (rowId: number, sort: any) => useSearchStore.getState().setRowOfferSort(rowId, sort),
  setIsSearching: (searching: boolean) => useSearchStore.getState().setIsSearching(searching),
  setMoreResultsIncoming: (rowId: number, incoming: boolean) => useSearchStore.getState().setMoreResultsIncoming(rowId, incoming),
  clearSearch: () => useSearchStore.getState().clearSearch(),
  setCardClickQuery: (query: string | null) => useSearchStore.getState().setCardClickQuery(query),
  setSidebarOpen: (isOpen: boolean) => useUIStore.getState().setSidebarOpen(isOpen),
  toggleSidebar: () => useUIStore.getState().toggleSidebar(),
  setReportBugModalOpen: (isOpen: boolean) => useUIStore.getState().setReportBugModalOpen(isOpen),
  requestDeleteRow: (rowId: number, undoWindowMs?: number) => useRowStore.getState().requestDeleteRow(rowId, undoWindowMs),
  undoDeleteRow: () => useRowStore.getState().undoDeleteRow(),
  selectOrCreateRow: (query: string, existingRows: Row[]) => useRowStore.getState().selectOrCreateRow(query, existingRows),
}));
