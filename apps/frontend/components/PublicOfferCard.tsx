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
      <div className="bg-white rounded-xl border border-blue-100 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
        <div className="p-4 flex-1 flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <Store size={14} className="text-blue-600 shrink-0" />
            <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-600">From our vendor network</span>
          </div>
          <h3 className="font-semibold text-gray-900 text-sm leading-snug mb-1 line-clamp-2">
            {offer.vendor_company || offer.vendor_name || offer.title}
          </h3>
          <p className="text-xs text-gray-500 line-clamp-2 mb-3 flex-1">{offer.title}</p>
          {offer.vendor_website && (
            <a
              href={offer.vendor_website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:underline mb-3 inline-flex items-center gap-1"
            >
              Visit website <ExternalLink size={10} />
            </a>
          )}
          <button
            onClick={() => onRequestQuote?.(offer)}
            className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Request Quote
          </button>
        </div>
      </div>
    );
  }

  // Product card (retail)
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col">
      {offer.image_url && (
        <div className="aspect-square bg-gray-50 overflow-hidden">
          <img
            src={offer.image_url}
            alt={offer.title}
            className="w-full h-full object-contain p-2"
            loading="lazy"
          />
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-1">{offer.merchant}</p>
        <h3 className="font-medium text-gray-900 text-sm leading-snug mb-2 line-clamp-2 flex-1">{offer.title}</h3>

        {offer.rating && (
          <div className="flex items-center gap-1 mb-2">
            <Star size={12} className="text-yellow-400 fill-yellow-400" />
            <span className="text-xs text-gray-600">{offer.rating.toFixed(1)}</span>
            {offer.reviews_count && (
              <span className="text-xs text-gray-400">({offer.reviews_count.toLocaleString()})</span>
            )}
          </div>
        )}

        <div className="flex items-end justify-between mt-auto">
          <div>
            {offer.price !== null ? (
              <p className="text-lg font-bold text-gray-900">{formatPrice(offer.price, offer.currency)}</p>
            ) : (
              <p className="text-sm text-gray-500 italic">Request Quote</p>
            )}
            {offer.shipping_info && (
              <p className="text-[10px] text-gray-400">{offer.shipping_info}</p>
            )}
          </div>
          <button
            onClick={handleBuyClick}
            className="py-1.5 px-4 bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium rounded-lg transition-colors"
          >
            Buy
          </button>
        </div>
      </div>
    </div>
  );
}

export type { PublicOffer };
