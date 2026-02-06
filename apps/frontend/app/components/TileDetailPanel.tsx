'use client';

import React, { useEffect, useRef } from 'react';
import { X, Loader2, AlertCircle } from 'lucide-react';
import { useDetailPanelStore } from '../stores/detailPanelStore';
import { TileDetailPanelErrorBoundary } from './TileDetailPanelErrorBoundary';

export function TileDetailPanel() {
  const panelRef = useRef<HTMLDivElement>(null);
  const { isOpen, bidData, loading, error, closePanel, retryFetch } = useDetailPanelStore();

  // Focus management
  useEffect(() => {
    if (isOpen && panelRef.current) {
      panelRef.current.focus();
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        closePanel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, closePanel]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 lg:hidden"
        onClick={closePanel}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className="fixed inset-y-0 right-0 w-full lg:w-[500px] bg-white shadow-2xl z-50 overflow-y-auto focus:outline-none"
        role="dialog"
        aria-modal="true"
        aria-labelledby="panel-title"
        tabIndex={-1}
      >
        <TileDetailPanelErrorBoundary>
          {/* Header */}
          <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
            <h2 id="panel-title" className="text-lg font-semibold">
              Product Details
            </h2>
            <button
              onClick={closePanel}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              aria-label="Close panel"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            )}

            {error && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <AlertCircle className="w-12 h-12 text-red-500" />
                <div className="text-center">
                  <p className="text-gray-900 font-medium mb-2">Unable to load details</p>
                  <p className="text-sm text-gray-600 mb-4">{error}</p>
                  <button
                    onClick={retryFetch}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}

            {!loading && !error && !bidData && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <AlertCircle className="w-12 h-12 text-gray-400 mb-3" />
                <p className="text-gray-600">Item no longer available</p>
              </div>
            )}

            {!loading && !error && bidData && (
              <div className="space-y-6">
                {/* Basic Info */}
                <div>
                  <h3 className="text-xl font-semibold mb-2">{bidData.item_title}</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-blue-600">
                      {bidData.currency} {bidData.price.toFixed(2)}
                    </span>
                    {bidData.seller && (
                      <span className="text-sm text-gray-500">from {bidData.seller.name}</span>
                    )}
                  </div>
                </div>

                {/* Image */}
                {bidData.image_url && (
                  <div className="rounded-lg overflow-hidden border">
                    <img
                      src={bidData.image_url}
                      alt={bidData.item_title}
                      className="w-full h-auto"
                    />
                  </div>
                )}

                {/* Product Info */}
                {bidData.product_info && (
                  <section aria-label="Product information">
                    <h4 className="font-semibold mb-3" tabIndex={0}>Product Information</h4>
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                      {bidData.product_info.brand && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Brand: </span>
                          <span className="text-sm text-gray-900">{bidData.product_info.brand}</span>
                        </div>
                      )}
                      {bidData.product_info.specs && (
                        <div className="space-y-1">
                          {Object.entries(bidData.product_info.specs).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-sm font-medium text-gray-700 capitalize">
                                {key}:{' '}
                              </span>
                              <span className="text-sm text-gray-900">{String(value)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </section>
                )}

                {/* Matched Features */}
                {bidData.matched_features && bidData.matched_features.length > 0 && (
                  <section aria-label="Why this matches your search">
                    <h4 className="font-semibold mb-3" tabIndex={0}>Why this matches</h4>
                    <ul className="space-y-2">
                      {bidData.matched_features.map((feature, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-blue-600 mt-1">✓</span>
                          <span className="text-sm text-gray-700">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}

                {/* Chat Excerpts */}
                {bidData.chat_excerpts && bidData.chat_excerpts.length > 0 && (
                  <section aria-label="Related conversation excerpts">
                    <h4 className="font-semibold mb-3" tabIndex={0}>From your conversation</h4>
                    <div className="space-y-3">
                      {bidData.chat_excerpts.map((excerpt, idx) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg ${
                            excerpt.role === 'user'
                              ? 'bg-blue-50 border-l-4 border-blue-600'
                              : 'bg-gray-50 border-l-4 border-gray-300'
                          }`}
                        >
                          <div className="text-xs font-medium text-gray-500 uppercase mb-1">
                            {excerpt.role === 'user' ? 'You' : 'Assistant'}
                          </div>
                          <div className="text-sm text-gray-900">{excerpt.content}</div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* No Provenance Fallback */}
                {!bidData.product_info &&
                  (!bidData.matched_features || bidData.matched_features.length === 0) &&
                  (!bidData.chat_excerpts || bidData.chat_excerpts.length === 0) && (
                    <div className="text-center py-8 text-gray-500 text-sm" role="status">
                      Based on your search
                    </div>
                  )}

                {/* Link to Product */}
                {bidData.item_url && (
                  <a
                    href={bidData.item_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full py-3 bg-blue-600 text-white text-center rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    View on {bidData.seller?.domain || 'Seller Site'}
                  </a>
                )}
              </div>
            )}
          </div>
        </TileDetailPanelErrorBoundary>
      </div>
    </>
  );
}
