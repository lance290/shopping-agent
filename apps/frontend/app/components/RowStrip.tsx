import { useEffect, useRef, useState } from 'react';
import { Row, Offer, OfferSortMode, useShoppingStore } from '../store';
import RequestTile from './RequestTile';
import OfferTile from './OfferTile';
import { Archive, RefreshCw, FlaskConical, Undo2 } from 'lucide-react';
import { runSearchApi, selectOfferForRow } from '../utils/api';
import { Button } from '../../components/ui/Button';
import { cn } from '../../utils/cn';

interface RowStripProps {
  row: Row;
  offers: Offer[];
  isActive: boolean;
  onSelect: () => void;
  onToast?: (message: string, tone?: 'success' | 'error') => void;
}

export default function RowStrip({ row, offers, isActive, onSelect, onToast }: RowStripProps) {
  const requestDeleteRow = useShoppingStore(state => state.requestDeleteRow);
  const pendingRowDelete = useShoppingStore(state => state.pendingRowDelete);
  const undoDeleteRow = useShoppingStore(state => state.undoDeleteRow);
  const rowOfferSort = useShoppingStore(state => state.rowOfferSort);
  const setRowOfferSort = useShoppingStore(state => state.setRowOfferSort);
  const setIsSearching = useShoppingStore(state => state.setIsSearching);
  const setRowResults = useShoppingStore(state => state.setRowResults);
  const updateRow = useShoppingStore(state => state.updateRow);
  const isPendingArchive = pendingRowDelete?.row.id === row.id;
  const sortMode: OfferSortMode = rowOfferSort[row.id] || 'original';

  const [cooldownUntil, setCooldownUntil] = useState<number>(0);
  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
    };
  }, []);

  const canRefresh = () => Date.now() > cooldownUntil;

  const refresh = async (mode: 'all' | 'rainforest') => {
    if (!canRefresh()) return;

    const until = Date.now() + 5000;
    setCooldownUntil(until);
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    cooldownTimerRef.current = setTimeout(() => setCooldownUntil(0), 5000);

    setIsSearching(true);
    try {
      const results = await runSearchApi(
        row.title,
        row.id,
        mode === 'rainforest' ? { providers: ['rainforest'] } : undefined
      );
      setRowResults(row.id, results);
    } finally {
      setIsSearching(false);
    }
  };

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

  const handleSelectOffer = async (offer: Offer) => {
    if (!offer.bid_id) return;

    const previousOffers = offers.map((item) => ({ ...item }));
    const previousStatus = row.status;
    const updatedOffers = offers.map((item) => ({
      ...item,
      is_selected: item.bid_id === offer.bid_id,
    }));

    setRowResults(row.id, updatedOffers);
    updateRow(row.id, { status: 'closed' });

    const success = await selectOfferForRow(row.id, offer.bid_id);
    if (!success) {
      console.error('[RowStrip] Failed to persist selection');
      setRowResults(row.id, previousOffers);
      updateRow(row.id, { status: previousStatus });
      onToast?.('Could not select that deal. Try again.', 'error');
      return;
    }

    onToast?.(`Selected “${offer.title}”`, 'success');
  };

  return (
    <div 
      className={cn(
        "rounded-md transition-all duration-200 overflow-hidden bg-transparent"
      )}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between px-5 py-3 border border-warm-grey/60 bg-white/80 rounded-md">
        <div className="flex items-center gap-4">
          <div className={cn(
            "w-2.5 h-2.5 rounded-full",
            isActive ? "bg-agent-blurple" : "bg-warm-grey"
          )} />
          <h3 className="text-lg font-semibold text-onyx">{row.title}</h3>
          <span className={cn(
            "text-[10px] px-2.5 py-1 rounded-full uppercase tracking-wider font-semibold",
            row.status === 'sourcing' ? "bg-warm-light text-onyx-muted" : 
            row.status === 'closed' ? "bg-status-success/10 text-status-success" : 
            "bg-warm-light text-onyx-muted"
          )}>
            {row.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <select
              className="appearance-none pl-3 pr-8 py-1.5 text-xs font-medium border border-warm-grey rounded-lg bg-white text-onyx hover:border-onyx-muted focus:outline-none focus:ring-1 focus:ring-onyx/10 transition-colors cursor-pointer"
              value={sortMode}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => {
                e.stopPropagation();
                setRowOfferSort(row.id, e.target.value as OfferSortMode);
              }}
              aria-label="Sort offers"
            >
              <option value="original">Featured</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-onyx-muted">
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              refresh('all');
            }}
            disabled={!canRefresh()}
            className="h-8 w-8 p-0 rounded-lg border border-warm-grey text-onyx-muted hover:text-onyx"
            title="Refresh offers"
          >
            <RefreshCw size={14} className={!canRefresh() ? "opacity-50" : ""} />
          </Button>

          {isPendingArchive ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={(e) => {
                e.stopPropagation();
                undoDeleteRow();
              }}
              className="h-8 px-3 text-xs gap-1.5"
            >
              <Undo2 size={14} />
              Undo
            </Button>
          ) : (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                requestDeleteRow(row.id);
              }}
              className="h-8 w-8 p-0 rounded-lg border border-warm-grey text-onyx-muted hover:text-status-error"
              title="Archive row"
            >
              <Archive size={14} />
            </Button>
          )}
          
          <div className="ml-2 text-[10px] font-mono text-onyx-muted/50">
            #{row.id}
          </div>
        </div>
      </div>
      
      <div className="p-5 overflow-x-auto scrollbar-hide bg-transparent">
        <div className="flex gap-6 min-h-[320px]">
          {/* Request Tile (Leftmost) */}
          <RequestTile row={row} />
          
          {/* Offer Tiles */}
          {sortedOffers && sortedOffers.length > 0 ? (
            sortedOffers.map((offer, idx) => (
              <OfferTile
                key={`${row.id}-${idx}`}
                offer={offer}
                index={idx}
                rowId={row.id}
                onSelect={handleSelectOffer}
              />
            ))
          ) : (
            <div className="flex flex-col items-center justify-center w-64 rounded-2xl border border-dashed border-warm-grey bg-warm-light/60 text-onyx-muted">
              {row.status === 'sourcing' ? (
                <>
                  <RefreshCw className="w-6 h-6 animate-spin mb-3 opacity-50" />
                  <span className="text-sm font-medium">Sourcing offers...</span>
                </>
              ) : (
                <>
                  <FlaskConical className="w-6 h-6 mb-3 opacity-50" />
                  <span className="text-sm font-medium">No offers found</span>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
