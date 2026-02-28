'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import Image from 'next/image';

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
}

interface PopList {
  project_id: number;
  title: string;
  items: ListItem[];
}

type TabType = 'deals' | 'swaps';

export default function PopListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [list, setList] = useState<PopList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());
  const [activeTab, setActiveTab] = useState<Record<number, TabType>>({});

  useEffect(() => {
    async function fetchList() {
      try {
        const res = await fetch(`/api/pop/list/${id}`);
        if (!res.ok) throw new Error('List not found');
        const data = await res.json();
        setList(data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load list');
      } finally {
        setLoading(false);
      }
    }
    fetchList();
  }, [id]);

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
          <Link
            href="/chat"
            className="text-sm bg-green-600 text-white px-4 py-2 rounded-full hover:bg-green-700 transition-colors"
          >
            + Add Items
          </Link>
        </div>
      </nav>

      <div className="max-w-2xl mx-auto px-4 py-6">
        {/* List Header */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span>🛒</span> {list.title}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {checkedCount > 0
              ? `${checkedCount} of ${totalItems} checked off`
              : `${totalItems} item${totalItems !== 1 ? 's' : ''}`}
          </p>
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
              const isExpanded = expandedItem === item.id;
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
                      onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                    >
                      <span
                        className={`text-sm font-medium block truncate ${
                          isChecked ? 'line-through text-gray-400' : 'text-gray-900'
                        }`}
                      >
                        {item.title}
                      </span>
                      <div className="flex items-center gap-2 mt-0.5">
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
                      onClick={() => setExpandedItem(isExpanded ? null : item.id)}
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
                                  <img
                                    src={deal.image_url}
                                    alt=""
                                    className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                                  />
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
                                  <img
                                    src={swap.image_url}
                                    alt=""
                                    className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                                  />
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

        {/* Share List CTA */}
        {totalItems > 0 && (
          <div className="mt-6 text-center">
            <button
              onClick={() => {
                if (navigator.share) {
                  navigator.share({
                    title: list.title,
                    text: `Check out my grocery list on Pop!`,
                    url: window.location.href,
                  });
                } else {
                  navigator.clipboard.writeText(window.location.href);
                }
              }}
              className="inline-flex items-center gap-2 text-sm text-green-700 bg-green-50 hover:bg-green-100 font-medium px-5 py-2.5 rounded-full transition-colors"
            >
              📤 Share List with Family
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-12 py-6 text-center text-xs text-gray-400">
        <p>
          Powered by <Link href="/" className="text-green-600 hover:underline">Pop</Link> — your AI grocery savings assistant
        </p>
      </footer>
    </div>
  );
}
