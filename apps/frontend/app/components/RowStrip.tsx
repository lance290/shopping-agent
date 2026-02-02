import { useEffect, useRef, useState } from 'react';
import { Row, Offer, OfferSortMode, useShoppingStore } from '../store';
import RequestTile from './RequestTile';
import OfferTile from './OfferTile';
import ProviderStatusBadge from './ProviderStatusBadge';
import { Archive, RefreshCw, FlaskConical, Undo2, Link2, X } from 'lucide-react';
import { fetchSingleRowFromDb, runSearchApiWithStatus, selectOfferForRow, toggleLikeApi, fetchLikesApi, createCommentApi, fetchCommentsApi } from '../utils/api';
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
  const rowProviderStatuses = useShoppingStore(state => state.rowProviderStatuses);
  const moreResultsIncoming = useShoppingStore(state => state.moreResultsIncoming);
  const setRowOfferSort = useShoppingStore(state => state.setRowOfferSort);
  const setIsSearching = useShoppingStore(state => state.setIsSearching);
  const setRowResults = useShoppingStore(state => state.setRowResults);
  const updateRow = useShoppingStore(state => state.updateRow);
  const isPendingArchive = pendingRowDelete?.row.id === row.id;
  const sortMode: OfferSortMode = rowOfferSort[row.id] || 'original';
  const providerStatuses = rowProviderStatuses[row.id];
  const hasMoreIncoming = moreResultsIncoming[row.id] ?? false;

  const [cooldownUntil, setCooldownUntil] = useState<number>(0);
  const [searchErrorMessage, setSearchErrorMessage] = useState<string | null>(null);
  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const didAutoLoadRef = useRef<boolean>(false);
  const didLoadLikesRef = useRef<boolean>(false);
  const loadedLikesRef = useRef<any[]>([]);
  const didLoadCommentsRef = useRef<boolean>(false);

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
    };
  }, []);

  const canRefresh = () => Date.now() > cooldownUntil;

  const getCanonicalOfferUrl = (offer: Offer): string | null => {
    const raw = offer.url || '';

    const extract = (u: string): string | null => {
      if (!u) return null;

      // If this is our clickout wrapper, unwrap it.
      if (u.startsWith('/api/clickout')) {
        try {
          const parsed = new URL(u, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
          const inner = parsed.searchParams.get('url');
          return inner ? decodeURIComponent(inner) : null;
        } catch {
          return null;
        }
      }

      // If it's a real http(s) URL, keep it.
      if (u.startsWith('http://') || u.startsWith('https://')) return u;

      return null;
    };

    return extract(raw) || extract(offer.click_url || '');
  };

  const refresh = async (mode: 'all' | 'rainforest') => {
    console.log('[RowStrip] refresh() called, mode:', mode, 'canRefresh:', canRefresh(), 'cooldownUntil:', cooldownUntil, 'now:', Date.now());
    if (!canRefresh()) {
      console.log('[RowStrip] refresh blocked by cooldown');
      return;
    }

    const until = Date.now() + 5000;
    setCooldownUntil(until);
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    cooldownTimerRef.current = setTimeout(() => setCooldownUntil(0), 5000);

    setIsSearching(true);
    setSearchErrorMessage(null);
    console.log('[RowStrip] calling runSearchApiWithStatus for row:', row.id, 'title:', row.title);
    try {
      const searchResponse = await runSearchApiWithStatus(
        row.title,
        row.id,
        mode === 'rainforest' ? { providers: ['rainforest'] } : undefined
      );
      console.log('[RowStrip] searchResponse:', searchResponse.results.length, 'results, userMessage:', searchResponse.userMessage);
      
      if (searchResponse.userMessage) {
        setSearchErrorMessage(searchResponse.userMessage);
      }
      
      // Re-fetch likes after search to ensure sync.
      const likes = await fetchLikesApi(row.id);
      const mergedResults = mergeLikes(searchResponse.results, likes);
      
      setRowResults(row.id, mergedResults, searchResponse.providerStatuses);

      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
    } finally {
      setIsSearching(false);
    }
  };

  // Helper to merge likes into offers
  const mergeLikes = (currentOffers: Offer[], likes: any[]): Offer[] => {
    if (!likes || likes.length === 0) return currentOffers;

    // Create maps to store both liked status and timestamp
    const likedBidData = new Map(
      likes.filter(l => l.bid_id).map(l => [l.bid_id, l.created_at])
    );
    const likedUrlData = new Map(
      likes.filter(l => l.offer_url).map(l => [l.offer_url, l.created_at])
    );

    return currentOffers.map((offer) => {
      const canonical = getCanonicalOfferUrl(offer);
      let likedAt: string | undefined;
      let isLiked = false;

      if (offer.bid_id && likedBidData.has(offer.bid_id)) {
        isLiked = true;
        likedAt = likedBidData.get(offer.bid_id);
      } else if (canonical && likedUrlData.has(canonical)) {
        isLiked = true;
        likedAt = likedUrlData.get(canonical);
      }

      return {
        ...offer,
        is_liked: isLiked,
        liked_at: likedAt,
      };
    });
  };

  // Load likes when active (once)
  useEffect(() => {
    if (isActive && !didLoadLikesRef.current && row.id) {
      didLoadLikesRef.current = true;
      console.log('[Like] fetching likes for row:', row.id);
      fetchLikesApi(row.id).then(likes => {
        console.log('[Like] fetched likes:', likes);
        loadedLikesRef.current = Array.isArray(likes) ? likes : [];
        if (likes.length > 0) {
          const merged = mergeLikes(offers, likes);
          console.log('[Like] merged offers with likes, matched:', merged.filter(o => o.is_liked).length);
          if (JSON.stringify(merged) !== JSON.stringify(offers)) {
            setRowResults(row.id, merged);
          }
        }
      });
    }
  }, [isActive, row.id, offers, setRowResults]);

  useEffect(() => {
    if (!isActive || !row.id) return;
    if (!loadedLikesRef.current || loadedLikesRef.current.length === 0) return;

    const merged = mergeLikes(offers, loadedLikesRef.current);
    if (JSON.stringify(merged) !== JSON.stringify(offers)) {
      setRowResults(row.id, merged);
    }
  }, [isActive, row.id, offers, setRowResults]);

  // Helper to merge comment previews into offers (latest comment wins)
  const mergeComments = (currentOffers: Offer[], comments: any[]): Offer[] => {
    if (!comments || comments.length === 0) return currentOffers;

    const latestByBidId = new Map<number, string>();
    const latestByUrl = new Map<string, string>();

    for (const c of comments) {
      const body = typeof c?.body === 'string' ? c.body : '';
      if (!body) continue;
      if (typeof c?.bid_id === 'number') {
        if (!latestByBidId.has(c.bid_id)) latestByBidId.set(c.bid_id, body);
        continue;
      }
      if (typeof c?.offer_url === 'string' && c.offer_url) {
        if (!latestByUrl.has(c.offer_url)) latestByUrl.set(c.offer_url, body);
      }
    }

    return currentOffers.map((offer) => {
      const preview =
        (offer.bid_id && latestByBidId.get(offer.bid_id)) ||
        (offer.url && latestByUrl.get(offer.url)) ||
        offer.comment_preview;
      return preview ? { ...offer, comment_preview: preview } : offer;
    });
  };

  // Load comments when active (once)
  useEffect(() => {
    if (isActive && !didLoadCommentsRef.current && row.id) {
      didLoadCommentsRef.current = true;
      fetchCommentsApi(row.id).then((comments) => {
        if (comments.length > 0) {
          const merged = mergeComments(offers, comments);
          if (JSON.stringify(merged) !== JSON.stringify(offers)) {
            setRowResults(row.id, merged);
          }
        }
      });
    }
  }, [isActive, row.id, offers, setRowResults]);

  const isSearching = useShoppingStore(state => state.isSearching);
  
  useEffect(() => {
    if (!isActive) return;
    if (didAutoLoadRef.current) return;
    // Don't auto-refresh if Chat is already streaming results
    const streamingInProgress = isSearching || (moreResultsIncoming[row.id] ?? false);
    if (streamingInProgress) return;
    if (Array.isArray(offers) && offers.length > 0) {
        // If we have offers but haven't loaded likes yet, ensure we do (handled above)
        return;
    }

    didAutoLoadRef.current = true;
    refresh('all');
  }, [isActive, row.id, isSearching, moreResultsIncoming]);

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
        // Liked items come before unliked items
        const likeDiff = Number(Boolean(b.offer.is_liked)) - Number(Boolean(a.offer.is_liked));
        if (likeDiff !== 0) return likeDiff;

        // Among liked items, sort by most recently liked (descending)
        if (a.offer.is_liked && b.offer.is_liked) {
          const aTime = a.offer.liked_at ? new Date(a.offer.liked_at).getTime() : 0;
          const bTime = b.offer.liked_at ? new Date(b.offer.liked_at).getTime() : 0;
          if (bTime !== aTime) return bTime - aTime; // Most recent first
        }

        // Otherwise preserve original order
        return a.idx - b.idx;
      })
      .map((entry) => entry.offer);
  };

  const getOfferKey = (offer: Offer, idx: number) => {
    if (offer.bid_id) return `bid:${offer.bid_id}`;
    const canonical = getCanonicalOfferUrl(offer);
    if (canonical) return `url:${canonical}`;
    return `fallback:${offer.title}-${offer.merchant}-${offer.price}-${idx}`;
  };

  const updateLoadedLikes = (rowId: number, isLiked: boolean, bidId?: number, offerUrl?: string) => {
    if (!rowId) return;
    const current = Array.isArray(loadedLikesRef.current) ? [...loadedLikesRef.current] : [];
    const matches = (like: any) => {
      if (bidId && like?.bid_id === bidId) return true;
      if (offerUrl && like?.offer_url === offerUrl) return true;
      return false;
    };
    const filtered = current.filter((like) => !matches(like));
    if (isLiked) {
      filtered.push({
        row_id: rowId,
        bid_id: bidId,
        offer_url: offerUrl,
        created_at: new Date().toISOString()
      });
    }
    loadedLikesRef.current = filtered;
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

  const handleToggleLike = async (offer: Offer) => {
    const previousOffers = [...offers];
    const newIsLiked = !offer.is_liked;

    const canonicalUrl = getCanonicalOfferUrl(offer);
    const offerBidId = offer.bid_id;
    
    console.log('[Like] handleToggleLike called:', {
      offerTitle: offer.title,
      offerBidId,
      canonicalUrl,
      offerPrice: offer.price,
      offersCount: offers.length,
    });
    
    // Optimistic update - match by bid_id, canonical URL, or object reference
    const updatedOffers = offers.map((item, idx) => {
      const itemUrl = getCanonicalOfferUrl(item);

      // Match by bid_id if available
      if (offerBidId && item.bid_id === offerBidId) {
        console.log('[Like] matched by bid_id at index', idx);
        return {
          ...item,
          is_liked: newIsLiked,
          liked_at: newIsLiked ? new Date().toISOString() : undefined
        };
      }
      // Match by canonical URL if no bid_id on clicked offer
      if (!offerBidId && canonicalUrl && itemUrl === canonicalUrl) {
        console.log('[Like] matched by URL at index', idx);
        return {
          ...item,
          is_liked: newIsLiked,
          liked_at: newIsLiked ? new Date().toISOString() : undefined
        };
      }
      // Fallback: match by title + price + merchant
      if (!offerBidId && !canonicalUrl) {
        if (item.title === offer.title && item.price === offer.price && item.merchant === offer.merchant) {
          console.log('[Like] matched by title/price/merchant at index', idx);
          return {
            ...item,
            is_liked: newIsLiked,
            liked_at: newIsLiked ? new Date().toISOString() : undefined
          };
        }
      }
      return item;
    });

    setRowResults(row.id, updatedOffers);
    
    // Call API
    // Use bid_id if available, otherwise canonical URL
    const success = await toggleLikeApi(
      row.id,
      newIsLiked,
      offer.bid_id || undefined,
      canonicalUrl || undefined
    );
    
    console.log('[Like] toggled:', { rowId: row.id, bidId: offer.bid_id, url: canonicalUrl, newIsLiked, success });
    
    if (success) {
      updateLoadedLikes(row.id, newIsLiked, offer.bid_id || undefined, canonicalUrl || undefined);
      onToast?.(newIsLiked ? 'Liked this offer.' : 'Removed like.', 'success');
    } else {
      // Revert on failure
      console.error('[RowStrip] Failed to save like');
      setRowResults(row.id, previousOffers);
      onToast?.('Failed to save like.', 'error');
    }
  };

  const handleComment = (_offer: Offer) => {
    const comment = window.prompt('Add a comment for this offer');
    if (!comment || comment.trim().length === 0) return;

    const body = comment.trim();
    const previousOffers = [...offers];

    // Optimistic UI
    const optimisticOffers = offers.map((item) => {
      if (_offer.bid_id && item.bid_id === _offer.bid_id) {
        return { ...item, comment_preview: body };
      }
      if (!_offer.bid_id && item.url === _offer.url) {
        return { ...item, comment_preview: body };
      }
      return item;
    });
    setRowResults(row.id, optimisticOffers);

    createCommentApi(row.id, body, _offer.bid_id, _offer.url)
      .then((created) => {
        if (created) {
          onToast?.('Comment saved.', 'success');
          return;
        }
        setRowResults(row.id, previousOffers);
        onToast?.('Failed to save comment. Try again.', 'error');
      })
      .catch(() => {
        setRowResults(row.id, previousOffers);
        onToast?.('Failed to save comment. Try again.', 'error');
      });
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

  const handleCopySearchLink = async () => {
    try {
      if (typeof window === 'undefined') return;

      // Create a shareable URL with the search query
      const url = new URL(window.location.origin);
      url.searchParams.set('q', row.title);

      if (navigator?.clipboard) {
        await navigator.clipboard.writeText(url.toString());
        onToast?.('Search link copied to clipboard.', 'success');
        return;
      }

      onToast?.('Could not copy link.', 'error');
    } catch (err) {
      console.error('[RowStrip] Failed to copy search link:', err);
      onToast?.('Failed to copy link.', 'error');
    }
  };

  return (
    <div 
      data-testid="row-strip"
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

        {/* Provider Status Badges */}
        {providerStatuses && providerStatuses.length > 0 && (
          <div className="flex-1 flex items-center justify-end px-4 gap-2 overflow-hidden opacity-80 hover:opacity-100 transition-opacity">
            {providerStatuses.map((status, idx) => (
              <ProviderStatusBadge key={status.provider_id + idx} status={status} />
            ))}
          </div>
        )}

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              handleCopySearchLink();
            }}
            className="h-8 w-8 p-0 rounded-lg border border-warm-grey/60 text-onyx-muted hover:text-onyx"
            title="Copy search link"
          >
            <Link2 size={14} />
          </Button>

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
              className="h-9 w-9 p-0 rounded-lg border border-warm-grey/60 text-onyx-muted hover:text-status-error hover:border-status-error hover:bg-status-error/10 transition-all"
              title="Archive row"
            >
              <X size={18} strokeWidth={2.5} className="text-onyx-muted" />
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
                <>
                  {sortedOffers.map((offer, idx) => (
                    <OfferTile
                      key={getOfferKey(offer, idx)}
                      offer={offer}
                      index={idx}
                      rowId={row.id}
                      onSelect={handleSelectOffer}
                      onToggleLike={handleToggleLike}
                      onComment={handleComment}
                      onShare={handleShare}
                    />
                  ))}
                  {/* More incoming indicator */}
                  {hasMoreIncoming && (
                    <div className="flex flex-col items-center justify-center w-48 shrink-0 rounded-2xl border-2 border-dashed border-agent-blurple/40 bg-agent-blurple/5 text-agent-blurple p-4 animate-pulse">
                      <RefreshCw className="w-6 h-6 animate-spin mb-3" />
                      <span className="text-sm font-semibold">More incoming...</span>
                      <span className="text-xs opacity-70 mt-1">Searching providers</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center w-64 rounded-2xl border border-dashed border-warm-grey bg-warm-light/60 text-onyx-muted p-4">
                  {row.status === 'sourcing' || hasMoreIncoming ? (
                    <>
                      <RefreshCw className="w-6 h-6 animate-spin mb-3 opacity-50" />
                      <span className="text-sm font-medium">Sourcing offers...</span>
                    </>
                  ) : searchErrorMessage ? (
                    <>
                      <FlaskConical className="w-6 h-6 mb-3 opacity-50" />
                      <span className="text-sm font-medium text-center">{searchErrorMessage}</span>
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
