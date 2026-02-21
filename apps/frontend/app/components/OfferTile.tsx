import { Offer, Row, useShoppingStore } from '../store';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Heart, MessageSquare, Share2, ShieldCheck, Star, Truck, X, UserPlus, Mail, MailCheck } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useState } from 'react';
import { createPortal } from 'react-dom';
import { isLoggedIn } from '../utils/auth';
import VendorContactModal from './VendorContactModal';

interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
  row: Row;
  onSelect?: (offer: Offer) => void | Promise<void>;
  onToggleLike?: (offer: Offer) => void;
  onComment?: (offer: Offer) => void;
  onShare?: (offer: Offer) => void;
}

export default function OfferTile({
  offer,
  index,
  rowId,
  row,
  onSelect,
  onToggleLike,
  onComment,
  onShare,
}: OfferTileProps) {
  const [showVendorModal, setShowVendorModal] = useState(false);
  const [showAuthPrompt, setShowAuthPrompt] = useState(false);
  const updateRowOffer = useShoppingStore(state => state.updateRowOffer);

  // Build clickout URL - service providers show modal, others go through clickout
  const isQuoteBased = offer.price === null || offer.price === undefined;
  const safePrice = Number.isFinite(offer.price) ? offer.price! : 0;
  const source = String(offer.source || '').toLowerCase();
  const isBiddable = source === 'manual' || source.includes('seller');
  const isSellerQuote = source === 'seller_quote';
  const isServiceProvider = offer.is_service_provider === true;
  const clickUrl = isServiceProvider 
    ? offer.url 
    : (offer.click_url || `/api/clickout?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`);
  const isSelected = offer.is_selected === true;
  const isLiked = offer.is_liked === true;
  const canSelect = Boolean(onSelect && offer.bid_id);
  const isVendorDirectory = offer.source === 'vendor_directory';
  const ratingValue = typeof offer.rating === 'number' ? offer.rating : null;
  const reviewsValue = typeof offer.reviews_count === 'number' ? offer.reviews_count : null;
  const hasRating = ratingValue !== null && ratingValue > 0;
  const merchantLabel = offer.merchant_domain || offer.merchant;

  return (
    <Card
      variant="hover"
      data-testid="offer-tile"
      className={cn(
        "min-w-[255px] max-w-[255px] h-[450px] flex flex-col relative group",
        "shadow-[0_2px_6px_rgba(0,0,0,0.16)]",
        isSelected
          ? "border-status-success ring-2 ring-status-success/30 shadow-[0_10px_24px_rgba(28,148,64,0.25)]"
          : "border-warm-grey/70"
      )}
    >
      <a
        href={isServiceProvider ? '#' : clickUrl}
        target={isServiceProvider ? undefined : "_blank"}
        rel={isServiceProvider ? undefined : "noopener noreferrer"}
        className="flex flex-col h-full"
        onClick={isServiceProvider ? (e) => {
          e.preventDefault();
          setShowVendorModal(true);
        } : undefined}
      >
        {/* Badges */}
        <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
          {isServiceProvider && (
            <div className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-blue-500/10 text-blue-700 border border-blue-500/20">
              <ShieldCheck size={10} />
              Charter Provider
            </div>
          )}
          {isSellerQuote && !isServiceProvider && (
            <div className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
              <ShieldCheck size={10} />
              Vendor Quote
            </div>
          )}
          {offer.outreach_status === 'contacted' && (
            <div className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-amber-500/10 text-amber-700 border border-amber-500/20">
              <Mail size={10} />
              Contacted
            </div>
          )}
          {offer.outreach_status === 'quoted' && (
            <div className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-emerald-500/10 text-emerald-700 border border-emerald-500/20">
              <MailCheck size={10} />
              Quote Received
            </div>
          )}
          {isBiddable && !isSellerQuote && !isServiceProvider && (
            <div className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-black/5 text-onyx-muted border border-black/10">
              Negotiable
            </div>
          )}
          {!isBiddable && !isSellerQuote && !isServiceProvider && (
            <div className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-black/5 text-onyx-muted border border-black/10">
              {offer.source === 'vendor_directory' ? 'Specialist' : 'Marketplace'}
            </div>
          )}
        </div>

        <div className="absolute top-3 right-3 z-10 flex flex-col gap-1.5">
          {isSelected ? (
            <div className="flex items-center gap-1 bg-status-success/10 text-status-success text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide border border-status-success/20">
              <ShieldCheck size={10} />
              Selected
            </div>
          ) : (
            offer.match_score && offer.match_score > 0.7 && (
              <div className="flex items-center gap-1 bg-agent-blurple/10 text-agent-blurple text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide border border-agent-blurple/20">
                <Star size={10} className="fill-current" />
                Best Match
              </div>
            )
          )}
        </div>

        {/* Image Area */}
        <div className="w-full h-[40%] bg-white relative overflow-hidden flex items-center justify-center p-0.5">
          {offer.image_url ? (
            <img 
              src={offer.image_url} 
              alt={offer.title}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="text-warm-grey">
              <FallbackShoppingBag size={32} />
            </div>
          )}
        </div>
        
        {/* Content */}
        <div className="p-3 flex flex-col flex-1 bg-warm-light border-t border-warm-grey/70">
          <div className="text-xs font-medium text-onyx-muted mb-1 truncate flex items-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-onyx-muted/60"></span>
            {offer.merchant_domain || offer.merchant}
          </div>
          
          <div className="text-sm font-bold text-onyx line-clamp-3 mb-2 min-h-[48px] leading-snug group-hover:text-onyx-muted transition-colors" title={offer.title}>
            {offer.title}
          </div>

          {offer.comment_preview && (
            <div className="text-[10px] text-onyx-muted/90 bg-white/60 border border-warm-grey/60 rounded-md px-2 py-1 mb-2 line-clamp-2">
              {offer.comment_preview}
            </div>
          )}
          
          <div className="mt-auto">
            {isQuoteBased && (
              <div className="text-[11px] font-medium text-onyx-muted mb-8 text-center leading-snug">
                {isVendorDirectory
                  ? (offer.description
                      ? <span className="line-clamp-2">{offer.description}</span>
                      : <span>Specialist · Custom pricing</span>)
                  : 'Pricing on request'}
              </div>
            )}
            {!isQuoteBased && (
              <div className="text-[13px] font-semibold text-onyx mb-2">
                {offer.currency === 'USD' ? '$' : offer.currency}
                {safePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            )}
            <div className="flex items-center gap-2 mb-2">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggleLike?.(offer);
                }}
                aria-pressed={isLiked}
                className={cn(
                  "h-7 rounded-full border border-warm-grey/70 flex items-center justify-center transition-colors gap-0.5",
                  isLiked
                    ? "bg-status-success/10 text-status-success border-status-success/40"
                    : "bg-white text-onyx-muted hover:text-onyx",
                  offer.like_count && offer.like_count > 0 ? "w-auto px-1.5" : "w-7"
                )}
                title={isLiked ? 'Unlike' : 'Like'}
              >
                <Heart size={12} className={cn(isLiked && "fill-current")} />
                {offer.like_count != null && offer.like_count > 0 && (
                  <span className="text-[9px] font-semibold">{offer.like_count}</span>
                )}
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onComment?.(offer);
                }}
                className={cn(
                  "h-7 rounded-full border border-warm-grey/70 flex items-center justify-center bg-white text-onyx-muted hover:text-onyx transition-colors gap-0.5",
                  offer.comment_count && offer.comment_count > 0 ? "w-auto px-1.5" : "w-7"
                )}
                title="Comment"
              >
                <MessageSquare size={12} />
                {offer.comment_count != null && offer.comment_count > 0 && (
                  <span className="text-[9px] font-semibold">{offer.comment_count}</span>
                )}
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onShare?.(offer);
                }}
                className="h-7 w-7 rounded-full border border-warm-grey/70 flex items-center justify-center bg-white text-onyx-muted hover:text-onyx transition-colors"
                title="Share"
              >
                <Share2 size={12} />
              </button>
            </div>
            
            <div className="space-y-1 min-h-[36px]">
              {merchantLabel && (
                <div className="flex items-center gap-1.5 text-[10px] text-onyx-muted font-medium">
                  <span className="w-1 h-1 rounded-full bg-onyx-muted/60"></span>
                  <span className="truncate">{merchantLabel}</span>
                </div>
              )}

              {offer.shipping_info && (
                <div className="flex items-center gap-1.5 text-[10px] text-onyx-muted font-medium">
                  <Truck size={12} />
                  <span className="truncate">{offer.shipping_info}</span>
                </div>
              )}

              {/* Affiliate Disclosure (PRD 08) — shown on marketplace clickout tiles */}
              {!isServiceProvider && !isSellerQuote && !isBiddable && (
                <div className="text-[8px] text-onyx-muted/50 leading-tight" title="BuyAnything.ai may earn a commission from purchases made through this link.">
                  Ad · May earn commission
                </div>
              )}

              {hasRating && (
                <div className="flex items-center gap-1 text-[10px] text-onyx-muted font-medium">
                  <Star size={9} className="fill-[#F9AB00] text-[#F9AB00]" />
                  <span>{ratingValue?.toFixed(1)}</span>
                  {reviewsValue !== null && <span className="text-onyx-muted/70">({reviewsValue})</span>}
                </div>
              )}
            </div>
            
            <div className="grid gap-2">
              {canSelect && !isSelected && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onSelect?.(offer);
                  }}
                  className="w-full h-8 text-xs"
                >
                  Select
                </Button>
              )}
              {!isServiceProvider && safePrice > 0 && offer.bid_id && !isSelected && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    try {
                      // No drop-ship / checkout: route user directly to merchant via clickout.
                      window.open(clickUrl, '_blank', 'noopener,noreferrer');
                    } catch (err) {
                      console.error('[OfferTile] Clickout error:', err);
                    }
                  }}
                  className="w-full h-8 text-xs"
                >
                  Buy Now
                </Button>
              )}
              {isVendorDirectory && !isSelected && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!isLoggedIn()) {
                      setShowAuthPrompt(true);
                    } else {
                      setShowVendorModal(true);
                    }
                  }}
                  className="w-full h-8 text-xs"
                >
                  Request Quote
                </Button>
              )}
              {isSelected && (
                <div className="w-full py-2 text-center text-xs font-semibold text-status-success bg-status-success/10 rounded-full border border-status-success/20">
                  Selected
                </div>
              )}
            </div>
          </div>
        </div>
      </a>

      {showAuthPrompt && typeof document !== 'undefined' && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowAuthPrompt(false)} />
          <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 p-6 text-center">
            <button onClick={() => setShowAuthPrompt(false)} className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"><X size={18} /></button>
            <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center mx-auto mb-4">
              <UserPlus size={24} className="text-blue-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Create a free account</h3>
            <p className="text-sm text-gray-500 mb-5">
              Sign up in 30 seconds to request quotes from vendors. We&apos;ll keep your search history too.
            </p>
            <Button
              variant="primary"
              className="w-full mb-3"
              onClick={() => {
                // Save all anonymous row IDs so they can be claimed after login
                const storeState = useShoppingStore.getState();
                const rowIds = storeState.rows.map((r: { id: number }) => r.id);
                console.log('[OfferTile] Saving anonymous row IDs for claim:', rowIds);
                if (rowIds.length) sessionStorage.setItem('pending_claim_rows', JSON.stringify(rowIds));
                window.location.href = '/login';
              }}
            >
              Sign Up / Log In
            </Button>
            <button onClick={() => setShowAuthPrompt(false)} className="text-sm text-gray-400 hover:text-gray-600">
              Maybe later
            </button>
          </div>
        </div>,
        document.body
      )}

      {(isServiceProvider || isVendorDirectory) && (
        <VendorContactModal
          isOpen={showVendorModal}
          onClose={() => setShowVendorModal(false)}
          rowId={rowId}
          rowTitle={row.title}
          rowChoiceAnswers={row.choice_answers}
          serviceCategory={row.service_category}
          vendorName={offer.vendor_name || 'Contact'}
          vendorCompany={offer.vendor_company || offer.merchant}
          vendorEmail={offer.vendor_email || ''}
          onSent={() => {
            // Update the offer's outreach_status to 'contacted' after successful send
            const email = offer.vendor_email;
            if (email) {
              updateRowOffer(
                rowId,
                (o) => (o.vendor_email || '').toLowerCase() === email.toLowerCase(),
                { outreach_status: 'contacted' },
              );
            }
          }}
        />
      )}
    </Card>
  );
}

function FallbackShoppingBag({ size }: { size: number }) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="1.5" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
      <line x1="3" y1="6" x2="21" y2="6" />
      <path d="M16 10a4 4 0 0 1-8 0" />
    </svg>
  );
}
