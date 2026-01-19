import { Row, Offer, OfferSortMode, useShoppingStore } from '../store';
import RequestTile from './RequestTile';
import OfferTile from './OfferTile';
import { Archive } from 'lucide-react';

interface RowStripProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  onSelect: () => void;
}

export default function RowStrip({ row, offers, isActive, onSelect }: RowStripProps) {
  const requestDeleteRow = useShoppingStore(state => state.requestDeleteRow);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);
  const rowOfferSort = useShoppingStore(state => state.rowOfferSort);
  const setRowOfferSort = useShoppingStore(state => state.setRowOfferSort);
  const isPendingArchive = pendingRowDelete?.row.id === row.id;
  const sortMode: OfferSortMode = rowOfferSort[row.id] || 'original';

  const sortedOffers = (() => {
    if (!offers || offers.length === 0) return [];
    if (sortMode === 'original') return offers;

    const byPrice = [...offers].sort((a, b) => {
      const ap = Number.isFinite(a.price) ? a.price : Number.POSITIVE_INFINITY;
      const bp = Number.isFinite(b.price) ? b.price : Number.POSITIVE_INFINITY;
      return ap - bp;
    });
    return sortMode === 'price_desc' ? byPrice.reverse() : byPrice;
  })();

  return (
    <div 
      className={`border rounded-lg bg-white mb-4 transition-all duration-200 ${
        isActive 
          ? 'ring-2 ring-blue-500 shadow-md border-transparent' 
          : 'border-gray-200 hover:border-blue-300 shadow-sm'
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between p-3 border-b border-gray-100 bg-gray-50/50 rounded-t-lg">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-blue-500' : 'bg-gray-300'}`} />
          <h3 className="font-medium text-gray-900">{row.title}</h3>
          <span className={`text-xs px-2 py-0.5 rounded-full uppercase tracking-wide font-medium ${
            row.status === 'sourcing' ? 'bg-yellow-100 text-yellow-700' : 
            row.status === 'closed' ? 'bg-green-100 text-green-700' : 
            'bg-gray-100 text-gray-600'
          }`}>
            {row.status}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <select
            className="text-xs border border-gray-200 bg-white rounded-md px-2 py-1 text-gray-700 hover:border-gray-300"
            value={sortMode}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              e.stopPropagation();
              setRowOfferSort(row.id, e.target.value as OfferSortMode);
            }}
            aria-label="Sort offers"
            title="Sort offers"
          >
            <option value="original">Original</option>
            <option value="price_asc">Price ↑</option>
            <option value="price_desc">Price ↓</option>
          </select>
          {isPendingArchive ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                undoDeleteRow();
              }}
              className="text-xs font-semibold text-blue-700 border border-blue-200 bg-blue-50 hover:bg-blue-100 px-2 py-1 rounded-md transition-colors"
              title="Undo archive"
              aria-label="Undo archive"
            >
              Undo
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                requestDeleteRow(row.id);
              }}
              className="text-xs font-medium text-gray-600 hover:text-red-700 border border-gray-200 hover:border-red-200 bg-white hover:bg-red-50 px-2 py-1 rounded-md transition-colors inline-flex items-center gap-1"
              title="Archive row"
              aria-label="Archive row"
            >
              <Archive size={14} />
              Archive
            </button>
          )}
          <div className="text-xs text-gray-400">
            ID: {row.id}
          </div>
        </div>
      </div>
      
      <div className="p-3 overflow-x-auto">
        <div className="flex gap-4 min-h-[280px]">
          {/* Request Tile (Leftmost) */}
          <RequestTile row={row} />
          
          {/* Offer Tiles */}
          {sortedOffers && sortedOffers.length > 0 ? (
            sortedOffers.map((offer, idx) => (
              <OfferTile key={`${row.id}-${idx}`} offer={offer} index={idx} rowId={row.id} />
            ))
          ) : (
            <div className="flex items-center justify-center w-64 text-sm text-gray-400 italic border-2 border-dashed border-gray-100 rounded-lg">
              {row.status === 'sourcing' ? 'Searching for offers...' : 'No offers found yet'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
