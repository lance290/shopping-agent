'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import PopItemEditor from './PopItemEditor';
import HouseholdModal from './HouseholdModal';
import BulkParseModal from './BulkParseModal';

interface Deal {
  id: number;
  title: string;
  price: number | null;
  source: string;
  url: string | null;
  image_url: string | null;
}

interface Swap {
  id: number;
  title: string;
  price: number | null;
  source: string;
  url: string | null;
  image_url: string | null;
  savings_vs_first: number | null;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
  created_at: string | null;
  deals: Deal[];
  swaps: Swap[];
  lowest_price: number | null;
  deal_count: number;
  department?: string | null;
  brand?: string | null;
  size?: string | null;
  quantity?: string | null;
  origin_channel?: string | null;
  origin_user_id?: number | null;
  like_count?: number;
  user_liked?: boolean;
  comment_count?: number;
  coupon?: {
    swap_id: number;
    savings_cents: number;
    savings_display: string;
    brand_name: string | null;
    product_name: string;
    url: string | null;
  } | null;
}

interface PopList {
  project_id: number;
  title: string;
  items: ListItem[];
}

type TabType = 'deals' | 'swaps';

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const seconds = Math.floor((new Date().getTime() - new Date(dateStr).getTime()) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + 'y ago';
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + 'mo ago';
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + 'd ago';
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + 'h ago';
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + 'm ago';
  return Math.floor(seconds) + 's ago';
}

