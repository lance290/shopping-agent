import { create } from 'zustand';

export interface Offer {
  title: string;
  price: number;
  currency: string;
  merchant: string;
  url: string;
  image_url: string | null;
  rating: number | null;
  reviews_count: number | null;
  shipping_info: string | null;
  source: string;
  // New fields
  merchant_domain?: string;
  click_url?: string;
  match_score?: number;
}

export interface Bid {
  id: number;
  price: number;
  currency: string;
  item_title: string;
  item_url: string | null;
  image_url: string | null;
  source: string;
  seller?: {
    name: string;
    domain: string | null;
  };
}

export interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
  choice_factors?: string;   // JSON string
  choice_answers?: string;   // JSON string
  bids?: Bid[];              // Persisted bids from DB
}

interface PendingRowDelete {
  row: Row;
  rowIndex: number;
  results: Offer[];
  timeoutId: ReturnType<typeof setTimeout>;
  expiresAt: number;
}

// Helper to convert DB Bid to Offer
export function mapBidToOffer(bid: Bid): Offer {
  return {
    title: bid.item_title,
    price: bid.price,
    currency: bid.currency,
    merchant: bid.seller?.name || 'Unknown',
    url: bid.item_url || '#',
    image_url: bid.image_url,
    rating: null, // Not persisted yet
    reviews_count: null,
    shipping_info: null,
    source: bid.source,
    merchant_domain: bid.seller?.domain || undefined,
    click_url: `/api/out?url=${encodeURIComponent(bid.item_url || '')}`
  };
}

// Helper to parse factors
export function parseChoiceFactors(row: Row): any[] {
  if (!row.choice_factors) return [];
  try {
    return JSON.parse(row.choice_factors);
  } catch {
    return [];
  }
}

export function parseChoiceAnswers(row: Row): Record<string, any> {
  if (!row.choice_answers) return {};
  try {
    return JSON.parse(row.choice_answers);
  } catch {
    return {};
  }
}

export interface ChoiceFactor {
  name: string;
  label: string;
  type: 'number' | 'select' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}

export type OfferSortMode = 'original' | 'price_asc' | 'price_desc';

// The source of truth state
interface ShoppingState {
  // Core state - SOURCE OF TRUTH
  currentQuery: string;           // The current search query
  activeRowId: number | null;     // The currently selected row ID
  rows: Row[];                    // All rows from database
  searchResults: Offer[];         // Current search results (legacy view)
  rowResults: Record<number, Offer[]>; // Per-row cached results
  rowOfferSort: Record<number, OfferSortMode>; // Per-row UI sort mode
  isSearching: boolean;           // Loading state for search
  cardClickQuery: string | null;  // Query from card click (triggers chat append)
  
  // Actions
  setCurrentQuery: (query: string) => void;
  setActiveRowId: (id: number | null) => void;
  setRows: (rows: Row[]) => void;
  addRow: (row: Row) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  removeRow: (id: number) => void;
  setSearchResults: (results: Offer[]) => void;
  setRowResults: (rowId: number, results: Offer[]) => void;
  clearRowResults: (rowId: number) => void;
  setRowOfferSort: (rowId: number, sort: OfferSortMode) => void;
  setIsSearching: (searching: boolean) => void;
  clearSearch: () => void;
  setCardClickQuery: (query: string | null) => void;  // For card click -> chat append
  
  // UI State
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;

  pendingRowDelete: PendingRowDelete | null;
  requestDeleteRow: (rowId: number, undoWindowMs?: number) => void;
  undoDeleteRow: () => void;
  
  // Combined actions for the flow
  selectOrCreateRow: (query: string, existingRows: Row[]) => Row | null;
}

