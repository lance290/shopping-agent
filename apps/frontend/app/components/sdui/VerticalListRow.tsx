'use client';

import { useState, useRef, useEffect } from 'react';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { runSearchApiWithStatus } from '../../utils/api';
import { Trash2, RotateCw } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';
import VendorContactModal from '../VendorContactModal';

interface VerticalListRowProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

export function VerticalListRow({ row, offers, isActive, isExpanded, onSelect, onToggleExpand }: VerticalListRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);

  // On mobile, scroll this row to the top of the sheet when expanded
  useEffect(() => {
    if (isExpanded && rowRef.current && window.innerWidth < 1024) {
      // Small delay so the expand animation starts first
      requestAnimationFrame(() => {
        rowRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }, [isExpanded]);

  const hasSchema = !!(row.ui_schema && validateUISchema(row.ui_schema));
  const bidCount = row.bids?.length ?? 0;
  const unsortedOffers = offers.length > 0 ? offers : (row.bids || []).map(mapBidToOffer);
  const displayOffers = [...unsortedOffers].sort((a, b) => {
    // Liked/selected always float to top
    if (a.is_liked && !b.is_liked) return -1;
    if (!a.is_liked && b.is_liked) return 1;
    if (a.is_selected && !b.is_selected) return -1;
    if (!a.is_selected && b.is_selected) return 1;
    // Sort by combined_score descending — only when both have scores (stable otherwise)
    const sa = a.match_score;
    const sb = b.match_score;
    if (sa != null && sb != null) return sb - sa;
    if (sa != null) return -1;  // scored items above unscored
    if (sb != null) return 1;
    return 0;  // preserve original order for unscored items
  });
  
  const requestDeleteRow = useShoppingStore((s) => s.requestDeleteRow);
  const setIsSearching = useShoppingStore((s) => s.setIsSearching);
  const setRowResults = useShoppingStore((s) => s.setRowResults);

  const handleRerunSearch = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setIsSearching(true);
      const res = await runSearchApiWithStatus(null, row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
    } catch (err) {
      console.error('Failed to rerun search', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    requestDeleteRow(row.id);
  };

  return (
    <div
      ref={rowRef}
      className={`bg-white rounded-xl shadow-sm border transition-all ${
        isActive ? 'border-gold ring-1 ring-gold/30' : 'border-warm-grey'
      }`}
    >
      {/* Row Header */}
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3 group"
        onClick={() => { onSelect(); onToggleExpand(); }}
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
          row.status === 'sourcing' ? 'bg-yellow-400 animate-pulse' :
          row.status === 'closed' || row.status === 'delivered' ? 'bg-green-400' :
          'bg-gold'
        }`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-ink truncate">{row.title}</p>
          <p className="text-xs text-ink-muted">
            {row.status === 'sourcing' ? 'Searching...' :
             bidCount > 0 ? `${bidCount} option${bidCount !== 1 ? 's' : ''}` :
             row.status}
          </p>
        </div>
        
        {/* Quick Actions (visible on hover) — use div+role to avoid nested <button> */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity pr-2">
          <div 
            role="button"
            tabIndex={0}
            onClick={(e) => handleRerunSearch(e as React.MouseEvent)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleRerunSearch(e as unknown as React.MouseEvent); }}
            className="p-1.5 text-onyx-muted hover:text-accent-blue rounded-md hover:bg-accent-blue/10 transition-colors cursor-pointer"
            title="Rerun Search"
          >
            <RotateCw size={14} />
          </div>
          <div 
            role="button"
            tabIndex={0}
            onClick={(e) => handleDelete(e as React.MouseEvent)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleDelete(e as unknown as React.MouseEvent); }}
            className="p-1.5 text-onyx-muted hover:text-red-600 rounded-md hover:bg-red-50 transition-colors cursor-pointer"
            title="Delete Request"
          >
            <Trash2 size={14} />
          </div>
        </div>

        <svg className={`w-4 h-4 text-onyx-muted transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded: show SDUI schema + ALL bids as cards */}
      {isExpanded && (
        <div className="border-t border-warm-grey px-4 py-3 space-y-4 max-h-[calc(100dvh-8rem)] lg:max-h-[600px] overflow-y-auto">
          {hasSchema && (
            <div className="mb-4">
              <DynamicRenderer
                schema={row.ui_schema}
                fallbackTitle={row.title}
                fallbackStatus={row.status}
              />
            </div>
          )}
          
          <div className="space-y-2">
            {displayOffers.length === 0 && !hasSchema && (
              <p className="text-sm text-onyx-muted italic">No options found yet.</p>
            )}
            {displayOffers.map((offer, i) => (
              <BidCard key={offer.bid_id ?? i} offer={offer} row={row} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  rainforest_amazon: 'Amazon',
  amazon: 'Amazon',
  ebay_browse: 'eBay',
  ebay: 'eBay',
  serpapi: 'Google',
  google_cse: 'Google',
  kroger: 'Kroger',
  vendor_directory: 'Vendor',
  seller_quote: 'Quote',
  registered_merchant: 'Merchant',
};

function friendlySource(source: string): string {
  return SOURCE_DISPLAY_NAMES[source] || source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function BidCard({ offer, row }: { offer: Offer; row: Row }) {
  const [showContactModal, setShowContactModal] = useState(false);
  const priceStr = offer.price !== null && offer.price !== undefined
    ? `$${offer.price.toFixed(2)}`
    : 'Request Quote';

  const isVendor = offer.source === 'vendor_directory' || offer.is_service_provider;

  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-canvas-dark transition-colors">
      {offer.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={offer.image_url} alt={offer.title} className="w-12 h-12 rounded-md object-cover bg-canvas-dark flex-shrink-0" />
      ) : (
        <div className="w-12 h-12 rounded-md bg-canvas-dark flex-shrink-0 flex items-center justify-center">
          <svg className="w-5 h-5 text-onyx-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-ink truncate">{offer.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-sm font-semibold text-ink">{priceStr}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-canvas-dark text-ink-muted">{friendlySource(offer.source)}</span>
          {offer.merchant && offer.merchant !== 'Unknown' && (
            <span className="text-[10px] text-onyx-muted">{offer.merchant}</span>
          )}
        </div>
      </div>
      {isVendor ? (
        <button
          onClick={() => setShowContactModal(true)}
          className="px-3 py-1.5 text-xs font-medium bg-status-success text-white rounded-lg hover:bg-status-success/90 transition-colors flex-shrink-0"
        >
          Request Quote
        </button>
      ) : offer.url && offer.url !== '#' ? (
        <a
          href={offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}${offer.bid_id ? `&bid_id=${offer.bid_id}` : ''}&row_id=${row.id}&source=${offer.source}`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1.5 text-xs font-medium bg-gold text-navy rounded-lg hover:bg-gold-dark transition-colors flex-shrink-0"
        >
          View Deal
        </a>
      ) : null}
      {showContactModal && (
        <VendorContactModal
          isOpen={showContactModal}
          onClose={() => setShowContactModal(false)}
          rowId={row.id}
          rowTitle={row.title}
          vendorName={offer.vendor_name || offer.merchant || ''}
          vendorCompany={offer.vendor_company || offer.title}
          vendorEmail={offer.vendor_email || ''}
          onSent={() => setShowContactModal(false)}
        />
      )}
    </div>
  );
}
