'use client';

import { useState, useCallback } from 'react';
import Chat from './components/Chat';
import ProcurementBoard from './components/Board';

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

export default function Home() {
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [searchContext, setSearchContext] = useState<SearchContext | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const onSearchResults = useCallback((results: Product[], context: SearchContext) => {
    setSearchResults(results);
    setSearchContext(context);
    setIsSearching(false);
  }, []);

  const onSearchStart = useCallback((context: SearchContext) => {
    setSearchContext(context);
    setIsSearching(true);
  }, []);

  return (
    <main className="flex h-screen w-full bg-white overflow-hidden">
      {/* Chat Pane (Left) */}
      <Chat 
        onSearchResults={onSearchResults}
        onSearchStart={onSearchStart}
      />
      
      {/* Board Pane (Right/Center) */}
      <ProcurementBoard 
        searchResults={searchResults}
        searchContext={searchContext}
        isSearching={isSearching}
      />
    </main>
  );
}
