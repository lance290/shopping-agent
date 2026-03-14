'use client';

import { useState } from 'react';
import { useShoppingStore } from '../../store';
import type { Row, Offer } from '../../store';
import { toggleVendorBookmark, toggleItemBookmark, createCommentApi, fetchCommentsApi, AUTH_REQUIRED, submitFeedback, FEEDBACK_OPTIONS } from '../../utils/api';
import type { CommentDto, FeedbackType } from '../../utils/api';
import { Heart, CheckCircle2, MessageSquare, Star, ThumbsUp, ThumbsDown, Shield } from 'lucide-react';
import VendorContactModal from '../VendorContactModal';

const SERVICE_FIRST_DESIRE_TIERS = new Set(['service', 'bespoke', 'high_value', 'advisory']);

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

interface BidCardProps {
  offer: Offer;
  row: Row;
  isRfpSelected: boolean;
  isRfpSent: boolean;
  onToggleRfpSelection?: () => void;
}

export default function BidCard({
  offer,
  row,
  isRfpSelected,
  isRfpSent,
  onToggleRfpSelection,
}: BidCardProps) {
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
