'use client';

import { useState, useEffect } from 'react';
import { Package, Trash2, ChevronLeft, Menu, LogOut } from 'lucide-react';
import { useShoppingStore, Row } from '../store';
import { useRouter } from 'next/navigation';

export default function RequestsSidebar() {
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(true);
  const store = useShoppingStore();
  const router = useRouter();

  const selectedRow = store.rows.find(r => r.id === store.activeRowId) || null;

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
      router.push('/login');
    } catch (e) {
      console.error('Logout failed:', e);
    }
  };

  const fetchRows = async () => {
    try {
      const res = await fetch('/api/rows', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        store.setRows(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error("Failed to fetch rows", e);
    } finally {
      setLoading(false);
    }
  };

  const deleteRow = async (id: number) => {
    try {
      const res = await fetch(`/api/rows?id=${id}`, { method: 'DELETE' });
      if (res.ok) {
        store.removeRow(id);
      }
    } catch (e) {
      console.error("Failed to delete row", e);
    }
  };

  const handleCardClick = async (row: Row) => {
    if (store.activeRowId === row.id) return;
    
    console.log('[Sidebar] === CARD CLICK FLOW START ===');
    console.log('[Sidebar] 3a. User clicked card:', row.id, row.title);

    store.setCurrentQuery(row.title);
    store.setActiveRowId(row.id);
    store.setCardClickQuery(row.title);
    console.log('[Sidebar] 3b. Zustand updated - query:', row.title, 'activeRowId:', row.id);

    console.log('[Sidebar] 3c. Chat will be notified via store');

    console.log('[Sidebar] 3d. Running search for:', row.title);
    store.setIsSearching(true);
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: row.title }),
      });
      if (res.ok) {
        const data = await res.json();
        console.log('[Sidebar] Search returned:', data.results?.length || 0, 'products');
        store.setSearchResults(data.results || []);
      }
    } catch (e) {
      console.error('[Sidebar] Search failed:', e);
      store.setSearchResults([]);
    }

    console.log('[Sidebar] === CARD CLICK FLOW END ===');
  };

  useEffect(() => {
    fetchRows();
  }, []);

  if (!isExpanded) {
    return (
      <div className="h-full bg-gray-800 border-r border-gray-700 flex flex-col items-center py-4 w-12 transition-all duration-300 shrink-0">
        <button 
          onClick={() => setIsExpanded(true)}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
          title="Expand Requests"
        >
          <Menu size={20} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col transition-all duration-300 h-full relative group shrink-0">
      <div className="p-4 border-b border-gray-700">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Requests</h2>
          <div className="flex items-center gap-2">
            <button onClick={fetchRows} className="text-sm text-blue-400 hover:text-blue-300">
              Refresh
            </button>
            <button 
              onClick={() => setIsExpanded(false)}
              className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
              title="Collapse"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {loading && store.rows.length === 0 && (
          <div className="text-center text-gray-500 py-10">Loading...</div>
        )}

        {!loading && store.rows.length === 0 && (
          <div className="text-center text-gray-500 py-10">
            <Package className="mx-auto h-8 w-8 text-gray-600 mb-2" />
            <p className="text-sm">No requests yet</p>
          </div>
        )}

        {store.rows.map((row: Row) => (
          <div
            key={row.id}
            onClick={() => handleCardClick(row)}
            className={`p-3 rounded-lg cursor-pointer transition-colors ${
              selectedRow?.id === row.id 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
            }`}
          >
            <div className="flex justify-between items-start">
              <h3 className="font-medium text-sm line-clamp-1">{row.title}</h3>
              <button
                onClick={(e) => { e.stopPropagation(); deleteRow(row.id); }}
                className="p-1 hover:bg-red-500/20 rounded"
              >
                <Trash2 size={14} className="text-red-400" />
              </button>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                row.status === 'sourcing' ? 'bg-yellow-500/20 text-yellow-400' : 
                row.status === 'closed' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
              }`}>
                {row.status}
              </span>
              <span className="text-xs text-gray-400">#{row.id}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="p-4 border-t border-gray-700">
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors w-full p-2 rounded hover:bg-gray-700"
        >
          <LogOut size={16} />
          Sign Out
        </button>
      </div>
    </div>
  );
}
