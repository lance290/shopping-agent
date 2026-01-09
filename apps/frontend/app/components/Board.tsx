'use client';

import { useState, useEffect } from 'react';
import { Package, DollarSign, Trash2, Search, Star, Truck, X } from 'lucide-react';
import { useShoppingStore, Row, Product } from '../store';

export default function ProcurementBoard() {
  const [loading, setLoading] = useState(true);
  const store = useShoppingStore();

  const selectedRow = store.rows.find(r => r.id === store.activeRowId) || null;

  // Use search results from store
  const displayProducts = store.searchResults;
  const displayQuery = store.currentQuery || selectedRow?.title || '';

  const fetchRows = async () => {
    try {
      const res = await fetch('/api/rows', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        store.setRows(Array.isArray(data) ? data : []);
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
        store.removeRow(id);
      }
    } catch (e) {
      console.error("Failed to delete row", e);
    }
  };

  /**
   * CARD CLICK FLOW (Step 3):
   * 3a. User clicks a card
   * 3b. The query is set in Zustand as the source of truth
   * 3c. The text from the card is appended to the chat (via store update)
   * 3d. We run the search
   * 3e. Goto step 2 (continued chat flow)
   */
  const handleCardClick = async (row: Row) => {
    if (store.activeRowId === row.id) return;
    
    console.log('[Board] === CARD CLICK FLOW START ===');
    console.log('[Board] 3a. User clicked card:', row.id, row.title);

    // 3b. Set query in Zustand as source of truth
    store.setCurrentQuery(row.title);
    store.setActiveRowId(row.id);
    console.log('[Board] 3b. Zustand updated - query:', row.title, 'activeRowId:', row.id);

    // 3c. The chat will react to the store update (via useEffect)
    // The chat component watches store.currentQuery and store.activeRowId
    console.log('[Board] 3c. Chat will be notified via store');

    // 3d. Run the search
    console.log('[Board] 3d. Running search for:', row.title);
    store.setIsSearching(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: row.title }),
      });
      if (res.ok) {
        const data = await res.json();
        console.log('[Board] Search returned:', data.results?.length || 0, 'products');
        store.setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error('[Board] Search failed:', e);
      store.setSearchResults([]);
    }

    console.log('[Board] === CARD CLICK FLOW END ===');
    // 3e. Now the user can continue typing in chat (goto step 2)
  };

  useEffect(() => {
    fetchRows();
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
          {loading && store.rows.length === 0 && (
            <div className="text-center text-gray-500 py-10">Loading...</div>
          )}

          {!loading && store.rows.length === 0 && (
            <div className="text-center text-gray-500 py-10">
              <Package className="mx-auto h-8 w-8 text-gray-600 mb-2" />
              <p className="text-sm">No requests yet</p>
            </div>
          )}

          {store.rows.map((row: Row) => (
            <div
              key={row.id}
              onClick={() => handleCardClick(row)}
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
        {!store.currentQuery && !selectedRow && displayProducts.length === 0 && !store.isSearching ? (
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
                onClick={() => store.clearSearch()}
                className="p-2 hover:bg-gray-700 rounded-lg"
              >
                <X size={20} className="text-gray-400" />
              </button>
            </div>

            {store.isSearching ? (
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
