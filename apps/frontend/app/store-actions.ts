import type { Offer, ProviderStatusSnapshot, Row, OfferSortMode } from "./store-types";

import type { ShoppingState } from "./store-state";

type SetStoreState = (
  partial: Partial<ShoppingState> | ((state: ShoppingState) => Partial<ShoppingState>)
) => void;

export const createStoreActions = (set: SetStoreState, get: () => ShoppingState) => ({
  setRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming: boolean = false, userMessage?: string) => set((state: ShoppingState) => {
    // STREAMING LOCK: If SSE is actively streaming for this row, skip the replace.
    // This prevents auto-load, comment merge, and other paths from wiping SSE results.
    if (state.streamingRowIds[rowId]) {
      console.warn(`[Store] setRowResults BLOCKED for row ${rowId} — streaming lock active`);
      return {};
    }

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
  appendRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming: boolean = false, userMessage?: string) => set((state: ShoppingState) => {
    const existingResults = state.rowResults[rowId] || [];
    const existingStatuses = state.rowProviderStatuses[rowId] || [];
    // Dedupe by bid_id (stable identity), fall back to URL for pre-persistence offers
    const seenBidIds = new Set(existingResults.filter(r => r.bid_id).map(r => r.bid_id));
    const seenUrls = new Set(existingResults.map(r => r.url));
    const newResults = results.filter(r => {
      if (r.bid_id) return !seenBidIds.has(r.bid_id);
      return !seenUrls.has(r.url);
    });
    return {
      rowResults: { ...state.rowResults, [rowId]: [...existingResults, ...newResults] },
      rowProviderStatuses: providerStatuses 
        ? { ...state.rowProviderStatuses, [rowId]: (() => {
            // Dedupe by provider_id — keep latest status per provider
            const merged = [...existingStatuses, ...providerStatuses];
            const byId = new Map<string, ProviderStatusSnapshot>();
            merged.forEach(s => byId.set(s.provider_id, s));
            return Array.from(byId.values());
          })() }
        : state.rowProviderStatuses,
      rowSearchErrors: userMessage !== undefined 
        ? { ...state.rowSearchErrors, [rowId]: userMessage }
        : state.rowSearchErrors,
      moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: moreIncoming },
      isSearching: moreIncoming,
    };
  }),
  updateRowOffer: (rowId: number, matcher: (offer: Offer) => boolean, updates: Partial<Offer>) => set((state: ShoppingState) => {
    const existing = state.rowResults[rowId];
    if (!existing) return {};
    const updated = existing.map((offer) => matcher(offer) ? { ...offer, ...updates } : offer);
    return { rowResults: { ...state.rowResults, [rowId]: updated } };
  }),
  clearRowResults: (rowId: number) => set((state: ShoppingState) => {
    const rest = { ...state.rowResults };
    const restStatuses = { ...state.rowProviderStatuses };
    const restErrors = { ...state.rowSearchErrors };
    delete rest[rowId];
    delete restStatuses[rowId];
    delete restErrors[rowId];
    return { rowResults: rest, rowProviderStatuses: restStatuses, rowSearchErrors: restErrors };
  }),
  setRowOfferSort: (rowId: number, sort: OfferSortMode) => set((state: ShoppingState) => {
    if (sort === 'original') {
      const rest = { ...state.rowOfferSort };
      delete rest[rowId];
      return { rowOfferSort: rest };
    }
    return { rowOfferSort: { ...state.rowOfferSort, [rowId]: sort } };
  }),
  setIsSearching: (searching: boolean) => set({ isSearching: searching }),
  setMoreResultsIncoming: (rowId: number, incoming: boolean) => set((state: ShoppingState) => ({
    moreResultsIncoming: { ...state.moreResultsIncoming, [rowId]: incoming },
  })),
  setStreamingLock: (rowId: number, locked: boolean) => set((state: ShoppingState) => ({
    streamingRowIds: { ...state.streamingRowIds, [rowId]: locked },
  })),
  clearSearch: () => set({ rowResults: {}, rowProviderStatuses: {}, rowSearchErrors: {}, moreResultsIncoming: {}, currentQuery: '', isSearching: false, activeRowId: null, cardClickQuery: null }),
  setCardClickQuery: (query: string | null) => set({ cardClickQuery: query }),

  // Find a row that matches the query, or return null if we need to create one
  selectOrCreateRow: (query: string, existingRows: Row[]) => {
    const lowerQuery = query.toLowerCase().trim();
    const activeRowId = get().activeRowId;
    const targetProjectId = get().targetProjectId;

    const candidateRows = targetProjectId
      ? existingRows.filter((r) => r.project_id === targetProjectId)
      : existingRows;

    // 1. If there's an active row, check if it's a good match for the new query
    // This allows continuing a conversation within the same card.
    if (activeRowId) {
      const activeRow = existingRows.find((r) => r.id === activeRowId);
      if (activeRow) {
        if (!targetProjectId || activeRow.project_id === targetProjectId) {
          const rowTitle = activeRow.title.toLowerCase().trim();
          const rowWords = rowTitle.split(/\s+/).filter((w) => w.length > 3);
          const queryWords = lowerQuery.split(/\s+/).filter((w) => w.length > 3);

          // Check for significant word overlap (at least 2 matching words > 3 chars)
          const overlap = rowWords.filter((w) => queryWords.some((qw) => qw.includes(w) || w.includes(qw)));

          if (lowerQuery.includes(rowTitle) || rowTitle.includes(lowerQuery) || overlap.length >= 2) {
            return activeRow;
          }
        }
      }
    }

    // 2. Try exact match across all rows
    let match = candidateRows.find((r) => r.title.toLowerCase().trim() === lowerQuery);
    if (match) return match;

    // 3. Try partial match (is an existing row title contained in the new query?)
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return lowerQuery.includes(rowTitle);
    });
    if (match) return match;

    // 4. Try reverse partial match (is the new query contained in an existing row title?)
    match = candidateRows.find((r) => {
      const rowTitle = r.title.toLowerCase().trim();
      return rowTitle.includes(lowerQuery);
    });

    return match || null;
  },
});

export function shouldForceNewRow(params: {
  message: string;
  activeRowTitle?: string | null;
  aggressiveness: number;
}): boolean {
  const msg = (params.message || '').toLowerCase().trim();
  const activeTitle = (params.activeRowTitle || '').toLowerCase().trim();
  const aggressiveness = Math.max(0, Math.min(100, params.aggressiveness));

  if (!msg || !activeTitle) return false;

  if (aggressiveness < 60) return false;

  const refinementRegex = /\b(over|under|below|above|cheaper|more|less|budget|price)\b|\$\s*\d+|\b\d+\s*(usd|dollars)\b/;
  if (refinementRegex.test(msg)) return false;

  const aWords = new Set(activeTitle.split(/\s+/).filter((w) => w.length > 2));
  const mWords = msg.split(/\s+/).filter((w) => w.length > 2);
  const overlap = mWords.filter((w) => aWords.has(w)).length;
  const denom = Math.max(1, Math.min(aWords.size, mWords.length));
  const similarity = overlap / denom;

  const normalized = (aggressiveness - 60) / 40;
  const threshold = 0.1 + normalized * 0.4;
  return similarity < threshold;
}
