'use client';

import { useState, useEffect } from 'react';
import { Package, DollarSign, Trash2, Search, Star, Truck, X } from 'lucide-react';
import { useShoppingStore } from '../store';

interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
}

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

export default function ProcurementBoard() {
  const [loading, setLoading] = useState(true);
  const { rows, setRows, searchResults, setSearchResults, searchContext, setSearchStart, isSearching, activeRowId, setActiveRowId, clearSearch } = useShoppingStore();

  const selectedRow = rows.find(r => r.id === activeRowId) || null;

  // Use search results from store
  const displayProducts = searchResults;
  const displayQuery = searchContext?.query || selectedRow?.title || '';
  
  // Local loading state for row selection search
  const [rowSearching, setRowSearching] = useState(false);
  const showSearching = isSearching || rowSearching;

  const fetchRows = async () => {
    try {
        const res = await fetch('/api/rows', { cache: 'no-store' });
        if (res.ok) {
            const data = await res.json();
            setRows(Array.isArray(data) ? data : []);
        }
    } catch (e) {
        console.error("Failed to fetch rows", e);
    } finally {
        setLoading(false);
    }
  };

  const deleteRow = async (id: number) => {
    try {
      const res = await fetch(`/api/rows?id=${id}`, { method: 'DELETE' });
      if (res.ok) {
        setRows(rows.filter(r => r.id !== id));
        if (activeRowId === id) {
          setActiveRowId(null);
          clearSearch();
        }
      }
    } catch (e) {
      console.error("Failed to delete row", e);
    }
  };

  const searchRowProducts = async (row: Row) => {
    setRowSearching(true);
    // Update store to reflect we are searching for this row
    setSearchStart({ query: row.title, rowId: row.id });
    
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: row.title }),
      });
      if (res.ok) {
        const data = await res.json();
        // Update store with results
        setSearchResults(data.results || [], { query: row.title, rowId: row.id });
      }
    } catch (e) {
      console.error("Failed to search products", e);
    } finally {
      setRowSearching(false);
    }
  };

  const selectRow = (row: Row) => {
    if (activeRowId === row.id) return;
    setActiveRowId(row.id);
    searchRowProducts(row);
  };

  useEffect(() => {
    fetchRows();
    const interval = setInterval(fetchRows, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex-1 flex bg-gray-900 overflow-hidden">
      {/* Left: Row List */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-white">Requests</h2>
            <button onClick={fetchRows} className="text-sm text-blue-400 hover:text-blue-300">
              Refresh
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {loading && rows.length === 0 && (
            <div className="text-center text-gray-500 py-10">Loading...</div>
          )}

          {!loading && rows.length === 0 && (
            <div className="text-center text-gray-500 py-10">
              <Package className="mx-auto h-8 w-8 text-gray-600 mb-2" />
              <p className="text-sm">No requests yet</p>
            </div>
          )}

          {rows.map((row) => (
            <div
              key={row.id}
              onClick={() => selectRow(row)}
              className={`p-3 rounded-lg cursor-pointer transition-colors ${
                selectedRow?.id === row.id 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              }`}
            >
              <div className="flex justify-between items-start">
                <h3 className="font-medium text-sm line-clamp-1">{row.title}</h3>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteRow(row.id); }}
                  className="p-1 hover:bg-red-500/20 rounded"
                >
                  <Trash2 size={14} className="text-red-400" />
                </button>
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  row.status === 'sourcing' ? 'bg-yellow-500/20 text-yellow-400' : 
                  row.status === 'closed' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                }`}>
                  {row.status}
                </span>
                <span className="text-xs text-gray-400">#{row.id}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Product Grid */}
      <div className="flex-1 overflow-y-auto">
        {!searchContext && !selectedRow && displayProducts.length === 0 && !isSearching ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Search className="mx-auto h-12 w-12 text-gray-600 mb-3" />
              <p>Ask for something in the chat or select a request</p>
            </div>
          </div>
        ) : (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold text-white">{displayQuery}</h1>
                <p className="text-gray-400 text-sm mt-1">
                  {displayProducts.length} products found
                </p>
              </div>
              <button
                onClick={() => { setActiveRowId(null); clearSearch(); }}
                className="p-2 hover:bg-gray-700 rounded-lg"
              >
                <X size={20} className="text-gray-400" />
              </button>
            </div>

            {showSearching ? (
              <div className="text-center py-20 text-gray-500">
                <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
                <p>Searching products...</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {displayProducts.map((product: Product, idx: number) => (
                  <a
                    key={idx}
                    href={product.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`bg-gray-800 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all group block ${product.url ? 'cursor-pointer' : 'cursor-default'}`}
                  >
                    <div className="aspect-square bg-gray-700 relative overflow-hidden">
                      {product.image_url ? (
                        <img
                          src={product.image_url}
                          alt={product.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Package className="h-12 w-12 text-gray-600" />
                        </div>
                      )}
                    </div>
                    <div className="p-3">
                      <h3 className="text-sm text-white font-medium line-clamp-2 mb-1">
                        {product.title}
                      </h3>
                      <p className="text-lg font-bold text-green-400">
                        ${product.price.toFixed(2)}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {product.merchant !== 'Unknown' ? product.merchant : 'Various sellers'}
                      </p>
                      {product.rating && (
                        <div className="flex items-center gap-1 mt-1">
                          <Star size={12} className="text-yellow-400 fill-yellow-400" />
                          <span className="text-xs text-gray-400">
                            {product.rating} ({product.reviews_count?.toLocaleString()})
                          </span>
                        </div>
                      )}
                      {product.shipping_info && (
                        <div className="flex items-center gap-1 mt-1 text-xs text-gray-500">
                          <Truck size={12} />
                          <span className="line-clamp-1">{product.shipping_info}</span>
                        </div>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
