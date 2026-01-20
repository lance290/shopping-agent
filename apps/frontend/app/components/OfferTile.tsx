import { Offer } from '../store';

interface OfferTileProps {
  offer: Offer;
  index: number;
  rowId: number;
  onSelect?: (offer: Offer) => void | Promise<void>;
}

export default function OfferTile({ offer, index, rowId, onSelect }: OfferTileProps) {
  // Build clickout URL (will be handled by Task 02)
  // We use the offer fields if available, otherwise fallback
  const clickUrl = offer.click_url || `/api/clickout?url=${encodeURIComponent(offer.url)}&row_id=${rowId}&idx=${index}&source=${encodeURIComponent(offer.source)}`;
  const safePrice = Number.isFinite(offer.price) ? offer.price : 0;
  const source = String(offer.source || '').toLowerCase();
  const isBiddable = source === 'manual' || source.includes('seller');
  const isSelected = offer.is_selected === true;
  const canSelect = Boolean(onSelect && offer.bid_id);
  
  return (
    <a
      href={clickUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`min-w-[220px] max-w-[220px] bg-white border rounded-lg overflow-hidden transition-all flex-shrink-0 flex flex-col group h-full relative ${
        isSelected
          ? 'border-green-500 ring-2 ring-green-300'
          : 'border-gray-200 hover:ring-2 hover:ring-blue-400'
      }`}
    >
      <div
        className={`absolute top-2 left-2 text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm z-10 uppercase tracking-wide ${
          isBiddable ? 'bg-purple-600 text-white' : 'bg-gray-600 text-white'
        }`}
        title={isBiddable ? 'Negotiation possible' : 'Offsite listing (no negotiation)'}
      >
        {isBiddable ? 'Biddable' : 'Not biddable'}
      </div>

      {isSelected ? (
        <div className="absolute top-2 right-2 bg-green-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm z-10 uppercase tracking-wide">
          Selected
        </div>
      ) : (
        offer.match_score && offer.match_score > 0.7 && (
          <div className="absolute top-2 right-2 bg-green-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm z-10 uppercase tracking-wide">
            Best Match
          </div>
        )
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
        
        <div className="mt-3 pt-2 space-y-2">
          {canSelect && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onSelect?.(offer);
              }}
              className={`w-full text-center text-sm font-semibold py-2 rounded-lg border transition-colors ${
                isSelected
                  ? 'bg-green-600 border-green-600 text-white'
                  : 'bg-white border-green-500 text-green-700 hover:bg-green-50'
              }`}
            >
              {isSelected ? 'Selected' : 'Select Deal'}
            </button>
          )}
          <span className="block w-full text-center bg-blue-600 text-white text-sm font-medium py-2 rounded-lg group-hover:bg-blue-700 transition-colors">
            View Deal →
          </span>
        </div>
      </div>
    </a>
  );
}
