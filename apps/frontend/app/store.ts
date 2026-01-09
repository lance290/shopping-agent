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

interface ShoppingState {
  searchResults: Product[];
  searchContext: SearchContext | null;
  isSearching: boolean;
  setSearchResults: (results: Product[], context: SearchContext) => void;
  setSearchStart: (context: SearchContext) => void;
  clearSearch: () => void;
}

export const useShoppingStore = create<ShoppingState>((set) => ({
  searchResults: [],
  searchContext: null,
  isSearching: false,
  setSearchResults: (results, context) => set({ searchResults: results, searchContext: context, isSearching: false }),
  setSearchStart: (context) => set({ searchContext: context, isSearching: true }),
  clearSearch: () => set({ searchResults: [], searchContext: null, isSearching: false }),
}));
