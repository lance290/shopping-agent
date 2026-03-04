import { create } from "zustand";
import type { Offer, ProviderStatusSnapshot, Bid, Row, Project, OfferSortMode } from "./store-types";
import { mapBidToOffer } from "./store";
import { createStoreActions } from "./store-actions";

export interface PendingRowDelete {
  row: Row;
  rowIndex: number;
  results: Offer[];
  timeoutId: ReturnType<typeof setTimeout>;
  expiresAt: number;
}

// ChoiceFactor, OfferSortMode, CommentData, BidSocialData — now in store-types.ts (re-exported above)

// The source of truth state
export interface ShoppingState {
  // Core state - SOURCE OF TRUTH
  currentQuery: string;           // The current search query
  activeRowId: number | null;     // The currently selected row ID
  targetProjectId: number | null; // The project ID to create new rows in
  newRowAggressiveness: number;   // 0..100: higher => more likely to start a new row
  rows: Row[];                    // All rows from database
  projects: Project[];            // All projects
  rowResults: Record<number, Offer[]>; // Per-row cached results
  rowProviderStatuses: Record<number, ProviderStatusSnapshot[]>; // Per-row provider statuses
  rowSearchErrors: Record<number, string | null>; // Per-row search error messages
  rowOfferSort: Record<number, OfferSortMode>; // Per-row UI sort mode
  moreResultsIncoming: Record<number, boolean>; // Per-row flag for streaming results
  streamingRowIds: Record<number, boolean>; // Per-row lock: true while SSE is actively streaming results
  isSearching: boolean;           // Loading state for search
  cardClickQuery: string | null;  // Query from card click (triggers chat append)

  // Actions
  setCurrentQuery: (query: string) => void;
  setActiveRowId: (id: number | null) => void;
  setTargetProjectId: (id: number | null) => void;
  setNewRowAggressiveness: (value: number) => void;
  setRows: (rows: Row[]) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  removeProject: (id: number) => void;
  addRow: (row: Row) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  removeRow: (id: number) => void;
  setRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean, userMessage?: string) => void;
  appendRowResults: (rowId: number, results: Offer[], providerStatuses?: ProviderStatusSnapshot[], moreIncoming?: boolean, userMessage?: string) => void;
  updateRowOffer: (rowId: number, matcher: (offer: Offer) => boolean, updates: Partial<Offer>) => void;
  clearRowResults: (rowId: number) => void;
  setRowOfferSort: (rowId: number, sort: OfferSortMode) => void;
  setIsSearching: (searching: boolean) => void;
  setMoreResultsIncoming: (rowId: number, incoming: boolean) => void;
  setStreamingLock: (rowId: number, locked: boolean) => void;
  clearSearch: () => void;
  setCardClickQuery: (query: string | null) => void;  // For card click -> chat append

  // Search provider toggles
  selectedProviders: Record<string, boolean>;
  toggleProvider: (providerId: string) => void;
  setSelectedProviders: (providers: Record<string, boolean>) => void;

  // UI State
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;

  isReportBugModalOpen: boolean;
  setReportBugModalOpen: (isOpen: boolean) => void;

  pendingRowDelete: PendingRowDelete | null;
  requestDeleteRow: (rowId: number, undoWindowMs?: number) => void;
  undoDeleteRow: () => void;

  // SDUI state
  expandedRowId: number | null;            // Which row is expanded in vertical list
  setExpandedRowId: (id: number | null) => void;
  sduiFallbackCount: number;               // Observability: how often MVR fallback is used
  incrementSduiFallback: () => void;
  
  // Combined actions for the flow
  selectOrCreateRow: (query: string, existingRows: Row[]) => Row | null;
}

