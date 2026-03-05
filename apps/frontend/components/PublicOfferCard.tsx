'use client';

import { ExternalLink, Store, Star } from 'lucide-react';

interface PublicOffer {
  title: string;
  price: number | null;
  currency?: string;
  merchant: string;
  url: string;
  image_url?: string | null;
  source: string;
  rating?: number | null;
  reviews_count?: number | null;
  shipping_info?: string | null;
  match_score?: number;
  vendor_name?: string | null;
  vendor_company?: string | null;
  vendor_website?: string | null;
}

interface PublicOfferCardProps {
  offer: PublicOffer;
  onRequestQuote?: (offer: PublicOffer) => void;
}

export default function PublicOfferCard({ offer, onRequestQuote }: PublicOfferCardProps) {
  const isVendor = offer.source === 'vendor_directory';

  const formatPrice = (price: number | null, currency?: string) => {
    if (price === null || price === undefined) return null;
    const symbol = currency === 'GBP' ? '£' : currency === 'EUR' ? '€' : '$';
    return `${symbol}${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const handleBuyClick = () => {
    if (!offer.url) return;
    const clickoutUrl = `/api/out?url=${encodeURIComponent(offer.url)}&merchant=${encodeURIComponent(offer.merchant || '')}`;
    window.open(clickoutUrl, '_blank', 'noopener');
  };

  if (isVendor) {
    return (
      <div className="bg-white rounded-lg border border-warm-grey shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col">
        <div className="p-4 flex-1 flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <Store size={14} className="text-gold-dark shrink-0" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-gold-dark">From our vendor network</span>
          </div>
          <h3 className="font-semibold text-ink text-sm leading-snug mb-1 line-clamp-2">
            {offer.vendor_company || offer.vendor_name || offer.title}
          </h3>
          <p className="text-xs text-ink-muted line-clamp-2 mb-3 flex-1">{offer.title}</p>
          {offer.vendor_website && (
            <a
              href={offer.vendor_website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent-blue hover:underline mb-3 inline-flex items-center gap-1"
            >
              Visit website <ExternalLink size={10} />
            </a>
          )}
          <button
            onClick={() => onRequestQuote?.(offer)}
            className="w-full py-2 px-3 bg-gold hover:bg-gold-dark text-navy text-sm font-semibold rounded-lg transition-colors"
          >
            Request Quote
          </button>
        </div>
      </div>
    );
  }

  // Product card (retail)
  return (
    <div className="bg-white rounded-lg border border-warm-grey shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col">
      {offer.image_url && (
        <div className="aspect-square bg-canvas-dark overflow-hidden relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={offer.image_url}
            alt={offer.title}
            className="w-full h-full object-contain p-2"
            loading="lazy"
          />
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-[10px] text-ink-muted uppercase tracking-wider mb-1">{offer.merchant}</p>
        <h3 className="font-medium text-ink text-sm leading-snug mb-2 line-clamp-2 flex-1">{offer.title}</h3>

        {offer.rating && (
          <div className="flex items-center gap-1 mb-2">
            <Star size={12} className="text-yellow-400 fill-yellow-400" />
            <span className="text-xs text-ink-muted">{offer.rating.toFixed(1)}</span>
            {offer.reviews_count && (
              <span className="text-xs text-onyx-muted">({offer.reviews_count.toLocaleString()})</span>
            )}
          </div>
        )}

        <div className="flex items-end justify-between mt-auto">
          <div>
            {offer.price !== null ? (
              <p className="text-lg font-bold text-ink">{formatPrice(offer.price, offer.currency)}</p>
            ) : (
              <p className="text-sm text-ink-muted italic">Request Quote</p>
            )}
            {offer.shipping_info && (
              <p className="text-[10px] text-onyx-muted">{offer.shipping_info}</p>
            )}
          </div>
          <button
            onClick={handleBuyClick}
            className="py-1.5 px-4 bg-gold hover:bg-gold-dark text-navy text-sm font-semibold rounded-lg transition-colors"
          >
            Buy
          </button>
        </div>
      </div>
    </div>
  );
}

export type { PublicOffer };
