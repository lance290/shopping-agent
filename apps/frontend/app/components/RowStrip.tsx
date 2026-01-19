import { Row, Offer, useShoppingStore } from '../store';
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
          {offers && offers.length > 0 ? (
            offers.map((offer, idx) => (
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