export const useShoppingStore = create<ShoppingState>((set, get) => {
  return {
  // Initial state
  currentQuery: '',
  activeRowId: null,
  targetProjectId: null,
  newRowAggressiveness: 50,
  rows: [],
  projects: [],
  rowResults: {},
  rowProviderStatuses: {},
  rowSearchErrors: {},
  rowOfferSort: {},
  moreResultsIncoming: {},
  streamingRowIds: {},
  isSearching: false,
  cardClickQuery: null,
  selectedProviders: { amazon: true, ebay: true, serpapi: true, vendor_directory: true },
  isSidebarOpen: false, // Default closed

  pendingRowDelete: null,

  // SDUI state
  expandedRowId: null,
  sduiFallbackCount: 0,
  setExpandedRowId: (id) => set({ expandedRowId: id }),
  incrementSduiFallback: () => set((s) => ({ sduiFallbackCount: s.sduiFallbackCount + 1 })),

  // Basic setters
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setTargetProjectId: (id) => set({ targetProjectId: id }),
  setNewRowAggressiveness: (value) => set({ newRowAggressiveness: Math.max(0, Math.min(100, Math.round(value))) }),
  setActiveRowId: (id) => set((state) => {
    if (id === null) return { activeRowId: id };

    const updatedRows = state.rows.map((row) =>
      row.id === id ? { ...row, last_engaged_at: Date.now() } : row
    );

    // Load per-row providers into toggles when switching rows
    const targetRow = state.rows.find((r) => r.id === id);
    let providers = state.selectedProviders;
    if (targetRow?.selected_providers) {
      try {
        const parsed = JSON.parse(targetRow.selected_providers);
        if (parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)) {
          providers = parsed;
        }
      } catch { /* keep current */ }
    }

    return { activeRowId: id, rows: updatedRows, selectedProviders: providers };
  }),
  toggleProvider: (providerId) => set((state) => {
    const newProviders = {
      ...state.selectedProviders,
      [providerId]: !state.selectedProviders[providerId],
    };

    // Save to active row if one exists
    if (state.activeRowId !== null) {
      const serialized = JSON.stringify(newProviders);
      const newRows = state.rows.map((row) =>
        row.id === state.activeRowId
          ? { ...row, selected_providers: serialized }
          : row
      );
      // Fire-and-forget persist to backend
      fetch(`/api/rows?id=${state.activeRowId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_providers: serialized }),
      }).catch(() => {});
      return { selectedProviders: newProviders, rows: newRows };
    }

    return { selectedProviders: newProviders };
  }),
  setSelectedProviders: (providers) => set({ selectedProviders: providers }),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  isReportBugModalOpen: false,
  setReportBugModalOpen: (isOpen) => set({ isReportBugModalOpen: isOpen }),

  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((state) => ({ projects: [project, ...state.projects] })),
  removeProject: (id) => set((state) => ({ projects: state.projects.filter((p) => p.id !== id) })),

  requestDeleteRow: (rowId, undoWindowMs = 7000) => {
    const existingPending = get().pendingRowDelete;
    if (existingPending) {
      // Previous pending delete was already sent to the API immediately; just clean up its timer and state.
      clearTimeout(existingPending.timeoutId);
      set((s) => {
        const id = existingPending.row.id;
        const { [id]: _, ...restResults } = s.rowResults;
        const { [id]: __, ...restStatuses } = s.rowProviderStatuses;
        const { [id]: ___, ...restErrors } = s.rowSearchErrors;
        return {
          rowResults: restResults,
          rowProviderStatuses: restStatuses,
          rowSearchErrors: restErrors,
          pendingRowDelete: null,
        };
      });
    }

    const state = get();
    const rowIndex = state.rows.findIndex(r => r.id === rowId);
    if (rowIndex === -1) return;

    const row = state.rows[rowIndex];
    const results = state.rowResults[rowId] || [];

    // Immediately remove from local state so a refresh won't show it again.
    set((s) => {
      const nextRows = s.rows.filter(r => r.id !== rowId);
      const nextActive = s.activeRowId === rowId ? null : s.activeRowId;
      return { rows: nextRows, activeRowId: nextActive };
    });

    // Immediately archive in the backend — don't wait for the undo window.
    fetch(`/api/rows?id=${rowId}`, { method: 'DELETE' }).catch(() => {});

    // Timer just expires the undo UI after the window closes.
    const timeoutId = setTimeout(() => {
      set((s) => {
        if (!s.pendingRowDelete || s.pendingRowDelete.row.id !== rowId) return s;
        const { [rowId]: _, ...restResults } = s.rowResults;
        const { [rowId]: __, ...restStatuses } = s.rowProviderStatuses;
        const { [rowId]: ___, ...restErrors } = s.rowSearchErrors;
        return {
          rowResults: restResults,
          rowProviderStatuses: restStatuses,
          rowSearchErrors: restErrors,
          pendingRowDelete: null,
        };
      });
    }, undoWindowMs);

    set({
      pendingRowDelete: {
        row,
        rowIndex,
        results,
        timeoutId,
        expiresAt: Date.now() + undoWindowMs,
      },
    });
  },

  undoDeleteRow: () => {
    const pending = get().pendingRowDelete;
    if (!pending) return;
    clearTimeout(pending.timeoutId);

    // Restore the row in local state.
    set((state) => {
      const newRows = [...state.rows];
      const clampedIndex = Math.min(pending.rowIndex, newRows.length);
      newRows.splice(clampedIndex, 0, pending.row);
      return {
        rows: newRows,
        rowResults: { ...state.rowResults, [pending.row.id]: pending.results },
        pendingRowDelete: null,
      };
    });

    // Restore the row in the backend by unarchiving it.
    fetch(`/api/rows?id=${pending.row.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: pending.row.status }),
    }).catch(() => {});
  },
  
  setRows: (rows) => set((state) => {
    // Preserve last_engaged_at timestamps from existing state
    const existingEngagement = new Map<number, number>();
    state.rows.forEach((r) => {
      if (r.last_engaged_at) {
        existingEngagement.set(r.id, r.last_engaged_at);
      }
    });

    // Merge incoming rows with preserved engagement timestamps
    const mergedRows = rows.map((row) => ({
      ...row,
      last_engaged_at: existingEngagement.get(row.id) || row.last_engaged_at,
    }));

    const orderedRows = [...mergedRows];

    // Automatically hydrate rowResults from persisted bids
    // IMPORTANT: Merge bids with existing rowResults to preserve search results
    const rowIds = new Set(orderedRows.map((row) => row.id));
    const prunedRowResults = Object.fromEntries(
      Object.entries(state.rowResults || {}).filter(([id]) => rowIds.has(Number(id)))
    ) as Record<number, Offer[]>;
    const newRowResults = { ...prunedRowResults };
    const prunedProviderStatuses = Object.fromEntries(
      Object.entries(state.rowProviderStatuses || {}).filter(([id]) => rowIds.has(Number(id)))
    ) as Record<number, ProviderStatusSnapshot[]>;
    orderedRows.forEach(row => {
      if (row.bids && row.bids.length > 0) {
        const bidsAsOffers = row.bids.map(b => mapBidToOffer(b, row.id));
        const existingResults = newRowResults[row.id] || [];

        // Create a map of existing offers by bid_id for deduplication
        const existingByBidId = new Map<number, Offer>();
        const existingWithoutBidId: Offer[] = [];

        existingResults.forEach(offer => {
          if (offer.bid_id) {
            existingByBidId.set(offer.bid_id, offer);
          } else {
            existingWithoutBidId.push(offer);
          }
        });

        // Update existing offers with fresh bid data or add new bids
        bidsAsOffers.forEach(bidOffer => {
          if (bidOffer.bid_id) {
            existingByBidId.set(bidOffer.bid_id, bidOffer);
          }
        });

        // Merge: bids first (in order), then other search results
        newRowResults[row.id] = [
          ...Array.from(existingByBidId.values()),
          ...existingWithoutBidId
        ];
      }
    });

    return { rows: orderedRows, rowResults: newRowResults, rowProviderStatuses: prunedProviderStatuses };
  }),
  addRow: (row) => set((state) => {
    const newRow = { ...row, last_engaged_at: Date.now() };
    const { [newRow.id]: _, ...restResults } = state.rowResults;
    const { [newRow.id]: __, ...restStatuses } = state.rowProviderStatuses;
    // Add new row at the beginning (most recent)
    return { rows: [newRow, ...state.rows], rowResults: restResults, rowProviderStatuses: restStatuses };
  }),
  updateRow: (id, updates) => set((state) => {
    const newRows = state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row));
    const newState: any = { rows: newRows };

    // Hydrate rowResults from bids when row has them — ensures results display
    // even if the search response was empty (e.g. after error recovery or page reload)
    const updatedRow = newRows.find((r) => r.id === id);
    if (updatedRow?.bids && updatedRow.bids.length > 0) {
      const bidsAsOffers = updatedRow.bids.map(b => mapBidToOffer(b, updatedRow.id));
      const existingResults = state.rowResults[id] || [];

      // Merge: update existing by bid_id, add new ones
      const existingByBidId = new Map<number, Offer>();
      const existingWithoutBidId: Offer[] = [];
      existingResults.forEach((offer) => {
        if (offer.bid_id) {
          existingByBidId.set(offer.bid_id, offer);
        } else {
          existingWithoutBidId.push(offer);
        }
      });
      bidsAsOffers.forEach((bidOffer) => {
        if (bidOffer.bid_id) {
          existingByBidId.set(bidOffer.bid_id, bidOffer);
        }
      });

      newState.rowResults = {
        ...state.rowResults,
        [id]: [...Array.from(existingByBidId.values()), ...existingWithoutBidId],
      };
    }

    return newState;
  }),
  removeRow: (id) => set((state) => ({
    rows: state.rows.filter((row) => row.id !== id),
    activeRowId: state.activeRowId === id ? null : state.activeRowId,
  })),

  ...(createStoreActions(set, get) as any)
  } as ShoppingState;
});