/**
 * Search store: manages search results, provider status, and deduplication
 */

import { create } from 'zustand';
import { Offer, ProviderStatusSnapshot, OfferSortMode } from './types';

interface SearchStoreState {
  // Core state
  currentQuery: string;
  searchResults: Offer[];
  rowResults: Record<number, Offer[]>;
  rowProviderStatuses: Record<number, ProviderStatusSnapshot[]>;
  rowSearchErrors: Record<number, string | null>;
  rowOfferSort: Record<number, OfferSortMode>;
  moreResultsIncoming: Record<number, boolean>;
  isSearching: boolean;
  cardClickQuery: string | null;

  // Actions
  setCurrentQuery: (query: string) => void;
  setSearchResults: (results: Offer[]) => void;
  setRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean, userMessage?: string) => void;
  appendRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean, userMessage?: string) => void;
  clearRowResults: (rowId: number) => void;
  setRowOfferSort: (rowId: number, sort: OfferSortMode) => void;
  setIsSearching: (searching: boolean) => void;
  setMoreResultsIncoming: (rowId: number, incoming: boolean) => void;
  clearSearch: () => void;
  setCardClickQuery: (query: string | null) => void;
}

export const useSearchStore = create<SearchStoreState>((set) => ({
  // Initial state
  currentQuery: '',
  searchResults: [],
  rowResults: {},
  rowProviderStatuses: {},
  rowSearchErrors: {},
  rowOfferSort: {},
  moreResultsIncoming: {},
  isSearching: false,
  cardClickQuery: null,

  setCurrentQuery: (query) => set({ currentQuery: query }),

  setSearchResults: (results) => set({ searchResults: results, isSearching: false }),

  setRowResults: (rowId, results, providerStatuses, moreIncoming = false, userMessage) => set((state) => {
    const existing = state.rowResults[rowId] || [];

    // Preserve service providers (mailto: links) when incoming results don't include them
    const incomingHasServiceProviders = results.some((o) => o.is_service_provider);
    const preservedServiceProviders = incomingHasServiceProviders
      ? []
      : existing.filter((o) => o.is_service_provider);

    return {
      rowResults: {
        ...state.rowResults,
        [rowId]: [...preservedServiceProviders, ...results],
      },
      rowProviderStatuses: providerStatuses ? { ...state.rowProviderStatuses, [rowId]: providerStatuses } : state.rowProviderStatuses,
      rowSearchErrors: { ...state.rowSearchErrors, [rowId]: userMessage || null },
      moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: moreIncoming },
      isSearching: moreIncoming,
    };
  }),

  appendRowResults: (rowId, results, providerStatuses, moreIncoming = false, userMessage) => set((state) => {
    const existingResults = state.rowResults[rowId] || [];
    const existingStatuses = state.rowProviderStatuses[rowId] || [];

    // Dedupe by URL
    const seenUrls = new Set(existingResults.map(r => r.url));
    const newResults = results.filter(r => !seenUrls.has(r.url));

    return {
      rowResults: { ...state.rowResults, [rowId]: [...existingResults, ...newResults] },
      rowProviderStatuses: providerStatuses
        ? { ...state.rowProviderStatuses, [rowId]: [...existingStatuses, ...providerStatuses] }
        : state.rowProviderStatuses,
      rowSearchErrors: userMessage !== undefined
        ? { ...state.rowSearchErrors, [rowId]: userMessage }
        : state.rowSearchErrors,
      moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: moreIncoming },
      isSearching: moreIncoming,
    };
  }),

  clearRowResults: (rowId) => set((state) => {
    const { [rowId]: _, ...rest } = state.rowResults;
    const { [rowId]: __, ...restStatuses } = state.rowProviderStatuses;
    const { [rowId]: ___, ...restErrors } = state.rowSearchErrors;
    return { rowResults: rest, rowProviderStatuses: restStatuses, rowSearchErrors: restErrors };
  }),

  setRowOfferSort: (rowId, sort) => set((state) => {
    if (sort === 'original') {
      const { [rowId]: _, ...rest } = state.rowOfferSort;
      return { rowOfferSort: rest };
    }
    return { rowOfferSort: { ...state.rowOfferSort, [rowId]: sort } };
  }),

  setIsSearching: (searching) => set({ isSearching: searching }),

  setMoreResultsIncoming: (rowId, incoming) => set((state) => ({
    moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: incoming },
  })),

  clearSearch: () => set({
    searchResults: [],
    rowResults: {},
    rowProviderStatuses: {},
    rowSearchErrors: {},
    moreResultsIncoming: {},
    currentQuery: '',
    isSearching: false,
    cardClickQuery: null
  }),

  setCardClickQuery: (query) => set({ cardClickQuery: query }),
}));
