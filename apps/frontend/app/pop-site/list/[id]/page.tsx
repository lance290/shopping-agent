'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';

interface Deal {
  id: number;
  title: string;
  price: number | null;
  source: string;
  url: string | null;
  image_url: string | null;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
  created_at: string | null;
  deals: Deal[];
}

interface PopList {
  project_id: number;
  title: string;
  items: ListItem[];
}

export default function PopListPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [list, setList] = useState<PopList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItem, setExpandedItem] = useState<number | null>(null);

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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl">🍿</span>
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
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <span>🛒</span> {list.title}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {list.items.length} item{list.items.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Items */}
        {list.items.length === 0 ? (
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
            {list.items.map((item) => (
              <li key={item.id} className="bg-white rounded-2xl shadow-sm overflow-hidden">
                <button
                  className="w-full flex items-center gap-4 px-4 py-4 text-left hover:bg-gray-50 transition-colors"
                  onClick={() =>
                    setExpandedItem(expandedItem === item.id ? null : item.id)
                  }
                >
                  <div className="w-6 h-6 rounded-full border-2 border-gray-300 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-gray-900 block truncate">
                      {item.title}
                    </span>
                    {item.deals.length > 0 && (
                      <span className="text-xs text-green-600 font-medium">
                        {item.deals.length} deal{item.deals.length !== 1 ? 's' : ''} found
                      </span>
                    )}
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      expandedItem === item.id ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Expanded deals */}
                {expandedItem === item.id && item.deals.length > 0 && (
                  <div className="border-t border-gray-100 px-4 py-3 bg-green-50/30">
                    <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
                      Best deals
                    </p>
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
              </li>
            ))}
          </ul>
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
