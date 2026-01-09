import { create } from 'zustand';

interface Product {
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

interface SearchContext {
  query: string;
  rowId: number | null;
}

interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
}

interface ShoppingState {
  rows: Row[];
  searchResults: Product[];
  searchContext: SearchContext | null;
  isSearching: boolean;
  setRows: (rows: Row[]) => void;
  updateRow: (id: number, updates: Partial<Row>) => void;
  setSearchResults: (results: Product[], context: SearchContext) => void;
  setSearchStart: (context: SearchContext) => void;
  clearSearch: () => void;
}

export const useShoppingStore = create<ShoppingState>((set) => ({
  rows: [],
  searchResults: [],
  searchContext: null,
  isSearching: false,
  setRows: (rows) => set({ rows }),
  updateRow: (id, updates) => set((state) => ({
    rows: state.rows.map((row) => (row.id === id ? { ...row, ...updates } : row)),
  })),
  setSearchResults: (results, context) => set({ searchResults: results, searchContext: context, isSearching: false }),
  setSearchStart: (context) => set({ searchContext: context, isSearching: true }),
  clearSearch: () => set({ searchResults: [], searchContext: null, isSearching: false }),
}));
