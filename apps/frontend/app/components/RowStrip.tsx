import { useEffect, useRef, useState } from 'react';
import { Row, Offer, OfferSortMode, useShoppingStore } from '../store';
import RequestTile from './RequestTile';
import OfferTile from './OfferTile';
import ProviderStatusBadge from './ProviderStatusBadge';
import { RefreshCw, FlaskConical, Undo2, Link2, X } from 'lucide-react';
import { fetchSingleRowFromDb, runSearchApiWithStatus, selectOfferForRow, toggleLikeApi, createCommentApi, fetchCommentsApi, AUTH_REQUIRED } from '../utils/api';
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
  const rowSearchErrors = useShoppingStore(state => state.rowSearchErrors);
  const moreResultsIncoming = useShoppingStore(state => state.moreResultsIncoming);
  const setRowOfferSort = useShoppingStore(state => state.setRowOfferSort);
  const setIsSearching = useShoppingStore(state => state.setIsSearching);
  const setRowResults = useShoppingStore(state => state.setRowResults);
  const updateRowOffer = useShoppingStore(state => state.updateRowOffer);
  const updateRow = useShoppingStore(state => state.updateRow);
  const isPendingArchive = pendingRowDelete?.row.id === row.id;
  const sortMode: OfferSortMode = rowOfferSort[row.id] || 'original';
  const providerStatuses = rowProviderStatuses[row.id];
  const searchError = rowSearchErrors[row.id];
  const hasMoreIncoming = moreResultsIncoming[row.id] ?? false;

  const [cooldownUntil, setCooldownUntil] = useState<number>(0);
  const [localSearchError, setLocalSearchError] = useState<string | null>(null);
  const activeSearchError = searchError || localSearchError;

  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const didAutoLoadRef = useRef<boolean>(false);
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
      if (u.startsWith('/api/clickout') || u.startsWith('/api/out')) {
        try {
          const parsed = new URL(u, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
          const inner = parsed.searchParams.get('url');
          return inner ? decodeURIComponent(inner) : null;
        } catch {
          return null;
        }
      }

      // Service-provider tiles often use mailto links.
      if (u.startsWith('mailto:')) return u;

      // If it's a real http(s) URL, keep it.
      if (u.startsWith('http://') || u.startsWith('https://')) return u;

      return null;
    };

    return extract(raw) || extract(offer.click_url || '');
  };

  const refresh = async (mode: 'all' | 'amazon') => {
    if (!canRefresh()) {
      return;
    }

    const until = Date.now() + 5000;
    setCooldownUntil(until);
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    cooldownTimerRef.current = setTimeout(() => setCooldownUntil(0), 5000);

    setIsSearching(true);
    setLocalSearchError(null);
    try {
      const searchResponse = await runSearchApiWithStatus(
        row.title,
        row.id,
        mode === 'amazon' ? { providers: ['amazon'] } : undefined
      );

      if (searchResponse.userMessage) {
        setLocalSearchError(searchResponse.userMessage);
      }

      // is_liked comes directly from the Bid now — no separate merge needed
      setRowResults(row.id, searchResponse.results, searchResponse.providerStatuses);

      const freshRow = await fetchSingleRowFromDb(row.id);
      if (freshRow) {
        updateRow(row.id, freshRow);
      }
    } finally {
      setIsSearching(false);
    }
  };

  // is_liked now comes directly from the Bid via search results — no separate fetch/merge needed

  // Load comments when active (once)
  // Uses updateRowOffer for targeted mutation — safe during streaming
  useEffect(() => {
    if (isActive && !didLoadCommentsRef.current && row.id) {
      didLoadCommentsRef.current = true;
      fetchCommentsApi(row.id).then((comments) => {
        if (!comments || comments.length === 0) return;

        // Build lookup maps from comments
        const latestByBidId = new Map<number, string>();
        const countByBidId = new Map<number, number>();
        for (const c of comments) {
          const body = typeof c?.body === 'string' ? c.body : '';
          if (!body || typeof c?.bid_id !== 'number') continue;
          if (!latestByBidId.has(c.bid_id)) latestByBidId.set(c.bid_id, body);
          countByBidId.set(c.bid_id, (countByBidId.get(c.bid_id) || 0) + 1);
        }

        // Apply comment data via targeted mutations — never replaces the full array
        latestByBidId.forEach((preview, bidId) => {
          updateRowOffer(
            row.id,
            (o) => o.bid_id === bidId,
            { comment_preview: preview, comment_count: countByBidId.get(bidId) || 0 },
          );
        });
      });
    }
  }, [isActive, row.id, updateRowOffer]);

  const isSearching = useShoppingStore(state => state.isSearching);
  const streamingRowIds = useShoppingStore(state => state.streamingRowIds);
  const selectedProviders = useShoppingStore(state => state.selectedProviders);
  
  useEffect(() => {
    if (!isActive) return;
    if (didAutoLoadRef.current) return;
    // Don't auto-refresh if Chat is already streaming results or streaming lock is held
    const streamingInProgress = isSearching || (moreResultsIncoming[row.id] ?? false) || (streamingRowIds[row.id] ?? false);
    if (streamingInProgress) return;
    if (Array.isArray(offers) && offers.length > 0) {
        // Results already loaded (e.g. via chat SSE) — mark as loaded so toggle re-search works
        didAutoLoadRef.current = true;
        return;
    }

    didAutoLoadRef.current = true;

    // Run search — vendor directory results come through the normal search pipeline
    refresh('all');
  }, [isActive, row.id, isSearching, moreResultsIncoming, row.service_category, row.status, setRowResults, updateRow]);

  // Re-search when provider toggles change on the active row
  const prevProvidersRef = useRef<string>(JSON.stringify(selectedProviders));
  useEffect(() => {
    if (!isActive) return;
    const current = JSON.stringify(selectedProviders);
    if (current === prevProvidersRef.current) return;
    prevProvidersRef.current = current;
    // Skip if initial load hasn't happened yet or if already searching
    if (!didAutoLoadRef.current) return;
    if (isSearching) return;
    refresh('all');
  }, [isActive, selectedProviders, isSearching]);

  const sortOffers = (list: Offer[]) => {
    if (!list || list.length === 0) return [];
    if (sortMode === 'original') {
      const hasScore = list.some((o) => Number.isFinite(o.match_score as number));
      if (!hasScore) return list;
      return list
        .map((offer, idx) => ({ offer, idx }))
        .sort((a, b) => {
          const aScore = Number.isFinite(a.offer.match_score as number) ? (a.offer.match_score as number) : -1;
          const bScore = Number.isFinite(b.offer.match_score as number) ? (b.offer.match_score as number) : -1;
          if (bScore !== aScore) return bScore - aScore;
          return a.idx - b.idx;
        })
        .map((entry) => entry.offer);
    }

    const byPrice = [...list].sort((a, b) => {
      const ap = (a.price !== null && Number.isFinite(a.price)) ? a.price : Number.POSITIVE_INFINITY;
      const bp = (b.price !== null && Number.isFinite(b.price)) ? b.price : Number.POSITIVE_INFINITY;
      return ap - bp;
    });
    return sortMode === 'price_desc' ? byPrice.reverse() : byPrice;
  };

  const applyLikedOrdering = (list: Offer[]) => {
    return list
      .map((offer, idx) => ({ offer, idx }))
      .sort((a, b) => {
        // Selected items come FIRST (leftmost)
        const selectDiff = Number(Boolean(b.offer.is_selected)) - Number(Boolean(a.offer.is_selected));
        if (selectDiff !== 0) return selectDiff;

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

  const sortedOffers = applyLikedOrdering(sortOffers(offers));

  const handleSelectOffer = async (offer: Offer) => {
    if (!offer.bid_id) return;

    const previousStatus = row.status;
    // Optimistic: mark this offer selected, unselect others — targeted mutation
    updateRowOffer(row.id, () => true, { is_selected: false });
    updateRowOffer(row.id, (o: Offer) => o.bid_id === offer.bid_id, { is_selected: true });
    updateRow(row.id, { status: 'closed' });

    const success = await selectOfferForRow(row.id, offer.bid_id);
    if (!success) {
      console.error('[RowStrip] Failed to persist selection');
      // Revert: unselect all
      updateRowOffer(row.id, (o: Offer) => o.bid_id === offer.bid_id, { is_selected: false });
      updateRow(row.id, { status: previousStatus });
      onToast?.('Could not select that deal. Try again.', 'error');
      return;
    }

    onToast?.(`Selected "${offer.title}"`, 'success');
  };

  const _isLoggedIn = () => typeof window !== 'undefined' && !!localStorage.getItem('session_token');

  const handleToggleLike = async (offer: Offer) => {
    if (!_isLoggedIn()) {
      onToast?.('Sign up to save likes and track your finds → /login', 'error');
      return;
    }

    const optimisticIsLiked = !offer.is_liked;
    const offerBidId = offer.bid_id;

    // Optimistic update — targeted mutation, safe during streaming
    if (offerBidId) {
      updateRowOffer(row.id, (o: Offer) => o.bid_id === offerBidId, { is_liked: optimisticIsLiked });
    }

    // Call API — ONE toggle endpoint
    const toggled = await toggleLikeApi(
      row.id,
      optimisticIsLiked,
      offer.bid_id || undefined,
    );

    if (toggled === AUTH_REQUIRED) {
      if (offerBidId) {
        updateRowOffer(row.id, (o: Offer) => o.bid_id === offerBidId, { is_liked: !optimisticIsLiked });
      }
      localStorage.removeItem('session_token');
      onToast?.('Sign up to save likes and track your finds → /login', 'error');
      return;
    }
    if (toggled) {
      onToast?.(toggled.is_liked ? 'Liked this offer.' : 'Removed like.', 'success');
    } else {
      if (offerBidId) {
        updateRowOffer(row.id, (o: Offer) => o.bid_id === offerBidId, { is_liked: !optimisticIsLiked });
      }
      onToast?.('Failed to save like.', 'error');
    }
  };

  const handleComment = (_offer: Offer) => {
    if (!_isLoggedIn()) {
      onToast?.('Create an account to leave comments → /login', 'error');
      return;
    }

    const comment = window.prompt('Add a comment for this offer');
    if (!comment || comment.trim().length === 0) return;

    const body = comment.trim();
    const previousPreview = _offer.comment_preview;

    // Optimistic UI — targeted mutation, safe during streaming
    const matcher = _offer.bid_id
      ? (o: Offer) => o.bid_id === _offer.bid_id
      : (o: Offer) => o.url === _offer.url;
    updateRowOffer(row.id, matcher, { comment_preview: body });

    createCommentApi(row.id, body, _offer.bid_id, _offer.url)
      .then((created) => {
        if (created === AUTH_REQUIRED) {
          updateRowOffer(row.id, matcher, { comment_preview: previousPreview });
          localStorage.removeItem('session_token');
          onToast?.('Sign up to leave comments → /login', 'error');
          return;
        }
        if (created) {
          onToast?.('Comment saved.', 'success');
          return;
        }
        updateRowOffer(row.id, matcher, { comment_preview: previousPreview });
        onToast?.('Failed to save comment. Try again.', 'error');
      })
      .catch(() => {
        updateRowOffer(row.id, matcher, { comment_preview: previousPreview });
        onToast?.('Failed to save comment. Try again.', 'error');
      });
  };

  const handleShare = async (offer: Offer) => {
    try {
      // If offer has a bid_id, create a backend share link
      if (offer.bid_id) {
        const res = await fetch('/api/shares', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('session_token') || '' : ''}`,
          },
          body: JSON.stringify({ resource_type: 'tile', resource_id: offer.bid_id }),
        });
        if (res.ok) {
          const data = await res.json();
          const shareUrl = `${window.location.origin}/share/${data.token}`;
          await navigator.clipboard.writeText(shareUrl);
          onToast?.('Share link copied!', 'success');
          return;
        }
        if (res.status === 401) {
          // Still copy raw URL as fallback, but prompt signup
          const link = offer.url || offer.click_url || '';
          if (navigator?.clipboard && link) {
            await navigator.clipboard.writeText(link);
          }
          onToast?.('Sign up to create trackable share links → /login', 'error');
          return;
        }
      }
      // Fallback: copy raw URL
      const link = offer.url || offer.click_url || '';
      if (navigator?.clipboard && link) {
        await navigator.clipboard.writeText(link);
        onToast?.('Link copied.', 'success');
        return;
      }
    } catch {
      onToast?.('Could not copy share link.', 'error');
      return;
    }
    onToast?.('Could not generate share link.', 'error');
  };

  const handleCopySearchLink = async () => {
    try {
      if (typeof window === 'undefined') return;

      // Try creating a backend share link for the row
      const res = await fetch('/api/shares', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('session_token') || ''}`,
        },
        body: JSON.stringify({ resource_type: 'row', resource_id: row.id }),
      });
      if (res.ok) {
        const data = await res.json();
        const shareUrl = `${window.location.origin}/share/${data.token}`;
        await navigator.clipboard.writeText(shareUrl);
        onToast?.('Share link copied!', 'success');
        return;
      }

      // Fallback: copy search query URL
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
      data-row-id={row.id}
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
          {(() => {
            const statusLabels: Record<string, string> = {
              closed: 'Selected',
              new: 'New',
              sourcing: 'Searching',
            };
            const label = statusLabels[row.status];
            if (!label) return null;
            return (
              <span className={cn(
                "text-[10px] uppercase tracking-wider font-semibold",
                row.status === 'closed' ? "text-status-success" : "text-onyx-muted"
              )}>
                {label}
              </span>
            );
          })()}
        </div>

        {/* Provider Status Badges */}
        {providerStatuses && providerStatuses.length > 0 && (
          <div className="flex-1 flex items-center justify-end px-4 gap-2 overflow-hidden opacity-80 hover:opacity-100 transition-opacity">
            {providerStatuses.map((status) => (
              <ProviderStatusBadge key={status.provider_id} status={status} />
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
                      row={row}
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
                  {row.status === 'sourcing' || hasMoreIncoming || isSearching ? (
                    <>
                      <RefreshCw className="w-6 h-6 animate-spin mb-3 opacity-50" />
                      <span className="text-sm font-medium">
                        Sourcing offers...
                      </span>
                    </>
                  ) : activeSearchError ? (
                    <>
                      <FlaskConical className="w-6 h-6 mb-3 opacity-50" />
                      <span className="text-sm font-medium text-center">{activeSearchError}</span>
                    </>
                  ) : (
                    <>
                      <FlaskConical className="w-6 h-6 mb-3 opacity-50" />
                      <span className="text-sm font-medium">
                        No results found
                      </span>
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
