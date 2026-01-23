import { Offer } from '../store';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Heart, MessageSquare, Share2, ShieldCheck, Star, Truck } from 'lucide-react';
import { cn } from '../../utils/cn';

interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
  onSelect?: (offer: Offer) => void | Promise<void>;
  onToggleLike?: (offer: Offer) => void;
  onComment?: (offer: Offer) => void;
  onShare?: (offer: Offer) => void;
}

export default function OfferTile({
  offer,
  index,
  rowId,
  onSelect,
  onToggleLike,
  onComment,
  onShare,
}: OfferTileProps) {
  // Build clickout URL
  const clickUrl = offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`;
  const safePrice = Number.isFinite(offer.price) ? offer.price : 0;
  const source = String(offer.source || '').toLowerCase();
  const isBiddable = source === 'manual' || source.includes('seller');
  const isSelected = offer.is_selected === true;
  const isLiked = offer.is_liked === true;
  const canSelect = Boolean(onSelect && offer.bid_id);
  const ratingValue = typeof offer.rating === 'number' ? offer.rating : null;
  const reviewsValue = typeof offer.reviews_count === 'number' ? offer.reviews_count : null;
  const hasRating = ratingValue !== null && ratingValue > 0;
  const merchantLabel = offer.merchant_domain || offer.merchant;
  
  return (
    <Card
      variant="hover"
      className={cn(
        "min-w-[255px] max-w-[255px] h-[360px] flex flex-col relative group",
        "shadow-[0_2px_6px_rgba(0,0,0,0.16)]",
        isSelected
          ? "border-status-success ring-2 ring-status-success/30 shadow-[0_10px_24px_rgba(28,148,64,0.25)]"
          : "border-warm-grey/70"
      )}
    >
      <a
        href={clickUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex flex-col h-full"
      >
        {/* Badges */}
        <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
          {isBiddable && (
            <div className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-black/5 text-onyx-muted border border-black/10">
              Negotiable
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
          <div className="text-[10px] font-medium text-onyx-muted mb-1 truncate flex items-center gap-1.5">
            <span className="w-1 h-1 rounded-full bg-onyx-muted/60"></span>
            {offer.merchant_domain || offer.merchant}
          </div>
          
          <div className="text-[12px] font-semibold text-onyx line-clamp-3 mb-2 min-h-[48px] leading-snug group-hover:text-onyx-muted transition-colors" title={offer.title}>
            {offer.title}
          </div>
          
          <div className="mt-auto">
            <div className="flex items-center gap-2 mb-2">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onToggleLike?.(offer);
                }}
                className={cn(
                  "h-7 w-7 rounded-full border border-warm-grey/70 flex items-center justify-center transition-colors",
                  isLiked
                    ? "bg-status-success/10 text-status-success border-status-success/40"
                    : "bg-white text-onyx-muted hover:text-onyx"
                )}
                title={isLiked ? 'Unlike' : 'Like'}
              >
                <Heart size={12} className={cn(isLiked && "fill-current")} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onComment?.(offer);
                }}
                className="h-7 w-7 rounded-full border border-warm-grey/70 flex items-center justify-center bg-white text-onyx-muted hover:text-onyx transition-colors"
                title="Comment"
              >
                <MessageSquare size={12} />
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
            <div className="text-[13px] font-semibold text-onyx mb-2">
              {offer.currency === 'USD' ? '$' : offer.currency}
              {safePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                  Select Deal
                </Button>
              )}
              {isSelected && (
                <div className="w-full py-2 text-center text-xs font-semibold text-status-success bg-status-success/10 rounded-full border border-status-success/20">
                  Deal Selected
                </div>
              )}
            </div>
          </div>
        </div>
      </a>
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
