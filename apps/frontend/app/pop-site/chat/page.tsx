'use client';

import { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import PopListSidebar from './PopListSidebar';

const LS_ITEMS_KEY = 'pop_guest_list_items';
const LS_GUEST_PROJECT_KEY = 'pop_guest_project_id';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface Deal {
  id: number;
  title: string;
  price: number;
  source: string;
  url: string;
  image_url: string | null;
  is_selected: boolean;
}

interface ListItem {
  id: number;
  title: string;
  status: string;
  deals?: Deal[];
  lowest_price?: number | null;
  deal_count?: number;
  ui_schema?: Record<string, unknown> | null;
}

function PopChatInner() {
  const searchParams = useSearchParams();
  const sharedListId = searchParams.get('list');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hey! I'm Pop, your grocery savings assistant. Tell me what you need from the store and I'll find the best deals for you. Try something like \"I need milk, eggs, and bread\".",
    },
  ]);
  const [listItems, setListItems] = useState<ListItem[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [projectTitle, setProjectTitle] = useState<string>('My Shopping List');
  const [allProjects, setAllProjects] = useState<{id: number, title: string}[]>([]);
  const [activeRequests, setActiveRequests] = useState(0);
  const isLoading = activeRequests > 0;
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');
  const [expandedItemIds, setExpandedItemIds] = useState<Set<number>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const isCommittingRef = useRef(false);

  const handleDuplicateProject = async () => {
    if (!projectId || !isLoggedIn) return;
    try {
      const res = await fetch(`/api/pop/list/${projectId}/duplicate`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setProjectId(data.project_id);
        setProjectTitle(data.title);
        // refresh items
        const listRes = await fetch(`/api/pop/my-list?project_id=${data.project_id}`);
        if (listRes.ok) {
          const listData = await listRes.json();
          const items = listData.items || [];
          setListItems(items);
          setExpandedItemIds(new Set(items.map((i: ListItem) => i.id)));
        }
        // refresh all projects
        const listsRes = await fetch('/api/pop/lists');
        if (listsRes.ok) {
          setAllProjects(await listsRes.json());
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSwitchProject = async (id: number) => {
    try {
      const listRes = await fetch(`/api/pop/my-list?project_id=${id}`);
      if (listRes.ok) {
        const listData = await listRes.json();
        setProjectId(listData.project_id);
        setProjectTitle(listData.title || 'My Shopping List');
        const items = listData.items || [];
        setListItems(items);
        setExpandedItemIds(new Set(items.map((i: ListItem) => i.id)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateProject = async () => {
    const title = window.prompt("Enter new list name:");
    if (!title || !title.trim()) return;
    try {
      const res = await fetch('/api/pop/lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        setProjectId(data.project_id);
        setProjectTitle(data.title);
        setListItems([]);
        const listsRes = await fetch('/api/pop/lists');
        if (listsRes.ok) {
          setAllProjects(await listsRes.json());
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (editingId !== null) editInputRef.current?.focus();
  }, [editingId]);

  // On mount: try to load list from DB (logged-in) or localStorage (guest)
  useEffect(() => {
    async function loadInitialList() {
      try {
        // If a shared list ID is provided, load that list directly
        if (sharedListId) {
          const sharedRes = await fetch(`/api/pop/list/${sharedListId}`);
          if (sharedRes.ok) {
            const data = await sharedRes.json();
            setIsLoggedIn(true);
            setProjectId(data.project_id);
            if (data.items?.length > 0) {
              setListItems(data.items);
              setExpandedItemIds(new Set(data.items.map((i: ListItem) => i.id)));
            }
            return;
          }
        }
        const res = await fetch('/api/pop/my-list');
        if (res.ok) {
          const data = await res.json();
          setIsLoggedIn(true);
          if (data.project_id) {
            setProjectId(data.project_id);
            if (data.items?.length > 0) {
              setListItems(data.items);
              setExpandedItemIds(new Set(data.items.map((i: ListItem) => i.id)));
            }
          }
          return;
        }
        // Only fall through to localStorage when explicitly not authenticated.
        // Any other error (500, 503) should not silently drop to guest mode.
        if (res.status !== 401) return;
      } catch {
        // Network error — stay in guest mode
      }
      // Guest: restore from localStorage
      try {
        const raw = localStorage.getItem(LS_ITEMS_KEY);
        if (raw) {
          const saved: ListItem[] = JSON.parse(raw);
          if (saved.length > 0) {
            setListItems(saved);
            setExpandedItemIds(new Set(saved.map((i) => i.id)));
          }
        }
        const savedProjectId = localStorage.getItem(LS_GUEST_PROJECT_KEY);
        if (savedProjectId) setProjectId(Number(savedProjectId));
      } catch {
        // ignore
      }
    }
    loadInitialList();
  }, [sharedListId]);

  // Persist guest items + project_id to localStorage whenever they change
  useEffect(() => {
    if (!isLoggedIn) {
      if (listItems.length > 0) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(listItems));
      if (projectId) localStorage.setItem(LS_GUEST_PROJECT_KEY, String(projectId));
    }
  }, [listItems, isLoggedIn, projectId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;

    const userMsg: Message = { id: `user-${Date.now()}`, role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setActiveRequests((prev) => prev + 1);

    // Refocus immediately using setTimeout to sidestep React render loop
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);

    const guestProjectId = !isLoggedIn
      ? projectId ?? (localStorage.getItem(LS_GUEST_PROJECT_KEY) ? Number(localStorage.getItem(LS_GUEST_PROJECT_KEY)) : null)
      : null;

    try {
      const res = await fetch('/api/pop/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, ...(guestProjectId ? { guest_project_id: guestProjectId } : {}) }),
      });
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        { id: `asst-${Date.now()}`, role: 'assistant', content: data.reply || 'Got it!' },
      ]);

      if (data.list_items?.length > 0) {
        setListItems(data.list_items);
        setExpandedItemIds(new Set(data.list_items.map((i: ListItem) => i.id)));
      }
      if (data.project_id) setProjectId(data.project_id);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: 'assistant', content: 'Oops, something went wrong. Try again!' },
      ]);
    } finally {
      setActiveRequests((prev) => Math.max(0, prev - 1));
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  };

  const handleDeleteItem = useCallback(async (item: ListItem) => {
    if (isLoggedIn) {
      await fetch(`/api/pop/item/${item.id}`, { method: 'DELETE' });
    }
    setListItems((prev) => {
      const next = prev.filter((i) => i.id !== item.id);
      if (!isLoggedIn) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(next));
      return next;
    });
  }, [isLoggedIn]);

  const startEdit = (item: ListItem) => {
    setEditingId(item.id);
    setEditValue(item.title);
  };

  const commitEdit = useCallback(async (item: ListItem) => {
    if (isCommittingRef.current) return;
    const newTitle = editValue.trim();
    if (!newTitle || newTitle === item.title) {
      setEditingId(null);
      return;
    }
    isCommittingRef.current = true;
    setEditingId(null);
    try {
      if (isLoggedIn) {
        await fetch(`/api/pop/item/${item.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle }),
        });
      }
      setListItems((prev) => {
        const next = prev.map((i) => (i.id === item.id ? { ...i, title: newTitle } : i));
        if (!isLoggedIn) localStorage.setItem(LS_ITEMS_KEY, JSON.stringify(next));
        return next;
      });
    } finally {
      isCommittingRef.current = false;
    }
  }, [editValue, isLoggedIn]);

  const handleClaimDeal = useCallback(async (itemId: number, dealId: number) => {
    try {
      await fetch(`/api/pop/offer/${dealId}/claim`, { method: 'POST' });
      setListItems((prev) =>
        prev.map((item) => {
          if (item.id !== itemId || !item.deals) return item;
          return {
            ...item,
            deals: item.deals.map((d) => ({
              ...d,
              is_selected: d.id === dealId,
            })),
          };
        })
      );
    } catch {
      // ignore
    }
  }, []);

  const sourceLabel = (source: string): string => {
    const map: Record<string, string> = {
      kroger: 'Kroger',
      rainforest_amazon: 'Amazon',
      ebay_browse: 'eBay',
      searchapi_google_shopping: 'Google',
    };
    return map[source] || source;
  };

  const sourceColor = (source: string): string => {
    const map: Record<string, string> = {
      kroger: 'bg-blue-100 text-blue-700',
      rainforest_amazon: 'bg-orange-100 text-orange-700',
      ebay_browse: 'bg-red-100 text-red-700',
      searchapi_google_shopping: 'bg-emerald-100 text-emerald-700',
    };
    return map[source] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/pop-avatar.png" alt="Pop" width={32} height={32} className="rounded-full" />
            <span className="text-lg font-bold text-green-700">Pop</span>
          </Link>
          <div className="flex items-center gap-3">
            <a
              href="https://buy.stripe.com/test_dRm5kEcSC6lWc0NeUh1ck00"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-50 text-green-700 hover:bg-green-100 transition-colors mr-2"
            >
              <span>☕️</span> Tip Jar
            </a>
            {listItems.length > 0 && (
              <Link
                href={projectId ? `/list/${projectId}` : '#'}
                className="text-xs bg-green-100 text-green-800 px-2.5 py-1 rounded-full font-medium hover:bg-green-200 transition-colors"
              >
                {listItems.length} item{listItems.length !== 1 ? 's' : ''} on list →
              </Link>
            )}
            <Link
              href="/login"
              className="text-sm text-gray-500 hover:text-green-700 transition-colors"
            >
              {isLoggedIn ? 'My Account' : 'Sign In'}
            </Link>
          </div>
        </div>
      </nav>

      <div className="flex-1 flex flex-col lg:flex-row max-w-6xl mx-auto w-full">
        {/* Chat Panel */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-end gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <Image src="/pop-avatar.png" alt="Pop" width={28} height={28} className="rounded-full flex-shrink-0 mb-1" />
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex items-end gap-2 justify-start">
                <Image src="/pop-avatar.png" alt="Pop" width={28} height={28} className="rounded-full flex-shrink-0 mb-1" />
                <div className="bg-gray-100 rounded-2xl px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-gray-100 bg-white p-4">
            <form onSubmit={handleSubmit} className="flex gap-3 max-w-2xl mx-auto">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What do you need from the store?"
                className="flex-1 px-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm text-gray-900 placeholder-gray-400"
              />
              <button
                type="submit"
                disabled={!input.trim()}
                className="bg-green-600 text-white px-5 py-3 rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : null}
                Send
              </button>
            </form>
            <p className="text-center text-xs text-gray-400 mt-2">
              Pop finds deals on groceries. Try: &quot;eggs, butter, and whole wheat bread&quot;
            </p>
          </div>
        </div>

        {/* List Sidebar */}
        {(listItems.length > 0 || isLoggedIn) && (
          <PopListSidebar
            listItems={listItems}
            isLoggedIn={isLoggedIn}
            projectId={projectId}
            projectTitle={projectTitle}
            allProjects={allProjects}
            expandedItemIds={expandedItemIds}
            setExpandedItemIds={setExpandedItemIds}
            editingId={editingId}
            editValue={editValue}
            setEditValue={setEditValue}
            editInputRef={editInputRef}
            startEdit={startEdit}
            commitEdit={commitEdit}
            setEditingId={setEditingId}
            handleSwitchProject={handleSwitchProject}
            handleCreateProject={handleCreateProject}
            handleDuplicateProject={handleDuplicateProject}
            handleDeleteItem={handleDeleteItem}
            handleClaimDeal={handleClaimDeal}
            sourceColor={sourceColor}
            sourceLabel={sourceLabel}
          />
        )}
      </div>
    </div>
  );
}

export default function PopChatPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-white flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600" /></div>}>
      <PopChatInner />
    </Suspense>
  );
}
