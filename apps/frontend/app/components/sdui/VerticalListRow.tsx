'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { runSearchApiWithStatus, fetchSingleRowFromDb, createShareLink, fetchWithAuth, preferredSearchQueryForRow } from '../../utils/api';
import { Trash2, RotateCw, Share2, Copy, Send } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';
import OutreachQueue from '../OutreachQueue';
import { SearchProgressBar, SkeletonCardGroup } from './SearchProgressBar';
import BidCard from './BidCard';
import RowOutcomeSelector from './RowOutcomeSelector';

interface VerticalListRowProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

const SERVICE_FIRST_DESIRE_TIERS = new Set(['service', 'bespoke', 'high_value', 'advisory']);

function isCustomVendorOffer(offer: Offer): boolean {
  return offer.source === 'vendor_directory'
    || offer.source === 'seller_quote'
    || offer.source === 'registered_merchant'
    || offer.is_service_provider === true;
}

function isOutreachEligible(offer: Offer): boolean {
  return typeof offer.bid_id === 'number' && (
    offer.source === 'vendor_directory'
    || offer.is_service_provider === true
    || (offer.vendor_id != null && offer.source?.startsWith('apify_'))
  );
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
  const [sortMode, setSortMode] = useState<'relevance' | 'price_asc' | 'price_desc'>('relevance');
  const [rfpSelectedBidIds, setRfpSelectedBidIds] = useState<Set<number>>(new Set());
  const [rfpSentBidIds, setRfpSentBidIds] = useState<Set<number>>(() => {
    const emailedIds = new Set<number>();
    for (const bid of row.bids || []) {
      if (bid.is_emailed && bid.id) emailedIds.add(bid.id);
    }
    return emailedIds;
  });
  const [isOutreachOpen, setIsOutreachOpen] = useState(false);
  const unsortedOffers = useMemo(
    () => offers.length > 0 ? offers : (row.bids || []).map(mapBidToOffer),
    [offers, row.bids],
  );
  const prefersCustomVendors = row.is_service === true || SERVICE_FIRST_DESIRE_TIERS.has(row.desire_tier || '');
  const displayOffers = useMemo(() => [...unsortedOffers].sort((a, b) => {
    const aIsSaved = !!(a.is_vendor_bookmarked || a.is_item_bookmarked || a.is_liked);
    const bIsSaved = !!(b.is_vendor_bookmarked || b.is_item_bookmarked || b.is_liked);
    if (aIsSaved && !bIsSaved) return -1;
    if (!aIsSaved && bIsSaved) return 1;
    if (a.is_selected && !b.is_selected) return -1;
    if (!a.is_selected && b.is_selected) return 1;

    if (sortMode === 'price_asc') {
      const pa = a.price ?? Infinity;
      const pb = b.price ?? Infinity;
      return pa - pb;
    }
    if (sortMode === 'price_desc') {
      const pa = a.price ?? -Infinity;
      const pb = b.price ?? -Infinity;
      return pb - pa;
    }
    if (prefersCustomVendors) {
      const aIsCustomVendor = isCustomVendorOffer(a);
      const bIsCustomVendor = isCustomVendorOffer(b);
      if (aIsCustomVendor && !bIsCustomVendor) return -1;
      if (!aIsCustomVendor && bIsCustomVendor) return 1;
    }
    // Default: relevance (combined_score descending)
    const sa = a.match_score;
    const sb = b.match_score;
    if (sa != null && sb != null) return sb - sa;
    if (sa != null) return -1;
    if (sb != null) return 1;
    return 0;
  }), [unsortedOffers, sortMode, prefersCustomVendors]);
  const rfpEligibleOffers = useMemo(
    () => displayOffers.filter(isOutreachEligible),
    [displayOffers],
  );
  const selectedRfpBidIds = useMemo(
    () => rfpEligibleOffers
      .map((offer) => offer.bid_id as number)
      .filter((bidId) => rfpSelectedBidIds.has(bidId) && !rfpSentBidIds.has(bidId)),
    [rfpEligibleOffers, rfpSelectedBidIds, rfpSentBidIds],
  );
  
  const requestDeleteRow = useShoppingStore((s) => s.requestDeleteRow);
  const setIsSearching = useShoppingStore((s) => s.setIsSearching);
  const setRowResults = useShoppingStore((s) => s.setRowResults);
  const updateRow = useShoppingStore((s) => s.updateRow);
  const moreIncoming = useShoppingStore((s) => s.moreResultsIncoming[row.id] ?? false);
  const searchProgress = useShoppingStore((s) => s.searchProgress[row.id]);
  const isRowSearching = moreIncoming || (searchProgress && !searchProgress.isComplete);

  useEffect(() => {
    const validBidIds = new Set(rfpEligibleOffers.map((offer) => offer.bid_id as number));
    setRfpSelectedBidIds((prev) => new Set(Array.from(prev).filter((bidId) => validBidIds.has(bidId))));
    setRfpSentBidIds((prev) => new Set(Array.from(prev).filter((bidId) => validBidIds.has(bidId))));
  }, [rfpEligibleOffers]);

  const handleRerunSearch = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setIsSearching(true);
      const res = await runSearchApiWithStatus(preferredSearchQueryForRow(row), row.id);
      setRowResults(row.id, res.results, res.providerStatuses);
      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) updateRow(row.id, freshRow);
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

  const toggleRfpBid = (bidId: number) => {
    setRfpSelectedBidIds((prev) => {
      const next = new Set(prev);
      if (next.has(bidId)) next.delete(bidId);
      else next.add(bidId);
      return next;
    });
  };

  const handleOpenRfps = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (selectedRfpBidIds.length === 0) return;
    setIsOutreachOpen(true);
  };

  return (
    <div
      ref={rowRef}
      className={`bg-white rounded-xl shadow-sm border transition-all ${
        isActive ? 'border-gold ring-1 ring-gold/30' : 'border-warm-grey'
      }`}
    >
      {/* Row Header */}
      <div className="w-full text-left px-4 py-3 flex items-center gap-3 group cursor-pointer"
        onClick={() => { onSelect(); onToggleExpand(); }}
      >
        {isRowSearching ? (
          <div className="w-4 h-4 flex-shrink-0">
            <div className="w-4 h-4 border-2 border-gold border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
            row.status === 'sourcing' ? 'bg-yellow-400 animate-pulse' :
            row.status === 'closed' || row.status === 'delivered' ? 'bg-green-400' :
            'bg-gold'
          }`} />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-ink truncate">{row.title}</p>
          <p className="text-xs text-ink-muted">
            {isRowSearching
              ? (searchProgress?.totalResultsSoFar
                ? `Found ${searchProgress.totalResultsSoFar} result${searchProgress.totalResultsSoFar !== 1 ? 's' : ''} so far...`
                : 'Searching...')
              : row.status === 'sourcing' ? 'Searching...' :
                bidCount > 0 ? `${bidCount} option${bidCount !== 1 ? 's' : ''}` :
                row.status}
          </p>
        </div>

        {rfpEligibleOffers.length > 0 && (
          <button
            onClick={handleOpenRfps}
            disabled={selectedRfpBidIds.length === 0}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              selectedRfpBidIds.length > 0
                ? 'bg-status-success text-white hover:bg-status-success/90'
                : 'bg-canvas-dark text-onyx-muted cursor-not-allowed'
            }`}
            title={selectedRfpBidIds.length > 0 ? 'Draft outreach for selected vendors' : 'Select vendors below to start outreach'}
          >
            <Send size={14} />
            Start Outreach{selectedRfpBidIds.length > 0 ? ` (${selectedRfpBidIds.length})` : ''}
          </button>
        )}
        
        {/* Quick Actions — always visible on mobile, hover on desktop */}
        <div className="flex items-center gap-1 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity pr-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleRerunSearch(e); }}
            className="p-1.5 text-onyx-muted hover:text-accent-blue rounded-md hover:bg-accent-blue/10 transition-colors"
            title="Rerun Search"
          >
            <RotateCw size={14} />
          </button>
          <button
            onClick={async (e) => {
              e.stopPropagation();
              const link = await createShareLink('row', row.id);
              if (link?.share_url) {
                await navigator.clipboard.writeText(link.share_url);
                alert('Share link copied!');
              }
            }}
            className="p-1.5 text-onyx-muted hover:text-accent-blue rounded-md hover:bg-accent-blue/10 transition-colors"
            title="Share Search"
          >
            <Share2 size={14} />
          </button>
          <button
            onClick={async (e) => {
              e.stopPropagation();
              try {
                const res = await fetchWithAuth(`/api/rows/${row.id}/duplicate`, { method: 'POST' });
                if (res.ok) {
                  const newRow = await res.json();
                  if (newRow?.id) {
                    updateRow(newRow.id, newRow);
                    window.location.reload();
                  }
                }
              } catch (err) {
                console.error('Failed to duplicate search', err);
              }
            }}
            className="p-1.5 text-onyx-muted hover:text-accent-blue rounded-md hover:bg-accent-blue/10 transition-colors"
            title="Duplicate Search"
          >
            <Copy size={14} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(e); }}
            className="p-1.5 text-onyx-muted hover:text-red-600 rounded-md hover:bg-red-50 transition-colors"
            title="Delete Request"
          >
            <Trash2 size={14} />
          </button>
        </div>

        <svg className={`w-4 h-4 text-onyx-muted transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>

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
          
          {/* Sort dropdown */}
          {displayOffers.length > 1 && (
            <div className="flex justify-end">
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as typeof sortMode)}
                className="text-[10px] text-ink-muted font-medium pl-2 pr-5 py-0.5 rounded border border-warm-grey bg-white hover:border-ink-muted transition-colors outline-none cursor-pointer appearance-none"
                style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E\")", backgroundRepeat: 'no-repeat', backgroundPosition: 'right 4px center' }}
              >
                <option value="relevance">Best Match</option>
                <option value="price_asc">Price: Low → High</option>
                <option value="price_desc">Price: High → Low</option>
              </select>
            </div>
          )}

          {/* Search progress bar — visible while streaming */}
          {isRowSearching && (
            <SearchProgressBar progress={searchProgress} isSearching={!!isRowSearching} />
          )}

          <div className="space-y-2">
            {displayOffers.length === 0 && !hasSchema && !isRowSearching && (
              <p className="text-sm text-onyx-muted italic">No options found yet.</p>
            )}
            {displayOffers.map((offer, i) => (
              <div
                key={offer.bid_id ?? i}
                className="bid-card-enter"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <BidCard
                  offer={offer}
                  row={row}
                  isRfpSelected={typeof offer.bid_id === 'number' ? rfpSelectedBidIds.has(offer.bid_id) : false}
                  isRfpSent={typeof offer.bid_id === 'number' ? rfpSentBidIds.has(offer.bid_id) : false}
                  onToggleRfpSelection={isOutreachEligible(offer)
                    ? () => toggleRfpBid(offer.bid_id as number)
                    : undefined}
                />
              </div>
            ))}

            {/* Skeleton cards — visible while searching and no results yet */}
            {isRowSearching && displayOffers.length === 0 && (
              <SkeletonCardGroup count={4} />
            )}

            {/* Partial skeleton — show 1-2 more placeholders while more results are incoming */}
            {isRowSearching && displayOffers.length > 0 && (
              <SkeletonCardGroup count={2} />
            )}
          </div>

          {/* Outcome selector — request-level feedback (Trust Metrics PRD §8.2) */}
          {displayOffers.length > 0 && (
            <RowOutcomeSelector
              rowId={row.id}
              currentResolution={row.row_outcome as string | undefined}
              currentQuality={row.row_quality_assessment as string | undefined}
            />
          )}

          {rfpEligibleOffers.length > 0 && (
            <OutreachQueue
              isOpen={isOutreachOpen}
              onClose={() => setIsOutreachOpen(false)}
              onSent={(bidIds) => {
                setRfpSentBidIds((prev) => new Set([...Array.from(prev), ...bidIds]));
                setRfpSelectedBidIds((prev) => new Set(Array.from(prev).filter((bidId) => !bidIds.includes(bidId))));
              }}
              rowId={row.id}
              desireTier={row.desire_tier || 'service'}
              offers={displayOffers}
              selectedBidIds={selectedRfpBidIds}
            />
          )}
        </div>
      )}
    </div>
  );
}

