import { Offer } from '../store';

interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
}

export default function OfferTile({ offer, index, rowId }: OfferTileProps) {
  // Build clickout URL (will be handled by Task 02)
  // We use the offer fields if available, otherwise fallback
  const clickUrl = offer.click_url || `/api/out?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`;
  const safePrice = Number.isFinite(offer.price) ? offer.price : 0;
  
  return (
    <a
      href={clickUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="min-w-[220px] max-w-[220px] bg-white border border-gray-200 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-400 transition-all flex-shrink-0 flex flex-col group h-full relative"
    >
      {offer.match_score && offer.match_score > 0.7 && (
        <div className="absolute top-2 right-2 bg-green-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm z-10 uppercase tracking-wide">
          Best Match
        </div>
      )}

      <div className="w-full h-32 bg-gray-100 relative overflow-hidden">
        {offer.image_url ? (
          <img 
            src={offer.image_url} 
            alt={offer.title}
            className="w-full h-full object-contain mix-blend-multiply p-2"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300">
            No Image
          </div>
        )}
      </div>
      
      <div className="p-3 flex flex-col flex-1">
        <div className="text-xs text-gray-500 mb-1 truncate" title={offer.merchant}>
          {offer.merchant_domain || offer.merchant}
        </div>
        
        <div className="text-sm font-medium text-gray-900 line-clamp-2 mb-2 group-hover:text-blue-600 transition-colors" title={offer.title}>
          {offer.title}
        </div>
        
        <div className="mt-auto pt-2 border-t border-gray-100 flex justify-between items-end">
          <div className="text-lg font-bold text-gray-900">
            {offer.currency === 'USD' ? '$' : offer.currency}
            {safePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          
          {offer.rating && (
            <div className="flex items-center gap-1 text-xs text-gray-600">
              <span className="text-yellow-400">★</span>
              <span>{offer.rating}</span>
              {offer.reviews_count && <span className="text-gray-400">({offer.reviews_count})</span>}
            </div>
          )}
        </div>
        
        {offer.shipping_info && (
          <div className="text-[10px] text-green-600 mt-1 truncate">
            {offer.shipping_info}
          </div>
        )}
      </div>
    </a>
  );
}