export const useShoppingStore = create<ShoppingState>((set, get) => ({
  // Initial state
  currentQuery: '',
  activeRowId: null,
  rows: [],
  searchResults: [],
  rowResults: {},
  rowOfferSort: {},
  isSearching: false,
  cardClickQuery: null,
  isSidebarOpen: false, // Default closed

  pendingRowDelete: null,
  
  // Basic setters
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setActiveRowId: (id) => set({ activeRowId: id }),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),

  requestDeleteRow: (rowId, undoWindowMs = 7000) => {
    const existingPending = get().pendingRowDelete;
    if (existingPending) {
      clearTimeout(existingPending.timeoutId);
      fetch(`/api/rows?id=${existingPending.row.id}`, { method: 'DELETE' }).catch(() => {});
      set((s) => {
        const id = existingPending.row.id;
        const nextRows = s.rows.filter(r => r.id !== id);
        const { [id]: _, ...restResults } = s.rowResults;
        const nextActive = s.activeRowId === id ? null : s.activeRowId;
        return {
          rows: nextRows,
          rowResults: restResults,
          activeRowId: nextActive,
          pendingRowDelete: null,
        };
      });
    }

    const state = get();
    const rowIndex = state.rows.findIndex(r => r.id === rowId);
    if (rowIndex === -1) return;

    const row = state.rows[rowIndex];
    const results = state.rowResults[rowId] || [];

    const timeoutId = setTimeout(async () => {
      const pending = get().pendingRowDelete;
      if (!pending || pending.row.id !== rowId) return;

      try {
        const res = await fetch(`/api/rows?id=${rowId}`, { method: 'DELETE' });
        if (!res.ok) return;
      } catch {
        return;
      }

      set((s) => {
        const nextRows = s.rows.filter(r => r.id !== rowId);
        const { [rowId]: _, ...restResults } = s.rowResults;
        const nextActive = s.activeRowId === rowId ? null : s.activeRowId;
        return {
          rows: nextRows,
          rowResults: restResults,
          activeRowId: nextActive,
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

    set({ pendingRowDelete: null });
  },
  
  setRows: (rows) => set((state) => {
    // Keep row order stable across refreshes/polls.
    // Preserve existing order for known IDs; append any new rows at the end.
    const existingOrder = new Map<number, number>();
    state.rows.forEach((r, idx) => existingOrder.set(r.id, idx));

    const incomingIndex = new Map<number, number>();
    rows.forEach((r, idx) => incomingIndex.set(r.id, idx));

    const orderedRows = [...rows].sort((a, b) => {
      const aExisting = existingOrder.get(a.id);
      const bExisting = existingOrder.get(b.id);

      const aHas = aExisting !== undefined;
      const bHas = bExisting !== undefined;

      if (aHas && bHas) return aExisting! - bExisting!;
      if (aHas && !bHas) return -1;
      if (!aHas && bHas) return 1;

      // Both new: preserve server/incoming order
      return (incomingIndex.get(a.id) ?? 0) - (incomingIndex.get(b.id) ?? 0);
    });

    // Automatically hydrate rowResults from persisted bids
    const newRowResults = { ...state.rowResults };
    orderedRows.forEach(row => {
      if (row.bids && row.bids.length > 0) {
        newRowResults[row.id] = row.bids.map(mapBidToOffer);
      }
    });

    return { rows: orderedRows, rowResults: newRowResults };
  }),
  addRow: (row) => set((state) => ({ rows: [...state.rows, row] })),
  updateRow: (id, updates) => set((state) => ({
    rows: state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
  })),
  removeRow: (id) => set((state) => ({
    rows: state.rows.filter((row) => row.id !== id),
    activeRowId: state.activeRowId === id ? null : state.activeRowId,
  })),
  setSearchResults: (results) => set({ searchResults: results, isSearching: false }),
  setRowResults: (rowId, results) => set((state) => ({
    rowResults: { ...state.rowResults, [rowId]: results },
    isSearching: false,
  })),
  clearRowResults: (rowId) => set((state) => {
    const { [rowId]: _, ...rest } = state.rowResults;
    return { rowResults: rest };
  }),
  setRowOfferSort: (rowId, sort) => set((state) => {
    if (sort === 'original') {
      const { [rowId]: _, ...rest } = state.rowOfferSort;
      return { rowOfferSort: rest };
    }
    return { rowOfferSort: { ...state.rowOfferSort, [rowId]: sort } };
  }),
  setIsSearching: (searching) => set({ isSearching: searching }),
  clearSearch: () => set({ searchResults: [], rowResults: {}, currentQuery: '', isSearching: false, activeRowId: null, cardClickQuery: null }),
  setCardClickQuery: (query) => set({ cardClickQuery: query }),
  
  // Find a row that matches the query, or return null if we need to create one
  selectOrCreateRow: (query, existingRows) => {
    const lowerQuery = query.toLowerCase().trim();
    const activeRowId = get().activeRowId;
    
    // 1. If there's an active row, check if it's a good match for the new query
    // This allows continuing a conversation within the same card.
    if (activeRowId) {
      const activeRow = existingRows.find(r => r.id === activeRowId);
      if (activeRow) {
        const rowTitle = activeRow.title.toLowerCase().trim();
        const rowWords = rowTitle.split(/\s+/).filter(w => w.length > 3);
        const queryWords = lowerQuery.split(/\s+/).filter(w => w.length > 3);
        
        // Check for significant word overlap (at least 2 matching words > 3 chars)
        const overlap = rowWords.filter(w => queryWords.some(qw => qw.includes(w) || w.includes(qw)));
        
        if (lowerQuery.includes(rowTitle) || rowTitle.includes(lowerQuery) || overlap.length >= 2) {
          return activeRow;
        }
      }
    }

    // 2. Try exact match across all rows
    let match = existingRows.find(r => r.title.toLowerCase().trim() === lowerQuery);
    if (match) return match;

    // 3. Try partial match (is an existing row title contained in the new query?)
    match = existingRows.find(r => {
      const rowTitle = r.title.toLowerCase().trim();
      return lowerQuery.includes(rowTitle);
    });
    if (match) return match;

    // 4. Try reverse partial match (is the new query contained in an existing row title?)
    match = existingRows.find(r => {
      const rowTitle = r.title.toLowerCase().trim();
      return rowTitle.includes(lowerQuery);
    });

    return match || null;
  },
}));
