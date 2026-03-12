'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { runSearchApiWithStatus, fetchSingleRowFromDb, toggleVendorBookmark, toggleItemBookmark, createShareLink, createCommentApi, fetchCommentsApi, fetchWithAuth, AUTH_REQUIRED, preferredSearchQueryForRow, submitFeedback, submitOutcome, FEEDBACK_OPTIONS, RESOLUTION_OPTIONS, QUALITY_OPTIONS } from '../../utils/api';
import type { CommentDto, FeedbackType, ResolutionType, QualityType } from '../../utils/api';
import { Trash2, RotateCw, Heart, CheckCircle2, MessageSquare, Share2, Copy, Send, Star, ThumbsUp, ThumbsDown, ChevronDown, Shield } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';
import VendorContactModal from '../VendorContactModal';
import OutreachQueue from '../OutreachQueue';
import { SearchProgressBar, SkeletonCardGroup } from './SearchProgressBar';

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
    () => displayOffers.filter((offer) =>
      typeof offer.bid_id === 'number' && (
        offer.source === 'vendor_directory'
        || offer.is_service_provider
        || (offer.vendor_id != null && offer.source?.startsWith('apify_'))
      )
    ),
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
                  onToggleRfpSelection={typeof offer.bid_id === 'number' && offer.source === 'vendor_directory'
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
              currentResolution={row.row_outcome as ResolutionType | undefined}
              currentQuality={row.row_quality_assessment as QualityType | undefined}
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

function RowOutcomeSelector({
  rowId,
  currentResolution,
  currentQuality,
}: {
  rowId: number;
  currentResolution?: ResolutionType;
  currentQuality?: QualityType;
}) {
  const [resolution, setResolution] = useState<ResolutionType | undefined>(currentResolution);
  const [quality, setQuality] = useState<QualityType | undefined>(currentQuality);
  const [openMenu, setOpenMenu] = useState<'resolution' | 'quality' | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleResolution = async (val: ResolutionType) => {
    setIsSaving(true);
    const result = await submitOutcome(rowId, { outcome: val });
    setIsSaving(false);
    if (result === AUTH_REQUIRED) { alert('Sign in to rate this search'); return; }
    if (!result || typeof result !== 'object' || !('status' in result)) { alert('Failed to save'); return; }
    setResolution(val);
    setOpenMenu(null);
  };

  const handleQuality = async (val: QualityType) => {
    setIsSaving(true);
    const result = await submitOutcome(rowId, { quality: val });
    setIsSaving(false);
    if (result === AUTH_REQUIRED) { alert('Sign in to rate this search'); return; }
    if (!result || typeof result !== 'object' || !('status' in result)) { alert('Failed to save'); return; }
    setQuality(val);
    setOpenMenu(null);
  };

  const resLabel = RESOLUTION_OPTIONS.find((o) => o.type === resolution)?.label;
  const qualLabel = QUALITY_OPTIONS.find((o) => o.type === quality)?.label;

  const pillClass = (
    selected: string | undefined,
    positive: string[],
    negative: string[],
  ) =>
    selected
      ? positive.includes(selected)
        ? 'bg-green-50 border-green-200 text-green-700'
        : negative.includes(selected)
        ? 'bg-orange-50 border-orange-200 text-orange-700'
        : 'bg-blue-50 border-blue-200 text-blue-700'
      : 'bg-canvas-dark border-warm-grey text-ink-muted hover:border-gold/30';

  return (
    <div className="flex items-center gap-2 pt-2 border-t border-warm-grey/50 flex-wrap">
      <span className="text-[10px] text-onyx-muted font-medium uppercase tracking-wide">How did this go?</span>
      {/* Resolution selector */}
      <div className="relative">
        <button
          onClick={() => setOpenMenu(openMenu === 'resolution' ? null : 'resolution')}
          disabled={isSaving}
          className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition-colors ${pillClass(resolution, ['solved'], ['not_solved'])}`}
        >
          {resLabel || 'Outcome'}
          <ChevronDown size={12} className={`transition-transform ${openMenu === 'resolution' ? 'rotate-180' : ''}`} />
        </button>
        {openMenu === 'resolution' && (
          <div className="absolute left-0 bottom-full mb-1 z-50 bg-white border border-warm-grey rounded-lg shadow-lg py-1 min-w-[160px]">
            {RESOLUTION_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleResolution(opt.type)}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-canvas-dark transition-colors ${
                  resolution === opt.type ? 'font-semibold text-gold-dark' : 'text-ink'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
      {/* Quality selector */}
      <div className="relative">
        <button
          onClick={() => setOpenMenu(openMenu === 'quality' ? null : 'quality')}
          disabled={isSaving}
          className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg border transition-colors ${pillClass(quality, ['results_were_strong'], ['results_were_noisy', 'routing_was_wrong'])}`}
        >
          {qualLabel || 'Result quality'}
          <ChevronDown size={12} className={`transition-transform ${openMenu === 'quality' ? 'rotate-180' : ''}`} />
        </button>
        {openMenu === 'quality' && (
          <div className="absolute left-0 bottom-full mb-1 z-50 bg-white border border-warm-grey rounded-lg shadow-lg py-1 min-w-[180px]">
            {QUALITY_OPTIONS.map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleQuality(opt.type)}
                className={`w-full text-left px-3 py-1.5 text-xs hover:bg-canvas-dark transition-colors ${
                  quality === opt.type ? 'font-semibold text-gold-dark' : 'text-ink'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
      </div>
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

function BidCard({
  offer,
  row,
  isRfpSelected,
  isRfpSent,
  onToggleRfpSelection,
}: {
  offer: Offer;
  row: Row;
  isRfpSelected: boolean;
  isRfpSent: boolean;
  onToggleRfpSelection?: () => void;
}) {
  const [showContactModal, setShowContactModal] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState<CommentDto[]>([]);
  const [isLikeLoading, setIsLikeLoading] = useState(false);
  const [showFeedbackMenu, setShowFeedbackMenu] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState<FeedbackType | null>(null);
  const updateRowOffer = useShoppingStore((s) => s.updateRowOffer);
  const priceStr = offer.price !== null && offer.price !== undefined
    ? `$${offer.price.toFixed(2)}`
    : 'Request Quote';

  const isVendor = offer.source === 'vendor_directory' || offer.is_service_provider || (offer.vendor_id != null && offer.source?.startsWith('apify_'));
  const showRfpToggle = typeof onToggleRfpSelection === 'function';

  const handleToggleLike = async () => {
    if (!offer.bid_id || isLikeLoading) return;
    setIsLikeLoading(true);

    if (isVendor && offer.vendor_id) {
      const wasBookmarked = !!offer.is_vendor_bookmarked;
      updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_vendor_bookmarked: !wasBookmarked, is_liked: !wasBookmarked });
      try {
        const result = await toggleVendorBookmark(offer.vendor_id, wasBookmarked, row.id);
        if (result === AUTH_REQUIRED || !result) {
          updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_vendor_bookmarked: wasBookmarked, is_liked: wasBookmarked });
          if (result === AUTH_REQUIRED) alert('Sign in to save to Rolodex');
        }
      } catch { /* optimistic UI already applied */ }
    } else {
      const bookmarkUrl = offer.canonical_url || (offer.url && offer.url !== '#' ? offer.url : undefined);
      if (!bookmarkUrl) {
        setIsLikeLoading(false);
        return;
      }
      const wasBookmarked = !!offer.is_item_bookmarked;
      updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, {
        canonical_url: bookmarkUrl,
        is_item_bookmarked: !wasBookmarked,
        is_liked: !wasBookmarked,
      });
      try {
        const result = await toggleItemBookmark(bookmarkUrl, wasBookmarked, row.id);
        if (result === AUTH_REQUIRED || !result) {
          updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, {
            canonical_url: bookmarkUrl,
            is_item_bookmarked: wasBookmarked,
            is_liked: wasBookmarked,
          });
          if (result === AUTH_REQUIRED) alert('Sign in to save products');
        }
      } catch { /* optimistic UI already applied */ }
    }
    setIsLikeLoading(false);
  };

  const handleSelect = async () => {
    if (!offer.bid_id) return;
    updateRowOffer(row.id, () => true, { is_selected: false });
    updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_selected: true });
    try {
      const { selectOfferForRow } = await import('../../utils/api');
      await selectOfferForRow(row.id, offer.bid_id);
    } catch (err) {
      console.error('Failed to select offer', err);
    }
  };

  const handleToggleComments = async () => {
    if (showCommentInput) {
      setShowCommentInput(false);
      return;
    }
    setShowCommentInput(true);
    try {
      const fetched = await fetchCommentsApi(row.id);
      const filtered = offer.bid_id
        ? fetched.filter((c) => c.bid_id === offer.bid_id)
        : fetched;
      setComments(filtered);
    } catch { /* empty */ }
  };

  const handleSubmitComment = async () => {
    if (!commentText.trim()) return;
    const result = await createCommentApi(row.id, commentText.trim(), offer.bid_id ?? undefined);
    if (result === AUTH_REQUIRED) {
      alert('Sign in to add comments');
    } else if (result && typeof result === 'object' && 'id' in result) {
      setComments((prev) => [result as CommentDto, ...prev]);
      setCommentText('');
    }
  };

  const handleFeedback = async (feedbackType: FeedbackType) => {
    if (!offer.bid_id) return;
    const result = await submitFeedback(row.id, { bid_id: offer.bid_id, feedback_type: feedbackType });
    if (result === AUTH_REQUIRED) {
      alert('Sign in to rate this result');
      return;
    }
    if (!result || typeof result !== 'object' || !('status' in result)) {
      alert('Failed to save result feedback');
      return;
    }
    setFeedbackSent(feedbackType);
    setShowFeedbackMenu(false);
  };

  return (
    <div className={`rounded-lg transition-colors ${
      offer.is_selected ? 'bg-gold/5 ring-1 ring-gold/30' : 'hover:bg-canvas-dark'
    }`}>
      <div className="flex items-center gap-3 p-2">
        {offer.url && offer.url !== '#' ? (
          <a
            href={offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}${offer.bid_id ? `&bid_id=${offer.bid_id}` : ''}&row_id=${row.id}&source=${offer.source}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 block hover:opacity-80 transition-opacity"
            title="View product"
          >
            {offer.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={offer.image_url} alt={offer.title} className="w-12 h-12 rounded-md object-cover bg-canvas-dark block" />
            ) : (
              <div className="w-12 h-12 rounded-md bg-canvas-dark flex items-center justify-center">
                <svg className="w-5 h-5 text-onyx-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            )}
          </a>
        ) : (
          offer.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={offer.image_url} alt={offer.title} className="w-12 h-12 rounded-md object-cover bg-canvas-dark flex-shrink-0" />
          ) : (
            <div className="w-12 h-12 rounded-md bg-canvas-dark flex-shrink-0 flex items-center justify-center">
              <svg className="w-5 h-5 text-onyx-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          )
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-ink truncate">{offer.title}</p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="text-sm font-semibold text-ink">{priceStr}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-canvas-dark text-ink-muted">{friendlySource(offer.source)}</span>
            {offer.merchant && offer.merchant !== 'Unknown' && (
              <span className="text-[10px] text-onyx-muted">{offer.merchant}</span>
            )}
            {isVendor && offer.contact_quality_score != null && offer.contact_quality_score >= 0.7 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-0.5">
                <Shield size={8} /> Verified Contact
              </span>
            )}
            {isVendor && offer.contact_quality_score != null && offer.contact_quality_score >= 0.4 && offer.contact_quality_score < 0.7 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-0.5">
                <Shield size={8} /> Has Contact
              </span>
            )}
            {offer.is_vendor_bookmarked && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-0.5">
                <Star size={8} className="fill-current" /> Saved to Rolodex
              </span>
            )}
            {!offer.is_vendor_bookmarked && offer.is_item_bookmarked && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 flex items-center gap-0.5">
                <Heart size={8} className="fill-current" /> Saved Product
              </span>
            )}
            {isRfpSent && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200">Emailed</span>
            )}
            {offer.is_selected && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gold/10 text-gold-dark border border-gold/20 flex items-center gap-0.5">
                <CheckCircle2 size={8} /> Selected
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {showRfpToggle && (
            <button
              onClick={onToggleRfpSelection}
              className={`px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                isRfpSent
                  ? 'bg-green-50 text-green-700 border border-green-200'
                  : isRfpSelected
                  ? 'bg-gold/15 text-gold-dark border border-gold/30'
                  : 'bg-canvas-dark text-ink-muted border border-warm-grey hover:border-gold/30 hover:text-ink'
              }`}
              title={isRfpSent ? 'Included in outreach this session' : isRfpSelected ? 'Remove from outreach' : 'Add to outreach'}
            >
              {isRfpSent ? 'Sent' : isRfpSelected ? 'In Outreach' : 'Add to Outreach'}
            </button>
          )}
          <button
            onClick={handleToggleLike}
            className={`p-1.5 rounded-md transition-colors ${
              isVendor && offer.vendor_id
                ? (offer.is_vendor_bookmarked ? 'text-amber-500 bg-amber-50' : 'text-onyx-muted hover:text-amber-500 hover:bg-amber-50')
                : (offer.is_item_bookmarked ? 'text-red-500 bg-red-50' : 'text-onyx-muted hover:text-red-500 hover:bg-red-50')
            }`}
            title={isVendor && offer.vendor_id ? (offer.is_vendor_bookmarked ? 'Remove from Rolodex' : 'Save to Rolodex') : (offer.is_item_bookmarked ? 'Remove saved product' : 'Save product')}
            aria-pressed={isVendor && offer.vendor_id ? !!offer.is_vendor_bookmarked : !!offer.is_item_bookmarked}
          >
            {isVendor && offer.vendor_id
              ? <Star size={14} className={offer.is_vendor_bookmarked ? 'fill-current' : ''} />
              : <Heart size={14} className={offer.is_item_bookmarked ? 'fill-current' : ''} />
            }
          </button>
          <button
            onClick={handleSelect}
            className={`p-1.5 rounded-md transition-colors ${offer.is_selected ? 'text-gold-dark bg-gold/15' : 'text-onyx-muted hover:text-gold-dark hover:bg-gold/10'}`}
            title={offer.is_selected ? 'Selected' : 'Select this option'}
          >
            <CheckCircle2 size={14} className={offer.is_selected ? 'fill-gold/30' : ''} />
          </button>
          <button
            onClick={handleToggleComments}
            className={`p-1.5 rounded-md transition-colors ${showCommentInput ? 'text-accent-blue bg-accent-blue/10' : 'text-onyx-muted hover:text-accent-blue hover:bg-accent-blue/10'}`}
            title="Comment"
          >
            <MessageSquare size={14} />
          </button>
          <div className="relative">
            <button
              onClick={() => setShowFeedbackMenu(!showFeedbackMenu)}
              className={`p-1.5 rounded-md transition-colors ${
                feedbackSent
                  ? feedbackSent === 'good_lead' || feedbackSent === 'saved_me_time'
                    ? 'text-green-600 bg-green-50'
                    : 'text-orange-600 bg-orange-50'
                  : 'text-onyx-muted hover:text-ink hover:bg-canvas-dark'
              }`}
              title={feedbackSent ? `Feedback: ${feedbackSent}` : 'Rate this result'}
            >
              {feedbackSent && (feedbackSent === 'good_lead' || feedbackSent === 'saved_me_time')
                ? <ThumbsUp size={14} className="fill-current" />
                : feedbackSent
                ? <ThumbsDown size={14} className="fill-current" />
                : <ThumbsUp size={14} />
              }
            </button>
            {showFeedbackMenu && (
              <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-warm-grey rounded-lg shadow-lg py-1 min-w-[160px]">
                {FEEDBACK_OPTIONS.map((opt) => (
                  <button
                    key={opt.type}
                    onClick={() => handleFeedback(opt.type)}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-canvas-dark transition-colors ${
                      feedbackSent === opt.type ? 'font-semibold text-gold-dark' : 'text-ink'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          {isVendor ? (
            <button
              onClick={() => setShowContactModal(true)}
              className="px-3 py-1.5 text-xs font-medium bg-status-success text-white rounded-lg hover:bg-status-success/90 transition-colors"
            >
              Request Quote
            </button>
          ) : offer.url && offer.url !== '#' ? (
            <a
              href={offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}${offer.bid_id ? `&bid_id=${offer.bid_id}` : ''}&row_id=${row.id}&source=${offer.source}`}
              target="_blank"
              rel="noopener noreferrer"
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                (row.is_service || SERVICE_FIRST_DESIRE_TIERS.has(row.desire_tier || '')) && (offer.price === null || offer.price === undefined)
                  ? 'bg-status-success text-white hover:bg-status-success/90'
                  : 'bg-gold text-navy hover:bg-gold-dark'
              }`}
            >
              {(row.is_service || SERVICE_FIRST_DESIRE_TIERS.has(row.desire_tier || '')) && (offer.price === null || offer.price === undefined)
                ? 'Request Quote'
                : (row.desire_tier === 'bespoke' || row.desire_tier === 'high_value')
                  ? 'Contact Source'
                  : 'View Deal'}
            </a>
          ) : null}
        </div>
      </div>

      {showCommentInput && (
        <div className="px-3 pb-3 space-y-2">
          {comments.length > 0 && (
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {comments.map((c) => (
                <div key={c.id} className="text-xs text-ink-muted bg-canvas-dark rounded px-2 py-1">
                  {c.body}
                  <span className="ml-2 text-onyx-muted">{new Date(c.created_at).toLocaleDateString()}</span>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              type="text"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSubmitComment(); }}
              placeholder="Add a note..."
              className="flex-1 text-xs px-2 py-1.5 rounded-lg border border-warm-grey bg-white text-ink placeholder:text-onyx-muted focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold/30"
            />
            <button
              onClick={handleSubmitComment}
              disabled={!commentText.trim()}
              className="px-2 py-1.5 text-xs font-medium bg-accent-blue text-white rounded-lg hover:bg-accent-blue/90 disabled:opacity-50 transition-colors"
            >
              Post
            </button>
          </div>
        </div>
      )}

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
