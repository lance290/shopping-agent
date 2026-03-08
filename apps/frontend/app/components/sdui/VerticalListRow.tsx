'use client';

import { useState, useRef, useEffect } from 'react';
import { useShoppingStore, mapBidToOffer } from '../../store';
import type { Row, Offer } from '../../store';
import { runSearchApiWithStatus, fetchSingleRowFromDb, toggleLikeApi, createShareLink, createCommentApi, fetchCommentsApi, fetchWithAuth, AUTH_REQUIRED } from '../../utils/api';
import type { CommentDto } from '../../utils/api';
import { Trash2, RotateCw, Heart, CheckCircle2, MessageSquare, Share2, Copy } from 'lucide-react';
import { DynamicRenderer } from './DynamicRenderer';
import { validateUISchema } from '../../sdui/types';
import VendorContactModal from '../VendorContactModal';
import OutreachQueue from '../OutreachQueue';

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
  const [sortMode, setSortMode] = useState<'relevance' | 'price_asc' | 'price_desc'>('relevance');
  const unsortedOffers = offers.length > 0 ? offers : (row.bids || []).map(mapBidToOffer);
  const displayOffers = [...unsortedOffers].sort((a, b) => {
    // Liked/selected always float to top
    if (a.is_liked && !b.is_liked) return -1;
    if (!a.is_liked && b.is_liked) return 1;
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
    // Default: relevance (combined_score descending)
    const sa = a.match_score;
    const sb = b.match_score;
    if (sa != null && sb != null) return sb - sa;
    if (sa != null) return -1;
    if (sb != null) return 1;
    return 0;
  });
  
  const requestDeleteRow = useShoppingStore((s) => s.requestDeleteRow);
  const setIsSearching = useShoppingStore((s) => s.setIsSearching);
  const setRowResults = useShoppingStore((s) => s.setRowResults);
  const updateRow = useShoppingStore((s) => s.updateRow);

  const handleRerunSearch = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setIsSearching(true);
      const res = await runSearchApiWithStatus(row.title, row.id);
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

          <div className="space-y-2">
            {displayOffers.length === 0 && !hasSchema && (
              <p className="text-sm text-onyx-muted italic">No options found yet.</p>
            )}
            {displayOffers.map((offer, i) => (
              <BidCard key={offer.bid_id ?? i} offer={offer} row={row} />
            ))}
          </div>

          {displayOffers.some((o) => o.source === 'vendor_directory') && (
            <OutreachQueue
              rowId={row.id}
              desireTier={row.desire_tier || 'service'}
              offers={displayOffers}
            />
          )}
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
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState<CommentDto[]>([]);
  const [isLikeLoading, setIsLikeLoading] = useState(false);
  const updateRowOffer = useShoppingStore((s) => s.updateRowOffer);
  const priceStr = offer.price !== null && offer.price !== undefined
    ? `$${offer.price.toFixed(2)}`
    : 'Request Quote';

  const isVendor = offer.source === 'vendor_directory' || offer.is_service_provider;

  const handleToggleLike = async () => {
    if (!offer.bid_id || isLikeLoading) return;
    setIsLikeLoading(true);
    updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_liked: !offer.is_liked });
    try {
      const result = await toggleLikeApi(row.id, !!offer.is_liked, offer.bid_id);
      if (result === AUTH_REQUIRED) {
        updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_liked: offer.is_liked });
        alert('Sign in to save favorites');
      } else if (result && typeof result === 'object' && 'is_liked' in result) {
        updateRowOffer(row.id, (o) => o.bid_id === offer.bid_id, { is_liked: result.is_liked });
      }
    } catch { /* optimistic UI already applied */ }
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
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-sm font-semibold text-ink">{priceStr}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-canvas-dark text-ink-muted">{friendlySource(offer.source)}</span>
            {offer.merchant && offer.merchant !== 'Unknown' && (
              <span className="text-[10px] text-onyx-muted">{offer.merchant}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={handleToggleLike}
            className={`p-1.5 rounded-md transition-colors ${offer.is_liked ? 'text-red-500 bg-red-50' : 'text-onyx-muted hover:text-red-500 hover:bg-red-50'}`}
            title={offer.is_liked ? 'Unlike' : 'Like'}
            aria-pressed={!!offer.is_liked}
          >
            <Heart size={14} className={offer.is_liked ? 'fill-current' : ''} />
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
              className="px-3 py-1.5 text-xs font-medium bg-gold text-navy rounded-lg hover:bg-gold-dark transition-colors"
            >
              View Deal
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
