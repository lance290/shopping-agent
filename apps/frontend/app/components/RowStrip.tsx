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

  const sortOffers = (list: Offer[]) => {
    if (!list || list.length === 0) return [];
    if (sortMode === 'original') return list;

    const byPrice = [...list].sort((a, b) => {
      const ap = Number.isFinite(a.price) ? a.price : Number.POSITIVE_INFINITY;
      const bp = Number.isFinite(b.price) ? b.price : Number.POSITIVE_INFINITY;
      return ap - bp;
    });
    return sortMode === 'price_desc' ? byPrice.reverse() : byPrice;
  };

  const applyLikedOrdering = (list: Offer[]) => {
    return list
      .map((offer, idx) => ({ offer, idx }))
      .sort((a, b) => {
        const likeDiff = Number(Boolean(b.offer.is_liked)) - Number(Boolean(a.offer.is_liked));
        if (likeDiff !== 0) return likeDiff;
        return a.idx - b.idx;
      })
      .map((entry) => entry.offer);
  };

  const sortedOffers = applyLikedOrdering(sortOffers(offers));

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

  const handleToggleLike = (offer: Offer) => {
    const updatedOffers = offers.map((item) => {
      if (item.bid_id && offer.bid_id && item.bid_id === offer.bid_id) {
        return { ...item, is_liked: !item.is_liked };
      }
      if (!item.bid_id && !offer.bid_id && item.url === offer.url) {
        return { ...item, is_liked: !item.is_liked };
      }
      return item;
    });

    setRowResults(row.id, applyLikedOrdering(sortOffers(updatedOffers)));
    onToast?.(offer.is_liked ? 'Removed like.' : 'Liked this offer.', 'success');
  };

  const handleComment = (_offer: Offer) => {
    const comment = window.prompt('Add a comment for this offer');
    if (comment && comment.trim().length > 0) {
      onToast?.('Comment saved.', 'success');
    }
  };

  const handleShare = async (offer: Offer) => {
    const link = offer.url || offer.click_url || '';
    try {
      if (navigator?.clipboard && link) {
        await navigator.clipboard.writeText(link);
        onToast?.('Link copied.', 'success');
        return;
      }
    } catch {
      // ignore
    }
    onToast?.('Share link ready.', 'success');
  };

  return (
    <div 
      className={cn(
        "rounded-md transition-all duration-200 overflow-hidden bg-transparent"
      )}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between px-4 py-2 border-b border-warm-grey/60 bg-transparent">
        <div className="flex items-center gap-4">
          <div className={cn(
            "w-2.5 h-2.5 rounded-full",
            isActive ? "bg-agent-blurple" : "bg-warm-grey"
          )} />
          <h3 className="text-base font-semibold text-onyx">{row.title}</h3>
          <span className={cn(
            "text-[10px] uppercase tracking-wider font-semibold",
            row.status === 'closed' ? "text-status-success" : "text-onyx-muted"
          )}>
            {row.status === 'closed' ? 'selected' : row.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative group">
            <select
              className="appearance-none pl-3 pr-8 py-1.5 text-xs font-medium border border-warm-grey/60 rounded-lg bg-warm-light text-onyx hover:border-onyx-muted focus:outline-none focus:ring-1 focus:ring-onyx/20 transition-colors cursor-pointer"
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
            className="h-8 w-8 p-0 rounded-lg border border-warm-grey/60 text-onyx-muted hover:text-onyx"
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
              <Undo2 size={14} className="text-warm-light" />
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
              className="h-8 w-8 p-0 rounded-lg border border-warm-grey/60 text-warm-light hover:text-status-error"
              title="Archive row"
            >
              <Archive size={14} className="text-warm-light" />
            </Button>
          )}
          
          <div className="ml-2 text-[10px] font-mono text-warm-light/50">
            #{row.id}
          </div>
        </div>
      </div>
      
      <div className="p-5 bg-transparent">
        <div className="flex gap-6 min-h-[450px]">
          {/* Request/Options Tile (Pinned Left) */}
          <div className="shrink-0">
            <RequestTile row={row} />
          </div>

          {/* Offer Tiles (Scrollable) */}
          <div className="flex-1 overflow-x-auto scrollbar-hide">
            <div className="flex gap-6 min-h-[450px] pr-2">
              {sortedOffers && sortedOffers.length > 0 ? (
                sortedOffers.map((offer, idx) => (
                  <OfferTile
                    key={`${row.id}-${idx}`}
                    offer={offer}
                    index={idx}
                    rowId={row.id}
                    onSelect={handleSelectOffer}
                    onToggleLike={handleToggleLike}
                    onComment={handleComment}
                    onShare={handleShare}
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
      </div>
    </div>
  );
}
