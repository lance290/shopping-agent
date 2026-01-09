import { create } from 'zustand';

export interface Product {
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
}

export interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
}

// The source of truth state
interface ShoppingState {
  // Core state - SOURCE OF TRUTH
  currentQuery: string;           // The current search query
  activeRowId: number | null;     // The currently selected row ID
  rows: Row[];                    // All rows from database
  searchResults: Product[];       // Current search results
  isSearching: boolean;           // Loading state for search
  
  // Actions
  setCurrentQuery: (query: string) => void;
  setActiveRowId: (id: number | null) => void;
  setRows: (rows: Row[]) => void;
  addRow: (row: Row) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  removeRow: (id: number) => void;
  setSearchResults: (results: Product[]) => void;
  setIsSearching: (searching: boolean) => void;
  clearSearch: () => void;
  
  // Combined actions for the flow
  selectOrCreateRow: (query: string, existingRows: Row[]) => Row | null;
}

export const useShoppingStore = create<ShoppingState>((set, get) => ({
  // Initial state
  currentQuery: '',
  activeRowId: null,
  rows: [],
  searchResults: [],
  isSearching: false,
  
  // Basic setters
  setCurrentQuery: (query) => set({ currentQuery: query }),
  setActiveRowId: (id) => set({ activeRowId: id }),
  setRows: (rows) => set({ rows }),
  addRow: (row) => set((state) => ({ rows: [...state.rows, row] })),
  updateRow: (id, updates) => set((state) => ({
    rows: state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
  })),
  removeRow: (id) => set((state) => ({
    rows: state.rows.filter((row) => row.id !== id),
    activeRowId: state.activeRowId === id ? null : state.activeRowId,
  })),
  setSearchResults: (results) => set({ searchResults: results, isSearching: false }),
  setIsSearching: (searching) => set({ isSearching: searching }),
  clearSearch: () => set({ searchResults: [], currentQuery: '', isSearching: false, activeRowId: null }),
  
  // Find a row that matches the query, or return null if we need to create one
  selectOrCreateRow: (query, existingRows) => {
    const lowerQuery = query.toLowerCase().trim();
    // Find exact or close match
    const match = existingRows.find(r => 
      r.title.toLowerCase().trim() === lowerQuery ||
      r.title.toLowerCase().includes(lowerQuery) ||
      lowerQuery.includes(r.title.toLowerCase())
    );
    return match || null;
  },
}));