export default function PopListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [list, setList] = useState<PopList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
  const [hasInitializedExpanded, setHasInitializedExpanded] = useState(false);
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState<Record<number, TabType>>({});
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [joinError, setJoinError] = useState<string | null>(null);
  const [hasJoined, setHasJoined] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [copiedReferral, setCopiedReferral] = useState(false);
  const [referralLink, setReferralLink] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<ListItem | null>(null);
  const [showHousehold, setShowHousehold] = useState(false);
  const [showBulkParse, setShowBulkParse] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [itemLikes, setItemLikes] = useState<Record<number, { liked: boolean; count: number }>>({});
  const [commentingItemId, setCommentingItemId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');
  const [itemComments, setItemComments] = useState<Record<number, { id: number; user_name: string; text: string; created_at: string | null }[]>>({});

  useEffect(() => {
    async function fetchList() {
      try {
        const res = await fetch(`/api/pop/list/${id}`);
        if (!res.ok) throw new Error('List not found');
        const data = await res.json();
        setList(data);
        
        // Initialize social states
        if (data.items) {
          const initialLikes: Record<number, { liked: boolean; count: number }> = {};
          data.items.forEach((item: ListItem) => {
            initialLikes[item.id] = { 
              liked: item.user_liked || false, 
              count: item.like_count || 0 
            };
          });
          setItemLikes(initialLikes);
        }

        if (!hasInitializedExpanded && data.items) {
          setExpandedItems(new Set(data.items.map((i: any) => i.id)));
          setHasInitializedExpanded(true);
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
        const loggedIn = res.ok;
        setIsLoggedIn(loggedIn);
        if (loggedIn) {
          try {
            const refRes = await fetch('/api/pop/referral');
            if (refRes.ok) {
              const refData = await refRes.json();
              setReferralLink(refData.referral_link || null);
            }
          } catch {
            // non-fatal: referral link is optional
          }
        }
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
      
      // Update local state by removing checked items
      setList((prev: any) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.filter((item: any) => !checkedItems.has(item.id))
        };
      });
      setCheckedItems(new Set());
    } catch (e: any) {
      setError(e.message || 'An error occurred');
    } finally {
      setIsClearing(false);
    }
  };

  const handleBulkParsed = (newItems: any[]) => {
    setList((prev: any) => {
      if (!prev) return prev;
      return {
        ...prev,
        items: [...newItems, ...prev.items]
      };
    });
    setExpandedItems((prev) => {
      const next = new Set(prev);
      newItems.forEach((item: any) => next.add(item.id));
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
            <span className="text-lg font-bold text-green-700">Pop</span>
          </Link>
          {isLoggedIn ? (
            <Link
              href={`/pop-site/chat?list=${id}`}
              className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
            >
              + Add Items
            </Link>
          ) : (
            <Link
              href={`/login?brand=pop&redirect=/pop-site/list/${id}`}
              className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
            >
              Sign In to Add
            </Link>
          )}
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* List Header */}
        <div className="mb-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <span>🛒</span> {list.title}
            </h1>
            <div className="flex items-center gap-2">
              {isLoggedIn && (
                <button
                  onClick={() => setShowBulkParse(true)}
                  className="text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1"
                >
                  📋 Paste Recipe
                </button>
              )}
              {isLoggedIn && (
                <button
                  onClick={() => setShowHousehold(true)}
                  className="text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1"
                >
                  👨‍👩‍👧 Household
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between mt-1">
            <p className="text-sm text-gray-500">
              {checkedCount > 0
                ? `${checkedCount} of ${totalItems} checked off`
                : `${totalItems} item${totalItems !== 1 ? 's' : ''}`}
            </p>
            {checkedCount > 0 && isLoggedIn && (
              <button
                onClick={handleClearCompleted}
                disabled={isClearing}
                className="text-xs font-medium text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                {isClearing ? 'Clearing...' : '🗑️ Clear Completed'}
              </button>
            )}
          </div>
        </div>

        {/* Savings Summary Banner */}
        {(itemsWithDeals > 0 || itemsWithSwaps > 0) && (
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

        {/* Items */}
        {totalItems === 0 ? (
          <div className="text-center py-16">
            <span className="text-5xl block mb-4">📝</span>
            <p className="text-gray-500 mb-4">Your list is empty</p>
            <Link
              href="/chat"
              className="inline-block bg-green-600 text-white font-medium px-6 py-3 rounded-xl hover:bg-green-700 transition-colors"
            >
              Chat with Pop to add items
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {list.items.map((item) => {
              const isChecked = checkedItems.has(item.id);
              const isExpanded = expandedItems.has(item.id);
              const tab = getItemTab(item.id);

              return (
                <li
                  key={item.id}
                  className={`bg-white rounded-2xl shadow-sm overflow-hidden transition-opacity ${
                    isChecked ? 'opacity-60' : ''
                  }`}
                >
                  {/* Item Row */}
                  <div className="flex items-center gap-3 px-4 py-4">
                    <button
                      onClick={() => toggleChecked(item.id)}
                      className={`w-6 h-6 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                        isChecked
                          ? 'bg-green-600 border-green-600'
                          : 'border-gray-300 hover:border-green-400'
                      }`}
                    >
                      {isChecked && (
                        <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>

                    <button
                      className="flex-1 min-w-0 text-left"
                      onClick={() => toggleExpanded(item.id)}
                    >
                      <span
                        className={`text-sm font-medium block truncate ${
                          isChecked ? 'line-through text-gray-400' : 'text-gray-900'
                        }`}
                      >
                        {item.title}
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
                        {item.department && (
                          <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
                            {item.department}
                          </span>
                        )}
                        {item.origin_channel && (
                          <span className="text-[10px] text-gray-400">
                            via {item.origin_channel}
                          </span>
                        )}
                        {item.lowest_price != null && (
                          <span className="text-xs font-semibold text-green-700">
                            from ${item.lowest_price.toFixed(2)}
                          </span>
                        )}
                        {item.deal_count > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                            🏷️ {item.deal_count} deal{item.deal_count !== 1 ? 's' : ''}
                          </span>
                        )}
                        {item.swaps.length > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
                            🔄 {item.swaps.length} swap{item.swaps.length !== 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </button>

                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingItem(item); }}
                      className="p-1.5 flex-shrink-0 text-gray-300 hover:text-green-600 transition-colors"
                      title="Edit item"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>

                    <button
                      onClick={() => toggleExpanded(item.id)}
                      className="p-1 flex-shrink-0"
                    >
                      <svg
                        className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  </div>

                  {/* Coupon Badge (PRD-08) */}
                  {item.coupon && (
                    <div className="px-4 py-2 border-t border-gray-50" data-testid={`coupon-badge-${item.id}`}>
                      <a
                        href={item.coupon.url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5 hover:bg-amber-100 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span className="text-sm">🎟️</span>
                        <span className="text-xs font-semibold text-amber-800">
                          {item.coupon.savings_display}
                        </span>
                        <span className="text-[10px] text-amber-600">
                          Clip Coupon{item.coupon.brand_name ? ` — ${item.coupon.brand_name}` : ''}
                        </span>
                      </a>
                    </div>
                  )}

                  {/* Social Action Bar (PRD-07) */}
                  {isLoggedIn && (
                    <div className="flex items-center gap-4 px-4 py-1.5 border-t border-gray-50" data-testid={`social-bar-${item.id}`}>
                      <button
                        data-testid={`like-btn-${item.id}`}
                        onClick={() => handleToggleLike(item.id)}
                        className={`flex items-center gap-1 text-xs transition-colors ${
                          (itemLikes[item.id]?.liked) ? 'text-red-500' : 'text-gray-400 hover:text-red-400'
                        }`}
                      >
                        <svg className="w-4 h-4" fill={(itemLikes[item.id]?.liked) ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                        </svg>
                        {(itemLikes[item.id]?.count || 0) > 0 && (
                          <span>{itemLikes[item.id].count}</span>
                        )}
                      </button>
                      <button
                        data-testid={`comment-btn-${item.id}`}
                        onClick={() => handleToggleComments(item.id)}
                        className={`flex items-center gap-1 text-xs transition-colors ${
                          commentingItemId === item.id ? 'text-green-600' : 'text-gray-400 hover:text-green-500'
                        }`}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        {Math.max(item.comment_count || 0, itemComments[item.id]?.length || 0) > 0 && (
                          <span>{Math.max(item.comment_count || 0, itemComments[item.id]?.length || 0)}</span>
                        )}
                      </button>
                    </div>
                  )}

                  {/* Inline Comment Thread (PRD-07) */}
                  {commentingItemId === item.id && (
                    <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50" data-testid={`comment-thread-${item.id}`}>
                      {(itemComments[item.id] || []).map((c) => (
                        <div key={c.id} className="flex gap-2 mb-2">
                          <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                            <span className="text-[10px] font-bold text-green-700">{(c.user_name || '?')[0].toUpperCase()}</span>
                          </div>
                          <div className="min-w-0">
                            <span className="text-xs font-medium text-gray-700">{c.user_name}</span>
                            {c.created_at && (
                              <span className="text-[10px] text-gray-400 ml-1">• {timeAgo(c.created_at)}</span>
                            )}
                            <p className="text-xs text-gray-600 mt-0.5">{c.text}</p>
                          </div>
                        </div>
                      ))}
                      <form
                        className="flex gap-2 mt-2"
                        onSubmit={(e) => { e.preventDefault(); handleSubmitComment(item.id); }}
                      >
                        <input
                          type="text"
                          value={commentText}
                          onChange={(e) => setCommentText(e.target.value)}
                          placeholder="Add a comment..."
                          className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-1 focus:ring-green-500 text-gray-900 placeholder-gray-400"
                          maxLength={500}
                        />
                        <button
                          type="submit"
                          disabled={!commentText.trim()}
                          className="text-xs font-medium text-green-600 hover:text-green-700 disabled:text-gray-300 disabled:cursor-not-allowed px-2"
                        >
                          Send
                        </button>
                      </form>
                    </div>
                  )}

                  {/* Expanded Section */}
                  {isExpanded && (item.deals.length > 0 || item.swaps.length > 0) && (
                    <div className="border-t border-gray-100">
                      {/* Tabs */}
                      {item.swaps.length > 0 && (
                        <div className="flex border-b border-gray-100">
                          <button
                            onClick={() => setItemTab(item.id, 'deals')}
                            className={`flex-1 text-xs font-medium py-2.5 text-center transition-colors ${
                              tab === 'deals'
                                ? 'text-green-700 border-b-2 border-green-600'
                                : 'text-gray-400 hover:text-gray-600'
                            }`}
                          >
                            🏷️ Best Deals ({item.deals.length})
                          </button>
                          <button
                            onClick={() => setItemTab(item.id, 'swaps')}
                            className={`flex-1 text-xs font-medium py-2.5 text-center transition-colors ${
                              tab === 'swaps'
                                ? 'text-amber-700 border-b-2 border-amber-500'
                                : 'text-gray-400 hover:text-gray-600'
                            }`}
                          >
                            🔄 Try Instead ({item.swaps.length})
                          </button>
                        </div>
                      )}

                      {/* Deals Tab */}
                      {tab === 'deals' && item.deals.length > 0 && (
                        <div className="px-4 py-3 bg-green-50/30">
                          <div className="space-y-2">
                            {item.deals.map((deal) => (
                              <a
                                key={deal.id}
                                href={deal.url || '#'}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-3 bg-white rounded-xl px-3 py-2.5 hover:shadow-md transition-shadow"
                              >
                                {deal.image_url ? (
                                  <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 relative">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                      src={deal.image_url}
                                      alt=""
                                      className="w-full h-full object-cover"
                                    />
                                  </div>
                                ) : (
                                  <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                                    <span className="text-lg">🏷️</span>
                                  </div>
                                )}
                                <div className="flex-1 min-w-0">
                                  <span className="text-sm text-gray-900 block truncate">
                                    {deal.title}
                                  </span>
                                  <span className="text-xs text-gray-500">{deal.source}</span>
                                </div>
                                {deal.price != null && (
                                  <span className="text-sm font-semibold text-green-700 flex-shrink-0">
                                    ${deal.price.toFixed(2)}
                                  </span>
                                )}
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Swaps Tab */}
                      {tab === 'swaps' && item.swaps.length > 0 && (
                        <div className="px-4 py-3 bg-amber-50/30">
                          <p className="text-xs text-amber-700 mb-2">
                            Try these alternatives and save!
                          </p>
                          <div className="space-y-2">
                            {item.swaps.map((swap) => (
                              <a
                                key={swap.id}
                                href={swap.url || '#'}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-3 bg-white rounded-xl px-3 py-2.5 hover:shadow-md transition-shadow"
                              >
                                {swap.image_url ? (
                                  <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 relative">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                      src={swap.image_url}
                                      alt=""
                                      className="w-full h-full object-cover"
                                    />
                                  </div>
                                ) : (
                                  <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                                    <span className="text-lg">🔄</span>
                                  </div>
                                )}
                                <div className="flex-1 min-w-0">
                                  <span className="text-sm text-gray-900 block truncate">
                                    {swap.title}
                                  </span>
                                  <span className="text-xs text-gray-500">{swap.source}</span>
                                </div>
                                <div className="text-right flex-shrink-0">
                                  {swap.price != null && (
                                    <span className="text-sm font-semibold text-amber-700 block">
                                      ${swap.price.toFixed(2)}
                                    </span>
                                  )}
                                  {swap.savings_vs_first != null && swap.savings_vs_first > 0 && (
                                    <span className="text-[10px] font-bold text-green-600">
                                      Save ${swap.savings_vs_first.toFixed(2)}
                                    </span>
                                  )}
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* No swaps yet — placeholder for GroFlo */}
                      {tab === 'deals' && item.deals.length === 0 && (
                        <div className="px-4 py-6 text-center">
                          <p className="text-xs text-gray-400">Pop is searching for deals...</p>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {/* Join List CTA for logged-in non-members */}
        {isLoggedIn && !hasJoined && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded-2xl px-4 py-4 text-center">
            <p className="text-sm text-green-800 font-medium mb-3">
              Want to add items to this list together?
            </p>
            {joinError && (
              <p className="text-xs text-red-500 mb-2">{joinError}</p>
            )}
            <button
              onClick={handleJoinList}
              disabled={isJoining}
              className="inline-flex items-center gap-2 bg-green-600 text-white text-sm font-semibold px-5 py-2.5 rounded-full hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {isJoining ? 'Joining...' : '🤝 Join this list'}
            </button>
          </div>
        )}
        {isLoggedIn && hasJoined && (
          <div className="mt-4 bg-green-100 border border-green-300 rounded-2xl px-4 py-3 text-center">
            <p className="text-sm text-green-800 font-semibold">✓ You joined this list!</p>
            <Link
              href={`/pop-site/chat?list=${id}`}
              className="inline-block mt-2 text-sm text-green-700 underline hover:text-green-900"
            >
              Add items now →
            </Link>
          </div>
        )}
        {/* Dual CopyLink System (PRD-06) */}
        {totalItems > 0 && (
          <div className="mt-6 space-y-3">
            <p className="text-center text-xs text-gray-500 font-medium uppercase tracking-wide">United we save</p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3" data-testid="dual-copylink">
              {/* Share List Link */}
              <button
                data-testid="copy-list-link"
                disabled={isSharing}
                onClick={async () => {
                  setIsSharing(true);
                  try {
                    let shareUrl = window.location.href;
                    if (isLoggedIn) {
                      const res = await fetch(`/api/pop/invite/${id}`, { method: 'POST' });
                      if (res.ok) {
                        const data = await res.json();
                        shareUrl = data.invite_url || shareUrl;
                      }
                    }
                    if (navigator.share) {
                      await navigator.share({ title: list.title, text: `Join my grocery list on Pop! United we save.`, url: shareUrl });
                    } else {
                      await navigator.clipboard.writeText(shareUrl);
                      setCopiedInvite(true);
                      setTimeout(() => setCopiedInvite(false), 2500);
                    }
                  } finally {
                    setIsSharing(false);
                  }
                }}
                className="inline-flex items-center gap-2 text-sm text-green-700 bg-green-50 hover:bg-green-100 font-medium px-5 py-2.5 rounded-full transition-colors disabled:opacity-50"
              >
                {copiedInvite ? '✓ List link copied!' : isSharing ? 'Creating link...' : '🏠 Share List with Family'}
              </button>

              {/* Refer Friends / TeamPop Link */}
              {isLoggedIn && referralLink && (
                <button
                  data-testid="copy-referral-link"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(referralLink);
                      setCopiedReferral(true);
                      setTimeout(() => setCopiedReferral(false), 2500);
                    } catch {
                      // fallback: ignore
                    }
                  }}
                  className="inline-flex items-center gap-2 text-sm text-purple-700 bg-purple-50 hover:bg-purple-100 font-medium px-5 py-2.5 rounded-full transition-colors"
                >
                  {copiedReferral ? '✓ Referral link copied!' : '🤝 Refer Friends — Save $100/mo'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Edit Item Modal */}
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

      {/* Household Modal */}
      {showHousehold && list && (
        <HouseholdModal
          projectId={list.project_id}
          onClose={() => setShowHousehold(false)}
        />
      )}

      {/* Bulk Parse Modal */}
      {showBulkParse && list && (
        <BulkParseModal
          projectId={list.project_id}
          onClose={() => setShowBulkParse(false)}
          onParsed={handleBulkParsed}
        />
      )}

      {/* Footer */}
      <footer className="mt-12 py-6 text-center text-xs text-gray-400">
        <p>
          Powered by <Link href="/" className="text-green-600 hover:underline">Pop</Link> — your AI grocery savings assistant
        </p>
      </footer>
    </div>
  );
}
