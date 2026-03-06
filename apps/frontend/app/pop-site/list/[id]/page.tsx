'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import PopItemEditor from './PopItemEditor';
import HouseholdModal from './HouseholdModal';
import BulkParseModal from './BulkParseModal';
import PopListNav from './components/PopListNav';
import PopListHeader from './components/PopListHeader';
import PopListItems from './components/PopListItems';
import PopListFooterActions from './components/PopListFooterActions';
import { ItemComment, ItemLikeState, ListItem, PopList, TabType } from './components/types';

export default function PopListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [list, setList] = useState<PopList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState<Record<number, TabType>>({});
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [hasJoined, setHasJoined] = useState(false);
  const [editingItem, setEditingItem] = useState<ListItem | null>(null);
  const [showHousehold, setShowHousehold] = useState(false);
  const [showBulkParse, setShowBulkParse] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [itemLikes, setItemLikes] = useState<Record<number, ItemLikeState>>({});
  const [commentingItemId, setCommentingItemId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');
  const [itemComments, setItemComments] = useState<Record<number, ItemComment[]>>({});
  const [shoppingMode, setShoppingMode] = useState(false);
  const [togglingMode, setTogglingMode] = useState(false);

  useEffect(() => {
    async function fetchList() {
      try {
        const res = await fetch(`/api/pop/list/${id}`);
        if (!res.ok) throw new Error('List not found');
        const data: PopList = await res.json();
        setList(data);
        setShoppingMode(Boolean(data.shopping_mode));
        
        // Initialize social states
        if (data.items) {
          const initialLikes: Record<number, ItemLikeState> = {};
          data.items.forEach((item: ListItem) => {
            initialLikes[item.id] = { 
              liked: item.user_liked || false, 
              count: item.like_count || 0 
            };
          });
          setItemLikes(initialLikes);
        }

        if (data.items) {
          setExpandedItems((prev) => (prev.size > 0 ? prev : new Set(data.items.map((item) => item.id))));
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load list');
      } finally {
        setLoading(false);
      }
    }
    async function checkAuth() {
      try {
        const res = await fetch('/api/pop/my-list');
        setIsLoggedIn(res.ok);
      } catch {
        setIsLoggedIn(false);
      }
    }
    fetchList();
    checkAuth();
  }, [id]);

  const handleJoinList = async () => {
    setIsJoining(true);
    setJoinError(null);
    try {
      const res = await fetch(`/api/pop/join-list/${id}`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to join list');
      setHasJoined(true);
    } catch (e: unknown) {
      setJoinError(e instanceof Error ? e.message : 'Failed to join list');
    } finally {
      setIsJoining(false);
    }
  };

  const handleClearCompleted = async () => {
    if (checkedItems.size === 0) return;
    setIsClearing(true);
    try {
      const res = await fetch(`/api/pop/projects/${list?.project_id}/clear_completed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row_ids: Array.from(checkedItems) }),
      });
      if (!res.ok) throw new Error('Failed to clear completed items');
      
      setList((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.filter((item) => !checkedItems.has(item.id))
        };
      });
      setCheckedItems(new Set());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setIsClearing(false);
    }
  };

  const handleBulkParsed = (newItems: ListItem[]) => {
    setList((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: [...newItems, ...prev.items]
      };
    });
    setExpandedItems((prev) => {
      const next = new Set(prev);
      newItems.forEach((item) => next.add(item.id));
      return next;
    });
    setShowBulkParse(false);
  };

  const toggleExpanded = (itemId: number) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  const toggleChecked = (itemId: number) => {
    setCheckedItems((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  const getItemTab = (itemId: number): TabType => activeTab[itemId] || 'deals';
  const setItemTab = (itemId: number, tab: TabType) =>
    setActiveTab((prev) => ({ ...prev, [itemId]: tab }));

  const handleToggleShoppingMode = async () => {
    if (!list) return;
    const next = !shoppingMode;
    setTogglingMode(true);
    try {
      const res = await fetch(`/api/pop/projects/${list.project_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shopping_mode: next }),
      });
      if (res.ok) setShoppingMode(next);
    } catch { /* silent */ }
    finally { setTogglingMode(false); }
  };

  const handleClaimDeal = async (itemId: number, dealId: number) => {
    try {
      await fetch(`/api/pop/offer/${dealId}/claim`, { method: 'POST' });
      setList((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) => {
            if (item.id !== itemId) return item;
            return {
              ...item,
              deals: item.deals.map((d) => ({ ...d, is_selected: d.id === dealId })),
              swaps: item.swaps.map((swap) => ({ ...swap, is_selected: false })),
            };
          }),
        };
      });
    } catch { /* silent */ }
  };

  const handleUnclaimDeal = async (itemId: number, dealId: number) => {
    try {
      await fetch(`/api/pop/offer/${dealId}/claim`, { method: 'DELETE' });
      setList((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) => {
            if (item.id !== itemId) return item;
            return {
              ...item,
              deals: item.deals.map((d) => ({ ...d, is_selected: false })),
            };
          }),
        };
      });
    } catch { /* silent */ }
  };

  const handleClaimSwap = async (itemId: number, swapId: number) => {
    try {
      await fetch(`/api/pop/swap/${swapId}/claim`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row_id: itemId }),
      });
      setList((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) => {
            if (item.id !== itemId) return item;
            return {
              ...item,
              deals: item.deals.map((d) => ({ ...d, is_selected: false })),
              swaps: item.swaps.map((swap) => ({ ...swap, is_selected: swap.id === swapId })),
            };
          }),
        };
      });
    } catch { /* silent */ }
  };

  const handleUnclaimSwap = async (itemId: number, swapId: number) => {
    try {
      await fetch(`/api/pop/swap/${swapId}/claim`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row_id: itemId }),
      });
      setList((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) => {
            if (item.id !== itemId) return item;
            return {
              ...item,
              swaps: item.swaps.map((swap) => ({ ...swap, is_selected: false })),
            };
          }),
        };
      });
    } catch { /* silent */ }
  };

  const handleQuantityChange = async (itemId: number, qty: number) => {
    const qStr = String(Math.max(1, qty));
    setList((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.map((item) =>
          item.id === itemId ? { ...item, quantity: qStr } : item
        ),
      };
    });
    try {
      await fetch(`/api/pop/item/${itemId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: qStr }),
      });
    } catch { /* silent */ }
  };

  const handleToggleLike = async (rowId: number) => {
    // Optimistic update
    setItemLikes((prev) => {
      const cur = prev[rowId] || { liked: false, count: 0 };
      return { ...prev, [rowId]: { liked: !cur.liked, count: cur.liked ? Math.max(0, cur.count - 1) : cur.count + 1 } };
    });
    try {
      const res = await fetch(`/api/pop/item/${rowId}/react`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setItemLikes((prev) => ({ ...prev, [rowId]: { liked: data.liked, count: data.like_count } }));
      }
    } catch { /* revert handled by next poll */ }
  };

  const handleLoadComments = async (rowId: number) => {
    try {
      const res = await fetch(`/api/pop/item/${rowId}/comments`);
      if (res.ok) {
        const data = await res.json();
        setItemComments((prev) => ({ ...prev, [rowId]: data.comments }));
      }
    } catch { /* silent */ }
  };

  const handleToggleComments = (rowId: number) => {
    if (commentingItemId === rowId) {
      setCommentingItemId(null);
    } else {
      setCommentingItemId(rowId);
      handleLoadComments(rowId);
    }
    setCommentText('');
  };

  const handleSubmitComment = async (rowId: number) => {
    const text = commentText.trim();
    if (!text) return;
    try {
      const res = await fetch(`/api/pop/item/${rowId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        setCommentText('');
        handleLoadComments(rowId);
      }
    } catch { /* silent */ }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" />
      </div>
    );
  }

  if (error || !list) {
    return (
      <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4">
        <span className="text-4xl">😕</span>
        <p className="text-gray-600">{error || 'List not found'}</p>
        <Link href="/" className="text-green-600 hover:text-green-700 font-medium">
          Go to Pop
        </Link>
      </div>
    );
  }

  const totalItems = list.items.length;
  const checkedCount = checkedItems.size;
  const itemsWithDeals = list.items.filter((i) => i.deal_count > 0).length;
  const itemsWithSwaps = list.items.filter((i) => i.swaps.length > 0).length;

  const selectedItems = list.items.filter(
    (item) => item.deals.some((deal) => deal.is_selected) || item.swaps.some((swap) => swap.is_selected)
  );
  const selectedCount = selectedItems.length;
  const visibleItems = shoppingMode ? selectedItems : list.items;

  return (
    <div className="min-h-screen bg-gray-50">
      <PopListNav id={id} isLoggedIn={isLoggedIn} />

      <div className="max-w-2xl mx-auto px-4 py-6">
        <PopListHeader
          title={list.title}
          shoppingMode={shoppingMode}
          isLoggedIn={isLoggedIn}
          selectedCount={selectedCount}
          totalItems={totalItems}
          checkedCount={checkedCount}
          togglingMode={togglingMode}
          isClearing={isClearing}
          onShowBulkParse={() => setShowBulkParse(true)}
          onShowHousehold={() => setShowHousehold(true)}
          onToggleShoppingMode={handleToggleShoppingMode}
          onClearCompleted={handleClearCompleted}
        />

        {/* Savings Summary Banner */}
        {!shoppingMode && (itemsWithDeals > 0 || itemsWithSwaps > 0) && (
          <div className="mb-5 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-2xl px-4 py-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">💰</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-green-800">
                  Pop found savings on your list!
                </p>
                <p className="text-xs text-green-600 mt-0.5">
                  {itemsWithDeals} item{itemsWithDeals !== 1 ? 's' : ''} with deals
                  {itemsWithSwaps > 0 && (
                    <> &middot; {itemsWithSwaps} swap suggestion{itemsWithSwaps !== 1 ? 's' : ''}</>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}

        <PopListItems
          totalItems={totalItems}
          visibleItems={visibleItems}
          checkedItems={checkedItems}
          expandedItems={expandedItems}
          shoppingMode={shoppingMode}
          isLoggedIn={isLoggedIn}
          itemLikes={itemLikes}
          commentingItemId={commentingItemId}
          commentText={commentText}
          itemComments={itemComments}
          onToggleChecked={toggleChecked}
          onToggleExpanded={toggleExpanded}
          getItemTab={getItemTab}
          onSetItemTab={setItemTab}
          onQuantityChange={handleQuantityChange}
          onClaimDeal={handleClaimDeal}
          onUnclaimDeal={handleUnclaimDeal}
          onClaimSwap={handleClaimSwap}
          onUnclaimSwap={handleUnclaimSwap}
          onEditItem={setEditingItem}
          onToggleLike={handleToggleLike}
          onToggleComments={handleToggleComments}
          onSetCommentText={setCommentText}
          onSubmitComment={handleSubmitComment}
        />

        <PopListFooterActions
          id={id}
          title={list.title}
          totalItems={totalItems}
          isLoggedIn={isLoggedIn}
          hasJoined={hasJoined}
          isJoining={isJoining}
          joinError={joinError}
          onJoinList={handleJoinList}
        />
      </div>

      {editingItem && (
        <PopItemEditor
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onSaved={(updated) => {
            setList((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                items: prev.items.map((it) =>
                  it.id === editingItem.id
                    ? { ...it, ...updated }
                    : it
                ),
              };
            });
            setEditingItem(null);
          }}
        />
      )}

      {showHousehold && list && (
        <HouseholdModal
          projectId={list.project_id}
          onClose={() => setShowHousehold(false)}
        />
      )}

      {showBulkParse && list && (
        <BulkParseModal
          projectId={list.project_id}
          onClose={() => setShowBulkParse(false)}
          onParsed={handleBulkParsed}
        />
      )}
    </div>
  );
}
