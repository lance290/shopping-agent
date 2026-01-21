import { Offer } from '../store';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Star, Truck, ShieldCheck } from 'lucide-react';
import { cn } from '../../utils/cn';

interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
  onSelect?: (offer: Offer) => void | Promise<void>;
}

export default function OfferTile({ offer, index, rowId, onSelect }: OfferTileProps) {
  // Build clickout URL
  const clickUrl = offer.click_url || `/api/clickout?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`;
  const safePrice = Number.isFinite(offer.price) ? offer.price : 0;
  const source = String(offer.source || '').toLowerCase();
  const isBiddable = source === 'manual' || source.includes('seller');
  const isSelected = offer.is_selected === true;
  const canSelect = Boolean(onSelect && offer.bid_id);
  
  return (
    <Card
      variant="hover"
      className={cn(
        "min-w-[260px] max-w-[260px] h-[360px] flex flex-col relative group",
        isSelected ? "border-status-success" : "border-warm-grey/70"
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
            <div className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide bg-warm-light text-onyx-muted border border-warm-grey/70">
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
        <div className="w-full h-[65%] bg-white relative overflow-hidden flex items-center justify-center">
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
        <div className="p-4 flex flex-col flex-1 bg-canvas border-t border-warm-grey/60">
          <div className="text-xs font-medium text-onyx-muted mb-1 truncate flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-onyx-muted/60"></span>
            {offer.merchant_domain || offer.merchant}
          </div>
          
          <div className="text-sm font-semibold text-onyx line-clamp-2 mb-4 h-10 leading-snug group-hover:text-onyx-muted transition-colors" title={offer.title}>
            {offer.title}
          </div>
          
          <div className="mt-auto">
            <div className="flex justify-between items-end mb-3">
              <div className="text-lg font-semibold text-onyx">
                {offer.currency === 'USD' ? '$' : offer.currency}
                {safePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              
              {offer.rating && (
                <div className="flex items-center gap-1 text-[11px] text-onyx-muted font-medium bg-warm-light px-2 py-0.5 rounded-full border border-warm-grey/60">
                  <Star size={10} className="fill-agent-blurple text-agent-blurple" />
                  <span>{offer.rating}</span>
                  {offer.reviews_count && <span className="text-onyx-muted/70">({offer.reviews_count})</span>}
                </div>
              )}
            </div>
            
            {offer.shipping_info && (
              <div className="flex items-center gap-1.5 text-[10px] text-onyx-muted font-medium mb-3">
                <Truck size={12} />
                <span className="truncate">{offer.shipping_info}</span>
              </div>
            )}
            
            <div className="grid gap-2">
              {canSelect && !isSelected && (
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    onSelect?.(offer);
                  }}
                  className="w-full h-9"
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
