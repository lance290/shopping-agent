'use client';

import { Package, Search, Star, Truck, X } from 'lucide-react';
import { useShoppingStore, Product } from '../store';

export default function ProcurementBoard() {
  const store = useShoppingStore();

  const selectedRow = store.rows.find(r => r.id === store.activeRowId) || null;

  // Use search results from store
  const displayProducts = store.searchResults;
  const displayQuery = store.currentQuery || selectedRow?.title || '';

  return (
    <div className="flex-1 flex bg-gray-900 overflow-hidden">
      {/* Product Grid */}
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
