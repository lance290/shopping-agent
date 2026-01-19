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

// The source of truth state
interface ShoppingState {
  // Core state - SOURCE OF TRUTH
  currentQuery: string;           // The current search query
  activeRowId: number | null;     // The currently selected row ID
  rows: Row[];                    // All rows from database
  searchResults: Offer[];         // Current search results (legacy view)
  rowResults: Record<number, Offer[]>; // Per-row cached results
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
  setIsSearching: (searching: boolean) => void;
  clearSearch: () => void;
  setCardClickQuery: (query: string | null) => void;  // For card click -> chat append
  
  // UI State
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;
  
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
  isSearching: false,
  cardClickQuery: null,
  isSidebarOpen: false, // Default closed
  
  // Basic setters
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setActiveRowId: (id) => set({ activeRowId: id }),
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  
  setRows: (rows) => set((state) => {
    // Automatically hydrate rowResults from persisted bids
    const newRowResults = { ...state.rowResults };
    rows.forEach(row => {
      if (row.bids && row.bids.length > 0) {
        newRowResults[row.id] = row.bids.map(mapBidToOffer);
      }
    });
    return { rows, rowResults: newRowResults };
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
